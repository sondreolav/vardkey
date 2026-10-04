"use strict";

const form = document.querySelector("#setup-form");
const saveButton = document.querySelector("#save-setup");
const status = document.querySelector("#setup-status");

// The app always configures exactly three key slots (section 23.2).
const KEY_COUNT = 3;

function slot(number) {
  return {
    name: form.querySelector(`[name="key_${number}_name"]`),
    type: form.querySelector(`[name="key_${number}_type"]`),
    addressPath: form.querySelector(`[name="key_${number}_address_path"]`),
  };
}

function fillSlot(number, key) {
  const fields = slot(number);
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
  for (let number = 1; number <= KEY_COUNT; number += 1) {
    const fields = slot(number);
    entries.push({
      key_number: number,
      name: fields.name.value.trim(),
      type: fields.type.value,
      address_path: fields.addressPath.value.trim(),
    });
  }
  return { keys: entries };
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
  try {
    const response = await fetch("/api/setup", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("The key setup is unavailable.");
    }
    const setup = await response.json();
    if (!setup.configured) {
      status.textContent = "";
      return;
    }
    // The stored keys arrive in key order, so the slot number is their index.
    (setup.keys || []).forEach((key, index) => fillSlot(index + 1, key));
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

form.addEventListener("submit", saveSetup);
loadSetup();
