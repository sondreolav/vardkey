"use strict";

const keysList = document.querySelector("#keys-list");
const softwareList = document.querySelector("#wallet-software-list");
const softwareStatus = document.querySelector("#software-status");
const addSoftwareButton = document.querySelector("#add-software");
const saveSoftwareButton = document.querySelector("#save-software");
const rotationList = document.querySelector("#rotation-list");
const rotationStatus = document.querySelector("#rotation-status");
const rotationReplaced = document.querySelector("#rotation-replaced");
const rotationPathUnchanged = document.querySelector("#rotation-path-unchanged");
const rotateButton = document.querySelector("#rotate-keys");
const settingsStatus = document.querySelector("#settings-status");

// The key the dashboard asked to rotate, if any (section 25.2).
let requestedRotation = new URLSearchParams(window.location.search).get("rotate");

// The keys with their address paths and the wallet software list (section 25.4).
let settings = { keys: [], wallet_software: [] };

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

function makeTextInput(value = "", maxLength = 60) {
  const input = document.createElement("input");
  input.type = "text";
  input.maxLength = maxLength;
  input.autocomplete = "off";
  input.value = value;
  return input;
}

function makeCheckbox(className, text, checked = false) {
  const label = document.createElement("label");
  label.className = "field checkbox-field";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.className = className;
  input.checked = checked;
  const span = document.createElement("span");
  span.textContent = text;
  label.append(input, span);
  return label;
}

function makeStatusLine() {
  const status = document.createElement("p");
  status.className = "workflow-note";
  status.setAttribute("role", "status");
  return status;
}

function renderKeys() {
  keysList.replaceChildren();
  if (!settings.keys.length) {
    keysList.append(emptyState(
      "No key setup is stored yet. Open the key setup to configure the three keys.",
    ));
    return;
  }
  for (const key of settings.keys) {
    keysList.append(keyCard(key));
  }
}

function keyCard(key) {
  const card = document.createElement("fieldset");
  card.className = "check-card";
  const legend = document.createElement("legend");
  legend.textContent = `Key ${key.key_number}: ${key.type === "cloud" ? "Cloud key" : "Hardware key"}`;
  card.append(legend);

  const nameInput = makeTextInput(key.name);
  card.append(makeField("Name", `key_${key.key_number}_name`, nameInput));

  const pathInput = makeTextInput(key.address_path || "", 200);
  // The address path is part of the key's identity, so it is locked once the key
  // has a saved check (section 25.1).
  pathInput.disabled = Boolean(key.has_checks);
  card.append(makeField("Address path", `key_${key.key_number}_address_path`, pathInput));

  const help = document.createElement("p");
  help.className = "field-help";
  help.textContent = key.has_checks
    ? "The address path is locked because this key already has a saved check. The name can still be changed."
    : "The address path can be changed until this key has its first saved check. The type is locked.";
  card.append(help);

  const status = makeStatusLine();
  const save = document.createElement("button");
  save.type = "button";
  save.className = "primary-button active-button";
  save.textContent = "Save key";
  save.addEventListener("click", () => saveKey(key, nameInput, pathInput, status, save));

  const actions = document.createElement("div");
  actions.className = "form-actions";
  actions.append(save);
  card.append(actions, status);
  return card;
}

async function saveKey(key, nameInput, pathInput, status, button) {
  button.disabled = true;
  status.textContent = "Saving…";
  try {
    const response = await fetch("/api/settings/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        key_id: key.id,
        name: nameInput.value.trim(),
        address_path: pathInput.value.trim(),
      }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The key settings could not be saved.");
    }
    settings = await response.json();
    renderKeys();
    renderRotation();
    settingsStatus.textContent = `Key ${key.key_number} saved.`;
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function softwareRow(name) {
  const row = document.createElement("div");
  row.className = "software-row";

  const input = makeTextInput(name);
  input.className = "software-name";
  row.append(makeField("Wallet software name", "wallet_software_name", input));

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "secondary-button";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => row.remove());
  row.append(remove);
  return row;
}

function renderSoftware() {
  softwareList.replaceChildren();
  for (const name of settings.wallet_software || []) {
    softwareList.append(softwareRow(name));
  }
  if (!softwareList.children.length) {
    softwareList.append(softwareRow(""));
  }
}

function collectSoftware() {
  // An empty row is a row the user did not fill in, so it is not sent. The
  // server still refuses an empty list and a repeated name (section 25.4).
  return [...softwareList.querySelectorAll(".software-name")]
    .map((input) => input.value.trim())
    .filter((name) => name !== "");
}

async function saveSoftware() {
  saveSoftwareButton.disabled = true;
  softwareStatus.textContent = "Saving…";
  try {
    const response = await fetch("/api/settings/wallet-software", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ wallet_software: collectSoftware() }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The wallet software list could not be saved.");
    }
    const saved = await response.json();
    settings.wallet_software = saved.wallet_software || [];
    renderSoftware();
    softwareStatus.textContent = "Wallet software list saved.";
  } catch (error) {
    softwareStatus.textContent = error.message;
  } finally {
    saveSoftwareButton.disabled = false;
  }
}

function renderRotation() {
  rotationList.replaceChildren();
  if (!settings.keys.length) {
    rotationList.append(emptyState("No key setup is stored yet."));
    return;
  }
  for (const key of settings.keys) {
    rotationList.append(rotationCard(key));
  }
}

function rotationCard(key) {
  const card = document.createElement("fieldset");
  card.className = "check-card";
  const legend = document.createElement("legend");
  legend.textContent = `Key ${key.key_number}: ${key.name}`;
  card.append(legend);

  const select = makeCheckbox("rotation-select", "Rotate this key", false);
  const checkbox = select.querySelector("input");
  checkbox.dataset.keyId = String(key.id);
  // A link from the dashboard pre-selects the key it points at (section 25.2).
  checkbox.checked = requestedRotation === String(key.id);
  card.append(select);

  const nameInput = makeTextInput("", 60);
  nameInput.className = "rotation-name";
  nameInput.disabled = true;

  const keep = document.createElement("input");
  keep.type = "radio";
  keep.name = `rotation_name_${key.id}`;
  keep.className = "rotation-keep";
  keep.checked = true;
  const change = document.createElement("input");
  change.type = "radio";
  change.name = `rotation_name_${key.id}`;
  change.className = "rotation-change";
  keep.addEventListener("change", () => {
    nameInput.disabled = true;
  });
  change.addEventListener("change", () => {
    nameInput.disabled = false;
    nameInput.focus();
  });

  const keepLabel = document.createElement("label");
  keepLabel.className = "field checkbox-field";
  const keepText = document.createElement("span");
  keepText.textContent = `Keep the name “${key.name}”`;
  keepLabel.append(keep, keepText);
  card.append(keepLabel);

  const changeLabel = document.createElement("label");
  changeLabel.className = "field checkbox-field";
  const changeText = document.createElement("span");
  changeText.textContent = "Change the name to";
  changeLabel.append(change, changeText);
  card.append(changeLabel);

  card.append(makeField("New name", `rotation_name_${key.id}_value`, nameInput));
  return card;
}

function collectRotation() {
  const entries = [];
  for (const card of rotationList.querySelectorAll(".check-card")) {
    const checkbox = card.querySelector(".rotation-select");
    if (!checkbox || !checkbox.checked) {
      continue;
    }
    const change = card.querySelector(".rotation-change");
    const nameInput = card.querySelector(".rotation-name");
    const keepName = !(change && change.checked);
    entries.push({
      key_id: Number(checkbox.dataset.keyId),
      keep_name: keepName,
      name: keepName ? "" : nameInput.value.trim(),
    });
  }
  return entries;
}

async function rotateSelected() {
  const entries = collectRotation();
  if (!entries.length) {
    rotationStatus.textContent = "Select at least one key to rotate.";
    return;
  }
  // Every action that closes an alert requires a confirmation from the user, and
  // the app never performs the action itself (sections 25.2 and 25.3).
  if (!rotationReplaced.checked || !rotationPathUnchanged.checked) {
    rotationStatus.textContent = "Confirm that the selected keys have been replaced and that their address path is unchanged.";
    return;
  }

  rotateButton.disabled = true;
  rotationStatus.textContent = "Rotating…";
  const rotated = [];
  const failed = [];
  for (const entry of entries) {
    try {
      const response = await fetch(`/api/keys/${entry.key_id}/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          replaced: true,
          keep_name: entry.keep_name,
          name: entry.name,
          address_path_unchanged: true,
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.error || "The key could not be rotated.");
      }
      const result = await response.json();
      settings = result.settings || settings;
      rotated.push(entry.key_id);
    } catch (error) {
      failed.push(`Key ${entry.key_id}: ${error.message}`);
    }
  }

  requestedRotation = null;
  renderKeys();
  renderRotation();
  rotationReplaced.checked = false;
  rotationPathUnchanged.checked = false;
  rotateButton.disabled = false;

  const summary = rotated.length === 1 ? "1 key rotated." : `${rotated.length} keys rotated.`;
  rotationStatus.textContent = failed.length
    ? `${summary} ${failed.join(" ")}`
    : `${summary} The alerts those keys raised are closed until a newer check raises them again.`;
}

function scrollToRotation() {
  if (!requestedRotation) {
    return;
  }
  document.querySelector("#settings-rotation-title")
    ?.closest(".form-section")
    ?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadSettings() {
  try {
    const response = await fetch("/api/settings", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("The settings are unavailable.");
    }
    settings = await response.json();
  } catch {
    settingsStatus.textContent = "The settings could not be loaded. Reload the page or contact the service administrator.";
    keysList.replaceChildren();
    rotationList.replaceChildren();
    return;
  }
  renderKeys();
  renderSoftware();
  renderRotation();
  scrollToRotation();
}

addSoftwareButton.addEventListener("click", () => {
  softwareList.append(softwareRow(""));
});
saveSoftwareButton.addEventListener("click", saveSoftware);
rotateButton.addEventListener("click", rotateSelected);
loadSettings();
