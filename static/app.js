"use strict";

const keyList = document.querySelector("#key-list");
const keyCount = document.querySelector("#key-count");

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
    keyList.replaceChildren();
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent = "Key profiles are unavailable. Please reload the page or contact the service administrator.";
    keyList.append(message);
    keyCount.textContent = "Unavailable";
  }
}

loadKeys();
