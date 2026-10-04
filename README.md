# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three key profiles, the latest saved check dates, and every active follow-up alert. Each key card shows its own last check date and next due date, and the summary cards above the alerts show the earliest upcoming date and any key that has passed its due date. The annual health-check form records the checklist for **one selected key per submission** and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. `GET /api/export` returns every saved check as a CSV download. `/settings` holds the key names, the wallet software list, and the key rotation. The StartOS package is not implemented yet. The application does not claim that any device or backup has been tested.

The form is in six sections, in this order: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes.

The key setup is configured once, on a new database, at `/setup`: the user gives each of the three key slots a name, a type (`hardware` or `cloud`), and an **address path**. The name is a label that the settings can change later. The type and the address path are locked once the setup is saved, and together they are the identity of the key.

Each key has its own next-check date, calculated on the server as one calendar year after the check date (29 February is clamped to 28 February). The date is not editable in the form, and a submission for one key never changes another key's interval.

`Availability` is the first question in the form and is required. When a key is not available, the rest of the check cannot be recorded, so the form hides the software compatibility and the security statuses and submits only the availability, the key note, the contact confirmation, and the overall comment. That single submission is a complete result and raises the follow-up alert.

`Hardware works` and the contact confirmation are required choices. Both start on `Select status`, which is not an answer, and a submission that leaves either of them out is rejected with `400`.

Firmware version, address path, and software version are pre-filled with the last saved value for the selected key and the selected wallet software. The value is a real input value, not a placeholder, so a field the user leaves untouched is saved as it stands. A field with no relevant saved value stays empty.

## Run locally

Requires Python 3.9 or later. No third-party packages are needed.

```sh
python3 app.py
```

Open <http://localhost:8080>. Set the `PORT` environment variable to use a different port. Set `DATABASE_PATH` to change the SQLite database file location; it defaults to `data/helsesjekk.sqlite3`.

Run the tests with:

```sh
python3 -m unittest discover -s tests
```

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Returns `{"status":"ok"}` for service health checks. |
| GET | `/api/setup` | Returns whether the key setup is stored, with the stored keys. |
| POST | `/api/setup` | Stores the key setup once, for the three key slots. |
| GET | `/api/keys` | Returns the three configured key profiles, or `[]` on a new database. |
| GET | `/api/key-status` | Returns each key with the dates of its newest saved check. |
| GET | `/api/settings` | Returns the keys with their address paths and the wallet software list. |
| POST | `/api/settings/keys` | Stores the name of one key, and its address path while it is unlocked. |
| POST | `/api/settings/wallet-software` | Stores the whole wallet software list. |
| POST | `/api/keys/<id>/rotate` | Rotates one key and closes the alerts it raised. |
| GET | `/api/health-checks` | Returns saved check summaries, newest first, including the checked key numbers. |
| GET | `/api/health-checks/<id>` | Returns one saved check with its related rows. |
| GET | `/api/alerts` | Returns the merged follow-up alerts of every saved check. |
| POST | `/api/alerts/acknowledge` | Acknowledges one alert, so it stays hidden until a newer check raises it. |
| GET | `/api/export` | Returns every saved key check as a CSV download. |
| POST | `/api/health-checks` | Validates and stores one check for one selected key. |

## Key setup

`POST /api/setup` accepts exactly three keys, one per slot, and writes them once:

```json
{"keys": [
  {"key_number": 1, "name": "ColdCard", "type": "hardware", "address_path": "m/48'/0'/0'/2'"},
  {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": "m/48'/0'/0'/2'"},
  {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": "m/48'/0'/0'/2'"}
]}
```

A name that is empty, a name that repeats another name (compared without regard to case), a type other than `hardware` or `cloud`, an address path that is empty or longer than 200 characters, a missing key number, or a key number outside 1–3 is rejected with `400`. Two keys may share an address path, because the three keys of one multisig setup normally use the same derivation path. A database that already holds a setup is answered with `409`, because the type and the address path are locked. A database that holds only part of a setup is answered with `500` and is never treated as a new installation.

`GET /api/setup` returns `{"configured": false, "keys": []}` on a new database, and `{"configured": true, "keys": [...]}` once the setup is stored.

`GET /api/key-status` returns one entry per key with `key_id`, `key_number`, `name`, `type`, `last_checked_at`, and `next_check_due`. A key that has never been checked has `null` dates. Whether a date is overdue is decided by the client from `next_check_due`, so the endpoint stays independent of the current date.

## Settings

`GET /api/settings` returns the keys with the settings that may change, together with the wallet software list:

```json
{"keys": [
  {"id": 1, "key_number": 1, "name": "ColdCard", "type": "hardware",
   "address_path": "m/48'/0'/0'/2'", "has_checks": false}
], "wallet_software": ["Sparrow Wallet"]}
```

`has_checks` tells the page whether the address path of a key is still editable.

`POST /api/settings/keys` stores one key at a time:

```json
{"key_id": 1, "name": "ColdCard", "address_path": "m/48'/0'/0'/2'"}
```

The name is only a label and may be changed at any time; it must be non-empty, at most 60 characters, and must not repeat another key's name. The type is never part of the payload. The address path is part of the key's identity, so it may only be changed while the key has **no saved check**: sending the stored path again is accepted, while a different path for a key that already has a check is answered with `409`. The answer is the same payload as `GET /api/settings`. An unknown key, an empty name, or a missing address path is a `400`.

`POST /api/settings/wallet-software` stores the whole list, not one entry at a time:

```json
{"wallet_software": ["Sparrow Wallet", "BlueWallet"]}
```

The list must hold at least one name, every name must be non-empty and at most 60 characters, no name may repeat another one (compared without regard to case), and a name that a configured cloud key already provides is refused, because that key offers its own name as a choice. A new database starts with `Sparrow Wallet` as its only entry, so a hardware key has a choice from the first check on. The entry may be replaced once another name has been added, but the list may never be emptied. Removing a name never changes a saved check, because `health_checks` keeps the selected software as free text.

## Key rotation

`POST /api/keys/<id>/rotate` records that a key has been replaced by a new one:

```json
{"replaced": true, "address_path_unchanged": true, "keep_name": true, "name": ""}
```

Both confirmations must be `true`, and `keep_name` must be `true` or `false`. When the name changes, `name` must be non-empty and must not repeat another key's name. The type and the address path are locked and are never part of the payload. The rotation updates the key row and acknowledges the alerts that this key's own checks raised and that a replacement resolves. It changes no earlier check: the history shows the name the key has now, while the recorded results stay as they were.

The answer is the settings payload plus the acknowledged alerts:

```json
{"settings": {"keys": [], "wallet_software": []}, "acknowledged": [{"code": "key_unavailable", "source": "Key 2: Blockstream Jade"}]}
```

A rotation of an unknown key is a `404`, and a payload without the two confirmations is a `400`.

**Rotating a key creates a new wallet.** The funds have to be moved from the old multisig setup to the new one, and the new setup has to be verified, before it is relied on. The old keys and the old seed backups must not be discarded until the funds have been moved and confirmed. The settings page states this before the rotation can be confirmed.

## Health check

`POST /api/health-checks` accepts JSON and records exactly one configured key:

- `key_check` is one object with the selected `key_id` and `available`. `available` is required and is `1` (yes) or `0` (no).
- `address_path` is the path the user read from the key. The server compares it with the path stored for that key, after stripping both, and records the result in `address_path_verified`: equal gives `OK`, different gives `PROBLEM`. The client never sends the verification result, and a submitted one is ignored.
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

A minimal submission for a key that was not available is therefore the check date, the key check, and the contact confirmation:

```json
{"checked_at": "2026-10-01", "contact_info_verified": "Confirmed current", "key_check": {"key_id": 2, "available": 0, "comments": "Key is with the third holder"}}
```

A minimal submission for a key whose address path does not match is the check date, the key check with the recorded path, and the contact confirmation:

```json
{"checked_at": "2026-10-01", "contact_info_verified": "Confirmed current", "key_check": {"key_id": 1, "available": 1, "address_path": "m/48'/9'/0'/2'", "comments": "Path read from the device"}}
```

Unknown statuses, unknown key ids, a missing `available`, a missing `hardware_works`, a missing contact confirmation, irrelevant or duplicated providers, security results for a key that could not be checked, invalid dates, and over-long text are rejected with `400`.

## CSV export

`GET /api/export` sends `helsesjekk-export.csv` as a download: UTF-8, comma separated, CRLF line endings, with a header row. It contains every saved key check, oldest first.

One row is one key check. The `Check id` column identifies the submission a row belongs to, so records saved before section 19 (up to three keys in one submission) stay grouped. The `Security status` column has more than one value per submission, so those values are joined into a single cell as `Label: value; Label: value`.

Stored `0`/`1` values are written as `No`/`Yes`, matching the history view. That covers `Available` and `Hardware works`. Status values are written exactly as stored, including the contact confirmation, which is `Confirmed current` or `Needs external update`. The `Address path verified` column holds the result the server derived from the comparison. The two derived cloud columns are gone, because a cloud key records only its availability. Empty values are written as empty cells, so a check that recorded only an unavailable key leaves the software and security columns empty. Text that contains a comma, a quote, or a semicolon is quoted and escaped by the standard CSV rules, so the file can be opened directly in a spreadsheet.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise the follow-up alerts of **every** saved check:

```json
{"code": "address_path_mismatch", "severity": "critical", "source": "Key 1: ColdCard", "message": "The recorded address path does not match this key. Replace the key before continuing; the remaining checks for this key cannot be recorded.", "actions": ["rotate"], "key_id": 1, "check_id": 12, "checked_at": "2026-10-01"}
```

`check_id` and `checked_at` name the saved check an alert came from, so the dashboard can show where a warning originated. `actions` names the actions that close the alert, and `key_id` names the key when the source is a key. Identical alerts (same `code` and `source`) are merged, and only the newest one is listed, with its own date. Critical alerts come first, then the newest check first inside each severity. An alert from an older check therefore stays visible until a newer check for the same key and source resolves it.

A key alert names the key by its number and its configured name, so an alert always matches the key it came from. The name in the alert is the name the key has now, which the settings may change.

The alerts and the actions that close them:

| `code` | Severity | Raised by | Closed by |
| --- | --- | --- | --- |
| `key_unavailable` | critical | `available` = No | Rotating the key |
| `address_path_mismatch` | critical | `address_path_verified` = `PROBLEM` | Rotating the key |
| `hardware_failure` | critical | `Hardware works` = No | Rotating the key, or closing the alert |
| `seed_backup_problem` | critical | Seed backup `PROBLEM` | Rotating the key |
| `software_incompatible` | critical | `software_compatibility_status` = `PROBLEM` | Closing the alert, after alternative software has been added in the settings |
| `security_vulnerable` | critical | Security status `VULNERABLE` | A key source may be rotated or closed; a software source is closed |
| `security_compromised` | critical | Security status `COMPROMISED` | A key source must be rotated; a software source is closed |
| `contact_info_unconfirmed` | info | Contact confirmation `Needs external update` | Closing the alert, once the records are updated externally |

The source of a security alert is the provider. When that provider is the key's own configured name, the key is the source and a rotation closes the alert; otherwise the provider is the software the key runs with, and a replacement does not resolve it.

A value that has not been assessed (`NOT_ASSESSED` or empty) never raises an alert, so "not assessed" is never confused with a negative result. An unavailable key raises one critical alert only, because the remaining checks for the key could not be performed. The old cloud health rule and the old address verification rule are gone: the two cloud fields they read no longer exist, and the mismatch has its own code.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

### Acknowledging an alert

`POST /api/alerts/acknowledge` closes one alert, identified by its code and its source:

```json
{"code": "address_path_mismatch", "source": "Key 1: ColdCard", "reason": "The key was replaced"}
```

A reason is required. The acknowledgement stores the newest check that raised the alert at that moment, so the alert stays hidden until a **newer check** for the same code and source raises it again; a newer check always has a higher id, so it reappears whatever date it carries. A pair that is not among the current alerts is a `404`, a bad payload is a `400`, and a stored acknowledgement answers `201`. Every action that closes an alert requires a confirmation from the user, and the app never performs the action itself.

## Development

The web server, validation, alert rules, export, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.

The application UI, source code, comments, and technical documentation are in English. `TODO.md` is intentionally written in Norwegian. Two names are deliberate exceptions to the English rule: the product name **Helsesjekk** and the database file name **`data/helsesjekk.sqlite3`**.

Stored status values are English. The seed backup result is `OK` or `PROBLEM`; software compatibility is `OK` or `PROBLEM` for a check that could be performed; the security statuses are `SECURE`, `PATCHED`, `VULNERABLE`, and `COMPROMISED`; the contact confirmation is `Confirmed current` or `Needs external update`. `NOT_ASSESSED` is only ever the derived `software_compatibility_status` of a key that could not be checked, and no other field offers or accepts it.

The provider and the wallet software are the configured key name and the selected software, so those columns hold free text. The database does not limit them to the products that shipped with the first version, and the wallet software choices come from the settings list and the configured cloud keys.

The address path is a public derivation path and holds no secret. It is part of a key's identity, so the setup records it, the check form compares the recorded path with it, and the settings may only change it while the key has no saved check.

The schema is version 10. `keys.address_path`, the `wallet_software` table, and the `alert_acknowledgements` table were added, and the two derived cloud results were dropped from `key_checks`. The application is still under development, so no data migration is written for an older database: delete the `data` folder and configure the setup again. Databases created by earlier versions are still migrated on startup where the older migrations exist:

- The removed columns are dropped, and the old boolean verification flags become `OK`/`PROBLEM`.
- The Norwegian security status values become the English ones.
- `IKKJE_VURDERT` becomes `NOT_ASSESSED`.
- The old `0`/`1` contact flag becomes `Confirmed current` (was `1`) or `Needs external update` (was `0`), and an empty value stays empty.
- The fixed `device` column, the fixed product and provider lists, and the fixed wallet-software list are dropped, because the configured key name and the selected software replace them.
- The `tool_checks` table is dropped, together with the BIP327/SLIP39 results it held. It is a child table, so the drop needs no rebuild of a parent table, and the rest of the history is kept.
- The two derived cloud results are dropped from `key_checks`, and a key that predates the address path starts with an empty one.

Because `health_checks` is a parent table with foreign keys from the child tables, the migration disables foreign keys for the transaction, checks them with `PRAGMA foreign_key_check` before committing, and rolls back if anything is wrong. Older records keep rendering in the history.

Making the rest of a check optional for an unavailable key, and for a key whose address path does not match, needs no migration: `wallet_software` is already nullable, and the security results live in their own table. A record with no such rows simply renders and exports as empty.
