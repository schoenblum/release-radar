"""Operator commands, run inside the container.

Lockout recovery:
    docker compose exec app python -m app.cli reset-password someone@example.org

This prints a random temporary password to the operator's terminal, reactivates
the account, signs out its sessions and requires a new password at next sign-in.
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.services.security import generate_temporary_password, hash_password
from app.services.sessions import revoke_all_sessions


async def reset_password(email: str) -> int:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            print("No account has that email address.", file=sys.stderr)
            return 1
        temporary = generate_temporary_password()
        user.password_hash = hash_password(temporary)
        user.force_password_change = True
        user.is_active = True
        await revoke_all_sessions(db, user)
        await db.commit()
    print(f"Temporary password: {temporary}")
    print("A new password is required at next sign-in.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    reset = commands.add_parser("reset-password", help="Set a temporary password for an account")
    reset.add_argument("email")
    arguments = parser.parse_args()
    return asyncio.run(reset_password(arguments.email))


if __name__ == "__main__":
    sys.exit(main())
