"use strict";

const keyList = document.querySelector("#key-list");
const setupShape = document.querySelector("#setup-shape");
const overdueTitle = document.querySelector("#overdue-title");
const overdueDetail = document.querySelector("#overdue-detail");
const alertsList = document.querySelector("#alerts-list");
const alertCount = document.querySelector("#alert-count");

// The button wording of every action that closes an alert (section 26.4). The
// alert itself names the actions it offers.
const ACTION_LABELS = {
  rotate: "Rotate key",
  replace_hardware: "Replace hardware",
  remove_software: "Remove software",
  ignore: "Ignore alert",
  contact_updated: "Contact details updated",
};
// Every action has its own confirmation step, and the app never performs the
// action itself (section 26.4).
const ACTION_CONFIRMATIONS = {
  replace_hardware: "I have replaced the hardware wallet and restored the same seed on the new device.",
  remove_software: "I have stopped using this wallet software for this key, and I want to remove it from the settings.",
  ignore: "I understand that this alert is closed without a replacement, and that it comes back if a newer check raises it again.",
  contact_updated: "I have updated the contact details in my external documentation.",
};

let keyStatus = [];
let alerts = [];
// The wallet software list from the settings, so a software alert can point at
// the entry it is about (section 26.7).
let walletSoftware = [];
let keysLoaded = false;
let alertsLoaded = false;
// The browser's own view of the connection. The service worker keeps the shell,
// but every API call needs the server, so the app says so plainly instead of
// showing empty cards (section 31 point 6).
let offline = navigator.onLine === false;

function createEmptyState(text) {
  const message = document.createElement("p");
  message.className = "empty-state";
  message.textContent = text;
  return message;
}

function unavailableText(onlineText) {
  if (offline) {
    return "You are offline. VardKey needs the server for every page, so the data cannot be loaded right now. It reloads as soon as the connection is back.";
  }
  return onlineText;
}

async function fetchJson(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`${path} is unavailable.`);
  }
  return response.json();
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

function alertsForKey(keyId) {
  return alerts.filter((alert) => alert.key_id === keyId);
}

function actionLabels(actions) {
  return (actions || []).map((action) => ACTION_LABELS[action] || action).join(" or ");
}

function keyTypeLabel(type) {
  return type === "cloud" ? "Cloud" : "Hardware";
}

function sameLabel(first, second) {
  // Case and spacing do not make two labels different, so a model that only
  // repeats the key's own name says nothing (section 32.2 point 8).
  const normalize = (value) => String(value || "").toLowerCase().replace(/\s+/g, "");
  return normalize(first) === normalize(second);
}

function createKeyCard(entry) {
  const card = document.createElement("article");
  card.className = "key-card";

  const top = document.createElement("div");
  top.className = "key-card-top";

  const number = document.createElement("span");
  number.className = "key-number";
  // The number and the type share the top line, so the card has no line of its
  // own for the type (section 32.2 point 6).
  number.textContent = `${String(entry.key_number).padStart(2, "0")} · ${keyTypeLabel(entry.type)}`;

  const open = alertsForKey(entry.key_id);
  const status = document.createElement("span");
  if (open.length) {
    // A key with an open alert needs the user's attention instead of its
    // ordinary status, and it cannot be checked until the alert is closed
    // (sections 26.1 and 26.5).
    status.className = "status status-alert";
    status.textContent = "Needs action";
  } else {
    status.className = `status ${statusClass(entry)}`;
    status.textContent = statusLabel(entry);
  }

  const name = document.createElement("h3");
  name.textContent = entry.name;

  // The model is documentation only, and it is shown under the name with no
  // label. A model that only repeats the key's own name is left out
  // (section 32.2 point 8).
  let model = null;
  if (entry.model && !sameLabel(entry.model, entry.name)) {
    model = document.createElement("p");
    model.className = "key-model";
    model.textContent = entry.model;
  }

  // The address path is part of the identity of a key, so the card shows it on
  // its own, without a label. An empty path, which a migrated key can have, is
  // left out (sections 31.4 and 32.2 point 7).
  const path = document.createElement("p");
  path.className = "key-path";
  if (entry.address_path) {
    path.textContent = entry.address_path;
  }

  top.append(number, status);
  card.append(top, name);
  if (model) {
    card.append(model);
  }
  if (entry.address_path) {
    card.append(path);
  }

  // The next due date stays visible with an open alert, so the card never hides
  // the date of a key that only needs an informational follow-up
  // (sections 27 and 32.2 point 9).
  const dates = document.createElement("dl");
  dates.className = "key-dates";
  appendDateRow(dates, "Next check due", entry.next_check_due);
  card.append(dates);

  if (open.length) {
    card.append(createKeyAlertNote(entry, open));
  }
  return card;
}

function createKeyAlertNote(entry, open) {
  // The card says how many alerts are open, that the key needs action before it
  // can be checked again, and which action closes them, with a link to the alert
  // list for the rest (section 26.5).
  const note = document.createElement("div");
  note.className = "key-alert-note";

  const message = document.createElement("p");
  message.className = "key-alert-message";
  message.textContent = open.length === 1
    ? "1 open alert. This key needs action, and it cannot be checked until the alert is closed."
    : `${open.length} open alerts. This key needs action, and it cannot be checked until they are closed.`;
  note.append(message);

  const first = open[0];
  const detail = document.createElement("p");
  detail.className = "key-alert-detail";
  detail.textContent = `Close it with: ${actionLabels(first.actions)} (${first.source}).`;
  note.append(detail);

  const link = document.createElement("a");
  link.className = "back-link";
  link.href = "#alerts-list";
  link.textContent = "Open the alert list";
  note.append(link);
  return note;
}

function renderSetupHeading(setup) {
  // The heading reads the threshold and the key count from the API, because the
  // single setup may be any shape, not only 2-of-3 (sections 31 point 7 and
  // 32.2 point 3). The line that stands in the markup is the fallback until the
  // setup has been read.
  if (!setup || typeof setup.threshold !== "number" || typeof setup.key_count !== "number") {
    return;
  }
  setupShape.textContent = `Bitcoin Health Monitor for a ${setup.threshold}-of-${setup.key_count} Multisig Setup.`;
}

function renderSummary(status) {
  // The Attention card is the only summary card now that the Next check card is
  // gone, so it carries the earliest due date when nothing is overdue
  // (section 32.7 point 3).
  const overdue = status.filter(isOverdue);
  if (overdue.length) {
    overdueTitle.textContent = overdue.length === 1 ? "1 key overdue" : `${overdue.length} keys overdue`;
    overdueDetail.textContent = overdue
      .map((entry) => `Key ${entry.key_number}: ${entry.name} (due ${entry.next_check_due})`)
      .join(" · ");
    return;
  }

  overdueTitle.textContent = "Nothing overdue";
  const scheduled = status.filter((entry) => entry.next_check_due);
  if (!scheduled.length) {
    overdueDetail.textContent = "No key has a next check date yet. Save a health check to schedule one.";
    return;
  }
  const earliest = scheduled.reduce((first, entry) => (
    entry.next_check_due < first.next_check_due ? entry : first
  ));
  overdueDetail.textContent = `Earliest next check ${earliest.next_check_due}, for Key ${earliest.key_number}: ${earliest.name}.`;
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
  // Every alert names the actions that close it, and each action has its own
  // button text and its own confirmation step (section 26.4).
  const actions = document.createElement("div");
  actions.className = "alert-actions";
  for (const action of alert.actions || []) {
    if (action === "rotate") {
      actions.append(createRotateLink(alert));
      continue;
    }
    if (action === "remove_software") {
      actions.append(createRemoveSoftwareControl(alert));
      continue;
    }
    actions.append(createConfirmControl(
      ACTION_LABELS[action] || action,
      ACTION_CONFIRMATIONS[action] || "I confirm this action.",
      (status, button) => acknowledgeAlert(alert, action, status, button),
    ));
  }
  return actions;
}

function createRotateLink(alert) {
  // A rotation replaces the key and is confirmed in the settings, where the new
  // address path is recorded (sections 26.3 and 26.4).
  const link = document.createElement("a");
  link.className = "secondary-button";
  link.href = alert.key_id
    ? `/settings?rotate=${encodeURIComponent(alert.key_id)}`
    : "/settings";
  link.textContent = ACTION_LABELS.rotate;
  return link;
}

function createConfirmControl(text, confirmationText, onConfirm) {
  const wrapper = document.createElement("div");
  wrapper.className = "alert-close";

  const open = document.createElement("button");
  open.type = "button";
  open.className = "secondary-button";
  open.textContent = text;

  const panel = document.createElement("div");
  panel.className = "form-stack";
  panel.hidden = true;

  const label = document.createElement("label");
  label.className = "field checkbox-field";
  const confirm = document.createElement("input");
  confirm.type = "checkbox";
  const textSpan = document.createElement("span");
  textSpan.textContent = confirmationText;
  label.append(confirm, textSpan);

  const confirmButton = document.createElement("button");
  confirmButton.type = "button";
  confirmButton.className = "primary-button active-button";
  confirmButton.textContent = `Confirm ${text.toLowerCase()}`;

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
    confirm.focus();
  });
  cancelButton.addEventListener("click", () => {
    panel.hidden = true;
    open.hidden = false;
    status.textContent = "";
  });
  confirmButton.addEventListener("click", () => {
    if (!confirm.checked) {
      status.textContent = "Confirm the action before you continue.";
      return;
    }
    onConfirm(status, confirmButton);
  });
  return wrapper;
}

function createRemoveSoftwareControl(alert) {
  // Removing the failing software from the settings closes the alert, and the
  // alert names the software it is about, so the removal points at the right
  // entry (section 26.7).
  const software = alert.software;
  const removable = Boolean(software)
    && walletSoftware.includes(software)
    && walletSoftware.length > 1;
  if (!removable) {
    // The list may never be empty, so a single entry has to be replaced in the
    // settings first (sections 25.4 and 26.7).
    const link = document.createElement("a");
    link.className = "secondary-button";
    link.href = "/settings";
    link.textContent = "Open the settings";
    return link;
  }
  return createConfirmControl(
    `Remove ${software} from the settings`,
    ACTION_CONFIRMATIONS.remove_software,
    (status, button) => removeSoftware(software, status, button),
  );
}

async function removeSoftware(software, status, button) {
  button.disabled = true;
  status.textContent = "Removing…";
  try {
    const remaining = walletSoftware.filter((name) => name !== software);
    const response = await fetch("/api/settings/wallet-software", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ wallet_software: remaining }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The wallet software could not be removed.");
    }
    await loadDashboard();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

async function acknowledgeAlert(alert, action, status, button) {
  button.disabled = true;
  status.textContent = "Closing…";
  try {
    const response = await fetch("/api/alerts/acknowledge", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ code: alert.code, source: alert.source, action: action }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || "The alert could not be closed.");
    }
    await loadDashboard();
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

function renderKeyCards() {
  if (!keysLoaded) {
    keyList.replaceChildren(createEmptyState(unavailableText(
      "Key status is unavailable. Please reload the page or contact the service administrator.",
    )));
    overdueTitle.textContent = "Unavailable";
    overdueDetail.textContent = "The overdue keys could not be determined.";
    return;
  }
  keyList.replaceChildren(...keyStatus.map(createKeyCard));
  renderSummary(keyStatus);
}

function renderAlerts() {
  if (!alertsLoaded) {
    alertsList.replaceChildren(createEmptyState(unavailableText(
      "Alerts could not be loaded. Please reload the page.",
    )));
    alertCount.textContent = "Unavailable";
    return;
  }
  if (!alerts.length) {
    // An empty list carries no text of its own: the count beside the heading
    // already says that there is nothing to follow up (section 32.7 point 4).
    alertsList.replaceChildren();
    alertCount.textContent = "No alerts";
    return;
  }

  const list = document.createElement("ul");
  list.className = "alert-list";
  list.append(...alerts.map(createAlertItem));
  alertsList.replaceChildren(list);
  alertCount.textContent = alerts.length === 1 ? "1 alert" : `${alerts.length} alerts`;
}

async function loadDashboard() {
  const [statusResult, alertResult, settingsResult, setupResult] = await Promise.allSettled([
    fetchJson("/api/key-status"),
    fetchJson("/api/alerts"),
    fetchJson("/api/settings"),
    fetchJson("/api/setup"),
  ]);

  if (settingsResult.status === "fulfilled") {
    // The wallet software list tells a software alert whether the failing entry
    // can be removed from here (section 26.7).
    walletSoftware = settingsResult.value.wallet_software || [];
  }
  if (alertResult.status === "fulfilled") {
    alerts = alertResult.value;
    alertsLoaded = true;
  }
  if (statusResult.status === "fulfilled") {
    keyStatus = statusResult.value;
    keysLoaded = true;
  }
  if (setupResult.status === "fulfilled") {
    // The setup shape is what the heading under the title reads
    // (section 32.2 point 3).
    renderSetupHeading(setupResult.value);
  }

  renderKeyCards();
  renderAlerts();
}

function registerServiceWorker() {
  // The worker caches only the shell, so the pages stay reachable while the
  // server is down. It only registers in a secure context, which StartOS
  // provides over HTTPS and which http://localhost also is; a LAN IP over plain
  // HTTP does not register one (section 31 point 6).
  if (!("serviceWorker" in navigator)) {
    return;
  }
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // A browser that refuses the worker still gets the whole app; only the
    // offline shell is lost.
  });
}

window.addEventListener("online", () => {
  // The shell may have come from the cache, so a reload is what fetches the
  // live data again.
  window.location.reload();
});

window.addEventListener("offline", () => {
  offline = true;
  keysLoaded = false;
  alertsLoaded = false;
  renderKeyCards();
  renderAlerts();
});

registerServiceWorker();
redirectWhenSetupIsMissing();
loadDashboard();
