# VardKey

## Documentation

- [VardKey repository](https://github.com/sondreolav/vardkey) — the application source, its HTTP API reference, and the development notes.

## What you get on StartOS

VardKey runs as a single service with its own web interface and a local SQLite database on the service volume. Everything you record stays on your own server: the key profiles, the annual health checks, the follow-up alerts, and the CSV export.

## Getting set up

1. Start the service and open its web interface. On a fresh install there is no admin account yet, so VardKey opens the **create-admin** step first: choose a username and a password of at least 8 characters. You are signed in straight away, and the session lasts 30 days.
2. The key setup step comes next, because no key setup is stored yet. Choose the multisig threshold and the number of key slots, then give each key a name, a type (`Hardware` or `Cloud`), and its address path. The name is only a label and can be changed later; the type and the address path are locked once the setup is saved, and no two keys may share an address path.
3. Open the dashboard, which then shows the keys with their next due dates and any open alerts.

If you would rather not sign in through the browser — or if the password is lost — use the **Set Admin Password** action under **Actions & Config**: it generates a new password inside the container and shows it once. StartOS also raises the task *Set the admin password before VardKey can be used.* while no admin exists, and it points at the same action. The task is listed as *recommended*, so it does not stop the service from starting; the app's own login gate is what keeps everything closed until an admin exists.

## Using VardKey

### Web interface

The dashboard shows the keys with their next due date and any open alerts, plus an Attention card that names the earliest upcoming date, or the keys that have passed it. `Start annual health check` opens the check form, `History` lists the saved checks and carries the CSV export, `Settings` holds the wallet software list and the key rotation, and `Sign out` ends the session. All of it lives in the `Menu` button in the top bar, and the page you are already on is greyed out.

The health check form has six sections, in this order: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. One submission records one key, and the check date may be today or earlier — never a future date. A key with an open alert cannot be checked until that alert is closed.

The history list carries one entry per saved check, with the date and the key it was recorded for, and a short status: `All OK` when the check raised nothing, `Needs follow-up` while something is still open, and `Follow-up closed` once everything that was raised has been closed. Opening a check shows the follow-up that was closed on it, with the source of each alert, so a key alert and a software alert of the same kind can be told apart.

### Actions & Config

Two actions are available on the service page, under **Actions & Config**:

- **Delete all data** — deletes the key setup, the saved checks, and the wallet software list, so the app is back at the first-run setup step. The admin account is kept, so you stay signed in. It cannot be undone, so it asks for a confirmation box first.
- **Set Admin Password** — generates a new admin password and shows it once, replacing any existing one. Leave the username field empty to keep the current username, or to create the account when none exists yet.

## Limitations

- VardKey only records results. It never signs a Bitcoin transaction, never performs a wallet operation, and never asks for or stores a seed phrase, a private key, or a wallet password. Free-text fields are screened locally before they are stored, so the unmistakable wallet-secret shapes are refused, but that check is not comprehensive.
- The setup is built for one multisig setup. Its threshold and its number of key slots are chosen at first run — 2 to 15 keys, with 2-of-3 as the default — but there is never a second setup.
- An open alert blocks its key until the alert is closed with the action that belongs to it.
- The SQLite database sits unencrypted on the service volume; StartOS's own disk encryption and volume access controls are what protect it.
