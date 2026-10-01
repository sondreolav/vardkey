# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard shows the three fixed key profiles and the latest saved check dates. The annual health-check form records the full checklist and saves it to a local SQLite database, and `/history` lists saved checks with a read-only detail view. Alerts, report export, and the StartOS package are not implemented yet. The application does not claim that any device or backup has been tested.

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
| POST | `/api/health-checks` | Validates and stores one annual health check. |

`POST /api/health-checks` accepts JSON. All three keys, all four products (BIP327/SLIP39), and a security status for all four providers are required. Unknown statuses, unknown key ids, invalid dates, and over-long text are rejected with `400`.

## Development

The web server, validation, and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details. The application UI, source code, comments, and technical documentation must be in English; `TODO.md` is intentionally written in Norwegian.
