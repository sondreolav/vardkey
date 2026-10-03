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
  };
}

function fillSlot(number, key) {
  const fields = slot(number);
  fields.name.value = key.name;
  fields.type.value = key.type;
}

function lockForm() {
  // The names and the types are locked once the setup is saved, so nothing on
  // the page can change them afterwards (section 23.2).
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
    });
  }
  return { keys: entries };
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
    status.textContent = "The key setup is already saved. The names and the types are locked.";
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
