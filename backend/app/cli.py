"""Admin commands.

    uv run python -m app.cli create-admin --email admin@example.com --name "Admin"

The password is prompted for (never pass it as an argument: it would end up
in shell history). For unattended installs, set ADMIN_PASSWORD instead.
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError

from app.database.session import session_scope
from app.models.user import Role
from app.schemas.user import UserCreate
from app.services.users import UserService


def create_admin(email: str, name: str) -> None:
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password (12+ chars): ")
    try:
        data = UserCreate(email=email, full_name=name, password=password, role=Role.ADMIN)
    except ValidationError as exc:
        sys.exit(f"Invalid input: {exc.errors()[0]['msg']}")
    with session_scope() as db:
        user = UserService(db).create_user(data)
        print(f"Created admin {user.email} ({user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an admin user")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin(args.email, args.name)


if __name__ == "__main__":
    main()
