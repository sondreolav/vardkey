# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three fixed key profiles, the latest saved check dates, and every active follow-up alert. Each key card shows its own last check date and next due date, and the summary cards above the alerts show the earliest upcoming date and any key that has passed its due date. The annual health-check form records the checklist for **one selected key per submission** and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. `GET /api/export` returns every saved check as a CSV download. The StartOS package is not implemented yet. The application does not claim that any device or backup has been tested.

Each key has its own next-check date, calculated on the server as one calendar year after the check date (29 February is clamped to 28 February). The date is not editable in the form, and a submission for one key never changes another key's interval.

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
| GET | `/api/keys` | Returns the three fixed key profiles. |
| GET | `/api/key-status` | Returns each key with the dates of its newest saved check. |
| GET | `/api/health-checks` | Returns saved check summaries, newest first, including the checked key numbers. |
| GET | `/api/health-checks/<id>` | Returns one saved check with its related rows. |
| GET | `/api/alerts` | Returns the merged follow-up alerts of every saved check. |
| GET | `/api/export` | Returns every saved key check as a CSV download. |
| POST | `/api/health-checks` | Validates and stores one check for one selected key. |

`GET /api/key-status` returns one entry per key with `key_id`, `key_number`, `name`, `type`, `device`, `last_checked_at`, and `next_check_due`. A key that has never been checked has `null` dates. Whether a date is overdue is decided by the client from `next_check_due`, so the endpoint stays independent of the current date.

`POST /api/health-checks` accepts JSON and records exactly one configured key:

- `key_check` is one object with the selected `key_id`. When `available` is `0`, the remaining key fields are not required and are stored as empty.
- `wallet_software` is `Sparrow Wallet` or `Nunchuk`. Key 3 (the cloud key) only accepts `Nunchuk`.
- `tool_checks` must cover the selected key's product plus the selected wallet software, without duplicates: at most two rows, and one row for the cloud key. `bip327_status` and `slip39_status` accept `YES`, `NO`, or `NOT_ASSESSED`.
- `ai_security_checks` must cover the providers relevant to the selected key: the key's product, `Sparrow Wallet`, and `Nunchuk` for keys 1 and 2, and `Nunchuk` alone for key 3.
- `seed_backup_verified` (keys 1 and 2 only) and `address_path_verified` accept `OK` or `PROBLEM` and are required when the key was available.
- `software_compatibility_status` accepts `OK`, `PROBLEM`, or `NOT_ASSESSED`.
- `address_path` is only recorded when `address_path_verified` is `OK`; the form hides the field and clears it otherwise.
- `next_check_due` is ignored; the server derives it from `checked_at`.

Unknown statuses, unknown key ids, irrelevant or duplicated products and providers, invalid dates, and over-long text are rejected with `400`.

## CSV export

`GET /api/export` sends `helsesjekk-export.csv` as a download: UTF-8, comma separated, CRLF line endings, with a header row. It contains every saved key check, oldest first.

One row is one key check. The `Check id` column identifies the submission a row belongs to, so records saved before section 19 (up to three keys in one submission) stay grouped. Results that have more than one value per submission are joined into a single cell as `Label: value; Label: value`:

- `BIP327` and `SLIP39` list the key's product and the chosen wallet software.
- `Security status` lists the key's product, `Sparrow Wallet`, and `Nunchuk`, or `Nunchuk` alone for the cloud key.

Stored `0`/`1` values are written as `No`/`Yes`, matching the history view. Status values are written exactly as stored. Empty values are written as empty cells. Text that contains a comma, a quote, or a semicolon is quoted and escaped by the standard CSV rules, so the file can be opened directly in a spreadsheet.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise the follow-up alerts of **every** saved check:

```json
{"code": "key_unavailable", "severity": "critical", "source": "Key 1: SeedSigner", "message": "This key was not available. Replace the key before continuing; the remaining checks for this key cannot be recorded.", "check_id": 12, "checked_at": "2026-10-01"}
```

`check_id` and `checked_at` name the saved check an alert came from, so the dashboard can show where a warning originated. Identical alerts (same `code` and `source`) are merged, and only the newest one is listed, with its own date. Critical alerts come first, then the newest check first inside each severity. An alert from an older check therefore stays visible until a newer check for the same key and source resolves it.

`severity` is `critical` for results that require action (unavailable key, hardware failure, missing or damaged seed backup, a cloud provider that is not operating normally, failed address verification, software that no longer supports the hardware, security status `VULNERABLE` or `COMPROMISED`) and `info` for results that can be considered later (reported BIP327 or SLIP39 support, unconfirmed contact information).

A value that has not been assessed (`NOT_ASSESSED` or empty) never raises an alert, so "not assessed" is never confused with a negative result. A reported `NO` for BIP327 or SLIP39 is a negative result as well, and raises no alert. An unavailable key raises one critical alert only, because the remaining checks for the key could not be performed; for the cloud key that single alert also states that the provider is recorded as not operating.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

## Development

The web server, validation, alert rules, export, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.

The application UI, source code, comments, and technical documentation are in English. `TODO.md` is intentionally written in Norwegian. Two names are deliberate exceptions to the English rule: the product name **Helsesjekk** and the database file name **`data/helsesjekk.sqlite3`**.

Stored status values are English. General results are `OK`, `PROBLEM`, or `NOT_ASSESSED`; the two verification results are `OK` or `PROBLEM`; BIP327 and SLIP39 are `YES`, `NO`, or `NOT_ASSESSED`; the security statuses are `SECURE`, `PATCHED`, `VULNERABLE`, and `COMPROMISED`.

Databases created by earlier versions are migrated on startup, up to schema version 6:

- The removed columns are dropped, and the old boolean verification flags become `OK`/`PROBLEM`.
- The Norwegian security status values become the English ones.
- `IKKJE_VURDERT` becomes `NOT_ASSESSED`, and the BIP327/SLIP39 results `OK`/`PROBLEM` become `YES`/`NO`.

Because `health_checks` is a parent table with foreign keys from the three child tables, the migration disables foreign keys for the transaction, checks them with `PRAGMA foreign_key_check` before committing, and rolls back if anything is wrong. Older records keep rendering in the history.
