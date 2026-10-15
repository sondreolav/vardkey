"use strict";

const form = document.querySelector("#health-check-form");
const keySelect = document.querySelector("#key-select");
const keyCheck = document.querySelector("#key-check");
const softwareSection = document.querySelector("#software-section");
const softwareGrid = document.querySelector("#software-grid");
const walletSoftwareSelect = document.querySelector("#wallet-software");
const softwareCompatibilitySelect = document.querySelector("#software-compatibility");
const softwareVersionInput = document.querySelector("#software-version");
const softwareHelp = document.querySelector("#software-help");
const contactSelect = document.querySelector("#contact-info-verified");
const contactReminder = document.querySelector("#contact-reminder");
const securityChecks = document.querySelector("#security-checks");
const addressPathWarning = document.querySelector("#address-path-warning");
const addressPathConfirmed = document.querySelector("#address-path-confirmed");
const blockedKeysNote = document.querySelector("#blocked-keys-note");
const blockedKeysList = document.querySelector("#blocked-keys-list");
const nextCheckPreview = document.querySelector("#next-check-preview");
const reviewPanel = document.querySelector("#review-panel");
const reviewSummary = document.querySelector("#review-summary");
const saveButton = document.querySelector("#save-check");
const saveStatus = document.querySelector("#save-status");
const securityChecksSection = securityChecks.closest(".form-section");

const SECURITY_STATUSES = ["SECURE", "PATCHED", "VULNERABLE", "COMPROMISED"];
const UNAVAILABLE_MESSAGE = "The remaining checks for this key cannot be recorded.";
// The contact result that reminds the user to update their own records (section 23.1).
const CONTACT_NEEDS_UPDATE = "Needs external update";
// The button wording of every action that closes an alert (section 26.4). The
// alert itself names the actions it offers.
const ACTION_LABELS = {
  rotate: "Rotate key",
  replace_hardware: "Replace hardware",
  remove_software: "Remove software",
  ignore: "Ignore alert",
  contact_updated: "Contact details updated",
};
const verificationStatuses = [
  ["OK", "OK"],
  ["PROBLEM", "Problem"],
];
// Availability is always recorded, so it has no "not assessed" value (section 22).
const availabilityOptions = [["", "Select availability"], ["1", "Yes"], ["0", "No"]];
// Hardware works requires an active choice, so the placeholder is not an answer
// (section 24.1).
const hardwareWorksOptions = [["", "Select status"], ["1", "Yes"], ["0", "No"]];
let keyProfiles = [];
let previousValues = { keys: [] };
// The wallet software list the user maintains in the settings (section 25.4).
let walletSoftwareList = [];
// The open alerts that belong to a key. A key with one of them cannot get a new
// check until the alert is closed (section 26.1).
let blockingAlerts = [];
// True while the compatibility control carries the value derived for a cloud key.
let compatibilityDerived = false;

function emptyState(text) {
  const message = document.createElement("p");
  message.className = "empty-state";
  message.textContent = text;
  return message;
}

function makeField(labelText, name, control) {
  const label = document.createElement("label");
  label.className = "field";
  const labelSpan = document.createElement("span");
  labelSpan.textContent = labelText;
  control.name = name;
  label.append(labelSpan, control);
  return label;
}

function makeSelect(options, name, placeholder = "") {
  const select = document.createElement("select");
  select.name = name;
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.append(option);
  }
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }
  return select;
}

function makeTextInput(name, maxLength = 200, value = "") {
  const input = document.createElement("input");
  input.type = "text";
  input.name = name;
  input.maxLength = maxLength;
  input.autocomplete = "off";
  // A previous value is a real input value, not a placeholder, so a field the
  // user does not touch is saved as it stands (section 23.1).
  input.value = value;
  return input;
}

function makeTextarea(name, maxLength = 2000) {
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.rows = 3;
  textarea.maxLength = maxLength;
  return textarea;
}

function makeCard(title, subtitle) {
  const card = document.createElement("fieldset");
  card.className = "check-card";
  const legend = document.createElement("legend");
  legend.textContent = title;
  card.append(legend);
  const description = document.createElement("p");
  description.className = "field-help";
  description.textContent = subtitle;
  card.append(description);
  return card;
}

function productSlug(product) {
  return product.toLowerCase().replaceAll(" ", "_");
}

function selectedKey() {
  const keyId = Number(keySelect.value);
  return keyProfiles.find((key) => key.id === keyId) || null;
}

function previousForKey(keyId) {
  return (previousValues.keys || []).find((entry) => entry.key_id === keyId) || null;
}

function previousText(previous, field) {
  // An empty field is the right answer when no relevant value was saved.
  return (previous && previous[field]) || "";
}

function addressPathInput() {
  return form.querySelector('[name="address_path"]');
}

function availabilityValue() {
  const availability = form.querySelector('[name="available"]');
  return availability === null ? null : availability.value;
}

function walletSoftwareChoices() {
  // The settings list plus the name of every configured cloud key. A hardware key
  // name is never a software choice (sections 23.3 and 25.4).
  const cloudNames = keyProfiles
    .filter((key) => key.type === "cloud")
    .map((key) => key.name);
  return [...new Set([...walletSoftwareList, ...cloudNames])];
}

function renderWalletSoftwareOptions() {
  const choices = walletSoftwareChoices();
  const current = walletSoftwareSelect.value;
  walletSoftwareSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select software";
  walletSoftwareSelect.append(placeholder);
  for (const name of choices) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    walletSoftwareSelect.append(option);
  }
  walletSoftwareSelect.value = choices.includes(current) ? current : "";
}

function keyIsUnavailable() {
  return Boolean(selectedKey()) && availabilityValue() === "0";
}

function addressPathMismatch() {
  const key = selectedKey();
  const input = addressPathInput();
  if (!key || !input || keyIsUnavailable()) {
    // A key that was not available records no path at all, so no mismatch is
    // reported for it (sections 22 and 25.1).
    return false;
  }
  // The server compares the recorded path with the path stored for the key,
  // after stripping both (section 25.1).
  return input.value.trim() !== (key.address_path || "").trim();
}

function keyIsUncheckable() {
  return keyIsUnavailable() || addressPathMismatch();
}

function expectedLabels(key) {
  const software = walletSoftwareSelect.value;
  if (!key || !software) {
    return [];
  }
  // The security statuses are recorded for the selected key, by its configured
  // name, and for the selected wallet software (section 23.3).
  return [...new Set([key.name, software])];
}

function blockedKeyIds() {
  return new Set(blockingAlerts.map((alert) => alert.key_id));
}

function alertFor(key) {
  return blockingAlerts.find((alert) => alert.key_id === key.id) || null;
}

function actionLabels(actions) {
  return (actions || []).map((action) => ACTION_LABELS[action] || action).join(" or ");
}

function keyLabel(key) {
  return `Key ${key.key_number}: ${key.name}`;
}

function renderKeySelect() {
  keySelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select a key";
  keySelect.append(placeholder);

  const blocked = blockedKeyIds();
  for (const key of keyProfiles) {
    const option = document.createElement("option");
    option.value = String(key.id);
    if (blocked.has(key.id)) {
      // A key with an open alert cannot get a new check until the alert is
      // closed, so it cannot be selected at all (section 26.1).
      option.disabled = true;
      option.textContent = `${keyLabel(key)} — blocked by an open alert`;
    } else {
      option.textContent = keyLabel(key);
    }
    keySelect.append(option);
  }
}

function renderBlockedKeysNote() {
  // The form names the alert that stands in the way, the action that closes it,
  // and the keys that are still free (section 26.1).
  const blocked = keyProfiles.filter((key) => blockedKeyIds().has(key.id));
  blockedKeysNote.hidden = blocked.length === 0;
  blockedKeysList.replaceChildren();
  if (!blocked.length) {
    return;
  }

  for (const key of blocked) {
    const alert = alertFor(key);
    const item = document.createElement("li");
    item.textContent = `${keyLabel(key)} — ${alert.code}: ${alert.message} Close it with: ${actionLabels(alert.actions)}.`;
    blockedKeysList.append(item);
  }

  const free = keyProfiles.filter((key) => !blockedKeyIds().has(key.id));
  const summary = document.createElement("li");
  summary.textContent = free.length
    ? `Keys that can still be checked: ${free.map(keyLabel).join(", ")}.`
    : "No key can be checked until an alert is closed.";
  blockedKeysList.append(summary);
}

function renderKeyCheck() {
  const key = selectedKey();
  keyCheck.replaceChildren();
  if (!key) {
    keyCheck.append(emptyState("Select a key to record its checks."));
    return;
  }
  if (blockedKeyIds().has(key.id)) {
    // The server refuses the submission as well, so the form and the API agree
    // (section 26.1).
    keyCheck.append(emptyState(
      "This key has an open alert and cannot be checked until the alert is closed.",
    ));
    return;
  }

  const previous = previousForKey(key.id);
  const card = makeCard(
    keyLabel(key),
    key.type === "cloud"
      ? "Cloud key — report the result of your manual check."
      : "Hardware key — record the result of your manual check.",
  );
  const available = makeSelect(availabilityOptions, "available");
  available.required = true;
  card.append(makeField("Availability", "available", available));

  const details = document.createElement("div");
  details.id = "key-details";
  details.className = "form-stack";
  if (key.type === "hardware") {
    // Hardware works requires an active Yes or No (section 24.1).
    details.append(makeField(
      "Hardware works",
      "hardware_works",
      makeSelect(hardwareWorksOptions, "hardware_works"),
    ));
    details.append(makeField(
      "Firmware version",
      "firmware_version",
      makeTextInput("firmware_version", 100, previousText(previous, "firmware_version")),
    ));
    details.append(makeField(
      "Seed backup intact and matching the device",
      "seed_backup_verified",
      makeSelect(verificationStatuses, "seed_backup_verified", "Select a status"),
    ));
  }
  card.append(details);

  // The user records the address path only; the server compares it with the path
  // stored for the key and derives the verification result (section 25.1).
  card.append(makeField(
    "Address path",
    "address_path",
    makeTextInput("address_path", 200, key.address_path || ""),
  ));
  card.append(makeField("Key notes", "key_comments", makeTextarea("key_comments")));
  keyCheck.append(card);

  available.addEventListener("change", () => {
    syncKeyDetails();
    syncAddressPathState();
    refreshKeySections();
  });
  addressPathInput().addEventListener("input", syncAddressPathState);
  syncKeyDetails();
  syncAddressPathState();
}

function syncKeyDetails() {
  // Nothing else about the key is recorded when it was not available or when the
  // recorded address path does not match, so those fields are hidden
  // (sections 22 and 25.1).
  const details = form.querySelector("#key-details");
  if (details) {
    details.hidden = keyIsUncheckable();
  }
  syncRequiredFields();
}

function syncRequiredFields() {
  // Hardware works and the seed backup result require an active choice for a key
  // that was available and could be checked (sections 23.1 and 24.1). The
  // required flag is cleared otherwise, because a hidden required control would
  // block the submission.
  const required = Boolean(selectedKey())
    && availabilityValue() === "1"
    && !addressPathMismatch();
  for (const name of ["hardware_works", "seed_backup_verified"]) {
    const select = form.querySelector(`[name="${name}"]`);
    if (select) {
      select.required = required;
    }
  }
}

function syncAddressPathState() {
  const field = addressPathInput()?.closest(".field");
  if (field) {
    // The path is not asked for when the key was not available, because nothing
    // else about that key is recorded (section 22).
    field.hidden = keyIsUnavailable();
  }
  const mismatch = addressPathMismatch();
  addressPathWarning.hidden = !mismatch;
  // The confirmation is required while the warning is shown, so the browser
  // itself stops the submission. The flag follows the warning, so a required
  // control is never hidden.
  addressPathConfirmed.required = mismatch;
  if (!mismatch) {
    addressPathConfirmed.checked = false;
  }
  syncUncheckableState();
}

function syncUncheckableState() {
  // A key that was not available and a key whose recorded address path does not
  // match record nothing else, so the compatibility and the security sections are
  // hidden and never required (sections 22 and 25.1).
  const uncheckable = keyIsUncheckable();
  softwareSection.hidden = uncheckable;
  securityChecksSection.hidden = uncheckable;
  // A hidden required control blocks the submission, so the two controls inside
  // the hidden grid are not required for a cloud key either (sections 20 and 25.5).
  const key = selectedKey();
  const isCloud = Boolean(key) && key.type === "cloud";
  const required = !uncheckable && !isCloud;
  walletSoftwareSelect.required = required;
  softwareCompatibilitySelect.required = required;
}

function lockSoftwareFields() {
  const key = selectedKey();
  const isCloud = Boolean(key) && key.type === "cloud";
  // The grid holds the wallet software and the compatibility result, which are
  // both derived for a cloud key. The software version stays visible for every
  // key (sections 20 and 25.5).
  softwareGrid.hidden = isCloud;
  if (isCloud) {
    walletSoftwareSelect.value = key.name;
    softwareCompatibilitySelect.value = "OK";
    compatibilityDerived = true;
    softwareHelp.textContent = "Compatibility is derived from availability for a cloud key: available gives OK, not checked gives not assessed. Record the version of the software you use for that key.";
  } else {
    if (compatibilityDerived) {
      // The derived value is not an answer for another key, so it is cleared.
      softwareCompatibilitySelect.value = "";
      compatibilityDerived = false;
    }
    softwareHelp.textContent = "Record the version of the software you selected for this key.";
  }
  updateSoftwareVersionValue();
}

function updateSoftwareVersionValue() {
  const key = selectedKey();
  const previous = key ? previousForKey(key.id) : null;
  // The saved version belongs to the saved software choice, so it is only reused
  // for the same key and the same software. A cloud key records its own name as
  // its software, so the same rule applies to it (sections 23.1 and 25.5).
  const reusable = Boolean(key)
    && previous
    && previous.wallet_software === walletSoftwareSelect.value
    && previous.software_version;
  softwareVersionInput.value = reusable ? previous.software_version : "";
}

function syncContactReminder() {
  // "Needs external update" records the status only and reminds the user to
  // update the contact details in their own documentation (section 23.1).
  contactReminder.hidden = contactSelect.value !== CONTACT_NEEDS_UPDATE;
}

function renderSecurityChecks() {
  const key = selectedKey();
  securityChecks.replaceChildren();
  if (!key) {
    securityChecks.append(emptyState("Select a key to see the providers to check."));
    return;
  }
  if (keyIsUncheckable()) {
    securityChecks.append(emptyState(UNAVAILABLE_MESSAGE));
    return;
  }

  const options = SECURITY_STATUSES.map((status) => [status, status]);
  for (const provider of expectedLabels(key)) {
    const slug = productSlug(provider);
    const statusName = `security_${slug}_status`;
    const commentName = `security_${slug}_comments`;
    const card = makeCard(provider, "Enter the result of external research; do not include credentials or secrets.");
    const status = makeSelect(options, statusName, "Select a status");
    status.required = true;
    card.append(makeField("Security status", statusName, status));
    card.append(makeField("Comment", commentName, makeTextarea(commentName, 1000)));
    securityChecks.append(card);
  }
}

function refreshKeySections() {
  renderWalletSoftwareOptions();
  lockSoftwareFields();
  renderSecurityChecks();
  syncUncheckableState();
}

function formatLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function nextCheckDate(value) {
  if (!value) {
    return "";
  }
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  date.setFullYear(date.getFullYear() + 1);
  if (date.getMonth() !== month - 1) {
    // 29 February has no equivalent in a non-leap year, so clamp to 28 February.
    date.setDate(0);
  }
  return formatLocalDate(date);
}

function updateDuePreview() {
  const due = nextCheckDate(document.querySelector("#checked-at").value);
  nextCheckPreview.textContent = due
    ? `Next check due: ${due} (one calendar year after the check date).`
    : "Next check due is calculated automatically as one calendar year after the check date.";
}

function setCheckDate() {
  const checkedAt = document.querySelector("#checked-at");
  checkedAt.value = formatLocalDate(new Date());
  updateDuePreview();
  checkedAt.addEventListener("change", updateDuePreview);
}

function resetReview() {
  reviewPanel.hidden = true;
  saveStatus.textContent = "";
  saveButton.disabled = true;
}

function appendSummaryList(parent, title, items) {
  const heading = document.createElement("h3");
  heading.textContent = title;
  const list = document.createElement("ul");
  for (const item of items) {
    const entry = document.createElement("li");
    entry.textContent = item;
    list.append(entry);
  }
  parent.append(heading, list);
}

function derivedSummary(key, available, mismatch) {
  // The address path comparison and the compatibility of a key that could not be
  // checked are both derived by the server (sections 22 and 25.1).
  if (mismatch) {
    return [
      "Address path verified: PROBLEM",
      "Software compatibility: not assessed",
    ];
  }
  if (!key || key.type !== "cloud" || available === null) {
    return [];
  }
  return available === 1
    ? ["Compatibility status: OK"]
    : ["Compatibility status: not assessed"];
}

function buildReview() {
  const data = new FormData(form);
  const problems = [];
  // The summary lists the results that need follow-up. The list of the checks
  // that were still awaiting an answer was removed, because the form itself
  // already shows what is missing (section 32.2 point 11).
  for (const select of form.querySelectorAll("select")) {
    if (select.closest("[hidden]")) {
      continue;
    }
    const fieldLabel = select.closest(".field")?.querySelector("span");
    const label = fieldLabel?.textContent || select.name;
    const value = data.get(select.name);
    if (
      value === "PROBLEM"
      || value === "0"
      || value === "VULNERABLE"
      || value === "COMPROMISED"
      || value === CONTACT_NEEDS_UPDATE
    ) {
      problems.push(`${label}: ${value}`);
    }
  }

  const key = selectedKey();
  const available = key ? flagValue(data, "available") : null;
  const mismatch = addressPathMismatch();
  const fragment = document.createDocumentFragment();
  if (mismatch) {
    // The choice to save anyway is clearly marked in the summary (section 25.1).
    appendSummaryList(fragment, "Recorded as a key that could not be checked", [
      "The address path does not match the path stored for this key.",
      "Only the address path, the key note, the contact confirmation, and the overall comment are recorded.",
      "The hardware, the software, and the security results are not recorded, and this check raises a critical alert.",
    ]);
  }
  appendSummaryList(fragment, "Results requiring follow-up", problems.length ? problems : ["None"]);

  const derived = derivedSummary(key, available, mismatch);
  if (derived.length) {
    appendSummaryList(fragment, "Derived from availability and the address path", derived);
  }

  reviewSummary.replaceChildren(fragment);
  reviewPanel.hidden = false;
  saveStatus.textContent = "";
  saveButton.disabled = false;
  reviewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function flagValue(data, name) {
  const value = data.get(name);
  return value === "1" || value === "0" ? Number(value) : null;
}

function textValue(data, name) {
  const value = data.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function statusValue(data, name) {
  const value = data.get(name);
  return typeof value === "string" && value !== "" ? value : null;
}

function collectKeyCheck(data, key) {
  const available = flagValue(data, "available");
  const entry = {
    key_id: key.id,
    available: available,
    hardware_works: null,
    firmware_version: "",
    seed_backup_verified: null,
    address_path: "",
    comments: textValue(data, "key_comments"),
  };
  if (available === 0) {
    return entry;
  }
  entry.address_path = textValue(data, "address_path");
  if (addressPathMismatch()) {
    // The key could not be checked, so only the recorded path, the key note, the
    // contact confirmation, and the overall comment are sent (section 25.1).
    return entry;
  }
  if (key.type === "hardware") {
    entry.hardware_works = flagValue(data, "hardware_works");
    entry.firmware_version = textValue(data, "firmware_version");
    entry.seed_backup_verified = statusValue(data, "seed_backup_verified");
  }
  return entry;
}

function collectPayload() {
  const data = new FormData(form);
  const key = selectedKey();
  const available = key ? flagValue(data, "available") : null;
  // A key that was not available and a key whose address path does not match
  // record nothing else, so the payload leaves those parts out entirely
  // (sections 22 and 25.1).
  const uncheckable = available === 0 || addressPathMismatch();
  return {
    checked_at: textValue(data, "checked_at"),
    wallet_software: uncheckable ? null : data.get("wallet_software"),
    software_version: uncheckable ? "" : textValue(data, "software_version"),
    software_compatibility_status: uncheckable
      ? "NOT_ASSESSED"
      : statusValue(data, "software_compatibility_status"),
    software_comments: uncheckable ? "" : textValue(data, "software_comments"),
    contact_info_verified: statusValue(data, "contact_info_verified"),
    comments: textValue(data, "comments"),
    key_check: collectKeyCheck(data, key),
    ai_security_checks: uncheckable ? [] : expectedLabels(key).map((provider) => {
      const slug = productSlug(provider);
      const statusName = `security_${slug}_status`;
      const commentName = `security_${slug}_comments`;
      return {
        provider,
        status: statusValue(data, statusName),
        comments: textValue(data, commentName),
      };
    }),
  };
}

async function saveHealthCheck() {
  saveButton.disabled = true;
  saveStatus.textContent = "Saving…";
  try {
    const response = await fetch("/api/health-checks", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    if (!response.ok) {
      // The server refuses a key with an open alert as well, so the rule holds
      // even if the form let the key through (section 26.1).
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The health check could not be saved.");
    }
    const saved = await response.json();
    saveStatus.textContent = "Health check saved.";
    const target = `/history?id=${encodeURIComponent(saved.id)}`;
    window.location.assign(target);
  } catch (error) {
    saveStatus.textContent = error.message;
    saveButton.disabled = false;
  }
}

async function loadFormData() {
  try {
    const [keysResponse, previousResponse, settingsResponse, alertsResponse] = await Promise.all([
      fetch("/api/keys", { headers: { Accept: "application/json" } }),
      fetch("/api/previous-values", { headers: { Accept: "application/json" } }),
      fetch("/api/settings", { headers: { Accept: "application/json" } }),
      fetch("/api/alerts", { headers: { Accept: "application/json" } }),
    ]);
    if (!keysResponse.ok) {
      throw new Error("Key profiles are unavailable.");
    }
    keyProfiles = await keysResponse.json();
    if (!keyProfiles.length) {
      // A new database has no key setup yet, so the form cannot record anything.
      window.location.assign("/setup");
      return;
    }
    if (previousResponse.ok) {
      const values = await previousResponse.json();
      previousValues = { keys: values.keys || [] };
    }
    if (settingsResponse.ok) {
      const settings = await settingsResponse.json();
      // The wallet software choices come from the settings list and the
      // configured cloud keys (section 25.4).
      walletSoftwareList = settings.wallet_software || [];
    }
    if (alertsResponse.ok) {
      const alerts = await alertsResponse.json();
      // Only an alert that belongs to a key blocks that key (section 26.1).
      blockingAlerts = alerts.filter((alert) => alert.key_id);
    }
    renderKeySelect();
    renderBlockedKeysNote();
    renderKeyCheck();
    refreshKeySections();
  } catch {
    keySelect.disabled = true;
    keyCheck.replaceChildren(emptyState(
      "Key profiles could not be loaded. Return to the dashboard or contact the service administrator.",
    ));
  }
}

setCheckDate();
renderKeyCheck();
refreshKeySections();
syncContactReminder();
saveButton.addEventListener("click", saveHealthCheck);
keySelect.addEventListener("change", () => {
  renderKeyCheck();
  refreshKeySections();
});
walletSoftwareSelect.addEventListener("change", () => {
  updateSoftwareVersionValue();
  renderSecurityChecks();
});
contactSelect.addEventListener("change", syncContactReminder);
form.addEventListener("input", resetReview);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) {
    return;
  }
  buildReview();
});
loadFormData();
