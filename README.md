# Helsesjekk

Helsesjekk is a local web application for recording annual checks of a fixed 2-of-3 multisig setup. It does not sign transactions, perform wallet operations, or store seed phrases, private keys, passwords, or other wallet secrets.

## Current status

The initial dashboard is a UI scaffold. Check forms, database storage, key editing, history, alerts, and report export are not implemented yet. The dashboard does not claim that any device or backup has been tested.

## Run locally

Requires Python 3.9 or later. No third-party packages are needed.

```sh
python3 app.py
```

Open <http://localhost:8080>. Set the `PORT` environment variable to use a different port. The `GET /health` endpoint returns `{"status":"ok"}` for service health checks.

## Development

The web server uses Python's standard library and serves only the explicitly listed static assets. Keep application data local; never add fields for seed phrases, private keys, wallet passwords, cloud credentials, or contact details.
