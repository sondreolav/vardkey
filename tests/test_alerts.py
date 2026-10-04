"""Tests for the follow-up alerts derived from saved health checks."""

import unittest

from alerts import (
    ACKNOWLEDGE,
    ALERT_CODES,
    ROTATE,
    build_alerts,
    collect_alerts,
    rotation_alert_targets,
)


def clean_record(key_number=1, name="SeedSigner", key_type="hardware"):
    """Return a saved check for one key whose results need no follow-up.

    The provider list is fixed, so a test that needs another provider has to
    replace one of the entries itself.
    """
    entry = {
        "key_id": key_number,
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
        "contact_info_verified": "Confirmed current",
        "key_checks": [entry],
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


def key_profile(key_number=1, name="SeedSigner"):
    """Return the configured key profile a record belongs to."""
    return {"id": key_number, "key_number": key_number, "name": name}


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

    def test_an_unavailable_cloud_key_gets_the_same_alert(self):
        # The cloud results are gone, so one message covers every key
        # (sections 25.3 and 25.6).
        cloud = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        cloud["key_checks"][0]["available"] = 0
        hardware = clean_record()
        hardware["key_checks"][0]["available"] = 0

        alerts = build_alerts(cloud)

        self.assertEqual(self.codes(cloud), ["key_unavailable"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Key 3: Nunchuk")
        self.assertEqual(alerts[0]["message"], build_alerts(hardware)[0]["message"])

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

    def test_a_mismatched_address_path_asks_for_a_replacement(self):
        # The recorded path does not match the key, so the key could not be
        # checked (section 25.1).
        record = clean_record()
        record["key_checks"][0]["address_path_verified"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["address_path_mismatch"])
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[0]["source"], "Key 1: SeedSigner")
        self.assertIn("does not match this key", alerts[0]["message"])
        self.assertIn("Replace the key", alerts[0]["message"])
        self.assertEqual(alerts[0]["actions"], [ROTATE])

    def test_a_mismatch_is_not_merged_with_a_real_unavailable_alert(self):
        # The mismatch has its own code, so the two are never merged even though
        # they share a source (section 25.1). Both are critical and come from
        # checks with the same date, so the newest check is listed first.
        mismatch = dated_record(1, "2026-10-01")
        mismatch["key_checks"][0]["address_path_verified"] = "PROBLEM"
        unavailable = dated_record(2, "2026-10-01")
        unavailable["key_checks"][0]["available"] = 0

        alerts = collect_alerts([mismatch, unavailable])

        self.assertEqual(
            sorted(alert["code"] for alert in alerts),
            ["address_path_mismatch", "key_unavailable"],
        )
        self.assertEqual({alert["source"] for alert in alerts}, {"Key 1: SeedSigner"})

    def test_incompatible_software_suggests_an_alternative(self):
        record = clean_record()
        record["software_compatibility_status"] = "PROBLEM"

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["software_incompatible"])
        self.assertEqual(alerts[0]["source"], "Software compatibility")

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
            "address_path_verified": None,
        })

        self.assertEqual(build_alerts(record), [])

    def test_the_removed_alert_rules_cannot_be_triggered(self):
        # The two cloud fields and the old address verification rule are gone
        # (sections 25.1 and 25.3), so a legacy record that carries them raises
        # nothing.
        record = clean_record()
        record["key_checks"][0].update({
            "cloud_health_status": "PROBLEM",
            "cloud_provider_operational": 0,
            "address_verified": 0,
        })

        self.assertEqual(build_alerts(record), [])
        self.assertNotIn("cloud_provider_problem", ALERT_CODES)
        self.assertNotIn("address_verification_failed", ALERT_CODES)

    def test_the_alert_codes_are_the_current_ones(self):
        self.assertEqual(
            ALERT_CODES,
            frozenset({
                "key_unavailable",
                "address_path_mismatch",
                "hardware_failure",
                "seed_backup_problem",
                "software_incompatible",
                "security_vulnerable",
                "security_compromised",
                "contact_info_unconfirmed",
            }),
        )

    def test_critical_alerts_are_listed_before_informational_ones(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["contact_info_verified"] = "Needs external update"
        record["ai_security_checks"][1]["status"] = "VULNERABLE"
        record["key_checks"][0]["available"] = 0

        severities = [alert["severity"] for alert in build_alerts(record)]

        self.assertEqual(severities, ["critical", "critical", "info"])
        self.assertEqual(
            self.codes(record),
            ["key_unavailable", "security_vulnerable", "contact_info_unconfirmed"],
        )

    def test_every_alert_names_the_actions_that_close_it(self):
        record = clean_record()
        record["key_checks"][0]["available"] = 0
        record["software_compatibility_status"] = "PROBLEM"
        record["contact_info_verified"] = "Needs external update"

        alerts = build_alerts(record)

        self.assertEqual(
            {alert["code"]: alert["actions"] for alert in alerts},
            {
                "key_unavailable": [ROTATE],
                "software_incompatible": [ACKNOWLEDGE],
                "contact_info_unconfirmed": [ACKNOWLEDGE],
            },
        )

    def test_a_hardware_failure_may_be_rotated_or_closed(self):
        record = clean_record()
        record["key_checks"][0]["hardware_works"] = 0

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["actions"], [ROTATE, ACKNOWLEDGE])

    def test_a_key_alert_names_the_key_it_came_from(self):
        record = clean_record(key_number=2, name="Blockstream Jade")
        record["key_checks"][0]["available"] = 0

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["key_id"], 2)

    def test_a_security_alert_names_the_key_only_when_the_key_is_the_source(self):
        record = clean_record()
        # The provider "SeedSigner" is the key's own name, while "Sparrow Wallet"
        # is the software the key runs with (section 25.3).
        record["ai_security_checks"][0]["status"] = "COMPROMISED"
        record["ai_security_checks"][1]["status"] = "VULNERABLE"

        alerts = {alert["source"]: alert for alert in build_alerts(record)}

        # A compromised key must be replaced, so closing is not enough there.
        self.assertEqual(alerts["SeedSigner"]["key_id"], 1)
        self.assertEqual(alerts["SeedSigner"]["actions"], [ROTATE])
        # A problem in the software is not resolved by replacing the key.
        self.assertIsNone(alerts["Sparrow Wallet"]["key_id"])
        self.assertEqual(alerts["Sparrow Wallet"]["actions"], [ACKNOWLEDGE])

    def test_a_key_named_vulnerable_security_status_may_be_rotated_or_closed(self):
        record = clean_record()
        record["ai_security_checks"][0]["status"] = "VULNERABLE"

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["actions"], [ROTATE, ACKNOWLEDGE])


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

    def test_an_acknowledged_alert_is_hidden(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0

        acknowledgements = [{
            "code": "key_unavailable",
            "source": "Key 1: SeedSigner",
            "check_id": 1,
            "acknowledged_at": "2026-10-02T09:00:00",
        }]

        self.assertEqual(collect_alerts([record], acknowledgements), [])

    def test_a_newer_check_raises_an_acknowledged_alert_again(self):
        # The acknowledgement stores the check it closed, so a newer check, which
        # always has a higher id, raises the alert again (section 25.3).
        older = dated_record(1, "2026-10-01")
        older["key_checks"][0]["available"] = 0
        newer = dated_record(2, "2027-10-01")
        newer["key_checks"][0]["available"] = 0
        acknowledged = [{
            "code": "key_unavailable",
            "source": "Key 1: SeedSigner",
            "check_id": 1,
            "acknowledged_at": "2026-10-02T09:00:00",
        }]

        alerts = collect_alerts([newer, older], acknowledged)

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 2)

        acknowledged.append({
            "code": "key_unavailable",
            "source": "Key 1: SeedSigner",
            "check_id": 2,
            "acknowledged_at": "2027-10-02T09:00:00",
        })
        self.assertEqual(collect_alerts([newer, older], acknowledged), [])

    def test_an_acknowledgement_covers_one_code_and_source_only(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0
        record["contact_info_verified"] = "Needs external update"
        acknowledgements = [
            {
                "code": "key_unavailable",
                "source": "Key 2: Blockstream Jade",
                "check_id": 1,
                "acknowledged_at": "2026-10-02T09:00:00",
            },
            {
                "code": "contact_info_unconfirmed",
                "source": "Contact information",
                "check_id": 1,
                "acknowledged_at": "2026-10-02T09:00:00",
            },
        ]

        alerts = collect_alerts([record], acknowledgements)

        # The key alert has another source, so only the contact alert is hidden.
        self.assertEqual(self.codes(alerts), ["key_unavailable"])

    def test_an_acknowledgement_without_a_check_id_hides_nothing(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0
        acknowledgements = [{
            "code": "key_unavailable",
            "source": "Key 1: SeedSigner",
            "check_id": None,
            "acknowledged_at": "2026-10-02T09:00:00",
        }]

        self.assertEqual(self.codes(collect_alerts([record], acknowledgements)), ["key_unavailable"])

    def test_an_alert_survives_a_quiet_newer_check_until_it_is_closed(self):
        # Only the newest alert of a code and source pair is kept, so a newer
        # check that raises nothing does not clear an older alert. The alert is
        # closed by the user, either by acknowledging it or by rotating the key
        # (sections 21 and 25.3).
        older = dated_record(1, "2026-10-01")
        older["key_checks"][0]["available"] = 0
        newer = dated_record(2, "2027-10-01")

        alerts = collect_alerts([newer, older])

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 1)

        # Acknowledging it hides it, and it stays hidden because no newer check
        # raises it again.
        acknowledged = [{
            "code": "key_unavailable",
            "source": "Key 1: SeedSigner",
            "check_id": 1,
            "acknowledged_at": "2026-10-02T09:00:00",
        }]

        self.assertEqual(collect_alerts([newer, older], acknowledged), [])


class RotationAlertTargetsTests(unittest.TestCase):
    """A rotation closes the alerts its own key raised (section 25.3)."""

    def test_a_rotation_closes_the_key_alerts(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0

        targets = rotation_alert_targets([record], key_profile())

        self.assertEqual(targets, [("key_unavailable", "Key 1: SeedSigner")])

    def test_a_rotation_ignores_software_and_contact_alerts(self):
        record = dated_record(1, "2026-10-01")
        record["software_compatibility_status"] = "PROBLEM"
        record["contact_info_verified"] = "Needs external update"

        self.assertEqual(rotation_alert_targets([record], key_profile()), [])

    def test_a_rotation_closes_a_key_named_security_alert(self):
        record = dated_record(1, "2026-10-01")
        record["ai_security_checks"][0]["status"] = "COMPROMISED"

        targets = rotation_alert_targets([record], key_profile())

        self.assertEqual(targets, [("security_compromised", "SeedSigner")])

    def test_a_rotation_does_not_close_a_software_named_security_alert(self):
        # A problem in the software the key runs with is not resolved by
        # replacing the key (section 25.3).
        record = dated_record(1, "2026-10-01")
        record["ai_security_checks"][1]["status"] = "VULNERABLE"

        self.assertEqual(rotation_alert_targets([record], key_profile()), [])

    def test_a_rotation_ignores_the_checks_of_another_key(self):
        record = dated_record(1, "2026-10-01", key_number=2, name="Blockstream Jade")
        record["key_checks"][0]["available"] = 0

        self.assertEqual(rotation_alert_targets([record], key_profile()), [])

    def test_a_rotation_closes_every_alert_of_its_own_key_once(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["seed_backup_verified"] = "PROBLEM"
        record["key_checks"][0]["hardware_works"] = 0
        second = dated_record(2, "2026-10-01")
        second["key_checks"][0]["seed_backup_verified"] = "PROBLEM"

        targets = rotation_alert_targets([record, second], key_profile())

        self.assertEqual(
            targets,
            [
                ("hardware_failure", "Key 1: SeedSigner"),
                ("seed_backup_problem", "Key 1: SeedSigner"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
