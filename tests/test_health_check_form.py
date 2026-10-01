"""Tests for annual health-check form content and client-side behavior."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HealthCheckFormTests(unittest.TestCase):
    def test_form_includes_privacy_notice_and_review_without_save_claim(self):
        html = (ROOT / "static" / "health-check.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="en">', html)
        self.assertIn("Never enter seed phrases", html)
        self.assertIn('id="health-check-form"', html)
        self.assertIn("Review check", html)
        self.assertIn("No data from this form has been stored", html)

    def test_form_script_covers_all_four_products_and_checklist_fields(self):
        script = (ROOT / "static" / "health-check.js").read_text(encoding="utf-8")
        for product in ("SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet"):
            self.assertIn(product, script)
        for field in (
            "address_verified",
            "address_path_verified",
            "derivation_height",
            "seed_backup_verified",
            "bip327_status",
            "slip39_status",
            "contact_info_verified",
        ):
            self.assertIn(field, script)
        self.assertIn("setFullYear", script)
        self.assertIn("Needs assessment", script)
        self.assertIn("Results requiring follow-up", script)


if __name__ == "__main__":
    unittest.main()
