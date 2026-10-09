"use strict";

const softwareList = document.querySelector("#wallet-software-list");
const softwareStatus = document.querySelector("#software-status");
const addSoftwareButton = document.querySelector("#add-software");
const saveSoftwareButton = document.querySelector("#save-software");
const rotationList = document.querySelector("#rotation-list");
const rotationStatus = document.querySelector("#rotation-status");
const rotationReplaced = document.querySelector("#rotation-replaced");
const saveKeysButton = document.querySelector("#save-keys");
const settingsStatus = document.querySelector("#settings-status");

// The key the dashboard asked to rotate, if any (section 25.2).
let requestedRotation = new URLSearchParams(window.location.search).get("rotate");

// The keys with their address paths and the wallet software list (section 25.4).
let settings = { keys: [], wallet_software: [] };

// The two types a key can have (section 23.3).
const typeOptions = [["hardware", "Hardware"], ["cloud", "Cloud"]];

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

function makeSelect(options, selected) {
  const select = document.createElement("select");
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === selected;
    select.append(option);
  }
  return select;
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

function alertCountText(count) {
  return count === 1 ? "1 alert" : `${count} alerts`;
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
    // Removing an entry closes the alerts that software raised, such as software
    // that no longer supports the hardware (section 26.7).
    const closed = saved.acknowledged || [];
    softwareStatus.textContent = closed.length
      ? `Wallet software list saved. The ${alertCountText(closed.length)} raised by the removed software were closed.`
      : "Wallet software list saved.";
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
  card.dataset.keyId = String(key.id);

  const legend = document.createElement("legend");
  legend.textContent = `Key ${key.key_number}: ${key.name}`;
  card.append(legend);

  const select = makeCheckbox("rotation-select", "Rotate this key", false);
  const checkbox = select.querySelector("input");
  checkbox.dataset.keyId = String(key.id);
  // A link from the dashboard pre-selects the key it points at (section 25.2).
  checkbox.checked = requestedRotation === String(key.id);
  card.append(select);

  // The type is part of the identity of a key, and the setup locks it. A
  // rotation replaces the key with a new one, so the replacement may carry the
  // other type, and the choice is only offered together with a rotation
  // (section 28).
  const typeSelect = makeSelect(typeOptions, key.type);
  typeSelect.className = "rotation-type";
  card.append(makeField("Type", `rotation_type_${key.id}`, typeSelect));

  // The name is only a label, so the field starts on the name the key has now,
  // and a name that is changed without a rotation is saved on its own
  // (sections 25.2 and 26.3).
  const nameInput = makeTextInput(key.name, 60);
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

  // The address path is part of the identity of a key. It can be changed while
  // the key has no saved check, and a rotation always records a new one
  // (sections 25.1 and 26.3).
  const pathInput = makeTextInput(key.has_checks ? "" : key.address_path || "", 200);
  pathInput.className = "rotation-path";
  card.append(makeField("Address path", `rotation_path_${key.id}`, pathInput));

  const help = document.createElement("p");
  help.className = "field-help";
  help.textContent = key.has_checks
    ? "This key already has a saved check, so its path is locked. Mark it for rotation to record a new one, which must differ from the stored one and be free."
    : "The path can be changed here until this key has its first saved check. A rotation must record a new one, which differs from the stored one and is free.";
  card.append(help);

  function syncRotationFields() {
    const rotating = checkbox.checked;
    // The type and the path are only asked for the keys the user actually
    // rotates, so a disabled field is never in the way.
    typeSelect.disabled = !rotating;
    pathInput.disabled = !rotating && Boolean(key.has_checks);
  }

  checkbox.addEventListener("change", () => {
    syncRotationFields();
    if (checkbox.checked) {
      pathInput.focus();
    }
  });
  syncRotationFields();
  return card;
}

function collectKeys() {
  const entries = [];
  for (const card of rotationList.querySelectorAll(".check-card")) {
    const keyId = Number(card.dataset.keyId);
    const key = settings.keys.find((entry) => entry.id === keyId);
    if (!key) {
      continue;
    }
    const rotating = card.querySelector(".rotation-select").checked;
    const change = card.querySelector(".rotation-change");
    const nameInput = card.querySelector(".rotation-name");
    const typeSelect = card.querySelector(".rotation-type");
    const pathInput = card.querySelector(".rotation-path");
    const keepName = !(change && change.checked);
    const name = keepName ? key.name : nameInput.value.trim();
    const storedPath = key.address_path || "";
    // A key that is not rotated keeps its stored path, because only a key that
    // has no saved check can change it here (section 25.1).
    const path = !rotating && key.has_checks ? storedPath : pathInput.value.trim();
    entries.push({
      key_id: keyId,
      key_number: key.key_number,
      rotating,
      keep_name: keepName,
      name: keepName ? "" : name,
      type: typeSelect ? typeSelect.value : key.type,
      address_path: path,
      changed: name !== key.name || path !== storedPath,
    });
  }
  return entries;
}

async function saveKeys() {
  const entries = collectKeys();
  const rotations = entries.filter((entry) => entry.rotating);
  const changes = entries.filter((entry) => !entry.rotating && entry.changed);

  if (!rotations.length && !changes.length) {
    rotationStatus.textContent = "Nothing to save. Change a name, or mark a key for rotation.";
    return;
  }
  // A rotation records a new key, so its address path has to change
  // (section 26.3).
  if (rotations.some((entry) => !entry.address_path)) {
    rotationStatus.textContent = "Write the new address path of every key you mark for rotation. The key is a new one, so its path must change.";
    return;
  }
  // A rotation replaces a key, and the app never performs the action itself
  // (sections 25.2 and 26.4).
  if (rotations.length && !rotationReplaced.checked) {
    rotationStatus.textContent = "Confirm that the keys you marked have been replaced by new keys or hardware wallets.";
    return;
  }

  saveKeysButton.disabled = true;
  rotationStatus.textContent = "Saving…";

  const renamed = [];
  const rotated = [];
  const failed = [];
  const closed = [];

  // A name that is only changed, and the path of a key that has no saved check,
  // go through the settings endpoint (sections 25.1 and 25.2).
  for (const entry of changes) {
    try {
      const response = await fetch("/api/settings/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          key_id: entry.key_id,
          name: entry.name,
          address_path: entry.address_path,
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.error || "The key settings could not be saved.");
      }
      settings = await response.json();
      renamed.push(entry.key_id);
    } catch (error) {
      failed.push(`Key ${entry.key_number}: ${error.message}`);
    }
  }

  for (const entry of rotations) {
    try {
      const response = await fetch(`/api/keys/${entry.key_id}/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          replaced: true,
          keep_name: entry.keep_name,
          name: entry.name,
          type: entry.type,
          address_path: entry.address_path,
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.error || "The key could not be rotated.");
      }
      const result = await response.json();
      settings = result.settings || settings;
      rotated.push(entry.key_id);
      closed.push(...(result.acknowledged || []));
    } catch (error) {
      failed.push(`Key ${entry.key_number}: ${error.message}`);
    }
  }

  requestedRotation = null;
  renderRotation();
  rotationReplaced.checked = false;
  saveKeysButton.disabled = false;
  rotationStatus.textContent = saveSummary(renamed, rotated, closed, failed);
}

function saveSummary(renamed, rotated, closed, failed) {
  const parts = [];
  if (renamed.length) {
    parts.push(renamed.length === 1 ? "1 name saved" : `${renamed.length} names saved`);
  }
  if (rotated.length) {
    parts.push(rotated.length === 1 ? "1 key rotated" : `${rotated.length} keys rotated`);
  }
  if (!parts.length) {
    parts.push("Nothing was saved");
  }
  let summary = `${parts.join(", ")}.`;
  if (closed.length) {
    summary += ` The ${alertCountText(closed.length)} those keys raised were closed, and they come back only if a newer check raises them again.`;
  }
  if (failed.length) {
    summary += ` ${failed.join(" ")}`;
  }
  return summary;
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
    softwareList.replaceChildren(emptyState("The wallet software list could not be loaded."));
    rotationList.replaceChildren(emptyState("The keys could not be loaded."));
    return;
  }
  renderSoftware();
  renderRotation();
  scrollToRotation();
}

addSoftwareButton.addEventListener("click", () => {
  softwareList.append(softwareRow(""));
});
saveSoftwareButton.addEventListener("click", saveSoftware);
saveKeysButton.addEventListener("click", saveKeys);
loadSettings();
