<p align="center">
  <img src="icon.svg" alt="VardKey Logo" width="21%">
</p>

# VardKey on StartOS

> Everything not listed in this document should behave the same as the VardKey
> application itself. If a feature, setting, or behavior is not mentioned here,
> the application's own documentation is accurate and fully applicable — see the
> Documentation section of `instructions.md`.

VardKey records the annual health check of a Bitcoin multisig setup, 2-of-3 by default: the keys,
the yearly checklist, the follow-up alerts, and the full history, in a local SQLite database. It
does not sign transactions, perform wallet operations, or store wallet secrets. The application
source is this repository: <https://github.com/sondreolav/vardkey>.

The application reference — the HTTP API and the rules it enforces — is in
[`docs/application.md`](docs/application.md). This file documents the StartOS package around it.

---

## Table of Contents

- [Image and Container Runtime](#image-and-container-runtime)
- [Volume and Data Layout](#volume-and-data-layout)
- [File Models](#file-models)
- [Dependencies](#dependencies)
- [Network Access and Interfaces](#network-access-and-interfaces)
- [Installation and First-Run Flow](#installation-and-first-run-flow)
- [Actions](#actions)
- [Tasks](#tasks)
- [Health Checks](#health-checks)
- [Backups and Restore](#backups-and-restore)
- [Limitations and Differences](#limitations-and-differences)
- [Quick Reference for AI Consumers](#quick-reference-for-ai-consumers)

---

## Image and Container Runtime

The package builds the application from this repository's root with the `Dockerfile`, referenced
as `dockerBuild: {}` in the manifest. There is no upstream image and no git submodule: VardKey is
our own application, so the package and the application move together in one repository.

The image is a slim Python base with the application copied in. The application uses only the
Python standard library, so the image installs no packages. The `Dockerfile` deliberately declares
no `USER`: the `main` volume is mounted at `/data` and must be writable without a `chown`, so the
daemon runs as the image default.

One subcontainer runs, named `vardkey-sub`, hosting a single daemon named `primary`. The daemon
runs `python3 app.py`. There is no sidecar, no oneshot, and no second container.

The `COPY` lines matter: `app.py`, `database.py`, `alerts.py`, `export.py`, `validation.py`,
`auth.py`, `maintenance.py`, and `secret_guard.py` are copied to `/app`, and `static/` is copied to
`/app/static`. `app.py` answers `/health` from code, but every page and asset is read from
`./static`, so an image built without it reports a healthy service whose entire UI answers `404`.

The package artwork is the `icon.svg` at the repository root, which the build reads from the root.
It is the same retro drawing as the icon the application serves, and the two must stay in step; it
must stay under 40 KiB.

## Volume and Data Layout

The package declares one volume, `main`, mounted writable at `/data`. It holds the SQLite
database; there is no separate config volume and no `startos` volume, because the package keeps no
state of its own outside the application's database.

The database file is `/data/vardkey.sqlite3`. The application's own default is
`data/vardkey.sqlite3` relative to the working directory, so the package overrides it with the
`DATABASE_PATH` environment variable to place it on the volume. Nothing else is written outside
`/data`.

Because the whole database is a single file on the volume, restoring the volume restores the entire
installation: the key profiles, every saved check, the wallet software list, and the alert
acknowledgements.

## File Models

None. The package defines no file models, and it writes no configuration file of its own.

Two environment variables are set on the daemon instead of being written to a file:

- `PORT` — the port the application listens on inside the container. It is a constant in
  `startos/utils.ts`, passed by `startos/main.ts`, and the same value is bound in
  `startos/interfaces.ts`. The three must agree or the readiness check never goes green.
- `DATABASE_PATH` — the absolute path of the SQLite database on the mounted volume, described
  above.

Both are set by the package on every start; a user has no reason to change either, and there is no
action that does.

The application does keep configuration of its own, but it lives in the database rather than in a
file: the key setup, the wallet software list, the admin account, and the settings are all rows. A
hand edit of the database file is therefore the only way to change them out of band, and it is not
supported.

## Dependencies

None. The package declares no required or optional dependencies. VardKey is entirely self-contained:
it contacts no other service, no Bitcoin node, and no external network endpoint.

## Network Access and Interfaces

The package exposes one interface:

| id | type | internal port | protocol | purpose |
| --- | --- | --- | --- | --- |
| `ui` | `ui` | `8080` | `http` | The VardKey web interface: dashboard, setup, health check form, history, settings, and CSV download. |

The interface is bound on the `ui` MultiHost with `preferredExternalPort: 80`. StartOS terminates
TLS at the platform edge and proxies plain HTTP to the container, so the application never builds an
absolute `http://` URL and never configures TLS itself.

The application binds `0.0.0.0` inside the container, so it is reachable on the interface the user
enables. Nothing else in the application listens on a port.

## Installation and First-Run Flow

Installing the package creates the `main` volume and starts the single daemon. There is no install
action and no generated credential: the whole first-run flow is the application's own, and the
package adds no ordering constraint on top of it.

On a fresh install the database is created empty, and the application shows its **create-admin
step** before anything else: the user picks a username and a password, and the session that answers
is the one every later page and API call needs. The `Set Admin Password` action and the task below
point at that same account, so a user who never reaches the web interface can set the password from
StartOS instead. See [Actions](#actions) and [Tasks](#tasks).

Once an admin exists, the application answers the **first-run setup step** rather than the
dashboard: the user gives the multisig threshold, the number of key slots, and each key a name, a
type, and an address path. That setup is the application's own flow at `/setup`, not a StartOS
action or task.

## Actions

Two actions are registered through `Actions.of()` in `startos/actions/index.ts`, with their strings
in `startos/i18n/dictionaries/`. Both appear under **Actions & Config** in StartOS.

| id | name | what it does |
| --- | --- | --- |
| `delete-all-data` | **Delete all data** | Deletes the key setup, the saved checks, and the wallet software list, so the app is back at the first-run setup step. The admin account is kept, so the user stays signed in. |
| `set-admin-password` | **Set Admin Password** | Generates a new admin password, shows it once, and replaces any existing one. An empty `Admin username` keeps the stored username, or creates the account when none exists. |

Both run `maintenance.py` in a `withTemp` subcontainer mounted on the `main` volume, and neither is
an HTTP endpoint. The generated password never travels from the host into the container, as an
argument or on stdin: `maintenance.py` generates it inside the container and prints the credentials
as one JSON object that the handler reads back. `delete-all-data` refuses to run without its
confirmation box ticked, and the handler enforces that, because a toggle has no `required` flag.

## Tasks

One task is raised, by the init script `startos/init/requireAdmin.ts`, which is registered in
`sdk.setupInit()` after the actions. While the database holds no admin, it raises the task
**Set the admin password before VardKey can be used.**, pointing at the `set-admin-password` action
above; once an admin exists, it clears the task again.

**The task does not hold the service back.** On the box it shows on Tasks as *recommended*, and the
user can start the app without an admin. That is not a bug: this SDK release offers no
`TaskCondition` for "the admin password is unset" — the only one is `input-not-matches`, which is
about an action's form — so the init script raises and clears the task itself, with a replay id it
writes once and reuses. What actually refuses everything until an admin exists is the application's
own login gate: `/api/*` answers `401`, the pages redirect to `/login`, and `/login` shows the
create-admin form.

The probe that decides this cannot read the application's SQLite database from its own JavaScript
context, so it runs a small `python3` command in a `withTemp` subcontainer that opens the database
**readonly**. It **fails open**: if the probe cannot run, no task is raised rather than a task being
raised on a guess, so a user who already has an admin is never held back by a wrong answer.

## Health Checks

One check exists: the daemon's readiness check, named `primary` and displayed to the user as
**Web Interface**. It calls `checkWebUrl` against `http://127.0.0.1:8080/health` inside the
container, and the application answers that endpoint with `{"status":"ok"}` as soon as its HTTP
listener is up. The check is green as soon as the process is listening; it says nothing about
whether the UI is usable.

There is no grace period and no standalone health check. A readiness check that stays red means the
daemon is not running or the port does not match: look at the service logs for a Python traceback,
and confirm that `PORT`, the `bindPort` value, and the readiness URL all name the same port. A
green check with a `404` on every page means `static/` did not make it into the image.

## Backups and Restore

The backup strategy is a volume snapshot: `sdk.Backups.ofVolumes('main')`. The whole volume is
copied, so the SQLite database is captured as a file rather than dumped and replayed. There are no
exclusions — the volume holds nothing that can be rebuilt.

StartOS stops the service for the duration of a backup, and restarts it afterwards only if it was
running when the backup began. The database file is therefore quiescent while it is copied, and no
separate snapshot hook is needed for a consistent copy. A restore puts the volume back as it was,
and the service starts against the restored database with no post-restore step: there is no
external state to re-register and no credential to re-enter, because the application keeps
everything in that one file and contacts nothing outside the container.

## Limitations and Differences

1. **It records results; it does not verify them.** VardKey never signs a transaction, never
   performs a wallet operation, and never checks a device itself. The user records what they found.
2. **No wallet secrets, by design.** The application never asks for or stores a seed phrase, a
   private key, a wallet password, or a cloud credential. This is a standing prohibition, not an
   unfinished feature.
3. **One setup only.** The application is built for exactly one multisig setup. Its threshold and
   its number of key slots are configured at first run — `2 ≤ key_count ≤ 15` and
   `1 ≤ threshold ≤ key_count`, with 2-of-3 as the default — but there is never a second setup.
4. **No external services.** There is no AI integration, no Bitcoin node integration, and no cloud
   sync of application data.
5. **A key with an open alert cannot be checked.** The server enforces this, so a direct API call
   cannot bypass it; the key becomes available again once the alert is closed with the action that
   belongs to it.
6. **The CSV export is plain CSV.** There is no XLSX export, and the application does not promise
   Excel compatibility.
7. **The database is not encrypted.** The SQLite file sits in plain form on the `main` volume, so
   anyone who can read the volume or a backup can read every key profile and every saved check.
   StartOS's own disk encryption and volume access controls are what protect it; the application
   adds no encryption of its own.
8. **Free text is screened locally, not comprehensively.** Every free-text field is checked by
   `secret_guard.py` before it is stored, so the unmistakable wallet-secret shapes are refused with
   `400`, but a bare 64-character hex string, a phrase in another language, or a secret split across
   several fields is not caught. The check makes no network call.

## Quick Reference for AI Consumers

```yaml
package_id: vardkey
image: python
architectures: [x86_64, aarch64]
subcontainers: [vardkey-sub]
volumes:
  main: /data
file_models: []
startos_managed_env_vars:
  - PORT
  - DATABASE_PATH
dependencies: none
interfaces:
  ui: { type: ui, port: 8080 }
actions: [delete-all-data, set-admin-password]
tasks: [set-admin-password]
health_checks: []
donation_url: https://sondreolav.com/donations
```
