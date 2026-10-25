"use strict";

const listSection = document.querySelector("#history-list");
const detailSection = document.querySelector("#history-detail");
const detailTitle = document.querySelector("#history-detail-title");
const detailBody = document.querySelector("#history-detail-body");
const requestedId = new URLSearchParams(window.location.search).get("id");

// The readable wording of every action that closes an alert (section 26.4). The
// dashboard and the form carry the same map, and it is duplicated here on
// purpose, so the history can show the action that was carried out
// (section 27).
const ACTION_LABELS = {
  rotate: "Rotate key",
  replace_hardware: "Replace hardware",
  remove_software: "Remove software",
  ignore: "Ignore alert",
  contact_updated: "Contact details updated",
};

function display(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

function displayFlag(value) {
  if (value === 1) {
    return "Yes";
  }
  if (value === 0) {
    return "No";
  }
  return "—";
}

function mergedLine(...values) {
  // Two values that belong together are shown on one line, for example
  // "Sparrow Wallet 2.5.1" or "Blockstream Jade 1.4.1". A missing part is left
  // out, and a line with nothing to show is the same dash as everywhere else.
  const parts = values.filter(
    (value) => value !== null && value !== undefined && value !== "",
  );
  return parts.length ? parts.join(" ") : "—";
}

function emptyNote(text) {
  const note = document.createElement("p");
  note.className = "empty-state";
  note.textContent = text;
  return note;
}

function definitionList(entries) {
  const list = document.createElement("dl");
  list.className = "detail-list";
  for (const [label, value] of entries) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = display(value);
    list.append(term, detail);
  }
  return list;
}

function dataTable(headers, rows) {
  const table = document.createElement("table");
  table.className = "detail-table";

  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const header of headers) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = header;
    headRow.append(cell);
  }
  head.append(headRow);

  const body = document.createElement("tbody");
  for (const row of rows) {
    const bodyRow = document.createElement("tr");
    for (const value of row) {
      const cell = document.createElement("td");
      cell.textContent = display(value);
      bodyRow.append(cell);
    }
    body.append(bodyRow);
  }

  table.append(head, body);
  return table;
}

function card(title, content) {
  const section = document.createElement("section");
  section.className = "detail-card";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading, content);
  return section;
}

function keyLabel(record) {
  // The key name is read from the key row, so a saved check shows the name the
  // key has now, which the settings may change (section 25.2).
  const labels = (record.key_checks || []).map(
    (entry) => `Key ${entry.key_number}: ${entry.name}`,
  );
  return labels.length ? labels.join(", ") : "—";
}

function summaryEntries(record) {
  const entries = [
    ["Check date", record.checked_at],
    ["Next check due", record.next_check_due],
    ["Key checked", keyLabel(record)],
    // The wallet software and its version belong together, so they share one
    // line: "Sparrow Wallet 2.5.1". A missing version leaves the software on
    // its own, and a check without either shows a dash.
    ["Wallet software", mergedLine(record.wallet_software, record.software_version)],
    ["Software compatibility", record.software_compatibility_status],
    ["Software notes", record.software_comments],
    // The contact confirmation is a stored status, so it is shown as text
    // (section 23.1).
    ["Contact details confirmed", record.contact_info_verified],
    ["Comments", record.comments],
  ];
  if (record.sparrow_version) {
    entries.push(["Sparrow version (legacy record)", record.sparrow_version]);
  }
  if (record.nunchuk_version) {
    entries.push(["Nunchuk version (legacy record)", record.nunchuk_version]);
  }
  return entries;
}

function keyEntries(keyCheck) {
  const entries = [["Availability", displayFlag(keyCheck.available)]];
  if (keyCheck.type === "hardware") {
    entries.push(["Hardware works", displayFlag(keyCheck.hardware_works)]);
    // The hardware model and the firmware version belong together, so they
    // share one line: "Blockstream Jade 1.4.1". Either one alone is shown on
    // its own, and a key without both shows a dash.
    entries.push([
      "Hardware and firmware",
      mergedLine(keyCheck.model, keyCheck.firmware_version),
    ]);
    entries.push(["Seed backup verified", keyCheck.seed_backup_verified]);
  }
  // The user records the address path only; the verification result is derived
  // by the server, so it is shown as a derived value (sections 9 and 25.1).
  entries.push(["Address path", keyCheck.address_path]);
  entries.push(["Address path verified (derived)", keyCheck.address_path_verified]);
  entries.push(["Comments", keyCheck.comments]);
  return entries;
}

function securityTable(securityChecks) {
  if (!securityChecks.length) {
    return emptyNote("No security statuses were recorded for this check.");
  }
  return dataTable(
    ["Provider", "Status", "Comment"],
    securityChecks.map((entry) => [entry.provider, entry.status, entry.comments]),
  );
}

function closedAlertsTable(closedAlerts) {
  // Every closure of the check is shown with the source of the alert it closed,
  // the code, the action written out as a readable label, and the date
  // (section 27). The source is what tells the key form and the software form
  // of the same code apart, so it has a column of its own (section 32.9
  // point 1).
  if (!closedAlerts.length) {
    return emptyNote("No follow-up was closed on this check.");
  }
  return dataTable(
    ["Source", "Alert", "Action", "Closed"],
    closedAlerts.map((entry) => [
      entry.source,
      entry.code,
      ACTION_LABELS[entry.action] || entry.action,
      entry.acknowledged_at,
    ]),
  );
}

function revealDetail() {
  // The detail section is hidden until a check is opened, and a hidden element
  // has no box, so the browser cannot jump to #history-detail on its own. The
  // section is revealed first and the page moves to it afterwards
  // (section 32.7 follow-up point 3).
  detailSection.hidden = false;
  detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDetail(record) {
  detailTitle.textContent = `Check from ${record.checked_at}`;
  const fragment = document.createDocumentFragment();

  fragment.append(card("Summary", definitionList(summaryEntries(record))));

  for (const keyCheck of record.key_checks || []) {
    fragment.append(card(
      `Key ${keyCheck.key_number}: ${keyCheck.name}`,
      definitionList(keyEntries(keyCheck)),
    ));
  }

  fragment.append(card("Security status", securityTable(record.ai_security_checks || [])));
  fragment.append(card("Follow-up closed", closedAlertsTable(record.closed_alerts || [])));

  detailBody.replaceChildren(fragment);
  revealDetail();
}

function keyNamesText(check) {
  // The card names the key by its number and the name it has now, which the
  // settings may change (sections 25.2 and 32.2 point 14).
  const numbers = check.key_numbers || [];
  const names = check.key_names || [];
  if (!numbers.length) {
    return "Key not recorded";
  }
  return numbers
    .map((number, index) => `Key ${number}: ${names[index] || "—"}`)
    .join(", ");
}

function followUpText(check) {
  // The card reports the state of the check as it stands now, in three steps:
  // nothing was raised, something is still open, or everything that was raised
  // is closed (section 32.9 point 2). needs_follow_up is frozen at save time,
  // while follow_up_open follows the merged, unacknowledged alerts the
  // dashboard shows, so an alert a newer check re-raised is the newer check's.
  if (!check.needs_follow_up) {
    return "All OK";
  }
  return check.follow_up_open ? "Needs follow-up" : "Follow-up closed";
}

function renderList(checks) {
  listSection.replaceChildren();
  if (!checks.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No health checks have been saved yet.";
    listSection.append(empty);
    return;
  }

  const list = document.createElement("ul");
  list.className = "history-list";
  for (const check of checks) {
    const item = document.createElement("li");
    item.className = "history-item";

    const text = document.createElement("div");
    const heading = document.createElement("h3");
    heading.textContent = check.checked_at;
    const meta = document.createElement("p");
    meta.textContent = `${keyNamesText(check)} · ${followUpText(check)}`;
    text.append(heading, meta);

    // The link carries the anchor of the detail section, so the browser lands on
    // the check that was opened and not at the top of the page
    // (section 32.7 follow-up point 3).
    const link = document.createElement("a");
    link.className = "secondary-button";
    link.href = `/history?id=${check.id}#history-detail`;
    link.textContent = "View";

    item.append(text, link);
    list.append(item);
  }
  listSection.append(list);
}

async function loadList() {
  try {
    const response = await fetch("/api/health-checks", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Saved checks are unavailable.");
    }
    renderList(await response.json());
  } catch {
    listSection.replaceChildren();
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent = "Saved health checks could not be loaded. Please reload the page.";
    listSection.append(message);
  }
}

async function loadDetail() {
  if (!requestedId) {
    return;
  }
  try {
    const response = await fetch(`/api/health-checks/${encodeURIComponent(requestedId)}`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error("Health check not found.");
    }
    renderDetail(await response.json());
  } catch {
    detailTitle.textContent = "Health check not found";
    detailBody.replaceChildren();
    revealDetail();
  }
}

loadList();
loadDetail();
