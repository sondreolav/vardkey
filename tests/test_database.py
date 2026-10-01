"""Tests for SQLite schema, storage, and constraints."""

from contextlib import contextmanager
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import (
    SCHEMA_VERSION,
    get_health_check,
    initialize_database,
    list_health_checks,
    list_keys,
    save_health_check,
    seed_fixed_keys,
)
from validation import validate_health_check


PRODUCTS = ("SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet")


def sample_payload(keys):
    """Return a valid health check payload matching the given key profiles."""
    return {
        "checked_at": "2026-10-01",
        "next_check_due": "2027-10-01",
        "software_compatibility_status": "OK",
        "sparrow_version": "1.8.0",
        "nunchuk_version": "",
        "software_comments": "",
        "contact_info_verified": 1,
        "comments": "Annual review",
        "key_checks": [
            {
                "key_id": key["id"],
                "available": 1,
                "hardware_works": 1 if key["type"] == "hardware" else None,
                "firmware_version": "1.0.0" if key["type"] == "hardware" else "",
                "seed_backup_status": "OK" if key["type"] == "hardware" else None,
                "seed_backup_verified": 1 if key["type"] == "hardware" else None,
                "cloud_health_status": "OK" if key["type"] == "cloud" else None,
                "cloud_provider_operational": 1 if key["type"] == "cloud" else None,
                "address_verified": 1,
                "derivation_height": "m/48'/0'/0'/2'",
                "address_path_verified": 1,
                "address_path": "m/48'/0'/0'/2'/0/0",
                "comments": "",
            }
            for key in keys
        ],
        "tool_checks": [
            {
                "product": product,
                "bip327_status": "IKKJE_VURDERT",
                "slip39_status": "IKKJE_VURDERT",
                "version": "",
                "checked_at": "",
                "notes": "",
            }
            for product in PRODUCTS
        ],
        "ai_security_checks": [
            {"provider": product, "status": "TRYGG", "comments": ""}
            for product in PRODUCTS
        ],
    }


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

    def test_partial_schema_with_zero_version_is_repaired_idempotently(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE key_checks (
                    id INTEGER PRIMARY KEY,
                    address_verified INTEGER,
                    derivation_height TEXT,
                    seed_backup_verified INTEGER
                );
                CREATE TABLE health_checks (
                    id INTEGER PRIMARY KEY,
                    software_comments TEXT
                );
                INSERT INTO key_checks (address_verified, derivation_height) VALUES (1, '0');
                PRAGMA user_version = 0;
                """
            )

        initialize_database(self.database_path)
        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            row = connection.execute(
                "SELECT address_verified, derivation_height FROM key_checks"
            ).fetchone()
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(key_checks)")
            }

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(row, (1, "0"))
        self.assertIn("seed_backup_verified", columns)

    def test_legacy_database_migrates_without_losing_existing_values(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE keys (
                    id INTEGER PRIMARY KEY,
                    key_number INTEGER NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    device TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE health_checks (
                    id INTEGER PRIMARY KEY,
                    checked_at TEXT NOT NULL,
                    next_check_due TEXT NOT NULL,
                    software_compatibility_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
                    sparrow_version TEXT,
                    nunchuk_version TEXT,
                    contact_info_verified INTEGER,
                    comments TEXT
                );
                CREATE TABLE key_checks (
                    id INTEGER PRIMARY KEY,
                    health_check_id INTEGER NOT NULL,
                    key_id INTEGER NOT NULL,
                    available INTEGER,
                    hardware_works INTEGER,
                    firmware_version TEXT,
                    seed_backup_status TEXT,
                    cloud_health_status TEXT,
                    cloud_provider_operational INTEGER,
                    address_path_verified INTEGER,
                    address_path TEXT,
                    comments TEXT,
                    UNIQUE (health_check_id, key_id)
                );
                INSERT INTO health_checks (checked_at, next_check_due) VALUES ('2026-01-01', '2027-01-01');
                PRAGMA user_version = 1;
                """
            )

        initialize_database(self.database_path)
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            health_check_id = connection.execute("SELECT id FROM health_checks").fetchone()[0]
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(key_checks)")
            }

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(health_check_id, 1)
        self.assertTrue(
            {"address_verified", "derivation_height", "seed_backup_verified"} <= columns
        )

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

    def test_saved_health_checks_are_stored_and_never_overwritten(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)
        data = validate_health_check(sample_payload(keys), {key["id"] for key in keys})

        first_id = save_health_check(data, self.database_path)
        second_id = save_health_check(data, self.database_path)

        self.assertNotEqual(first_id, second_id)
        summaries = list_health_checks(self.database_path)
        self.assertEqual([entry["id"] for entry in summaries], [second_id, first_id])

        record = get_health_check(first_id, self.database_path)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["comments"], "Annual review")
        self.assertEqual(len(record["key_checks"]), 3)
        self.assertEqual(len(record["tool_checks"]), 4)
        self.assertEqual(len(record["ai_security_checks"]), 4)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(record["ai_security_checks"][0]["status"], "TRYGG")
        self.assertIsNone(get_health_check(9999, self.database_path))

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
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

        with self.assertRaises(RuntimeError):
            initialize_database(self.database_path)


if __name__ == "__main__":
    unittest.main()
