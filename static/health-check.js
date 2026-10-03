"use strict";

const form = document.querySelector("#health-check-form");
const keySelect = document.querySelector("#key-select");
const keyCheck = document.querySelector("#key-check");
const softwareSection = document.querySelector("#software-section");
const softwareGrid = document.querySelector("#software-section .field-grid");
const walletSoftwareSelect = document.querySelector("#wallet-software");
const softwareCompatibilitySelect = document.querySelector("#software-compatibility");
const softwareVersionInput = document.querySelector("#software-version");
const softwareHelp = document.querySelector("#software-help");
const contactSelect = document.querySelector("#contact-info-verified");
const contactReminder = document.querySelector("#contact-reminder");
const toolChecks = document.querySelector("#tool-checks");
const securityChecks = document.querySelector("#security-checks");
const nextCheckPreview = document.querySelector("#next-check-preview");
const reviewPanel = document.querySelector("#review-panel");
const reviewSummary = document.querySelector("#review-summary");
const saveButton = document.querySelector("#save-check");
const saveStatus = document.querySelector("#save-status");
const toolChecksSection = toolChecks.closest(".form-section");
const securityChecksSection = securityChecks.closest(".form-section");

// Sparrow is always a wallet software choice; a cloud key contributes its own
// name as well (section 23.3).
const SPARROW_SOFTWARE = "Sparrow Wallet";
const SECURITY_STATUSES = ["SECURE", "PATCHED", "VULNERABLE", "COMPROMISED"];
const UNAVAILABLE_MESSAGE = "The remaining checks for this key cannot be recorded.";
// The contact result that reminds the user to update their own records (section 23.1).
const CONTACT_NEEDS_UPDATE = "Needs external update";
// BIP327 and SLIP39 answer yes or no, and "not assessed" is not a no (section 21).
const standardsStatuses = [
  ["NOT_ASSESSED", "Not assessed"],
  ["YES", "Yes"],
  ["NO", "No"],
];
const verificationStatuses = [
  ["OK", "OK"],
  ["PROBLEM", "Problem"],
];
// Availability is always recorded, so it has no "not assessed" value (section 22).
const availabilityOptions = [["", "Select availability"], ["1", "Yes"], ["0", "No"]];
const booleanOptions = [["", "Not assessed"], ["1", "Yes"], ["0", "No"]];
let keyProfiles = [];
let previousValues = { keys: [] };
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

function walletSoftwareChoices() {
  // Sparrow plus the name of every configured cloud key. A hardware key name is
  // never a software choice (section 23.3).
  const cloudNames = keyProfiles
    .filter((key) => key.type === "cloud")
    .map((key) => key.name);
  return [...new Set([SPARROW_SOFTWARE, ...cloudNames])];
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
  const availability = form.querySelector('[name="available"]');
  return Boolean(selectedKey()) && availability !== null && availability.value === "0";
}

function expectedLabels(key) {
  const software = walletSoftwareSelect.value;
  if (!key || !software) {
    return [];
  }
  // The standards and the security statuses are recorded for the selected key,
  // by its configured name, and for the selected wallet software (section 23.3).
  return [...new Set([key.name, software])];
}

function renderKeySelect() {
  for (const key of keyProfiles) {
    const option = document.createElement("option");
    option.value = String(key.id);
    option.textContent = `Key ${key.key_number}: ${key.name}`;
    keySelect.append(option);
  }
}

function renderKeyCheck() {
  const key = selectedKey();
  keyCheck.replaceChildren();
  if (!key) {
    keyCheck.append(emptyState("Select a key to record its checks."));
    return;
  }

  const previous = previousForKey(key.id);
  const card = makeCard(
    `Key ${key.key_number}: ${key.name}`,
    key.type === "cloud"
      ? "Cloud key — report the result of your manual check."
      : "Hardware key — record the result of your manual check.",
  );
  const available = makeSelect(availabilityOptions, "available");
  available.required = true;
  card.append(makeField("Availability", "available", available));

  const details = document.createElement("div");
  details.className = "form-stack";
  if (key.type === "hardware") {
    details.append(makeField("Hardware works", "hardware_works", makeSelect(booleanOptions, "hardware_works")));
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
  const addressVerified = makeSelect(verificationStatuses, "address_path_verified", "Select a status");
  details.append(makeField("Address path verified", "address_path_verified", addressVerified));
  details.append(makeField(
    "Address path",
    "address_path",
    makeTextInput("address_path", 200, previousText(previous, "address_path")),
  ));
  card.append(details);
  card.append(makeField("Key notes", "key_comments", makeTextarea("key_comments")));
  keyCheck.append(card);

  available.addEventListener("change", () => {
    details.hidden = available.value === "0";
    syncRequiredFields();
    refreshKeySections();
  });
  addressVerified.addEventListener("change", syncAddressPathField);
  syncAddressPathField();
  syncRequiredFields();
}

function syncRequiredFields() {
  const key = selectedKey();
  const availability = form.querySelector('[name="available"]');
  const required = Boolean(key) && availability !== null && availability.value === "1";
  for (const name of ["seed_backup_verified", "address_path_verified"]) {
    const selector = `[name="${name}"]`;
    const select = form.querySelector(selector);
    if (select) {
      select.required = required;
    }
  }
}

function syncAddressPathField() {
  // The path is only recorded when it was verified as OK, so an unverified or
  // failed result never stores a path (section 21). The control is disabled
  // while it is hidden instead of cleared, so a pre-filled path is kept for the
  // user and still cannot be submitted with an unverified result.
  const field = form.querySelector('[name="address_path"]')?.closest(".field");
  const verified = form.querySelector('[name="address_path_verified"]');
  if (!field || verified === null) {
    return;
  }
  const input = form.querySelector('[name="address_path"]');
  const show = Boolean(selectedKey()) && verified.value === "OK";
  field.hidden = !show;
  input.disabled = !show;
}

function syncUnavailableState() {
  // A key that was not available records nothing else, so those parts of the
  // form are hidden and never required (section 22).
  const unavailable = keyIsUnavailable();
  softwareSection.hidden = unavailable;
  toolChecksSection.hidden = unavailable;
  securityChecksSection.hidden = unavailable;
  walletSoftwareSelect.required = !unavailable;
  // A hidden required control blocks the submission, so the compatibility
  // result is not required for a key that was not available either.
  softwareCompatibilitySelect.required = !unavailable;
}

function lockSoftwareFields() {
  const key = selectedKey();
  const isCloud = Boolean(key) && key.type === "cloud";
  const sparrow = walletSoftwareSelect.querySelector(`option[value="${SPARROW_SOFTWARE}"]`);
  if (sparrow) {
    sparrow.disabled = isCloud;
  }
  softwareGrid.hidden = isCloud;
  if (isCloud) {
    // A cloud key records its own name as the wallet software, and its
    // compatibility is derived from availability (sections 20 and 23.3).
    walletSoftwareSelect.value = key.name;
    softwareCompatibilitySelect.value = "OK";
    compatibilityDerived = true;
    softwareHelp.textContent = "Compatibility is derived from availability for a cloud key: available gives OK, not available gives not assessed.";
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
  // The saved version belongs to the saved software choice, so it is only
  // reused for the same key and the same software (section 23.1). A cloud key
  // has no version field of its own.
  const reusable = Boolean(key)
    && key.type === "hardware"
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

function renderToolChecks() {
  toolChecks.replaceChildren();
  if (keyIsUnavailable()) {
    toolChecks.append(emptyState(UNAVAILABLE_MESSAGE));
    return;
  }
  const labels = expectedLabels(selectedKey());
  if (!labels.length) {
    toolChecks.append(emptyState("Select a key and software to see the products to check."));
    return;
  }
  for (const label of labels) {
    const slug = productSlug(label);
    const bip327Name = `tool_${slug}_bip327_status`;
    const slip39Name = `tool_${slug}_slip39_status`;
    const card = makeCard(label, "Record the support status for this submission.");
    card.append(makeField("BIP327 status", bip327Name, makeSelect(standardsStatuses, bip327Name)));
    card.append(makeField("SLIP39 status", slip39Name, makeSelect(standardsStatuses, slip39Name)));
    toolChecks.append(card);
  }
}

function renderSecurityChecks() {
  const key = selectedKey();
  securityChecks.replaceChildren();
  if (!key) {
    securityChecks.append(emptyState("Select a key to see the providers to check."));
    return;
  }
  if (keyIsUnavailable()) {
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
  renderToolChecks();
  renderSecurityChecks();
  syncUnavailableState();
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

function derivedSummary(key, available) {
  if (!key || key.type !== "cloud" || available === null) {
    return [];
  }
  if (available === 1) {
    return [
      "Cloud health check: OK",
      "Provider operational: Yes",
      "Compatibility status: OK",
    ];
  }
  return [
    "Cloud health check: PROBLEM",
    "Provider operational: No",
    "Compatibility status: not assessed",
  ];
}

function buildReview() {
  const data = new FormData(form);
  const missing = [];
  const problems = [];
  for (const select of form.querySelectorAll("select")) {
    if (select.closest("[hidden]")) {
      continue;
    }
    const fieldLabel = select.closest(".field")?.querySelector("span");
    const label = fieldLabel?.textContent || select.name;
    const value = data.get(select.name);
    if (value === "" || value === "NOT_ASSESSED") {
      missing.push(label);
    } else if (
      value === "PROBLEM"
      || value === "0"
      || value === "VULNERABLE"
      || value === "COMPROMISED"
      || value === CONTACT_NEEDS_UPDATE
    ) {
      const problem = `${label}: ${value}`;
      problems.push(problem);
    }
  }

  const key = selectedKey();
  const available = key ? flagValue(data, "available") : null;
  const fragment = document.createDocumentFragment();
  appendSummaryList(fragment, "Needs assessment", missing.length ? missing : ["None"]);
  appendSummaryList(fragment, "Results requiring follow-up", problems.length ? problems : ["None"]);

  const derived = derivedSummary(key, available);
  if (derived.length) {
    appendSummaryList(fragment, "Derived from availability", derived);
  }

  const checkedAt = data.get("checked_at");
  const dates = document.createElement("p");
  const keyLabel = key ? `Key ${key.key_number}: ${key.name}` : "No key selected";
  dates.textContent = `${keyLabel} · Check date: ${checkedAt} · Next check due: ${nextCheckDate(checkedAt)}`;
  fragment.append(dates);
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

function derivedValues(key, available) {
  // The cloud key records these from availability alone (section 20).
  if (!key || key.type !== "cloud") {
    return {};
  }
  if (available === 1) {
    return {
      cloud_health_status: "OK",
      cloud_provider_operational: 1,
      software_compatibility_status: "OK",
    };
  }
  if (available === 0) {
    return {
      cloud_health_status: "PROBLEM",
      cloud_provider_operational: 0,
      software_compatibility_status: "NOT_ASSESSED",
    };
  }
  return {
    cloud_health_status: null,
    cloud_provider_operational: null,
    software_compatibility_status: "NOT_ASSESSED",
  };
}

function collectKeyCheck(data, key, derived) {
  const available = flagValue(data, "available");
  const isCloud = key.type === "cloud";
  const entry = {
    key_id: key.id,
    available: available,
    hardware_works: null,
    firmware_version: "",
    seed_backup_verified: null,
    cloud_health_status: isCloud ? derived.cloud_health_status : null,
    cloud_provider_operational: isCloud ? derived.cloud_provider_operational : null,
    address_path_verified: null,
    address_path: "",
    comments: textValue(data, "key_comments"),
  };
  if (available === 0) {
    return entry;
  }
  if (!isCloud) {
    entry.hardware_works = flagValue(data, "hardware_works");
    entry.firmware_version = textValue(data, "firmware_version");
    entry.seed_backup_verified = statusValue(data, "seed_backup_verified");
  }
  entry.address_path_verified = statusValue(data, "address_path_verified");
  entry.address_path = textValue(data, "address_path");
  return entry;
}

function collectPayload() {
  const data = new FormData(form);
  const key = selectedKey();
  const available = key ? flagValue(data, "available") : null;
  // A key that was not available records nothing else, so the payload leaves
  // those parts out entirely (section 22).
  const unavailable = available === 0;
  const derived = derivedValues(key, available);
  return {
    checked_at: textValue(data, "checked_at"),
    wallet_software: unavailable ? null : data.get("wallet_software"),
    software_version: unavailable ? "" : textValue(data, "software_version"),
    software_compatibility_status: derived.software_compatibility_status
      || (unavailable ? "NOT_ASSESSED" : statusValue(data, "software_compatibility_status")),
    software_comments: unavailable ? "" : textValue(data, "software_comments"),
    contact_info_verified: statusValue(data, "contact_info_verified"),
    comments: textValue(data, "comments"),
    key_check: collectKeyCheck(data, key, derived),
    tool_checks: unavailable ? [] : expectedLabels(key).map((label) => {
      const slug = productSlug(label);
      const bip327Name = `tool_${slug}_bip327_status`;
      const slip39Name = `tool_${slug}_slip39_status`;
      return {
        product: label,
        bip327_status: data.get(bip327Name),
        slip39_status: data.get(slip39Name),
      };
    }),
    ai_security_checks: unavailable ? [] : expectedLabels(key).map((provider) => {
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
    const [keysResponse, previousResponse] = await Promise.all([
      fetch("/api/keys", { headers: { Accept: "application/json" } }),
      fetch("/api/previous-values", { headers: { Accept: "application/json" } }),
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
    renderKeySelect();
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
  renderToolChecks();
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
