"""Maintenance entry point for VardKey.

This module runs the maintenance tasks that do not need the HTTP server to be
up. It is the entry point the StartOS actions call inside a temporary
subcontainer, and it can be run by hand:

    python3 maintenance.py delete-history

The database path comes from the ``DATABASE_PATH`` environment variable and
falls back to the application default, so the container's own environment is
enough. The schema is created or migrated first, exactly as the server does at
startup, so the command is safe to run against a database that has never been
opened (section 31 point 2).
"""

import argparse
import os
import sys

from database import delete_history, initialize_database


DEFAULT_DATABASE_PATH = "data/vardkey.sqlite3"


def get_database_path():
    """Return the database path the maintenance command should use."""
    return os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)


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


def build_parser():
    """Return the argument parser for the maintenance commands."""
    parser = argparse.ArgumentParser(
        prog="maintenance.py",
        description="Maintenance tasks for VardKey that do not need the server.",
    )
    parser.add_argument(
        "--database",
        default=None,
        help=(
            "Path of the SQLite database. Defaults to DATABASE_PATH, or "
            f"{DEFAULT_DATABASE_PATH}."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    delete = commands.add_parser(
        "delete-history",
        help="Delete every saved health check and the follow-up it closed.",
    )
    delete.set_defaults(handler=delete_history_command)
    return parser


def main(argv=None):
    """Run one maintenance command and return its exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.database is None:
        args.database = get_database_path()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
