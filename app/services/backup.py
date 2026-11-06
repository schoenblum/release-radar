"""Nightly encrypted database backup (R5.2.5).

``pg_dump -Fc`` of the whole database, encrypted with a key derived from
``BACKUP_PASSPHRASE`` and written to ``BACKUP_DIR``, which is the NAS share in
production. Files older than ``BACKUP_RETENTION_DAYS`` are removed, but only
after a new backup has succeeded, so failures can never empty the folder.

File format (``*.dump.enc``):
    b"RRBK1\\n" (6) || salt (16) || nonce (12) || AES-256-GCM ciphertext
Key = Scrypt(passphrase, salt, n=2**14, r=8, p=1, length=32). The magic header
is the GCM associated data. ``ops/decrypt_backup.py`` decrypts it and needs only
the ``cryptography`` package. ``ops/README.md`` documents the restore.
"""

import asyncio
import contextlib
import logging
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from sqlalchemy import func, select
from sqlalchemy.engine.url import make_url

from app.config import get_settings
from app.database import SessionLocal
from app.services.scheduler import JobResult

logger = logging.getLogger(__name__)

MAGIC = b"RRBK1\n"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
FILE_PATTERN = "release_radar_*.dump.enc"
_FILE_TIMESTAMP = re.compile(r"release_radar_(\d{8}T\d{6}Z)\.dump\.enc$")
_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
# Stops a manual backup and the nightly one from running at the same moment.
_BACKUP_LOCK_KEY = 0x5252_4B55


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_bytes(plaintext: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    ciphertext = AESGCM(_derive_key(passphrase, salt)).encrypt(nonce, plaintext, MAGIC)
    return MAGIC + salt + nonce + ciphertext


def decrypt_bytes(blob: bytes, passphrase: str) -> bytes:
    if blob[: len(MAGIC)] != MAGIC:
        raise ValueError("Not a Release Radar backup file (bad magic header).")
    body = blob[len(MAGIC) :]
    salt, nonce, ciphertext = body[:16], body[16:28], body[28:]
    return AESGCM(_derive_key(passphrase, salt)).decrypt(nonce, ciphertext, MAGIC)


def _backup_dir() -> Path:
    return Path(get_settings().BACKUP_DIR)


def _created_at(path: Path) -> datetime:
    """Read the time from the file name. Copying to a NAS can change the mtime."""
    match = _FILE_TIMESTAMP.search(path.name)
    if match:
        return datetime.strptime(match.group(1), _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def list_backups() -> list[Path]:
    """Backups in the folder, newest first."""
    directory = _backup_dir()
    if not directory.is_dir():
        return []
    return sorted(directory.glob(FILE_PATTERN), key=_created_at, reverse=True)


def latest_backup_info() -> dict | None:
    backups = list_backups()
    if not backups:
        return None
    newest = backups[0]
    return {
        "filename": newest.name,
        "size_bytes": newest.stat().st_size,
        "created_at": _created_at(newest),
    }


def prune_old_backups(now: datetime | None = None) -> int:
    """Delete backups past the retention period. Returns how many were removed."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=get_settings().BACKUP_RETENTION_DAYS)
    removed = 0
    for path in list_backups():
        if _created_at(path) < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _pg_dump_binary() -> str:
    return shutil.which("pg_dump") or "pg_dump"


async def _pg_dump() -> bytes:
    url = make_url(get_settings().DATABASE_URL)
    env = dict(os.environ)
    if url.password:
        env["PGPASSWORD"] = url.password
    process = await asyncio.create_subprocess_exec(
        _pg_dump_binary(),
        "-h",
        url.host or "localhost",
        "-p",
        str(url.port or 5432),
        "-U",
        url.username or "postgres",
        "-d",
        url.database or "",
        "-Fc",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        message = stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"pg_dump exited with {process.returncode}: {message}")
    return stdout


async def prepare_backup() -> JobResult:
    """Create one encrypted backup and return its visible outcome."""
    settings = get_settings()
    if not settings.BACKUP_PASSPHRASE:
        return JobResult("skipped", "BACKUP_PASSPHRASE is not configured.")

    # The transaction, and with it the lock, stays open for the whole dump.
    async with SessionLocal() as db:
        locked = await db.scalar(select(func.pg_try_advisory_xact_lock(_BACKUP_LOCK_KEY)))
        if not locked:
            return JobResult("skipped", "Another backup is already running.")
        try:
            dump = await _pg_dump()
        except (OSError, RuntimeError) as exc:
            logger.error("Backup failed: %s", exc)
            return JobResult("failed", str(exc))

        blob = encrypt_bytes(dump, settings.BACKUP_PASSPHRASE)
        timestamp = datetime.now(UTC).strftime(_TIMESTAMP_FORMAT)
        path = _backup_dir() / f"release_radar_{timestamp}.dump.enc"
        temporary = path.with_name(f"{path.name}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(blob)
            temporary.replace(path)
            removed = prune_old_backups()
        except OSError as exc:
            with contextlib.suppress(OSError):
                temporary.unlink(missing_ok=True)
            logger.error("Backup could not be written: %s", exc)
            return JobResult("failed", f"Could not write to the backup folder: {exc}")

    logger.info("Backup written: %s (%d bytes)", path.name, len(blob))
    return JobResult(
        detail=f"{path.name}, {len(blob)} bytes. Removed {removed} past the retention period."
    )
