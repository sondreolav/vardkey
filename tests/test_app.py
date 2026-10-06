"""HTTP tests for the dashboard server.

Every test gets its own database and server, so the tests stay independent of
each other and of the order they run in. ``AppHandlerTests`` starts from a
stored key setup; ``KeySetupApiTests`` starts from a new, empty database.
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
from database import initialize_database, save_key_setup
from export import HEADERS


# The address path each key slot is configured with (sections 25.1 and 26.2).
ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
# The path a rotation of each key records: it must be new and unique
# (section 26.3).
ROTATION_PATHS = {
    1: "m/48'/10'/0'/2'",
    2: "m/48'/11'/0'/2'",
    3: "m/48'/12'/0'/2'",
}
# The key setup most tests start from (section 23.2).
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
]
# A setup with the cloud key in the first slot, renamed hardware keys, and a
# different address path per key.
RENAMED_SETUP = [
    {"key_number": 1, "name": "Coinbase", "type": "cloud", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "ColdCard", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Jade", "type": "hardware", "address_path": THIRD_ADDRESS_PATH},
]


def sample_payload(key, wallet_software=None, address_path=None):
    """Return a valid single-key payload for the given key profile.

    The recorded address path matches the stored one unless a test asks for
    another one (section 25.1).
    """
    if wallet_software is None:
        wallet_software = key["name"] if key["type"] == "cloud" else "Sparrow Wallet"
    labels = list(dict.fromkeys((key["name"], wallet_software)))
    entry = {
        "key_id": key["id"],
        "available": 1,
        "address_path": address_path if address_path is not None else key["address_path"],
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
        "wallet_software": None,
        "software_compatibility_status": "NOT_ASSESSED",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 0,
            "comments": "Key is with the third holder",
        },
        "ai_security_checks": [],
    }


def mismatch_payload(key, address_path="m/48'/9'/0'/2'"):
    """Return the minimal payload the form sends when the path does not match.

    Everything else about the key is left out, because the key could not be
    checked (section 25.1).
    """
    return {
        "checked_at": "2026-10-01",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 1,
            "address_path": address_path,
            "comments": "Path read from the device",
        },
    }


class ServerTestCase(unittest.TestCase):
    """Start a server on a temporary database."""

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

    def store_setup(self, setup=DEFAULT_SETUP):
        """Store the key setup directly, without going through the API."""
        save_key_setup(setup, self.database_path)

    def key_profiles(self):
        with urlopen(f"{self.base_url}/api/keys") as response:
            return json.load(response)

    def get_setup(self):
        with urlopen(f"{self.base_url}/api/setup") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_settings(self):
        with urlopen(f"{self.base_url}/api/settings") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_health_checks(self):
        with urlopen(f"{self.base_url}/api/health-checks") as response:
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

    def post_health_check(self, payload):
        """Store one check and return its id."""
        with self.post_json("/api/health-checks", payload) as response:
            self.assertEqual(response.status, 201)
            return json.load(response)["id"]

    def post_setup(self, payload):
        return self.post_json("/api/setup", payload)

    def post_key_settings(self, payload):
        return self.post_json("/api/settings/keys", payload)

    def post_wallet_software(self, names):
        return self.post_json("/api/settings/wallet-software", {"wallet_software": names})

    def post_rotation(self, key_id, payload):
        return self.post_json(f"/api/keys/{key_id}/rotate", payload)

    def post_acknowledgement(self, payload):
        return self.post_json("/api/alerts/acknowledge", payload)

    def get_record(self, health_check_id):
        with urlopen(f"{self.base_url}/api/health-checks/{health_check_id}") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def get_alerts(self):
        with urlopen(f"{self.base_url}/api/alerts") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def assert_rejected_at(self, path, payload, status=400):
        """Post a payload to one endpoint and expect an error status."""
        try:
            with self.post_json(path, payload) as response:
                self.fail(f"Expected {status}, received {response.status}")
        except HTTPError as error:
            try:
                self.assertEqual(error.code, status)
                error.read()
            finally:
                error.close()

    def assert_rejected(self, payload, status=400):
        self.assert_rejected_at("/api/health-checks", payload, status)

    def assert_setup_rejected(self, payload, status=400):
        self.assert_rejected_at("/api/setup", payload, status)

    def rotation_path(self, key_id):
        """Return the new address path a rotation of one key records."""
        return ROTATION_PATHS[key_id]

    def rotate(self, key_id, keep_name=True, name="", address_path=None, **extra):
        """Rotate one key and return the stored settings the server answers."""
        payload = {
            "replaced": True,
            "keep_name": keep_name,
            "name": name,
            "address_path": address_path or self.rotation_path(key_id),
        }
        payload.update(extra)
        with self.post_rotation(key_id, payload) as response:
            self.assertEqual(response.status, 200)
            return json.load(response)


class AppHandlerTests(ServerTestCase):
    """The endpoints once the key setup is stored."""

    def setUp(self):
        super().setUp()
        self.store_setup()

    def test_health_endpoint_returns_json(self):
        with urlopen(f"{self.base_url}/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok"})
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_key_api_returns_the_configured_profiles(self):
        keys = self.key_profiles()

        self.assertEqual([key["key_number"] for key in keys], [1, 2, 3])
        self.assertEqual(
            [key["name"] for key in keys],
            ["SeedSigner", "Blockstream Jade", "Nunchuk"],
        )
        self.assertEqual([key["type"] for key in keys], ["hardware", "hardware", "cloud"])
        # The address path is part of the key's identity, and every key has its
        # own one (sections 25.1 and 26.2).
        self.assertEqual(
            [key["address_path"] for key in keys],
            [ADDRESS_PATH, SECOND_ADDRESS_PATH, THIRD_ADDRESS_PATH],
        )
        # The configured name is the product label, so there is no device field.
        self.assertNotIn("device", keys[0])

    def test_setup_api_reports_the_stored_setup(self):
        setup = self.get_setup()

        self.assertTrue(setup["configured"])
        self.assertEqual([key["name"] for key in setup["keys"]],
                         ["SeedSigner", "Blockstream Jade", "Nunchuk"])

    def test_a_stored_setup_cannot_be_replaced(self):
        self.assert_setup_rejected({"keys": RENAMED_SETUP}, status=409)

        self.assertEqual([key["name"] for key in self.key_profiles()],
                         ["SeedSigner", "Blockstream Jade", "Nunchuk"])

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
        self.assertEqual(by_key[key["id"]]["address_path"], ADDRESS_PATH)
        self.assertEqual(by_key[key["id"]]["wallet_software"], "Sparrow Wallet")
        self.assertEqual(by_key[key["id"]]["software_version"], "1.8.5")

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
        self.assertEqual(values["Hardware works"], "Yes")
        self.assertEqual(values["Seed backup verified"], "OK")
        self.assertEqual(values["Address path"], ADDRESS_PATH)
        self.assertEqual(values["Address path verified"], "OK")
        self.assertEqual(values["Wallet software"], "Sparrow Wallet")
        # The contact confirmation is a status, not a yes/no flag (section 23.1).
        self.assertEqual(values["Contact details confirmed"], "Confirmed current")
        self.assertIn("SeedSigner: SECURE", values["Security status"])
        # The two derived cloud columns are gone (section 25.6).
        self.assertNotIn("Cloud health status", HEADERS)
        self.assertNotIn("Cloud provider operational", HEADERS)

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
        self.assertEqual(values["Security status"], "")

    def test_health_check_form_is_served_in_english(self):
        with urlopen(f"{self.base_url}/health-check") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="health-check-form"', body)
        self.assertIn('id="key-select"', body)
        self.assertIn('id="address-path-warning"', body)
        # The form names the keys that an open alert blocks (section 26.1).
        self.assertIn('id="blocked-keys-note"', body)
        self.assertIn('id="blocked-keys-list"', body)
        self.assertIn("Never enter seed phrases", body)
        self.assertIn("Save health check", body)

    def test_setup_page_is_served_in_english(self):
        with urlopen(f"{self.base_url}/setup") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="setup-form"', body)
        self.assertIn('name="key_1_address_path"', body)
        self.assertIn("Never enter seed phrases", body)
        self.assertIn("Save key setup", body)

    def test_settings_page_is_served_in_english(self):
        with urlopen(f"{self.base_url}/settings") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="keys-list"', body)
        self.assertIn('id="wallet-software-list"', body)
        self.assertIn('id="rotation-list"', body)
        self.assertIn("Rotate selected keys", body)
        # The funds have to be moved to the new wallet, and the path has to change
        # because the key is a new one (sections 25.2 and 26.3).
        self.assertIn("Rotating a key creates a new wallet", body)
        self.assertIn("The address path must change", body)
        self.assertIn("Never enter seed phrases", body)

    def test_history_page_is_served_in_english(self):
        with urlopen(f"{self.base_url}/history") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('<html lang="en">', body)
        self.assertIn('id="history-list"', body)
        self.assertIn("Saved health checks", body)

    def test_dashboard_links_to_the_form_the_history_the_export_and_the_settings(self):
        with urlopen(self.base_url) as response:
            body = response.read().decode("utf-8")

        self.assertIn('href="/health-check"', body)
        self.assertIn('href="/history"', body)
        self.assertIn('href="/api/export"', body)
        self.assertIn('href="/settings"', body)
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
        # The alert names the action that closes it and the key it came from
        # (sections 25.2 and 26.4).
        self.assertEqual(alerts[0]["actions"], ["rotate"])
        self.assertEqual(alerts[0]["key_id"], self.key_profiles()[1]["id"])
        self.assertIsNone(alerts[0]["software"])

    def test_a_key_with_an_open_alert_cannot_get_a_new_check(self):
        # The server enforces the rule, so a direct API call cannot bypass it
        # (section 26.1).
        keys = self.key_profiles()
        self.post_health_check(unavailable_payload(keys[1]))
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["key_unavailable"])

        self.assert_rejected(unavailable_payload(keys[1]), status=409)

        # The blocking applies to that key only.
        self.post_health_check(sample_payload(keys[0]))

        # Closing the alert with the action that belongs to it frees the key again.
        self.rotate(keys[1]["id"])
        self.assertEqual(self.get_alerts(), [])
        self.post_health_check(unavailable_payload(keys[1]))

        self.assertEqual(len(self.get_health_checks()), 3)

    def test_the_blocking_rule_runs_before_the_rest_of_the_validation(self):
        keys = self.key_profiles()
        self.post_health_check(unavailable_payload(keys[1]))

        # The key is blocked, so the answer is 409 even when the payload would
        # otherwise be refused with 400 (section 26.1).
        payload = unavailable_payload(keys[1])
        payload["contact_info_verified"] = ""
        self.assert_rejected(payload, status=409)

    def test_closing_an_alert_with_its_action_frees_the_key(self):
        keys = self.key_profiles()
        payload = sample_payload(keys[0])
        payload["key_check"]["hardware_works"] = 0
        self.post_health_check(payload)
        alert = self.get_alerts()[0]
        self.assertEqual(alert["code"], "hardware_failure")

        self.assert_rejected(sample_payload(keys[0]), status=409)

        with self.post_acknowledgement({
            "code": alert["code"],
            "source": alert["source"],
            "action": "replace_hardware",
        }) as response:
            self.assertEqual(response.status, 201)

        self.assertEqual(self.get_alerts(), [])
        self.post_health_check(sample_payload(keys[0]))

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
        # A second check for a key with an open alert would be blocked
        # (section 26.1), so the informational contact alert is used here: it
        # carries no key and never blocks one.
        key = self.key_profiles()[1]
        older = sample_payload(key)
        older["checked_at"] = "2026-01-01"
        older["contact_info_verified"] = "Needs external update"
        older_id = self.post_health_check(older)

        newer = sample_payload(key)
        newer["checked_at"] = "2027-01-01"
        newer["contact_info_verified"] = "Needs external update"
        newer_id = self.post_health_check(newer)

        alerts = self.get_alerts()

        self.assertNotEqual(older_id, newer_id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["code"], "contact_info_unconfirmed")
        self.assertEqual(alerts[0]["check_id"], newer_id)
        self.assertEqual(alerts[0]["checked_at"], "2027-01-01")

    def test_alerts_api_lists_critical_alerts_before_informational_ones(self):
        older = sample_payload(self.key_profiles()[1])
        older["checked_at"] = "2026-01-01"
        older["key_check"]["hardware_works"] = 0
        self.post_health_check(older)

        newer = sample_payload(self.key_profiles()[0])
        newer["checked_at"] = "2027-01-01"
        newer["contact_info_verified"] = "Needs external update"
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

    def test_a_software_alert_names_the_software_it_is_about(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["software_compatibility_status"] = "PROBLEM"
        self.post_health_check(payload)

        alerts = self.get_alerts()

        self.assertEqual([alert["code"] for alert in alerts], ["software_incompatible"])
        # The alert names the software, so the settings link and the removal point
        # at the right entry (section 26.7).
        self.assertEqual(alerts[0]["source"], "Sparrow Wallet")
        self.assertEqual(alerts[0]["software"], "Sparrow Wallet")
        self.assertEqual(alerts[0]["actions"], ["remove_software"])

    def test_saved_health_check_can_be_read_back(self):
        key = self.key_profiles()[0]
        saved_id = self.post_health_check(sample_payload(key))

        summary = next(entry for entry in self.get_health_checks() if entry["id"] == saved_id)
        self.assertEqual(summary["key_numbers"], [1])

        record = self.get_record(saved_id)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertEqual(record["wallet_software"], "Sparrow Wallet")
        self.assertEqual(record["contact_info_verified"], "Confirmed current")
        self.assertEqual(len(record["key_checks"]), 1)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(record["key_checks"][0]["address_path"], ADDRESS_PATH)
        self.assertEqual(record["key_checks"][0]["address_path_verified"], "OK")
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )

    def test_each_key_can_be_posted_and_read_back(self):
        for key in self.key_profiles():
            saved_id = self.post_health_check(sample_payload(key))
            record = self.get_record(saved_id)
            self.assertEqual(record["key_checks"][0]["key_number"], key["key_number"])

    def test_a_minimal_unavailable_payload_is_accepted(self):
        # The check date, the key check, and the contact confirmation are the
        # minimum, because the confirmation is required for every submission
        # (section 24.1).
        key = self.key_profiles()[1]
        payload = {
            "checked_at": "2026-10-01",
            "contact_info_verified": "Confirmed current",
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
        self.assertEqual(record["contact_info_verified"], "Confirmed current")
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
            ("ai_security_checks", [{"provider": "SeedSigner", "status": "SECURE", "comments": ""}]),
        )
        for field, value in recorded:
            payload = {
                "checked_at": "2026-10-01",
                "contact_info_verified": "Confirmed current",
                "key_check": {"key_id": key["id"], "available": 0},
                field: value,
            }
            self.assert_rejected(payload)

    def test_a_payload_without_availability_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        del payload["key_check"]["available"]

        self.assert_rejected(payload)

    def test_a_hardware_key_without_hardware_works_is_rejected(self):
        # Hardware works requires an active Yes or No (section 24.1).
        for value in ("", None):
            payload = sample_payload(self.key_profiles()[0])
            payload["key_check"]["hardware_works"] = value
            self.assert_rejected(payload)

        payload = sample_payload(self.key_profiles()[0])
        del payload["key_check"]["hardware_works"]
        self.assert_rejected(payload)

    def test_an_unavailable_cloud_key_records_nothing_else(self):
        key = self.key_profiles()[2]
        saved_id = self.post_health_check(unavailable_payload(key))

        record = self.get_record(saved_id)

        self.assertIsNone(record["wallet_software"])
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["ai_security_checks"], [])
        self.assertEqual(record["key_checks"][0]["available"], 0)
        self.assertIsNone(record["key_checks"][0]["address_path_verified"])
        self.assertIsNone(record["key_checks"][0]["address_path"])

        alerts = self.get_alerts()

        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertIn("Key 3", alerts[0]["source"])

    def test_invalid_health_check_is_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["checked_at"] = "not-a-date"

        self.assert_rejected(payload)

    def test_the_old_status_values_are_rejected(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["software_compatibility_status"] = "IKKJE_VURDERT"

        self.assert_rejected(payload)

    def test_a_missing_compatibility_status_is_rejected(self):
        # Compatibility requires an active choice for a key that was available
        # (section 23.1).
        for value in ("", None, "NOT_ASSESSED"):
            payload = sample_payload(self.key_profiles()[0])
            payload["software_compatibility_status"] = value
            self.assert_rejected(payload)

        payload = sample_payload(self.key_profiles()[0])
        del payload["software_compatibility_status"]
        self.assert_rejected(payload)

    def test_the_cloud_key_derives_its_compatibility_status(self):
        payload = sample_payload(self.key_profiles()[2])
        saved_id = self.post_health_check(payload)
        self.assertEqual(
            self.get_record(saved_id)["software_compatibility_status"], "OK"
        )

        rejected = sample_payload(self.key_profiles()[2])
        rejected["software_compatibility_status"] = "PROBLEM"
        self.assert_rejected(rejected)

    def test_the_server_records_the_address_path_result(self):
        key = self.key_profiles()[0]

        matching = self.post_health_check(sample_payload(key))
        self.assertEqual(
            self.get_record(matching)["key_checks"][0]["address_path_verified"], "OK"
        )

        mismatch = self.post_health_check(mismatch_payload(key))
        self.assertEqual(
            self.get_record(mismatch)["key_checks"][0]["address_path_verified"], "PROBLEM"
        )

    def test_a_mismatch_records_only_the_minimal_content(self):
        key = self.key_profiles()[0]
        saved_id = self.post_health_check(mismatch_payload(key))

        record = self.get_record(saved_id)
        key_check = record["key_checks"][0]

        # The recorded path and the key note are kept, while everything else
        # stays empty (section 25.1).
        self.assertEqual(key_check["address_path"], "m/48'/9'/0'/2'")
        self.assertEqual(key_check["address_path_verified"], "PROBLEM")
        self.assertEqual(key_check["comments"], "Path read from the device")
        self.assertIsNone(key_check["hardware_works"])
        self.assertIsNone(key_check["firmware_version"])
        self.assertIsNone(key_check["seed_backup_verified"])
        self.assertIsNone(record["wallet_software"])
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["ai_security_checks"], [])
        self.assertEqual(record["comments"], "Annual review")

        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["address_path_mismatch"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["check_id"], saved_id)

    def test_a_mismatch_rejects_software_or_security_results(self):
        key = self.key_profiles()[0]
        recorded = (
            ("wallet_software", "Sparrow Wallet"),
            ("ai_security_checks", [{"provider": "SeedSigner", "status": "SECURE", "comments": ""}]),
            ("software_compatibility_status", "OK"),
        )
        for field, value in recorded:
            payload = mismatch_payload(key)
            payload[field] = value
            self.assert_rejected(payload)

    def test_an_unavailable_key_never_reports_a_mismatch(self):
        key = self.key_profiles()[1]
        payload = unavailable_payload(key)
        payload["key_check"]["address_path"] = SECOND_ADDRESS_PATH

        saved_id = self.post_health_check(payload)

        record = self.get_record(saved_id)
        self.assertIsNone(record["key_checks"][0]["address_path"])
        self.assertIsNone(record["key_checks"][0]["address_path_verified"])
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["key_unavailable"])

    def test_a_submitted_address_path_result_is_ignored(self):
        # The client never sends the result, and the server overrules it anyway
        # (section 25.1).
        key = self.key_profiles()[0]
        payload = mismatch_payload(key)
        payload["key_check"]["address_path_verified"] = "OK"

        saved_id = self.post_health_check(payload)

        self.assertEqual(
            self.get_record(saved_id)["key_checks"][0]["address_path_verified"], "PROBLEM"
        )

    def test_the_old_contact_flag_is_rejected(self):
        # Only the two contact statuses are recorded (section 23.1).
        for value in (1, 0, "yes"):
            payload = sample_payload(self.key_profiles()[0])
            payload["contact_info_verified"] = value
            self.assert_rejected(payload)

    def test_a_submission_without_a_contact_confirmation_is_rejected(self):
        # The confirmation is required, also for a key that was not available
        # (section 24.1).
        for payload in (
            sample_payload(self.key_profiles()[0]),
            unavailable_payload(self.key_profiles()[1]),
        ):
            for value in ("", None):
                payload["contact_info_verified"] = value
                self.assert_rejected(payload)
            del payload["contact_info_verified"]
            self.assert_rejected(payload)

    def test_the_contact_status_is_recorded_and_raises_an_informational_alert(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["contact_info_verified"] = "Needs external update"
        saved_id = self.post_health_check(payload)

        record = self.get_record(saved_id)
        self.assertEqual(record["contact_info_verified"], "Needs external update")

        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["contact_info_unconfirmed"])
        self.assertEqual(alerts[0]["severity"], "info")
        self.assertEqual(alerts[0]["check_id"], saved_id)
        self.assertEqual(alerts[0]["actions"], ["contact_updated"])

    def test_a_hardware_key_name_is_not_a_wallet_software_choice(self):
        # "Jade" is a hardware key in this setup, so it is never software.
        payload = sample_payload(self.key_profiles()[1])
        payload["wallet_software"] = "Jade"

        self.assert_rejected(payload)

    def test_a_hardware_key_may_use_the_cloud_key_name_as_its_software(self):
        payload = sample_payload(self.key_profiles()[0], wallet_software="Nunchuk")
        payload["ai_security_checks"] = [
            {"provider": label, "status": "SECURE", "comments": ""}
            for label in ("SeedSigner", "Nunchuk")
        ]

        saved_id = self.post_health_check(payload)

        self.assertEqual(self.get_record(saved_id)["wallet_software"], "Nunchuk")

    def test_a_renamed_key_records_its_own_name(self):
        with urlopen(f"{self.base_url}/api/setup") as response:
            self.assertEqual(response.status, 200)

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


class RenamedSetupTests(ServerTestCase):
    """The endpoints with a renamed setup and the cloud key in the first slot."""

    def setUp(self):
        super().setUp()
        self.store_setup(RENAMED_SETUP)

    def test_the_cloud_key_records_its_own_name(self):
        key = self.key_profiles()[0]
        self.assertEqual(key["name"], "Coinbase")
        self.assertEqual(key["type"], "cloud")

        saved_id = self.post_health_check(sample_payload(key))

        record = self.get_record(saved_id)
        self.assertEqual(record["wallet_software"], "Coinbase")
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]], ["Coinbase"]
        )

    def test_a_hardware_key_records_its_configured_name(self):
        key = self.key_profiles()[1]
        self.assertEqual(key["name"], "ColdCard")

        saved_id = self.post_health_check(sample_payload(key))

        record = self.get_record(saved_id)
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]],
            ["ColdCard", "Sparrow Wallet"],
        )

    def test_the_address_path_of_the_selected_key_is_the_one_that_counts(self):
        # The three keys have different paths, so a path that belongs to another
        # key is a mismatch for this one (section 25.1).
        key = self.key_profiles()[2]

        matching = self.post_health_check(sample_payload(key))
        self.assertEqual(
            self.get_record(matching)["key_checks"][0]["address_path_verified"], "OK"
        )

        other_path = self.key_profiles()[1]["address_path"]
        mismatch = self.post_health_check(mismatch_payload(key, other_path))
        self.assertEqual(
            self.get_record(mismatch)["key_checks"][0]["address_path_verified"], "PROBLEM"
        )

    def test_the_dashboard_reports_the_configured_names(self):
        with urlopen(f"{self.base_url}/api/key-status") as response:
            status = json.load(response)

        self.assertEqual([entry["name"] for entry in status], ["Coinbase", "ColdCard", "Jade"])
        self.assertEqual([entry["type"] for entry in status], ["cloud", "hardware", "hardware"])

    def test_the_export_uses_the_configured_name(self):
        key = self.key_profiles()[1]
        self.post_health_check(sample_payload(key))

        with urlopen(f"{self.base_url}/api/export") as response:
            body = response.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(body)))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Key name"], "ColdCard")
        self.assertEqual(values["Key type"], "hardware")
        self.assertEqual(values["Security status"], "ColdCard: SECURE; Sparrow Wallet: SECURE")


class SettingsApiTests(ServerTestCase):
    """The settings page reads and writes one section at a time (section 25.4)."""

    def setUp(self):
        super().setUp()
        self.store_setup()

    def test_the_settings_api_returns_the_keys_and_the_software_list(self):
        settings = self.get_settings()

        self.assertEqual(
            [key["name"] for key in settings["keys"]],
            ["SeedSigner", "Blockstream Jade", "Nunchuk"],
        )
        self.assertEqual(
            [key["address_path"] for key in settings["keys"]],
            [ADDRESS_PATH, SECOND_ADDRESS_PATH, THIRD_ADDRESS_PATH],
        )
        self.assertEqual(settings["wallet_software"], ["Sparrow Wallet"])

    def test_the_settings_api_reports_whether_a_key_has_checks(self):
        self.assertEqual([key["has_checks"] for key in self.get_settings()["keys"]],
                         [False, False, False])

        self.post_health_check(sample_payload(self.key_profiles()[0]))

        self.assertEqual([key["has_checks"] for key in self.get_settings()["keys"]],
                         [True, False, False])

    def test_a_key_name_can_be_changed(self):
        key = self.key_profiles()[0]

        with self.post_key_settings({
            "key_id": key["id"],
            "name": "  ColdCard  ",
            "address_path": ADDRESS_PATH,
        }) as response:
            self.assertEqual(response.status, 200)
            body = json.load(response)

        self.assertEqual(body["keys"][0]["name"], "ColdCard")
        self.assertEqual(self.key_profiles()[0]["name"], "ColdCard")
        # The type is locked (section 25.2).
        self.assertEqual(self.key_profiles()[0]["type"], "hardware")

    def test_the_address_path_can_be_changed_until_the_key_has_a_check(self):
        key = self.key_profiles()[0]

        with self.post_key_settings({
            "key_id": key["id"],
            "name": key["name"],
            "address_path": "m/48'/7'/0'/2'",
        }) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual(self.key_profiles()[0]["address_path"], "m/48'/7'/0'/2'")

    def test_the_address_path_is_locked_after_the_first_check(self):
        key = self.key_profiles()[0]
        self.post_health_check(sample_payload(key))

        # A different path is refused, while the stored one may be sent again
        # (section 25.1).
        self.assert_rejected_at("/api/settings/keys", {
            "key_id": key["id"],
            "name": key["name"],
            "address_path": "m/48'/8'/0'/2'",
        }, status=409)

        with self.post_key_settings({
            "key_id": key["id"],
            "name": "ColdCard",
            "address_path": ADDRESS_PATH,
        }) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual(self.key_profiles()[0]["name"], "ColdCard")
        self.assertEqual(self.key_profiles()[0]["address_path"], ADDRESS_PATH)

    def test_a_path_that_another_key_already_has_is_rejected(self):
        # The settings answer a duplicate path with 409, and the message names
        # the key that has it (section 26.2).
        key = self.key_profiles()[1]

        for value in (ADDRESS_PATH, f"  {ADDRESS_PATH}  ", ADDRESS_PATH.upper()):
            self.assert_rejected_at("/api/settings/keys", {
                "key_id": key["id"],
                "name": key["name"],
                "address_path": value,
            }, status=409)

        self.assertEqual(self.key_profiles()[1]["address_path"], SECOND_ADDRESS_PATH)

    def test_a_name_that_repeats_another_key_is_rejected(self):
        key = self.key_profiles()[0]

        for name in ("Nunchuk", "nunchuk"):
            self.assert_rejected_at("/api/settings/keys", {
                "key_id": key["id"],
                "name": name,
                "address_path": ADDRESS_PATH,
            })

    def test_an_unknown_key_or_a_missing_path_is_rejected(self):
        key = self.key_profiles()[0]

        for payload in (
            {"key_id": 999, "name": "ColdCard", "address_path": ADDRESS_PATH},
            {"key_id": key["id"], "name": "ColdCard", "address_path": ""},
            {"key_id": key["id"], "name": "", "address_path": ADDRESS_PATH},
        ):
            self.assert_rejected_at("/api/settings/keys", payload)

    def test_the_wallet_software_list_is_stored_whole(self):
        with self.post_wallet_software(["Sparrow Wallet", "BlueWallet"]) as response:
            self.assertEqual(response.status, 200)
            body = json.load(response)

        self.assertEqual(body["wallet_software"], ["Sparrow Wallet", "BlueWallet"])
        self.assertEqual(body["acknowledged"], [])
        self.assertEqual(self.get_settings()["wallet_software"], ["Sparrow Wallet", "BlueWallet"])

        # Replacing the list removes the entries that are not sent again.
        with self.post_wallet_software(["BlueWallet"]) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual(self.get_settings()["wallet_software"], ["BlueWallet"])

    def test_the_settings_list_completes_the_wallet_software_choices(self):
        key = self.key_profiles()[0]

        with self.post_wallet_software(["BlueWallet"]) as response:
            self.assertEqual(response.status, 200)

        # A name from the settings list is a choice, and a name that is in
        # neither the list nor a cloud key is not (section 25.4).
        saved_id = self.post_health_check(sample_payload(key, wallet_software="BlueWallet"))
        self.assertEqual(self.get_record(saved_id)["wallet_software"], "BlueWallet")

        self.assert_rejected(sample_payload(key, wallet_software="Sparrow Wallet"))

    def test_a_removed_software_name_still_renders_in_the_history(self):
        key = self.key_profiles()[0]
        with self.post_wallet_software(["BlueWallet"]) as response:
            self.assertEqual(response.status, 200)
        saved_id = self.post_health_check(sample_payload(key, wallet_software="BlueWallet"))

        with self.post_wallet_software(["Sparrow Wallet"]) as response:
            self.assertEqual(response.status, 200)

        # The selected software is kept as free text, so an earlier check is not
        # changed by removing the name (sections 25.4 and 26.7).
        self.assertEqual(self.get_record(saved_id)["wallet_software"], "BlueWallet")

    def test_removing_the_failing_software_closes_its_alert(self):
        key = self.key_profiles()[0]
        with self.post_wallet_software(["Sparrow Wallet", "BlueWallet"]) as response:
            self.assertEqual(response.status, 200)

        payload = sample_payload(key, wallet_software="BlueWallet")
        payload["software_compatibility_status"] = "PROBLEM"
        saved_id = self.post_health_check(payload)
        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["software_incompatible"])
        self.assertEqual(alerts[0]["source"], "BlueWallet")

        # Removing the failing software is what closes the alert (section 26.7).
        with self.post_wallet_software(["Sparrow Wallet"]) as response:
            self.assertEqual(response.status, 200)
            body = json.load(response)

        self.assertEqual(
            body["acknowledged"],
            [{"code": "software_incompatible", "source": "BlueWallet"}],
        )
        self.assertEqual(self.get_alerts(), [])
        # The saved check is untouched.
        self.assertEqual(self.get_record(saved_id)["software_compatibility_status"], "PROBLEM")

    def test_removing_a_software_closes_a_software_named_security_alert(self):
        key = self.key_profiles()[0]
        with self.post_wallet_software(["Sparrow Wallet", "BlueWallet"]) as response:
            self.assertEqual(response.status, 200)

        payload = sample_payload(key, wallet_software="BlueWallet")
        for entry in payload["ai_security_checks"]:
            if entry["provider"] == "BlueWallet":
                entry["status"] = "VULNERABLE"
        self.post_health_check(payload)
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["security_vulnerable"])

        with self.post_wallet_software(["Sparrow Wallet"]) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual(self.get_alerts(), [])

    def test_removing_a_software_leaves_the_other_alerts_alone(self):
        key = self.key_profiles()[0]
        with self.post_wallet_software(["Sparrow Wallet", "BlueWallet"]) as response:
            self.assertEqual(response.status, 200)

        payload = sample_payload(key, wallet_software="BlueWallet")
        payload["software_compatibility_status"] = "PROBLEM"
        self.post_health_check(payload)
        self.post_health_check(unavailable_payload(self.key_profiles()[1]))

        with self.post_wallet_software(["Sparrow Wallet"]) as response:
            self.assertEqual(response.status, 200)

        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["key_unavailable"])

    def test_the_only_software_entry_cannot_be_removed(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["software_compatibility_status"] = "PROBLEM"
        self.post_health_check(payload)
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["software_incompatible"])

        # The list may never be empty, so a single entry has to be replaced
        # first, and the alert stays open (sections 25.4 and 26.7).
        self.assert_rejected_at("/api/settings/wallet-software", {"wallet_software": []})

        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["software_incompatible"])

    def test_an_empty_list_or_a_cloud_key_name_is_rejected(self):
        for names in ([], ["   "], ["Nunchuk"], ["nunchuk"], ["Sparrow Wallet", "sparrow wallet"]):
            self.assert_rejected_at(
                "/api/settings/wallet-software", {"wallet_software": names}
            )

    def test_a_missing_software_list_is_rejected(self):
        for payload in ({}, {"wallet_software": None}, {"wallet_software": "Sparrow Wallet"}):
            self.assert_rejected_at("/api/settings/wallet-software", payload)


class RotationApiTests(ServerTestCase):
    """A rotation replaces one key and closes the alerts it raised (sections 25.2 and 26.3)."""

    def setUp(self):
        super().setUp()
        self.store_setup()

    def test_a_rotation_keeps_the_name_and_records_the_new_path(self):
        key = self.key_profiles()[0]

        body = self.rotate(key["id"])

        self.assertEqual(body["acknowledged"], [])
        stored = self.key_profiles()[0]
        self.assertEqual(stored["name"], key["name"])
        self.assertEqual(stored["type"], key["type"])
        self.assertEqual(stored["address_path"], self.rotation_path(key["id"]))

    def test_a_rotation_changes_the_name(self):
        key = self.key_profiles()[1]

        self.rotate(key["id"], keep_name=False, name="  Replacement  ")

        stored = self.key_profiles()[1]
        self.assertEqual(stored["name"], "Replacement")
        self.assertEqual(stored["address_path"], self.rotation_path(key["id"]))

    def test_a_rotation_needs_the_replacement_confirmation(self):
        key = self.key_profiles()[0]

        for value in (None, False, 1, "yes"):
            self.assert_rejected_at(f"/api/keys/{key['id']}/rotate", {
                "replaced": value,
                "keep_name": True,
                "address_path": self.rotation_path(key["id"]),
            })

    def test_a_rotation_requires_a_new_address_path(self):
        key = self.key_profiles()[0]
        path = f"/api/keys/{key['id']}/rotate"

        # The key is a new one, so an empty path, the stored path, and the path of
        # another key are all refused (sections 26.2 and 26.3).
        for value in (None, "", "   ", ADDRESS_PATH, SECOND_ADDRESS_PATH):
            self.assert_rejected_at(path, {
                "replaced": True,
                "keep_name": True,
                "address_path": value,
            })

        self.assert_rejected_at(path, {"replaced": True, "keep_name": True})
        self.assertEqual(self.key_profiles()[0]["address_path"], ADDRESS_PATH)

    def test_a_rotation_keeps_the_new_path_after_it_is_stored(self):
        key = self.key_profiles()[0]
        self.rotate(key["id"], address_path="m/48'/5'/0'/2'")

        self.assertEqual(self.key_profiles()[0]["address_path"], "m/48'/5'/0'/2'")

        # The new path is the identity of the key now, so it may not be recorded
        # as the next rotation either.
        self.assert_rejected_at(f"/api/keys/{key['id']}/rotate", {
            "replaced": True,
            "keep_name": True,
            "address_path": "m/48'/5'/0'/2'",
        })

    def test_a_rotation_of_an_unknown_key_is_rejected(self):
        self.assert_rejected_at("/api/keys/999/rotate", {
            "replaced": True,
            "keep_name": True,
            "address_path": self.rotation_path(1),
        }, status=404)

    def test_a_rotation_closes_the_alerts_of_its_key(self):
        key = self.key_profiles()[1]
        self.post_health_check(unavailable_payload(key))
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["key_unavailable"])

        body = self.rotate(key["id"])

        self.assertEqual(
            body["acknowledged"],
            [{"code": "key_unavailable", "source": "Key 2: Blockstream Jade"}],
        )
        self.assertEqual(self.get_alerts(), [])

    def test_a_rotation_leaves_the_other_keys_alone(self):
        other = self.key_profiles()[1]
        self.post_health_check(unavailable_payload(other))

        self.rotate(self.key_profiles()[0]["id"])

        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["key_unavailable"])
        self.assertIn("Key 2", alerts[0]["source"])

    def test_a_rotation_does_not_close_a_software_alert(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["software_compatibility_status"] = "PROBLEM"
        self.post_health_check(payload)
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["software_incompatible"])

        body = self.rotate(key["id"])

        self.assertEqual(body["acknowledged"], [])
        self.assertEqual([alert["code"] for alert in self.get_alerts()], ["software_incompatible"])

    def test_a_rotation_does_not_change_an_earlier_check(self):
        key = self.key_profiles()[1]
        saved_id = self.post_health_check(unavailable_payload(key))
        before = self.get_record(saved_id)

        self.rotate(key["id"], keep_name=False, name="Replacement")

        after = self.get_record(saved_id)
        self.assertEqual(len(self.get_health_checks()), 1)
        self.assertEqual(after["key_checks"][0]["available"], before["key_checks"][0]["available"])
        self.assertEqual(after["key_checks"][0]["comments"], before["key_checks"][0]["comments"])
        self.assertEqual(after["key_checks"][0]["key_number"], 2)
        # The name shown is the name the key has now (section 25.2).
        self.assertEqual(after["key_checks"][0]["name"], "Replacement")


class AcknowledgementApiTests(ServerTestCase):
    """An alert is closed by the action that belongs to it (sections 25.3 and 26.4)."""

    def setUp(self):
        super().setUp()
        self.store_setup()

    def test_an_acknowledged_alert_disappears(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["contact_info_verified"] = "Needs external update"
        saved_id = self.post_health_check(payload)
        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["contact_info_unconfirmed"])

        with self.post_acknowledgement({
            "code": alerts[0]["code"],
            "source": alerts[0]["source"],
            "action": "contact_updated",
        }) as response:
            self.assertEqual(response.status, 201)
            body = json.load(response)

        self.assertEqual(body["action"], "contact_updated")
        self.assertEqual(self.get_alerts(), [])
        # The saved check itself is untouched.
        self.assertEqual(self.get_record(saved_id)["contact_info_verified"], "Needs external update")

    def test_a_newer_check_raises_the_alert_again(self):
        key = self.key_profiles()[0]
        older = sample_payload(key)
        older["checked_at"] = "2026-10-01"
        older["contact_info_verified"] = "Needs external update"
        self.post_health_check(older)
        alerts = self.get_alerts()

        with self.post_acknowledgement({
            "code": alerts[0]["code"],
            "source": alerts[0]["source"],
            "action": "contact_updated",
        }) as response:
            self.assertEqual(response.status, 201)

        self.assertEqual(self.get_alerts(), [])

        newer = sample_payload(key)
        newer["checked_at"] = "2027-10-01"
        newer["contact_info_verified"] = "Needs external update"
        self.post_health_check(newer)

        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["contact_info_unconfirmed"])
        self.assertEqual(alerts[0]["checked_at"], "2027-10-01")

    def test_an_unknown_alert_is_rejected(self):
        self.post_health_check(unavailable_payload(self.key_profiles()[1]))

        for payload in (
            {"code": "key_unavailable", "source": "Key 3: Nunchuk", "action": "replace_hardware"},
            {"code": "address_path_mismatch", "source": "Key 2: Blockstream Jade", "action": "replace_hardware"},
        ):
            self.assert_rejected_at("/api/alerts/acknowledge", payload, status=404)

    def test_an_unknown_code_or_an_unknown_action_is_rejected(self):
        self.post_health_check(unavailable_payload(self.key_profiles()[1]))
        source = self.get_alerts()[0]["source"]

        for payload in (
            {"code": "cloud_provider_problem", "source": source, "action": "replace_hardware"},
            {"code": "address_verification_failed", "source": source, "action": "replace_hardware"},
            {"code": "key_unavailable", "source": source, "action": ""},
            {"code": "key_unavailable", "source": source},
            {"code": "key_unavailable", "source": "", "action": "replace_hardware"},
            # A rotation has its own endpoint, and the removed generic
            # acknowledgement is gone (sections 26.3 and 26.4).
            {"code": "key_unavailable", "source": source, "action": "rotate"},
            {"code": "key_unavailable", "source": source, "action": "acknowledge"},
        ):
            self.assert_rejected_at("/api/alerts/acknowledge", payload)

    def test_an_action_that_does_not_belong_to_the_alert_is_rejected(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["key_check"]["hardware_works"] = 0
        self.post_health_check(payload)
        alert = self.get_alerts()[0]
        self.assertEqual(alert["actions"], ["rotate", "replace_hardware"])

        # An action the alert does not offer cannot close it (section 26.4).
        for action in ("ignore", "remove_software", "contact_updated"):
            self.assert_rejected_at("/api/alerts/acknowledge", {
                "code": alert["code"],
                "source": alert["source"],
                "action": action,
            })

        self.assertEqual([entry["code"] for entry in self.get_alerts()], ["hardware_failure"])

    def test_a_software_alert_can_only_be_removed_or_ignored(self):
        key = self.key_profiles()[0]
        payload = sample_payload(key)
        payload["software_compatibility_status"] = "PROBLEM"
        self.post_health_check(payload)
        alert = self.get_alerts()[0]
        self.assertEqual(alert["actions"], ["remove_software"])

        for action in ("replace_hardware", "contact_updated"):
            self.assert_rejected_at("/api/alerts/acknowledge", {
                "code": alert["code"],
                "source": alert["source"],
                "action": action,
            })

        with self.post_acknowledgement({
            "code": alert["code"],
            "source": alert["source"],
            "action": "remove_software",
        }) as response:
            self.assertEqual(response.status, 201)

        self.assertEqual(self.get_alerts(), [])

    def test_an_informational_alert_can_be_closed_too(self):
        payload = sample_payload(self.key_profiles()[0])
        payload["contact_info_verified"] = "Needs external update"
        self.post_health_check(payload)
        alerts = self.get_alerts()
        self.assertEqual([alert["code"] for alert in alerts], ["contact_info_unconfirmed"])

        with self.post_acknowledgement({
            "code": alerts[0]["code"],
            "source": alerts[0]["source"],
            "action": "contact_updated",
        }) as response:
            self.assertEqual(response.status, 201)

        self.assertEqual(self.get_alerts(), [])


class KeySetupApiTests(ServerTestCase):
    """The endpoints on a new database, before the key setup is stored."""

    def test_setup_api_reports_an_unconfigured_database(self):
        setup = self.get_setup()

        self.assertFalse(setup["configured"])
        self.assertEqual(setup["keys"], [])

    def test_the_key_api_is_empty_before_the_setup(self):
        self.assertEqual(self.key_profiles(), [])

    def test_the_key_setup_can_be_stored_once(self):
        with self.post_setup({"keys": DEFAULT_SETUP}) as response:
            self.assertEqual(response.status, 201)
            body = json.load(response)

        self.assertTrue(body["configured"])
        self.assertEqual([key["name"] for key in body["keys"]],
                         ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        self.assertEqual(
            [key["address_path"] for key in body["keys"]],
            [ADDRESS_PATH, SECOND_ADDRESS_PATH, THIRD_ADDRESS_PATH],
        )
        self.assertTrue(self.get_setup()["configured"])
        self.assertEqual(len(self.key_profiles()), 3)

    def test_a_setup_with_all_three_keys_as_cloud_keys_is_accepted(self):
        payload = {"keys": [
            {"key_number": 1, "name": "Provider one", "type": "cloud", "address_path": ADDRESS_PATH},
            {"key_number": 2, "name": "Provider two", "type": "cloud", "address_path": SECOND_ADDRESS_PATH},
            {"key_number": 3, "name": "Provider three", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
        ]}

        with self.post_setup(payload) as response:
            self.assertEqual(response.status, 201)

        self.assertEqual([key["type"] for key in self.key_profiles()], ["cloud"] * 3)

    def test_a_duplicate_name_is_rejected(self):
        payload = {"keys": [
            {"key_number": 1, "name": "Jade", "type": "hardware", "address_path": ADDRESS_PATH},
            {"key_number": 2, "name": "jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
            {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
        ]}

        self.assert_setup_rejected(payload)
        self.assertFalse(self.get_setup()["configured"])

    def test_a_duplicate_address_path_is_rejected(self):
        # Every key needs its own path, and the message names the key that
        # already has it (section 26.2).
        for value in (ADDRESS_PATH, f"  {ADDRESS_PATH}  ", ADDRESS_PATH.upper()):
            payload = {"keys": [
                {"key_number": 1, "name": "ColdCard", "type": "hardware", "address_path": ADDRESS_PATH},
                {"key_number": 2, "name": "Jade", "type": "hardware", "address_path": value},
                {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
            ]}
            self.assert_setup_rejected(payload)

        self.assertFalse(self.get_setup()["configured"])

    def test_an_empty_name_is_rejected(self):
        payload = {"keys": [
            {"key_number": 1, "name": "   ", "type": "hardware", "address_path": ADDRESS_PATH},
            {"key_number": 2, "name": "Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
            {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
        ]}

        self.assert_setup_rejected(payload)

    def test_a_missing_or_empty_address_path_is_rejected(self):
        # The setup records the address path of every key (section 25.1).
        for value in (None, "", "   "):
            payload = {"keys": [
                {"key_number": 1, "name": "ColdCard", "type": "hardware", "address_path": value},
                {"key_number": 2, "name": "Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
                {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
            ]}
            self.assert_setup_rejected(payload)

        payload = {"keys": [
            {"key_number": 1, "name": "ColdCard", "type": "hardware"},
            {"key_number": 2, "name": "Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
            {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
        ]}
        self.assert_setup_rejected(payload)

    def test_the_wrong_number_of_keys_is_rejected(self):
        self.assert_setup_rejected({"keys": DEFAULT_SETUP[:2]})
        self.assert_setup_rejected({"keys": DEFAULT_SETUP + [DEFAULT_SETUP[0]]})
        self.assert_setup_rejected({})

    def test_an_unknown_type_is_rejected(self):
        payload = {"keys": [
            {"key_number": 1, "name": "ColdCard", "type": "usb", "address_path": ADDRESS_PATH},
            {"key_number": 2, "name": "Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
            {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
        ]}

        self.assert_setup_rejected(payload)

    def test_a_health_check_cannot_be_posted_before_the_setup(self):
        key = {"id": 1, "key_number": 1, "name": "SeedSigner", "type": "hardware",
               "address_path": ADDRESS_PATH}

        self.assert_rejected(sample_payload(key))

    def test_the_key_status_is_empty_before_the_setup(self):
        with urlopen(f"{self.base_url}/api/key-status") as response:
            self.assertEqual(json.load(response), [])

    def test_the_settings_report_an_empty_setup_and_the_software_list(self):
        settings = self.get_settings()

        self.assertEqual(settings["keys"], [])
        # The list a new database starts with is there before the keys are
        # configured (section 25.4).
        self.assertEqual(settings["wallet_software"], ["Sparrow Wallet"])

    def test_a_key_cannot_be_rotated_before_the_setup(self):
        self.assert_rejected_at("/api/keys/1/rotate", {
            "replaced": True,
            "keep_name": True,
            "address_path": self.rotation_path(1),
        }, status=404)


if __name__ == "__main__":
    unittest.main()
