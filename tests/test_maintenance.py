"""Tests for deleting the stored history (section 31 point 2).

The history, the export and the alerts are emptied, while the key setup, the
multisig settings and the wallet software list stay. The acknowledgements have
no foreign key, so they are deleted explicitly.
"""

from contextlib import redirect_stdout
import io
import os
import tempfile
import unittest

import maintenance
from database import (
    DEFAULT_WALLET_SOFTWARE,
    delete_history,
    get_health_check,
    get_multisig_settings,
    initialize_database,
    list_alert_acknowledgements,
    list_export_rows,
    list_health_checks,
    list_keys,
    list_wallet_software,
    save_alert_acknowledgement,
    save_health_check,
    save_key_setup,
)
from validation import validate_health_check


ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
SOFTWARE_NAMES = (DEFAULT_WALLET_SOFTWARE,)
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
]


def sample_payload(key):
    """Return a valid single-key payload for the given key profile."""
    wallet_software = key["name"] if key["type"] == "cloud" else DEFAULT_WALLET_SOFTWARE
    labels = list(dict.fromkeys((key["name"], wallet_software)))
    entry = {
        "key_id": key["id"],
        "available": 1,
        "address_path": key["address_path"],
        "comments": "",
    }
    if key["type"] == "hardware":
        entry.update({
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "OK",
        })
    return {
        "checked_at": "2026-10-01",
        "wallet_software": wallet_software,
        "software_version": "1.8.0",
        "software_compatibility_status": "OK",
        "software_comments": "",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": entry,
        "ai_security_checks": [
            {"provider": label, "status": "SECURE", "comments": ""} for label in labels
        ],
    }


def unavailable_payload(key):
    """Return the payload the form sends for a key that was not available."""
    return {
        "checked_at": "2026-10-01",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 0,
            "comments": "Key is with the third holder",
        },
    }


class DeleteHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        save_key_setup(DEFAULT_SETUP, self.database_path)
        keys = list_keys(self.database_path)
        self.first = save_health_check(
            validate_health_check(sample_payload(keys[0]), keys, SOFTWARE_NAMES),
            self.database_path,
        )
        self.second = save_health_check(
            validate_health_check(unavailable_payload(keys[1]), keys, SOFTWARE_NAMES),
            self.database_path,
        )
        # An acknowledgement has no foreign key, so it does not cascade and has
        # to be deleted explicitly (section 31 point 2).
        save_alert_acknowledgement(
            "key_unavailable",
            "Key 2: Blockstream Jade",
            keys[1]["id"],
            self.second,
            "rotate",
            self.database_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deleting_the_history_empties_the_checks_the_export_and_the_alerts(self):
        deleted = delete_history(self.database_path)

        self.assertEqual(deleted, 2)
        self.assertEqual(list_health_checks(self.database_path), [])
        self.assertEqual(list_export_rows(self.database_path), [])
        self.assertEqual(list_alert_acknowledgements(self.database_path), [])
        # The child rows went with the checks, so neither check can be read back.
        self.assertIsNone(get_health_check(self.first, self.database_path))
        self.assertIsNone(get_health_check(self.second, self.database_path))

    def test_the_key_setup_and_the_software_list_survive(self):
        delete_history(self.database_path)

        keys = list_keys(self.database_path)
        self.assertEqual(
            [key["name"] for key in keys],
            ["SeedSigner", "Blockstream Jade", "Nunchuk"],
        )
        self.assertEqual(
            [key["address_path"] for key in keys],
            [ADDRESS_PATH, SECOND_ADDRESS_PATH, THIRD_ADDRESS_PATH],
        )
        self.assertEqual(list_wallet_software(self.database_path), [DEFAULT_WALLET_SOFTWARE])
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 2, "key_count": 3},
        )

    def test_deleting_an_empty_history_reports_zero(self):
        delete_history(self.database_path)

        self.assertEqual(delete_history(self.database_path), 0)


class MaintenanceCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        save_key_setup(DEFAULT_SETUP, self.database_path)
        keys = list_keys(self.database_path)
        save_health_check(
            validate_health_check(sample_payload(keys[0]), keys, SOFTWARE_NAMES),
            self.database_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_command(self, argv):
        """Run one maintenance command and return its exit code and output."""
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = maintenance.main(argv)
        return code, buffer.getvalue()

    def test_the_delete_history_command_reports_the_count(self):
        code, output = self.run_command(["delete-history", "--database", self.database_path])

        self.assertEqual(code, 0)
        self.assertEqual(
            output.strip(),
            "Deleted 1 saved health check, with the follow-up they closed.",
        )
        self.assertEqual(list_health_checks(self.database_path), [])

    def test_the_database_path_can_come_from_the_environment(self):
        previous = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.database_path
        try:
            code, output = self.run_command(["delete-history"])
        finally:
            if previous is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = previous

        self.assertEqual(code, 0)
        self.assertIn("Deleted 1 saved health check", output)

    def test_the_command_handles_a_database_that_was_never_opened(self):
        # The schema is created first, so the command is safe on a fresh path
        # (section 31 point 2).
        fresh = os.path.join(self.temp_dir.name, "fresh.sqlite3")

        code, output = self.run_command(["delete-history", "--database", fresh])

        self.assertEqual(code, 0)
        self.assertIn("Deleted 0 saved health checks", output)


if __name__ == "__main__":
    unittest.main()
