"use strict";

const listSection = document.querySelector("#history-list");
const detailSection = document.querySelector("#history-detail");
const detailTitle = document.querySelector("#history-detail-title");
const detailBody = document.querySelector("#history-detail-body");
const requestedId = new URLSearchParams(window.location.search).get("id");

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
    ["Wallet software", record.wallet_software],
    ["Software version", record.software_version],
    ["Software compatibility", record.software_compatibility_status],
    ["Software notes", record.software_comments],
    ["Contact details confirmed", displayFlag(record.contact_info_verified)],
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
    entries.push(["Firmware version", keyCheck.firmware_version]);
    entries.push(["Seed backup verified", keyCheck.seed_backup_verified]);
  } else {
    entries.push(["Cloud health check", keyCheck.cloud_health_status]);
    entries.push(["Provider operational", displayFlag(keyCheck.cloud_provider_operational)]);
  }
  entries.push(["Address path verified", keyCheck.address_path_verified]);
  entries.push(["Address path", keyCheck.address_path]);
  entries.push(["Comments", keyCheck.comments]);
  return entries;
}

function toolCheckTable(toolChecks) {
  const headers = ["Product", "BIP327", "SLIP39"];
  // Older records stored a version, a date, and notes for each product.
  const hasLegacyColumns = toolChecks.some(
    (entry) => entry.version || entry.checked_at || entry.notes,
  );
  if (hasLegacyColumns) {
    headers.push("Version", "Date checked", "Notes");
  }
  const rows = toolChecks.map((entry) => {
    const row = [entry.product, entry.bip327_status, entry.slip39_status];
    if (hasLegacyColumns) {
      row.push(entry.version, entry.checked_at, entry.notes);
    }
    return row;
  });
  return dataTable(headers, rows);
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

  fragment.append(card("BIP327 and SLIP39", toolCheckTable(record.tool_checks || [])));

  fragment.append(card("Security status", dataTable(
    ["Provider", "Status", "Comment"],
    (record.ai_security_checks || []).map((entry) => [entry.provider, entry.status, entry.comments]),
  )));

  detailBody.replaceChildren(fragment);
  detailSection.hidden = false;
}

function keyNumbersText(check) {
  const numbers = check.key_numbers || [];
  if (!numbers.length) {
    return "Key not recorded";
  }
  return numbers.map((number) => `Key ${number}`).join(", ");
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
    meta.textContent = `${keyNumbersText(check)} · Next check due ${check.next_check_due} · Software ${check.software_compatibility_status}`;
    text.append(heading, meta);

    const link = document.createElement("a");
    link.className = "secondary-button";
    link.href = `/history?id=${check.id}`;
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
    detailSection.hidden = false;
  }
}

loadList();
loadDetail();
