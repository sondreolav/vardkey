# Working in this repository

This repository holds **both** the VardKey application and its StartOS package, side by side at the
repository root. The application is the Python source at the top level (`app.py`, `database.py`,
`alerts.py`, `export.py`, `validation.py`, `static/`, `tests/`); the package is `startos/` together
with the `Dockerfile`, `Makefile`, `package.json`, `tsconfig.json`, and the rest of the StartOS
skeleton.

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
  `Dockerfile` does not `COPY` is not in the image.
- **The application is pure Python standard library.** There is no `requirements.txt` and no
  package-installation step in the image.

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

## Build

```sh
make x86        # or: make arm
```

Building needs a StartOS packaging workspace — see the packaging guide's Environment Setup.
`make install` needs `host.default` in the workspace `.startos/config.yaml` and one
`start-cli auth login`.
