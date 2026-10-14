import getpass
import json
import sys
from pathlib import Path

from teacher_auth import create_password_hash

ACCOUNTS_FILE = Path(__file__).with_name("teacher_accounts.json")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python src/manage_teachers.py <username>")

    username = sys.argv[1].strip()
    if not username:
        raise SystemExit("Username must not be empty")

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        raise SystemExit("Password must not be empty")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    with ACCOUNTS_FILE.open(encoding="utf-8") as accounts_file:
        accounts = json.load(accounts_file)
    if not isinstance(accounts, list):
        raise ValueError("Teacher accounts file must contain a JSON list")
    if any(account.get("username") == username for account in accounts):
        raise SystemExit(f"Teacher account already exists: {username}")

    salt, password_hash = create_password_hash(password)
    accounts.append(
        {"username": username, "salt": salt, "password_hash": password_hash}
    )
    ACCOUNTS_FILE.write_text(
        json.dumps(accounts, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Added teacher account {username}. Commit the updated teacher_accounts.json.")


if __name__ == "__main__":
    main()
