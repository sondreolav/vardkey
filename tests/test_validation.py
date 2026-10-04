"""Tests for payload validation."""

import unittest

from validation import (
    ValidationError,
    next_check_due,
    validate_acknowledgement,
    validate_health_check,
    validate_key_settings,
    validate_key_setup,
    validate_rotation,
    validate_wallet_software,
)


# The address path the keys are configured with (section 25.1).
ADDRESS_PATH = "m/48'/0'/0'/2'"
KEYS = (
    {"id": 1, "key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"id": 2, "key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": ADDRESS_PATH},
    {"id": 3, "key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": ADDRESS_PATH},
)
# A setup with the cloud key in the first slot, renamed hardware keys, and a
# different address path per key, to show that the comparison is per key and that
# the type decides the checks and never the key number.
RENAMED_KEYS = (
    {"id": 1, "key_number": 1, "name": "Coinbase", "type": "cloud", "address_path": ADDRESS_PATH},
    {"id": 2, "key_number": 2, "name": "ColdCard", "type": "hardware", "address_path": "m/48'/1'/0'/2'"},
    {"id": 3, "key_number": 3, "name": "Jade", "type": "hardware", "address_path": "m/48'/2'/0'/2'"},
)
# The wallet software list the settings hold (section 25.4).
SOFTWARE_NAMES = ("Sparrow Wallet",)


def key_for(key_number, keys=KEYS):
    """Return the key profile with the given number."""
    return next(entry for entry in keys if entry["key_number"] == key_number)


def entry(key_number, name, key_type, address_path=ADDRESS_PATH):
    """Return one key of a setup payload."""
    return {
        "key_number": key_number,
        "name": name,
        "type": key_type,
        "address_path": address_path,
    }


def validate(payload, keys=KEYS, software_names=SOFTWARE_NAMES):
    """Return a validated payload, with the settings list the app passes."""
    return validate_health_check(payload, keys, software_names)


def sample_payload(key_number=1, wallet_software=None, keys=KEYS, address_path=None):
    """Return a valid single-key payload for the given key number.

    The recorded address path matches the stored one unless a test asks for
    another one (section 25.1).
    """
    key = key_for(key_number, keys)
    if wallet_software is None:
        wallet_software = key["name"] if key["type"] == "cloud" else "Sparrow Wallet"
    labels = list(dict.fromkeys((key["name"], wallet_software)))
    entry_payload = {
        "key_id": key["id"],
        "available": 1,
        "address_path": address_path if address_path is not None else key["address_path"],
        "comments": "",
    }
    if key["type"] == "hardware":
        entry_payload.update({
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
        "key_check": entry_payload,
        "ai_security_checks": [
            {"provider": label, "status": "SECURE", "comments": ""} for label in labels
        ],
    }


def unavailable_payload(key_number=1, keys=KEYS):
    """Return the payload the form sends for a key that was not available."""
    key = key_for(key_number, keys)
    return {
        "checked_at": "2026-10-01",
        "wallet_software": None,
        "software_compatibility_status": "NOT_ASSESSED",
        "contact_info_verified": "Needs external update",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 0,
            "comments": "Key is with the third holder",
        },
        "ai_security_checks": [],
    }


def mismatch_payload(key_number=1, address_path="m/48'/9'/0'/2'", keys=KEYS):
    """Return the minimal payload the form sends when the path does not match.

    Everything else about the key is left out, because the key could not be
    checked (section 25.1).
    """
    key = key_for(key_number, keys)
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


class KeySetupTests(unittest.TestCase):
    def test_a_valid_setup_is_normalized_and_sorted(self):
        result = validate_key_setup({"keys": [
            entry(3, "  Nunchuk  ", "cloud"),
            entry(1, "ColdCard", "hardware"),
            entry(2, "Jade", "hardware"),
        ]})

        self.assertEqual(
            result,
            [
                entry(1, "ColdCard", "hardware"),
                entry(2, "Jade", "hardware"),
                entry(3, "Nunchuk", "cloud"),
            ],
        )

    def test_all_three_keys_may_be_cloud_keys(self):
        result = validate_key_setup({"keys": [
            entry(1, "Provider one", "cloud"),
            entry(2, "Provider two", "cloud"),
            entry(3, "Provider three", "cloud"),
        ]})

        self.assertEqual([item["type"] for item in result], ["cloud"] * 3)

    def test_duplicate_names_are_rejected_without_regard_to_case(self):
        for names in (("Jade", "Jade"), ("Jade", "jade"), ("Jade", " JADE ")):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    entry(1, names[0], "hardware"),
                    entry(2, names[1], "hardware"),
                    entry(3, "Nunchuk", "cloud"),
                ]})

    def test_an_empty_or_non_text_name_is_rejected(self):
        for name in ("", "   ", None, 12):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    entry(1, name, "hardware"),
                    entry(2, "Jade", "hardware"),
                    entry(3, "Nunchuk", "cloud"),
                ]})

    def test_an_over_long_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_key_setup({"keys": [
                entry(1, "x" * 61, "hardware"),
                entry(2, "Jade", "hardware"),
                entry(3, "Nunchuk", "cloud"),
            ]})

    def test_an_unknown_type_is_rejected(self):
        for key_type in ("", "hardware ", "cloudy", None):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    entry(1, "ColdCard", key_type),
                    entry(2, "Jade", "hardware"),
                    entry(3, "Nunchuk", "cloud"),
                ]})

    def test_a_repeated_or_unknown_key_number_is_rejected(self):
        for numbers in ((1, 1, 3), (1, 2, 4), (0, 2, 3), (1, 2, None), (1, 2, True)):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    entry(numbers[0], "ColdCard", "hardware"),
                    entry(numbers[1], "Jade", "hardware"),
                    entry(numbers[2], "Nunchuk", "cloud"),
                ]})

    def test_the_wrong_number_of_keys_is_rejected(self):
        single = entry(1, "ColdCard", "hardware")
        for entries in ([], [single], [single, single], [single] * 4):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": entries})

    def test_a_missing_key_list_is_rejected(self):
        for payload in ({}, {"keys": None}, {"keys": "ColdCard"}, []):
            with self.assertRaises(ValidationError):
                validate_key_setup(payload)

    def test_the_address_path_is_required_for_every_key(self):
        for value in ("", "   ", None, 12):
            with self.assertRaises(ValidationError):
                validate_key_setup({"keys": [
                    entry(1, "ColdCard", "hardware", value),
                    entry(2, "Jade", "hardware"),
                    entry(3, "Nunchuk", "cloud"),
                ]})

    def test_an_over_long_address_path_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_key_setup({"keys": [
                entry(1, "ColdCard", "hardware", "m/" + "x" * 200),
                entry(2, "Jade", "hardware"),
                entry(3, "Nunchuk", "cloud"),
            ]})

    def test_two_keys_may_share_an_address_path(self):
        # The three keys of one multisig setup normally share their derivation
        # path, so the path is not unique (section 25.1).
        result = validate_key_setup({"keys": [
            entry(1, "ColdCard", "hardware"),
            entry(2, "Jade", "hardware"),
            entry(3, "Nunchuk", "cloud"),
        ]})

        self.assertEqual([item["address_path"] for item in result], [ADDRESS_PATH] * 3)


class ValidationTests(unittest.TestCase):
    def test_valid_payload_is_normalized(self):
        result = validate(sample_payload())

        self.assertEqual(result["checked_at"], "2026-10-01")
        self.assertEqual(result["comments"], "Annual review")
        self.assertEqual(result["key_check"]["key_id"], 1)
        self.assertEqual(result["key_check"]["seed_backup_verified"], "OK")
        self.assertEqual(len(result["ai_security_checks"]), 2)

    def test_the_configured_name_is_the_product_label(self):
        result = validate(sample_payload(key_number=2, keys=RENAMED_KEYS), RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Sparrow Wallet")
        self.assertEqual(
            [item["provider"] for item in result["ai_security_checks"]],
            ["ColdCard", "Sparrow Wallet"],
        )

    def test_a_cloud_key_records_its_own_name_once(self):
        result = validate(sample_payload(key_number=1, keys=RENAMED_KEYS), RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Coinbase")
        self.assertEqual([item["provider"] for item in result["ai_security_checks"]], ["Coinbase"])
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])

    def test_a_hardware_key_may_use_a_cloud_key_name_as_its_software(self):
        payload = sample_payload(key_number=2, keys=RENAMED_KEYS)
        payload["wallet_software"] = "Coinbase"
        payload["ai_security_checks"] = [
            {"provider": label, "status": "SECURE", "comments": ""}
            for label in ("ColdCard", "Coinbase")
        ]

        result = validate(payload, RENAMED_KEYS)

        self.assertEqual(result["wallet_software"], "Coinbase")
        self.assertEqual(
            [item["provider"] for item in result["ai_security_checks"]],
            ["ColdCard", "Coinbase"],
        )

    def test_a_hardware_key_name_is_not_a_wallet_software_choice(self):
        # "Jade" is a hardware key in this setup, so it is never software.
        payload = sample_payload(key_number=2, keys=RENAMED_KEYS)
        payload["wallet_software"] = "Jade"

        with self.assertRaises(ValidationError):
            validate(payload, RENAMED_KEYS)

    def test_the_wallet_software_choices_are_the_settings_list_and_the_cloud_keys(self):
        # A name from the settings list is a choice for a hardware key, and a
        # name that is in neither is not (section 25.4).
        payload = sample_payload()
        payload["wallet_software"] = "BlueWallet"
        payload["ai_security_checks"] = [
            {"provider": label, "status": "SECURE", "comments": ""}
            for label in ("SeedSigner", "BlueWallet")
        ]

        result = validate(payload, KEYS, ("BlueWallet",))
        self.assertEqual(result["wallet_software"], "BlueWallet")

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_a_cloud_key_rejects_another_wallet_software(self):
        for value in ("Sparrow Wallet", "ColdCard"):
            payload = sample_payload(key_number=1, keys=RENAMED_KEYS)
            payload["wallet_software"] = value
            with self.assertRaises(ValidationError):
                validate(payload, RENAMED_KEYS)

    def test_next_check_due_is_derived_on_the_server(self):
        payload = sample_payload()
        payload["next_check_due"] = "1999-01-01"

        result = validate(payload)

        self.assertEqual(result["next_check_due"], "2027-10-01")

    def test_leap_day_is_clamped_to_the_last_day_of_february(self):
        self.assertEqual(next_check_due("2028-02-29"), "2029-02-28")
        self.assertEqual(next_check_due("2026-02-28"), "2027-02-28")

    def test_blank_text_is_stored_as_null(self):
        payload = sample_payload()
        payload["software_version"] = "   "

        result = validate(payload)

        self.assertIsNone(result["software_version"])

    def test_invalid_dates_are_rejected(self):
        for value in ("01-10-2026", "", None, "2026-13-01"):
            payload = sample_payload()
            payload["checked_at"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_unsupported_status_is_rejected(self):
        payload = sample_payload()
        payload["software_compatibility_status"] = "MAYBE"

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_compatibility_status_requires_an_explicit_choice(self):
        # "not assessed" is no longer submittable for a new registration
        # (section 23.1).
        for value in ("", None, "NOT_ASSESSED", "IKKJE_VURDERT"):
            payload = sample_payload()
            payload["software_compatibility_status"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_compatibility_status_accepts_ok_and_problem(self):
        for value in ("OK", "PROBLEM"):
            payload = sample_payload()
            payload["software_compatibility_status"] = value
            self.assertEqual(
                validate(payload)["software_compatibility_status"],
                value,
            )

    def test_cloud_key_compatibility_is_derived_from_availability(self):
        payload = sample_payload(key_number=3)
        payload["software_compatibility_status"] = "OK"
        self.assertEqual(
            validate(payload)["software_compatibility_status"],
            "OK",
        )

        for value in ("PROBLEM", "NOT_ASSESSED"):
            payload = sample_payload(key_number=3)
            payload["software_compatibility_status"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_unavailable_key_keeps_the_derived_compatibility(self):
        payload = unavailable_payload()
        payload["software_compatibility_status"] = "NOT_ASSESSED"
        self.assertEqual(
            validate(payload)["software_compatibility_status"],
            "NOT_ASSESSED",
        )

        payload["software_compatibility_status"] = "OK"
        with self.assertRaises(ValidationError):
            validate(payload)

    def test_not_assessed_is_only_the_derived_compatibility(self):
        # No other field offers or accepts NOT_ASSESSED (section 24.1).
        payload = sample_payload()
        payload["key_check"]["seed_backup_verified"] = "NOT_ASSESSED"

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_hardware_works_is_required_for_an_available_hardware_key(self):
        # Hardware works requires an active Yes or No (section 24.1).
        for value in ("", None, "NOT_ASSESSED"):
            payload = sample_payload()
            payload["key_check"]["hardware_works"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

        payload = sample_payload()
        del payload["key_check"]["hardware_works"]
        with self.assertRaises(ValidationError):
            validate(payload)

    def test_hardware_works_accepts_yes_and_no(self):
        for value in (1, 0):
            payload = sample_payload()
            payload["key_check"]["hardware_works"] = value
            self.assertEqual(
                validate(payload)["key_check"]["hardware_works"],
                value,
            )

    def test_contact_status_uses_the_two_stored_values(self):
        for value in ("Confirmed current", "Needs external update"):
            payload = sample_payload()
            payload["contact_info_verified"] = value
            self.assertEqual(
                validate(payload)["contact_info_verified"], value
            )

    def test_contact_status_is_required_and_never_a_flag(self):
        # The confirmation is required, also when the key was not available,
        # because the question is still asked (section 24.1).
        for payload in (sample_payload(), unavailable_payload()):
            for value in ("", None):
                payload["contact_info_verified"] = value
                with self.assertRaises(ValidationError):
                    validate(payload)
            del payload["contact_info_verified"]
            with self.assertRaises(ValidationError):
                validate(payload)

        # The old 0/1 flag is no longer a valid value (section 23.1).
        for value in (1, 0, True, "yes"):
            payload = sample_payload()
            payload["contact_info_verified"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_security_status_must_use_the_four_english_values(self):
        for value in ("TRYGG", "UNKNOWN", ""):
            payload = sample_payload()
            payload["ai_security_checks"][0]["status"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_security_labels_are_specific_to_the_selected_key(self):
        payload = sample_payload(key_number=1)
        payload["ai_security_checks"] = [
            {"provider": "SeedSigner", "status": "SECURE", "comments": ""},
            {"provider": "Sparrow Wallet", "status": "SECURE", "comments": ""},
            {"provider": "Blockstream Jade", "status": "SECURE", "comments": ""},
        ]

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_unknown_key_id_is_rejected(self):
        payload = sample_payload()
        payload["key_check"]["key_id"] = 99

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_missing_key_check_is_rejected(self):
        payload = sample_payload()
        del payload["key_check"]

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_the_server_sets_the_address_path_verification(self):
        result = validate(sample_payload())

        self.assertEqual(result["key_check"]["address_path"], ADDRESS_PATH)
        self.assertEqual(result["key_check"]["address_path_verified"], "OK")

    def test_the_address_path_is_compared_after_stripping(self):
        payload = sample_payload()
        payload["key_check"]["address_path"] = f"  {ADDRESS_PATH}  "

        result = validate(payload)

        self.assertEqual(result["key_check"]["address_path"], ADDRESS_PATH)
        self.assertEqual(result["key_check"]["address_path_verified"], "OK")

    def test_a_different_address_path_makes_the_key_uncheckable(self):
        result = validate(mismatch_payload(1, "m/48'/9'/0'/2'"))
        key_check = result["key_check"]

        # The recorded path and the key note are kept, while the rest of the
        # check is empty and the compatibility stays not assessed
        # (section 25.1).
        self.assertEqual(key_check["address_path"], "m/48'/9'/0'/2'")
        self.assertEqual(key_check["address_path_verified"], "PROBLEM")
        self.assertEqual(key_check["comments"], "Path read from the device")
        self.assertEqual(key_check["available"], 1)
        self.assertIsNone(key_check["hardware_works"])
        self.assertIsNone(key_check["firmware_version"])
        self.assertIsNone(key_check["seed_backup_verified"])
        self.assertIsNone(result["wallet_software"])
        self.assertEqual(result["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(result["ai_security_checks"], [])
        self.assertEqual(result["contact_info_verified"], "Confirmed current")
        self.assertEqual(result["comments"], "Annual review")

    def test_a_mismatched_submission_rejects_recorded_results(self):
        recorded = (
            ("wallet_software", "Sparrow Wallet"),
            ("ai_security_checks", [
                {"provider": "SeedSigner", "status": "SECURE", "comments": ""}
            ]),
            ("software_compatibility_status", "OK"),
        )
        for field, value in recorded:
            payload = mismatch_payload()
            payload[field] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_the_path_of_another_key_does_not_match(self):
        # The comparison uses the selected key's own path (section 25.1), so the
        # path of another key is a mismatch for this one.
        result = validate(mismatch_payload(2, ADDRESS_PATH, RENAMED_KEYS), RENAMED_KEYS)

        self.assertEqual(result["key_check"]["address_path"], ADDRESS_PATH)
        self.assertEqual(result["key_check"]["address_path_verified"], "PROBLEM")

        own_path = validate(
            mismatch_payload(2, "m/48'/1'/0'/2'", RENAMED_KEYS), RENAMED_KEYS
        )
        self.assertEqual(own_path["key_check"]["address_path_verified"], "OK")

    def test_a_submitted_verification_result_is_ignored(self):
        # The client never sends the result, and the server overrules it anyway
        # (section 25.1).
        payload = mismatch_payload()
        payload["key_check"]["address_path_verified"] = "OK"
        self.assertEqual(validate(payload)["key_check"]["address_path_verified"], "PROBLEM")

        payload = sample_payload()
        payload["key_check"]["address_path_verified"] = "PROBLEM"
        self.assertEqual(validate(payload)["key_check"]["address_path_verified"], "OK")

    def test_an_unavailable_key_never_reports_a_mismatch(self):
        # A key that was not available records no path at all, so nothing is
        # compared (sections 22 and 25.1).
        result = validate(unavailable_payload())

        self.assertIsNone(result["key_check"]["address_path"])
        self.assertIsNone(result["key_check"]["address_path_verified"])

    def test_a_missing_address_path_does_not_match_a_stored_one(self):
        payload = mismatch_payload()
        del payload["key_check"]["address_path"]

        result = validate(payload)

        self.assertEqual(result["key_check"]["address_path_verified"], "PROBLEM")

    def test_verification_status_is_required_when_the_key_is_available(self):
        payload = sample_payload()
        payload["key_check"]["seed_backup_verified"] = ""
        with self.assertRaises(ValidationError):
            validate(payload)

    def test_verification_status_rejects_not_assessed(self):
        payload = sample_payload()
        payload["key_check"]["seed_backup_verified"] = "NOT_ASSESSED"

        with self.assertRaises(ValidationError):
            validate(payload)

    def test_availability_is_required(self):
        for value in ("", None):
            payload = sample_payload()
            payload["key_check"]["available"] = value
            with self.assertRaises(ValidationError):
                validate(payload)

    def test_a_minimal_unavailable_payload_is_accepted(self):
        # The check date, the key check, and the contact confirmation are the
        # minimum, because the confirmation is required for every submission
        # (section 24.1).
        payload = {
            "checked_at": "2026-10-01",
            "contact_info_verified": "Needs external update",
            "key_check": {"key_id": 1, "available": 0},
        }

        result = validate(payload)

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
                validate(payload)

    def test_an_unavailable_hardware_key_records_nothing_else(self):
        payload = unavailable_payload()
        payload["key_check"].update({
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "PROBLEM",
            "address_path": ADDRESS_PATH,
        })

        result = validate(payload)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["firmware_version"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["key_check"]["comments"], "Key is with the third holder")

    def test_an_unavailable_cloud_key_records_nothing_else(self):
        payload = unavailable_payload(key_number=3)
        payload["key_check"].update({
            "address_path": ADDRESS_PATH,
            "comments": "Key is with the third holder",
        })

        result = validate(payload)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(result["key_check"]["comments"], "Key is with the third holder")

    def test_over_long_text_is_rejected(self):
        payload = sample_payload()
        payload["comments"] = "x" * 4001

        with self.assertRaises(ValidationError):
            validate(payload)


class KeySettingsTests(unittest.TestCase):
    def test_a_new_name_and_path_are_normalized(self):
        result = validate_key_settings(
            {"key_id": 1, "name": "  ColdCard  ", "address_path": f"  {ADDRESS_PATH}  "},
            KEYS,
        )

        self.assertEqual(result, {"key_id": 1, "name": "ColdCard", "address_path": ADDRESS_PATH})

    def test_the_type_is_never_part_of_the_settings(self):
        # The type is locked and cannot be changed through the settings
        # (section 25.2).
        result = validate_key_settings(
            {"key_id": 1, "name": "ColdCard", "address_path": ADDRESS_PATH, "type": "cloud"},
            KEYS,
        )

        self.assertNotIn("type", result)

    def test_an_unknown_key_is_rejected(self):
        for key_id in (99, None, "1", True):
            with self.assertRaises(ValidationError):
                validate_key_settings(
                    {"key_id": key_id, "name": "ColdCard", "address_path": ADDRESS_PATH},
                    KEYS,
                )

    def test_the_name_is_required_and_must_be_unique(self):
        for name in ("", "   ", None, 12, "x" * 61):
            with self.assertRaises(ValidationError):
                validate_key_settings(
                    {"key_id": 1, "name": name, "address_path": ADDRESS_PATH}, KEYS
                )

        # A name that repeats another key's name is refused without regard to
        # case, while the key's own name is of course allowed (section 25.2).
        for name in ("Nunchuk", "nunchuk", " NUNCHUK "):
            with self.assertRaises(ValidationError):
                validate_key_settings(
                    {"key_id": 1, "name": name, "address_path": ADDRESS_PATH}, KEYS
                )

        result = validate_key_settings(
            {"key_id": 3, "name": "Nunchuk", "address_path": ADDRESS_PATH}, KEYS
        )
        self.assertEqual(result["name"], "Nunchuk")

    def test_the_address_path_is_required(self):
        for value in ("", "   ", None, 12, "m/" + "x" * 200):
            with self.assertRaises(ValidationError):
                validate_key_settings(
                    {"key_id": 1, "name": "ColdCard", "address_path": value}, KEYS
                )

    def test_a_missing_or_wrong_payload_is_rejected(self):
        for payload in ({}, [], {"key_id": 1}, {"name": "ColdCard"}):
            with self.assertRaises(ValidationError):
                validate_key_settings(payload, KEYS)


class WalletSoftwareTests(unittest.TestCase):
    def test_a_valid_list_is_normalized(self):
        result = validate_wallet_software(
            {"wallet_software": ["  Sparrow Wallet  ", "BlueWallet"]}, KEYS
        )

        self.assertEqual(result, ["Sparrow Wallet", "BlueWallet"])

    def test_sparrow_may_be_replaced_by_another_name(self):
        # The list may not be emptied, but the entry a new database starts with
        # may be replaced once another name has been added (section 25.4).
        result = validate_wallet_software({"wallet_software": ["BlueWallet"]}, KEYS)

        self.assertEqual(result, ["BlueWallet"])

    def test_an_empty_list_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_wallet_software({"wallet_software": []}, KEYS)

    def test_a_missing_or_wrong_list_is_rejected(self):
        for payload in ({}, [], {"wallet_software": None}, {"wallet_software": "Sparrow Wallet"}):
            with self.assertRaises(ValidationError):
                validate_wallet_software(payload, KEYS)

    def test_an_empty_or_over_long_name_is_rejected(self):
        for value in ("", "   ", None, 12, "x" * 61):
            with self.assertRaises(ValidationError):
                validate_wallet_software({"wallet_software": [value]}, KEYS)

    def test_a_repeated_name_is_rejected_without_regard_to_case(self):
        for names in (["BlueWallet", "BlueWallet"], ["BlueWallet", "bluewallet"]):
            with self.assertRaises(ValidationError):
                validate_wallet_software({"wallet_software": names}, KEYS)

    def test_a_cloud_key_name_is_rejected(self):
        # A cloud key already provides its own name as a choice (section 25.4).
        for name in ("Nunchuk", "nunchuk", " NUNCHUK "):
            with self.assertRaises(ValidationError):
                validate_wallet_software({"wallet_software": [name]}, KEYS)

        # A hardware key name is not a cloud key name, so it is allowed.
        result = validate_wallet_software({"wallet_software": ["SeedSigner"]}, KEYS)
        self.assertEqual(result, ["SeedSigner"])


class RotationTests(unittest.TestCase):
    def test_keeping_the_name_needs_no_name(self):
        result = validate_rotation(
            {"replaced": True, "address_path_unchanged": True, "keep_name": True}, KEYS, 1
        )

        self.assertEqual(result, {"key_id": 1, "keep_name": True, "name": None})

    def test_changing_the_name_requires_a_unique_non_empty_name(self):
        for name in ("", "   ", None, 12, "x" * 61, "Nunchuk", "nunchuk"):
            with self.assertRaises(ValidationError):
                validate_rotation(
                    {
                        "replaced": True,
                        "address_path_unchanged": True,
                        "keep_name": False,
                        "name": name,
                    },
                    KEYS,
                    1,
                )

        result = validate_rotation(
            {
                "replaced": True,
                "address_path_unchanged": True,
                "keep_name": False,
                "name": "  ColdCard  ",
            },
            KEYS,
            1,
        )
        self.assertEqual(result, {"key_id": 1, "keep_name": False, "name": "ColdCard"})

    def test_the_two_confirmations_are_required(self):
        for field in ("replaced", "address_path_unchanged"):
            for value in (None, False, 0, 1, "yes", "true"):
                payload = {
                    "replaced": True,
                    "address_path_unchanged": True,
                    "keep_name": True,
                }
                payload[field] = value
                with self.assertRaises(ValidationError):
                    validate_rotation(payload, KEYS, 1)

    def test_keep_name_must_be_a_boolean(self):
        for value in (None, "yes", 1, 0, ""):
            with self.assertRaises(ValidationError):
                validate_rotation(
                    {
                        "replaced": True,
                        "address_path_unchanged": True,
                        "keep_name": value,
                    },
                    KEYS,
                    1,
                )

    def test_an_unknown_key_is_rejected(self):
        for key_id in (99, None, "1", True):
            with self.assertRaises(ValidationError):
                validate_rotation(
                    {"replaced": True, "address_path_unchanged": True, "keep_name": True},
                    KEYS,
                    key_id,
                )

    def test_the_type_and_the_path_are_never_part_of_the_rotation(self):
        # The type is locked and the path must be confirmed as unchanged, so
        # neither is read from the payload (section 25.2).
        result = validate_rotation(
            {
                "replaced": True,
                "address_path_unchanged": True,
                "keep_name": True,
                "type": "cloud",
                "address_path": "m/48'/9'/0'/2'",
            },
            KEYS,
            1,
        )

        self.assertEqual(result, {"key_id": 1, "keep_name": True, "name": None})


class AcknowledgementTests(unittest.TestCase):
    def test_a_valid_acknowledgement_is_normalized(self):
        result = validate_acknowledgement({
            "code": "address_path_mismatch",
            "source": "  Key 1: SeedSigner  ",
            "reason": "  The key was replaced  ",
        })

        self.assertEqual(result, {
            "code": "address_path_mismatch",
            "source": "Key 1: SeedSigner",
            "reason": "The key was replaced",
        })

    def test_an_unknown_or_removed_code_is_rejected(self):
        # The removed rules can no longer be triggered or acknowledged
        # (section 25.3).
        for code in ("cloud_provider_problem", "address_verification_failed", "UNKNOWN", "", None):
            with self.assertRaises(ValidationError):
                validate_acknowledgement({
                    "code": code,
                    "source": "Key 1: SeedSigner",
                    "reason": "Done",
                })

    def test_the_source_and_the_reason_are_required(self):
        for field in ("source", "reason"):
            for value in ("", "   ", None, 12):
                payload = {
                    "code": "key_unavailable",
                    "source": "Key 1: SeedSigner",
                    "reason": "Done",
                }
                payload[field] = value
                with self.assertRaises(ValidationError):
                    validate_acknowledgement(payload)

            payload = {"code": "key_unavailable", "source": "Key 1: SeedSigner", "reason": "Done"}
            del payload[field]
            with self.assertRaises(ValidationError):
                validate_acknowledgement(payload)

    def test_over_long_text_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_acknowledgement({
                "code": "key_unavailable",
                "source": "Key 1: SeedSigner",
                "reason": "x" * 2001,
            })

        with self.assertRaises(ValidationError):
            validate_acknowledgement({
                "code": "key_unavailable",
                "source": "x" * 201,
                "reason": "Done",
            })

    def test_a_missing_or_wrong_payload_is_rejected(self):
        for payload in ({}, [], {"code": "key_unavailable"}):
            with self.assertRaises(ValidationError):
                validate_acknowledgement(payload)


if __name__ == "__main__":
    unittest.main()
