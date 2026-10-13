"""HTTP tests for the configurable multisig setup (section 31 point 7).

A new database starts at the 2-of-3 default. ``POST /api/setup`` also takes a
``threshold`` and a ``key_count``, and the stored shape is read back from
``GET /api/setup`` and drives how many key slots the app uses.
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
from database import initialize_database


ADDRESS_PATHS = {
    1: "m/48'/0'/0'/2'",
    2: "m/48'/1'/0'/2'",
    3: "m/48'/2'/0'/2'",
    4: "m/48'/3'/0'/2'",
    5: "m/48'/4'/0'/2'",
}
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATHS[1]},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": ADDRESS_PATHS[2]},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": ADDRESS_PATHS[3]},
]
# A 3-of-5 setup, which the app was never hard-wired for (section 31 point 7).
FIVE_KEY_SETUP = [
    {"key_number": number, "name": f"Key {number}", "type": "hardware", "address_path": ADDRESS_PATHS[number]}
    for number in range(1, 6)
]


class MultisigSetupApiTests(unittest.TestCase):
    """The setup endpoint on a new database, before anything is stored."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
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

    def get_setup(self):
        with urlopen(f"{self.base_url}/api/setup") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_keys(self):
        with urlopen(f"{self.base_url}/api/keys") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_key_status(self):
        with urlopen(f"{self.base_url}/api/key-status") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def post_setup(self, payload):
        request = Request(
            f"{self.base_url}/api/setup",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request)

    def assert_setup_rejected(self, payload, status=400):
        try:
            with self.post_setup(payload) as response:
                self.fail(f"Expected {status}, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, status)
                error.read()
            finally:
                error.close()

    def test_an_unconfigured_database_reports_the_2_of_3_default(self):
        setup = self.get_setup()

        self.assertFalse(setup["configured"])
        self.assertEqual(setup["keys"], [])
        # The default shape is the one the app was built for, so a client that
        # sends only the keys keeps working (section 31 point 7).
        self.assertEqual(setup["threshold"], 2)
        self.assertEqual(setup["key_count"], 3)

    def test_a_setup_without_the_numbers_still_defaults_to_2_of_3(self):
        with self.post_setup({"keys": DEFAULT_SETUP}) as response:
            self.assertEqual(response.status, 201)

        setup = self.get_setup()
        self.assertTrue(setup["configured"])
        self.assertEqual(setup["threshold"], 2)
        self.assertEqual(setup["key_count"], 3)
        self.assertEqual([key["key_number"] for key in setup["keys"]], [1, 2, 3])

    def test_a_three_of_five_setup_is_stored_and_read_back(self):
        with self.post_setup({
            "threshold": 3,
            "key_count": 5,
            "keys": FIVE_KEY_SETUP,
        }) as response:
            self.assertEqual(response.status, 201)

        setup = self.get_setup()
        self.assertTrue(setup["configured"])
        self.assertEqual(setup["threshold"], 3)
        self.assertEqual(setup["key_count"], 5)
        self.assertEqual([key["key_number"] for key in setup["keys"]], [1, 2, 3, 4, 5])
        self.assertEqual([key["name"] for key in setup["keys"]],
                         ["Key 1", "Key 2", "Key 3", "Key 4", "Key 5"])

        # The key list and the key status carry the five keys, and the status
        # carries the address path the dashboard card shows (section 31.4).
        self.assertEqual([key["key_number"] for key in self.get_keys()], [1, 2, 3, 4, 5])
        status = self.get_key_status()
        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3, 4, 5])
        self.assertEqual(
            [entry["address_path"] for entry in status],
            [ADDRESS_PATHS[number] for number in range(1, 6)],
        )

    def test_a_key_count_that_does_not_match_the_keys_is_rejected(self):
        # The number of keys has to match the stated key count, so a five-key
        # setup sent as three keys is refused.
        self.assert_setup_rejected({
            "threshold": 2,
            "key_count": 3,
            "keys": FIVE_KEY_SETUP,
        })
        self.assert_setup_rejected({"threshold": 2, "key_count": 5, "keys": DEFAULT_SETUP})
        self.assertFalse(self.get_setup()["configured"])

    def test_a_key_number_above_the_key_count_is_rejected(self):
        # The loosened CHECK is enforced by the validator, so a key number above
        # the stated count is refused (section 31 point 7).
        payload = {
            "threshold": 2,
            "key_count": 3,
            "keys": [
                {"key_number": 1, "name": "Key 1", "type": "hardware", "address_path": ADDRESS_PATHS[1]},
                {"key_number": 2, "name": "Key 2", "type": "hardware", "address_path": ADDRESS_PATHS[2]},
                {"key_number": 4, "name": "Key 4", "type": "hardware", "address_path": ADDRESS_PATHS[3]},
            ],
        }

        self.assert_setup_rejected(payload)

    def test_the_bounds_of_the_key_count_and_the_threshold_are_enforced(self):
        # 2 <= key_count <= 15, and 1 <= threshold <= key_count (section 31.7).
        for key_count in (1, 16):
            self.assert_setup_rejected({
                "threshold": 1,
                "key_count": key_count,
                "keys": FIVE_KEY_SETUP,
            })
        self.assert_setup_rejected({
            "threshold": 6,
            "key_count": 5,
            "keys": FIVE_KEY_SETUP,
        })
        self.assert_setup_rejected({
            "threshold": 0,
            "key_count": 5,
            "keys": FIVE_KEY_SETUP,
        })

        self.assertFalse(self.get_setup()["configured"])

    def test_a_threshold_of_one_is_allowed(self):
        # A threshold of 1 is allowed, because the user chooses it and the app
        # puts no meaning into the number (section 31 point 7).
        with self.post_setup({
            "threshold": 1,
            "key_count": 2,
            "keys": FIVE_KEY_SETUP[:2],
        }) as response:
            self.assertEqual(response.status, 201)

        setup = self.get_setup()
        self.assertEqual(setup["threshold"], 1)
        self.assertEqual(setup["key_count"], 2)


if __name__ == "__main__":
    unittest.main()
