# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three fixed key profiles, the latest saved check dates, and the active follow-up alerts. Each key card shows its own last check date and next due date, and the summary cards above the alerts show the earliest upcoming date and any key that has passed its due date. The annual health-check form records the checklist for **one selected key per submission** and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. Report export and the StartOS package are not implemented yet. The application does not claim that any device or backup has been tested.

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
| GET | `/api/alerts` | Returns the follow-up alerts of the most recent saved check. |
| POST | `/api/health-checks` | Validates and stores one check for one selected key. |

`GET /api/key-status` returns one entry per key with `key_id`, `key_number`, `name`, `type`, `device`, `last_checked_at`, and `next_check_due`. A key that has never been checked has `null` dates. Whether a date is overdue is decided by the client from `next_check_due`, so the endpoint stays independent of the current date.

`POST /api/health-checks` accepts JSON and records exactly one configured key:

- `key_check` is one object with the selected `key_id`. When `available` is `0`, the remaining key fields are not required and are stored as empty.
- `wallet_software` is `Sparrow Wallet` or `Nunchuk`. Key 3 (the cloud key) only accepts `Nunchuk`.
- `tool_checks` must cover the selected key's product plus the selected wallet software, without duplicates: at most two rows, and one row for the cloud key.
- `ai_security_checks` must cover the providers relevant to the selected key: the key's product, `Sparrow Wallet`, and `Nunchuk` for keys 1 and 2, and `Nunchuk` alone for key 3.
- `seed_backup_verified` (keys 1 and 2 only) and `address_path_verified` accept `OK` or `PROBLEM` and are required when the key was available.
- `next_check_due` is ignored; the server derives it from `checked_at`.

Unknown statuses, unknown key ids, irrelevant or duplicated products and providers, invalid dates, and over-long text are rejected with `400`.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise one entry per result that needs follow-up in the most recent saved check:

```json
{"code": "key_unavailable", "severity": "critical", "source": "Key 1: SeedSigner", "message": "This key was not available. Replace the key before continuing; the remaining checks for this key cannot be recorded."}
```

`severity` is `critical` for results that require action (unavailable key, hardware failure, missing or damaged seed backup, a cloud provider that is not operating normally, failed address verification, software that no longer supports the hardware, security status `VULNERABLE` or `COMPROMISED`) and `info` for results that can be considered later (reported BIP327 or SLIP39 support, unconfirmed contact information). Critical alerts are listed first. A value that has not been assessed (`IKKJE_VURDERT` or empty) never raises an alert, so "not assessed" is never confused with a negative result. An unavailable key raises that one critical alert only, because the remaining checks for the key could not be performed.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

## Development

The web server, validation, alert rules, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.

The application UI, source code, comments, and technical documentation are in English. `TODO.md` is intentionally written in Norwegian. The stored data values are `OK`, `PROBLEM`, and `IKKJE_VURDERT` for general results, `OK` and `PROBLEM` for the two verification results, and `SECURE`, `PATCHED`, `VULNERABLE`, and `COMPROMISED` for the security status.

Databases created by earlier versions are migrated on startup: the removed columns are dropped, the old boolean verification flags become `OK`/`PROBLEM`, and the Norwegian security status values become the English ones. Older records keep rendering in the history.
