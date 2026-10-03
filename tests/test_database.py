"""Tests for SQLite schema, migration, storage, and constraints."""

from contextlib import contextmanager
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import (
    SCHEMA_VERSION,
    get_health_check,
    initialize_database,
    list_export_rows,
    list_health_checks,
    list_key_status,
    list_keys,
    list_previous_values,
    save_health_check,
    seed_fixed_keys,
)
from validation import validate_health_check


KEY_PRODUCTS = {1: "SeedSigner", 2: "Blockstream Jade", 3: "Nunchuk"}


def sample_payload(key, wallet_software=None):
    """Return a valid single-key payload for the given key profile."""
    number = key["key_number"]
    if wallet_software is None:
        wallet_software = "Nunchuk" if number == 3 else "Sparrow Wallet"
    products = list(dict.fromkeys((KEY_PRODUCTS[number], wallet_software)))
    providers = ["Nunchuk"] if number == 3 else [KEY_PRODUCTS[number], "Sparrow Wallet", "Nunchuk"]
    entry = {
        "key_id": key["id"],
        "available": 1,
        "address_path_verified": "OK",
        "address_path": "m/48'/0'/0'/2'/0/0",
        "comments": "",
    }
    if key["type"] == "hardware":
        entry.update({
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "OK",
        })
    else:
        entry.update({"cloud_health_status": "OK", "cloud_provider_operational": 1})
    return {
        "checked_at": "2026-10-01",
        "wallet_software": wallet_software,
        "software_version": "1.8.0",
        "software_compatibility_status": "OK",
        "software_comments": "",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": entry,
        "tool_checks": [
            {"product": product, "bip327_status": "NOT_ASSESSED", "slip39_status": "NOT_ASSESSED"}
            for product in products
        ],
        "ai_security_checks": [
            {"provider": provider, "status": "SECURE", "comments": ""} for provider in providers
        ],
    }


LEGACY_SCHEMA = """
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
        software_comments TEXT,
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
        address_verified INTEGER,
        seed_backup_verified INTEGER,
        address_path_verified INTEGER,
        derivation_height TEXT,
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE tool_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL,
        product TEXT NOT NULL,
        bip327_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
        slip39_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
        version TEXT,
        checked_at TEXT,
        notes TEXT,
        UNIQUE (health_check_id, product)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('TRYGG', 'PATCHA', 'SÅRBAR', 'KOMPROMITTERT')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type, device) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'SeedSigner'),
        (2, 2, 'Blockstream Jade', 'hardware', 'Blockstream Jade'),
        (3, 3, 'Nunchuk', 'cloud', 'Nunchuk');
    INSERT INTO health_checks (id, checked_at, next_check_due, sparrow_version)
        VALUES (1, '2026-01-01', '2027-01-01', '1.7.0');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_status, seed_backup_verified, address_verified,
        address_path_verified, derivation_height, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 1, 1, 1, 'm/48''/0''/0''/2''', 'm/48''/0''/0''/2''/0/0');
    INSERT INTO key_checks (
        health_check_id, key_id, available, seed_backup_status,
        seed_backup_verified, address_verified, address_path_verified
    ) VALUES (1, 2, 1, 'PROBLEM', 0, 0, 0);
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'TRYGG'),
        (1, 'Nunchuk', 'SÅRBAR');
    PRAGMA user_version = 4;
"""

# The layout introduced by section 19, before the status values became English
# and before the contact flag became a stored status.
SCHEMA_VERSION_5 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        device TEXT NOT NULL CHECK (device IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT CHECK (wallet_software IN ('Sparrow Wallet', 'Nunchuk')),
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified INTEGER CHECK (contact_info_verified IN (0, 1)),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        cloud_health_status TEXT CHECK (cloud_health_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        cloud_provider_operational INTEGER CHECK (cloud_provider_operational IN (0, 1)),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE tool_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        product TEXT NOT NULL CHECK (product IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        bip327_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (bip327_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        slip39_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (slip39_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        version TEXT,
        checked_at TEXT,
        notes TEXT,
        UNIQUE (health_check_id, product)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK (provider IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type, device) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'SeedSigner'),
        (2, 2, 'Blockstream Jade', 'hardware', 'Blockstream Jade'),
        (3, 3, 'Nunchuk', 'cloud', 'Nunchuk');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'IKKJE_VURDERT', 1, 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, cloud_health_status, cloud_provider_operational
    ) VALUES (1, 3, 1, 'IKKJE_VURDERT', 1);
    INSERT INTO tool_checks (health_check_id, product, bip327_status, slip39_status) VALUES
        (1, 'SeedSigner', 'OK', 'PROBLEM'),
        (1, 'Sparrow Wallet', 'IKKJE_VURDERT', 'OK');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'Nunchuk', 'SECURE');
    PRAGMA user_version = 5;
"""


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

    def write_schema(self, script):
        """Create a database from an explicit older schema script."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(script)

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

    def test_partial_schema_is_repaired_idempotently(self):
        self.write_schema(
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
            columns = {row[1] for row in connection.execute("PRAGMA table_info(key_checks)")}

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertTrue({"available", "seed_backup_verified", "address_path_verified"} <= columns)
        self.assertFalse({"address_verified", "derivation_height"} & columns)

    def test_legacy_database_migrates_to_per_key_checks(self):
        self.write_schema(LEGACY_SCHEMA)

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {row[1] for row in connection.execute("PRAGMA table_info(key_checks)")}
            rows = connection.execute(
                "SELECT key_id, seed_backup_verified, address_path_verified "
                "FROM key_checks ORDER BY key_id"
            ).fetchall()
            statuses = connection.execute(
                "SELECT provider, status FROM ai_security_checks ORDER BY provider"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertFalse({"seed_backup_status", "address_verified", "derivation_height"} & columns)
        self.assertEqual(rows, [(1, "OK", "OK"), (2, "PROBLEM", "PROBLEM")])
        self.assertEqual(statuses, [("Nunchuk", "VULNERABLE"), ("SeedSigner", "SECURE")])

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["checked_at"], "2026-01-01")
        self.assertEqual(record["sparrow_version"], "1.7.0")
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertIsNone(record["contact_info_verified"])
        self.assertEqual(record["key_checks"][0]["seed_backup_verified"], "OK")
        self.assertEqual(record["key_checks"][0]["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(record["key_checks"][1]["seed_backup_verified"], "PROBLEM")
        self.assertEqual([entry["status"] for entry in record["ai_security_checks"]], ["SECURE", "VULNERABLE"])

        keys = list_keys(self.database_path)
        new_id = save_health_check(validate_health_check(sample_payload(keys[2]), keys), self.database_path)
        new_record = get_health_check(new_id, self.database_path)
        self.assertEqual(new_record["wallet_software"], "Nunchuk")
        self.assertEqual(len(new_record["key_checks"]), 1)
        self.assertEqual(new_record["key_checks"][0]["key_number"], 3)
        self.assertEqual([entry["product"] for entry in new_record["tool_checks"]], ["Nunchuk"])
        self.assertEqual([entry["provider"] for entry in new_record["ai_security_checks"]], ["Nunchuk"])

    def test_status_values_migrate_to_english(self):
        self.write_schema(SCHEMA_VERSION_5)

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            compatibility = connection.execute(
                "SELECT software_compatibility_status FROM health_checks"
            ).fetchone()[0]
            cloud = connection.execute("SELECT cloud_health_status FROM key_checks").fetchone()[0]
            standards = connection.execute(
                "SELECT product, bip327_status, slip39_status FROM tool_checks ORDER BY id"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(compatibility, "NOT_ASSESSED")
        self.assertEqual(cloud, "NOT_ASSESSED")
        self.assertEqual(
            standards,
            [("SeedSigner", "YES", "NO"), ("Sparrow Wallet", "NOT_ASSESSED", "YES")],
        )

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["comments"], "Annual review")
        self.assertEqual(record["tool_checks"][0]["bip327_status"], "YES")
        self.assertEqual(record["tool_checks"][0]["slip39_status"], "NO")
        self.assertEqual(record["ai_security_checks"][0]["status"], "SECURE")

    def test_the_contact_flag_migrates_to_the_stored_statuses(self):
        self.write_schema(SCHEMA_VERSION_5)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (id, checked_at, next_check_due, contact_info_verified) "
                "VALUES (2, '2025-01-01', '2026-01-01', 0), (3, '2024-01-01', '2025-01-01', NULL)"
            )

        initialize_database(self.database_path)

        with self.connect() as connection:
            stored = connection.execute(
                "SELECT id, contact_info_verified FROM health_checks ORDER BY id"
            ).fetchall()

        # 1 meant "confirmed", 0 meant "not confirmed", and an empty value stays
        # empty (section 23.1).
        self.assertEqual(
            stored,
            [(1, "Confirmed current"), (2, "Needs external update"), (3, None)],
        )

    def test_the_migrated_schema_rejects_the_old_status_values(self):
        self.write_schema(SCHEMA_VERSION_5)
        initialize_database(self.database_path)

        with self.connect() as connection:
            for statement, parameters in (
                (
                    "INSERT INTO health_checks (checked_at, next_check_due, software_compatibility_status) "
                    "VALUES ('2026-01-01', '2027-01-01', ?)",
                    ("IKKJE_VURDERT",),
                ),
                (
                    "INSERT INTO health_checks (checked_at, next_check_due, contact_info_verified) "
                    "VALUES ('2026-01-01', '2027-01-01', ?)",
                    (1,),
                ),
                (
                    "INSERT INTO tool_checks (health_check_id, product, bip327_status, slip39_status) "
                    "VALUES (1, 'Nunchuk', ?, 'YES')",
                    ("OK",),
                ),
            ):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(statement, parameters)

    def test_the_rebuilt_parent_table_keeps_its_foreign_keys(self):
        self.write_schema(SCHEMA_VERSION_5)
        initialize_database(self.database_path)

        with self.connect() as connection:
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO key_checks (health_check_id, key_id) VALUES (999, 1)"
                )
            children = connection.execute(
                "SELECT COUNT(*) FROM key_checks WHERE health_check_id = 1"
            ).fetchone()[0]

        self.assertEqual(violations, [])
        self.assertEqual(children, 1)

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
        data = validate_health_check(sample_payload(keys[0]), keys)

        first_id = save_health_check(data, self.database_path)
        second_id = save_health_check(data, self.database_path)

        self.assertNotEqual(first_id, second_id)
        summaries = list_health_checks(self.database_path)
        self.assertEqual([entry["id"] for entry in summaries], [second_id, first_id])
        self.assertEqual(summaries[0]["key_numbers"], [1])

        record = get_health_check(first_id, self.database_path)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertEqual(record["comments"], "Annual review")
        self.assertEqual(record["contact_info_verified"], "Confirmed current")
        self.assertEqual(len(record["key_checks"]), 1)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(record["key_checks"][0]["seed_backup_verified"], "OK")
        self.assertEqual(
            [entry["product"] for entry in record["tool_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )
        self.assertEqual(record["ai_security_checks"][0]["status"], "SECURE")
        self.assertIsNone(get_health_check(9999, self.database_path))

    def test_each_key_can_be_recorded_separately(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)

        for key in keys:
            data = validate_health_check(sample_payload(key), keys)
            saved_id = save_health_check(data, self.database_path)
            record = get_health_check(saved_id, self.database_path)
            self.assertEqual(record["key_checks"][0]["key_number"], key["key_number"])

        summaries = list_health_checks(self.database_path)
        self.assertEqual([entry["key_numbers"] for entry in summaries], [[3], [2], [1]])

    def test_key_status_has_no_dates_before_anything_is_saved(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)

        status = list_key_status(self.database_path)

        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual([entry["name"] for entry in status], ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        self.assertEqual([entry["type"] for entry in status], ["hardware", "hardware", "cloud"])
        self.assertEqual([entry["last_checked_at"] for entry in status], [None, None, None])
        self.assertEqual([entry["next_check_due"] for entry in status], [None, None, None])

    def test_key_status_reports_the_newest_check_per_key(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)

        older = sample_payload(keys[0])
        older["checked_at"] = "2025-10-01"
        save_health_check(validate_health_check(older, keys), self.database_path)

        newer = sample_payload(keys[0])
        newer["checked_at"] = "2026-10-01"
        save_health_check(validate_health_check(newer, keys), self.database_path)

        cloud = sample_payload(keys[2])
        cloud["checked_at"] = "2026-05-01"
        save_health_check(validate_health_check(cloud, keys), self.database_path)

        status = {entry["key_number"]: entry for entry in list_key_status(self.database_path)}

        self.assertEqual(status[1]["last_checked_at"], "2026-10-01")
        self.assertEqual(status[1]["next_check_due"], "2027-10-01")
        self.assertEqual(status[3]["last_checked_at"], "2026-05-01")
        self.assertEqual(status[3]["next_check_due"], "2027-05-01")
        self.assertIsNone(status[2]["last_checked_at"])
        self.assertIsNone(status[2]["next_check_due"])

    def test_previous_values_are_empty_before_anything_is_saved(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)

        values = list_previous_values(self.database_path)

        self.assertEqual([entry["key_id"] for entry in values["keys"]], [1, 2, 3])
        self.assertEqual([entry["firmware_version"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["address_path"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["wallet_software"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["software_version"] for entry in values["keys"]], [None, None, None])
        self.assertEqual(values["security"], {})

    def test_previous_values_return_the_newest_saved_values(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)

        older = sample_payload(keys[0])
        older["checked_at"] = "2025-10-01"
        older["software_version"] = "1.7.0"
        older["key_check"]["firmware_version"] = "0.9.0"
        save_health_check(validate_health_check(older, keys), self.database_path)

        newer = sample_payload(keys[0])
        newer["checked_at"] = "2026-10-01"
        newer["software_version"] = "1.8.0"
        newer["key_check"]["firmware_version"] = "1.0.0"
        save_health_check(validate_health_check(newer, keys), self.database_path)

        cloud = sample_payload(keys[2])
        cloud["checked_at"] = "2026-05-01"
        cloud["software_version"] = "1.9.0"
        save_health_check(validate_health_check(cloud, keys), self.database_path)

        values = list_previous_values(self.database_path)
        by_key = {entry["key_id"]: entry for entry in values["keys"]}

        self.assertEqual(by_key[1]["firmware_version"], "1.0.0")
        self.assertEqual(by_key[1]["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(by_key[1]["wallet_software"], "Sparrow Wallet")
        self.assertEqual(by_key[1]["software_version"], "1.8.0")
        self.assertEqual(by_key[3]["wallet_software"], "Nunchuk")
        self.assertEqual(by_key[3]["software_version"], "1.9.0")
        self.assertIsNone(by_key[2]["firmware_version"])
        self.assertEqual(
            values["security"],
            {"SeedSigner": "SECURE", "Sparrow Wallet": "SECURE", "Nunchuk": "SECURE"},
        )

    def test_previous_security_status_keeps_the_newest_status_per_provider(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)

        older = sample_payload(keys[0])
        older["checked_at"] = "2025-10-01"
        older["ai_security_checks"] = [
            {"provider": "SeedSigner", "status": "VULNERABLE", "comments": ""},
            {"provider": "Sparrow Wallet", "status": "PATCHED", "comments": ""},
            {"provider": "Nunchuk", "status": "SECURE", "comments": ""},
        ]
        save_health_check(validate_health_check(older, keys), self.database_path)

        newer = sample_payload(keys[0])
        newer["checked_at"] = "2026-10-01"
        save_health_check(validate_health_check(newer, keys), self.database_path)

        values = list_previous_values(self.database_path)

        self.assertEqual(values["security"]["SeedSigner"], "SECURE")
        self.assertEqual(values["security"]["Sparrow Wallet"], "SECURE")
        self.assertEqual(values["security"]["Nunchuk"], "SECURE")

    def test_export_rows_are_empty_before_anything_is_saved(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)

        self.assertEqual(list_export_rows(self.database_path), [])

    def test_export_rows_join_products_and_security_statuses(self):
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
        keys = list_keys(self.database_path)

        saved_id = save_health_check(
            validate_health_check(sample_payload(keys[0]), keys), self.database_path
        )
        save_health_check(
            validate_health_check(sample_payload(keys[2]), keys), self.database_path
        )

        rows = list_export_rows(self.database_path)

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["check_id"], saved_id)
        self.assertEqual(first["checked_at"], "2026-10-01")
        self.assertEqual(first["next_check_due"], "2027-10-01")
        self.assertEqual(first["key_number"], 1)
        self.assertEqual(first["key_name"], "SeedSigner")
        self.assertEqual(first["key_type"], "hardware")
        self.assertEqual(first["seed_backup_verified"], "OK")
        self.assertEqual(first["address_path_verified"], "OK")
        self.assertEqual(first["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(first["wallet_software"], "Sparrow Wallet")
        self.assertEqual(first["contact_info_verified"], "Confirmed current")
        self.assertEqual(
            first["bip327_status"],
            "SeedSigner: NOT_ASSESSED; Sparrow Wallet: NOT_ASSESSED",
        )
        self.assertEqual(
            first["slip39_status"],
            "SeedSigner: NOT_ASSESSED; Sparrow Wallet: NOT_ASSESSED",
        )
        self.assertEqual(
            first["security_status"],
            "SeedSigner: SECURE; Sparrow Wallet: SECURE; Nunchuk: SECURE",
        )

        cloud = rows[1]
        self.assertEqual(cloud["key_number"], 3)
        self.assertEqual(cloud["key_name"], "Nunchuk")
        self.assertEqual(cloud["wallet_software"], "Nunchuk")
        self.assertEqual(cloud["bip327_status"], "Nunchuk: NOT_ASSESSED")
        self.assertEqual(cloud["security_status"], "Nunchuk: SECURE")

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

    def test_ai_security_status_is_limited_to_the_english_values(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (checked_at, next_check_due) VALUES (?, ?)",
                ("2026-01-01", "2027-01-01"),
            )
            health_check_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                (health_check_id, "SeedSigner", "SECURE"),
            )
            for value in ("TRYGG", "UNKNOWN"):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                        (health_check_id, "Nunchuk", value),
                    )

    def test_unknown_future_schema_version_is_rejected(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

        with self.assertRaises(RuntimeError):
            initialize_database(self.database_path)


if __name__ == "__main__":
    unittest.main()
