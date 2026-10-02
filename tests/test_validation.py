"""Tests for health check payload validation."""

import unittest

from validation import ValidationError, next_check_due, validate_health_check


KEYS = (
    {"id": 1, "key_number": 1, "name": "SeedSigner", "type": "hardware", "device": "SeedSigner"},
    {"id": 2, "key_number": 2, "name": "Blockstream Jade", "type": "hardware", "device": "Blockstream Jade"},
    {"id": 3, "key_number": 3, "name": "Nunchuk", "type": "cloud", "device": "Nunchuk"},
)
KEY_PRODUCTS = {1: "SeedSigner", 2: "Blockstream Jade", 3: "Nunchuk"}


def sample_payload(key_number=1, wallet_software=None):
    """Return a valid single-key payload for the given key number."""
    key = next(entry for entry in KEYS if entry["key_number"] == key_number)
    if wallet_software is None:
        wallet_software = "Nunchuk" if key_number == 3 else "Sparrow Wallet"
    products = list(dict.fromkeys((KEY_PRODUCTS[key_number], wallet_software)))
    providers = ["Nunchuk"] if key_number == 3 else [KEY_PRODUCTS[key_number], "Sparrow Wallet", "Nunchuk"]
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


class ValidationTests(unittest.TestCase):
    def test_valid_payload_is_normalized(self):
        result = validate_health_check(sample_payload(), KEYS)

        self.assertEqual(result["checked_at"], "2026-10-01")
        self.assertEqual(result["comments"], "Annual review")
        self.assertEqual(result["key_check"]["key_id"], 1)
        self.assertEqual(result["key_check"]["seed_backup_verified"], "OK")
        self.assertEqual(
            [entry["product"] for entry in result["tool_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )
        self.assertEqual(len(result["ai_security_checks"]), 3)

    def test_cloud_key_records_nunchuk_only(self):
        result = validate_health_check(sample_payload(key_number=3), KEYS)

        self.assertEqual(result["wallet_software"], "Nunchuk")
        self.assertEqual([entry["product"] for entry in result["tool_checks"]], ["Nunchuk"])
        self.assertEqual([entry["provider"] for entry in result["ai_security_checks"]], ["Nunchuk"])
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])

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

    def test_security_status_must_use_the_four_english_values(self):
        for value in ("TRYGG", "UNKNOWN", ""):
            payload = sample_payload()
            payload["ai_security_checks"][0]["status"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, KEYS)

    def test_security_providers_are_specific_to_the_selected_key(self):
        payload = sample_payload(key_number=1)
        payload["ai_security_checks"] = [
            {"provider": "SeedSigner", "status": "SECURE", "comments": ""},
            {"provider": "Sparrow Wallet", "status": "SECURE", "comments": ""},
            {"provider": "Nunchuk", "status": "SECURE", "comments": ""},
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

    def test_cloud_key_rejects_sparrow_wallet(self):
        payload = sample_payload(key_number=3)
        payload["wallet_software"] = "Sparrow Wallet"
        payload["tool_checks"] = [
            {"product": "Nunchuk", "bip327_status": "OK", "slip39_status": "OK"},
            {"product": "Sparrow Wallet", "bip327_status": "OK", "slip39_status": "OK"},
        ]

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_irrelevant_product_is_rejected(self):
        payload = sample_payload(key_number=1)
        payload["tool_checks"] = [
            {"product": "SeedSigner", "bip327_status": "OK", "slip39_status": "OK"},
            {"product": "Blockstream Jade", "bip327_status": "OK", "slip39_status": "OK"},
        ]

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_every_relevant_product_is_required(self):
        payload = sample_payload(key_number=1)
        payload["tool_checks"] = [
            {"product": "SeedSigner", "bip327_status": "OK", "slip39_status": "OK"},
        ]

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
        payload["key_check"]["seed_backup_verified"] = "IKKJE_VURDERT"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_an_unavailable_hardware_key_records_nothing_else(self):
        payload = sample_payload()
        payload["key_check"] = {
            "key_id": 1,
            "available": 0,
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "PROBLEM",
            "address_path_verified": "PROBLEM",
            "address_path": "m/48'/0'/0'/2'/0/0",
            "comments": "Key is with the third holder",
        }

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertIsNone(result["key_check"]["hardware_works"])
        self.assertIsNone(result["key_check"]["firmware_version"])
        self.assertIsNone(result["key_check"]["seed_backup_verified"])
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["key_check"]["comments"], "Key is with the third holder")

    def test_an_unavailable_cloud_key_keeps_its_derived_cloud_results(self):
        payload = sample_payload(key_number=3)
        payload["software_compatibility_status"] = "IKKJE_VURDERT"
        payload["key_check"] = {
            "key_id": 3,
            "available": 0,
            "cloud_health_status": "PROBLEM",
            "cloud_provider_operational": 0,
            "address_path_verified": "PROBLEM",
            "address_path": "m/48'/0'/0'/2'/0/0",
            "comments": "The provider is down",
        }

        result = validate_health_check(payload, KEYS)

        self.assertEqual(result["key_check"]["available"], 0)
        self.assertEqual(result["key_check"]["cloud_health_status"], "PROBLEM")
        self.assertEqual(result["key_check"]["cloud_provider_operational"], 0)
        self.assertIsNone(result["key_check"]["address_path_verified"])
        self.assertIsNone(result["key_check"]["address_path"])
        self.assertEqual(result["software_compatibility_status"], "IKKJE_VURDERT")
        self.assertEqual(result["key_check"]["comments"], "The provider is down")

    def test_invalid_flag_is_rejected(self):
        payload = sample_payload()
        payload["contact_info_verified"] = "yes"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)

    def test_over_long_text_is_rejected(self):
        payload = sample_payload()
        payload["comments"] = "x" * 4001

        with self.assertRaises(ValidationError):
            validate_health_check(payload, KEYS)


if __name__ == "__main__":
    unittest.main()
