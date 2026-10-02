# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three fixed key profiles, the latest saved check dates, and the active follow-up alerts. The annual health-check form records the full checklist and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. Report export and the StartOS package are not implemented yet. The application does not claim that any device or backup has been tested.

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
| GET | `/api/health-checks` | Returns saved check summaries, newest first. |
| GET | `/api/health-checks/<id>` | Returns one saved check with its related rows. |
| GET | `/api/alerts` | Returns the follow-up alerts of the most recent saved check. |
| POST | `/api/health-checks` | Validates and stores one annual health check. |

`POST /api/health-checks` accepts JSON. All three keys, all four products (BIP327/SLIP39), and a security status for all four providers are required. Unknown statuses, unknown key ids, invalid dates, and over-long text are rejected with `400`.

## Alerts

`GET /api/alerts` returns `[]` when no check has been saved, and otherwise one entry per result that needs follow-up in the most recent saved check:

```json
{"code": "key_unavailable", "severity": "critical", "source": "Key 1: SeedSigner", "message": "This key was not available. Immediate follow-up is required."}
```

`severity` is `critical` for results that require action (unavailable key, hardware failure, missing or damaged seed backup, failed address verification, software that no longer supports the hardware, security status `SÅRBAR` or `KOMPROMITTERT`) and `info` for results that can be considered later (reported BIP327 or SLIP39 support, unconfirmed contact information). Critical alerts are listed first. A value that has not been assessed (`IKKJE_VURDERT` or empty) never raises an alert, so "not assessed" is never confused with a negative result.

The application only reports these alerts. It never performs the follow-up actions itself, and it never contacts providers or AI services.

## Development

The web server, validation, alert rules, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details. The application UI, source code, comments, and technical documentation must be in English; `TODO.md` is intentionally written in Norwegian, and the stored status values (`IKKJE_VURDERT`, `TRYGG`, `PATCHA`, `SÅRBAR`, `KOMPROMITTERT`) are data values taken from the requirement specification.
