# AI Agent Note — VardKey

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification. Sections 1–18 are the binding spec; sections 19–30 are short summaries of the rounds that are implemented and verified, and section 31 is the round in progress. The full reasoning is in the git history.
- The binding rules live in `TODO.md` and `README.md`. This note does not repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 1–30, and section 18 steps 1–11. Schema version 12. 416 green tests.
- **Section 30 is done and verified.** The StartOS package lives in this repository beside the application: `startos/`, `Dockerfile`, `.dockerignore`, `Makefile`, `package.json`, `tsconfig.json`, `.prettierrc`, `LICENSE`, `icon.svg`, `instructions.md`, `UPDATING.md`, `AGENTS.md`, `README.md`, and `CLAUDE.md`. It built clean with `make x86` into `vardkey_x86_64.s9pk`, was sideloaded onto a StartOS 0.4.0 box, and runs there: the service shows **Running**, the health check reports **The web interface is ready**, and **Open UI** opens the VardKey web app. Sections 14, 16 and 17 were exercised on that box and are ticked in `TODO.md`.
- **Next work: section 31 — the eight points before version 1.** **In progress: points 7, 5, 4, 3, 2 and 1 are done.** Point 6 (the installable PWA) has its service worker, its registration and its offline state in place; the manifest, its `<link>` and the two PWA icons wait for the artwork, because the manifest needs a 192 and a 512 px icon. Point 8 (the icon) waits for the same artwork. The plan, the order and the file lists live in `TODO.md` section 31; the state of the round is at the top of that section. Read it there before touching anything.
- **Two things are still deliberately left in section 30, and both need the user's go-ahead.** Do **not** raise the package version from `0.1.0:0` to `1.0.0:0`, and do **not** draw the real `icon.svg`. Section 31 comes first, and it carries the icon as its eighth point.
- **A round stops when it is done.** Section 31 is the round. Do not roll into the version bump, into section 18 step 12, or into anything after it.
- **Verified how:** the automated suite, the user's manual browser testing, and the install and test round on a StartOS 0.4.0 box. The manual tests in section 16 are all run.
- **Tests:** the user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\<brukarnamn>\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Future work, deliberately not built:** nothing is left here. The last item — more than three keys, and another threshold than 2-of-3 — was done in section 31 point 7.

## Section 30 — the StartOS package

The package is one service: one daemon, one container, one SQLite database on the persistent `main` volume, mounted at `/data`. No Postgres, no Redis, no external backend, no extra container.

The decisions are recorded in `TODO.md` section 30; this is what the next model needs on top of them.

### Where the files live, and why

The application and the package share one repository, at the root. That is a deliberate deviation from the guide's "a package repo is not a fork of the application": the rule assumes a published upstream image or a git submodule, and VardKey has neither. `AGENTS.md` states the deviation so nobody adds an `upstream-project/` submodule to "fix" it.

The image is built by the root `Dockerfile`, referenced as `dockerBuild: {}` in `startos/manifest/index.ts`, which makes the build context the repository root. **Anything the `Dockerfile` does not `COPY` is not in the image.** In particular `static/` must be copied: `app.py` answers `/health` from code, but every page is read from `ROOT/static`, so an image without it reports a healthy service whose entire UI answers `404`. `maintenance.py` is copied too, for the `Delete history` action. New static files must be added to both the `Dockerfile` and `STATIC_FILES` — section 31 still owes the login page, `session.js`, the manifest, `sw.js` and the PWA icons.

There is no CI. The guide assumes GitHub Actions; this repository is on Gitea, so there are no `.github/workflows/` and there must not be any. The `.s9pk` is built locally with `make`.

### The three things that must agree

`startos/utils.ts` holds `uiPort` (8080). `startos/main.ts` passes it as `PORT` to the daemon and uses it in the readiness URL; `startos/interfaces.ts` binds it. Change one alone and the readiness check never goes green. The `DATABASE_PATH` constant in the same file is what puts the database on the volume instead of the application's own default of `data/vardkey.sqlite3` relative to the working directory.

The readiness check is `checkWebUrl` against `http://127.0.0.1:8080/health`, not `checkPortListening` — section 30 asks for the endpoint, and `/health` is the application's own. **Section 31 point 1 puts every other route behind a login, so `/health` must stay open, or StartOS reports the service as unhealthy.** A red `ECONNREFUSED 127.0.0.1:8080` blip before `VardKey listening on port 8080` is just the first readiness poll landing before Python has bound the socket; the check polls again and goes green. Nothing to fix.

### Actions

`startos/actions/deleteHistory.ts` is the first action, registered through `Actions.of()` in `startos/actions/index.ts`, with its strings in `startos/i18n/dictionaries/`. Section 31 point 1 adds `setAdminPassword.ts` the same way, and its command reaches the container through `maintenance.py`.

### Backups

`startos/backups.ts` is `sdk.Backups.ofVolumes('main')`. The open question section 30 raised — whether `setupBackups` has a hook for a consistent SQLite snapshot — turned out not to need one: StartOS stops the service for the duration of a backup, so the database file is quiescent while it is copied. That is written up in `README.md` and in `startos/backups.ts`; it is not a known limitation. Restore was tested on the box and brought the setup and the saved checks back.

### Notes on the skeleton

The skeleton files (`package.json`, `tsconfig.json`, `Makefile`, `.prettierrc`, `startos/sdk.ts`, `startos/index.ts`, `startos/i18n/`, `startos/fileModels/.gitkeep`, `assets/.gitkeep`) were written to match the Start9 template rather than generated by `s9pk init-workspace`, because that command was not available in the environment that wrote them. The successful build and install confirm they are equivalent; `@start9labs/start-sdk` is pinned to `3.0.4` and that is the version the `.s9pk` was built with. No reconciliation is outstanding.

The `icon.svg` in the repository is a minimal placeholder, kept so the build has an icon to pack. Section 30 defers the real one; section 31 point 8 brings it in.

### Documentation layout

`README.md` is the StartOS package README, with the guide's fixed heading set. The application's own reference — the HTTP API, the alerts table, the schema history — moved to `docs/application.md`, which is what `instructions.md` links to under `## Documentation`. `AGENTS.md` is the repo-specific agent context, and `CLAUDE.md` is the one-line `@AGENTS.md` import. Section 31 changes all of them: new endpoints, a new schema version, and two new actions.

## Section 31 — the eight points before version 1

Decided 10.10.2026. **In progress.** The plan, the per-point file lists and the tests are in `TODO.md` section 31; this is what is easy to get wrong.

### Where the round stands

- **Done: points 7, 5, 4, 3, 2 and 1.** The schema is 12. `maintenance.py` (with `delete-history` and `set-admin-password`), `startos/actions/deleteHistory.ts`, `startos/actions/setAdminPassword.ts`, and the test modules `test_multisig_setup.py`, `test_key_model.py`, `test_key_status.py`, `test_export_filename.py`, `test_maintenance.py` and `test_pwa.py` are all in the repository. Point 1 added `auth.py`, `static/login.html`, `static/login.js`, `static/session.js`, the login/logout/session/create-admin routes and the gating in `app.py`, and the CSRF double-submit on every state-changing POST. `auth.py` is the only place that knows the credential: `hash_password`, `verify_password`, `normalize_admin_username`, `validate_admin_credentials`, `get_admin`, `admin_configured`, `set_admin`, `authenticate`, `session_secret`, `create_session_token`, `verify_session_token`, `new_csrf_token` and `csrf_tokens_match`, with the constants `SESSION_COOKIE`, `CSRF_COOKIE` and `CSRF_HEADER`. **Build on this. Do not invent a second session mechanism.**
- **Partly done: point 6, the PWA.** `static/sw.js` caches only the shell, and it does it with an allowlist of the shell paths, so it never names the API, `/health` or the login page. `static/app.js` registers the worker and shows a clear offline state. `static/sw.js` is in `STATIC_FILES` and `app.py` lists `/sw.js`. **Still owed by point 6:** `static/manifest.webmanifest`, its `<link>` in the five pages, and the `STATIC_FILES` entry for it — all of which wait for the artwork, because the manifest needs a 192 and a 512 px icon.
- **Not started: point 8, the icon.** It waits for the user's artwork; the placeholder `icon.svg` stays until then.
- **The order is 7, 5, 4, 3, 2, 1, 6, 8** — the data model first, because everything else builds on it. Do not reorder it back.

### The order is not the numbering

The eight points are numbered by the user but are done in the order 7, 5, 4, 3, 2, 1, 6, 8 — the data model first, because everything else builds on it. Do not reorder it back.

**The schema went 11 → 12** (points 7 and 5), and **the package version stays at `0.1.0:0`**. Nothing in this round touches `startos/versions/`.

### It amends three parts of the binding spec

- **Section 1 forbids "PWA/offline-database".** The user has decided on an **installable PWA without offline data**: the shell may be cached, no API response may be, and there is no offline data entry. The prohibition now reads as "no offline database and no offline recording of checks".
- **Sections 2 and 15 forbid asking for and storing "passwords".** That is about *wallet* secrets. The admin login password is a different thing and is the only credential the app stores, as a `hashlib.scrypt` hash. Both sections must be reworded so this is explicit, or the code contradicts the spec.
- **Section 3's unchecked box** — "do not build general support for many setups yet" — is closed by point 7. It stays **one** setup; only its threshold and key count become configurable.

### The traps, per point

- **Point 7, dynamic key count — done.** `KEY_COUNT` is no longer a constant; it is read from `app_settings`, and `keys.key_number`'s CHECK was loosened through a table rebuild with `PRAGMA foreign_keys = OFF` and `PRAGMA foreign_key_check` before commit. `tests/test_health_check_form.py` no longer asserts the three hard-coded `key_N_name` fields in `setup.html`; it asserts the markup `setup.js` generates.
- **Point 5, the model/service field — done.** One nullable column through `OPTIONAL_COLUMNS`, so no rebuild. It is **documentation only**: not a wallet-software choice, not part of the alert source, not part of a key's identity, so it is not locked. The key's `name` keeps doing everything it does today (section 25.4 and section 28). The label switches with the type — "Model" for hardware, "Service" for cloud — but the column name does not.
- **Point 4, the address path on the card — done.** `GET /api/key-status` now returns `address_path`, and an empty path does not render an empty line.
- **Point 3, the dated export name — done.** `static/index.html` no longer carries a `download` attribute with a value, because one **overrides the server's `Content-Disposition` filename**; the server names the file `YYYY-MM-DD-vardkey-export.csv`.
- **Point 2, delete history — done.** `alert_acknowledgements` has **no foreign key**, so it does not cascade and is deleted explicitly; `key_checks` and `ai_security_checks` do cascade. The key setup, `app_settings` and `wallet_software` stay. `maintenance.py` is `COPY`ed into the image, or the action would fail at runtime on the box while the tests stayed green.
- **Point 1, the admin password — done.** The first run has no admin, so the login page can *create* one; every route except `GET /health` is gated, with `401` on the API and a redirect on the pages; the session is a signed cookie with `HttpOnly` and `SameSite=Strict`; and every state-changing POST needs the double-submit CSRF token. The StartOS action generates the password **inside the container** and shows it once, because the SDK documents no way to feed stdin to a `withTemp` command and an argument would be visible in the process list — that is the packaging guide's own password-reset pattern.
- **Point 6, the PWA — partly done.** The service worker must cache **only** the shell — never `/api/*`, never `/health`, never the login page, or the app shows stale or unauthenticated data. It is served from the root, because its scope is bounded by its path, so `/sw.js` is in `STATIC_FILES`. It only registers in a secure context: fine on StartOS over HTTPS and on `http://localhost`, but not on a LAN IP over plain HTTP, and that belongs in the docs. The shell comes from the cache while every fetch fails, so the UI needs a clear offline state instead of empty cards. The manifest needs 192 and 512 px icons from point 8, so `manifest.webmanifest` and its `STATIC_FILES` entry are the last pieces to land.
- **Point 8, the icon.** The user supplies the artwork. The package `icon.svg` is capped at 40 KiB, and the PWA needs 192 and 512 px PNGs. It is not part of the version bump.

### Compatibility rules that apply to all of them

From version 1 the app has to survive future updates without breaking data or contracts.

- Migrations are additive, or a rebuild with a literal older-schema test (`SCHEMA_VERSION_n` in `tests/test_database.py`) and a `PRAGMA foreign_key_check` before commit.
- The API keeps its names: new fields are added, existing ones are never renamed or retyped.
- An older database must always open and migrate forward, and the app must still **refuse** a schema newer than itself rather than write to it.
- The package version does not migrate app data — the app migrates its own schema at startup, so `startos/versions/` stays migration-free.
- A downgrade to an older package version is not supported once the schema has moved forward, and that goes in `UPDATING.md`.
- A backup taken on an older version must restore and migrate forward.
- The CSV column names are a contract and do not change without a section saying so.

## Sections 27 and 28 — implemented and verified

What the code does now, and the parts that are easy to get wrong:

- **The acknowledgement stores the key.** `alert_acknowledgements.key_id` is nullable and holds the key the alert belonged to, or `NULL` for a software alert raised by the settings list. An alert with a key is acknowledged and hidden by `(code, key_id)`; an alert without one stays on `(code, source)`. This closed a real bug: a rename — or a `rotate` with `keep_name=false` — used to reopen a closed alert, because `source` carries the name the key has *now*.
- **The contact alert belongs to the checked key.** It gets `key_id` and `source` = `Key N: <name>`, and its message names the key: `The contact details for Key 1: SeedSigner need an external update. Update them in your external documentation, then close this alert.` The severity stays `info` and the action stays `contact_updated`. It blocks its key like every other key alert, because `blocking_alert()` and the `blockingAlerts` filter in the form only look at `key_id`. A record without a key check raises no contact alert at all.
- **`software_incompatible` has two forms.** A software from the settings list keeps `source` = the software name, `key_id` = `None`, actions `[remove_software]`, and carries `software`. A wallet software that is the name of a configured cloud key can never be removed from the settings, so that form belongs to the checked key instead: `key_id` = the checked key, `source` = `Key N: <name>`, actions `[replace_hardware]`, and **no** `software` value, so a settings removal can never close it.
- **`alerts.py` needs the cloud key names.** `build_alerts()` and `collect_alerts()` take `cloud_names=()`, threaded through `rotation_alert_targets()`, `software_alert_targets()`, and the four call sites in `app.py` (`_send_alerts`, `_blocking_alert`, `_rotate_key`, `_close_removed_software`), plus `newest_alert_check_id()`. `app.cloud_key_names(keys)` builds the tuple. If `newest_alert_check_id()` does not get exactly the same names as `collect_alerts()`, the alert's `source` differs, the acknowledgement stores `check_id = None`, `_is_acknowledged()` refuses to hide an alert without a check id, and the alert can never be closed. Keep the default `()` on `build_alerts()`.
- **The closures that belong to a key are shown.** `app.closed_alerts()` and `database._grouped_closures()` both filter on `key_id IS NOT NULL`, so a rotation, a replaced hardware, an updated contact, and an ignored key alert are listed, while `remove_software` and a software-sourced `ignore` are not. `GET /api/health-checks/<id>` returns them as `closed_alerts` (code, source, action, acknowledged_at), and the CSV has one last column, `Follow-up closed`, with `code: action (YYYY-MM-DD)`. A closure hangs on the check it closed, through `check_id`.
- **The key card shows the dates and the note together.** `createKeyCard()` in `static/app.js` always renders `Last checked` / `Next check due`, and adds the alert note on top. It used to replace the dates with the note, which cost the dates for a key whose only alert was the informational contact one.
- **The type is part of a key's identity (section 28).** The setup locks it, the settings never change it, and only a rotation may pick the other one: `POST /api/keys/<id>/rotate` takes an optional `type` (`hardware`/`cloud`), and leaving it out keeps the current type. `save_key_settings(..., key_type=None)` uses `COALESCE(?, type)`, so the settings and a rotation share one statement.
- **A key that becomes a cloud key must not take a taken name.** A cloud key offers its own name as a wallet software choice, and the settings list holds the other choices, so a name the list already holds is refused with `409` through `WalletSoftwareNameInUse` — a `ValidationError` subclass, so it has to be caught before the general `ValidationError` in `_rotate_key`, or the `409` turns into a `400`. `validate_rotation()` therefore takes the wallet software list as a fourth argument.
- **The settings page has two sections:** `01 / Wallet software` and `02 / Key rotation`. The old `01 / Keys` section is gone, because the name now belongs with the rest of the key identity.
- **A rename needs no rotation and no confirmation.** In the rotation section the name can be changed on its own through `POST /api/settings/keys`, for any key, and the address path of a key with **no** saved check can be changed there the same way. Marking a key with `Rotate this key` and ticking the confirmation box (`#rotation-replaced`, "I confirm that each selected key has been replaced by a new key or hardware wallet") sends it through the rotate endpoint instead, together with the type and the new path. The single button is `Save keys`; it reports what was saved, and says so when there is nothing to save.

### Deliberately left out

`remove_software` is still a dead end in two places: a software-sourced `security_vulnerable` offers it next to `ignore` (so the alert stays closable, but one button leads nowhere), and a software-sourced `security_compromised` offers it as its only action, so an alert whose "software" is a cloud key name can never be closed. Neither is fixed, and section 31 does not fix them either.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **A key that could not be checked records nothing else.** That covers `available` = `0` and a recorded address path that does not match. `wallet_software` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED`.
- **`Availability` is required and offers only Yes/No.** A cloud key collects only `Availability`; its compatibility is derived from it, and its own name is the wallet software.
- **A hardware key needs an explicit compatibility status**, and `Hardware works` needs an explicit `Yes` or `No`. A missing value, `""` and `NOT_ASSESSED` are all a `400`.
- **The contact confirmation is required** for every submission, including one for a key that could not be checked, and it has no "not assessed" value.
- **`NOT_ASSESSED` is not offered or accepted anywhere else.** No field but the derived `software_compatibility_status` accepts it.
- **`Address path verified` is never a form field again.** The server derives it from the comparison. The stored column stays, so the history, the export and the alerts keep working.
- **The address path is locked after the first saved check**, and no two keys may share one — in the setup, in the settings or in a rotation.
- **The type is locked by the setup**, and only a rotation may change it. The settings never take a `type`, and a rename alone is not a rotation.
- **An alert is closed by the user, not by a newer check.** A newer check that raises nothing does not clear an older alert, and a key with an open alert cannot get a new check at all.
- **An acknowledgement stores the action name, not a free reason**, and only the actions the endpoint performs are accepted. `rotate` has its own endpoint, because it requires a new address path.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release — with the one amendment section 31 records for the installable PWA.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.
- **`/api/previous-values` still returns a `security` map** that nothing consumes any more, and its `address_path` per key is no longer used by the form, which pre-fills the path from `keys.address_path`. Both are deliberate: removing them would shrink the endpoint, but nothing breaks while they stay.

## Data model (schema version 12)

- `keys`: `key_number` (1–`multisig_key_count`), `name`, `type` (`hardware`/`cloud`), `model`, `address_path`, `created_at`. There is no `device` column. The name is editable in the settings; the type and the address path are the identity of the key, the path must be unique across the rows, and the type only changes through a rotation. `model` is optional documentation and is not locked.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`. The two cloud columns are gone.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- `wallet_software`: `name`, `created_at`. Stored whole, seeded with `Sparrow Wallet` when the list is empty, never emptied through the API.
- `alert_acknowledgements`: `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`. `reason` holds the action name that closed the alert, and `key_id` holds the key the alert belonged to, or `NULL` for a software alert from the settings list.
- `app_settings`: `name` (PRIMARY KEY), `value`. Holds `multisig_threshold`, `multisig_key_count`, `admin_username`, `admin_password_hash` and `session_secret`. Added by section 31 point 7; the credential keys are point 1's.
- `tool_checks` no longer exists.
- Startup migration rebuilds `keys` when it still has `device` or the old `key_number` CHECK, `key_checks` when it uses the old layout or still holds the two cloud columns, and `health_checks` and `key_checks` when their `CHECK` constraints still allow the old values. It then drops `tool_checks` if it is there, and adds the newer columns through `OPTIONAL_COLUMNS`.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5`, `SCHEMA_VERSION_8`, `SCHEMA_VERSION_9`, `SCHEMA_VERSION_10` and `SCHEMA_VERSION_11` as literal older schemas. Copy that pattern for a new migration test: write the old schema, run `initialize_database()`, then assert on the migrated rows.
- There is **no data migration** for an older test database: the user deletes the `data` folder and configures the setup again. An acknowledgement written before version 11 has no key, and the older contact alert used the source `Contact information`, which no longer matches, so the alert it closed is raised again. Section 29 renamed the database file for the same reason, and the old file is discarded with the rest.

## API

Pages: `/`, `/setup`, `/settings`, `/health-check`, `/history`, `/login`. Endpoints: `GET /health`, `GET /api/session`, `POST /api/admin`, `POST /api/login`, `POST /api/logout`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `POST /api/alerts/acknowledge`, `GET /api/export`, `POST /api/health-checks`. Field details are in `docs/application.md`.

The rotate payload is `replaced` + `keep_name` + `name` + `type` + `address_path`, and `type` is optional. `GET /api/health-checks/<id>` also returns `closed_alerts`. The settings page has two sections, and `POST /api/settings/keys` is what a rename alone goes through.

**Section 31 has already added** `threshold` and `key_count` to `POST /api/setup`, `model` to the key payloads, and `address_path` plus the two multisig numbers to `GET /api/key-status`. **Point 1 added** `GET /api/session`, `POST /api/admin`, `POST /api/login` and `POST /api/logout`, the gating of every route except `GET /health` (`401` on the API, a redirect on pages), and the CSRF requirement on every state-changing POST. `GET /health` stays open.

Five things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. That includes `/settings`, `/settings.js`, and everything section 31 still owes: the login page, `session.js`, the manifest, `sw.js` and the PWA icons.
- `/api/setup`, `/api/settings`, `/api/alerts`, `/api/key-status`, `/api/previous-values` and `/api/session` are extra endpoints that are not in the minimum list in section 11.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`. It also includes `ValueError`, so `validate_admin_credentials()` has to be called in its own `try` and mapped to a `400` before the storage handler.
- The settings, rotation and acknowledgement endpoints keep the same error handling as the existing ones: a bad payload is a `400`, an unknown key or alert is a `404`, a locked or duplicate address path is a `409`, and a broken database is a `500`. `DuplicateAddressPath` and `WalletSoftwareNameInUse` must be caught before the general `ValidationError` — in `_save_key_settings` and `_rotate_key` respectively — or the `409` turns into a `400`. A missing or invalid session is a `401`, and a missing CSRF token is a `403`.
- `newest_alert_check_id()` in `app.py` derives the check id for the acknowledgement, the rotation and the software removal, so the same comparison rule is used in all three places. `blocking_alert()` is the module-level helper the `409` is built on, and `_blocking_alert()` reads the key id straight from the payload, so the rule applies before validation.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form field is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderSecurityChecks()` shows an empty note instead of cards when a key could not be checked, why `syncUncheckableState()` clears the flags on the wallet software and the compatibility select — also for a cloud key, whose grid is hidden — and why `syncRequiredFields()` clears the flag on `hardware_works` and `seed_backup_verified`. The rotation fields follow the same rule: the type is `disabled` until the key is marked for rotation, the path is `disabled` when the key has a saved check and is not marked, and the script refuses to send an empty path. The login page sidesteps it with two separate forms, so only the visible one is ever validated.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while `#address-path-warning` is visible, so the browser itself stops the submission and a required control is never hidden.
- **The page heading uses `class="eyebrow"` too.** A regex over `health-check.html` finds `Annual security check` before the numbered sections. `settings.html` starts with `Settings`, then `01 / Wallet software` and `02 / Key rotation`. A test on the section order must expect that first. `tests/test_health_check_form.py` asserts those two lists **exactly**, so a new eyebrow on either page breaks it — the section 29 description line went on the dashboard only.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed, and `static/settings.js` uses double quotes. Assert on the selector text, e.g. `[name=\"address_path\"]`, and on quote-free substrings such as `/api/settings` and `/settings?rotate=`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list and carries `key_id` and `wallet_software`.** A test that needs another provider must replace the entry itself, and the recorded software is `Sparrow Wallet`, which is what a software alert names. A test that exercises the cloud-key form of `software_incompatible` has to pass `cloud_names` to `build_alerts()`.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, they always send `contact_info_verified`, and for a hardware key `hardware_works`. They must send the key's **own** `address_path`, because the server compares it with the stored one. Section 31 added a `model` field to them and a `threshold`/`key_count` pair to the setup fixtures.
- **Every test fixture uses one address path per key** (`ADDRESS_PATH`, `SECOND_ADDRESS_PATH`, `THIRD_ADDRESS_PATH`), because the setup refuses duplicates. `tests/test_app.py` also has `ROTATION_PATHS` and the `rotate()` helper, which picks an unused path per key so a test can rotate several keys in one run.
- **`validate_health_check()` takes a third argument** (the wallet software list), and `validate_rotation()` takes a fourth for the same reason. `tests/test_validation.py` and `tests/test_database.py` wrap the first one in a small `validate()` helper.
- **`tests/test_app.py` has seven test classes.** `ServerTestCase` starts the server and now keeps the session and CSRF cookies a sign-in returns; `AppHandlerTests`, `RenamedSetupTests`, `SettingsApiTests`, `RotationApiTests` and `AcknowledgementApiTests` store the default or renamed setup and call `authenticate()`; `AuthApiTests` starts from a database with **no admin** and covers the gating, the first-run admin, the login and logout, and the CSRF check; and `KeySetupApiTests` creates its admin through `POST /api/admin` and otherwise starts from an empty database. A new test must go in the class whose setup it needs. Every request helper sends the cookies and the CSRF header, and `assert_status()` is the one place an error status is expected.
- **The other server test modules share `tests/server_session.py`.** `test_export_filename.py`, `test_key_model.py`, `test_key_status.py` and `test_multisig_setup.py` mix in `SessionMixin`, which signs in through the API and carries the cookies; each class calls `authenticate()` at the end of its own `setUp`. **A test that switches `DATABASE_PATH` to another file has to call `authenticate()` again**, because the session secret lives in the database, so the old cookie is signed with the wrong secret and every request answers `401`. This cost a full test run once.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19. A legacy record with several `key_checks` is read through its first one when an alert needs the key it belongs to.
- **The database path default is repeated in sixteen places.** `database.py` carries `database_path="data/vardkey.sqlite3"` as the default of every storage function (fifteen of them), and `app.py` carries it in `get_database_path()`. A missed one makes a single code path read or create the other file, silently. Grep for the old name before and after a rename round.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software. A key is identified by its type and its address path, while the name is only a label that the user may change. The address path is unique per key, and a rotation replaces the key with a new one that must carry a new address path and may carry the other type. A rotation creates a new wallet, so the funds have to be moved from the old multisig setup to the new one before the old keys are discarded. An alert is closed by the user with the action that belongs to it, and a key with an open alert cannot be checked until the alert is closed.
