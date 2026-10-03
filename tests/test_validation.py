"""Tests for payload validation."""

import unittest

from validation import (
    ValidationError,
    next_check_due,
    validate_health_check,
    validate_key_setup,
)


KEYS = (
    {"id": 1, "key_number": 1, "name": "SeedSigner", "type": "hardware"},
    {"id": 2, "key_number": 2, "name": "Blockstream Jade", "type": "hardware"},
    {"id": 3, "key_number": 3, "name": "Nunchuk", "type": "cloud"},
)
# A setup with the cloud key in the first slot and a renamed hardware key, to
# show that the type decides the checks and never the key number.
RENAMED_KEYS = (
    {"id": 1, "key_number": 1, "name": "Coinbase", "type": "cloud"},
    {"id": 2, "key_number": 2, "name": "ColdCard", "type": "hardware"},
    {"id": 3, "key_number": 3, "name": "Jade", "type": "hardware"},
)


def key_for(key_number, keys=KEYS):
    """Return the key profile with the given number."""
    return next(entry for entry in keys if entry["key_number"] == key_number)


def sample_payload(key_number=1, wallet_software=None, keys=KEYS):
    """Return a valid single-key payload for the given key number."""
    key = key_for(key_number, keys)
    if wallet_software is None:
        wallet_software = key["name"] if key["type"] == "cloud" else "Sparrow Wallet"
    labels = list(dict.fromkeys((key["name"], wallet_software)))
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
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": entry,
        "ai_security_checks": [
            {"provider": label, "status": "SECURE", "comments": ""} for label in labels
        ],
    }


def unavailable_payload(key_number=1, keys=KEYS):
    """Return the payload the form sends for a key that was not available."""
    key = key_for(key_number, keys)
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
        "contact_info_verified": "Needs external update",
        "comments": "Annual review",
        "key_check": entry,
        "ai_security_checks": [],
    }


class KeySetupTests(unittest.TestCase):
    def test_a_valid_setup_is_normalized_and_sorted(self):
        result = validate_key_setup({"keys": [
            {"key_number": 3, "name": "  Nunchuk  ", "type": "cloud"},
            {"key_number": 1, "name": "ColdCard", "type": "hardware"},
            {"key_number": 2, "name": "Jade", "type": "hardware"},
        ]})

        self.assertEqual(
            result,
            [
                {"key_number": 1, "name": "ColdCard", "type": "hardware"},
                {"key_number": 2, "name": "Jade", "type": "hardware"},
                {"key_number": 3, "name": "Nunchuk", "type": "cloud"},
            ],
        )

    def test_all_three_keys_may_be_cloud_keys(self):
        result = validate_key_setup({"keys": [
            {"key_number": 1, "name": "Provider one", "type": "cloud"},
            {"key_number": 2, "name": "Provider two", "type": "cloud"},
            {"key_number": 3, "name": "Provider three", "type": "cloud"},
        ]})

        self.assertEqual([entry["type"] for entry in result], ["cloud"] * 3)

    def test_duplicate_names_are_rejected_without_regard_to_case(self):
        for names in (("Jade", "Jade"), ("Jade", "jade"), ("Jade", " JADE ")):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    {"key_number": 1, "name": names[0], "type": "hardware"},
                    {"key_number": 2, "name": names[1], "type": "hardware"},
                    {"key_number": 3, "name": "Nunchuk", "type": "cloud"},
                ]})

    def test_an_empty_or_non_text_name_is_rejected(self):
        for name in ("", "   ", None, 12):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    {"key_number": 1, "name": name, "type": "hardware"},
                    {"key_number": 2, "name": "Jade", "type": "hardware"},
                    {"key_number": 3, "name": "Nunchuk", "type": "cloud"},
                ]})

    def test_an_over_long_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_key_setup({"keys": [
                {"key_number": 1, "name": "x" * 61, "type": "hardware"},
                {"key_number": 2, "name": "Jade", "type": "hardware"},
                {"key_number": 3, "name": "Nunchuk", "type": "cloud"},
            ]})

    def test_an_unknown_type_is_rejected(self):
        for key_type in ("", "hardware ", "cloudy", None):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    {"key_number": 1, "name": "ColdCard", "type": key_type},
                    {"key_number": 2, "name": "Jade", "type": "hardware"},
                    {"key_number": 3, "name": "Nunchuk", "type": "cloud"},
                ]})

    def test_a_repeated_or_unknown_key_number_is_rejected(self):
        for numbers in ((1, 1, 3), (1, 2, 4), (0, 2, 3), (1, 2, None), (1, 2, True)):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    {"key_number": numbers[0], "name": "ColdCard", "type": "hardware"},
                    {"key_number": numbers[1], "name": "Jade", "type": "hardware"},
                    {"key_number": numbers[2], "name": "Nunchuk", "type": "cloud"},
                ]})

    def test_the_wrong_number_of_keys_is_rejected(self):
        entry = {"key_number": 1, "name": "ColdCard", "type": "hardware"}
        for entries in ([], [entry], [entry, entry], [entry] * 4):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": entries})

    def test_a_missing_key_list_is_rejected(self):
        for payload in ({}, {"keys": None}, {"keys": "ColdCard"}, []):
            with self.assertRaises(ValidationError):
                validate_key_setup(payload)


class ValidationTests(unittest.TestCase):
    def test_valid_payload_is_normalized(self):
        result = validate_health_check(sample_payload(), KEYS)

        self.assertEqual(result["checked_at"], "2026-10-01")
        self.assertEqual(result["comments"], "Annual review")
        self.assertEqual(result["key_check"]["key_id"], 1)
        self.assertEqual(result["key_check"]["seed_backup_verified"], "OK")
        self.assertEqual(len(result["ai_security_checks"]), 2)

    def test_the_configured_name_is_the_product_label(self):
        result = validate_health_check(sample_payload(key_number=2, keys=RENAMED_KEYS), RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Sparrow Wallet")
        self.assertEqual(
            [entry["provider"] for entry in result["ai_security_checks"]],
            ["ColdCard", "Sparrow Wallet"],
        )

    def test_a_cloud_key_records_its_own_name_once(self):
        result = validate_health_check(sample_payload(key_number=1, keys=RENAMED_KEYS), RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Coinbase")
        self.assertEqual([entry["provider"] for entry in result["ai_security_checks"]], ["Coinbase"])
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])

    def test_a_hardware_key_may_use_a_cloud_key_name_as_its_software(self):
        payload = sample_payload(key_number=2, keys=RENAMED_KEYS)
        payload["wallet_software"] = "Coinbase"
        payload["ai_security_checks"] = [
            {"provider": label, "status": "SECURE", "comments": ""}
            for label in ("ColdCard", "Coinbase")
        ]

        result = validate_health_check(payload, RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Coinbase")
        self.assertEqual(
            [entry["provider"] for entry in result["ai_security_checks"]],
            ["ColdCard", "Coinbase"],
        )

    def test_a_hardware_key_name_is_not_a_wallet_software_choice(self):
        # "Jade" is a hardware key in this setup, so it is never software.
        payload = sample_payload(key_number=2, keys=RENAMED_KEYS)
        payload["wallet_software"] = "Jade"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, RENAMED_KEYS)

    def test_a_cloud_key_rejects_another_wallet_software(self):
        for value in ("Sparrow Wallet", "ColdCard"):
            payload = sample_payload(key_number=1, keys=RENAMED_KEYS)
            payload["wallet_software"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, RENAMED_KEYS)

    def test_next_check_due_is_derived_on_the_server(self):
        payload = sample_payload()
        payload["next_check_due"] = "1999-01-01"

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["next_check_due"], "2027-10-01")

    def test_leap_day_is_clamped_to_the_last_day_of_february(self):
        self.assertEqual(next_check_due("2028-02-29"), "2029-02-28")
        self.assertEqual(next_check_due("2026-02-28"), "2027-02-28")

    def test_blank_text_is_stored_as_null(self):
        payload = sample_payload()
        payload["software_version"] = "   "

        result = validate_health_check(payload, KEYS)

        self.assertIsNone(result["software_version"])

    def test_invalid_dates_are_rejected(self):
        for value in ("01-10-2026", "", None, "2026-13-01"):
            payload = sample_payload()
            payload["checked_at"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_unsupported_status_is_rejected(self):
        payload = sample_payload()
        payload["software_compatibility_status"] = "MAYBE"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_compatibility_status_requires_an_explicit_choice(self):
        # "not assessed" is no longer submittable for a new registration
        # (section 23.1).
        for value in ("", None, "NOT_ASSESSED", "IKKJE_VURDERT"):
            payload = sample_payload()
            payload["software_compatibility_status"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_compatibility_status_accepts_ok_and_problem(self):
        for value in ("OK", "PROBLEM"):
            payload = sample_payload()
            payload["software_compatibility_status"] = value
            self.assertEqual(
                validate_health_check(payload, KEYS)["software_compatibility_status"],
                value,
            )

    def test_cloud_key_compatibility_is_derived_from_availability(self):
        payload = sample_payload(key_number=3)
        payload["software_compatibility_status"] = "OK"
        self.assertEqual(
            validate_health_check(payload, KEYS)["software_compatibility_status"],
            "OK",
        )

        for value in ("PROBLEM", "NOT_ASSESSED"):
            payload = sample_payload(key_number=3)
            payload["software_compatibility_status"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_unavailable_key_keeps_the_derived_compatibility(self):
        payload = unavailable_payload()
        payload["software_compatibility_status"] = "NOT_ASSESSED"
        self.assertEqual(
            validate_health_check(payload, KEYS)["software_compatibility_status"],
            "NOT_ASSESSED",
        )

        payload["software_compatibility_status"] = "OK"
        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_not_assessed_is_only_the_derived_compatibility(self):
        # No other field offers or accepts NOT_ASSESSED (section 24.1). The
        # cloud health result is derived from availability, so it is only ever
        # OK or PROBLEM.
        payload = sample_payload(key_number=3)
        payload["key_check"]["cloud_health_status"] = "NOT_ASSESSED"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_hardware_works_is_required_for_an_available_hardware_key(self):
        # Hardware works requires an active Yes or No (section 24.1).
        for value in ("", None, "NOT_ASSESSED"):
            payload = sample_payload()
            payload["key_check"]["hardware_works"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

        payload = sample_payload()
        del payload["key_check"]["hardware_works"]
        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_hardware_works_accepts_yes_and_no(self):
        for value in (1, 0):
            payload = sample_payload()
            payload["key_check"]["hardware_works"] = value
            self.assertEqual(
                validate_health_check(payload, KEYS)["key_check"]["hardware_works"],
                value,
            )

    def test_contact_status_uses_the_two_stored_values(self):
        for value in ("Confirmed current", "Needs external update"):
            payload = sample_payload()
            payload["contact_info_verified"] = value
            self.assertEqual(
                validate_health_check(payload, KEYS)["contact_info_verified"], value
            )

    def test_contact_status_is_required_and_never_a_flag(self):
        # The confirmation is required, also when the key was not available,
        # because the question is still asked (section 24.1).
        for payload in (sample_payload(), unavailable_payload()):
            for value in ("", None):
                payload["contact_info_verified"] = value
                with self.assertRaises(ValidationError):
                    validate_health_check(payload, KEYS)
            del payload["contact_info_verified"]
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

        # The old 0/1 flag is no longer a valid value (section 23.1).
        for value in (1, 0, True, "yes"):
            payload = sample_payload()
            payload["contact_info_verified"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_security_status_must_use_the_four_english_values(self):
        for value in ("TRYGG", "UNKNOWN", ""):
            payload = sample_payload()
            payload["ai_security_checks"][0]["status"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_security_labels_are_specific_to_the_selected_key(self):
        payload = sample_payload(key_number=1)
        payload["ai_security_checks"] = [
            {"provider": "SeedSigner", "status": "SECURE", "comments": ""},
            {"provider": "Sparrow Wallet", "status": "SECURE", "comments": ""},
            {"provider": "Blockstream Jade", "status": "SECURE", "comments": ""},
        ]

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_unknown_key_id_is_rejected(self):
        payload = sample_payload()
        payload["key_check"]["key_id"] = 99

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_missing_key_check_is_rejected(self):
        payload = sample_payload()
        del payload["key_check"]

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_verification_status_is_required_when_the_key_is_available(self):
        for field in ("seed_backup_verified", "address_path_verified"):
            payload = sample_payload()
            payload["key_check"][field] = ""
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_verification_status_rejects_not_assessed(self):
        payload = sample_payload()
        payload["key_check"]["seed_backup_verified"] = "NOT_ASSESSED"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_availability_is_required(self):
        for value in ("", None):
            payload = sample_payload()
            payload["key_check"]["available"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_a_minimal_unavailable_payload_is_accepted(self):
        # The check date, the key check, and the contact confirmation are the
        # minimum, because the confirmation is required for every submission
        # (section 24.1).
        payload = {
            "checked_at": "2026-10-01",
            "contact_info_verified": "Needs external update",
            "key_check": {"key_id": 1, "available": 0},
        }

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["next_check_due"], "2027-10-01")
        self.assertEqual(result["key_check"]["available"], 0)
        self.assertIsNone(result["wallet_software"])
        self.assertEqual(result["ai_security_checks"], [])
        self.assertEqual(result["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(result["contact_info_verified"], "Needs external update")
        self.assertIsNone(result["comments"])

    def test_an_unavailable_key_rejects_recorded_results(self):
        recorded = (
            ("wallet_software", "Sparrow Wallet"),
            ("ai_security_checks", [{"provider": "SeedSigner", "status": "SECURE", "comments": ""}]),
        )
        for field, value in recorded:
            payload = unavailable_payload()
            payload[field] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_an_unavailable_hardware_key_records_nothing_else(self):
        payload = unavailable_payload()
        payload["key_check"].update({
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "PROBLEM",
            "address_path_verified": "PROBLEM",
            "address_path": "m/48'/0'/0'/2'/0/0",
        })

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["firmware_version"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["key_check"]["comments"], "Key is with the third holder")

    def test_an_unavailable_cloud_key_keeps_its_derived_cloud_results(self):
        payload = unavailable_payload(key_number=3)
        payload["key_check"].update({
            "address_path_verified": "PROBLEM",
            "address_path": "m/48'/0'/0'/2'/0/0",
        })

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertEqual(result["key_check"]["cloud_health_status"], "PROBLEM")
        self.assertEqual(result["key_check"]["cloud_provider_operational"], 0)
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(result["key_check"]["comments"], "Key is with the third holder")

    def test_over_long_text_is_rejected(self):
        payload = sample_payload()
        payload["comments"] = "x" * 4001

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)


if __name__ == "__main__":
    unittest.main()
