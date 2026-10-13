"use strict";

const form = document.querySelector("#setup-form");
const saveButton = document.querySelector("#save-setup");
const status = document.querySelector("#setup-status");
const keyFields = document.querySelector("#key-fields");
const thresholdInput = document.querySelector("#threshold");
const keyCountInput = document.querySelector("#key-count");

// The number of key slots the page falls back to when nothing is stored yet,
// and the bounds the field enforces. The stored value decides the real count
// (section 31 point 7).
const KEY_COUNT = 3;
const MIN_KEY_COUNT = 2;
const MAX_KEY_COUNT = 15;

function slot(number) {
  return {
    name: form.querySelector(`[name="key_${number}_name"]`),
    type: form.querySelector(`[name="key_${number}_type"]`),
    addressPath: form.querySelector(`[name="key_${number}_address_path"]`),
  };
}

function currentKeyCount() {
  const value = Number.parseInt(keyCountInput.value, 10);
  if (Number.isNaN(value)) {
    return KEY_COUNT;
  }
  return Math.min(MAX_KEY_COUNT, Math.max(MIN_KEY_COUNT, value));
}

function buildFieldset(number) {
  const fieldset = document.createElement("fieldset");
  fieldset.className = "check-card";

  const legend = document.createElement("legend");
  legend.textContent = `Key ${number}`;
  fieldset.append(legend);

  const grid = document.createElement("div");
  grid.className = "field-grid";

  const nameLabel = document.createElement("label");
  nameLabel.className = "field";
  const nameSpan = document.createElement("span");
  nameSpan.textContent = "Name";
  const nameInput = document.createElement("input");
  nameInput.name = `key_${number}_name`;
  nameInput.type = "text";
  nameInput.maxLength = 60;
  nameInput.autocomplete = "off";
  nameInput.required = true;
  nameLabel.append(nameSpan, nameInput);

  const typeLabel = document.createElement("label");
  typeLabel.className = "field";
  const typeSpan = document.createElement("span");
  typeSpan.textContent = "Type";
  const typeSelect = document.createElement("select");
  typeSelect.name = `key_${number}_type`;
  typeSelect.required = true;
  for (const [value, text] of [["", "Select type"], ["hardware", "Hardware"], ["cloud", "Cloud"]]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    typeSelect.append(option);
  }
  typeLabel.append(typeSpan, typeSelect);

  grid.append(nameLabel, typeLabel);

  const pathLabel = document.createElement("label");
  pathLabel.className = "field";
  const pathSpan = document.createElement("span");
  pathSpan.textContent = "Address path";
  const pathInput = document.createElement("input");
  pathInput.name = `key_${number}_address_path`;
  pathInput.type = "text";
  pathInput.maxLength = 200;
  pathInput.autocomplete = "off";
  pathInput.required = true;
  pathLabel.append(pathSpan, pathInput);

  fieldset.append(grid, pathLabel);
  return fieldset;
}

function rebuildKeyFields() {
  // Whatever the user already typed is carried over, so changing the number of
  // key slots never throws away a key that is filled in (section 31 point 7).
  const existing = {};
  for (let number = 1; number <= MAX_KEY_COUNT; number += 1) {
    const fields = slot(number);
    if (!fields.name) {
      continue;
    }
    existing[number] = {
      name: fields.name.value,
      type: fields.type.value,
      addressPath: fields.addressPath.value,
    };
  }

  const count = currentKeyCount();
  const fieldsets = [];
  for (let number = 1; number <= count; number += 1) {
    fieldsets.push(buildFieldset(number));
  }
  keyFields.replaceChildren(...fieldsets);

  for (const [number, values] of Object.entries(existing)) {
    if (Number(number) > count) {
      continue;
    }
    const fields = slot(Number(number));
    fields.name.value = values.name;
    fields.type.value = values.type;
    fields.addressPath.value = values.addressPath;
  }
}

function fillSlot(number, key) {
  const fields = slot(number);
  if (!fields.name) {
    return;
  }
  fields.name.value = key.name;
  fields.type.value = key.type;
  fields.addressPath.value = key.address_path || "";
}

function lockForm() {
  // The setup is written once, so nothing on the page can change it afterwards
  // (sections 23.2 and 25.1).
  for (const field of form.querySelectorAll("input, select, button")) {
    field.disabled = true;
  }
}

function collectSetup() {
  const entries = [];
  const count = currentKeyCount();
  for (let number = 1; number <= count; number += 1) {
    const fields = slot(number);
    entries.push({
      key_number: number,
      name: fields.name.value.trim(),
      type: fields.type.value,
      address_path: fields.addressPath.value.trim(),
    });
  }
  return {
    threshold: Number.parseInt(thresholdInput.value, 10),
    key_count: count,
    keys: entries,
  };
}

function showLockedState() {
  // The type and the address path are locked with the setup, while the name is
  // only a label that the settings may change (sections 25.1 and 25.2).
  const note = document.createElement("span");
  note.textContent = "The key setup is already saved. The type and the address path are locked; the key names can be changed in the settings. ";
  const link = document.createElement("a");
  link.className = "back-link";
  link.href = "/settings";
  link.textContent = "Open settings";
  status.replaceChildren(note, link);
}

async function loadSetup() {
  rebuildKeyFields();
  try {
    const response = await fetch("/api/setup", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("The key setup is unavailable.");
    }
    const setup = await response.json();
    if (typeof setup.threshold === "number") {
      thresholdInput.value = String(setup.threshold);
    }
    if (typeof setup.key_count === "number") {
      keyCountInput.value = String(setup.key_count);
    }
    // The stored key count decides how many fieldsets the page shows.
    rebuildKeyFields();
    if (!setup.configured) {
      status.textContent = "";
      return;
    }
    (setup.keys || []).forEach((key) => fillSlot(key.key_number, key));
    lockForm();
    showLockedState();
  } catch {
    lockForm();
    status.textContent = "The key setup could not be loaded. Reload the page or contact the service administrator.";
  }
}

async function saveSetup(event) {
  event.preventDefault();
  if (!form.reportValidity()) {
    return;
  }
  saveButton.disabled = true;
  status.textContent = "Saving…";
  try {
    const response = await fetch("/api/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(collectSetup()),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The key setup could not be saved.");
    }
    status.textContent = "Key setup saved.";
    window.location.assign("/");
  } catch (error) {
    status.textContent = error.message;
    saveButton.disabled = false;
  }
}

keyCountInput.addEventListener("change", () => {
  if (!keyCountInput.disabled) {
    rebuildKeyFields();
  }
});
form.addEventListener("submit", saveSetup);
loadSetup();
