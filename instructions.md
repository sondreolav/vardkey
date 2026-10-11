# VardKey

## Documentation

- [VardKey repository](https://gitea.sondreolav.com/ai-bot/helsesjekk) — the application source, its HTTP API reference, and the development notes.

## What you get on StartOS

VardKey runs as a single service with its own web interface and a local SQLite database on the service volume. Everything you record stays on your own server: the three key profiles, the annual health checks, the follow-up alerts, and the CSV export.

## Getting set up

1. Start the service and open its web interface. On a fresh install there is no key setup yet, so VardKey opens the setup step instead of the dashboard.
2. On the setup step, give each of the three key slots a name, a type (`Hardware` or `Cloud`), and its address path. The name is only a label and can be changed later; the type and the address path are locked once the setup is saved, and no two keys may share an address path.
3. Open the dashboard, which then shows the three keys with their check dates and any open alerts.

## Using VardKey

### Web interface

The dashboard shows the three keys with their last check date and next due date, the earliest upcoming date, and every open follow-up alert. `Start annual health check` opens the check form, `History` lists the saved checks, `Settings` holds the wallet software list and the key rotation, and `Download CSV` exports the report.

The health check form has six sections, in this order: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. One submission records one key. A key with an open alert cannot be checked until that alert is closed.

## Limitations

- VardKey only records results. It never signs a Bitcoin transaction, never performs a wallet operation, and never asks for or stores a seed phrase, a private key, or a wallet password.
- The setup is built for one 2-of-3 multisig setup with exactly three keys. More than three keys, or another threshold, is not supported.
- An open alert blocks its key until the alert is closed with the action that belongs to it.
