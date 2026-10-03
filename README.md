# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three key profiles, the latest saved check dates, and every active follow-up alert. Each key card shows its own last check date and next due date, and the summary cards above the alerts show the earliest upcoming date and any key that has passed its due date. The annual health-check form records the checklist for **one selected key per submission** and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. `GET /api/export` returns every saved check as a CSV download. The StartOS package is not implemented yet. The application does not claim that any device or backup has been tested.

The key setup is configured once, on a new database, at `/setup`: the user gives each of the three key slots a name and a type (`hardware` or `cloud`). The names must be unique and non-empty, and both the name and the type are locked after the setup is saved. The configured name is the product label of that key everywhere: the check form, the alerts, the history, and the CSV export. An existing database is read from its stored key rows, so an installation that predates this step keeps its keys and all of its history.

Each key has its own next-check date, calculated on the server as one calendar year after the check date (29 February is clamped to 28 February). The date is not editable in the form, and a submission for one key never changes another key's interval.

`Availability` is the first question in the form and is required. When a key is not available, the rest of the check cannot be recorded, so the form hides the software compatibility, the standards, and the security statuses and submits only the availability, the key note, the contact confirmation, and the overall comment. That single submission is a complete result and raises the follow-up alert.

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
| GET | `/api/health-checks` | Returns saved check summaries, newest first, including the checked key numbers. |
| GET | `/api/health-checks/<id>` | Returns one saved check with its related rows. |
| GET | `/api/alerts` | Returns the merged follow-up alerts of every saved check. |
| GET | `/api/export` | Returns every saved key check as a CSV download. |
| POST | `/api/health-checks` | Validates and stores one check for one selected key. |

`POST /api/setup` accepts exactly three keys, one per slot, and writes them once:

```json
{"keys": [
  {"key_number": 1, "name": "ColdCard", "type": "hardware"},
  {"key_number": 2, "name": "Blockstream Jade", "type": "hardware"},
  {"key_number": 3, "name": "Nunchuk", "type": "cloud"}
]}
```

A name that is empty, a name that repeats another name (compared without regard to case), a type other than `hardware` or `cloud`, a missing key number, or a key number outside 1–3 is rejected with `400`. A database that already holds a setup is answered with `409`, because the names and the types are locked. A database that holds only part of a setup is answered with `500` and is never treated as a new installation.

`GET /api/setup` returns `{"configured": false, "keys": []}` on a new database, and `{"configured": true, "keys": [...]}` once the setup is stored.

`GET /api/key-status` returns one entry per key with `key_id`, `key_number`, `name`, `type`, `last_checked_at`, and `next_check_due`. A key that has never been checked has `null` dates. Whether a date is overdue is decided by the client from `next_check_due`, so the endpoint stays independent of the current date.

`POST /api/health-checks` accepts JSON and records exactly one configured key:

- `key_check` is one object with the selected `key_id` and `available`. `available` is required and is `1` (yes) or `0` (no).
- When `available` is `1`, the fields below are recorded as described.
- When `available` is `0`, the key could not be checked, so `wallet_software`, `tool_checks`, and `ai_security_checks` must be absent or empty. Sending them is a `400` rather than something dropped silently. `software_compatibility_status` may be omitted and is then stored as `NOT_ASSESSED`. No standards or security rows are stored, and `wallet_software` stays `NULL`.
- The remaining key fields are not required when the key was not available, and are stored as empty. The key note is kept. For a cloud key the derived cloud results are still stored (see below).
- `wallet_software` is `Sparrow Wallet` or the name of a configured cloud key. A cloud key records its own name, because the provider is the software for that key.
- `tool_checks` must cover the selected key by its configured name plus the selected wallet software, without duplicates: at most two rows, and one row when the key name and the software name are the same. `bip327_status` and `slip39_status` accept `YES`, `NO`, or `NOT_ASSESSED`.
- `ai_security_checks` must cover the same two labels, so a hardware key records its own name and the selected software, and a cloud key records its own name once.
- `seed_backup_verified` (hardware keys only) and `address_path_verified` accept `OK` or `PROBLEM` and are required when the key was available.
- `software_compatibility_status` requires an active choice when the key was available: `OK` or `PROBLEM`. A missing value, or `NOT_ASSESSED`, is a `400`. `NOT_ASSESSED` is only stored for a key that was not available, and a cloud key always derives its compatibility from availability.
- `contact_info_verified` is `Confirmed current` or `Needs external update`, and may be omitted. Only the status is stored, never names, addresses, phone numbers, or credentials. `Needs external update` shows a reminder in the form to update the records externally.
- `address_path` is only recorded when `address_path_verified` is `OK`; the form hides the field and clears it otherwise.
- `next_check_due` is ignored; the server derives it from `checked_at`.

A minimal submission for a key that was not available is therefore just the check date and the key check:

```json
{"checked_at": "2026-10-01", "key_check": {"key_id": 2, "available": 0, "comments": "Key is with the third holder"}}
```

Unknown statuses, unknown key ids, a missing `available`, irrelevant or duplicated products and providers, standards or security results for an unavailable key, invalid dates, and over-long text are rejected with `400`.

## CSV export

`GET /api/export` sends `helsesjekk-export.csv` as a download: UTF-8, comma separated, CRLF line endings, with a header row. It contains every saved key check, oldest first.

One row is one key check. The `Check id` column identifies the submission a row belongs to, so records saved before section 19 (up to three keys in one submission) stay grouped. Results that have more than one value per submission are joined into a single cell as `Label: value; Label: value`:

- `BIP327` and `SLIP39` list the key's configured name and the chosen wallet software.
- `Security status` lists the same two labels.

Stored `0`/`1` values are written as `No`/`Yes`, matching the history view. Status values are written exactly as stored, including the contact confirmation, which is `Confirmed current` or `Needs external update`. Empty values are written as empty cells, so a check that recorded only an unavailable key leaves the software, standards, and security columns empty. Text that contains a comma, a quote, or a semicolon is quoted and escaped by the standard CSV rules, so the file can be opened directly in a spreadsheet.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise the follow-up alerts of **every** saved check:

```json
{"code": "key_unavailable", "severity": "critical", "source": "Key 1: ColdCard", "message": "This key was not available. Replace the key before continuing; the remaining checks for this key cannot be recorded.", "check_id": 12, "checked_at": "2026-10-01"}
```

`check_id` and `checked_at` name the saved check an alert came from, so the dashboard can show where a warning originated. Identical alerts (same `code` and `source`) are merged, and only the newest one is listed, with its own date. Critical alerts come first, then the newest check first inside each severity. An alert from an older check therefore stays visible until a newer check for the same key and source resolves it.

A key alert names the key by its number and its configured name, so renaming a key in the setup is not possible after the fact and an alert always matches the key it came from.

`severity` is `critical` for results that require action (unavailable key, hardware failure, missing or damaged seed backup, a cloud provider that is not operating normally, failed address verification, software that no longer supports the hardware, security status `VULNERABLE` or `COMPROMISED`) and `info` for results that can be considered later (reported BIP327 or SLIP39 support, contact details that need an external update).

A value that has not been assessed (`NOT_ASSESSED` or empty) never raises an alert, so "not assessed" is never confused with a negative result. A reported `NO` for BIP327 or SLIP39 is a negative result as well, and raises no alert. An unavailable key raises one critical alert only, because the remaining checks for the key could not be performed; for a cloud key that single alert also states that the provider is recorded as not operating.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

## Development

The web server, validation, alert rules, export, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.

The application UI, source code, comments, and technical documentation are in English. `TODO.md` is intentionally written in Norwegian. Two names are deliberate exceptions to the English rule: the product name **Helsesjekk** and the database file name **`data/helsesjekk.sqlite3`**.

Stored status values are English. General results are `OK`, `PROBLEM`, or `NOT_ASSESSED`; the two verification results are `OK` or `PROBLEM`; software compatibility is `OK` or `PROBLEM` for a new check; BIP327 and SLIP39 are `YES`, `NO`, or `NOT_ASSESSED`; the security statuses are `SECURE`, `PATCHED`, `VULNERABLE`, and `COMPROMISED`; the contact confirmation is `Confirmed current` or `Needs external update`.

The product, the provider, and the wallet software are the configured key name and the selected software, so those columns hold free text. The database no longer limits them to the products that shipped with the first version.

Databases created by earlier versions are migrated on startup, up to schema version 8:

- The removed columns are dropped, and the old boolean verification flags become `OK`/`PROBLEM`.
- The Norwegian security status values become the English ones.
- `IKKJE_VURDERT` becomes `NOT_ASSESSED`, and the BIP327/SLIP39 results `OK`/`PROBLEM` become `YES`/`NO`.
- The old `0`/`1` contact flag becomes `Confirmed current` (was `1`) or `Needs external update` (was `0`), and an empty value stays empty.
- The fixed `device` column, the fixed product and provider lists, and the fixed wallet-software list are dropped, because the configured key name and the selected software replace them.

Because `health_checks` is a parent table with foreign keys from the three child tables, the migration disables foreign keys for the transaction, checks them with `PRAGMA foreign_key_check` before committing, and rolls back if anything is wrong. Older records keep rendering in the history.

Making the rest of a check optional for an unavailable key needs no migration: `wallet_software` is already nullable, and the standards and security results live in their own tables. A record with no such rows simply renders and exports as empty.
