# Working in this repository

This repository holds **both** the VardKey application and its StartOS package, side by side at the
repository root. The application is the Python source at the top level (`app.py`, `database.py`,
`alerts.py`, `export.py`, `validation.py`, `auth.py`, `maintenance.py`, `secret_guard.py`,
`static/`, `tests/`); the package is `startos/` together with the `Dockerfile`, `Makefile`,
`package.json`, `tsconfig.json`, and the rest of the StartOS skeleton.

## Repository mechanics

- **The package repo is also the application repo.** The packaging guide says a package repo is not
  a fork of the application. That rule assumes a published upstream image or a git submodule, and
  VardKey has neither — it is our own application and publishes no image — so the package builds
  the application from this repository's root. **Do not add an `upstream-project/` submodule to
  "fix" this**; it would point at this same repository and break the build.
- **There is no CI.** The packaging guide assumes GitHub Actions workflows. This repository is on
  Gitea, so there are no `.github/workflows/` and there must not be any. Build the `.s9pk` locally
  with `make`.
- **The image is built by `Dockerfile`**, referenced as `dockerBuild: {}` in
  `startos/manifest/index.ts`, which makes the build context the repository root. Anything the
  `Dockerfile` does not `COPY` is not in the image. The `COPY *.py ./` line is what keeps a new
  module from being left out; see the traps in `ai-note.md`.
- **The application is pure Python standard library.** There is no `requirements.txt` and no
  package-installation step in the image.
- **The package version is date based.** It lives in `startos/versions/current.ts` as
  `YYYY.MM.DD:revision`, and the bump edits `version` and `releaseNotes` in place — `index.ts` and
  the `current` export never change, and `startos/versions/` stays otherwise empty because the
  application migrates its own schema. `UPDATING.md` carries the rule, including the trap that
  ExVer normalizes numeric leading zeros, so a single-digit month or day is written without one
  (`2026.1.5`, not `2026.01.05`). The git tag is the version with `:` replaced by `_` and a leading
  `v` (`v2026.10.28_0`), pushed individually.
- **The admin account is touched outside the HTTP API only by `maintenance.py`.** The two StartOS
  actions, `delete-all-data` and `set-admin-password`, run it in a `withTemp` subcontainer, and the
  generated password never travels from the host into the container, as an argument or on stdin:
  `maintenance.py` generates it inside the container and prints the credentials back. The task that
  asks the user to set the password is raised and cleared by `startos/init/requireAdmin.ts`, which
  is registered in `sdk.setupInit()` after the actions; on the box it shows as *recommended*, so it
  does not hold the service back. Its probe fails open.

## Things that look right and are not

- **Do not add a `USER` line to the `Dockerfile`.** The `main` volume is mounted at `/data` and
  must be writable without a `chown`; dropping privileges in the image makes the SQLite database
  unwritable.
- **`static/` must be `COPY`ed into the image.** `app.py` answers `/health` from code, but every
  page and asset is read from `ROOT/static`. Leave it out and the health check goes green while the
  whole UI answers `404`.
- **The internal port must be the same in three places.** `startos/utils.ts` holds `uiPort`;
  `startos/main.ts` passes it as `PORT` to the daemon and uses it in the readiness URL, and
  `startos/interfaces.ts` binds it. Changing one alone leaves the readiness check permanently red.
- **Do not add a second container, Postgres, Redis, an external backend, or external storage for
  application data.** This is a standing prohibition, not a work item — see `TODO.md` sections 1
  and 13.

## Tests

```sh
python3 -m unittest discover -s tests
```

The suite is the application's regression net and does not exercise the package. It must stay
green, on Linux and on the Windows copy alike.

It also covers `secret_guard.py`, the one place that decides whether a piece of free text looks like
a wallet secret. That module is local, silent, and narrow by design: it makes no network call, never
puts the text in a log, a message, or an exception, and matches only unmistakable shapes. The
embedded BIP39 wordlist is pinned by the suite — 2048 words, alphabetical, 3–8 lower-case letters,
and no two words sharing their first four letters — and so are the shapes the guard recognises and
the shapes it deliberately does not. **Do not edit the wordlist without that test.**

## Build

```sh
make x86        # or: make arm
```

Building needs a StartOS packaging workspace — see the packaging guide's Environment Setup.
`make x86` also runs `prettier --check startos` with the SDK's own config, so the TypeScript files
under `startos/` have to be formatted the way prettier would write them. `make install` needs
`host.default` in the workspace `.startos/config.yaml` and one `start-cli auth login`.
