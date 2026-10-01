"""Tests for health check payload validation."""

import unittest

from validation import ValidationError, validate_health_check


PRODUCTS = ("SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet")


def sample_payload(key_ids):
    """Return a valid health check payload for the given key ids."""
    return {
        "checked_at": "2026-10-01",
        "next_check_due": "2027-10-01",
        "software_compatibility_status": "OK",
        "sparrow_version": "1.8.0",
        "nunchuk_version": "",
        "software_comments": "",
        "contact_info_verified": 1,
        "comments": "Annual review",
        "key_checks": [
            {
                "key_id": key_id,
                "available": 1,
                "hardware_works": 1,
                "firmware_version": "1.0.0",
                "seed_backup_status": "OK",
                "seed_backup_verified": 1,
                "cloud_health_status": None,
                "cloud_provider_operational": None,
                "address_verified": 1,
                "derivation_height": "m/48'/0'/0'/2'",
                "address_path_verified": 1,
                "address_path": "m/48'/0'/0'/2'/0/0",
                "comments": "",
            }
            for key_id in sorted(key_ids)
        ],
        "tool_checks": [
            {
                "product": product,
                "bip327_status": "IKKJE_VURDERT",
                "slip39_status": "IKKJE_VURDERT",
                "version": "",
                "checked_at": "",
                "notes": "",
            }
            for product in PRODUCTS
        ],
        "ai_security_checks": [
            {"provider": product, "status": "TRYGG", "comments": ""}
            for product in PRODUCTS
        ],
    }


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.key_ids = {1, 2, 3}

    def test_valid_payload_is_normalized(self):
        result = validate_health_check(sample_payload(self.key_ids), self.key_ids)

        self.assertEqual(result["checked_at"], "2026-10-01")
        self.assertEqual(result["next_check_due"], "2027-10-01")
        self.assertEqual(result["comments"], "Annual review")
        self.assertEqual(len(result["key_checks"]), 3)
        self.assertEqual(len(result["tool_checks"]), 4)
        self.assertEqual(len(result["ai_security_checks"]), 4)

    def test_blank_text_is_stored_as_null(self):
        payload = sample_payload(self.key_ids)
        payload["sparrow_version"] = "   "

        result = validate_health_check(payload, self.key_ids)

        self.assertIsNone(result["sparrow_version"])

    def test_invalid_dates_are_rejected(self):
        for value in ("01-10-2026", "", None, "2026-13-01"):
            payload = sample_payload(self.key_ids)
            payload["checked_at"] = value
            with self.assertRaises(ValidationError):
                validate_health_check(payload, self.key_ids)

    def test_unsupported_status_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["software_compatibility_status"] = "MAYBE"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_security_status_must_use_the_four_allowed_values(self):
        payload = sample_payload(self.key_ids)
        payload["ai_security_checks"][0]["status"] = "UNKNOWN"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_missing_security_status_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["ai_security_checks"][0]["status"] = ""

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_unknown_key_id_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["key_checks"][0]["key_id"] = 99

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_missing_key_check_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["key_checks"] = payload["key_checks"][:2]

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_unsupported_product_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["tool_checks"][0]["product"] = "Unknown Wallet"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_invalid_flag_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["contact_info_verified"] = "yes"

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)

    def test_over_long_text_is_rejected(self):
        payload = sample_payload(self.key_ids)
        payload["comments"] = "x" * 4001

        with self.assertRaises(ValidationError):
            validate_health_check(payload, self.key_ids)


if __name__ == "__main__":
    unittest.main()
