<p align="center">
  <img src="icon.svg" alt="VardKey Logo" width="21%">
</p>

# VardKey on StartOS

> Everything not listed in this document should behave the same as the VardKey
> application itself. If a feature, setting, or behavior is not mentioned here,
> the application's own documentation is accurate and fully applicable — see the
> Documentation section of `instructions.md`.

VardKey records the annual health check of a fixed 2-of-3 Bitcoin multisig setup: the three keys,
the yearly checklist, the follow-up alerts, and the full history, in a local SQLite database. It
does not sign transactions, perform wallet operations, or store wallet secrets. The application
source is this repository: <https://gitea.sondreolav.com/ai-bot/helsesjekk>.

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

The `COPY` lines matter: `app.py`, `database.py`, `alerts.py`, `export.py`, and `validation.py` are
copied to `/app`, and `static/` is copied to `/app/static`. `app.py` answers `/health` from code,
but every page and asset is read from `./static`, so an image built without it reports a healthy
service whose entire UI answers `404`.

## Volume and Data Layout

The package declares one volume, `main`, mounted writable at `/data`. It holds the SQLite
database; there is no separate config volume and no `startos` volume, because the package keeps no
state of its own outside the application's database.

The database file is `/data/vardkey.sqlite3`. The application's own default is
`data/vardkey.sqlite3` relative to the working directory, so the package overrides it with the
`DATABASE_PATH` environment variable to place it on the volume. Nothing else is written outside
`/data`.

Because the whole database is a single file on the volume, restoring the volume restores the entire
installation: the three key profiles, every saved check, the wallet software list, and the alert
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
file: the key setup, the wallet software list, and the settings are all rows. A hand edit of the
database file is therefore the only way to change them out of band, and it is not supported.

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
action, no generated credential, and no bootstrapping step run through the application's own API.

On a fresh install the database is created empty, and the application answers the first-run setup
step rather than the dashboard: the user gives each of the three key slots a name, a type, and an
address path. That setup is the application's own flow at `/setup`, not a StartOS action or task.
The package adds no ordering constraint on top of it.

## Actions

None. The package declares no actions. Everything the user does — the key setup, the health check
form, the history, the settings, and the CSV download — is done through the web interface.

## Tasks

None. The package creates no tasks, so the service is never held on a prompt and its ordinary
Start / Stop controls are always available.

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
3. **One setup only.** The application is built for exactly one 2-of-3 multisig setup with three
   key slots. More than three keys, or another threshold, is not supported.
4. **No external services.** There is no AI integration, no Bitcoin node integration, and no cloud
   sync of application data.
5. **A key with an open alert cannot be checked.** The server enforces this, so a direct API call
   cannot bypass it; the key becomes available again once the alert is closed with the action that
   belongs to it.
6. **The CSV export is plain CSV.** There is no XLSX export, and the application does not promise
   Excel compatibility.
7. **The package id is `vardkey`, while the repository is `helsesjekk`.** The Gitea repository and
   the project id keep the older name; only the product and the package were renamed.
8. **The icon is a placeholder.** It will be replaced when the package reaches its first release.

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
actions: []
tasks: []
health_checks: []
```
