"""Tests for the follow-up alerts derived from a saved health check."""

import unittest

from alerts import build_alerts


def clean_record(key_number=1, name="SeedSigner", key_type="hardware"):
    """Return a saved check for one key whose results need no follow-up."""
    entry = {
        "key_number": key_number,
        "name": name,
        "type": key_type,
        "available": 1,
        "hardware_works": 1,
        "seed_backup_verified": "OK",
        "address_path_verified": "OK",
    }
    if key_type == "cloud":
        entry.update({"hardware_works": None, "seed_backup_verified": None})
    return {
        "checked_at": "2026-10-01",
        "next_check_due": "2027-10-01",
        "software_compatibility_status": "OK",
        "contact_info_verified": 1,
        "key_checks": [entry],
        "tool_checks": [
            {"product": "SeedSigner", "bip327_status": "IKKJE_VURDERT", "slip39_status": "IKKJE_VURDERT"},
            {"product": "Sparrow Wallet", "bip327_status": "IKKJE_VURDERT", "slip39_status": "IKKJE_VURDERT"},
        ],
        "ai_security_checks": [
            {"provider": "SeedSigner", "status": "SECURE"},
            {"provider": "Sparrow Wallet", "status": "SECURE"},
            {"provider": "Nunchuk", "status": "SECURE"},
        ],
    }


class AlertTests(unittest.TestCase):
    def codes(self, record):
        return [alert["code"] for alert in build_alerts(record)]

    def test_a_check_without_problems_has_no_alerts(self):
        self.assertEqual(build_alerts(clean_record()), [])

    def test_an_unavailable_key_requires_immediate_follow_up(self):
        record = clean_record(key_number=2, name="Blockstream Jade")

        record["key_checks"][0]["available"] = 0

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["key_unavailable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Key 2: Blockstream Jade")
        self.assertIn("Replace the key", alerts[0]["message"])

    def test_an_unavailable_key_hides_the_other_results(self):
        record = clean_record()
        record["key_checks"][0].update({
            "available": 0,
            "hardware_works": 0,
            "seed_backup_verified": "PROBLEM",
            "address_path_verified": "PROBLEM",
        })

        self.assertEqual(self.codes(record), ["key_unavailable"])

    def test_a_hardware_failure_points_at_testing_the_backup_elsewhere(self):
        record = clean_record()
        record["key_checks"][0]["hardware_works"] = 0

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["hardware_failure"])
        self.assertIn("another compatible device", alerts[0]["message"])

    def test_a_damaged_seed_backup_points_at_protocol_3(self):
        record = clean_record()
        record["key_checks"][0]["seed_backup_verified"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["seed_backup_problem"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertIn("PROTOCOL 3", alerts[0]["message"])

    def test_a_failed_address_path_verification_points_at_bsms(self):
        record = clean_record()
        record["key_checks"][0]["address_path_verified"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["address_verification_failed"])
        self.assertIn("BSMS", alerts[0]["message"])

    def test_incompatible_software_suggests_an_alternative(self):
        record = clean_record()
        record["software_compatibility_status"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["software_incompatible"])
        self.assertEqual(alerts[0]["source"], "Software compatibility")

    def test_reported_bip327_support_is_an_informational_alert(self):
        record = clean_record()
        record["tool_checks"][0]["bip327_status"] = "OK"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["bip327_available"])
        self.assertEqual(alerts[0]["severity"], "info")
        self.assertEqual(alerts[0]["source"], "SeedSigner (BIP327)")

    def test_reported_slip39_support_is_an_informational_alert(self):
        record = clean_record()
        record["tool_checks"][1]["slip39_status"] = "OK"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["slip39_available"])
        self.assertEqual(alerts[0]["source"], "Sparrow Wallet (SLIP39)")

    def test_a_vulnerable_security_status_must_be_followed_up(self):
        record = clean_record()
        record["ai_security_checks"][2]["status"] = "VULNERABLE"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["security_vulnerable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Nunchuk")
        self.assertIn("VULNERABLE", alerts[0]["message"])

    def test_a_compromised_security_status_points_at_the_key_loss_procedure(self):
        record = clean_record()
        record["ai_security_checks"][0]["status"] = "COMPROMISED"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["security_compromised"])
        self.assertIn("key loss procedure", alerts[0]["message"])

    def test_a_norwegian_legacy_status_is_not_treated_as_a_failure(self):
        record = clean_record()
        record["ai_security_checks"][0]["status"] = "TRYGG"

        self.assertEqual(build_alerts(record), [])

    def test_unconfirmed_contact_information_is_reported(self):
        record = clean_record()
        record["contact_info_verified"] = 0

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["contact_info_unconfirmed"])
        self.assertEqual(alerts[0]["source"], "Contact information")

    def test_unassessed_values_are_not_treated_as_failures(self):
        record = clean_record()
        record["contact_info_verified"] = None
        record["software_compatibility_status"] = "IKKJE_VURDERT"
        record["key_checks"][0].update({
            "available": None,
            "hardware_works": None,
            "seed_backup_verified": None,
            "address_path_verified": None,
        })

        self.assertEqual(build_alerts(record), [])

    def test_critical_alerts_are_listed_before_informational_ones(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["contact_info_verified"] = 0
        record["tool_checks"][0]["bip327_status"] = "OK"
        record["ai_security_checks"][1]["status"] = "VULNERABLE"
        record["key_checks"][0]["available"] = 0

        severities = [alert["severity"] for alert in build_alerts(record)]

        self.assertEqual(severities, ["critical", "critical", "info", "info"])
        self.assertEqual(
            self.codes(record),
            ["key_unavailable", "security_vulnerable", "bip327_available", "contact_info_unconfirmed"],
        )


if __name__ == "__main__":
    unittest.main()
