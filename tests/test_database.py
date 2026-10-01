"""Tests for SQLite schema initialization and constraints."""

from contextlib import contextmanager
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import SCHEMA_VERSION, initialize_database, list_keys, seed_fixed_keys


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "nested" / "test.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def test_initialization_creates_versioned_schema_and_is_idempotent(self):
        initialize_database(self.database_path)
        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertTrue(
            {"keys", "health_checks", "key_checks", "tool_checks", "ai_security_checks"}
            <= tables
        )

    def test_v1_database_migrates_to_current_schema_without_losing_data(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE key_checks (
                    id INTEGER PRIMARY KEY,
                    address_path_verified INTEGER,
                    address_path TEXT
                );
                INSERT INTO key_checks (address_path_verified, address_path) VALUES (1, "m/48'/0'/0'/2'");
                PRAGMA user_version = 1;
                """
            )
        finally:
            connection.close()

        initialize_database(self.database_path)
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            row = connection.execute(
                "SELECT address_path_verified, address_path, address_verified, derivation_height FROM key_checks"
            ).fetchone()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(row, (1, "m/48'/0'/0'/2'", None, None))

    def test_seed_fixed_keys_is_idempotent_and_preserves_custom_names(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        seed_fixed_keys(self.database_path)

        keys = list_keys(self.database_path)
        self.assertEqual(len(keys), 3)
        self.assertEqual(
            [(key["key_number"], key["name"], key["type"], key["device"]) for key in keys],
            [
                (1, "SeedSigner", "hardware", "SeedSigner"),
                (2, "Blockstream Jade", "hardware", "Blockstream Jade"),
                (3, "Nunchuk", "cloud", "Nunchuk"),
            ],
        )

        with self.connect() as connection:
            connection.execute("UPDATE keys SET name = ? WHERE key_number = ?", ("My Jade", 2))
        seed_fixed_keys(self.database_path)
        self.assertEqual(list_keys(self.database_path)[1]["name"], "My Jade")

    def test_invalid_status_and_duplicate_key_numbers_are_rejected(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO health_checks (checked_at, next_check_due, software_compatibility_status) "
                    "VALUES ('2026-01-01', '2027-01-01', 'UNKNOWN')"
                )

            connection.execute(
                "INSERT INTO keys (key_number, name, type, device) VALUES (1, 'SeedSigner', 'hardware', 'SeedSigner')"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO keys (key_number, name, type, device) VALUES (1, 'Duplicate', 'hardware', 'SeedSigner')"
                )

    def test_ai_security_status_is_limited_to_required_values(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (checked_at, next_check_due) VALUES (?, ?)",
                ("2026-01-01", "2027-01-01"),
            )
            health_check_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                (health_check_id, "SeedSigner", "TRYGG"),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                    (health_check_id, "Nunchuk", "UNKNOWN"),
                )

    def test_unknown_future_schema_version_is_rejected(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            initialize_database(self.database_path)


if __name__ == "__main__":
    unittest.main()
