"use strict";

const keyList = document.querySelector("#key-list");
const keyCount = document.querySelector("#key-count");
const nextCheckTitle = document.querySelector("#next-check-title");
const nextCheckDetail = document.querySelector("#next-check-detail");
const overdueTitle = document.querySelector("#overdue-title");
const overdueDetail = document.querySelector("#overdue-detail");
const alertsList = document.querySelector("#alerts-list");
const alertCount = document.querySelector("#alert-count");

function createEmptyState(text) {
  const message = document.createElement("p");
  message.className = "empty-state";
  message.textContent = text;
  return message;
}

function formatLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isOverdue(entry) {
  // ISO dates compare correctly as text, so no parsing is needed here.
  return Boolean(entry.next_check_due) && entry.next_check_due < formatLocalDate(new Date());
}

function statusLabel(entry) {
  if (!entry.next_check_due) {
    return "Never checked";
  }
  return isOverdue(entry) ? "Overdue" : "Up to date";
}

function statusClass(entry) {
  if (!entry.next_check_due) {
    return "status-neutral";
  }
  return isOverdue(entry) ? "status-overdue" : "status-ok";
}

function appendDateRow(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value || "—";
  list.append(term, detail);
}

function createKeyCard(entry) {
  const card = document.createElement("article");
  card.className = "key-card";

  const top = document.createElement("div");
  top.className = "key-card-top";

  const number = document.createElement("span");
  number.className = "key-number";
  number.textContent = String(entry.key_number).padStart(2, "0");

  const status = document.createElement("span");
  status.className = `status ${statusClass(entry)}`;
  status.textContent = statusLabel(entry);

  const name = document.createElement("h3");
  name.textContent = entry.name;

  const type = document.createElement("p");
  type.textContent = entry.type === "cloud" ? "Cloud key" : "Hardware key";

  const dates = document.createElement("dl");
  dates.className = "key-dates";
  appendDateRow(dates, "Last checked", entry.last_checked_at);
  appendDateRow(dates, "Next check due", entry.next_check_due);

  top.append(number, status);
  card.append(top, name, type, dates);
  return card;
}

function renderSummary(status) {
  const scheduled = status.filter((entry) => entry.next_check_due);
  if (!scheduled.length) {
    nextCheckTitle.textContent = "Not scheduled";
    nextCheckDetail.textContent = "No key has a next check date yet. Save a health check to schedule one.";
  } else {
    const earliest = scheduled.reduce((first, entry) => (
      entry.next_check_due < first.next_check_due ? entry : first
    ));
    nextCheckTitle.textContent = earliest.next_check_due;
    nextCheckDetail.textContent = `Earliest next check, for key ${earliest.key_number}: ${earliest.name}.`;
  }

  const overdue = status.filter(isOverdue);
  if (!overdue.length) {
    overdueTitle.textContent = "Nothing overdue";
    overdueDetail.textContent = "No key has passed its next check date.";
  } else {
    overdueTitle.textContent = overdue.length === 1 ? "1 key overdue" : `${overdue.length} keys overdue`;
    overdueDetail.textContent = overdue
      .map((entry) => `Key ${entry.key_number}: ${entry.name} (due ${entry.next_check_due})`)
      .join(" · ");
  }
}

function createAlertItem(alert) {
  const item = document.createElement("li");
  item.className = `alert-item alert-${alert.severity}`;

  const source = document.createElement("strong");
  source.textContent = alert.source;

  const message = document.createElement("p");
  message.textContent = alert.message;

  // Every alert names the saved check it came from (section 21).
  const origin = document.createElement("p");
  origin.className = "alert-origin";
  origin.textContent = `From check ${alert.check_id} · ${alert.checked_at}`;

  item.append(source, message, origin, createAlertActions(alert));
  return item;
}

function createAlertActions(alert) {
  // Every alert names the actions that close it, and each action requires a
  // confirmation from the user (section 25.3).
  const actions = document.createElement("div");
  actions.className = "alert-actions";
  for (const action of alert.actions || []) {
    if (action === "rotate" && alert.key_id) {
      const link = document.createElement("a");
      link.className = "secondary-button";
      link.href = `/settings?rotate=${encodeURIComponent(alert.key_id)}`;
      link.textContent = "Rotate key";
      actions.append(link);
    }
    if (action === "acknowledge") {
      actions.append(createCloseControl(alert));
    }
  }
  return actions;
}

function createCloseControl(alert) {
  const wrapper = document.createElement("div");
  wrapper.className = "alert-close";

  const open = document.createElement("button");
  open.type = "button";
  open.className = "secondary-button";
  open.textContent = "Close alert";

  const panel = document.createElement("div");
  panel.className = "form-stack";
  panel.hidden = true;

  const label = document.createElement("label");
  label.className = "field";
  const labelText = document.createElement("span");
  labelText.textContent = "Reason for closing this alert";
  const reason = document.createElement("textarea");
  reason.rows = 2;
  reason.maxLength = 2000;
  label.append(labelText, reason);

  const confirmButton = document.createElement("button");
  confirmButton.type = "button";
  confirmButton.className = "primary-button active-button";
  confirmButton.textContent = "Confirm close";

  const cancelButton = document.createElement("button");
  cancelButton.type = "button";
  cancelButton.className = "secondary-button";
  cancelButton.textContent = "Cancel";

  const buttons = document.createElement("div");
  buttons.className = "form-actions";
  buttons.append(confirmButton, cancelButton);

  const status = document.createElement("p");
  status.className = "workflow-note";
  status.setAttribute("role", "status");

  panel.append(label, buttons, status);
  wrapper.append(open, panel);

  open.addEventListener("click", () => {
    open.hidden = true;
    panel.hidden = false;
    reason.focus();
  });
  cancelButton.addEventListener("click", () => {
    panel.hidden = true;
    open.hidden = false;
    status.textContent = "";
  });
  confirmButton.addEventListener("click", () => acknowledgeAlert(alert, reason, status, confirmButton));
  return wrapper;
}

async function acknowledgeAlert(alert, reason, status, button) {
  const text = reason.value.trim();
  if (!text) {
    status.textContent = "Write a short reason before you close the alert.";
    return;
  }
  button.disabled = true;
  status.textContent = "Closing…";
  try {
    const response = await fetch("/api/alerts/acknowledge", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ code: alert.code, source: alert.source, reason: text }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The alert could not be closed.");
    }
    await loadAlerts();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

async function redirectWhenSetupIsMissing() {
  try {
    const response = await fetch("/api/setup", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      return;
    }
    const setup = await response.json();
    if (!setup.configured) {
      // A new database has no key setup yet, so the dashboard has nothing to
      // show and the first-run setup step comes first (section 23.2).
      window.location.assign("/setup");
    }
  } catch {
    // A failed request is reported by the sections below, each in its own way.
  }
}

async function loadKeyStatus() {
  try {
    const response = await fetch("/api/key-status", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Key status is unavailable.");
    }

    const status = await response.json();
    keyList.replaceChildren(...status.map(createKeyCard));
    keyCount.textContent = `${status.length} keys`;
    renderSummary(status);
  } catch {
    keyList.replaceChildren(createEmptyState(
      "Key status is unavailable. Please reload the page or contact the service administrator.",
    ));
    keyCount.textContent = "Unavailable";
    nextCheckTitle.textContent = "Unavailable";
    nextCheckDetail.textContent = "The next check dates could not be loaded.";
    overdueTitle.textContent = "Unavailable";
    overdueDetail.textContent = "The overdue keys could not be determined.";
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
        "No alerts. No saved check has a result that needs follow-up.",
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

redirectWhenSetupIsMissing();
loadKeyStatus();
loadAlerts();
