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

        # The page heading comes first, and the form is renumbered with
        # 04 / Standards gone (section 24.3). The blocked-keys note adds no
        # section of its own (section 26.1).
        self.assertEqual(
            eyebrows,
            [
                "Annual security check",
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
            "address_path",
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

    def test_the_wallet_software_choices_come_from_the_settings_and_the_cloud_keys(self):
        script = read_static("health-check.js")
        html = read_static("health-check.html")
        self.assertIn("walletSoftwareChoices", script)
        self.assertIn("renderWalletSoftwareOptions", script)
        # The settings list plus the name of every configured cloud key
        # (section 25.4).
        self.assertIn("/api/settings", script)
        self.assertIn("walletSoftwareList", script)
        self.assertIn('key.type === "cloud"', script)
        self.assertIn("key.name", script)
        # The old fixed list and the built-in Sparrow constant are gone from both
        # the markup and the script.
        self.assertNotIn('option value="Nunchuk"', html)
        self.assertNotIn("KEY_PRODUCTS", script)
        self.assertNotIn("SPARROW_SOFTWARE", script)

    def test_form_script_uses_the_configured_key_name(self):
        script = read_static("health-check.js")
        self.assertIn("expectedLabels", script)
        self.assertIn("key.name", script)
        self.assertNotIn("keyProductFor", script)
        self.assertNotIn("CLOUD_KEY_NUMBER", script)

    def test_form_script_derives_from_availability(self):
        script = read_static("health-check.js")
        self.assertIn("/api/previous-values", script)
        self.assertIn("derivedSummary", script)
        self.assertIn("Derived from availability and the address path", script)
        self.assertIn('key.type === "cloud"', script)
        # The section 20 carry-forward of a third provider is gone (section 23.3).
        self.assertNotIn("carriedSecurity", script)
        self.assertNotIn("Carried forward from the last saved check", script)
        # The cloud key no longer renders the cloud results as form fields, and
        # the derived values themselves are gone (section 25.6).
        self.assertNotIn('makeField("Cloud health check"', script)
        self.assertNotIn('makeField("Provider operational"', script)
        self.assertNotIn("cloud_health_status", script)
        self.assertNotIn("cloud_provider_operational", script)

    def test_form_prefills_the_saved_values_as_input_values(self):
        script = read_static("health-check.js")
        # A previous value is a real input value, not an HTML placeholder, so an
        # untouched field is saved as it stands (section 23.1).
        self.assertIn("previousText", script)
        self.assertIn("input.value = value", script)
        self.assertNotIn("input.placeholder", script)
        self.assertIn('previousText(previous, "firmware_version")', script)
        # The address path is prefilled from the key profile, because that is the
        # stored path it is compared with (section 25.1).
        self.assertIn("key.address_path", script)
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
        # hidden required control would block the submission. The address path is
        # no longer a field of its own (section 25.1).
        self.assertIn('["hardware_works", "seed_backup_verified"]', script)
        self.assertNotIn("address_path_verified", script)
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
        self.assertIn('id="software-grid"', html)
        self.assertIn("softwareGrid.hidden = isCloud", script)

    def test_form_uses_the_english_status_values(self):
        script = read_static("health-check.js")
        self.assertIn("NOT_ASSESSED", script)
        self.assertNotIn("IKKJE_VURDERT", script)
        # The seed backup result keeps OK and PROBLEM.
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
        self.assertIn("syncUncheckableState", script)
        self.assertIn("softwareSection.hidden", script)
        self.assertIn("securityChecksSection.hidden", script)
        self.assertIn("walletSoftwareSelect.required", script)
        self.assertIn("UNAVAILABLE_MESSAGE", script)
        # The hidden parts render an empty state instead of required fields, so a
        # hidden required control can never block the submission.
        self.assertIn("emptyState(UNAVAILABLE_MESSAGE)", script)

    def test_form_sends_nothing_else_for_an_unavailable_key(self):
        script = read_static("health-check.js")
        self.assertIn("uncheckable ? null : data.get", script)
        self.assertIn("uncheckable ? [] : expectedLabels", script)
        self.assertIn('uncheckable\n      ? "NOT_ASSESSED"', script)

    def test_form_records_the_address_path_and_warns_when_it_does_not_match(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        # The user records the path only, and the browser compares it with the
        # stored one before it submits (section 25.1).
        self.assertIn('makeField(\n    "Address path"', script)
        self.assertIn('[name="address_path"]', script)
        self.assertIn("addressPathMismatch", script)
        self.assertIn("key.address_path", script)
        self.assertIn('id="address-path-warning"', html)
        self.assertIn("does not match the one stored for this key", html)
        self.assertIn("Check it against your BSMS", html)
        self.assertIn('id="address-path-confirmed"', html)
        self.assertIn("Record this check anyway", html)
        self.assertIn("addressPathWarning.hidden", script)
        self.assertIn("addressPathConfirmed.required = mismatch", script)
        # The choice to save anyway is marked in the review summary.
        self.assertIn("Recorded as a key that could not be checked", script)
        self.assertIn("Address path verified: PROBLEM", script)
        # The old verification field is gone from the form.
        self.assertNotIn('"address_path_verified"', script)
        self.assertNotIn("Address path verified", html)

    def test_form_hides_the_address_path_for_an_unavailable_key(self):
        script = read_static("health-check.js")
        self.assertIn("syncAddressPathState", script)
        # The path is not asked for when the key was not available (section 22).
        self.assertIn("field.hidden = keyIsUnavailable()", script)
        self.assertIn("#key-details", script)
        self.assertIn("details.hidden = keyIsUncheckable()", script)

    def test_form_records_the_software_version_for_every_key(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        # The label lost its "(if used)" wording (section 25.5).
        self.assertIn("<span>Software version</span>", html)
        self.assertNotIn("(if used)", html)
        # The version stays visible while the grid with the software and the
        # compatibility result is hidden for a cloud key (section 25.5).
        self.assertIn('id="software-version"', html)
        self.assertIn("updateSoftwareVersionValue", script)
        self.assertNotIn('key.type === "hardware"\n    && previous', script)
        # The help next to the field is written by the script, because its wording
        # depends on the selected key (section 32.3).
        self.assertIn('id="software-help"', html)
        self.assertIn("softwareHelp.textContent", script)

    def test_form_marks_the_keys_that_an_open_alert_blocks(self):
        html = read_static("health-check.html")
        script = read_static("health-check.js")
        # The form names the alert that stands in the way, the action that closes
        # it, and the keys that are still free (section 26.1).
        self.assertIn('id="blocked-keys-note"', html)
        self.assertIn('id="blocked-keys-list"', html)
        self.assertIn("Open the dashboard to close the alerts", html)
        # The note is the one place that explains the blocking, so the form does
        # not repeat it in a help line of its own (section 32.3).
        self.assertNotIn("A blocked key is marked in the list", html)
        self.assertIn("/api/alerts", script)
        self.assertIn("blockingAlerts", script)
        self.assertIn("blockedKeyIds", script)
        self.assertIn("renderBlockedKeysNote", script)
        self.assertIn("blocked by an open alert", script)
        self.assertIn("option.disabled = true", script)
        self.assertIn("Close it with:", script)
        self.assertIn("Keys that can still be checked:", script)
        self.assertIn("No key can be checked until an alert is closed.", script)
        # The action that closes an alert has its own wording (section 26.4).
        self.assertIn("ACTION_LABELS", script)
        self.assertIn('rotate: "Rotate key"', script)
        self.assertIn('replace_hardware: "Replace hardware"', script)
        self.assertIn('ignore: "Ignore alert"', script)
        self.assertIn('contact_updated: "Contact details updated"', script)
        # The server refuses the submission as well, so the form and the API agree.
        self.assertIn("open alert and cannot be checked until", script)

    def test_dashboard_shows_every_alert_with_its_check_date(self):
        script = read_static("app.js")
        styles = read_static("styles.css")
        self.assertIn("alert.check_id", script)
        self.assertIn("alert.checked_at", script)
        self.assertIn(".alert-origin", styles)

    def test_dashboard_key_card_shows_an_open_alert(self):
        script = read_static("app.js")
        styles = read_static("styles.css")
        # A key with an open alert shows a message instead of its ordinary status
        # (section 26.5).
        self.assertIn("alertsForKey", script)
        self.assertIn('status.className = "status status-alert"', script)
        self.assertIn("Needs action", script)
        self.assertIn("cannot be checked until", script)
        self.assertIn("createKeyAlertNote", script)
        self.assertIn("Close it with:", script)
        self.assertIn("#alerts-list", script)
        self.assertIn("Open the alert list", script)
        self.assertIn(".status-alert", styles)
        self.assertIn(".key-alert-note", styles)
        self.assertIn(".key-alert-message", styles)
        self.assertIn(".key-alert-detail", styles)

    def test_dashboard_key_card_keeps_the_dates_with_an_open_alert(self):
        script = read_static("app.js")
        # The alert note comes in addition to the dates, not instead of them, so
        # a key whose only alert is the informational contact one keeps its last
        # check and its next due date (section 27).
        self.assertIn('appendDateRow(dates, "Last checked", entry.last_checked_at)', script)
        self.assertIn('appendDateRow(dates, "Next check due", entry.next_check_due)', script)
        self.assertIn("card.append(dates);", script)
        dates_index = script.index('appendDateRow(dates, "Next check due"')
        note_index = script.index("card.append(createKeyAlertNote(entry, open))")
        self.assertLess(dates_index, note_index)

    def test_dashboard_offers_the_closing_action_of_every_alert(self):
        script = read_static("app.js")
        # Every alert names the actions that close it, and each action has its own
        # button text and confirmation step (section 26.4).
        self.assertIn("alert.actions", script)
        self.assertIn("alert.key_id", script)
        self.assertIn("ACTION_LABELS", script)
        self.assertIn('rotate: "Rotate key"', script)
        self.assertIn('replace_hardware: "Replace hardware"', script)
        self.assertIn('remove_software: "Remove software"', script)
        self.assertIn('ignore: "Ignore alert"', script)
        self.assertIn('contact_updated: "Contact details updated"', script)
        self.assertIn("ACTION_CONFIRMATIONS", script)
        self.assertIn("I have replaced the hardware wallet and restored the same seed on the new device.", script)
        self.assertIn("I have updated the contact details in my external documentation.", script)
        self.assertIn("createConfirmControl", script)
        self.assertIn("/settings?rotate=", script)
        self.assertIn("/api/alerts/acknowledge", script)
        self.assertIn("acknowledgeAlert", script)
        # The removed generic acknowledgement is gone.
        self.assertNotIn("Close alert", script)
        self.assertNotIn("Confirm close", script)
        self.assertNotIn("Reason for closing this alert", script)
        self.assertNotIn("acknowledge: ", script)

    def test_dashboard_removes_the_failing_software_from_the_settings(self):
        script = read_static("app.js")
        # Removing the failing software closes a software alert, and the alert
        # points at the right settings entry (section 26.7).
        self.assertIn("/api/settings", script)
        self.assertIn("walletSoftware", script)
        self.assertIn("createRemoveSoftwareControl", script)
        self.assertIn("removeSoftware", script)
        self.assertIn("/api/settings/wallet-software", script)
        self.assertIn("from the settings", script)
        self.assertIn("Open the settings", script)
        self.assertIn("walletSoftware.length > 1", script)

    def test_the_settings_link_has_one_wording(self):
        # The dashboard, the locked setup page and the top bar all point at the
        # same page, so the two call-to-action links use the same words
        # (section 32.3).
        self.assertIn('link.textContent = "Open the settings"', read_static("app.js"))
        self.assertIn('link.textContent = "Open the settings"', read_static("setup.js"))

    def test_dashboard_sends_to_the_key_setup_when_it_is_missing(self):
        script = read_static("app.js")
        self.assertIn("redirectWhenSetupIsMissing", script)
        self.assertIn('/api/setup', script)
        self.assertIn('window.location.assign("/setup")', script)

    def test_health_check_page_sends_to_the_key_setup_when_it_is_missing(self):
        script = read_static("health-check.js")
        self.assertIn('window.location.assign("/setup")', script)

    def test_the_setup_page_asks_for_a_name_a_type_and_an_address_path(self):
        html = read_static("setup.html")
        script = read_static("setup.js")
        self.assertIn('id="setup-form"', html)
        self.assertIn("Never enter seed phrases", html)
        for number in (1, 2, 3):
            self.assertIn(f'name="key_{number}_name"', html)
            self.assertIn(f'name="key_{number}_type"', html)
            # The setup records the address path of every key (section 25.1).
            self.assertIn(f'name="key_{number}_address_path"', html)
        self.assertIn('<option value="hardware">Hardware</option>', html)
        self.assertIn('<option value="cloud">Cloud</option>', html)
        self.assertIn("KEY_COUNT = 3", script)
        self.assertIn('/api/setup', script)
        self.assertIn("collectSetup", script)
        self.assertIn("address_path", script)
        self.assertIn("_address_path", script)
        # The type and the address path are locked once the setup is saved, while
        # the name may be changed in the settings (sections 25.1 and 25.2).
        self.assertIn("lockForm", script)
        self.assertIn("/settings", script)

    def test_the_settings_page_has_the_two_sections(self):
        html = read_static("settings.html")
        self.assertIn('<html lang="en">', html)
        self.assertIn("Never enter seed phrases", html)
        eyebrows = re.findall(r'<p class="eyebrow">([^<]+)</p>', html)
        # The key names, the address paths and the type are changed in the
        # rotation section, so the page has no separate keys section
        # (section 28). The page heading is the h1 on its own, without an eyebrow
        # that repeats it (section 32.3).
        self.assertEqual(eyebrows, ["01 / Wallet software", "02 / Key rotation"])
        self.assertIn("<h1>Settings</h1>", html)
        self.assertNotIn("01 / Keys", html)
        self.assertNotIn('id="keys-list"', html)
        self.assertIn('id="wallet-software-list"', html)
        self.assertIn('id="rotation-list"', html)
        self.assertIn('id="add-software"', html)
        self.assertIn('id="save-software"', html)
        self.assertIn('id="save-keys"', html)
        self.assertIn("Save keys", html)

    def test_the_settings_page_warns_about_moving_the_funds_and_changing_the_path(self):
        html = read_static("settings.html")
        # Rotating a key creates a new wallet, so the funds have to be moved
        # (section 25.2), and the key is a new one, so its path has to change
        # (section 26.3).
        self.assertIn("Rotating a key creates a new wallet", html)
        self.assertIn("Move your funds from the old multisig setup to the new one", html)
        self.assertIn("Do not discard the old keys", html)
        self.assertIn("The address path must change", html)
        self.assertIn("Every key needs its own new path", html)
        self.assertIn('id="rotation-replaced"', html)
        self.assertIn("I confirm that each selected key has been replaced", html)
        # The unchanged-path confirmation is gone (section 26.3).
        self.assertNotIn('id="rotation-path-unchanged"', html)
        self.assertNotIn("address path of each selected key is unchanged", html)
        # Removing an entry closes the alerts that software raised (section 26.7),
        # and the two removal helps are one paragraph (section 32.3).
        self.assertIn("Removing an entry also closes the alerts that software raised", html)
        self.assertNotIn("Removing an entry never changes a saved check</p>", html)
        self.assertIn(
            "Removing an entry never changes a saved check: the software selected "
            "in an earlier check stays as it was recorded. Removing an entry also "
            "closes the alerts that software raised",
            html,
        )

    def test_the_settings_script_stores_the_list_whole_and_saves_the_keys(self):
        script = read_static("settings.js")
        self.assertIn("/api/settings/keys", script)
        self.assertIn("/api/settings/wallet-software", script)
        self.assertIn("/api/keys/", script)
        self.assertIn("rotate", script)
        self.assertIn("wallet_software", script)
        self.assertIn("collectSoftware", script)
        # One action saves both the renamed keys and the rotated ones, and the
        # confirmation is only asked for when something is rotated (section 28).
        self.assertIn("collectKeys", script)
        self.assertIn("saveKeys", script)
        self.assertIn("keep_name", script)
        self.assertIn("replaced", script)
        self.assertIn("rotationReplaced.checked", script)
        # The address path is locked as soon as the key has a saved check, and the
        # name may always be changed (sections 25.1 and 25.2).
        self.assertIn("has_checks", script)
        self.assertIn("pathInput.disabled", script)
        # A link from the dashboard pre-selects the key it points at.
        self.assertIn("requestedRotation", script)
        # The rotation records a new, unique address path (sections 26.2 and 26.3).
        self.assertIn("rotation-path", script)
        self.assertIn("rotation_path_", script)
        self.assertIn("address_path: entry.address_path", script)
        self.assertIn("Write the new address path of every key you mark for rotation", script)
        # The name field starts on the name the key has now (section 26.3).
        self.assertIn("makeTextInput(key.name, 60)", script)
        # The type is only offered together with a rotation, because a type change
        # means the key is a new one (section 28).
        self.assertIn("rotation-type", script)
        self.assertIn("makeSelect", script)
        self.assertIn('["hardware", "Hardware"]', script)
        self.assertIn("type: entry.type", script)
        self.assertIn("typeSelect.disabled", script)
        # The removed confirmation is gone.
        self.assertNotIn("address_path_unchanged", script)
        self.assertNotIn("rotationPathUnchanged", script)
        # Removing an entry closes the alerts that software raised (section 26.7).
        self.assertIn("acknowledged", script)
        self.assertIn("raised by the removed software were closed", script)

    def test_history_shows_a_note_when_no_security_status_was_recorded(self):
        script = read_static("history.js")
        self.assertIn("securityTable", script)
        self.assertIn("No security statuses were recorded", script)

    def test_history_shows_the_contact_status_as_text(self):
        script = read_static("history.js")
        self.assertIn("Contact details confirmed", script)
        self.assertIn("record.contact_info_verified", script)

    def test_history_shows_the_derived_address_path_result(self):
        script = read_static("history.js")
        # The result is derived by the server, so it is shown as a derived value
        # (sections 9 and 25.1).
        self.assertIn("Address path verified (derived)", script)
        self.assertIn("keyCheck.address_path_verified", script)
        self.assertIn("keyCheck.address_path", script)
        # The removed cloud results are no longer shown (section 25.6).
        self.assertNotIn("Cloud health check", script)
        self.assertNotIn("Provider operational", script)
        self.assertNotIn("cloud_health_status", script)
        self.assertNotIn("cloud_provider_operational", script)

    def test_history_shows_the_follow_up_that_was_closed(self):
        script = read_static("history.js")
        # A closure that belongs to a key is shown as a card, with the code, the
        # source, the action written out, and the date (section 27).
        self.assertIn("Follow-up closed", script)
        self.assertIn("closed_alerts", script)
        self.assertIn("closedAlertsTable", script)
        self.assertIn("acknowledged_at", script)
        self.assertIn("No follow-up was closed on this check.", script)
        # The action labels are duplicated here, which is the existing pattern.
        self.assertIn("ACTION_LABELS", script)
        self.assertIn('rotate: "Rotate key"', script)
        self.assertIn('replace_hardware: "Replace hardware"', script)
        self.assertIn('contact_updated: "Contact details updated"', script)

    def test_stylesheet_makes_the_hidden_attribute_work_on_grid_containers(self):
        styles = read_static("styles.css")
        self.assertIn(".form-stack[hidden]", styles)
        self.assertIn(".field-grid[hidden]", styles)
        self.assertIn(".form-section[hidden]", styles)

    def test_stylesheet_separates_the_rotation_note_from_the_list(self):
        html = read_static("settings.html")
        styles = read_static("styles.css")
        # Only the spacing between the warning note and the rotation list changes
        # (section 26.6).
        self.assertIn('class="form-stack rotation-list"', html)
        self.assertIn(".rotation-list { margin-top: 22px; }", styles)

    def test_stylesheet_covers_the_new_elements(self):
        styles = read_static("styles.css")
        for rule in (
            ".warning-note",
            ".checkbox-field",
            ".software-row",
            ".alert-actions",
            ".topbar-actions",
            ".status-alert",
            ".key-alert-note",
        ):
            self.assertIn(rule, styles)


if __name__ == "__main__":
    unittest.main()
