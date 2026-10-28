# VardKey application reference

This is the VardKey application's own documentation: what it does, its HTTP API, and the rules it
enforces. It moved here from `README.md` when that file became the StartOS package README. The
packaging side — container runtime, volumes, interfaces, actions, tasks, backups — is documented in
`README.md`; the user-facing quick start is `instructions.md`.

VardKey is a local web application for recording annual checks of a multisig setup — 2-of-3 by
default — a Bitcoin multisig health monitor. It does not sign transactions, perform wallet
operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English UI sits behind a login gate. On a database with no admin yet the app shows the
create-admin step; afterwards `/login` asks for the stored credentials. Every page and every
`/api/*` endpoint needs a session, and the open routes are only `GET /health`, `GET /api/session`,
`POST /api/admin`, `POST /api/login`, the `/login` page, and the static assets. The navigation lives
in the top bar's `Menu` button, which `session.js` builds on the five application pages.

The dashboard shows the configured key profiles, the latest saved check dates, and every active
follow-up alert. A key that has an open alert shows a clear message that it needs action and how
many alerts are open, in addition to its next due date, which stays visible. The Attention card
reports how many keys have passed their due date, or names the earliest due date when none has. The
annual health-check form records the checklist for **one selected key per submission** and saves it
to a local SQLite database. `/history` lists saved checks with a read-only detail view that also
shows the follow-up that was closed on the check, and it carries the CSV export in an `Export`
section of its own after the list. `GET /api/export` returns every saved check as a CSV download,
with the follow-up that was closed in the last column. `/settings` holds the wallet software list
and the key rotation, where a name can be changed on its own and a key can be rotated into the other
type.

The StartOS package is implemented alongside the application, and it has been built, sideloaded, and
run on a StartOS 0.4.0 box. The application does not claim that any device or backup has been
tested.

The form is in six sections, in this order: 01 Schedule, 02 Key, 03 Compatibility, 04 External
research, 05 Contact confirmation, 06 Notes.

The key setup is configured once, on a new database, at `/setup`: the user chooses the multisig
threshold and the number of key slots, then gives each key a name, a type (`hardware` or `cloud`),
an **address path**, and optionally a model or service. The name and the model are labels that the
settings can change later. The type and the address path are locked once the setup is saved, and
together they are the identity of the key. **No two keys may share an address path.**

Each key has its own next-check date, calculated on the server as one calendar year after the check
date (29 February is clamped to 28 February). The date is not editable in the form, and a submission
for one key never changes another key's interval. **The check date itself may be today or earlier,
but never a date in the future**: the server refuses a later date with `400`, and the form's date
picker has its `max` set to today's local date, so it never offers one.

**A key with an open alert cannot be checked.** The form marks the blocked keys, names the alert
that stands in the way, the action that closes it, and the keys that are still free, and it links to
the dashboard. The server enforces the same rule, so a direct API call cannot bypass it, and the key
becomes available again as soon as its alert is closed. The blocking applies to that key only, and
it also covers the informational contact alert, which belongs to its key like every other key alert.

`Availability` is the first question in the form and is required. When a key is not available, the
rest of the check cannot be recorded, so the form hides the software compatibility and the security
statuses and submits only the availability, the key note, the contact confirmation, and the overall
comment. That single submission is a complete result and raises the follow-up alert.

`Hardware works` and the contact confirmation are required choices. Both start on `Select status`,
which is not an answer, and a submission that leaves either of them out is rejected with `400`.

Firmware version, address path, and software version are pre-filled with the last saved value for
the selected key and the selected wallet software. The value is a real input value, not a
placeholder, so a field the user leaves untouched is saved as it stands. A field with no relevant
saved value stays empty.

## Run locally

Requires Python 3.9 or later. No third-party packages are needed.

```sh
python3 app.py
```

Open <http://localhost:8080>. Set the `PORT` environment variable to use a different port. Set
`DATABASE_PATH` to change the SQLite database file location; it defaults to `data/vardkey.sqlite3`.
The first visit shows the create-admin step, then the key setup, and only then the dashboard.

Run the tests with:

```sh
python3 -m unittest discover -s tests
```

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Returns `{"status":"ok"}` for service health checks. Open. |
| GET | `/api/session` | Returns whether an admin exists and whether this request is signed in. Open. |
| POST | `/api/admin` | Creates the single admin account, once, on the first run. Open. |
| POST | `/api/login` | Signs in with the stored credential and starts a session. Open. |
| POST | `/api/logout` | Ends the session and clears both cookies. |
| GET | `/api/setup` | Returns whether the key setup is stored, its shape, and the stored keys. |
| POST | `/api/setup` | Stores the key setup once, for the configured key slots. |
| GET | `/api/keys` | Returns the configured key profiles, or `[]` on a new database. |
| GET | `/api/key-status` | Returns each key with its address path, its model, and the dates of its newest saved check. |
| GET | `/api/previous-values` | Returns the most recently saved values, so the form can pre-fill itself. |
| GET | `/api/settings` | Returns the keys with their address paths and the wallet software list. |
| POST | `/api/settings/keys` | Stores the name and the model of one key, and its address path while it is unlocked. |
| POST | `/api/settings/wallet-software` | Stores the whole wallet software list, and closes the alerts of a removed name. |
| POST | `/api/keys/<id>/rotate` | Rotates one key with a new address path and closes the alerts it raised. |
| GET | `/api/health-checks` | Returns saved check summaries, newest first, including the checked keys and the current follow-up state. |
| GET | `/api/health-checks/<id>` | Returns one saved check with its related rows and the closures it has. |
| GET | `/api/alerts` | Returns the merged follow-up alerts of every saved check. |
| POST | `/api/alerts/acknowledge` | Closes one alert with the action that belongs to it. |
| GET | `/api/export` | Returns every saved key check as a dated CSV download. |
| POST | `/api/health-checks` | Validates and stores one check for one selected key. |

## Sessions and authentication

The application has one admin account, stored in `app_settings` as a username and a
`hashlib.scrypt` hash of the password. The first run has no admin, so `/login` shows the
create-admin form rather than the sign-in form, and `GET /api/session` tells the page which of the
two to show:

```json
{"admin_configured": false, "authenticated": false}
```

`POST /api/admin` creates the account once and answers `201` with a session; a second attempt is a
`409`. The username must be non-empty and at most 60 characters, and the password must be 8 to 200
characters. The local bootstrap is deliberately not rate limited, because there is no credential to
guess yet.

`POST /api/login` signs in and answers `200` with a session. **Five failed attempts in a row lock
the login for fifteen minutes**: the fifth failure and every attempt during the window answer `429`
with a message that says how long is left, and a *correct* password in that window is refused the
same way, so the answer never reveals whether the password was right. A successful sign-in clears
the counter. The count and the moment the lock ends live in `app_settings`, so they survive a
restart, and they are keyed on nothing but the app itself: StartOS proxies every request, and the
app deliberately does not read `X-Forwarded-*`. Before an admin exists, `POST /api/login` is a
`409`.

The session is a signed, expiring token in an `HttpOnly`, `SameSite=Strict` cookie
(`vardkey_session`); it is valid for 30 days, and it survives a restart because it is signed with a
secret in `app_settings` rather than stored in a session table. Every page and every `/api/*`
endpoint needs it:

- A page without a session answers `302` to `/login`.
- An API call without a session answers `401`.
- The open routes are `GET /health`, `GET /api/session`, `POST /api/admin`, `POST /api/login`, the
  `/login` page, and the static assets. StartOS polls `/health` and reports the service as unhealthy
  otherwise, and the login page has to be reachable before a session exists.

Every state-changing POST also needs the double-submit CSRF token: the readable `vardkey_csrf`
cookie is copied by `session.js` into the `X-CSRF-Token` header on every `fetch`, and the two are
compared on the server. A request without the header, or with a different token, is a `403`.
`POST /api/logout` clears both cookies.

Error codes across the API: `400` for an invalid payload — including a free-text field that looks
like a wallet secret — `401` for a missing or invalid session, `403` for a missing or invalid CSRF
token, `404` for an unknown key, check, or alert, `409` for an already-stored setup or a locked or
duplicate address path, `429` for a locked login, and `500` for a broken database.

## Pages, navigation, and static assets

Six pages are served from `static/`: `/` (the dashboard), `/setup`, `/health-check`, `/history`,
`/settings`, and `/login`. Five of them load `session.js`, which builds the top bar's `Menu` button
and its panel: `Dashboard` → `/`, `Start health check` → `/health-check`, `Settings` → `/settings`,
`History` → `/history`, a separator, and `Sign out`, which calls `POST /api/logout`. The page the
user is already on is rendered as a `<span>` with `aria-current="page"` rather than a link, so it
cannot be clicked. The panel is hidden until it is opened, and it closes on `Escape`, on a click
outside it, and after a choice. `/login` has no menu, because it does not load `session.js`.

The top bar is sticky (`position: sticky; top: 0`), so it stays in view while a page scrolls. The
dashboard markup itself carries no navigation link: the menu is the only navigation, and the export
link lives on the history page.

The history page carries the CSV export in an `Export` section of its own, after the saved-check
list and before the detail section: an `Export` eyebrow, the heading `Download the report`, the link
`Download CSV` (which has no `download` attribute of its own), and a note under the link that
explains the file. The `View` link in the list, and the redirect after a check is saved, both carry
the anchor `#history-detail`, so the user lands on the check rather than at the top of the page.

Every page carries `<meta name="robots" content="noindex, nofollow">`, and the favicon link
`<link rel="icon" type="image/svg+xml" href="/icon.svg">` sits next to the manifest link. The
served icons are `/icon.svg`, `/icon-192.png`, and `/icon-512.png`; the manifest lists the SVG
first and the two PNGs after it, and the same drawing is the package artwork at the repository root.
`static/robots.txt` answers `Disallow: /`. `_send_security_headers()` in `app.py` adds
`X-Robots-Tag: noindex, nofollow` to every answer — pages, JSON, redirects, the CSV, and the static
files — so the indexing ban lives in one place. `static/robots.txt` is deliberately **not** in the
service worker's shell list.

New static files must be added to `STATIC_FILES` in `app.py`, or they answer `404`.

## Key setup

`POST /api/setup` accepts a `threshold`, a `key_count`, and exactly `key_count` keys, and writes them once:

```json
{"threshold": 2, "key_count": 3, "keys": [
  {"key_number": 1, "name": "ColdCard", "type": "hardware", "address_path": "m/48'/0'/0'/2'", "model": "ColdCard Q"},
  {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": "m/48'/1'/0'/2'"},
  {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": "m/48'/2'/0'/2'", "model": "Casa"}
]}
```

`threshold` and `key_count` are optional: a payload without them keeps the 2-of-3 default. The bounds are `2 ≤ key_count ≤ 15` and `1 ≤ threshold ≤ key_count`, and the number of keys has to match `key_count`. `model` is optional documentation — the hardware model or the service a cloud key comes from — trimmed, at most 60 characters, and an empty value means "not recorded".

A name that is empty, a name that repeats another name (compared without regard to case), a type other than `hardware` or `cloud`, an address path that is empty or longer than 200 characters, a missing key number, or a key number outside 1–`key_count` is rejected with `400`.

**Every key needs its own address path.** A path that another key already has is rejected with `400`, and the message names the key that has it. The comparison is **canonical**: `h`, `H`, and `'` are the same hardened marker, and surrounding whitespace and letter case are ignored, so `m/48h/0h/0h/2h` and `m/48'/0'/0'/2'` are the same path. The stored spelling is never rewritten. A database that already holds a setup is answered with `409`, because the type and the address path are locked. A database that holds only part of a setup is answered with `500` and is never treated as a new installation.

`GET /api/setup` returns `{"configured": false, "threshold": 2, "key_count": 3, "keys": []}` on a new database, and the stored shape and keys once the setup is stored.

`GET /api/key-status` returns one entry per key with `key_id`, `key_number`, `name`, `type`, `address_path`, `model`, `last_checked_at`, and `next_check_due`. A key that has never been checked has `null` dates, and a key the migration left without an address path answers with an empty one, which the card leaves out. Whether a date is overdue is decided by the client from `next_check_due`, so the endpoint stays independent of the current date.

`GET /api/previous-values` returns `{"keys": [...], "security": {...}}`: the last recorded firmware version, address path, wallet software, and software version per key, and the last recorded security status per provider. The `security` map is no longer consumed by the form, and the address path the form pre-fills comes from `keys.address_path`; both are kept as they are.

## Settings

`GET /api/settings` returns the keys with the settings that may change, together with the wallet software list:

```json
{"keys": [
  {"id": 1, "key_number": 1, "name": "ColdCard", "type": "hardware",
   "address_path": "m/48'/0'/0'/2'", "model": "ColdCard Q", "has_checks": false}
], "wallet_software": ["Sparrow Wallet"]}
```

`has_checks` tells the page whether the address path of a key is still editable.

The settings page has two sections, `01 / Wallet software` and `02 / Key rotation`, and each saves on its own. The keys themselves are changed in the rotation section: the name and the model of a key can be changed there on their own, the address path of a key that has no saved check can be changed with them, and the type and a new path are recorded together with a rotation.

`POST /api/settings/keys` stores one key at a time:

```json
{"key_id": 1, "name": "ColdCard", "address_path": "m/48'/0'/0'/2'", "model": "ColdCard Q"}
```

The name is only a label and may be changed at any time; it must be non-empty, at most 60 characters, and must not repeat another key's name. The model is a label too, so it is written as given, including an empty value that clears it. The type is never part of the payload: it is part of the identity of the key, and only a rotation changes it. The address path is part of the identity too, so it may only be changed while the key has **no saved check**: sending the stored path again is accepted, while a different path for a key that already has a check is answered with `409`. A path that another key already has is also answered with `409`, and the message names the key that has it. **This writes the active key row in place, so it is a rename, not a rotation.** The answer is the same payload as `GET /api/settings`. An unknown key, an empty name, or a missing address path is a `400`.

`POST /api/settings/wallet-software` stores the whole list, not one entry at a time:

```json
{"wallet_software": ["Sparrow Wallet", "BlueWallet"]}
```

The list must hold at least one name, every name must be non-empty and at most 60 characters, no name may repeat another one (compared without regard to case), and a name that a configured cloud key already provides is refused, because that key offers its own name as a choice. A new database starts with `Sparrow Wallet` as its only entry, so a hardware key has a choice from the first check on. The entry may be replaced once another name has been added, but the list may never be emptied.

Removing a name never changes a saved check, because `health_checks` keeps the selected software as free text. **Removing a name does close the alerts that software raised**, which is how a software-sourced `software_incompatible` or `security_vulnerable` alert is closed. The answer therefore names the alerts that were closed:

```json
{"wallet_software": ["Sparrow Wallet"], "acknowledged": [{"code": "software_incompatible", "source": "BlueWallet"}]}
```

A cloud key name can never be removed this way, because the validation refuses it. When the recorded software of a check is a cloud key name, the alert belongs to the checked key instead and is closed by replacing the hardware, so the removal is not offered for it.

## Key rotation

`POST /api/keys/<id>/rotate` records that a key has been replaced by a new one:

```json
{"replaced": true, "keep_name": true, "name": "", "type": "cloud", "address_path": "m/48'/7'/0'/2'", "model": "Casa"}
```

`replaced` must be `true`, and `keep_name` must be `true` or `false`. When the name changes, `name` must be non-empty and must not repeat another key's name. `model` is optional; when it is left out, the stored model is kept, because it is only a label.

**The address path must change.** The rotation replaces the key, so the key is a new one and the path is part of its identity: the new path is required, the stored path is refused, and a path that another key already has is refused, all with `400`. An empty value is a `400` as well. The comparison is canonical, as in the setup.

**The type may change here, and nowhere else.** The type is part of the identity of the key, so the setup locks it, and a rotation is what replaces the key with a new one. `type` is `hardware` or `cloud`, and leaving it out keeps the type the key has now. A key that ends up as a cloud key offers its own name as a wallet software choice, so a name the wallet software list already holds is refused with `409`, and the message names the entry that has to be removed first.

**The rotation inserts a new key row and retires the old one.** The multisig slot stays, so the new row carries the same `key_number`; the old row is marked inactive and stamped with `rotated_at`, and the replacement becomes the row the app reads. The older checks keep pointing at the old row, and each of them carries its own snapshot of the name, the type, and the model it was recorded with, so **no earlier check is changed**: the history shows the name and the type the key was recorded with, and the replacement starts with an empty history.

The rotation acknowledges the alerts that the key's own checks raised and that a replacement resolves. The acknowledgement is written against the **old** key id, the row the alerts and their checks belong to, so a rotation that changes the name still keeps the closed alerts closed.

The answer is the settings payload plus the acknowledged alerts:

```json
{"settings": {"keys": [], "wallet_software": []}, "acknowledged": [{"code": "key_unavailable", "source": "Key 2: Blockstream Jade"}]}
```

A rotation of an unknown key is a `404`, and a payload without the confirmation or without a new path is a `400`.

**Rotating a key creates a new wallet.** The funds have to be moved from the old multisig setup to the new one, and the new setup has to be verified, before it is relied on. The old keys and the old seed backups must not be discarded until the funds have been moved and confirmed. The settings page states this before the rotation can be confirmed, and it states why the path has to change.

## Health check

`POST /api/health-checks` accepts JSON and records exactly one configured key:

- **A key with an open alert is refused with `409`.** The key cannot get a new check until the alert is closed, and the rule is enforced on the server, so a direct API call cannot bypass it. The blocking applies to that key only, it covers the informational contact alert as well, and the answer names the alert that stands in the way. The check runs before the rest of the validation, so a blocked key always answers `409`.
- **A check date after the server's own day is refused with `400`.** A check that has not happened yet cannot be recorded; today and any earlier date are accepted, and `next_check_due` stays one calendar year after the recorded date.
- `key_check` is one object with the selected `key_id` and `available`. `available` is required and is `1` (yes) or `0` (no).
- `address_path` is the path the user read from the key. The server compares it with the path stored for that key, after canonicalising both, and records the result in `address_path_verified`: equal gives `OK`, different gives `PROBLEM`. The client never sends the verification result, and a submitted one is ignored.
- A recorded path that does not match makes the key **uncheckable**, which is treated exactly like a key that was not available: `address_path`, the key note, the contact confirmation, and the overall comment are stored, while the hardware, the software, and the security results stay empty, `wallet_software` becomes `NULL`, and `software_compatibility_status` becomes `NOT_ASSESSED`. Sending software or security results with a mismatched path is a `400`, not something dropped silently. The check raises the critical `address_path_mismatch` alert. A key that was not available records no path at all, so no mismatch is reported for it.
- When `available` is `1` and the path matches, the fields below are recorded as described.
- When `available` is `0`, the key could not be checked, so `wallet_software` and `ai_security_checks` must be absent or empty. Sending them is a `400` rather than something dropped silently. `software_compatibility_status` may be omitted and is then stored as `NOT_ASSESSED`. No security rows are stored, and `wallet_software` stays `NULL`.
- The remaining key fields are not required when the key was not available, and are stored as empty. The key note is kept.
- `hardware_works` (hardware keys only) requires an active `1` (yes) or `0` (no) when the key was available. A missing value is a `400`.
- `wallet_software` is one of the configured wallet software names: the settings list plus the name of every configured cloud key. A cloud key records its own name, because the provider is the software for that key. A hardware key name is never a software choice.
- `ai_security_checks` must cover the selected key by its configured name plus the selected wallet software, without duplicates: at most two rows, and one row when the key name and the software name are the same. `status` accepts `SECURE`, `PATCHED`, `VULNERABLE`, or `COMPROMISED`.
- `seed_backup_verified` (hardware keys only) accepts `OK` or `PROBLEM` and is required when the key was available and could be checked.
- `software_version` is recorded for every key, including a cloud key.
- `software_compatibility_status` requires an active choice when the key was available: `OK` or `PROBLEM`. A missing value, or `NOT_ASSESSED`, is a `400`. `NOT_ASSESSED` is only ever the derived `software_compatibility_status` of a key that could not be checked; no other field offers or accepts it. A cloud key always derives its compatibility from availability.
- `contact_info_verified` is required and is `Confirmed current` or `Needs external update`, also for a key that was not available. Only the status is stored, never names, addresses, phone numbers, or credentials. `Needs external update` shows a reminder in the form to update the records externally.
- `next_check_due` is ignored; the server derives it from `checked_at`.

The name, the type, and the model of the checked key are copied onto the check as a **snapshot**, so a later rotation or rename cannot change what an older record says. A security row carries the checked key when its provider is that key's own configured name, and `NULL` otherwise, so the source of a security alert is decided by the row itself.

A minimal submission for a key that was not available is therefore the check date, the key check, and the contact confirmation:

```json
{"checked_at": "2026-10-01", "contact_info_verified": "Confirmed current", "key_check": {"key_id": 2, "available": 0, "comments": "Key is with the third holder"}}
```

A minimal submission for a key whose address path does not match is the check date, the key check with the recorded path, and the contact confirmation:

```json
{"checked_at": "2026-10-01", "contact_info_verified": "Confirmed current", "key_check": {"key_id": 1, "available": 1, "address_path": "m/48'/9'/0'/2'", "comments": "Path read from the device"}}
```

Unknown statuses, unknown key ids, a missing `available`, a missing `hardware_works`, a missing contact confirmation, irrelevant or duplicated providers, security results for a key that could not be checked, invalid dates, a future date, and over-long text are rejected with `400`.

### The saved-check list

`GET /api/health-checks` returns one summary per saved check, newest first. Each summary carries
`id`, `checked_at`, `next_check_due`, `software_compatibility_status`, `wallet_software`,
`contact_info_verified`, `comments`, and `key_numbers`, and adds three fields of its own:

- `key_names` — the name each key was recorded with on that check, in the same order as
  `key_numbers`, read from the snapshot on the check.
- `needs_follow_up` — whether the check raised anything to follow up, computed from the alert rules.
  It is a property of the **saved** check, so it does not change when the user closes an alert later,
  and it is never rewritten.
- `follow_up_open` — whether the check still has anything open **now**, computed from the merged,
  unacknowledged alerts the dashboard shows. An alert that a newer check re-raises belongs to the
  newer check, so it is the newer summary that stays open. The history card reads the three states
  from these two fields: `All OK` when the check raised nothing, `Needs follow-up` while something
  is open, and `Follow-up closed` once everything is closed.

### One saved check

`GET /api/health-checks/<id>` returns the stored check with its related rows:

- the check's own columns, including `sparrow_version` and `nunchuk_version` for older records;
- `key_checks`, one row per recorded key, with `key_number`, `name`, `type`, and `model` read from
  the snapshot on the row, so a rotation or a rename cannot change them, and with
  `address_path_verified` as the derived result;
- `ai_security_checks`, one row per provider, with the `key_id` the row carries, which is what
  decides whether the provider is the key or the software;
- `closed_alerts`, every closure of the check, in the order it was written, as
  `{"code": ..., "source": ..., "action": ..., "acknowledged_at": ...}`. Each closure carries the
  source of the alert it closed, so the key form and the software form of the same `code` can be
  told apart.

## CSV export

`GET /api/export` sends a dated file as a download: `YYYY-MM-DD-vardkey-export.csv`, where the date is the server's own date when it answers the download. The file is UTF-8, comma separated, CRLF line endings, with a header row. It contains every saved key check, oldest first.

The `Download CSV` link on the history page carries no `download` attribute of its own, so the browser uses the filename from the server's `Content-Disposition` header; a `download` attribute with a value would override it.

One row is one key check. The `Check id` column identifies the submission a row belongs to, so records saved before section 19 (up to three keys in one submission) stay grouped. The key name and the key type come from the snapshot on the check, so a rotation or a rename cannot rewrite an older row. The `Security status` column has more than one value per submission, so those values are joined into a single cell as `Label: value; Label: value`.

The last column, `Follow-up closed`, lists every closure of the check, whether it belongs to a key or to a software entry in the settings list, joined the same way. Each closure is written as **`<source> — <code>: <action> (YYYY-MM-DD)`**, for example `Key 2: Blockstream Jade — key_unavailable: rotate (2026-10-05)` or `Sparrow Wallet — security_vulnerable: remove_software (2026-10-05)`. The source is part of the cell because `security_vulnerable` and `security_compromised` each have a key form and a software form, and without it the two are indistinguishable. The column name and the column order are unchanged; only the value grows.

Stored `0`/`1` values are written as `No`/`Yes`, matching the history view. That covers `Available` and `Hardware works`. Status values are written exactly as stored, including the contact confirmation, which is `Confirmed current` or `Needs external update`. The `Address path verified` column holds the result the server derived from the comparison. The two derived cloud columns are gone, because a cloud key records only its availability. Empty values are written as empty cells, so a check that recorded only an unavailable key leaves the software and security columns empty. Text that contains a comma, a quote, or a semicolon is quoted and escaped by the standard CSV rules, so the file can be opened directly in a spreadsheet.

A text cell that a spreadsheet would read as a formula — one that starts with `=`, `+`, `-`, `@`, or a control character, also after leading spaces — is **neutralized with a leading apostrophe**, so it is read as text instead of being evaluated. The guard is added only where it is needed, so the header row, the column names, the column order, and every ordinary value are unchanged.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise the follow-up alerts of **every** saved check:

```json
{"code": "software_incompatible", "severity": "critical", "source": "Sparrow Wallet", "message": "This wallet software no longer supports the hardware. Add another wallet software in the settings, then remove this one to close the alert.", "actions": ["remove_software"], "software": "Sparrow Wallet", "key_id": null, "check_id": 12, "checked_at": "2026-10-01"}
```

`check_id` and `checked_at` name the saved check an alert came from, so the dashboard can show where a warning originated. `actions` names the actions that close the alert, `key_id` names the key when the alert belongs to a key, and `software` names the wallet software the alert is about, so the settings link and the removal point at the right entry. Identical alerts (same `code` and `source`) are merged, and only the newest one is listed, with its own date. Critical alerts come first, then the newest check first inside each severity.

An alert is therefore not cleared by a newer check that raises nothing: it stays visible until the user closes it with the action that belongs to it, and a closed alert comes back when a newer check raises the same code and source again. An alert that belongs to a key is identified by its key instead, so renaming a key does not reopen a closed alert. **A key with an open alert cannot get a new check at all** until the alert is closed.

A key alert names the key by its number and the name it was **recorded with on the check that raised it**, read from the snapshot on that check, so a rotation or a rename cannot change the source of an older alert.

The alerts and the actions that close them:

| `code` | Severity | Source | Raised by | Actions |
| --- | --- | --- | --- | --- |
| `key_unavailable` | critical | key | `available` = No | `rotate` |
| `address_path_mismatch` | critical | key | `address_path_verified` = `PROBLEM` | `rotate` |
| `hardware_failure` | critical | key | `Hardware works` = No | `rotate`, `replace_hardware` |
| `seed_backup_problem` | critical | key | Seed backup `PROBLEM` | `rotate` |
| `software_incompatible` | critical | key | `software_compatibility_status` = `PROBLEM`, and the recorded software is a configured cloud key name | `replace_hardware` |
| `software_incompatible` | critical | software | `software_compatibility_status` = `PROBLEM` | `remove_software` |
| `security_vulnerable` | critical | key | Security status `VULNERABLE` | `rotate`, `ignore` |
| `security_vulnerable` | critical | software | Security status `VULNERABLE` | `remove_software`, `ignore` |
| `security_compromised` | critical | key | Security status `COMPROMISED` | `rotate` |
| `security_compromised` | critical | software | Security status `COMPROMISED` | `remove_software` |
| `contact_info_unconfirmed` | info | key | Contact confirmation `Needs external update` | `contact_updated` |

The source of a security alert is decided by the **row** in `ai_security_checks`, not by the names that are configured now. When the row carries the checked key — which it does when its provider is that key's own configured name — the key is the source, written as `Key N: <name>` like every other key alert, and a rotation closes it. Otherwise the provider is the software the key runs with, the source is the plain software name, and the alert is closed by removing that name from the settings. A rename or a rotation therefore cannot turn a key alert into a software one, or raise a second alert beside the one the rotation already closed.

`software_incompatible` has two forms. When the recorded software is a name from the settings list, the software is the source, the alert names it, and it is closed by removing that entry. When the recorded software is the name of a configured cloud key, that name can never be removed from the settings, so the alert belongs to the checked key, names it, and is closed by replacing the hardware instead.

The contact alert belongs to the checked key and names it, so it blocks that key until the user has closed it, even though its severity is `info`.

`rotate` is performed in the settings, because a rotation requires a new address path, and the alert links there. The other actions are carried out where the alert is shown, and each of them has its own button text and its own confirmation step:

- `replace_hardware` records that a new hardware wallet has been set up with the same seed, so the key and the address path stay the same. The confirmation reads: *I have replaced the hardware wallet and restored the same seed on the new device.*
- `remove_software` removes the failing wallet software from the settings list, which is what closes the alert. When the failing name is the only entry, the user has to add a replacement first, because the list may never be empty, and the alert offers a link to the settings instead.
- `ignore` closes an alert without a replacement. It is never offered for `security_compromised`.
- `contact_updated` closes the contact alert, after the details have been updated externally. The confirmation reads: *I have updated the contact details in my external documentation.*

Every alert carries at least one action, so a key is never locked without a way out. An alert without an action is a bug in the code, not a state the user can reach.

A value that has not been assessed (`NOT_ASSESSED` or empty) never raises an alert, so "not assessed" is never confused with a negative result. An unavailable key raises one critical alert only, because the remaining checks for the key could not be performed. The old cloud health rule and the old address verification rule are gone: the two cloud fields they read no longer exist, and the mismatch has its own code.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

### Closing an alert

`POST /api/alerts/acknowledge` closes one alert, identified by its code and its source, with the action that belongs to it:

```json
{"code": "hardware_failure", "source": "Key 1: ColdCard", "action": "replace_hardware"}
```

The action is stored as the reason, so the saved record says which action closed the alert. Only the actions the endpoint itself performs are accepted: `replace_hardware`, `remove_software`, `ignore`, and `contact_updated`. `rotate` is not one of them, because a rotation goes through `POST /api/keys/<id>/rotate` and requires a new address path; the removed generic acknowledgement is gone as well. An action that the alert does not offer is a `400`, an unknown code or action is a `400`, and a pair that is not among the current alerts is a `404`. A stored acknowledgement answers `201` and names the action:

```json
{"acknowledged": true, "code": "hardware_failure", "source": "Key 1: ColdCard", "action": "replace_hardware"}
```

The acknowledgement stores the newest check that raised the alert at that moment, so the alert stays hidden until a **newer check** for the same code and source raises it again; a newer check always has a higher id, so it reappears whatever date it carries. It also stores the key the alert belonged to, and an alert that belongs to a key is hidden by its key, so a rename does not open a closed alert again. Every action that closes an alert requires a confirmation from the user, and the app never performs the action itself.

The history detail view and the CSV export list **every** closure of a check, whether it belongs to a key or to a software entry in the settings list, each with its source, the action, and the date. A software alert that was closed by removing its name hangs on the same check through its `check_id`, so it is listed in the same place as a rotation.

## Development

The web server, validation, alert rules, export, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.

The application UI, source code, comments, and technical documentation are in English, and so is every document in the repository, including the specification in `docs/spec.md`. The earlier Norwegian revision of that specification is in the git history. The product name **VardKey** and the database file name **`data/vardkey.sqlite3`** are English, like the rest of the repository.

Stored status values are English. The seed backup result is `OK` or `PROBLEM`; software compatibility is `OK` or `PROBLEM` for a check that could be performed; the security statuses are `SECURE`, `PATCHED`, `VULNERABLE`, and `COMPROMISED`; the contact confirmation is `Confirmed current` or `Needs external update`. `NOT_ASSESSED` is only ever the derived `software_compatibility_status` of a key that could not be checked, and no other field offers or accepts it.

The provider and the wallet software are the configured key name and the selected software, so those columns hold free text. The database does not limit them to the products that shipped with the first version, and the wallet software choices come from the settings list and the configured cloud keys.

The address path is a public derivation path and holds no secret. It is part of a key's identity, so the setup records it, the check form compares the recorded path with it, the settings may only change it while the key has no saved check, and no two keys may share one. The comparison is canonical — `h`, `H`, and `'` are the same marker, and whitespace and letter case are ignored — and the rule lives in the validation layer, which is what the `400` and `409` answers are built on.

The type is part of the identity of a key too, so the setup locks it and the settings never change it. Only a rotation, which replaces the key with a new one, may pick the other type. A key that becomes a cloud key offers its own name as a wallet software choice, so a name the settings list already holds is refused with `409`: the same name cannot be both a cloud key and a settings entry, and the user has to remove that entry first. The rule lives in the validation layer as well.

The name and the model are labels, so neither is locked: the settings may change both at any time, and a rotation may carry a model as well. The model is documentation only — a hardware model or a cloud service — so it never opens or closes an alert and is never part of the alert source.

An alert names the actions that close it, and the acknowledgement stores the action name in `reason`. The actions are fixed per alert code and source, so no alert can be closed by an action it does not offer, and no alert can be left without one. An acknowledgement also stores the key the alert belonged to, so an alert that belongs to a key stays closed across a rename, and every closure can be listed in the history and the export.

**Every free-text field is screened locally.** `secret_guard.py` is the one place that decides whether a piece of text looks like a wallet secret. It is local — it makes no network call — silent — the text never reaches a log, a message, or an exception — and narrow — it matches only unmistakable shapes, so an ordinary note is not refused. It recognises a PEM private-key block, an extended private key with any SLIP-132 prefix (`xprv`, `yprv`, `zprv`, `tprv`, `uprv`, `vprv`) of 100 base58 characters or more, a WIF key, a BIP38 key, and a run of twelve or more consecutive BIP39 words, also in the middle of a sentence. A refused field is a `400` that says what the text looked like and never repeats the value. The guard runs **before** the field's length limit, so a seed phrase pasted into a short label is answered with what it looks like rather than with "too long". The admin username is checked the same way; the admin password is deliberately not, because a long passphrase is a legitimate password. The limitations are documented in the module and are not played down: a bare 64-character hex string is not refused, only the English BIP39 wordlist is used, and a secret split across several fields is not caught.

The number of key slots and the multisig threshold are configurable, so they are stored in the `app_settings` table rather than being fixed in the code. **`keys.key_number` is not `UNIQUE` on the table.** A rotation inserts a new row for the same slot and retires the old one, so the one-active-row-per-slot rule is a **partial unique index** over the active row (`idx_keys_active_key_number … WHERE active = 1`), and any number of retired rows may share a slot. The bounds on the key number live in the validation layer, which is what the `400` answers are built on. The setup is still exactly one setup.

The schema is **version 13**. `keys.address_path`, `keys.model`, the `wallet_software` table, the `app_settings` table, and the `alert_acknowledgements` table were added; the two derived cloud results were dropped from `key_checks`; `alert_acknowledgements.key_id` was added; the `key_number` `CHECK` was loosened; and `keys` gained the `active` flag and `rotated_at` while `key_checks` gained the `key_name`, `key_type`, and `key_model` snapshot columns and `ai_security_checks` gained `key_id`. The application is still under development, so no data migration is written for an older database: delete the `data` folder and configure the setup again. Databases created by earlier versions are still migrated on startup where the older migrations exist:

- The removed columns are dropped, and the old boolean verification flags become `OK`/`PROBLEM`.
- The Norwegian security status values become the English ones.
- `IKKJE_VURDERT` becomes `NOT_ASSESSED`.
- The old `0`/`1` contact flag becomes `Confirmed current` (was `1`) or `Needs external update` (was `0`), and an empty value stays empty.
- The fixed `device` column, the fixed product and provider lists, and the fixed wallet-software list are dropped, because the configured key name and the selected software replace them.
- The `tool_checks` table is dropped, together with the BIP327/SLIP39 results it held. It is a child table, so the drop needs no rebuild of a parent table, and the rest of the history is kept.
- The two derived cloud results are dropped from `key_checks`, and a key that predates the address path starts with an empty one.
- `alert_acknowledgements.key_id` is added to a database that predates version 11. An acknowledgement written before the change has no key, and the older contact alert used the source `Contact information`, which no longer matches; an acknowledgement from before the change is therefore not carried over, and the alert it closed is raised again. No data migration is written for it, because the database is a test database.
- `keys` is rebuilt once for a database that predates version 12, to loosen the `key_number` `CHECK` and to add the `model` column, and the `app_settings` table is created empty, so a database without the stored shape keeps the 2-of-3 default.
- `keys` is rebuilt again for a database that predates version 13, to drop the `UNIQUE` on `key_number` and add `active` and `rotated_at`; every row of such a database is active. The snapshot columns and `ai_security_checks.key_id` are added, and the snapshot is backfilled from the key each check belongs to, so an older check keeps the name, the type, and the model the key had at the migration.

Because `health_checks` is a parent table with foreign keys from the child tables, the migration disables foreign keys for the transaction, checks them with `PRAGMA foreign_key_check` before committing, and rolls back if anything is wrong. Older records keep rendering in the history.

Making the rest of a check optional for an unavailable key, and for a key whose address path does not match, needs no migration: `wallet_software` is already nullable, and the security results live in their own table. A record with no such rows simply renders and exports as empty.

The address path uniqueness, the type change on a rotation, and the alert actions need no migration either: all are enforced where they are used, and a database with a duplicate path is refused by the API rather than by a constraint, so an old database can still be opened.
