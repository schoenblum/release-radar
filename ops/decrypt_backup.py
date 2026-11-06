#!/usr/bin/env python3
"""Decrypt a Release Radar backup (*.dump.enc to *.dump). See ops/README.md.

Usage:
    python3 ops/decrypt_backup.py release_radar_YYYYMMDDTHHMMSSZ.dump.enc

It asks for the passphrase, or reads it from BACKUP_PASSPHRASE if that is set.
Its only dependency is the `cryptography` package, which the app image includes.
"""

import getpass
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"RRBK1\n"


def decrypt(blob: bytes, passphrase: str) -> bytes:
    if blob[: len(MAGIC)] != MAGIC:
        raise ValueError("not a Release Radar backup file (bad magic header)")
    body = blob[len(MAGIC) :]
    salt, nonce, ciphertext = body[:16], body[16:28], body[28:]
    key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase.encode("utf-8"))
    return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    source = Path(sys.argv[1])
    if not source.is_file():
        print(f"error: {source} not found", file=sys.stderr)
        return 1
    passphrase = os.environ.get("BACKUP_PASSPHRASE") or getpass.getpass("Backup passphrase: ")
    try:
        plaintext = decrypt(source.read_bytes(), passphrase)
    except Exception as exc:  # noqa: BLE001 - every failure gets the same plain message
        print(
            f"error: could not decrypt ({type(exc).__name__}). Wrong passphrase or damaged file.",
            file=sys.stderr,
        )
        return 1
    target = source.with_suffix("") if source.suffix == ".enc" else source.with_suffix(".dump")
    target.write_bytes(plaintext)
    print(f"Wrote {target} ({len(plaintext)} bytes). Restore it with pg_restore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
