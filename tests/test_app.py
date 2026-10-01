"""HTTP tests for the dashboard server."""

from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from app import AppHandler
from database import initialize_database, seed_fixed_keys


class AppHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = os.path.join(cls.temp_dir.name, "test.sqlite3")
        initialize_database(cls.database_path)
        seed_fixed_keys(cls.database_path)
        cls.previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = cls.database_path

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        if cls.previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = cls.previous_database_path
        cls.temp_dir.cleanup()

    def test_health_endpoint_returns_json(self):
        with urlopen(f"{self.base_url}/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok"})
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_key_api_returns_the_three_fixed_profiles(self):
        with urlopen(f"{self.base_url}/api/keys") as response:
            keys = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([key["device"] for key in keys], ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        self.assertEqual([key["key_number"] for key in keys], [1, 2, 3])

    def test_dashboard_loads_key_profiles_from_api(self):
        with urlopen(self.base_url) as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="key-list"', body)
        self.assertIn('<script src="/app.js" defer></script>', body)

    def test_unknown_path_returns_not_found(self):
        try:
            with urlopen(f"{self.base_url}/missing") as response:
                self.fail(f"Expected 404, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, 404)
                error.read()
            finally:
                error.close()


if __name__ == "__main__":
    unittest.main()
