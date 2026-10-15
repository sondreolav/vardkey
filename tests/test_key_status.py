"""Tests for the address path on the key status and the key card.

The dashboard card shows the address path of each key, so ``GET /api/key-status``
has to carry it, and an empty path -- which a migrated key can have -- is left
out instead of rendering an empty line (section 31 point 4).
"""

from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
import threading
import unittest

from app import AppHandler
from database import initialize_database, save_key_setup
from server_session import SessionMixin


ROOT = Path(__file__).resolve().parents[1]
ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
]
# A setup as an older database leaves it: the address paths were added by the
# migration and are still empty (section 25.1).
MIGRATED_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ""},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": ""},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": ""},
]


def read_static(name):
    """Return the text of one static asset."""
    return (ROOT / "static" / name).read_text(encoding="utf-8")


class KeyStatusAddressPathTests(SessionMixin, unittest.TestCase):
    """The address path across the key status and the dashboard card."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        save_key_setup(DEFAULT_SETUP, self.database_path)
        self.previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.database_path

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        # Every route except /health needs a session (section 31 point 1).
        self.authenticate()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def test_the_key_status_carries_the_address_path(self):
        # The card reads the path from the key status, so the endpoint has to
        # give it, in key order (section 31 point 4).
        status = self.get_json("/api/key-status")

        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual(
            [entry["address_path"] for entry in status],
            [ADDRESS_PATH, SECOND_ADDRESS_PATH, THIRD_ADDRESS_PATH],
        )

    def test_an_empty_address_path_is_passed_through_as_it_stands(self):
        # A key the migration left without a path answers with an empty value,
        # which the card leaves out (sections 25.1 and 31.4).
        migrated = os.path.join(self.temp_dir.name, "migrated.sqlite3")
        initialize_database(migrated)
        save_key_setup(MIGRATED_SETUP, migrated)
        os.environ["DATABASE_PATH"] = migrated
        # The session secret lives in the database, so the sign-in is repeated
        # for the new file.
        self.authenticate()

        status = self.get_json("/api/key-status")

        self.assertEqual([entry["address_path"] for entry in status], ["", "", ""])

    def test_the_key_status_still_carries_the_dates_with_the_path(self):
        # The path is an addition, not a replacement: the dates stay in the same
        # answer (section 31 point 4).
        status = self.get_json("/api/key-status")

        self.assertEqual([entry["last_checked_at"] for entry in status], [None, None, None])
        self.assertEqual([entry["next_check_due"] for entry in status], [None, None, None])

    def test_the_dashboard_card_shows_the_path_under_the_name(self):
        # createKeyCard() renders the name, then the model, then the path, and an
        # empty path is skipped (sections 31.4 and 32.2 point 7). The type shares
        # the top line with the number now, so it has no line of its own
        # (section 32.2 point 6).
        script = read_static("app.js")

        self.assertIn("entry.address_path", script)
        name_index = script.index("card.append(top, name);")
        model_index = script.index("card.append(model);")
        path_index = script.index("card.append(path);")
        self.assertLess(name_index, model_index)
        self.assertLess(model_index, path_index)
        self.assertIn("if (entry.address_path) {", script)
        self.assertNotIn("card.append(type);", script)
        self.assertNotIn("Hardware key", script)


if __name__ == "__main__":
    unittest.main()
