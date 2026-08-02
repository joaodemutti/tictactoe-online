"""Reset a user's password from the command line.

Intended for out-of-band recovery (e.g. over SSH on the server) when a user
has locked themselves out. Run it inside the app container so it uses the same
DATABASE_URL and password hashing as the app:

    docker compose exec tictactoe-online python -m scripts.reset_password <username> [new_password]

If new_password is omitted you'll be prompted for it (input is hidden and not
echoed to the shell history).
"""

import asyncio
import getpass
import sys

from sqlalchemy import select

from app.auth import hash_password
from app.database import AsyncSessionLocal
from app.models import User


async def reset(username: str, new_password: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with username {username!r}", file=sys.stderr)
            return 1
        user.password_hash = hash_password(new_password)
        await db.commit()
        print(f"Password updated for {user.username} ({user.id}).")
        return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: python -m scripts.reset_password <username> [new_password]",
            file=sys.stderr,
        )
        return 2

    username = sys.argv[1]
    if len(sys.argv) >= 3:
        new_password = sys.argv[2]
    else:
        new_password = getpass.getpass("New password: ")
        if new_password != getpass.getpass("Confirm password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1

    if not new_password:
        print("Password must not be empty.", file=sys.stderr)
        return 1

    return asyncio.run(reset(username, new_password))


if __name__ == "__main__":
    raise SystemExit(main())
