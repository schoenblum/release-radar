#!/usr/bin/env python3
"""Create .env from .env.example with fresh random secrets.

Uses only the standard library, so it runs on any host with Python 3.
It never overwrites an existing file and never prints a secret value.
"""

import argparse
import base64
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "change-me"

GENERATORS = {
    "POSTGRES_PASSWORD": lambda: secrets.token_hex(24),
    "SECRET_KEY": lambda: secrets.token_urlsafe(48),
    "FERNET_KEY": lambda: base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"),
    "BACKUP_PASSPHRASE": lambda: secrets.token_urlsafe(32),
    "BOOTSTRAP_ADMIN_PASSWORD": lambda: secrets.token_urlsafe(18),
}


def render(template: str) -> tuple[str, list[str]]:
    """Fill each placeholder. Returns the new text and the names that were set."""
    filled: list[str] = []

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in GENERATORS:
            raise SystemExit(f"No generator for {name}; add one to scripts/generate_env.py")
        filled.append(name)
        return f"{name}={GENERATORS[name]()}"

    text = re.sub(rf"^(\w+)={re.escape(PLACEHOLDER)}$", replace, template, flags=re.MULTILINE)
    return text, filled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".env")
    arguments = parser.parse_args()

    if arguments.output.exists():
        print(f"{arguments.output} already exists; leaving it unchanged.", file=sys.stderr)
        return 1

    text, filled = render((ROOT / ".env.example").read_text(encoding="utf-8"))
    # Create the file with owner-only access before any secret is written to it.
    descriptor = os.open(arguments.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)

    print(f"Wrote {arguments.output} with new values for: {', '.join(filled)}")
    print("Record them in the vault (HANDOVER section 4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
