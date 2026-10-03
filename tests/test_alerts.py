"""Tests for the follow-up alerts derived from saved health checks."""

import unittest

from alerts import build_alerts, collect_alerts


def clean_record(key_number=1, name="SeedSigner", key_type="hardware"):
    """Return a saved check for one key whose results need no follow-up.

    The provider list is fixed, so a test that needs another provider has to
    replace one of the entries itself.
    """
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
        entry.update({
            "hardware_works": None,
            "seed_backup_verified": None,
            "cloud_health_status": "OK",
            "cloud_provider_operational": 1,
        })
    return {
        "checked_at": "2026-10-01",
        "next_check_due": "2027-10-01",
        "software_compatibility_status": "OK",
        "contact_info_verified": "Confirmed current",
        "key_checks": [entry],
        "tool_checks": [
            {"product": "SeedSigner", "bip327_status": "NOT_ASSESSED", "slip39_status": "NOT_ASSESSED"},
            {"product": "Sparrow Wallet", "bip327_status": "NOT_ASSESSED", "slip39_status": "NOT_ASSESSED"},
        ],
        "ai_security_checks": [
            {"provider": "SeedSigner", "status": "SECURE"},
            {"provider": "Sparrow Wallet", "status": "SECURE"},
            {"provider": "Nunchuk", "status": "SECURE"},
        ],
    }


def dated_record(check_id, checked_at, **overrides):
    """Return a clean saved check carrying an id and a check date."""
    record = clean_record(**overrides)
    record["id"] = check_id
    record["checked_at"] = checked_at
    return record


class AlertTests(unittest.TestCase):
    def codes(self, record):
        return [alert["code"] for alert in build_alerts(record)]

    def test_a_check_without_problems_has_no_alerts(self):
        self.assertEqual(build_alerts(clean_record()), [])
        self.assertEqual(build_alerts(clean_record(3, "Nunchuk", "cloud")), [])

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

    def test_an_unavailable_cloud_key_gets_one_merged_alert(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["key_checks"][0].update({
            "available": 0,
            "cloud_health_status": "PROBLEM",
            "cloud_provider_operational": 0,
        })

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["key_unavailable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Key 3: Nunchuk")
        self.assertIn("cloud provider", alerts[0]["message"])
        self.assertIn("replace the key", alerts[0]["message"])

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

    def test_a_cloud_health_problem_must_be_followed_up(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["key_checks"][0]["cloud_health_status"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["cloud_provider_problem"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Key 3: Nunchuk")
        self.assertIn("cloud provider", alerts[0]["message"])

    def test_a_cloud_provider_outage_must_be_followed_up(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["key_checks"][0]["cloud_provider_operational"] = 0

        self.assertEqual(self.codes(record), ["cloud_provider_problem"])

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
        record["tool_checks"][0]["bip327_status"] = "YES"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["bip327_available"])
        self.assertEqual(alerts[0]["severity"], "info")
        self.assertEqual(alerts[0]["source"], "SeedSigner (BIP327)")

    def test_reported_slip39_support_is_an_informational_alert(self):
        record = clean_record()
        record["tool_checks"][1]["slip39_status"] = "YES"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["slip39_available"])
        self.assertEqual(alerts[0]["source"], "Sparrow Wallet (SLIP39)")

    def test_a_reported_lack_of_support_raises_no_alert(self):
        record = clean_record()
        record["tool_checks"][0]["bip327_status"] = "NO"
        record["tool_checks"][1]["slip39_status"] = "NO"

        self.assertEqual(build_alerts(record), [])

    def test_the_old_standards_values_raise_no_alert(self):
        record = clean_record()
        record["tool_checks"][0]["bip327_status"] = "OK"
        record["tool_checks"][1]["slip39_status"] = "PROBLEM"

        self.assertEqual(build_alerts(record), [])

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

    def test_contact_details_that_need_an_external_update_are_reported(self):
        record = clean_record()
        record["contact_info_verified"] = "Needs external update"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["contact_info_unconfirmed"])
        self.assertEqual(alerts[0]["severity"], "info")
        self.assertEqual(alerts[0]["source"], "Contact information")
        self.assertIn("external update", alerts[0]["message"])

    def test_the_old_contact_flag_raises_no_alert(self):
        # The 0/1 flag is migrated to a status, so a raw flag is never a result
        # (section 23.1).
        record = clean_record()
        record["contact_info_verified"] = 0

        self.assertEqual(build_alerts(record), [])

    def test_unassessed_values_are_not_treated_as_failures(self):
        record = clean_record()
        record["contact_info_verified"] = None
        record["software_compatibility_status"] = "NOT_ASSESSED"
        record["key_checks"][0].update({
            "available": None,
            "hardware_works": None,
            "seed_backup_verified": None,
            "cloud_health_status": None,
            "cloud_provider_operational": None,
            "address_path_verified": None,
        })

        self.assertEqual(build_alerts(record), [])

    def test_critical_alerts_are_listed_before_informational_ones(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["contact_info_verified"] = "Needs external update"
        record["tool_checks"][0]["bip327_status"] = "YES"
        record["ai_security_checks"][1]["status"] = "VULNERABLE"
        record["key_checks"][0]["available"] = 0

        severities = [alert["severity"] for alert in build_alerts(record)]

        self.assertEqual(severities, ["critical", "critical", "info", "info"])
        self.assertEqual(
            self.codes(record),
            ["key_unavailable", "security_vulnerable", "bip327_available", "contact_info_unconfirmed"],
        )


class CollectAlertsTests(unittest.TestCase):
    """The dashboard shows the merged alerts of every saved check (section 21)."""

    def codes(self, alerts):
        return [alert["code"] for alert in alerts]

    def test_no_saved_checks_give_no_alerts(self):
        self.assertEqual(collect_alerts([]), [])

    def test_every_alert_carries_its_check_id_and_date(self):
        record = dated_record(7, "2026-10-01")
        record["key_checks"][0]["available"] = 0

        alerts = collect_alerts([record])

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["check_id"], 7)
        self.assertEqual(alerts[0]["checked_at"], "2026-10-01")

    def test_alerts_from_every_saved_check_are_included(self):
        older = dated_record(1, "2025-10-01")
        older["ai_security_checks"][2]["status"] = "VULNERABLE"
        newer = dated_record(2, "2026-10-01", key_number=2, name="Blockstream Jade")
        newer["key_checks"][0]["hardware_works"] = 0

        alerts = collect_alerts([newer, older])

        self.assertEqual(self.codes(alerts), ["hardware_failure", "security_vulnerable"])
        self.assertEqual(alerts[1]["check_id"], 1)
        self.assertEqual(alerts[1]["checked_at"], "2025-10-01")

    def test_identical_alerts_are_merged_and_only_the_newest_is_kept(self):
        older = dated_record(1, "2025-10-01")
        older["key_checks"][0]["available"] = 0
        newer = dated_record(2, "2026-10-01")
        newer["key_checks"][0]["available"] = 0

        alerts = collect_alerts([newer, older])

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 2)
        self.assertEqual(alerts[0]["checked_at"], "2026-10-01")

    def test_alerts_with_the_same_code_but_another_source_are_kept(self):
        # The source of a security alert is the provider, not the key.
        first = dated_record(1, "2025-10-01")
        first["ai_security_checks"][0]["status"] = "VULNERABLE"
        second = dated_record(2, "2026-10-01", key_number=2, name="Blockstream Jade")
        second["ai_security_checks"][0] = {"provider": "Blockstream Jade", "status": "VULNERABLE"}

        alerts = collect_alerts([second, first])

        self.assertEqual(self.codes(alerts), ["security_vulnerable", "security_vulnerable"])
        self.assertEqual([alert["source"] for alert in alerts], ["Blockstream Jade", "SeedSigner"])
        self.assertEqual([alert["check_id"] for alert in alerts], [2, 1])

    def test_a_security_alert_for_the_same_provider_is_merged_across_keys(self):
        # Nunchuk is both the cloud key and wallet software, so its status is one
        # source, whatever key recorded it.
        first = dated_record(1, "2025-10-01")
        first["ai_security_checks"][2]["status"] = "VULNERABLE"
        second = dated_record(2, "2026-10-01", key_number=2, name="Blockstream Jade")
        second["ai_security_checks"][2]["status"] = "VULNERABLE"

        alerts = collect_alerts([second, first])

        self.assertEqual(self.codes(alerts), ["security_vulnerable"])
        self.assertEqual(alerts[0]["source"], "Nunchuk")
        self.assertEqual(alerts[0]["check_id"], 2)

    def test_critical_alerts_come_first_and_then_the_newest(self):
        older = dated_record(1, "2025-10-01")
        older["key_checks"][0]["hardware_works"] = 0
        newer = dated_record(2, "2026-10-01", key_number=2, name="Blockstream Jade")
        newer["key_checks"][0]["seed_backup_verified"] = "PROBLEM"
        newer["contact_info_verified"] = "Needs external update"

        alerts = collect_alerts([newer, older])

        self.assertEqual(
            [alert["severity"] for alert in alerts],
            ["critical", "critical", "info"],
        )
        self.assertEqual(
            self.codes(alerts),
            ["seed_backup_problem", "hardware_failure", "contact_info_unconfirmed"],
        )

    def test_a_check_without_problems_contributes_nothing(self):
        quiet = dated_record(1, "2026-10-01")
        noisy = dated_record(2, "2025-10-01")
        noisy["key_checks"][0]["available"] = 0

        alerts = collect_alerts([quiet, noisy])

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 2)


if __name__ == "__main__":
    unittest.main()
