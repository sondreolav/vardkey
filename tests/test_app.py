"""HTTP tests for the dashboard server."""

from http.server import ThreadingHTTPServer
import csv
import io
import json
import os
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import AppHandler
from database import initialize_database, seed_fixed_keys
from export import HEADERS


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
        "contact_info_verified": 1,
        "comments": "Annual review",
        "key_check": entry,
        "tool_checks": [
            {"product": product, "bip327_status": "IKKJE_VURDERT", "slip39_status": "IKKJE_VURDERT"}
            for product in products
        ],
        "ai_security_checks": [
            {"provider": provider, "status": "SECURE", "comments": ""} for provider in providers
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

    def key_profiles(self):
        with urlopen(f"{self.base_url}/api/keys") as response:
            return json.load(response)

    def post_json(self, path, payload):
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request)

    def assert_rejected(self, payload):
        try:
            with self.post_json("/api/health-checks", payload) as response:
                self.fail(f"Expected 400, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, 400)
                error.read()
            finally:
                error.close()

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

    def test_key_status_api_lists_each_key_with_its_newest_check(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "2027-03-01"
        with self.post_json("/api/health-checks", payload) as response:
            self.assertEqual(response.status, 201)

        with urlopen(f"{self.base_url}/api/key-status") as response:
            status = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual([entry["type"] for entry in status], ["hardware", "hardware", "cloud"])
        self.assertEqual(status[0]["last_checked_at"], "2027-03-01")
        self.assertEqual(status[0]["next_check_due"], "2028-03-01")
        self.assertEqual(status[0]["name"], "SeedSigner")

    def test_export_api_returns_a_csv_download(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "2027-04-01"
        with self.post_json("/api/health-checks", payload) as response:
            self.assertEqual(response.status, 201)
            saved = json.load(response)

        with urlopen(f"{self.base_url}/api/export") as response:
            body = response.read().decode("utf-8")
            content_type = response.headers["Content-Type"]
            disposition = response.headers["Content-Disposition"]

        self.assertEqual(response.status, 200)
        self.assertEqual(content_type, "text/csv; charset=utf-8")
        self.assertIn("helsesjekk-export.csv", disposition)

        rows = list(csv.reader(io.StringIO(body)))
        self.assertEqual(rows[0], list(HEADERS))
        matching = [row for row in rows[1:] if row[0] == str(saved["id"])]
        self.assertEqual(len(matching), 1)

        values = dict(zip(HEADERS, matching[0]))
        self.assertEqual(values["Check date"], "2027-04-01")
        self.assertEqual(values["Next check due"], "2028-04-01")
        self.assertEqual(values["Key number"], "1")
        self.assertEqual(values["Key name"], "SeedSigner")
        self.assertEqual(values["Available"], "Yes")
        self.assertEqual(values["Seed backup verified"], "OK")
        self.assertEqual(values["Wallet software"], "Sparrow Wallet")
        self.assertEqual(values["Contact details confirmed"], "Yes")
        self.assertIn("SeedSigner: IKKJE_VURDERT", values["BIP327"])
        self.assertIn("Nunchuk: SECURE", values["Security status"])

    def test_health_check_form_is_served_in_english(self):
        with urlopen(f"{self.base_url}/health-check") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="health-check-form"', body)
        self.assertIn('id="key-select"', body)
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

    def test_alerts_api_reports_follow_up_for_the_latest_check(self):
        key = self.key_profiles()[1]
        payload = sample_payload(key)
        payload["key_check"]["available"] = 0

        with self.post_json("/api/health-checks", payload) as response:
            self.assertEqual(response.status, 201)

        with urlopen(f"{self.base_url}/api/alerts") as response:
            alerts = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertIn("Key 2", alerts[0]["source"])

    def test_saved_health_check_can_be_read_back(self):
        key = self.key_profiles()[0]
        with self.post_json("/api/health-checks", sample_payload(key)) as response:
            self.assertEqual(response.status, 201)
            saved = json.load(response)

        with urlopen(f"{self.base_url}/api/health-checks") as response:
            summaries = json.load(response)
        summary = next(entry for entry in summaries if entry["id"] == saved["id"])
        self.assertEqual(summary["key_numbers"], [1])

        with urlopen(f"{self.base_url}/api/health-checks/{saved['id']}") as response:
            record = json.load(response)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertEqual(record["wallet_software"], "Sparrow Wallet")
        self.assertEqual(len(record["key_checks"]), 1)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(
            [entry["product"] for entry in record["tool_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )
        self.assertEqual(len(record["ai_security_checks"]), 3)

    def test_each_key_can_be_posted_and_read_back(self):
        for key in self.key_profiles():
            with self.post_json("/api/health-checks", sample_payload(key)) as response:
                self.assertEqual(response.status, 201)
                saved = json.load(response)
            with urlopen(f"{self.base_url}/api/health-checks/{saved['id']}") as response:
                record = json.load(response)
            self.assertEqual(record["key_checks"][0]["key_number"], key["key_number"])

    def test_invalid_health_check_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "not-a-date"

        self.assert_rejected(payload)

    def test_irrelevant_product_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["tool_checks"].append(
            {"product": "Blockstream Jade", "bip327_status": "OK", "slip39_status": "OK"}
        )

        self.assert_rejected(payload)

    def test_sparrow_wallet_is_rejected_for_the_cloud_key(self):
        payload = sample_payload(self.key_profiles()[2])
        payload["wallet_software"] = "Sparrow Wallet"

        self.assert_rejected(payload)

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
