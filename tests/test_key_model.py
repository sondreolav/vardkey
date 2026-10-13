"""HTTP tests for the optional model or service label (section 31 point 5).

The model is documentation only: it is set in the setup and in the rotation
section of the settings, it is shown on the dashboard card, and it never opens
or closes an alert.
"""

from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import AppHandler
from database import initialize_database, save_key_setup


ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
ROTATION_PATH = "m/48'/10'/0'/2'"
# A setup that carries a model for two of the three keys, so the empty one is
# proven to stay empty (section 31 point 5).
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH, "model": "ColdCard Q"},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH, "model": None},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH, "model": "Casa"},
]
# A setup for a new database, with a model that needs trimming and one that is
# left empty (section 31 point 5).
FRESH_SETUP = {
    "threshold": 2,
    "key_count": 3,
    "keys": [
        {"key_number": 1, "name": "Key 1", "type": "hardware", "address_path": ADDRESS_PATH, "model": "  Ledger Nano S  "},
        {"key_number": 2, "name": "Key 2", "type": "hardware", "address_path": SECOND_ADDRESS_PATH, "model": ""},
        {"key_number": 3, "name": "Key 3", "type": "cloud", "address_path": THIRD_ADDRESS_PATH, "model": "Casa"},
    ],
}


class KeyModelApiTests(unittest.TestCase):
    """The model label across the key endpoints and the settings."""

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

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def get_json(self, path):
        with urlopen(f"{self.base_url}{path}") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def post_json(self, path, payload):
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request)

    def assert_rejected_at(self, path, payload, status=400):
        try:
            with self.post_json(path, payload) as response:
                self.fail(f"Expected {status}, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, status)
                error.read()
            finally:
                error.close()

    def test_the_stored_models_are_returned_by_the_key_endpoints(self):
        # The model is carried by the key list, the settings and the key status,
        # because the dashboard card reads the last one (section 31 point 5).
        keys = self.get_json("/api/keys")
        self.assertEqual([key["model"] for key in keys], ["ColdCard Q", None, "Casa"])

        settings = self.get_json("/api/settings")
        self.assertEqual([key["model"] for key in settings["keys"]], ["ColdCard Q", None, "Casa"])

        status = self.get_json("/api/key-status")
        self.assertEqual([entry["model"] for entry in status], ["ColdCard Q", None, "Casa"])

    def test_the_setup_endpoint_stores_the_model(self):
        # A new database has no setup yet, so the first-run step writes the model
        # with the rest of the key (section 31 point 5).
        fresh = os.path.join(self.temp_dir.name, "fresh.sqlite3")
        initialize_database(fresh)
        os.environ["DATABASE_PATH"] = fresh

        with self.post_json("/api/setup", FRESH_SETUP) as response:
            self.assertEqual(response.status, 201)

        keys = self.get_json("/api/keys")
        self.assertEqual([key["name"] for key in keys], ["Key 1", "Key 2", "Key 3"])
        # The model is trimmed, and the empty one is stored as "not recorded".
        self.assertEqual([key["model"] for key in keys], ["Ledger Nano S", None, "Casa"])

    def test_an_over_long_model_is_rejected_by_the_setup(self):
        fresh = os.path.join(self.temp_dir.name, "fresh.sqlite3")
        initialize_database(fresh)
        os.environ["DATABASE_PATH"] = fresh

        payload = json.loads(json.dumps(FRESH_SETUP))
        payload["keys"][0]["model"] = "x" * 61
        self.assert_rejected_at("/api/setup", payload)

        self.assertFalse(self.get_json("/api/setup")["configured"])

    def test_the_settings_change_the_model(self):
        with self.post_json("/api/settings/keys", {
            "key_id": 2,
            "name": "Blockstream Jade",
            "address_path": SECOND_ADDRESS_PATH,
            "model": "  ColdCard Mk4  ",
        }) as response:
            self.assertEqual(response.status, 200)
            body = json.load(response)

        self.assertEqual(body["keys"][1]["model"], "ColdCard Mk4")
        self.assertEqual(self.get_json("/api/keys")[1]["model"], "ColdCard Mk4")

    def test_the_settings_clear_the_model_with_an_empty_value(self):
        # An empty value means "not recorded", so the model can be removed again
        # (section 31 point 5).
        with self.post_json("/api/settings/keys", {
            "key_id": 1,
            "name": "SeedSigner",
            "address_path": ADDRESS_PATH,
            "model": "",
        }) as response:
            self.assertEqual(response.status, 200)

        self.assertIsNone(self.get_json("/api/keys")[0]["model"])

    def test_a_rename_that_does_not_mention_the_model_clears_it(self):
        # The settings always manage the model, so a payload without it writes an
        # empty value. The form always sends the field (section 31 point 5).
        with self.post_json("/api/settings/keys", {
            "key_id": 3,
            "name": "Nunchuk",
            "address_path": THIRD_ADDRESS_PATH,
        }) as response:
            self.assertEqual(response.status, 200)

        self.assertIsNone(self.get_json("/api/keys")[2]["model"])

    def test_an_over_long_or_non_text_model_is_rejected(self):
        for value in ("x" * 61, 12):
            self.assert_rejected_at("/api/settings/keys", {
                "key_id": 1,
                "name": "SeedSigner",
                "address_path": ADDRESS_PATH,
                "model": value,
            })

        # The refused writes left the stored model untouched.
        self.assertEqual(self.get_json("/api/keys")[0]["model"], "ColdCard Q")

    def test_the_rotation_writes_the_model_when_it_is_sent(self):
        with self.post_json("/api/keys/1/rotate", {
            "replaced": True,
            "keep_name": True,
            "address_path": ROTATION_PATH,
            "model": "Ledger Nano S",
        }) as response:
            self.assertEqual(response.status, 200)
            body = json.load(response)

        self.assertEqual(body["settings"]["keys"][0]["model"], "Ledger Nano S")
        self.assertEqual(self.get_json("/api/keys")[0]["model"], "Ledger Nano S")

    def test_the_rotation_keeps_the_stored_model_when_it_is_not_sent(self):
        # The model is only a label, so a rotation that says nothing about it
        # keeps the stored value (section 31 point 5).
        with self.post_json("/api/keys/1/rotate", {
            "replaced": True,
            "keep_name": True,
            "address_path": ROTATION_PATH,
        }) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual(self.get_json("/api/keys")[0]["model"], "ColdCard Q")


if __name__ == "__main__":
    unittest.main()
