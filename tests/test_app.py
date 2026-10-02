"""HTTP tests for the dashboard server.

Every test gets its own database and server, so the tests stay independent of
each other and of the order they run in.
"""

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
            {"product": product, "bip327_status": "NOT_ASSESSED", "slip39_status": "NOT_ASSESSED"}
            for product in products
        ],
        "ai_security_checks": [
            {"provider": provider, "status": "SECURE", "comments": ""} for provider in providers
        ],
    }


def unavailable_payload(key):
    """Return the payload the form sends for a key that was not available."""
    entry = {
        "key_id": key["id"],
        "available": 0,
        "comments": "Key is with the third holder",
    }
    if key["type"] == "cloud":
        # The form derives these from availability alone (section 20).
        entry.update({"cloud_health_status": "PROBLEM", "cloud_provider_operational": 0})
    return {
        "checked_at": "2026-10-01",
        "wallet_software": None,
        "software_compatibility_status": "NOT_ASSESSED",
        "contact_info_verified": 1,
        "comments": "Annual review",
        "key_check": entry,
        "tool_checks": [],
        "ai_security_checks": [],
    }


class AppHandlerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        seed_fixed_keys(self.database_path)
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

    def post_health_check(self, payload):
        """Store one check and return its id."""
        with self.post_json("/api/health-checks", payload) as response:
            self.assertEqual(response.status, 201)
            return json.load(response)["id"]

    def get_record(self, health_check_id):
        with urlopen(f"{self.base_url}/api/health-checks/{health_check_id}") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_alerts(self):
        with urlopen(f"{self.base_url}/api/alerts") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

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

    def test_key_status_api_is_empty_before_anything_is_saved(self):
        with urlopen(f"{self.base_url}/api/key-status") as response:
            status = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual([entry["last_checked_at"] for entry in status], [None, None, None])
        self.assertEqual([entry["next_check_due"] for entry in status], [None, None, None])

    def test_key_status_api_lists_each_key_with_its_newest_check(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "2027-03-01"
        self.post_health_check(payload)

        with urlopen(f"{self.base_url}/api/key-status") as response:
            status = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual([entry["type"] for entry in status], ["hardware", "hardware", "cloud"])
        self.assertEqual(status[0]["name"], "SeedSigner")
        self.assertEqual(status[0]["last_checked_at"], "2027-03-01")
        self.assertEqual(status[0]["next_check_due"], "2028-03-01")
        self.assertIsNone(status[1]["last_checked_at"])
        self.assertIsNone(status[2]["last_checked_at"])

    def test_previous_values_api_is_empty_before_anything_is_saved(self):
        with urlopen(f"{self.base_url}/api/previous-values") as response:
            values = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual([entry["key_id"] for entry in values["keys"]], [1, 2, 3])
        self.assertEqual(values["security"], {})
        self.assertIsNone(values["keys"][0]["firmware_version"])
        self.assertIsNone(values["keys"][0]["software_version"])

    def test_previous_values_api_reports_the_last_saved_values(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["checked_at"] = "2027-06-01"
        payload["software_version"] = "1.8.5"
        payload["key_check"]["firmware_version"] = "1.2.3"
        self.post_health_check(payload)

        with urlopen(f"{self.base_url}/api/previous-values") as response:
            values = json.load(response)

        self.assertEqual(response.status, 200)
        by_key = {entry["key_id"]: entry for entry in values["keys"]}
        self.assertEqual(by_key[key["id"]]["firmware_version"], "1.2.3")
        self.assertEqual(by_key[key["id"]]["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(by_key[key["id"]]["wallet_software"], "Sparrow Wallet")
        self.assertEqual(by_key[key["id"]]["software_version"], "1.8.5")
        self.assertEqual(values["security"]["SeedSigner"], "SECURE")
        self.assertEqual(values["security"]["Sparrow Wallet"], "SECURE")
        self.assertEqual(values["security"]["Nunchuk"], "SECURE")

    def test_export_api_returns_a_csv_download(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "2027-04-01"
        saved_id = self.post_health_check(payload)

        with urlopen(f"{self.base_url}/api/export") as response:
            body = response.read().decode("utf-8")
            content_type = response.headers["Content-Type"]
            disposition = response.headers["Content-Disposition"]

        self.assertEqual(response.status, 200)
        self.assertEqual(content_type, "text/csv; charset=utf-8")
        self.assertIn("helsesjekk-export.csv", disposition)

        rows = list(csv.reader(io.StringIO(body)))
        self.assertEqual(rows[0], list(HEADERS))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(saved_id))

        values = dict(zip(HEADERS, rows[1]))
        self.assertEqual(values["Check date"], "2027-04-01")
        self.assertEqual(values["Next check due"], "2028-04-01")
        self.assertEqual(values["Key number"], "1")
        self.assertEqual(values["Key name"], "SeedSigner")
        self.assertEqual(values["Available"], "Yes")
        self.assertEqual(values["Seed backup verified"], "OK")
        self.assertEqual(values["Wallet software"], "Sparrow Wallet")
        self.assertEqual(values["Contact details confirmed"], "Yes")
        self.assertIn("SeedSigner: NOT_ASSESSED", values["BIP327"])
        self.assertIn("Nunchuk: SECURE", values["Security status"])

    def test_export_api_leaves_the_skipped_columns_empty(self):
        saved_id = self.post_health_check(unavailable_payload(self.key_profiles()[1]))

        with urlopen(f"{self.base_url}/api/export") as response:
            body = response.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(body)))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Check id"], str(saved_id))
        self.assertEqual(values["Available"], "No")
        self.assertEqual(values["Key comments"], "Key is with the third holder")
        self.assertEqual(values["Wallet software"], "")
        self.assertEqual(values["Software compatibility"], "NOT_ASSESSED")
        self.assertEqual(values["BIP327"], "")
        self.assertEqual(values["SLIP39"], "")
        self.assertEqual(values["Security status"], "")

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

    def test_dashboard_links_to_the_form_the_history_and_the_export(self):
        with urlopen(self.base_url) as response:
            body = response.read().decode("utf-8")

        self.assertIn('href="/health-check"', body)
        self.assertIn('href="/history"', body)
        self.assertIn('href="/api/export"', body)
        self.assertIn("Download CSV", body)
        self.assertNotIn("Report export is not implemented", body)

    def test_alerts_api_is_empty_before_anything_is_saved(self):
        with urlopen(f"{self.base_url}/api/alerts") as response:
            self.assertEqual(json.load(response), [])

    def test_alerts_api_reports_follow_up_from_the_saved_check(self):
        saved_id = self.post_health_check(unavailable_payload(self.key_profiles()[1]))

        alerts = self.get_alerts()

        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertIn("Key 2", alerts[0]["source"])
        self.assertEqual(alerts[0]["check_id"], saved_id)
        self.assertEqual(alerts[0]["checked_at"], "2026-10-01")

    def test_alerts_api_keeps_alerts_from_older_checks(self):
        older = unavailable_payload(self.key_profiles()[1])
        older_id = self.post_health_check(older)

        newer = sample_payload(self.key_profiles()[0])
        newer["checked_at"] = "2027-01-01"
        self.post_health_check(newer)

        alerts = self.get_alerts()

        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], older_id)

    def test_alerts_api_merges_identical_alerts_and_keeps_the_newest(self):
        older = unavailable_payload(self.key_profiles()[1])
        older["checked_at"] = "2026-01-01"
        older_id = self.post_health_check(older)

        newer = unavailable_payload(self.key_profiles()[1])
        newer["checked_at"] = "2027-01-01"
        newer_id = self.post_health_check(newer)

        alerts = self.get_alerts()

        self.assertNotEqual(older_id, newer_id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["code"], "key_unavailable")
        self.assertEqual(alerts[0]["check_id"], newer_id)
        self.assertEqual(alerts[0]["checked_at"], "2027-01-01")

    def test_alerts_api_lists_critical_alerts_before_informational_ones(self):
        older = sample_payload(self.key_profiles()[1])
        older["checked_at"] = "2026-01-01"
        older["key_check"]["hardware_works"] = 0
        self.post_health_check(older)

        newer = sample_payload(self.key_profiles()[0])
        newer["checked_at"] = "2027-01-01"
        newer["contact_info_verified"] = 0
        self.post_health_check(newer)

        alerts = self.get_alerts()

        self.assertEqual(
            [alert["severity"] for alert in alerts],
            ["critical", "info"],
        )
        self.assertEqual(
            [alert["code"] for alert in alerts],
            ["hardware_failure", "contact_info_unconfirmed"],
        )

    def test_saved_health_check_can_be_read_back(self):
        key = self.key_profiles()[0]
        saved_id = self.post_health_check(sample_payload(key))

        with urlopen(f"{self.base_url}/api/health-checks") as response:
            summaries = json.load(response)
        summary = next(entry for entry in summaries if entry["id"] == saved_id)
        self.assertEqual(summary["key_numbers"], [1])

        record = self.get_record(saved_id)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertEqual(record["wallet_software"], "Sparrow Wallet")
        self.assertEqual(len(record["key_checks"]), 1)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(
            [entry["product"] for entry in record["tool_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )
        self.assertEqual(record["tool_checks"][0]["bip327_status"], "NOT_ASSESSED")
        self.assertEqual(len(record["ai_security_checks"]), 3)

    def test_each_key_can_be_posted_and_read_back(self):
        for key in self.key_profiles():
            saved_id = self.post_health_check(sample_payload(key))
            record = self.get_record(saved_id)
            self.assertEqual(record["key_checks"][0]["key_number"], key["key_number"])

    def test_a_minimal_unavailable_payload_is_accepted(self):
        key = self.key_profiles()[1]
        payload = {
            "checked_at": "2026-10-01",
            "key_check": {
                "key_id": key["id"],
                "available": 0,
                "comments": "Key is with the third holder",
            },
        }

        saved_id = self.post_health_check(payload)

        record = self.get_record(saved_id)
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertIsNone(record["wallet_software"])
        self.assertIsNone(record["software_version"])
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["tool_checks"], [])
        self.assertEqual(record["ai_security_checks"], [])
        self.assertEqual(record["key_checks"][0]["available"], 0)
        self.assertEqual(record["key_checks"][0]["comments"], "Key is with the third holder")

        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], saved_id)

    def test_an_unavailable_key_rejects_recorded_results(self):
        key = self.key_profiles()[0]
        recorded = (
            ("wallet_software", "Sparrow Wallet"),
            ("tool_checks", [{"product": "SeedSigner", "bip327_status": "YES", "slip39_status": "YES"}]),
            ("ai_security_checks", [{"provider": "SeedSigner", "status": "SECURE", "comments": ""}]),
        )
        for field, value in recorded:
            payload = {
                "checked_at": "2026-10-01",
                "key_check": {"key_id": key["id"], "available": 0},
                field: value,
            }
            self.assert_rejected(payload)

    def test_a_payload_without_availability_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        del payload["key_check"]["available"]

        self.assert_rejected(payload)

    def test_an_unavailable_cloud_key_keeps_its_derived_cloud_results(self):
        key = self.key_profiles()[2]
        saved_id = self.post_health_check(unavailable_payload(key))

        record = self.get_record(saved_id)

        self.assertIsNone(record["wallet_software"])
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["tool_checks"], [])
        self.assertEqual(record["ai_security_checks"], [])
        self.assertEqual(record["key_checks"][0]["cloud_health_status"], "PROBLEM")
        self.assertEqual(record["key_checks"][0]["cloud_provider_operational"], 0)
        self.assertIsNone(record["key_checks"][0]["address_path_verified"])

        alerts = self.get_alerts()

        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertIn("cloud provider", alerts[0]["message"])

    def test_invalid_health_check_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "not-a-date"

        self.assert_rejected(payload)

    def test_the_old_status_values_are_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["software_compatibility_status"] = "IKKJE_VURDERT"

        self.assert_rejected(payload)

    def test_the_old_standards_values_are_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["tool_checks"][0]["bip327_status"] = "OK"

        self.assert_rejected(payload)

    def test_irrelevant_product_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["tool_checks"].append(
            {"product": "Blockstream Jade", "bip327_status": "YES", "slip39_status": "YES"}
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
