"use strict";

const keyList = document.querySelector("#key-list");
const keyCount = document.querySelector("#key-count");
const lastCheckTitle = document.querySelector("#last-check-title");
const nextCheckTitle = document.querySelector("#next-check-title");
const alertsList = document.querySelector("#alerts-list");
const alertCount = document.querySelector("#alert-count");

function createEmptyState(text) {
  const message = document.createElement("p");
  message.className = "empty-state";
  message.textContent = text;
  return message;
}

function createKeyCard(key) {
  const card = document.createElement("article");
  card.className = "key-card";

  const top = document.createElement("div");
  top.className = "key-card-top";

  const number = document.createElement("span");
  number.className = "key-number";
  number.textContent = String(key.key_number).padStart(2, "0");

  const status = document.createElement("span");
  status.className = "status status-neutral";
  status.textContent = "Profile configured";

  const name = document.createElement("h3");
  name.textContent = key.name;

  const type = document.createElement("p");
  type.textContent = key.type === "cloud" ? "Cloud key" : "Hardware key";

  top.append(number, status);
  card.append(top, name, type);
  return card;
}

function createAlertItem(alert) {
  const item = document.createElement("li");
  item.className = `alert-item alert-${alert.severity}`;

  const source = document.createElement("strong");
  source.textContent = alert.source;

  const message = document.createElement("p");
  message.textContent = alert.message;

  item.append(source, message);
  return item;
}

async function loadKeys() {
  try {
    const response = await fetch("/api/keys", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("The key profiles could not be loaded.");
    }

    const keys = await response.json();
    keyList.replaceChildren(...keys.map(createKeyCard));
    keyCount.textContent = `${keys.length} keys`;
  } catch {
    keyList.replaceChildren(createEmptyState(
      "Key profiles are unavailable. Please reload the page or contact the service administrator.",
    ));
    keyCount.textContent = "Unavailable";
  }
}

async function loadSummary() {
  try {
    const response = await fetch("/api/health-checks", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Saved checks are unavailable.");
    }

    const checks = await response.json();
    if (checks.length) {
      lastCheckTitle.textContent = checks[0].checked_at;
      nextCheckTitle.textContent = checks[0].next_check_due;
    }
  } catch {
    lastCheckTitle.textContent = "Unavailable";
    nextCheckTitle.textContent = "Unavailable";
  }
}

async function loadAlerts() {
  try {
    const response = await fetch("/api/alerts", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Alerts are unavailable.");
    }

    const alerts = await response.json();
    if (!alerts.length) {
      alertsList.replaceChildren(createEmptyState(
        "No alerts. The most recent saved check has no result that needs follow-up.",
      ));
      alertCount.textContent = "No alerts";
      return;
    }

    const list = document.createElement("ul");
    list.className = "alert-list";
    list.append(...alerts.map(createAlertItem));
    alertsList.replaceChildren(list);
    alertCount.textContent = alerts.length === 1 ? "1 alert" : `${alerts.length} alerts`;
  } catch {
    alertsList.replaceChildren(createEmptyState(
      "Alerts could not be loaded. Please reload the page.",
    ));
    alertCount.textContent = "Unavailable";
  }
}

loadKeys();
loadSummary();
loadAlerts();
