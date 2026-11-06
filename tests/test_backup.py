"""Backup encryption, retention, status, and the documented restore path."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from cryptography.exceptions import InvalidTag

from app.config import get_settings
from app.services import backup
from app.services.backup import decrypt_bytes, encrypt_bytes, prepare_backup, prune_old_backups
from tests.conftest import _PARSED_URL, ROOT, admin_connection, pg_args, pg_env, sign_in

PASSPHRASE = "test-only-backup-passphrase"


@pytest.fixture
def backup_dir(tmp_path, monkeypatch) -> Path:
    settings = get_settings()
    monkeypatch.setattr(settings, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "BACKUP_PASSPHRASE", PASSPHRASE)
    return tmp_path


def _write_backup(directory: Path, when: datetime) -> Path:
    path = directory / f"release_radar_{when.strftime('%Y%m%dT%H%M%SZ')}.dump.enc"
    path.write_bytes(b"x")
    return path


def test_encryption_round_trip():
    blob = encrypt_bytes("データ".encode(), PASSPHRASE)
    assert blob.startswith(b"RRBK1\n")
    assert "データ".encode() not in blob
    assert decrypt_bytes(blob, PASSPHRASE) == "データ".encode()


def test_wrong_passphrase_fails():
    with pytest.raises(InvalidTag):
        decrypt_bytes(encrypt_bytes(b"data", PASSPHRASE), "another-passphrase")


def test_tampered_file_fails():
    blob = bytearray(encrypt_bytes(b"data", PASSPHRASE))
    blob[-1] ^= 1
    with pytest.raises(InvalidTag):
        decrypt_bytes(bytes(blob), PASSPHRASE)


def test_other_files_are_rejected():
    with pytest.raises(ValueError, match="bad magic"):
        decrypt_bytes(b"MMBK1\nnot ours", PASSPHRASE)


def test_retention_removes_only_files_past_the_limit(backup_dir):
    now = datetime(2026, 11, 7, 3, 0, tzinfo=UTC)
    keep = _write_backup(backup_dir, now - timedelta(days=13))
    remove = _write_backup(backup_dir, now - timedelta(days=15))
    unrelated = backup_dir / "notes.txt"
    unrelated.write_text("mine")

    assert prune_old_backups(now) == 1
    assert keep.exists()
    assert not remove.exists()
    assert unrelated.exists()


async def test_no_passphrase_means_skipped_with_a_reason_and_no_file(backup_dir, monkeypatch):
    monkeypatch.setattr(get_settings(), "BACKUP_PASSPHRASE", None)
    result = await prepare_backup()
    assert result.status == "skipped"
    assert "BACKUP_PASSPHRASE" in result.detail
    assert list(backup_dir.iterdir()) == []


async def test_failed_dump_is_reported_and_old_backups_survive(backup_dir, monkeypatch):
    old = _write_backup(backup_dir, datetime.now(UTC) - timedelta(days=60))
    monkeypatch.setattr(backup, "_pg_dump_binary", lambda: "/nonexistent/pg_dump")
    result = await prepare_backup()
    assert result.status == "failed"
    assert old.exists()


async def test_unwritable_folder_is_reported(backup_dir, monkeypatch):
    blocker = backup_dir / "not-a-folder"
    blocker.write_text("in the way")
    monkeypatch.setattr(get_settings(), "BACKUP_DIR", str(blocker / "backups"))
    result = await prepare_backup()
    assert result.status == "failed"
    assert "backup folder" in result.detail


async def test_full_backup_and_documented_restore(backup_dir, client, make_user):
    """pg_dump, encrypt, then decrypt with the ops script, pg_restore and read the data back."""
    await make_user("restored@example.org")
    result = await prepare_backup()
    assert result.status == "succeeded", result.detail

    encrypted = next(backup_dir.glob("release_radar_*.dump.enc"))
    decrypted = subprocess.run(
        [sys.executable, os.path.join(ROOT, "ops/decrypt_backup.py"), str(encrypted)],
        env={**os.environ, "BACKUP_PASSPHRASE": PASSPHRASE},
        capture_output=True,
        text=True,
    )
    assert decrypted.returncode == 0, decrypted.stderr
    dump = encrypted.with_suffix("")
    assert dump.is_file()

    restore_db = "release_radar_restore_test"
    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{restore_db}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{restore_db}"')
    finally:
        await connection.close()

    restored = subprocess.run(
        ["pg_restore", *pg_args(restore_db), "--no-owner", "--exit-on-error", str(dump)],
        env=pg_env(),
        capture_output=True,
        text=True,
    )
    assert restored.returncode == 0, restored.stderr

    check = await asyncpg.connect(
        host=_PARSED_URL.host,
        port=_PARSED_URL.port or 5432,
        user=_PARSED_URL.username,
        password=_PARSED_URL.password,
        database=restore_db,
    )
    try:
        emails = {row["email"] for row in await check.fetch("SELECT email FROM users")}
    finally:
        await check.close()
    assert "restored@example.org" in emails

    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE "{restore_db}" WITH (FORCE)')
    finally:
        await connection.close()


def test_decrypt_script_reports_a_wrong_passphrase(backup_dir):
    encrypted = backup_dir / "release_radar_20260101T000000Z.dump.enc"
    encrypted.write_bytes(encrypt_bytes(b"data", PASSPHRASE))
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "ops/decrypt_backup.py"), str(encrypted)],
        env={**os.environ, "BACKUP_PASSPHRASE": "another-passphrase"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "could not decrypt" in result.stderr
    assert not encrypted.with_suffix("").exists()


async def test_status_requires_an_admin(client, make_user):
    await make_user()
    body = await sign_in(client, "editor@example.org", "correct-horse-battery")
    response = await client.get(
        "/api/v1/backups/status", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert response.status_code == 403


async def test_manual_backup_shows_up_in_the_status(client, admin_headers, backup_dir):
    before = await client.get("/api/v1/backups/status", headers=admin_headers)
    assert before.json()["latest"] is None
    assert before.json()["last_run"] is None
    assert before.json()["configured"] is True
    assert before.json()["retention_days"] == 14

    started = await client.post("/api/v1/backups/run", headers=admin_headers)
    assert started.status_code == 202

    after = (await client.get("/api/v1/backups/status", headers=admin_headers)).json()
    assert after["last_run"]["status"] == "succeeded", after["last_run"]["detail"]
    assert after["latest"]["filename"].startswith("release_radar_")
    assert after["latest"]["size_bytes"] > 0

    runs = await client.get("/api/v1/jobs/runs", headers=admin_headers)
    assert [run["job_key"] for run in runs.json()] == ["backup-manual"]


async def test_manual_backup_without_a_passphrase_is_refused_with_a_reason(
    client, admin_headers, monkeypatch
):
    monkeypatch.setattr(get_settings(), "BACKUP_PASSPHRASE", None)
    response = await client.post("/api/v1/backups/run", headers=admin_headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "backup_not_configured"}
