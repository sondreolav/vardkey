"""HTTP tests for the dashboard server."""

from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import AppHandler
from database import initialize_database, seed_fixed_keys


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

    def post_json(self, path, payload):
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request)

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

    def test_health_check_form_is_served_in_english(self):
        with urlopen(f"{self.base_url}/health-check") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="health-check-form"', body)
        self.assertIn("Never enter seed phrases", body)
        self.assertIn("Save health check", body)

    def test_history_page_is_served_in_english(self):
        with urlopen(f"{self.base_url}/history") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="history-list"', body)
        self.assertIn("Saved health checks", body)

    def test_dashboard_links_to_health_check_form(self):
        with urlopen(self.base_url) as response:
            body = response.read().decode("utf-8")

        self.assertIn('href="/health-check"', body)
        self.assertIn('href="/history"', body)

    def test_saved_health_check_can_be_read_back(self):
        with urlopen(f"{self.base_url}/api/keys") as response:
            keys = json.load(response)

        with self.post_json("/api/health-checks", sample_payload(keys)) as response:
            self.assertEqual(response.status, 201)
            saved = json.load(response)

        with urlopen(f"{self.base_url}/api/health-checks") as response:
            summaries = json.load(response)
        self.assertTrue(any(entry["id"] == saved["id"] for entry in summaries))

        with urlopen(f"{self.base_url}/api/health-checks/{saved['id']}") as response:
            record = json.load(response)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(len(record["key_checks"]), 3)
        self.assertEqual(len(record["tool_checks"]), 4)
        self.assertEqual(len(record["ai_security_checks"]), 4)

    def test_invalid_health_check_is_rejected(self):
        payload = sample_payload([{"id": 1, "type": "hardware"}])
        payload["checked_at"] = "not-a-date"

        try:
            with self.post_json("/api/health-checks", payload) as response:
                self.fail(f"Expected 400, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, 400)
                error.read()
            finally:
                error.close()

    def test_unknown_health_check_returns_not_found(self):
        try:
            with urlopen(f"{self.base_url}/api/health-checks/999999") as response:
                self.fail(f"Expected 404, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, 404)
                error.read()
            finally:
                error.close()

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
