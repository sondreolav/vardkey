"use strict";

const form = document.querySelector("#health-check-form");
const keyChecks = document.querySelector("#key-checks");
const toolChecks = document.querySelector("#tool-checks");
const securityChecks = document.querySelector("#security-checks");
const reviewPanel = document.querySelector("#review-panel");
const reviewSummary = document.querySelector("#review-summary");
const generalStatuses = [
  ["IKKJE_VURDERT", "Not assessed"],
  ["OK", "OK"],
  ["PROBLEM", "Problem"],
];
const booleanOptions = [["", "Not assessed"], ["1", "Yes"], ["0", "No"]];
const productNames = ["SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet"];
const securityStatuses = ["TRYGG", "PATCHA", "SÅRBAR", "KOMPROMITTERT"];

function makeField(labelText, name, control) {
  const label = document.createElement("label");
  label.className = "field";
  const labelSpan = document.createElement("span");
  labelSpan.textContent = labelText;
  control.name = name;
  label.append(labelSpan, control);
  return label;
}

function makeSelect(options, name, includeBlank = false) {
  const select = document.createElement("select");
  select.name = name;
  if (includeBlank) {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a status";
    select.append(placeholder);
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

function renderKeyChecks(keys) {
  keyChecks.replaceChildren();
  for (const key of keys) {
    const card = makeCard(`Key ${key.key_number}: ${key.name}`, key.type === "cloud" ? "Cloud key — report the result of your manual check." : "Hardware key — record the result of your manual check.");
    const prefix = `key_${key.id}_`;
    card.append(makeField("Availability", `${prefix}available`, makeSelect(booleanOptions)));

    if (key.type === "hardware") {
      card.append(makeField("Hardware works", `${prefix}hardware_works`, makeSelect(booleanOptions)));
      card.append(makeField("Firmware version", `${prefix}firmware_version`, makeTextInput(`${prefix}firmware_version`, 100)));
      card.append(makeField("Seed backup status", `${prefix}seed_backup_status`, makeSelect(generalStatuses)));
      card.append(makeField("Backup verified as intact and matching the device", `${prefix}seed_backup_verified`, makeSelect(booleanOptions)));
    } else {
      card.append(makeField("Cloud health check", `${prefix}cloud_health_status`, makeSelect(generalStatuses)));
      card.append(makeField("Provider operational", `${prefix}cloud_provider_operational`, makeSelect(booleanOptions)));
    }

    card.append(makeField("Address verified", `${prefix}address_verified`, makeSelect(booleanOptions)));
    card.append(makeField("Derivation height", `${prefix}derivation_height`, makeTextInput(`${prefix}derivation_height`, 100)));
    card.append(makeField("Address path verified", `${prefix}address_path_verified`, makeSelect(booleanOptions)));
    card.append(makeField("Address path", `${prefix}address_path`, makeTextInput(`${prefix}address_path`, 200)));
    card.append(makeField("Key notes", `${prefix}comments`, makeTextarea(`${prefix}comments`)));
    keyChecks.append(card);
  }
}

function renderToolChecks() {
  toolChecks.replaceChildren();
  for (const product of productNames) {
    const card = makeCard(product, "Record support status and the product version checked.");
    const prefix = `tool_${product.toLowerCase().replaceAll(" ", "_")}_`;
    card.append(makeField("BIP327 status", `${prefix}bip327_status`, makeSelect(generalStatuses)));
    card.append(makeField("SLIP39 status", `${prefix}slip39_status`, makeSelect(generalStatuses)));
    card.append(makeField("Version checked", `${prefix}version`, makeTextInput(`${prefix}version`, 100)));
    const checkedAt = document.createElement("input");
    checkedAt.type = "date";
    card.append(makeField("Date checked", `${prefix}checked_at`, checkedAt));
    card.append(makeField("Notes or source", `${prefix}notes`, makeTextarea(`${prefix}notes`)));
    toolChecks.append(card);
  }
}

function renderSecurityChecks() {
  securityChecks.replaceChildren();
  for (const product of productNames) {
    const card = makeCard(product, "Enter the result of external research; do not include credentials or secrets.");
    const prefix = `security_${product.toLowerCase().replaceAll(" ", "_")}_`;
    const options = securityStatuses.map((status) => [status, status]);
    card.append(makeField("Security status", `${prefix}status`, makeSelect(options, "", true)));
    card.append(makeField("Comment", `${prefix}comments`, makeTextarea("", 1000)));
    securityChecks.append(card);
  }
}

function formatLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setSuggestedDates() {
  const checkedAt = document.querySelector("#checked-at");
  const dueDate = document.querySelector("#next-check-due");
  checkedAt.value = formatLocalDate(new Date());
  dueDate.dataset.suggested = "true";
  suggestDueDate();
  checkedAt.addEventListener("change", suggestDueDate);
  dueDate.addEventListener("input", () => {
    dueDate.dataset.suggested = "false";
  });

  function suggestDueDate() {
    if (dueDate.dataset.suggested !== "false" && checkedAt.value) {
      const [year, month, day] = checkedAt.value.split("-").map(Number);
      const date = new Date(year, month - 1, day);
      date.setFullYear(date.getFullYear() + 1);
      dueDate.value = formatLocalDate(date);
    }
  }
}

function buildReview() {
  const data = new FormData(form);
  const missing = [];
  const problems = [];
  for (const select of form.querySelectorAll("select")) {
    const fieldLabel = select.closest(".field")?.querySelector("span");
    const label = fieldLabel?.textContent || select.name;
    const value = data.get(select.name);
    if (value === "" || value === "IKKJE_VURDERT") {
      missing.push(label);
    } else if (value === "PROBLEM" || value === "0" || value === "SÅRBAR" || value === "KOMPROMITTERT") {
      problems.push(`${label}: ${value}`);
    }
  }

  const fragment = document.createDocumentFragment();
  appendSummaryList(fragment, "Needs assessment", missing.length ? missing : ["None"]);
  appendSummaryList(fragment, "Results requiring follow-up", problems.length ? problems : ["None"]);
  const dates = document.createElement("p");
  dates.textContent = `Check date: ${data.get("checked_at")} · Next check due: ${data.get("next_check_due")}`;
  fragment.append(dates);
  reviewSummary.replaceChildren(fragment);
  reviewPanel.hidden = false;
  reviewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
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

async function loadKeys() {
  try {
    const response = await fetch("/api/keys", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Key profiles are unavailable.");
    }
    renderKeyChecks(await response.json());
  } catch {
    keyChecks.replaceChildren();
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent = "Key profiles could not be loaded. Return to the dashboard or contact the service administrator.";
    keyChecks.append(message);
  }
}

renderToolChecks();
renderSecurityChecks();
setSuggestedDates();
form.addEventListener("input", () => {
  reviewPanel.hidden = true;
});
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) {
    return;
  }
  buildReview();
});
loadKeys();
