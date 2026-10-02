"use strict";

const form = document.querySelector("#health-check-form");
const keySelect = document.querySelector("#key-select");
const keyCheck = document.querySelector("#key-check");
const walletSoftwareSelect = document.querySelector("#wallet-software");
const softwareHelp = document.querySelector("#software-help");
const toolChecks = document.querySelector("#tool-checks");
const securityChecks = document.querySelector("#security-checks");
const nextCheckPreview = document.querySelector("#next-check-preview");
const reviewPanel = document.querySelector("#review-panel");
const reviewSummary = document.querySelector("#review-summary");
const saveButton = document.querySelector("#save-check");
const saveStatus = document.querySelector("#save-status");

const CLOUD_KEY_NUMBER = 3;
const KEY_PRODUCTS = { 1: "SeedSigner", 2: "Blockstream Jade", 3: "Nunchuk" };
const WALLET_SOFTWARE = ["Sparrow Wallet", "Nunchuk"];
const generalStatuses = [
  ["IKKJE_VURDERT", "Not assessed"],
  ["OK", "OK"],
  ["PROBLEM", "Problem"],
];
const verificationStatuses = [
  ["OK", "OK"],
  ["PROBLEM", "Problem"],
];
const booleanOptions = [["", "Not assessed"], ["1", "Yes"], ["0", "No"]];
const securityStatuses = ["SECURE", "PATCHED", "VULNERABLE", "COMPROMISED"];
let keyProfiles = [];

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

function makeTextInput(name, maxLength = 200) {
  const input = document.createElement("input");
  input.type = "text";
  input.name = name;
  input.maxLength = maxLength;
  input.autocomplete = "off";
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

function expectedProducts() {
  const key = selectedKey();
  const software = walletSoftwareSelect.value;
  if (!key || !WALLET_SOFTWARE.includes(software)) {
    return [];
  }
  return [...new Set([KEY_PRODUCTS[key.key_number], software])];
}

function expectedProviders() {
  const key = selectedKey();
  if (!key) {
    return [];
  }
  if (key.key_number === CLOUD_KEY_NUMBER) {
    return ["Nunchuk"];
  }
  return [KEY_PRODUCTS[key.key_number], "Sparrow Wallet", "Nunchuk"];
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

  const card = makeCard(
    `Key ${key.key_number}: ${key.name}`,
    key.type === "cloud"
      ? "Cloud key — report the result of your manual check."
      : "Hardware key — record the result of your manual check.",
  );
  const available = makeSelect(booleanOptions, "available");
  card.append(makeField("Availability", "available", available));

  const details = document.createElement("div");
  details.className = "form-stack";
  if (key.type === "hardware") {
    details.append(makeField("Hardware works", "hardware_works", makeSelect(booleanOptions, "hardware_works")));
    details.append(makeField("Firmware version", "firmware_version", makeTextInput("firmware_version", 100)));
    details.append(makeField(
      "Seed backup intact and matching the device",
      "seed_backup_verified",
      makeSelect(verificationStatuses, "seed_backup_verified", "Select a status"),
    ));
  } else {
    details.append(makeField("Cloud health check", "cloud_health_status", makeSelect(generalStatuses, "cloud_health_status")));
    details.append(makeField("Provider operational", "cloud_provider_operational", makeSelect(booleanOptions, "cloud_provider_operational")));
  }
  details.append(makeField(
    "Address path verified",
    "address_path_verified",
    makeSelect(verificationStatuses, "address_path_verified", "Select a status"),
  ));
  details.append(makeField("Address path", "address_path", makeTextInput("address_path", 200)));
  card.append(details);
  card.append(makeField("Key notes", "key_comments", makeTextarea("key_comments")));
  keyCheck.append(card);

  available.addEventListener("change", () => {
    details.hidden = available.value === "0";
    syncRequiredFields();
  });
  syncRequiredFields();
}

function syncRequiredFields() {
  const key = selectedKey();
  const availability = form.querySelector('[name="available"]');
  const required = Boolean(key) && availability !== null && availability.value === "1";
  for (const name of ["seed_backup_verified", "address_path_verified"]) {
    const select = form.querySelector(`[name="${name}"]`);
    if (select) {
      select.required = required;
    }
  }
}

function lockWalletSoftware() {
  const key = selectedKey();
  const isCloud = Boolean(key) && key.key_number === CLOUD_KEY_NUMBER;
  const sparrow = walletSoftwareSelect.querySelector('option[value="Sparrow Wallet"]');
  sparrow.disabled = isCloud;
  if (isCloud) {
    walletSoftwareSelect.value = "Nunchuk";
    softwareHelp.textContent = "Nunchuk is the only wallet software available for the cloud key.";
  } else {
    softwareHelp.textContent = "Record the version of the software you selected for this key.";
  }
}

function renderToolChecks() {
  toolChecks.replaceChildren();
  const products = expectedProducts();
  if (!products.length) {
    toolChecks.append(emptyState("Select a key and software to see the products to check."));
    return;
  }
  for (const product of products) {
    const slug = productSlug(product);
    const card = makeCard(product, "Record the support status for this submission.");
    card.append(makeField("BIP327 status", `tool_${slug}_bip327_status`, makeSelect(generalStatuses, `tool_${slug}_bip327_status`)));
    card.append(makeField("SLIP39 status", `tool_${slug}_slip39_status`, makeSelect(generalStatuses, `tool_${slug}_slip39_status`)));
    toolChecks.append(card);
  }
}

function renderSecurityChecks() {
  securityChecks.replaceChildren();
  const providers = expectedProviders();
  if (!providers.length) {
    securityChecks.append(emptyState("Select a key to see the providers to check."));
    return;
  }
  const options = securityStatuses.map((status) => [status, status]);
  for (const provider of providers) {
    const slug = productSlug(provider);
    const card = makeCard(provider, "Enter the result of external research; do not include credentials or secrets.");
    const status = makeSelect(options, `security_${slug}_status`, "Select a status");
    status.required = true;
    card.append(makeField("Security status", `security_${slug}_status`, status));
    card.append(makeField("Comment", `security_${slug}_comments`, makeTextarea(`security_${slug}_comments`, 1000)));
    securityChecks.append(card);
  }
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
    if (value === "" || value === "IKKJE_VURDERT") {
      missing.push(label);
    } else if (value === "PROBLEM" || value === "0" || value === "VULNERABLE" || value === "COMPROMISED") {
      problems.push(`${label}: ${value}`);
    }
  }

  const fragment = document.createDocumentFragment();
  appendSummaryList(fragment, "Needs assessment", missing.length ? missing : ["None"]);
  appendSummaryList(fragment, "Results requiring follow-up", problems.length ? problems : ["None"]);
  const key = selectedKey();
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

function collectKeyCheck(data, key) {
  const available = flagValue(data, "available");
  const entry = {
    key_id: key.id,
    available: available,
    hardware_works: null,
    firmware_version: "",
    seed_backup_verified: null,
    cloud_health_status: null,
    cloud_provider_operational: null,
    address_path_verified: null,
    address_path: "",
    comments: textValue(data, "key_comments"),
  };
  if (available === 0) {
    return entry;
  }
  if (key.type === "hardware") {
    entry.hardware_works = flagValue(data, "hardware_works");
    entry.firmware_version = textValue(data, "firmware_version");
    entry.seed_backup_verified = statusValue(data, "seed_backup_verified");
  } else {
    entry.cloud_health_status = statusValue(data, "cloud_health_status");
    entry.cloud_provider_operational = flagValue(data, "cloud_provider_operational");
  }
  entry.address_path_verified = statusValue(data, "address_path_verified");
  entry.address_path = textValue(data, "address_path");
  return entry;
}

function collectPayload() {
  const data = new FormData(form);
  const key = selectedKey();
  return {
    checked_at: textValue(data, "checked_at"),
    wallet_software: data.get("wallet_software"),
    software_version: textValue(data, "software_version"),
    software_compatibility_status: data.get("software_compatibility_status"),
    software_comments: textValue(data, "software_comments"),
    contact_info_verified: flagValue(data, "contact_info_verified"),
    comments: textValue(data, "comments"),
    key_check: collectKeyCheck(data, key),
    tool_checks: expectedProducts().map((product) => {
      const slug = productSlug(product);
      return {
        product,
        bip327_status: data.get(`tool_${slug}_bip327_status`),
        slip39_status: data.get(`tool_${slug}_slip39_status`),
      };
    }),
    ai_security_checks: expectedProviders().map((provider) => {
      const slug = productSlug(provider);
      return {
        provider,
        status: statusValue(data, `security_${slug}_status`),
        comments: textValue(data, `security_${slug}_comments`),
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
    window.location.assign(`/history?id=${encodeURIComponent(saved.id)}`);
  } catch (error) {
    saveStatus.textContent = error.message;
    saveButton.disabled = false;
  }
}

async function loadKeys() {
  try {
    const response = await fetch("/api/keys", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Key profiles are unavailable.");
    }
    keyProfiles = await response.json();
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
renderToolChecks();
renderSecurityChecks();
saveButton.addEventListener("click", saveHealthCheck);
keySelect.addEventListener("change", () => {
  lockWalletSoftware();
  renderKeyCheck();
  renderToolChecks();
  renderSecurityChecks();
});
walletSoftwareSelect.addEventListener("change", renderToolChecks);
form.addEventListener("input", resetReview);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) {
    return;
  }
  buildReview();
});
loadKeys();
