"""Tests for annual health-check form content and client-side behavior."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read_static(name):
    """Return the text of one static asset."""
    return (ROOT / "static" / name).read_text(encoding="utf-8")


class HealthCheckFormTests(unittest.TestCase):
    def test_form_includes_privacy_notice_and_review_without_save_claim(self):
        html = read_static("health-check.html")
        self.assertIn('<html lang="en">', html)
        self.assertIn("Never enter seed phrases", html)
        self.assertIn('id="health-check-form"', html)
        self.assertIn("Review check", html)
        self.assertIn("No data from this form has been stored", html)

    def test_form_selects_one_key_and_one_wallet_software(self):
        html = read_static("health-check.html")
        self.assertIn('id="key-select"', html)
        self.assertIn('name="wallet_software"', html)
        self.assertIn('id="next-check-preview"', html)
        self.assertNotIn("next_check_due", html)
        self.assertIn('name="contact_info_verified"', html)

    def test_the_form_sections_follow_the_agreed_order(self):
        html = read_static("health-check.html")
        eyebrows = re.findall(r'<p class="eyebrow">([^<]+)</p>', html)

        # The form is renumbered, and 04 / Standards is gone (section 24.3).
        self.assertEqual(
            eyebrows,
            [
                "01 / Schedule",
                "02 / Key",
                "03 / Compatibility",
                "04 / External research",
                "05 / Contact confirmation",
                "06 / Notes",
                "Review",
            ],
        )

    def test_form_script_covers_the_checklist_fields_and_status_values(self):
        script = read_static("health-check.js")
        for field in (
            "hardware_works",
            "address_path_verified",
            "seed_backup_verified",
        ):
            self.assertIn(field, script)
        for status in ("SECURE", "PATCHED", "VULNERABLE", "COMPROMISED"):
            self.assertIn(status, script)
        self.assertIn("formatLocalDate", script)
        self.assertIn("Needs assessment", script)
        self.assertIn("Results requiring follow-up", script)

    def test_the_bip327_and_slip39_function_is_gone(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        history = read_static("history.js")
        # The whole function is removed (section 24.2), so neither the form, the
        # script, nor the history view mentions it any more.
        self.assertNotIn("BIP327", html)
        self.assertNotIn("SLIP39", html)
        self.assertNotIn("tool-checks", html)
        self.assertNotIn("toolChecks", script)
        self.assertNotIn("standardsStatuses", script)
        self.assertNotIn("tool_checks", script)
        self.assertNotIn("BIP327", history)
        self.assertNotIn("tool_checks", history)

    def test_form_script_no_longer_uses_the_removed_fields(self):
        script = read_static("health-check.js")
        for removed in ("seed_backup_status", "address_verified", "derivation_height"):
            self.assertNotIn(removed, script)

    def test_the_wallet_software_choices_come_from_the_key_setup(self):
        script = read_static("health-check.js")
        html = read_static("health-check.html")
        self.assertIn("walletSoftwareChoices", script)
        self.assertIn('SPARROW_SOFTWARE = "Sparrow Wallet"', script)
        self.assertIn("renderWalletSoftwareOptions", script)
        # Sparrow plus the name of every configured cloud key, and nothing else.
        self.assertIn('key.type === "cloud"', script)
        self.assertIn("key.name", script)
        # The old fixed list is gone from both the markup and the script.
        self.assertNotIn('option value="Nunchuk"', html)
        self.assertNotIn("KEY_PRODUCTS", script)

    def test_form_script_uses_the_configured_key_name(self):
        script = read_static("health-check.js")
        self.assertIn("expectedLabels", script)
        self.assertIn("key.name", script)
        self.assertNotIn("keyProductFor", script)
        self.assertNotIn("CLOUD_KEY_NUMBER", script)

    def test_form_script_derives_from_availability(self):
        script = read_static("health-check.js")
        self.assertIn("/api/previous-values", script)
        self.assertIn("derivedValues", script)
        self.assertIn("Derived from availability", script)
        self.assertIn('key.type === "cloud"', script)
        # The section 20 carry-forward of a third provider is gone (section 23.3).
        self.assertNotIn("carriedSecurity", script)
        self.assertNotIn("Carried forward from the last saved check", script)
        # The cloud key no longer renders the cloud results as form fields.
        self.assertNotIn('makeField("Cloud health check"', script)
        self.assertNotIn('makeField("Provider operational"', script)

    def test_form_prefills_the_saved_values_as_input_values(self):
        script = read_static("health-check.js")
        # A previous value is a real input value, not an HTML placeholder, so an
        # untouched field is saved as it stands (section 23.1).
        self.assertIn("previousText", script)
        self.assertIn("input.value = value", script)
        self.assertNotIn("input.placeholder", script)
        self.assertIn('previousText(previous, "firmware_version")', script)
        self.assertIn('previousText(previous, "address_path")', script)
        self.assertIn("updateSoftwareVersionValue", script)
        self.assertIn("softwareVersionInput.value = reusable", script)
        self.assertIn("previous.wallet_software === walletSoftwareSelect.value", script)

    def test_form_requires_an_explicit_compatibility_status(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        self.assertIn('id="software-compatibility"', html)
        self.assertIn('<option value="">Select status</option>', html)
        self.assertIn('name="software_compatibility_status" required', html)
        self.assertNotIn('value="NOT_ASSESSED"', html)
        # The hidden control carries the derived value for the cloud key and is
        # not required for a key that was not available (sections 20 and 22).
        self.assertIn("softwareCompatibilitySelect.required", script)
        self.assertIn("compatibilityDerived", script)
        self.assertIn('softwareCompatibilitySelect.value = "OK"', script)

    def test_form_requires_hardware_works_and_the_contact_confirmation(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        # Hardware works is a required choice for an available hardware key
        # (section 24.1), so the placeholder is not an answer.
        self.assertIn("hardwareWorksOptions", script)
        self.assertIn('["", "Select status"]', script)
        self.assertIn('makeSelect(hardwareWorksOptions, "hardware_works")', script)
        self.assertNotIn("booleanOptions", script)
        # The required flag is cleared when the key was not available, because a
        # hidden required control would block the submission.
        self.assertIn(
            '["hardware_works", "seed_backup_verified", "address_path_verified"]',
            script,
        )
        # The confirmation is required in the markup, with the same placeholder,
        # and it has no "not assessed" value.
        self.assertIn('name="contact_info_verified" required', html)
        self.assertNotIn("Not assessed", html)

    def test_form_asks_about_the_selected_key_holder_and_reminds_about_updates(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        self.assertIn("this key holder's contact details are current?", html)
        self.assertIn('<option value="Confirmed current">', html)
        self.assertIn('<option value="Needs external update">', html)
        self.assertIn('id="contact-reminder"', html)
        self.assertIn("syncContactReminder", script)
        self.assertIn("contactReminder.hidden", script)
        self.assertIn('CONTACT_NEEDS_UPDATE = "Needs external update"', script)
        # Only the status is recorded, and the old flag is gone (section 23.1).
        self.assertIn('statusValue(data, "contact_info_verified")', script)

    def test_form_can_hide_the_compatibility_grid_for_the_cloud_key(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        self.assertIn('id="software-section"', html)
        self.assertIn("#software-section .field-grid", script)

    def test_form_uses_the_english_status_values(self):
        script = read_static("health-check.js")
        self.assertIn("NOT_ASSESSED", script)
        self.assertNotIn("IKKJE_VURDERT", script)
        # The two verification results keep OK and PROBLEM.
        self.assertIn('["OK", "OK"]', script)
        self.assertIn('["PROBLEM", "Problem"]', script)

    def test_form_requires_availability_without_a_not_assessed_value(self):
        script = read_static("health-check.js")
        self.assertIn("availabilityOptions", script)
        self.assertIn('["", "Select availability"]', script)
        self.assertIn('makeSelect(availabilityOptions, "available")', script)
        self.assertIn("available.required = true", script)

    def test_form_hides_the_rest_of_the_check_for_an_unavailable_key(self):
        script = read_static("health-check.js")
        self.assertIn("keyIsUnavailable", script)
        self.assertIn("syncUnavailableState", script)
        self.assertIn("softwareSection.hidden", script)
        self.assertIn("securityChecksSection.hidden", script)
        self.assertIn("walletSoftwareSelect.required", script)
        self.assertIn("UNAVAILABLE_MESSAGE", script)
        # The hidden parts render an empty state instead of required fields, so a
        # hidden required control can never block the submission.
        self.assertIn("emptyState(UNAVAILABLE_MESSAGE)", script)

    def test_form_sends_nothing_else_for_an_unavailable_key(self):
        script = read_static("health-check.js")
        self.assertIn("unavailable ? null : data.get", script)
        self.assertIn("unavailable ? [] : expectedLabels", script)
        self.assertIn('unavailable ? "NOT_ASSESSED"', script)

    def test_form_hides_the_address_path_until_it_is_verified(self):
        script = read_static("health-check.js")
        styles = read_static("styles.css")
        self.assertIn("syncAddressPathField", script)
        self.assertIn('verified.value === "OK"', script)
        self.assertIn('[name="address_path"]', script)
        self.assertIn('[name="address_path_verified"]', script)
        # The control is disabled while it is hidden, so a pre-filled path is
        # kept for the user and still never submitted with an unverified result.
        self.assertIn("input.disabled = !show", script)
        # The field is a grid container, so the hidden attribute needs a rule.
        self.assertIn(".field[hidden]", styles)

    def test_dashboard_shows_every_alert_with_its_check_date(self):
        script = read_static("app.js")
        styles = read_static("styles.css")
        self.assertIn("alert.check_id", script)
        self.assertIn("alert.checked_at", script)
        self.assertIn(".alert-origin", styles)

    def test_dashboard_sends_to_the_key_setup_when_it_is_missing(self):
        script = read_static("app.js")
        self.assertIn("redirectWhenSetupIsMissing", script)
        self.assertIn('"/api/setup"', script)
        self.assertIn('window.location.assign("/setup")', script)

    def test_health_check_page_sends_to_the_key_setup_when_it_is_missing(self):
        script = read_static("health-check.js")
        self.assertIn('window.location.assign("/setup")', script)

    def test_the_setup_page_asks_for_a_name_and_a_type_for_three_keys(self):
        html = read_static("setup.html")
        script = read_static("setup.js")
        self.assertIn('id="setup-form"', html)
        self.assertIn("Never enter seed phrases", html)
        for number in (1, 2, 3):
            self.assertIn(f'name="key_{number}_name"', html)
            self.assertIn(f'name="key_{number}_type"', html)
        self.assertIn('<option value="hardware">Hardware</option>', html)
        self.assertIn('<option value="cloud">Cloud</option>', html)
        self.assertIn("KEY_COUNT = 3", script)
        self.assertIn('fetch("/api/setup"', script)
        self.assertIn("collectSetup", script)
        # The names and the types are locked once the setup is saved.
        self.assertIn("lockForm", script)

    def test_history_shows_a_note_when_no_security_status_was_recorded(self):
        script = read_static("history.js")
        self.assertIn("securityTable", script)
        self.assertIn("No security statuses were recorded", script)

    def test_history_shows_the_contact_status_as_text(self):
        script = read_static("history.js")
        self.assertIn("Contact details confirmed", script)
        self.assertIn("record.contact_info_verified", script)

    def test_stylesheet_makes_the_hidden_attribute_work_on_grid_containers(self):
        styles = read_static("styles.css")
        self.assertIn(".form-stack[hidden]", styles)
        self.assertIn(".field-grid[hidden]", styles)
        self.assertIn(".form-section[hidden]", styles)


if __name__ == "__main__":
    unittest.main()
