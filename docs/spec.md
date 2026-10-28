# VardKey specification

VardKey records the annual health check of one Bitcoin multisig setup, 2-of-3 by default. It is a
local web app that runs as a StartOS 0.4.0 service, and it records results and history only.

**This specification is closed.** Everything in it is implemented and verified, and §32 holds
nothing. It is written in English, like the rest of the repository; the earlier Norwegian revision is
in the git history.

**The section numbers are stable.** The code, the tests and the other documents cite them — for
example `export.py` cites §19 and §27, and `static/history.js` cites §26 and §32.9 — so a section is
never renumbered and never reused. New work gets a new section at the end, and its rules are written
into §1–§18 rather than left in the new section.

**A citation may also name a point inside a round**, such as §25.1, §26.4 or §31 point 1. Those
point numbers are the ones the round had when it was written, and the history table below keeps only
the round, so the round is what resolves today. They are left as they are for the same reason the
section numbers are: renumbering them would break every other citation and lose the record of how the
round was laid out.

- **§1–§18 are binding** and describe the app as it is now, not as it was built.
- **§19–§33 are history**, one line per round. The full reasoning is in the git history.
- A point without a checkbox is implemented and verified; `[ ]` marks what is still open.
- **Status:** schema version **13**, **534 green tests**, package version **`2026.10.28:0`** (tag
  `v2026.10.28_0`), built, sideloaded and run on a StartOS 0.4.0 box.

## Open, and only the maintainer can close it

- The storage, backup and StartOS box tests (§14 and §16) are run and verified, but have to be run
  **again before the first release**: the schema and the login have changed since they were last run.
- The prohibition lists in §1 and §13 are standing prohibitions, and are re-confirmed before release.

---

# 1. Scope

**In scope**

- A simple web app with a dashboard.
- Registration of the keys in the multisig setup.
- Registration of the annual health check, covering every point of the yearly checklist.
- Alerts when a check point needs follow-up.
- History of completed health checks.
- A suggested next check, about one year ahead, computed automatically.
- Report export as CSV.
- A local SQLite database.
- Persistent storage on StartOS.
- A StartOS health check.
- StartOS backup and restore.
- Password protection with one admin user, and a way to reset the app data from StartOS.

**Out of scope**

No AI integration, no Bitcoin node integration, no Bitcoin signing, no PSBT generation or signing,
no seed-phrase storage, no private-key storage, no cloud sync of app data, no external database, no
offline database, and no offline recording of checks (an installable PWA with no offline data is
allowed), no calendar integration, no advanced analysis or graphs, and no support for more than one
multisig setup: there is still exactly **one** setup, but its threshold and its number of keys are
configurable.

**Note:** this is a standing prohibition, not a work list. It is re-confirmed before release.

---

# 2. Key rules

- The app never asks for and never stores a seed phrase, a private key, a PIN, a password, or any
  other wallet secret. That covers *wallet* secrets: the admin password is the only credential the
  app stores, and it is stored as a `hashlib.scrypt` hash, never in plain text.
- A free-text field refuses a pasted wallet secret locally, before anything is stored (§15). The
  short warning against pasting a secret appears **once**, in the key setup, and is not repeated per
  field (§12 and §15).
- Contact details of key holders are never stored; only whether the contact information was
  confirmed.
- The app never pretends to have tested hardware itself. The user records the result of the test.
- The app stays local and simple. If something is not needed for the annual health check, it is not
  built.

---

# 3. Key setup

The app is built for **one** multisig setup. At first run the user gives the threshold and the number
of keys, and each key gets a name, a type (`hardware`/`cloud`), an optional model or service, and an
address path.

- The threshold is `1 ≤ threshold ≤ key_count`, and `2 ≤ key_count ≤ 15`. The app reads no meaning
  into the numbers.
- The name the user writes is the product label everywhere: the form, the alerts, the history and
  the CSV export. The key number is shown with the name where it is needed, for example
  `Key 1: ColdCard`.
- The key type decides which checks apply, never the key number.
- `type` and `address_path` are the identity of the key and are locked once the setup is stored. The
  name and the model can be changed in the settings. Only a rotation, which replaces the key with a
  new one, may give it the other type.

The default setup the app was built for, with example address paths:

| Key | Type | Device | Address path (example) |
|---|---|---|---|
| 1 | Hardware | SeedSigner | m/48'/0'/0'/2' |
| 2 | Hardware | Blockstream Jade | m/48'/1'/0'/2' |
| 3 | Cloud | Nunchuk | m/48'/2'/0'/2' |

---

# 4. Data model

SQLite, with as few tables as possible. Each table lists one column per line here; columns marked `*`
are legacy columns that exist only for old rows and are never written again.

**`keys`** — the key slots of the one setup, with one active row per `key_number` and any number of
retired rows beside it.
`id`, `key_number` (1–`multisig_key_count`), `name`, `type` (`hardware`/`cloud`), `model`,
`address_path`, `active` (`0`/`1`), `rotated_at`, `created_at`.

**`health_checks`** — one row per submission, which covers one selected key.
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`,
`software_compatibility_status`, `software_comments`, `sparrow_version*`, `nunchuk_version*`,
`contact_info_verified`, `comments`.

**`key_checks`** — one record for the selected key in each submission, with a snapshot of the key as
it was when the check was stored.
`id`, `health_check_id`, `key_id`, `key_name`, `key_type`, `key_model`, `available`,
`hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`,
`address_path`, `comments`.

**`ai_security_checks`** — AI security status per provider, carrying the checked key when the
provider is the key's own configured name.
`id`, `health_check_id`, `provider`, `key_id`, `status`, `comments`.

**`wallet_software`** — the list the user maintains in the settings.
`id`, `name`, `created_at`.

**`alert_acknowledgements`** — acknowledged alerts.
`id`, `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`.

**`app_settings`** — name/value, for what is not history.
`name` (PRIMARY KEY), `value`. Holds `multisig_threshold`, `multisig_key_count`, `admin_username`,
`admin_password_hash`, `session_secret`, `failed_login_count` and `failed_login_until`.

Rules:

- `hardware_works`, `firmware_version` and `seed_backup_verified` apply to hardware keys only.
- `seed_backup_verified` and `address_path_verified` hold only `OK` or `PROBLEM`.
- `address_path` stores the address path of that check.
- When `available` is No, the other key fields are emptied, while the key note is kept.
- When `available` is No, `wallet_software` and `ai_security_checks` are not recorded at all.
- `type` is stored once at first run and is locked afterwards; only a rotation may give the key the
  other type.
- `model` is optional free text (at most 60 characters) and is pure documentation: a hardware model
  or, for a cloud key, the name of the service. It is not part of the identity, not a wallet
  software choice, and is never used as an alert source.
- `provider` stores the configured key name and the selected software, not fixed product names.
- `contact_info_verified` is free text with two values, and has no "not assessed" value.
- `hardware_works` is required for an available hardware key.
- `name` can be changed in the settings; `type` and `address_path` are the identity of the key.
- `address_path_verified` is set by the server from a comparison with `keys.address_path`, and is
  never sent in by the user.
- `wallet_software` in `health_checks` stays free text, so older rows and removed list entries keep
  rendering correctly.
- `address_path` must be unique across all the keys of the setup: in the setup, in the settings and
  in a rotation. The comparison is canonical: `h`/`H` and `'` are the same marker, and whitespace and
  letter case are ignored. The stored value is never rewritten.
- `reason` in `alert_acknowledgements` stores the name of the action that closed the alert, not free
  text.
- `key_id` in `alert_acknowledgements` stores the key the alert belonged to, or `NULL` for a
  software alert from the settings list.
- Only one row in `keys` per `key_number` is active at a time. The rule is enforced by a **partial
  unique index** on `key_number` where `active = 1`, not by a `UNIQUE` on the table, so retired rows
  can share the multisig slot (§32.8).
- `active` is `1` on the row the app reads as "the key", and `rotated_at` is the timestamp when the
  row was retired by a rotation. Every query that reads "the key" — the setup, the settings, the
  form, the dashboard and the rotation — reads the **active** row, while the history, the CSV and the
  alerts read the snapshot on the check.
- `key_name`, `key_type` and `key_model` in `key_checks` are a **snapshot** of the key as it was when
  the check was stored. Neither a rotation nor a rename can change it, and the migration backfills
  the snapshot from the linked `keys` row (§32.8).
- `key_id` in `ai_security_checks` is the checked key when `provider` is that key's own configured
  name, and `NULL` otherwise. The source of an AI alert is therefore decided by the row itself, and
  it cannot flip when the key is renamed or rotated (§32.8).
- `failed_login_count` and `failed_login_until` in `app_settings` are the login counter and the end
  of the lockout (§32.8). They survive a restart, and `failed_login_until` is a Unix timestamp in
  seconds.
- `tool_checks` does not exist. Neither do `device`, `seed_backup_status`, `address_verified`,
  `derivation_height`, `cloud_health_status` or `cloud_provider_operational`.

---

# 5. Status values

- General checks use `OK` or `PROBLEM`. `NOT_ASSESSED` exists only as the derived value of
  `software_compatibility_status` when the key could not be checked; no other field offers or accepts
  it.
- `seed_backup_verified` and `address_path_verified` use only `OK` or `PROBLEM`.
- AI security status uses exactly `SECURE`, `PATCHED`, `VULNERABLE` and `COMPROMISED`.
- The contact confirmation uses `Confirmed current` or `Needs external update`.
- `Hardware works` (`Yes`/`No`) and `Software compatibility` (`OK`/`PROBLEM`) require an active
  choice for an available key.
- `address_path_verified` is derived by the server and is not a choice in the form.
- The same status logic applies in the database, the validation, the alerts, the CSV export and the
  UI.
- Never confuse "not assessed" with an actual negative result.

---

# 6. The annual health check, step by step

The steps follow the sections of the form.

## Step 1 — Schedule (01 / Schedule)

- The user presses `Start annual health check`, and today's date is suggested automatically.
- The check date may be today or an earlier date, but never a future date: the server refuses a date
  after its own day with `400` and a message that says so, and the form's date field has `max` set to
  today's local date (§32.8). A check that has not happened yet cannot be recorded.
- The next check date is computed on the server as one calendar year after the check date, and cannot
  be edited in the form. The limit does not change that computation.

## Step 2 — Key (02 / Key)

- The user chooses which key the submission covers. One submission covers one key.
- `Availability` is required: Yes or No.
- A key with an open alert cannot be chosen, and the form says which alert stands in the way.
- **Hardware key:** `Hardware works` is required (`Yes`/`No`), the firmware version is recorded, and
  an intact seed backup that matches the hardware gives `seed_backup_verified` (`OK`/`PROBLEM`).
  Comment when needed.
- **Cloud key:** only `Availability` is asked for. Comment when needed.
- **Address path (all keys):** the user records only `Address path`, pre-filled with the key's stored
  path. The server compares the submitted path with `keys.address_path` under the canonical rule in
  §4: equal gives `OK`, different gives `PROBLEM`.
- When the key is not available, the rest is hidden and not required.
- If the path does not match, the browser shows a reminder before submission, and the check is stored
  as a key that could not be checked.

## Step 3 — Compatibility (03 / Compatibility)

- The user chooses one wallet software: a name from the settings, or the name of a configured cloud
  key. A cloud key is locked to its own name.
- `Software version` is recorded for every key, including a cloud key.
- `OK` or `PROBLEM`, with a comment on a problem.
- For a cloud key, `Wallet software` and `Compatibility status` are hidden and derived.
- When the key is not available, the field is hidden and optional.

## Step 4 — External research (04 / External research)

- Providers per submission: the selected key (by name) and the selected software.
- Record the status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) and a short comment.
- Only the selected key and the selected software are recorded. The app never contacts AI itself.
- When the key is not available, no statuses are recorded.

## Step 5 — Contact confirmation (05 / Contact confirmation)

- Confirm that the contact details of the key holder of the selected key are valid:
  `Confirmed current` or `Needs external update`. The confirmation is required, also when the key is
  not available.
- Only the status is stored. Never store names, phone numbers, e-mail addresses or other contact
  content.

## Step 6 — Notes (06 / Notes)

- One overall comment field for observations, and per-key comments where they are needed.

## The review panel, before saving

- Before saving, the app shows every check point, every problem, every missing check, the next check
  date, the actions that should be followed up, and the derived values marked as just that.
- The user has to press `Save health check` to store the check.
- When the address path does not match, the choice to save anyway is clearly marked in the summary.

---

# 7. Alerts and follow-up

Every stored check is read, not only the newest one. Identical alerts (same `code` and `source`) are
merged and only the newest is shown. Critical alerts are listed before informational ones, and the
newest check first within each severity. An acknowledged alert stays hidden until a newer check for
the same `code` and `source` raises it again. An alert that belongs to a key is hidden by its key
instead, so a rename cannot open it again.

**An open alert that belongs to a key blocks that key** until the alert is closed. The server
enforces the rule, so a direct API call cannot bypass it. The block applies only to the key that has
the alert.

| `code` | Severity | Source | Raised by | Closed by |
|---|---|---|---|---|
| `key_unavailable` | critical | key | `available` = No | Rotation |
| `address_path_mismatch` | critical | key | The address path does not match the stored one | Rotation |
| `hardware_failure` | critical | key | `Hardware works` = No | Rotation, or replacing the hardware wallet with the same seed |
| `seed_backup_problem` | critical | key | Seed backup `PROBLEM` | Rotation |
| `software_incompatible` | critical | key | `software_compatibility_status` = `PROBLEM`, and the recorded software is the name of a configured cloud key | Replacing the hardware wallet |
| `software_incompatible` | critical | software | `software_compatibility_status` = `PROBLEM` | Removing the failing software in the settings |
| `security_vulnerable` | critical | key | AI status `VULNERABLE` | Rotation, or closing without action |
| `security_vulnerable` | critical | software | AI status `VULNERABLE` | Removing the software, or closing without action |
| `security_compromised` | critical | key | AI status `COMPROMISED` | Rotation is required |
| `security_compromised` | critical | software | AI status `COMPROMISED` | Removing the software |
| `contact_info_unconfirmed` | info | key | Contact confirmation `Needs external update` | Closing, after the contact details have been updated externally |

**The shape of the messages.** Each row above has a `message` in `alerts.py`, and all eleven were
rewritten into the same shape (§32.3): what is wrong, which key or software it concerns, and what
closes the alert. The messages are English, short and concrete, and they never say that the app did
something itself.

- **The message does not repeat the name in the source.** `source` is either `Key N: <name>` or the
  software name, and it is shown right above the message in the alert list, in brackets on the key
  card, and in front of the message in the block note in the form. The message therefore says "this
  key" and not the key name. The one exception is the key form of `software_incompatible`: there the
  source is the key, while the message names the software, because it appears nowhere else in that
  form.
- **The two forms of an AI code have a message each.** `security_vulnerable` and
  `security_compromised` are closed by different actions depending on whether the source is the key
  or the software, so each form says what closes it.
- **The action is also in the button and in the block note.** That is deliberate: the button and the
  note say what the user can press, while the message has to stand on its own when it is read without
  the buttons.
- **The message does not show the internal code.** `code` is for the API and for
  `alert_acknowledgements`, not for the user.

- Each alert code has a fixed set of actions: `rotate`, `replace_hardware`, `remove_software`,
  `ignore`, `contact_updated`. An action that does not belong to the alert is refused.
- `rotate` is carried out in the settings, because it requires a new address path. The other actions
  are carried out where the alert is shown, each with its own button text and its own confirmation
  step.
- The source of an AI alert is decided by the row in `ai_security_checks`, not by the names that are
  configured now. When the row carries the checked key, the key is the source, it is written as
  `Key N: <name>` like every other key alert, and a rotation closes the alert. Otherwise the provider
  is the software the key runs with, the source is only its name, and the alert is closed by removing
  it from the settings. A rename or a rotation therefore cannot raise a second software alert beside
  the one the rotation already closed (§32.8).
- A software alert from the settings list has no key and blocks no key. A software alert that comes
  from a cloud key name belongs to the checked key and blocks it, because the name can never be
  removed from the settings.
- Closed alerts are shown in the history and in the CSV, both those that belong to a key and those
  that belong to a software entry in the settings list: the closure hangs on the check it closed
  through `check_id`, so a closed software alert appears in the same list as a rotation (§32.8).
- Every action requires a confirmation from the user, and the app never carries out the action
  itself. It also never contacts providers or AI services.
- An alert without an action is a bug in the code, not a state the user can reach.
- An alert about an unavailable key, an address-path error or the seed backup applies only to that
  key, and the rest of the key fields cannot be recorded.

---

# 8. Dashboard

- Show the multisig setup and the status of each key, with the next due date per key.
- The key cards sit directly under the page heading, without a separate `Configured setup` section,
  without a `Your keys` heading and without a key counter (§32.7).
- One summary card, "Attention": how many keys have passed their due date, and which ones. If none
  has passed, the earliest check date is shown there instead, with the key it belongs to
  (`Earliest next check <date>, for Key N: <name>.`). If no key has a date, the fallback is to store
  a health check. Whether a date is overdue is decided in the browser.
- Show every active alert, with the submission each alert comes from and the action that closes it.
  An empty alert list shows no text; the count beside the heading says `No alerts` (§32.7).
- No navigation links inside the dashboard itself: the menu in the top bar is the way to the form,
  the settings and the history, and the export is on the history page (§32.7). The dashboard has no
  note line of its own either; the note that explains the export is in the export section on the
  history page (§32.7).
- Show the setup step instead of the dashboard when the key setup is missing.
- A key card shows the name, the address path, the model or service and the type, and a clear message
  when the key has an open alert, in addition to its dates: how many alerts are open, that the key
  cannot be checked until they are closed, which action closes the first one, and a link to the alert
  list. The card shows the number and the type on the top line, the model under the name and the
  address path under that, and of the dates only `Next check due` (§32.2).

---

# 9. History

- Show every completed health check chronologically, newest first, with the key each submission
  covers.
- Open a health check in a read-only view with the date, the next check, the status per key, the
  software and its version, the AI status and the comments.
- Old health checks are never overwritten.
- Show `Address path verified` as the derived value it is, not as a user choice.
- Show the name, the type and the model the key was recorded with, because the snapshot on the check
  is frozen and neither a rotation nor a rename can change it (§32.8).
- Show which alerts were closed on the check, with the action and the date, and with their source, so
  the key form and the software form of the same `code` can be told apart. Closed software alerts
  appear in the same list as closed key alerts (§32.8 and §32.9).
- The card in the list shows the date, the key number and the name the key was recorded with, and a
  short status: `All OK` when the check raised nothing, `Needs follow-up` while something is open,
  and `Follow-up closed` once everything is closed (§32.2 and §32.9). The status says what holds
  **now**, while `needs_follow_up` on the check is frozen (§11).
- The software and its version share one line, for example `Sparrow Wallet 2.5.1`, and the model and
  the firmware version share one line, for example `Blockstream Jade 1.4.1` (§32.1). If one part is
  missing, the rest stands alone; if both are missing, the line is `—`.
- The closure table on a check shows `Source`, `Alert`, `Action` and `Closed`, so the source of the
  alert has a column of its own (§32.9).
- The page has its own `Export` section after the list and before the detail section, with the title
  `Download the report`, the link `Download CSV` without a `download` attribute — so the filename
  from `Content-Disposition` wins — and the note that explains the export right under the link
  (§32.7). That is the only place the export is downloaded from, and the page never starts a new
  check.
- `View` in the list opens the check at the `#history-detail` anchor, and so does a submission from
  the form, so the user lands on the check and not at the top of the page (§32.7).

---

# 10. Report export

- `GET /api/export` returns plain CSV (UTF-8, comma, CRLF, header). No XLSX, and the app does not
  promise Excel compatibility.
- One row per key check. The `Check id` column ties together rows from the same submission.
- It contains the date, the next check, the key status, the hardware and firmware, the seed result,
  the address path, the software and its compatibility, the AI status, the contact confirmation and
  the comments.
- A result with more than one value per submission sits in one cell as
  `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- Status values are written as they are stored. `0`/`1` are written as `No`/`Yes`.
- A text cell that a spreadsheet would read as a formula — `=`, `+`, `-`, `@` or a control character,
  also after leading spaces — gets a leading apostrophe, so it becomes text. The column names, the
  column order and every ordinary value are unchanged.
- The key name and the key type come from the snapshot on the check, so a rotation or a rename cannot
  rewrite an older row (§32.8).
- The download is named `YYYY-MM-DD-vardkey-export.csv`, with the date the server has when it
  answers.
- The last column, `Follow-up closed`, lists every alert that was closed on the check, as
  `<source> — code: action (YYYY-MM-DD)`, for example
  `Key 2: Blockstream Jade — key_unavailable: rotate (2026-10-05)`, whether it belongs to a key or to
  a software entry in the settings list (§32.8). The source comes first in the same cell, so the key
  form and the software form of the same `code` can be told apart (§32.9). The column name and the
  column order are unchanged.

---

# 11. Backend

- SQLite with initialisation and migration. The schema is version 13.
- Storage of the keys, the health checks, the history and the report export.
- The alert logic (§7).
- A health endpoint, which is the only endpoint outside the login.
- Validate input on the server, and use parameterised SQL queries.

Minimum endpoints: `GET /health`, `GET /api/keys`, `GET /api/health-checks`,
`GET /api/health-checks/:id`, `POST /api/health-checks`, `GET /api/export`.

**Note:** `GET /api/session`, `POST /api/admin`, `POST /api/login`, `POST /api/logout`,
`GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`,
`POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`,
`GET /api/key-status`, `GET /api/previous-values` and `GET /api/alerts` are extra endpoints beyond
the minimum list, because the setup step, the settings, the dashboard, the form and the login need
them. They are not in the specification yet.

- `POST /api/health-checks` requires one configured key, `available`, and valid, relevant results,
  and refuses missing or duplicated records.
- `POST /api/health-checks` does not require software or AI status when the key could not be checked,
  and refuses such results with `400`.
- `POST /api/health-checks` refuses a key that has an open alert with `409`, and the rule is enforced
  before the rest of the validation.
- `POST /api/setup` stores the multisig numbers and the key setup once, with the name, the type, the
  model and the address path, and refuses a second setup with `409`.
- `POST /api/setup`, `POST /api/settings/keys` and `POST /api/keys/<id>/rotate` refuse an address
  path another key already has (`400` in the setup and the rotation, `409` in the settings). The
  comparison is canonical, see §4.
- `GET /api/settings` returns the keys with their address path and model, and the wallet software
  list.
- `POST /api/settings/keys` stores a new name and a model, and an address path as long as the key has
  no stored check. The type is never part of the payload. It writes the active row in place, so it is
  a rename and not a rotation.
- `POST /api/settings/wallet-software` stores the whole list, and closes the alerts of a software
  that is removed.
- `POST /api/keys/<id>/rotate` rotates a key with a new, unique address path, may give the key the
  other type, and acknowledges its alerts. The rotation adds a **new row** in `keys` with the same
  `key_number`, marks the old row inactive and stamps `rotated_at` on it, while the acknowledgements
  are written against the old row, which is the row the alerts belong to (§32.8).
- `POST /api/keys/<id>/rotate` refuses with `409` a type change that would make the key a cloud key
  under a name the wallet software list already holds.
- `POST /api/alerts/acknowledge` acknowledges an alert with `code`, `source` and the action that
  closes it.
- `POST /api/login` limits failed attempts: after five failed attempts in a row, further logins are
  refused for 15 minutes with `429` and a message that says how long is left. A correct password in
  the lockout window is refused too, so the answer does not reveal whether the password was right,
  and a successful login clears the counter. The counter lives in `app_settings`, so it survives a
  restart. `POST /api/admin`, the local bootstrap, is not rate limited (§32.8).
- `GET /api/health-checks/<id>` also returns `closed_alerts`, every closure that belongs to the check
  — both those that belong to a key and those that belong to a software entry in the settings list
  (§32.8) — and each key record carries `model` in addition to the fields it already had, so the
  history can show the model together with the firmware version (§32.1). The fields come in addition,
  and the existing names are unchanged; each closure carries its source (§32.9).
- `GET /api/health-checks` returns each summary with the same fields as before, and in addition
  `key_names` (the name each key was recorded with on the check, read from the snapshot, in the same
  order as `key_numbers`), `needs_follow_up` (whether the check raised anything to follow up,
  computed from the alert rules in §7, and a property of the stored check — it does not change when
  the user closes the alert later) and `follow_up_open` (whether the check has anything open **now**,
  computed from the same alert and acknowledgement rules, so an alert that a newer check re-raises
  belongs to the newer check). The fields come in addition, see §32.2, §32.8 and §32.9.
  `needs_follow_up` stays unchanged.
- Error codes: invalid payload `400`, unknown key or alert `404`, locked or duplicate address path
  `409`, broken database `500`, missing or invalid session `401`, missing or invalid CSRF token
  `403`, and too many failed logins in a row `429` (§32.8). A free-text field that looks like a
  wallet secret is also a `400` (see §15).
- `_send_security_headers()` adds `X-Robots-Tag: noindex, nofollow` to every answer — pages, JSON,
  redirects, the CSV and the static files — so the indexing ban lives in one place (§32.7).

---

# 12. Frontend

- A simple, responsive web UI. Simplicity comes before graphical complexity.
- Clear status fields, and fixed choices where the status has to be a bounded value.
- Show problems clearly, and show what is still missing before a health check can be stored.
- Hide fields that do not apply to the selected key or the selected software, and hide the software
  and the AI status when the key could not be checked. A hidden `required` field blocks submission,
  so the flag always has to be cleared when the field is hidden.
- A separate setup step at first run: the threshold, the number of keys, and the name, type, model
  and address path per key.
- A login step in front of everything else, and a create-admin step when no admin exists yet.
- The top bar has a `Menu` button with a drop-down on all five app pages, in this order:
  `Dashboard` → `/`, `Start health check` → `/health-check`, `Settings` → `/settings`,
  `History` → `/history`, a separator, and `Sign out`, which does what it did before. The panel is
  hidden until it is opened, and it closes on `Escape`, on a click outside it and after a choice. The
  page the user is already on is greyed out, is not a link and cannot be clicked, and carries
  `aria-current="page"`. `session.js` builds the button, the panel and the `.topbar-actions` wrapper,
  so the markup on the pages is unchanged. `/login` has no menu, because `session.js` is not loaded
  there (§32.7).
- The top bar is fixed to the top: `.topbar` is `position: sticky; top: 0` with a `z-index` that
  keeps it above the page content and below the menu panel, so it stays visible when the page
  scrolls. It is a flex child of `body`, which sets no `overflow`, and that is why the sticky
  position works. No inline style, and no `border-radius`, `box-shadow` or gradient (§32.8).
- The form shows which keys are blocked by an open alert, and which action closes it.
- A reminder before submission when the address path does not match.
- The date field for the check date has `max` set to today's local date, so the picker never offers a
  date the server would refuse (§32.8).
- A settings page with `01 / Wallet software` and `02 / Key rotation`, built for more themes later.
  The key name, the model, the address path of a key with no stored check, and the rotation with a
  new type are all changed in the rotation section, and one button stores all of it. There is no
  separate `01 / Keys` section any more.
- The alert buttons carry the text and the confirmation step that belong to their action, and the
  software-incompatibility alert points at the settings.
- The short warning against pasting a secret appears **once**, in the key setup, in addition to the
  page notice, with the `.secret-warning` style (§15). It is not repeated per field (§32.2).
- The app has to be installable as a PWA without offline data.
- Make sure the app works well in a normal StartOS browser.
- No indexing and no bots: all six pages carry `<meta name="robots" content="noindex, nofollow">`,
  `X-Robots-Tag: noindex, nofollow` is on every answer, and `static/robots.txt` answers `Disallow: /`
  (§32.7).

---

# 13. StartOS 0.4.0

The app is one simple StartOS service.

```text
StartOS 0.4.0
└── VardKey
    ├── Web UI
    ├── Backend/API
    ├── SQLite
    └── Persistent data
```

- Create the StartOS package.
- Create the manifest.
- Create the service definition.
- Create the HTTP web interface.
- Create the persistent volume.
- Create the health check.
- Create the backup setup.
- Write the installation and user instructions.
- Build the `.s9pk`.
- Verify that the package can be installed on StartOS 0.4.0.

**Note:** all ten points are met. The package is in the repository, built as
`vardkey_x86_64.s9pk`, sideloaded and run on a StartOS 0.4.0 box. Two actions sit in
`Actions & Config`: `Delete all data` and `Set Admin Password`.

Since §32.8 the package also raises a **task** that asks the user to set the admin password, through
`startos/init/requireAdmin.ts`. On the box it shows as *recommended*, so it does not hold the service
back; what actually refuses everything until an admin exists is the app's own login gate. The task
points at the existing `Set Admin Password` action, which runs `maintenance.py` in a `withTemp`
subcontainer, so the password is still generated **inside the container** and printed once —
nothing travels from the host into the container, as an argument or on stdin. The probe that decides
whether to raise the task reads `app_settings` **readonly**, and **fails open**. `README.md` has the
detail.

Avoid: Postgres, Redis, an external backend, an external cloud service for app data, and an extra
container without a concrete need.

**Note:** this is a standing prohibition, not a work list. It is re-confirmed before release.

---

# 14. Storage and backup

- The SQLite database lives on a persistent volume.
- App data survives a restart.
- StartOS backup of the persistent data is configured.
- Backup and restore are tested.
- Old health checks are present after a restore.

**Note:** all points are run and verified on the box, through the §16 StartOS test and §17.
`startos/backups.ts` uses `sdk.Backups.ofVolumes('main')`, and the database is on the `main` volume
at `/data`. StartOS stops the service while a backup runs, so the database file is not being written
when it is copied — no separate SQLite snapshot hook is needed, and no known limitation remains. The
points have to be run again before the first release.

---

# 15. Security and privacy

- No seed phrase, private keys, wallet passwords or cloud tokens in the database.
- No unnecessary personal data. Contact information is recorded only as a status
  (`Confirmed current` / `Needs external update`).
- Validate input on the server, and use parameterised SQL queries.
- Do not implement your own cryptography. The admin password uses `hashlib.scrypt` from the standard
  library, and the session an HMAC-SHA256 signature.
- Do not send data to external services.
- The address path is a public derivation path and holds no secret.
- Free text is checked locally in `secret_guard.py` before storage, and before the field's length
  limit. A field that looks like a wallet secret is refused with `400`, nothing is stored, and the
  message never repeats the value. The check makes no network call. It is a guard against the most
  common shapes, not a protection: a bare 64-character hex string, a phrase in another language, and
  a secret split across several fields are not caught. In the UI the short warning appears **once**,
  in the key setup, with the `.secret-warning` style; it is not repeated per field (§12 and §32.2).
  The server is unchanged and still refuses a secret in every free-text field.
- Logins are rate limited: five failed attempts in a row lock the login for 15 minutes with `429`.
  The counter lives in `app_settings`, is not tied to an IP, and the app deliberately does not read
  `X-Forwarded-*`, because StartOS proxies everything (§32.8).
- A `python3` probe in the package reads `app_settings` in the app database **readonly** to see
  whether an admin exists (§13). It writes nothing, makes no network call, and passes nothing on.

---

# 16. Testing

## Functional test

- Create the keys, start a health check, complete every check point, store it and show it in the
  history.
- Start a new health check and verify that the old check is still there.

## Problem test

Every rule in §6–§12 has a test. The cross-cutting ones:

- An unavailable key, a hardware failure and a seed-backup problem.
- An address-path error, both the reminder before submission and the alert afterwards.
- Software incompatibility, and that `Hardware works` and the contact confirmation require a choice.
- AI status `VULNERABLE` and `COMPROMISED`, and contact info `Needs external update`.
- Rotating a key, with and without a new name, and that a rotation requires a new address path.
- Acknowledging an alert, and that a newer alert comes back.
- That a key with an open alert cannot get a new check, and that the key is free again once the alert
  is closed.
- That two keys cannot share an address path — in the setup, in the settings or in a rotation, and
  also when the second is written with the `h` marker.
- Every alert action, and that an alert without actions is treated as a bug.
- That a key card shows an alert message when the key has an open alert.
- That removing the failing software closes `software_incompatible`.
- That a closed alert shows in the history and in the CSV, with its action and its date.
- That a contact alert gives `Needs action` and blocks the key, and that the key is free again after
  `contact_updated`.
- That `software_incompatible` with a cloud-key software gives `replace_hardware` on the checked key,
  while the same alert from the settings list keeps `remove_software`.
- That a key can be renamed in the rotation section without rotating it, and that a rotation requires
  the confirmation box.
- That a rotation can give the key the other type, and that a name the wallet software list already
  holds is refused.
- Login and session: first run without an admin, a right and a wrong password, `401` on the API
  without a session, a redirect on the pages, an open `/health`, and a missing CSRF token.
- That a free-text field that looks like a wallet secret is refused, that the message says what it
  looked like, and that nothing is stored or exported.
- That a CSV cell starting with `=`, `+`, `-`, `@` or a control character is exported as text, and
  that ordinary content is unchanged.
- A setup other than 2-of-3, a model or service per key, the dated export name, deleting all data,
  and installing the PWA.
- That `/robots.txt` is answered, that each of the six pages carries the robots meta, and that every
  answer carries `X-Robots-Tag`.
- The menu, that the current page is greyed out and cannot be clicked, that the export has its own
  section on the history page with the note under the link, and that both `View` and a submission
  land on `#history-detail`.
- That a future check date is refused with `400`, and that today and an earlier date go through
  (§32.8).
- That five failed logins lock the login for 15 minutes with `429`, that a correct password in the
  lockout window is refused too, and that a successful login clears the counter (§32.8).
- That a rotation adds a new row in `keys` with the same `key_number`, that the old row becomes
  inactive, and that older checks keep the name and the type they were recorded with (§32.8).
- That a cloud key with `COMPROMISED` gets no new software alert when the key is rotated or renamed,
  and that closed software alerts show in the history and in the CSV (§32.8).
- That a closure in the history and in the CSV carries its source, so the key form and the software
  form of the same `code` can be told apart (§32.9).
- That the history card shows all three states, that a check with everything closed does not say
  `Needs follow-up`, and that `needs_follow_up` is still frozen (§32.9).

**Note:** the manual browser tests are run and verified up to §31. §32 added new manual points: the
icon (§32.1), the UI pass and the retro theme on a narrow phone (§32.2), a look at the alert list,
the key card and the block note in the form after the text changes (§32.3), the footer on a short
page, the favicon in the tab, the brand mark in the top bar, installing the PWA with the two PNG
icons, the history view with the three table and line changes, the top-bar menu and the cleaned-up
dashboard with `Download CSV` and the note in its own `Export` section on the history page, the jump
to `#history-detail` (§32.7), and finally the manual end-to-end walkthrough in §32.8, which the user
ran and confirmed. §32.9 added a look at the closure table in the history and at the card in the
list, with and without an open alert.

## StartOS test

- Install the `.s9pk` on StartOS 0.4.0, start the service and open the web UI.
- Perform a complete test check.
- Restart the service, and verify that the data is still there.
- Take a backup, restore it, and verify the data after the restore.
- Verify that `Set Admin Password` and `Delete all data` are in `Actions & Config` and work.
- Verify that an installable PWA can be added from the browser.

**Note:** all are run and verified on the box. `vardkey_x86_64.s9pk` was sideloaded and installed,
the service shows as `Running`, the health check reports "The web interface is ready", and `Open UI`
opens VardKey in the browser on the StartOS address. Restart and restore kept the data, and the old
health checks were there after the restore. To be run again before the first release.

---

# 17. Release criteria for the first release

Before the first release, all of these have to be met:

- The app runs on StartOS 0.4.0.
- The keys of the multisig setup are represented in the app.
- A complete annual health check can be performed in the browser, and every yearly check point can be
  recorded.
- AI status can be recorded as SECURE, PATCHED, VULNERABLE or COMPROMISED.
- Contact information can be verified without storing the contact information.
- Problems give clear alerts, and an alert can be closed in the way that belongs to it.
- The next check is stored, and the history works.
- The CSV report can be exported.
- The data survives a restart, and backup and restore work.
- No wallet secrets are stored.
- The app is password protected with one admin user.
- All app data can be reset from StartOS, while the admin user remains.

**Note:** all points are run and verified on the box. The criteria are met, and the package version
is raised to `2026.10.28:0` (§32.5).

---

# 18. Work order for the AI programmer

Do the tasks in this order, and do not jump ahead to advanced features:

- 1–8. The basic web app, SQLite and the data model, the keys, the health-check form, storage and
  history, the alert logic, the dashboard and the report export.
- 9. Implement the StartOS package.
- 10. Implement persistent storage and backup.
- 11. Test restart and restore.
- 12. Build the final `.s9pk` and make the first release.

**Note:** steps 1–12 are done. Step 12 belonged to the same round as §32.5.

**Tests:** run `python3 -m unittest discover -s tests`. The suite has to be green on Linux and on the
Windows copy alike.

**Main rule:** build the smallest solution that meets the list above. Do not add new features,
services or architecture unless they are needed for the points in this specification.

---

# Rules that apply to every round

These are binding for every future change, not only for one round.

- **Migrations are additive, or a rebuild following the pattern in §21.** Every migration needs a
  test with a literal older schema (`SCHEMA_VERSION_n` in `tests/test_database.py`), and
  `PRAGMA foreign_key_check` before the commit where a table is rebuilt.
- **The API keeps its names.** New fields come in addition; existing fields do not change name or
  type. A field that disappears is a break.
- **An older database must always be openable** and be migrated forward. The app must still **refuse**
  to open a schema newer than the one it knows, instead of writing to it.
- **The package version does not touch app data.** The app migrates its own schema at startup, so
  `startos/versions/` needs no data migration. A package change that did need one writes `up`/`down`
  there, not in the app.
- **A downgrade to an older package version is not supported** once the schema has moved forward, and
  that is stated in `UPDATING.md`.
- **A backup taken on an older version** must be restorable and be migrated forward.
- **The export is an agreement.** The column names in the CSV are not changed unless it says so here
  or in a later round.
- **No indexing and no bots.** All six pages carry
  `<meta name="robots" content="noindex, nofollow">`, `_send_security_headers()` in `app.py` adds
  `X-Robots-Tag: noindex, nofollow` to every answer, and `static/robots.txt` answers `Disallow: /`.
  The robots file is in `STATIC_FILES`, but is **not** in the `SHELL` list in `static/sw.js`, because
  it is not part of the app shell. A new page carries the meta from the first moment.
- **The navigation lives in the top bar, not on the page.** `static/session.js` builds the menu on
  the five app pages, and the page the user is on is not a link. The dashboard must carry no
  navigation links in its markup, and the export is on the history page.
- **The prohibition lists in §1 and §13 are re-confirmed before release.**

---

# 19–32. History

Every round below is implemented and verified. Its rules live in §1–§18 and in `ai-note.md`; the full
reasoning is in the git history. The details are not repeated here, because none of them is open any
more.

| Round | What it did |
|---|---|
| §19 | Recording per key: one submission covers one selected key, and each key has its own next-check interval. |
| §20 | A field that does not apply to the selected key or software is hidden and derived, and everything derived is listed in the review summary. |
| §21 | English status values (`IKKJE_VURDERT` → `NOT_ASSESSED`) and `GET /api/alerts`, which sums up every stored check and lists critical ones first. Schema 11. |
| §22 | A key that could not be checked records nothing else: `wallet_software` becomes `NULL`, `software_compatibility_status` becomes `NOT_ASSESSED`, and a submitted result is a `400`. |
| §23 | A configurable key setup at first run; `GET`/`POST /api/setup`. |
| §24 | Required choices (`Hardware works`, the contact confirmation) and the six-section form. BIP327/SLIP39 and `tool_checks` removed. |
| §25 | The address path as identity, rotation, alert acknowledgement, and the settings. |
| §26 | Blocking a key with an open alert (`409`), unique address paths, and a closing action per alert code. |
| §27 | The alert actions in the history and the CSV, the contact alert as a key alert, and the two forms of `software_incompatible`. Schema 11. |
| §28 | The key type can only be changed by a rotation, and the name is changed in the rotation section. Since §32.8 a rotation adds a new row in `keys` and retires the old one, instead of writing over it. |
| §29 | The rename to **VardKey**, with the description "Bitcoin Multisig Health Monitor", the database file `data/vardkey.sqlite3` and the export file `vardkey-export.csv`. |
| §30 | The StartOS 0.4.0 package: `id: 'vardkey'`, `volumes: ['main']`, `GPL-3.0-only`, built and verified on the box. The package version starts at `0.1.0:0`. |
| §31 | The seven points before version 1: a flexible threshold (schema 12), a model or service per key, the address path on the key card, the dated CSV name, deleting all data, an admin password with session and CSRF, and an installable PWA without offline data. |
| §32.1 | The icon: the same retro drawing in `icon.svg` at the root and in `static/icon.svg`, the favicon link and `<img class="brand-mark">` on all six pages, and the two rasterised PNG icons (192 and 512) in the manifest (after the SVG), in `STATIC_FILES` and in the shell list. |
| §32.2 | The UI pass: the retro theme in `static/styles.css` (no `border-radius` except `0`, no `box-shadow`, no gradient), the pasting warning once in the key setup, the cleaned-up key card (number and type, name, model, path, `Next check due`), the history card with a short status, and the additive fields `key_names` and `needs_follow_up` in the summary. The follow-up: the footer at the bottom of the page, the favicon, the brand mark, no "Back to dashboard" or "Start annual health check" on the history page, and the history with software/version and model/firmware on one line each and the closure table `Alert`/`Action`/`Closed`. |
| §32.3 | The message texts in the eleven alert rows rewritten into the same shape: what is wrong, which key or software it concerns, and what closes the alert, without repeating the name in the source. |
| §32.4 | The bug report: BR-001 false positive (the source files are in `main` and tracked by Git), BR-002 fixed in `secret_guard.py`, BR-003 became §32.8 point 7, BR-004 fell away (the eight documents it asks for do not exist here and must not be created — the real documentation drift is §32.6), BR-005 verified in the code with no behaviour change, BR-006 fixed in `export.py`, BR-007 fixed in `static/sw.js`, BR-008 fixed in `validation.py`. |
| §32.7 | The top-bar menu (`Dashboard`, `Start health check`, `Settings`, `History`, a separator, `Sign out`) with the current page greyed out and `aria-current="page"`, and the cleanup of the dashboard: `Configured setup`/`Your keys` and the key counter gone, the `Next check` card folded into "Attention", an empty alert list with no placeholder text, the history block gone, `Download CSV` and the note in its own `Export` section on the history page, the `#history-detail` anchor, and the robots ban (`static/robots.txt`, the robots meta on all six pages and `X-Robots-Tag` on every answer). |
| §32.8 | Step A (points 3, 4 and 2), step B (point 1) and step C (points 6 and 5 together, since both needed schema 13): the date limit on `checked_at`, the fixed top bar, the login lockout with `429`, the `Set Admin Password` task that `startos/init/requireAdmin.ts` raises and clears, the AI source that comes from the row in `ai_security_checks`, and the rotation that adds a new key row with a snapshot of the name, the type and the model on every check. Schema **13**. Point 7, the user's manual end-to-end walkthrough, was run on the box and confirmed. |
| §32.9 | The source of a closed alert now appears in `Follow-up closed` in the CSV, as `<source> — code: action (date)`, and in a `Source` column of its own in the closure table in the history. The history card shows the current state in three steps (`All OK`, `Needs follow-up`, `Follow-up closed`) through the additive field `follow_up_open`, while `needs_follow_up` stays frozen. |
| §32.6 | The documentation drift: `README.md`, `docs/application.md`, `instructions.md`, `UPDATING.md` and `AGENTS.md` now describe the app and the package as they actually are — the actions, the task, schema 13, the login gate, the export, the robots ban and the optional numbers — and the short and long description in `startos/manifest/i18n.ts` says "one multisig setup, 2-of-3 by default" in all five languages. In the same round: every `helsesjekk` URL became `https://gitea.sondreolav.com/ai-bot/vardkey`, the limitation about the package id and the repository having different names was deleted, `UPDATING.md` got the date-based version scheme, `donationUrl` went into the manifest, and the two §32.9 fixes — the source in the closure and the third state on the history card — are in the documents. |
| §32.5 | The package version raised to `2026.10.28:0`, tag `v2026.10.28_0`, with release notes in all five languages, and `donationUrl: 'https://sondreolav.com/donations'` in the manifest. No schema change, no new endpoint and no new feature; `startos/versions/` stays empty, because the app migrates its own schema. |
| §33 | The documentation cleanup: this file moved from `TODO.md` at the root to `docs/spec.md` and was written in English, with the section numbers kept stable because the code and the documents cite them. `BUG-RAPPORT-AI-AGENT.md` was deleted — every finding in it is closed, and its content is summarised in §32.4 and in `ai-note.md`. The sub-point citations in the code and the tests were left as they are, and the paragraph above says what they mean. |

---

# 32. What is left

Nothing. Every round in §19–§33 is implemented and verified. New rounds are added to the table above
as one line each, and their rules are written into §1–§18.
