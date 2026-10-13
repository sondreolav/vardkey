"""Maintenance entry point for VardKey.

This module runs the maintenance tasks that do not need the HTTP server to be
up. It is the entry point the StartOS actions call inside a temporary
subcontainer, and it can be run by hand:

    python3 maintenance.py delete-history
    python3 maintenance.py set-admin-password

The database path comes from the ``DATABASE_PATH`` environment variable and
falls back to the application default, so the container's own environment is
enough. The schema is created or migrated first, exactly as the server does at
startup, so the commands are safe to run against a database that has never been
opened (section 31 points 1 and 2).
"""

import argparse
import json
import os
import secrets
import sqlite3
import sys

from auth import get_admin, normalize_admin_username, set_admin
from database import delete_history, initialize_database


DEFAULT_DATABASE_PATH = "data/vardkey.sqlite3"
# The username a fresh database gets when the action creates the account. The
# app's own create-admin step lets the user pick one; this is the fallback the
# StartOS action uses when nothing is stored yet.
DEFAULT_ADMIN_USERNAME = "admin"
# Unambiguous characters only, so the generated password can be read from a
# screen and typed back without confusion.
PASSWORD_ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PASSWORD_LENGTH = 24


def get_database_path():
    """Return the database path the maintenance command should use."""
    return os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)


def generate_password():
    """Return a strong random admin password, generated inside the container.

    The password never travels from the StartOS host into the container as an
    argument or on stdin, because the SDK does not document a way to feed stdin
    to a ``withTemp`` command and an argument is visible in the process list.
    Generating it here and printing it once is the packaging guide's own
    password-reset pattern (section 31 point 1).
    """
    return "".join(
        secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH)
    )


def delete_history_command(args):
    """Delete the stored history and report how many checks went with it.

    The key setup, the multisig settings, the admin credentials and the wallet
    software list are never touched (section 31 point 2).
    """
    initialize_database(args.database)
    deleted = delete_history(args.database)
    plural = "" if deleted == 1 else "s"
    print(f"Deleted {deleted} saved health check{plural}, with the follow-up they closed.")
    return 0


def set_admin_password_command(args):
    """Set a new admin password and print the credentials once.

    The stored admin username is kept when none is given, so a reset does not
    rename the account by accident. A username that does not fit is refused
    before anything is written. The credentials are printed as one JSON object,
    which the StartOS action reads back and shows (section 31 point 1).
    """
    initialize_database(args.database)
    username = (args.username or "").strip()
    if username:
        username = normalize_admin_username(username)
    else:
        username = get_admin(args.database)[0] or DEFAULT_ADMIN_USERNAME
    password = generate_password()
    set_admin(username, password, args.database)
    print(json.dumps({"username": username, "password": password}))
    return 0


def build_parser():
    """Return the argument parser for the maintenance commands.

    ``--database`` is shared by every command, so it can be given after the
    command name: ``maintenance.py delete-history --database /data/x.sqlite3``.
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--database",
        default=None,
        help=(
            "Path of the SQLite database. Defaults to DATABASE_PATH, or "
            f"{DEFAULT_DATABASE_PATH}."
        ),
    )

    parser = argparse.ArgumentParser(
        prog="maintenance.py",
        description="Maintenance tasks for VardKey that do not need the server.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    delete = commands.add_parser(
        "delete-history",
        parents=[common],
        help="Delete every saved health check and the follow-up it closed.",
    )
    delete.set_defaults(handler=delete_history_command)
    password = commands.add_parser(
        "set-admin-password",
        parents=[common],
        help="Set a new admin password and print the credentials once.",
    )
    password.add_argument(
        "--username",
        default=None,
        help=(
            "Admin username to store. Defaults to the stored one, or "
            f"{DEFAULT_ADMIN_USERNAME} when none is stored yet."
        ),
    )
    password.set_defaults(handler=set_admin_password_command)
    return parser


def main(argv=None):
    """Run one maintenance command and return its exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.database is None:
        args.database = get_database_path()
    try:
        return args.handler(args)
    except (ValueError, sqlite3.Error) as error:
        # The StartOS action shows the standard error as the alert, so a bad
        # value or an unreadable database becomes a message instead of a
        # traceback.
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
