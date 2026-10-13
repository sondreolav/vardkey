"""Tests for the dated CSV export filename (section 31 point 3).

The server names every download with its own date, and the dashboard link leaves
the name to the server, because a valued ``download`` attribute would override
the ``Content-Disposition`` filename.
"""

from datetime import datetime
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest

from app import AppHandler, export_filename
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
FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-vardkey-export\.csv$")


class ExportFilenameTests(unittest.TestCase):
    def test_the_filename_carries_the_server_date(self):
        # The name is built from the server's own date, so the same code path
        # answers every download (section 31 point 3).
        self.assertEqual(
            export_filename(datetime(2026, 10, 13, 12, 0, 0)),
            "2026-10-13-vardkey-export.csv",
        )
        self.assertRegex(export_filename(), FILENAME_PATTERN)

    def test_the_dashboard_link_does_not_override_the_filename(self):
        # A ``download`` attribute with a value would override the
        # ``Content-Disposition`` filename, so the dashboard link must not carry
        # one (section 31 point 3).
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('href="/api/export"', html)
        self.assertNotIn('download="', html)


class ExportFilenameApiTests(SessionMixin, unittest.TestCase):
    """The Content-Disposition the export endpoint sends."""

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

    def test_the_export_answers_with_a_dated_filename(self):
        with self.get("/api/export") as response:
            self.assertEqual(response.status, 200)
            disposition = response.headers["Content-Disposition"]
            response.read()

        # The date in the header is the server's own, taken when the download is
        # answered (section 31 point 3).
        today = datetime.now().date().isoformat()
        self.assertEqual(
            disposition,
            f'attachment; filename="{today}-vardkey-export.csv"',
        )


if __name__ == "__main__":
    unittest.main()
