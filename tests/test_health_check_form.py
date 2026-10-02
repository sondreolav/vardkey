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

    def test_form_selects_one_key_and_one_wallet_software(self):
        html = (ROOT / "static" / "health-check.html").read_text(encoding="utf-8")
        self.assertIn('id="key-select"', html)
        self.assertIn('name="wallet_software"', html)
        self.assertIn('id="next-check-preview"', html)
        self.assertNotIn("next_check_due", html)
        self.assertIn('name="contact_info_verified"', html)

    def test_form_script_covers_all_four_products_and_checklist_fields(self):
        script = (ROOT / "static" / "health-check.js").read_text(encoding="utf-8")
        for product in ("SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet"):
            self.assertIn(product, script)
        for field in (
            "address_path_verified",
            "seed_backup_verified",
            "bip327_status",
            "slip39_status",
        ):
            self.assertIn(field, script)
        for status in ("SECURE", "PATCHED", "VULNERABLE", "COMPROMISED"):
            self.assertIn(status, script)
        self.assertIn("formatLocalDate", script)
        self.assertIn("Needs assessment", script)
        self.assertIn("Results requiring follow-up", script)

    def test_form_script_no_longer_uses_the_removed_fields(self):
        script = (ROOT / "static" / "health-check.js").read_text(encoding="utf-8")
        for removed in ("seed_backup_status", "address_verified", "derivation_height"):
            self.assertNotIn(removed, script)

    def test_form_script_derives_and_carries_values(self):
        script = (ROOT / "static" / "health-check.js").read_text(encoding="utf-8")
        self.assertIn("/api/previous-values", script)
        self.assertIn("derivedValues", script)
        self.assertIn("carriedSecurity", script)
        self.assertIn("Derived from availability", script)
        self.assertIn("Carried forward from the last saved check", script)
        self.assertIn("placeholder", script)
        # The cloud key no longer renders the cloud results as form fields.
        self.assertNotIn('makeField("Cloud health check"', script)
        self.assertNotIn('makeField("Provider operational"', script)

    def test_form_can_hide_the_compatibility_grid_for_the_cloud_key(self):
        html = (ROOT / "static" / "health-check.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "health-check.js").read_text(encoding="utf-8")
        self.assertIn('id="software-section"', html)
        self.assertIn("#software-section .field-grid", script)

    def test_stylesheet_makes_the_hidden_attribute_work_on_grid_containers(self):
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".form-stack[hidden]", styles)
        self.assertIn(".field-grid[hidden]", styles)


if __name__ == "__main__":
    unittest.main()
