"""Tests for the follow-up alerts derived from saved health checks."""

import unittest

from alerts import (
    ALERT_ACTIONS,
    ALERT_CODES,
    CONTACT_UPDATED,
    CRITICAL,
    IGNORE,
    REMOVE_SOFTWARE,
    REPLACE_HARDWARE,
    ROTATE,
    _alert,
    build_alerts,
    collect_alerts,
    rotation_alert_targets,
    software_alert_targets,
)


def clean_record(key_number=1, name="SeedSigner", key_type="hardware"):
    """Return a saved check for one key whose results need no follow-up.

    The provider list is fixed, so a test that needs another provider has to
    replace one of the entries itself. The software the check recorded is
    "Sparrow Wallet", so a software alert can name it (section 26.7).
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
        "wallet_software": "Sparrow Wallet",
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


def acknowledgement(code, source, key_id, check_id, at="2026-10-02T09:00:00"):
    """Return one stored acknowledgement, with the key it belongs to.

    The key id is stored with the acknowledgement, so an alert that belongs to a
    key is hidden by its key rather than by its source (section 27).
    """
    return {
        "code": code,
        "source": source,
        "key_id": key_id,
        "check_id": check_id,
        "acknowledged_at": at,
    }


# One change per alert rule, so the rule sweep below covers every code.
def _unavailable(record):
    record["key_checks"][0]["available"] = 0


def _mismatch(record):
    record["key_checks"][0]["address_path_verified"] = "PROBLEM"


def _hardware_failure(record):
    record["key_checks"][0]["hardware_works"] = 0


def _seed_backup(record):
    record["key_checks"][0]["seed_backup_verified"] = "PROBLEM"


def _software_incompatible(record):
    record["software_compatibility_status"] = "PROBLEM"


def _vulnerable_key(record):
    record["ai_security_checks"][0]["status"] = "VULNERABLE"


def _vulnerable_software(record):
    record["ai_security_checks"][1]["status"] = "VULNERABLE"


def _compromised_key(record):
    record["ai_security_checks"][0]["status"] = "COMPROMISED"


def _compromised_software(record):
    record["ai_security_checks"][1]["status"] = "COMPROMISED"


def _contact_unconfirmed(record):
    record["contact_info_verified"] = "Needs external update"


RULE_CASES = (
    ("key_unavailable", _unavailable),
    ("address_path_mismatch", _mismatch),
    ("hardware_failure", _hardware_failure),
    ("seed_backup_problem", _seed_backup),
    ("software_incompatible", _software_incompatible),
    ("security_vulnerable", _vulnerable_key),
    ("security_compromised", _compromised_key),
    ("contact_info_unconfirmed", _contact_unconfirmed),
)


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

    def test_incompatible_software_names_the_software_and_asks_for_its_removal(self):
        record = clean_record()
        _software_incompatible(record)

        alerts = build_alerts(record)

        self.assertEqual(self.codes(record), ["software_incompatible"])
        # The alert names the software that produced the result, so the settings
        # link and the removal point at the right entry (section 26.7).
        self.assertEqual(alerts[0]["source"], "Sparrow Wallet")
        self.assertEqual(alerts[0]["software"], "Sparrow Wallet")
        self.assertEqual(alerts[0]["actions"], [REMOVE_SOFTWARE])
        self.assertIn("settings", alerts[0]["message"])

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
        # The alert belongs to the checked key and names it, so it blocks that
        # key like every other key alert (section 27).
        self.assertEqual(alerts[0]["source"], "Key 1: SeedSigner")
        self.assertEqual(alerts[0]["key_id"], 1)
        self.assertEqual(alerts[0]["actions"], [CONTACT_UPDATED])
        self.assertIn("Key 1: SeedSigner", alerts[0]["message"])
        self.assertIn("external update", alerts[0]["message"])

    def test_a_contact_alert_for_another_key_names_that_key(self):
        record = clean_record(key_number=3, name="Nunchuk", key_type="cloud")
        record["contact_info_verified"] = "Needs external update"

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["source"], "Key 3: Nunchuk")
        self.assertEqual(alerts[0]["key_id"], 3)
        self.assertIn("Key 3: Nunchuk", alerts[0]["message"])

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
        self.assertIsNone(alerts["SeedSigner"]["software"])
        # A problem in the software is not resolved by replacing the key.
        self.assertIsNone(alerts["Sparrow Wallet"]["key_id"])
        self.assertEqual(alerts["Sparrow Wallet"]["software"], "Sparrow Wallet")


class AlertActionTests(unittest.TestCase):
    """Every alert code has its own closing actions (section 26.4)."""

    def test_the_agreed_actions_are_offered_for_each_code_and_source(self):
        cases = (
            ("key_unavailable", _unavailable, "Key 1: SeedSigner", [ROTATE]),
            ("address_path_mismatch", _mismatch, "Key 1: SeedSigner", [ROTATE]),
            ("hardware_failure", _hardware_failure, "Key 1: SeedSigner", [ROTATE, REPLACE_HARDWARE]),
            ("seed_backup_problem", _seed_backup, "Key 1: SeedSigner", [ROTATE]),
            ("software_incompatible", _software_incompatible, "Sparrow Wallet", [REMOVE_SOFTWARE]),
            ("security_vulnerable", _vulnerable_key, "SeedSigner", [ROTATE, IGNORE]),
            ("security_vulnerable", _vulnerable_software, "Sparrow Wallet", [REMOVE_SOFTWARE, IGNORE]),
            ("security_compromised", _compromised_key, "SeedSigner", [ROTATE]),
            ("security_compromised", _compromised_software, "Sparrow Wallet", [REMOVE_SOFTWARE]),
            ("contact_info_unconfirmed", _contact_unconfirmed, "Key 1: SeedSigner", [CONTACT_UPDATED]),
        )
        for code, change, source, actions in cases:
            record = clean_record()
            change(record)
            alerts = {alert["source"]: alert for alert in build_alerts(record)}

            self.assertIn(source, alerts, f"{code} did not raise an alert for {source}")
            self.assertEqual(alerts[source]["code"], code)
            self.assertEqual(alerts[source]["actions"], actions)

    def test_a_hardware_failure_is_rotated_or_replaced(self):
        # Replacing the hardware wallet keeps the key and the address path, so the
        # generic acknowledgement is gone (section 26.4).
        record = clean_record()
        _hardware_failure(record)

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["actions"], [ROTATE, REPLACE_HARDWARE])

    def test_a_key_named_vulnerable_security_status_may_be_rotated_or_ignored(self):
        record = clean_record()
        _vulnerable_key(record)

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["actions"], [ROTATE, IGNORE])

    def test_a_compromised_key_or_software_can_never_be_ignored(self):
        for change, source in (
            (_compromised_key, "SeedSigner"),
            (_compromised_software, "Sparrow Wallet"),
        ):
            record = clean_record()
            change(record)
            alert = {entry["source"]: entry for entry in build_alerts(record)}[source]

            self.assertNotIn(IGNORE, alert["actions"])

    def test_a_software_alert_without_a_recorded_name_offers_the_settings_only(self):
        # A saved check that predates the software column has no name to point at,
        # so the alert keeps a stable source and no removal target (section 26.7).
        record = clean_record()
        record["wallet_software"] = None
        _software_incompatible(record)

        alerts = build_alerts(record)

        self.assertEqual(alerts[0]["source"], "Software compatibility")
        self.assertIsNone(alerts[0]["software"])
        self.assertEqual(alerts[0]["actions"], [REMOVE_SOFTWARE])

    def test_a_cloud_key_software_asks_for_a_replacement_instead_of_a_removal(self):
        # A hardware key may run the software of a configured cloud key. That name
        # can never be removed from the settings, so the alert belongs to the
        # checked key and is closed by replacing the hardware (section 27).
        record = clean_record()
        record["wallet_software"] = "Nunchuk"
        _software_incompatible(record)

        alerts = build_alerts(record, cloud_names=("Nunchuk",))

        self.assertEqual([alert["code"] for alert in alerts], ["software_incompatible"])
        self.assertEqual(alerts[0]["key_id"], 1)
        self.assertEqual(alerts[0]["source"], "Key 1: SeedSigner")
        self.assertEqual(alerts[0]["actions"], [REPLACE_HARDWARE])
        # There is no settings entry to remove, so no software removal target is
        # named (section 27).
        self.assertIsNone(alerts[0]["software"])

    def test_a_settings_list_software_keeps_its_removal_form(self):
        record = clean_record()
        _software_incompatible(record)

        alerts = build_alerts(record, cloud_names=("Nunchuk",))

        self.assertEqual(alerts[0]["source"], "Sparrow Wallet")
        self.assertIsNone(alerts[0]["key_id"])
        self.assertEqual(alerts[0]["actions"], [REMOVE_SOFTWARE])


class AlertGuardTests(unittest.TestCase):
    """An alert without an action would lock a key with no way out (section 26.1)."""

    def test_an_alert_without_an_action_is_a_bug(self):
        with self.assertRaises(ValueError):
            _alert("hardware_failure", CRITICAL, "Key 1: SeedSigner", "message", ())

    def test_every_alert_rule_produces_at_least_one_action(self):
        covered = set()
        for code, change in RULE_CASES:
            record = clean_record()
            change(record)

            alerts = build_alerts(record)

            self.assertEqual([alert["code"] for alert in alerts], [code])
            for alert in alerts:
                self.assertTrue(alert["actions"], f"{alert['code']} offers no action")
                self.assertTrue(set(alert["actions"]) <= ALERT_ACTIONS)
            covered.add(code)

        # The sweep really covers every code the app can raise.
        self.assertEqual(covered, set(ALERT_CODES))


class SoftwareAlertTargetsTests(unittest.TestCase):
    """Removing a wallet software closes the alerts that software raised (section 26.7)."""

    def test_removing_the_failing_software_closes_its_alert(self):
        record = dated_record(1, "2026-10-01")
        _software_incompatible(record)

        targets = software_alert_targets([record], [], ["Sparrow Wallet"])

        self.assertEqual(targets, [("software_incompatible", "Sparrow Wallet", None)])

    def test_removing_another_software_closes_nothing(self):
        record = dated_record(1, "2026-10-01")
        _software_incompatible(record)

        self.assertEqual(software_alert_targets([record], [], ["BlueWallet"]), [])

    def test_the_name_comparison_ignores_case_and_spacing(self):
        record = dated_record(1, "2026-10-01")
        _software_incompatible(record)

        targets = software_alert_targets([record], [], ["  sparrow wallet  "])

        self.assertEqual(targets, [("software_incompatible", "Sparrow Wallet", None)])

    def test_removing_a_software_closes_a_software_named_security_alert(self):
        record = dated_record(1, "2026-10-01")
        _vulnerable_software(record)

        targets = software_alert_targets([record], [], ["Sparrow Wallet"])

        self.assertEqual(targets, [("security_vulnerable", "Sparrow Wallet", None)])

    def test_removing_a_software_does_not_close_a_key_alert(self):
        # A key alert is about the key, not about the software, even when the
        # names happen to be the same (sections 26.4 and 26.7).
        unavailable = dated_record(1, "2026-10-01")
        _unavailable(unavailable)
        vulnerable = dated_record(1, "2026-10-01")
        _vulnerable_key(vulnerable)

        self.assertEqual(software_alert_targets([unavailable], [], ["SeedSigner"]), [])
        self.assertEqual(software_alert_targets([vulnerable], [], ["SeedSigner"]), [])

    def test_removing_a_cloud_key_name_does_not_close_the_replacement_alert(self):
        # A cloud key name is refused by the settings, so it can never be removed;
        # the alert offers the replacement action instead (section 27).
        record = dated_record(1, "2026-10-01")
        record["wallet_software"] = "Nunchuk"
        _software_incompatible(record)

        targets = software_alert_targets([record], [], ["Nunchuk"], ("Nunchuk",))

        self.assertEqual(targets, [])

    def test_an_acknowledged_software_alert_is_not_returned_again(self):
        record = dated_record(1, "2026-10-01")
        _software_incompatible(record)
        acknowledgements = [acknowledgement(
            "software_incompatible", "Sparrow Wallet", None, 1
        )]

        targets = software_alert_targets([record], acknowledgements, ["Sparrow Wallet"])

        self.assertEqual(targets, [])


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

        acknowledgements = [acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", 1, 1
        )]

        self.assertEqual(collect_alerts([record], acknowledgements), [])

    def test_a_newer_check_raises_an_acknowledged_alert_again(self):
        # The acknowledgement stores the check it closed, so a newer check, which
        # always has a higher id, raises the alert again (section 25.3).
        older = dated_record(1, "2026-10-01")
        older["key_checks"][0]["available"] = 0
        newer = dated_record(2, "2027-10-01")
        newer["key_checks"][0]["available"] = 0
        acknowledged = [acknowledgement("key_unavailable", "Key 1: SeedSigner", 1, 1)]

        alerts = collect_alerts([newer, older], acknowledged)

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 2)

        acknowledged.append(acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", 1, 2, "2027-10-02T09:00:00"
        ))
        self.assertEqual(collect_alerts([newer, older], acknowledged), [])

    def test_an_acknowledgement_covers_one_alert_only(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0
        record["contact_info_verified"] = "Needs external update"
        acknowledgements = [
            # The same code, but for another key, so it covers nothing here.
            acknowledgement("key_unavailable", "Key 2: Blockstream Jade", 2, 1),
            acknowledgement("contact_info_unconfirmed", "Key 1: SeedSigner", 1, 1),
        ]

        alerts = collect_alerts([record], acknowledgements)

        # Only the contact alert was closed; the key alert still stands.
        self.assertEqual(self.codes(alerts), ["key_unavailable"])

    def test_an_acknowledgement_with_a_key_id_hides_the_alert_after_a_rename(self):
        # The alert is identified by its key, so the name the key has now cannot
        # open the closed alert again (section 27). This is the bug a rotation
        # with a new name, or a plain rename, used to cause.
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0
        acknowledgements = [acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", 1, 1
        )]
        record["key_checks"][0]["name"] = "Replacement"

        self.assertEqual(collect_alerts([record], acknowledgements), [])

    def test_a_cloud_key_software_alert_is_hidden_by_its_key(self):
        # The cloud form of the alert carries the key, so it is hidden the same
        # way (section 27).
        record = dated_record(1, "2026-10-01")
        record["wallet_software"] = "Nunchuk"
        record["software_compatibility_status"] = "PROBLEM"
        acknowledgements = [acknowledgement(
            "software_incompatible", "Key 1: SeedSigner", 1, 1
        )]

        self.assertEqual(
            collect_alerts([record], acknowledgements, ("Nunchuk",)),
            [],
        )

    def test_an_acknowledgement_without_a_check_id_hides_nothing(self):
        record = dated_record(1, "2026-10-01")
        record["key_checks"][0]["available"] = 0
        acknowledgements = [acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", 1, None
        )]

        self.assertEqual(self.codes(collect_alerts([record], acknowledgements)), ["key_unavailable"])

    def test_an_alert_survives_a_quiet_newer_check_until_it_is_closed(self):
        # Only the newest alert of a code and source pair is kept, so a newer
        # check that raises nothing does not clear an older alert. The alert is
        # closed by the user, with the action that belongs to it (sections 21,
        # 25.3 and 26.4).
        older = dated_record(1, "2026-10-01")
        older["key_checks"][0]["available"] = 0
        newer = dated_record(2, "2027-10-01")

        alerts = collect_alerts([newer, older])

        self.assertEqual(self.codes(alerts), ["key_unavailable"])
        self.assertEqual(alerts[0]["check_id"], 1)

        # Closing it hides it, and it stays hidden because no newer check raises
        # it again.
        acknowledged = [acknowledgement("key_unavailable", "Key 1: SeedSigner", 1, 1)]

        self.assertEqual(collect_alerts([newer, older], acknowledged), [])


class RotationAlertTargetsTests(unittest.TestCase):
    """A rotation closes the alerts its own key raised (sections 25.3 and 26.4)."""

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
        # replacing the key (sections 25.3 and 26.4).
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
