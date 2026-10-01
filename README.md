# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The English dashboard loads the three fixed key profiles from SQLite. The profiles are seeded idempotently when the service starts, and `GET /api/keys` returns them as JSON. Check forms, saving health checks, history, alerts, and report export are not implemented yet. The dashboard does not claim that any device or backup has been tested.

## Run locally

Requires Python 3.9 or later. No third-party packages are needed.

```sh
python3 app.py
```

Open <http://localhost:8080>. Set the `PORT` environment variable to use a different port. Set `DATABASE_PATH` to change the SQLite database file location; it defaults to `data/helsesjekk.sqlite3`. The `GET /health` endpoint returns `{"status":"ok"}` for service health checks.

Run the tests with:

```sh
python3 -m unittest discover -s tests
```

## Development

The web server and database use Python's standard library. The server serves only explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details. The application UI, source code, comments, and technical documentation must be in English; `TODO.md` is intentionally written in Norwegian.
