# AI Agent Note — VardKey

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification: §1–§18 are binding and describe the app as
  it is now, §19–§32 are history as one line each, and §32 holds only what is left. The full
  reasoning is in the git history.
- The binding rules live in `TODO.md` and `README.md`. This note does not repeat them — it carries
  the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` and `ai-thought.md` were deleted as outdated. Do not recreate either.

## Status

- **Done and verified:** everything in §1–§32. Schema version **13**. **534 green tests.** The
  StartOS package is built, sideloaded and running on a StartOS 0.4.0 box.
- **The package version is `2026.10.28:0`**, and its git tag is `v2026.10.28_0`.
- **What is left:** nothing. The specification is closed, and a new round starts only when the user
  asks for one.
- **A round stops when it is done.** Do not start the next item unless the user asks.
- **Verified how:** the automated suite, the user's manual browser testing, and the install and test
  round on a StartOS 0.4.0 box. **The user runs the suite; the agent has no shell.**
- **Tests:** `python3 -m unittest discover -s tests`. They run on a Windows copy at
  `C:\Users\<brukarnamn>\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **The version scheme is date based**, `YYYY.MM.DD:revision`, and `UPDATING.md` carries the rule.
  ExVer is **not** SemVer: its numeric portion takes any number of dot-separated components, and it
  **normalizes numeric leading zeros**, so a single-digit month or day must be written without one —
  `2026.1.5`, never `2026.01.05` — or the version string and the tag stop matching. The bump edits
  `version` and `releaseNotes` in `startos/versions/current.ts` **in place**; the file name, the
  `current` export and `startos/versions/index.ts` never change, and `startos/versions/` stays
  otherwise empty because the application migrates its own schema.

## The wallet-secret guard (round 32-B)

`secret_guard.py` is the one place that decides whether a piece of text looks like a wallet secret. It
is local (no network call), silent (the text never reaches a log, a message or an exception) and
narrow (it matches only the shapes that are unmistakable, so an ordinary note is not refused).

- **What it recognises:** a PEM private-key block; an extended private key with any SLIP-132 prefix
  (`xprv`, `yprv`, `zprv`, `tprv`, `uprv`, `vprv`) at 100 base58 characters or more; a WIF key (51 or
  52 base58 characters starting `5`, `9`, `K`, `L` or `c`); a BIP38 key (`6P`, 58 characters); and a
  run of 12 or more consecutive BIP39 words, also in the middle of a sentence. It returns a short
  English label such as `"a seed phrase"`, never the value, and `rejection_message(field, label)`
  never repeats it either.
- **The wordlist is embedded**, 2048 words, from `bitcoin/bips` `bip-0039/english.txt`.
  `tests/test_secret_guard.py` checks it: 2048 words, alphabetical, 3–8 lower-case letters, and no
  two words sharing their first four letters. That last check is the strong one. Do not edit the list
  without that test.
- **Where it is wired in:** `validation.py` calls `_reject_secret()` from the four text helpers
  `_text`, `_key_name`, `_model` and `_required_path`, so every free-text field is covered by
  construction. `auth.py` checks the admin username the same way; the password is deliberately not
  checked, because a long passphrase is a legitimate password.
- **The refusal is a `ValidationError`** (`SecretDetected`), so the existing handlers answer `400`.
  `app.py` needed no change at all — do not add a handler for this. A plain `ValueError` would have
  been caught by `STORAGE_ERRORS` and answered `500`.
- **The guard runs before the field's length limit.** A seed phrase pasted into a 60-character label
  field is answered with "looks like a seed phrase", not with "too long". **This order is deliberate
  and pinned by tests; do not swap it back.**
- **The reminder in the UI is one line, in the key setup** — a single `p.secret-warning` above the
  whole key list in `static/setup.html`, and nowhere else. The page notice is a different thing and
  stays on `health-check.html`, `setup.html` and `settings.html`. The server side is unchanged.
- **The limitations are documented in the module docstring and are not to be played down:** a bare
  64-character hex string is not refused (it is indistinguishable from a transaction id); only the
  English wordlist is used; a secret split across several fields, or in a shape outside the patterns,
  is not caught; and a false positive is possible for a note that happens to be twelve or more BIP39
  words in a row.

## Alerts, closures and key identity — the parts that are easy to get wrong

The rules are in `TODO.md` §7; these are the traps that have already cost time.

- **The acknowledgement stores the key.** `alert_acknowledgements.key_id` is nullable and holds the
  key the alert belonged to, or `NULL` for a software alert raised by the settings list. An alert with
  a key is acknowledged and hidden by `(code, key_id)`; an alert without one stays on
  `(code, source)`. This closed a real bug: a rename — or a `rotate` with `keep_name=false` — used to
  reopen a closed alert, because `source` carries the name the key has *now*.
- **A key-sourced security alert carries `Key N: <name>`, and the row decides.** `build_alerts()`
  reads the key checks into a lookup by key id, and `_security_alerts()` looks the row's own `key_id`
  up in it. When the row carries the checked key, the key is the source and the alert belongs to it,
  so it is closed by a rotation; otherwise the source is the plain software name and it is closed by
  removing that software from the settings. **The provider name is never compared with the names that
  are configured now**, so a rename or a rotation cannot turn a key alert into a software one.
  `rotation_alert_targets()`, `software_alert_targets()` and `newest_alert_check_id()` all read the
  same `build_alerts()`, so they see the same source, which is what keeps an alert closable.
- **The contact alert belongs to the checked key.** It gets `key_id` and `source` = `Key N: <name>`,
  and its message says "this key". The severity stays `info` and the action stays `contact_updated`.
  It blocks its key like every other key alert, because `blocking_alert()` and the `blockingAlerts`
  filter in the form only look at `key_id`.
- **`software_incompatible` has two forms.** A software from the settings list keeps `source` = the
  software name, `key_id` = `None`, actions `[remove_software]`, and carries `software`. A wallet
  software that is the name of a configured cloud key can never be removed from the settings, so that
  form belongs to the checked key instead: `key_id` = the checked key, `source` = `Key N: <name>`,
  actions `[replace_hardware]`, and **no** `software` value, so a settings removal can never close it.
  Only that form names the software in its message, because its source is the key.
- **`alerts.py` still needs the cloud key names, but only for `software_incompatible`.**
  `build_alerts()` and `collect_alerts()` take `cloud_names=()`, threaded through
  `rotation_alert_targets()`, `software_alert_targets()`, and the four call sites in `app.py`
  (`_send_alerts`, `_blocking_alert`, `_rotate_key`, `_close_removed_software`), plus
  `newest_alert_check_id()`. `app.cloud_key_names(keys)` builds the tuple. If
  `newest_alert_check_id()` does not get exactly the same names as `collect_alerts()`, the alert's
  `source` differs, the acknowledgement stores `check_id = None`, `_is_acknowledged()` refuses to hide
  an alert without a check id, and the alert can never be closed. Keep the default `()` on
  `build_alerts()`. `_send_health_check_list()` passes the same tuple for its `needs_follow_up` and
  `follow_up_open` fields.
- **Every closure of a check is shown, key-sourced or not.** `app.closed_alerts()` and
  `database._grouped_closures()` list every acknowledgement that carries a `check_id`, so a rotation,
  a replaced hardware, an updated contact, an ignored key alert, and a software alert closed by
  removing it are all shown. `GET /api/health-checks/<id>` returns them as `closed_alerts`, and the CSV
  has one last column, `Follow-up closed`, hanging on the check it closed through `check_id`. **A
  closure carries its source**, because the two forms of a security code are otherwise
  indistinguishable: the CSV writes `<source> — <code>: <action> (YYYY-MM-DD)` into that cell, and the
  history table shows `Source`, `Alert`, `Action` and `Closed`. The CSV column names and the column
  order are unchanged — only the value grew.
- **The key card shows the next due date with the alert note.** `createKeyCard()` in `static/app.js`
  always renders `Next check due` and adds the alert note on top. The note comes in addition to the
  date, never instead of it.
- **The type is part of a key's identity.** The setup locks it, the settings never change it, and only
  a rotation may pick the other one: `POST /api/keys/<id>/rotate` takes an optional `type`, and
  leaving it out keeps the current type. Since schema 13 a rotation does **not** write the key row: it
  inserts a new row and retires the old one.
- **A key that becomes a cloud key must not take a taken name.** A cloud key offers its own name as a
  wallet software choice, so a name the list already holds is refused with `409` through
  `WalletSoftwareNameInUse` — a `ValidationError` subclass, so it has to be caught before the general
  `ValidationError` in `_rotate_key`, or the `409` turns into a `400`. `validate_rotation()` therefore
  takes the wallet software list as a fourth argument.
- **A rename needs no rotation and no confirmation.** In the rotation section the name can be changed
  on its own through `POST /api/settings/keys`, for any key, and the address path of a key with **no**
  saved check can be changed there the same way. The single button is `Save keys`.

### Deliberately left out

`remove_software` is still a dead end in two places: a software-sourced `security_vulnerable` offers it
next to `ignore` (so the alert stays closable, but one button leads nowhere), and a software-sourced
`security_compromised` offers it as its only action, so an alert whose "software" is a cloud key name
can never be closed. Neither is fixed.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its
  own date plus one calendar year, computed on the server and not editable in the form.
- **A key that could not be checked records nothing else.** That covers `available` = `0` and a
  recorded address path that does not match. `wallet_software` and `ai_security_checks` must be empty;
  a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and
  `software_compatibility_status` becomes `NOT_ASSESSED`.
- **`Availability` is required and offers only Yes/No.** A cloud key collects only `Availability`; its
  compatibility is derived from it, and its own name is the wallet software.
- **A hardware key needs an explicit compatibility status**, and `Hardware works` needs an explicit
  `Yes` or `No`. A missing value, `""` and `NOT_ASSESSED` are all a `400`.
- **The contact confirmation is required** for every submission, including one for a key that could
  not be checked, and it has no "not assessed" value.
- **`NOT_ASSESSED` is not offered or accepted anywhere else.**
- **`Address path verified` is never a form field again.** The server derives it from the comparison.
- **The address path is locked after the first saved check**, and no two keys may share one — in the
  setup, in the settings or in a rotation. The comparison is canonical: `m/48h/0h/0h/2h` and
  `m/48'/0'/0'/2'` are the same path, and the stored spelling is never rewritten.
- **The type is locked by the setup**, and only a rotation may change it. A rename alone is not a
  rotation.
- **An alert is closed by the user, not by a newer check.** A newer check that raises nothing does not
  clear an older alert, and a key with an open alert cannot get a new check at all.
- **An acknowledgement stores the action name, not a free reason.** `rotate` has its own endpoint,
  because it requires a new address path.
- **Every alert message says what is wrong, which key or software, and what closes it**, and it does
  not repeat the name in `source` — except the cloud-key form of `software_incompatible`. See §7.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel
  compatibility. The column names and the column order are an agreement; do not change them. A text
  cell that a spreadsheet would read as a formula is neutralized with a leading apostrophe, and that
  is the only change a cell may receive.
- **The PWA cache stores only a valid shell answer.** `isCacheable()` in `static/sw.js` requires
  `response.ok`, `response.type === "basic"` and `!response.redirected`. The allow-list is the other
  half: the worker never names `/api/*`, `/health`, `/login` or `/robots.txt`.
- **No page is meant to be crawled.** All six pages carry `<meta name="robots" content="noindex,
  nofollow">` in `<head>`, `_send_security_headers()` in `app.py` adds `X-Robots-Tag: noindex,
  nofollow`, and `static/robots.txt` answers `Disallow: /`. `static/robots.txt` must **not** be added
  to the service worker's shell list.
- **The navigation lives in the top bar, not on the page.** `static/session.js` builds the menu, the
  panel and the `.topbar-actions` wrapper on the five application pages; `/login` has none. The
  dashboard markup carries no `href` for `/health-check`, `/settings`, `/history` or `/api/export`,
  and the export link and its note are on the history page. The page the user is already on is a
  `<span>` with `aria-current="page"`, not a link.
- **The Attention card is the only summary card.** Its detail line carries the overdue list when
  something is overdue and the earliest due date otherwise; `.overview-grid` is one column at every
  width.
- **An empty alert list renders nothing.** The count beside the heading says `No alerts`.
- **The three summary fields are additive and mean what they say.** `key_names` follows `key_numbers`
  and carries the name the check was recorded with, read from the snapshot on the check.
  `needs_follow_up` is a property of the **saved** check, so it does not change when an alert is closed
  or a key is renamed; do not "fix" it to follow `collect_alerts()`, which hides acknowledged alerts
  and would rewrite history. `follow_up_open` is the **current** state, computed from the merged,
  unacknowledged alerts the dashboard shows, so an alert that a newer check re-raises belongs to the
  newer check and the older check reads as closed. The history card reads its three states (`All OK`,
  `Needs follow-up`, `Follow-up closed`) from these two fields.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing
  prohibitions, to be re-confirmed before release — with the one amendment for the installable PWA.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of
  the current date.
- **`/api/previous-values` still returns a `security` map** that nothing consumes any more, and its
  `address_path` per key is no longer used by the form, which pre-fills the path from
  `keys.address_path`. Both are deliberate.
- **`delete_all_data()` deletes the checks before the keys.** `key_checks.key_id` is
  `ON DELETE RESTRICT`, so the other order fails. The acknowledgements are deleted explicitly, because
  they have no foreign key at all. The delete has to clear every row of `keys`, active and retired
  alike.

## Data model (schema version 13)

- `keys`: `key_number` (1–`multisig_key_count`), `name`, `type` (`hardware`/`cloud`), `model`,
  `address_path`, `active`, `rotated_at`, `created_at`. There is no `device` column. The name is
  editable in the settings; the type and the address path are the identity of the key, the path must be
  unique across the **active** rows, and the type only changes through a rotation. `model` is optional
  documentation and is not locked.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`,
  `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the
  legacy `sparrow_version` / `nunchuk_version`.
- `key_checks`: one row per submission — `key_id`, `key_name`, `key_type`, `key_model`, `available`,
  `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`,
  `address_path`, `comments`. The three snapshot columns are a frozen copy of the key the check was
  recorded for.
- `ai_security_checks`: `provider` (free text), `key_id` (nullable), `status`, `comments`, with
  `UNIQUE (health_check_id, provider)`.
- `wallet_software`: `name`, `created_at`. Seeded with `DEFAULT_WALLET_SOFTWARE` (`Sparrow Wallet`)
  when the list is empty, never emptied through the API.
- `alert_acknowledgements`: `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`.
- `app_settings`: `name` (PRIMARY KEY), `value`. Holds `multisig_threshold`, `multisig_key_count`,
  `admin_username`, `admin_password_hash`, `session_secret`, `failed_login_count` and
  `failed_login_until`.
- `tool_checks` no longer exists.
- Startup migration rebuilds `keys` when it still has `device`, the old `key_number` CHECK, or no
  `active` flag; `key_checks` when it uses the old layout or still holds the two cloud columns; and
  `health_checks` when its `CHECK` constraints still allow the old values. It then drops `tool_checks`
  if it is there, adds the newer columns through `OPTIONAL_COLUMNS`, backfills the snapshot on every
  check from the key it belongs to, and creates the partial unique index over the active row. The
  `UNIQUE` on `keys.key_number` is now a partial unique index over the active row
  (`idx_keys_active_key_number … WHERE active = 1`).
- The table definitions are `{table}` templates, so a rebuild can create the same table under a
  temporary name. `health_checks` is a parent table, so the whole migration runs with
  `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on
  any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5`, `SCHEMA_VERSION_8`,
  `SCHEMA_VERSION_9`, `SCHEMA_VERSION_10`, `SCHEMA_VERSION_11` and `SCHEMA_VERSION_12` as literal
  older schemas. Copy that pattern for a new migration test: write the old schema, run
  `initialize_database()`, then assert on the migrated rows.
- There is **no data migration** for an older test database: the user deletes the `data` folder and
  configures the setup again. An acknowledgement written before version 11 has no key, and the older
  contact alert used the source `Contact information`, which no longer matches, so the alert it closed
  is raised again.

## API

Pages: `/`, `/setup`, `/settings`, `/health-check`, `/history`, `/login`. Endpoints: `GET /health`,
`GET /api/session`, `POST /api/admin`, `POST /api/login`, `POST /api/logout`, `GET /api/setup`,
`POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`,
`GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`,
`POST /api/keys/<id>/rotate`, `GET /api/health-checks`, `GET /api/health-checks/<id>`,
`GET /api/alerts`, `POST /api/alerts/acknowledge`, `GET /api/export`, `POST /api/health-checks`.
Field details are in `docs/application.md`, which is now in step with the code.

`GET /api/health-checks` carries `key_names`, `needs_follow_up` and `follow_up_open`.
`GET /api/health-checks/<id>` carries `closed_alerts` and `model` on each key check.

Maintenance commands, run inside the container by the StartOS actions and usable by hand:
`maintenance.py delete-all-data` and `maintenance.py set-admin-password`. Neither is an HTTP endpoint.

Five things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. That includes
  `/settings`, `/settings.js`, `/login`, `/login.js`, `/session.js`, `/sw.js`,
  `/manifest.webmanifest`, `/icon.svg`, the two raster icons `/icon-192.png` and `/icon-512.png`, and
  `/robots.txt`, which is `text/plain; charset=utf-8` and is deliberately absent from the service
  worker's shell list.
- `/api/setup`, `/api/settings`, `/api/alerts`, `/api/key-status`, `/api/previous-values` and
  `/api/session` are extra endpoints that are not in the minimum list in section 11.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial
  setup. Keep it there, or a broken database answers with a traceback instead of a `500`. It also
  includes `ValueError`, so `validate_admin_credentials()` has to be called in its own `try` and
  mapped to a `400` before the storage handler — and it is why a refused secret has to be a
  `ValidationError` rather than a bare `ValueError`.
- The settings, rotation and acknowledgement endpoints keep the same error handling as the existing
  ones: a bad payload is a `400`, an unknown key or alert is a `404`, a locked or duplicate address
  path is a `409`, and a broken database is a `500`. `DuplicateAddressPath` and
  `WalletSoftwareNameInUse` must be caught before the general `ValidationError` — in
  `_save_key_settings` and `_rotate_key` respectively — or the `409` turns into a `400`. A missing or
  invalid session is a `401`, a missing CSRF token is a `403`, and a locked login is a `429`.
- `newest_alert_check_id()` in `app.py` derives the check id for the acknowledgement, the rotation and
  the software removal, so the same comparison rule is used in all three places. `blocking_alert()` is
  the module-level helper the `409` is built on, and `_blocking_alert()` reads the key id straight
  from the payload, so the rule applies before validation.

The rotate payload is `replaced` + `keep_name` + `name` + `type` + `address_path`, and `type` is
optional. A rotation inserts a new row and retires the old one, and the acknowledgements are written
against the **old** key id. The `#history-detail` anchor and the `?id=` query on `/history` are
client-side only: they never reach the server, so no route changed for them.

## The StartOS package — the parts that bite

The package is one service: one daemon, one container, one SQLite database on the persistent `main`
volume, mounted at `/data`. No Postgres, no Redis, no external backend, no extra container.

- **The application and the package share one repository, at the root.** A deliberate deviation from
  the guide's "a package repo is not a fork of the application": the rule assumes a published upstream
  image or a git submodule, and VardKey has neither. `AGENTS.md` states the deviation so nobody adds
  an `upstream-project/` submodule to "fix" it.
- **Anything the `Dockerfile` does not `COPY` is not in the image.** The modules go in with
  `COPY *.py ./` and the assets with `COPY static ./static`; `.dockerignore` keeps `tests`, `data`,
  `node_modules`, `javascript` and the build output out of the context. `static/` must be copied:
  `app.py` answers `/health` from code, but every page is read from `ROOT/static`, so an image without
  it reports a healthy service whose whole UI answers `404`.
- **Three things must agree.** `startos/utils.ts` holds `uiPort` (8080); `startos/main.ts` passes it as
  `PORT` and uses it in the readiness URL; `startos/interfaces.ts` binds it. The readiness check is
  `checkWebUrl` against `http://127.0.0.1:8080/health`, and `/health` must stay open. A red
  `ECONNREFUSED 127.0.0.1:8080` blip before `VardKey listening on port 8080` is just the first poll
  landing before Python has bound the socket; nothing to fix.
- **Two actions**, registered through `Actions.of()` in `startos/actions/index.ts`, with their strings
  in `startos/i18n/dictionaries/`: `deleteAllData.ts` (`delete-all-data`) and `setAdminPassword.ts`
  (`set-admin-password`). Both run `maintenance.py` in a `withTemp` subcontainer, behind a confirmation
  the handler enforces. The generated password never travels into the container: `maintenance.py`
  generates it there and prints it.
- **The admin task** from §32.8 lives in `startos/init/requireAdmin.ts` and keeps the same property: no
  password travels from the host into the container. It raises and clears the task itself, because SDK
  3.0.4 has no condition for "the admin password is unset", and the probe fails open. **On the box the
  task is raised and shows on Tasks as *recommended*, and it does not hold the service back** — the
  user can start the app without an admin. `README.md` documents that behaviour.
- **Backups.** `startos/backups.ts` is `sdk.Backups.ofVolumes('main')`. StartOS stops the service for
  the duration of a backup, so the database file is quiescent while it is copied — no snapshot hook is
  needed.
- **No CI.** The guide assumes GitHub Actions; this repository is on Gitea, so there are no
  `.github/workflows/` and there must not be any. The `.s9pk` is built locally with `make`.
- **The skeleton** was written to match the Start9 template rather than generated by
  `s9pk init-workspace`, because that command was not available where it was written. The successful
  build and install confirm they are equivalent; `@start9labs/start-sdk` is pinned to `3.0.4`.
  `node_modules/` is not in the repository.
- **The root `icon.svg` is the package artwork**, read from the repository root by the build. It is the
  same retro drawing as `static/icon.svg`, and it must stay under 40 KiB.
- **Documentation layout.** `README.md` is the StartOS package README, with the guide's fixed heading
  set. The application's own reference is `docs/application.md`, which `instructions.md` links to.
  `AGENTS.md` is the repo-specific agent context, and `CLAUDE.md` is the one-line `@AGENTS.md` import.
  All of them, plus `UPDATING.md` and the package i18n strings, were brought in step with the code in
  §32.6; keep them there. The repository is `https://gitea.sondreolav.com/ai-bot/vardkey`, and the old
  `helsesjekk` name must not come back in a URL.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the
  transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with
  `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in
  `tests/test_database.py`.
- **A module the image is missing is a runtime error, not a build error.** `auth.py` was once left out
  of the `Dockerfile`, and both `app.py` and `maintenance.py` then died with `ModuleNotFoundError`
  inside the container while every test stayed green. The `COPY *.py ./` line is what stops that
  recurring. `secret_guard.py` is covered by the same line.
- **Every server test module needs a session, and a redirect makes a missing one look like a pass.** A
  page fetched without a session answers `302 → /login`, and `urllib` follows it, so an assertion on
  page markup reads the login page's HTML instead of failing with `401`. Use
  `tests/server_session.py`'s `SessionMixin`. The manifest, the icons and `/robots.txt` are open while
  the pages are not.
- **`urlopen` raises `HTTPError` on a 4xx.** A test that expects a `400` has to catch it and read the
  body from the exception; `tests/test_secret_guard.py`'s `post_status()` helper is the pattern. A
  `429` is read the same way.
- **A field has a length limit, and the guard runs before it.** Use a WIF key (52 characters) or a
  BIP38 key (58) when a test needs a secret that *fits* a short field, and the seed phrase where the
  field has room.
- **A `required` control inside a `display:none` container still blocks submission.** Hiding a section
  is not enough: the required flags must be cleared. That is why `renderSecurityChecks()` shows an
  empty note instead of cards when a key could not be checked, why `syncUncheckableState()` clears the
  flags on the wallet software and the compatibility select, and why `syncRequiredFields()` clears the
  flag on `hardware_works` and `seed_backup_verified`. The rotation fields follow the same rule: the
  type is `disabled` until the key is marked for rotation, the path is `disabled` when the key has a
  saved check and is not marked, and the script refuses to send an empty path. The login page sidesteps
  it with two separate forms.
- **A hidden element has no box, so an anchor cannot jump to it.** `#history-detail` is hidden until a
  check is opened, so `revealDetail()` in `history.js` unhides the section first and only then calls
  `scrollIntoView()`. Do not reorder those two lines.
- **A bare substring assertion over page markup also catches comments.** Assert on the element, not on
  the phrase.
- **A `display: grid` panel ignores the `hidden` attribute.** `.menu-panel[hidden] { display: none; }`
  is in the sheet for that reason, the same way `.form-stack[hidden]`, `.field-grid[hidden]` and
  `.form-section[hidden]` already were.
- **The menu's outside-click listener has to allow the button's own click.** The button's handler runs
  first and toggles the panel; the document listener then sees a target inside `.menu` and does
  nothing.
- **The current-page check compares a normalised path, and the current item is a span.**
  `currentPath()` strips trailing slashes and keeps the root as `/`. The match is rendered as a
  `<span class="menu-item menu-item-current">` with `aria-current="page"`, never an `<a>`.
- **A sticky top bar needs a scroll container that is the viewport.** `.topbar` is a flex child of
  `body`, and `body` sets no `overflow`, so `position: sticky; top: 0` works — but it stops working the
  moment an ancestor gets `overflow: hidden` or `auto`. The menu panel is `position: absolute` inside
  the bar, so it travels with it.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while
  `#address-path-warning` is visible, so the browser itself stops the submission.
- **The per-field secret reminder is gone; only the setup keeps one.** A test asserts `setup.html`
  holds exactly one `class="secret-warning"` and that the check form and the settings hold none.
- **`static/health-check.js` must not use `placeholder` anywhere.** A test asserts the string is
  absent, because a previous value is a real input value.
- **The key card's line order is pinned by two test modules.** `tests/test_key_status.py` asserts
  `card.append(top, name)` → `card.append(model)` → `card.append(path)`, and
  `tests/test_health_check_form.py` asserts the top line, that `card.append(type)` is gone, and that
  the model line is skipped by `sameLabel(entry.model, entry.name)`.
- **The dashboard heading is dynamic and the static description is gone.** `tests/test_app.py` asserts
  `id="setup-shape"` and the fallback text on the dashboard, while `tests/test_pwa.py` still asserts
  the manifest description. Do not move the one into the other.
- **The stylesheet test asserts on the shape of the theme, not on its wording.** It checks the two
  bevel colour pairs, the dotted focus outline, the font stack, the absence of `box-shadow` and
  `gradient`, and that every `border-radius` in the sheet is `0`.
- **The brand mark is an image, and the class name is pinned.** `IconTests` in `tests/test_pwa.py`
  asserts that all six pages carry `<img class="brand-mark" src="/icon.svg" alt="" aria-hidden="true">`,
  that the sheet holds `image-rendering: pixelated`, and that `place-items: center` appears nowhere. It
  also pins `min-height: 100vh`, `min-height: 100dvh`, `flex-direction: column` and the exact string
  `main { flex: 1 1 auto; }`. Do not style the brand mark as a letter again.
- **The two SVG files must keep the same drawing.** The package icon at the repository root is the
  source of truth, and `test_the_served_icon_carries_the_same_drawing_as_the_package_icon` compares
  them from `<svg>` onwards. A change to one drawing has to be made in both.
- **The two PNGs are real files, rasterized by the user**, because the agent has no rasterizer.
  `IconTests` reads each file's IHDR and asserts 192×192 and 512×512.
- **The manifest lists the SVG first, and the two PNGs after it.** `test_the_manifest_lists_the_served_icon`
  reads `icons[0]`. The PNG entries must carry the real size (`192x192` and `512x512`) and
  `type: "image/png"`.
- **The favicon link sits next to the manifest link, and `/login` has no manifest.** `IconTests`
  asserts the exact string `<link rel="icon" type="image/svg+xml" href="/icon.svg">` on all six pages.
- **The prettier config is the SDK's own, and `make x86` does not run the check.** `.prettierrc` is the
  single line `"@start9labs/start-sdk/prettier.config.json"`, which is
  `{ trailingComma: "all", tabWidth: 2, semi: false, singleQuote: true }` — everything else is
  prettier's default, so `printWidth` is 80 and `quoteProps` is `"as-needed"`. The SDK makefile
  defines the check as `FORMAT_CHECK`, but `make x86` packs without it, so write the TypeScript the way
  prettier would **and** run
  `npx prettier --config node_modules/@start9labs/start-sdk/prettier.config.json --check startos`
  before you hand the round back; `--write` fixes the files.
  In `startos/manifest/i18n.ts` a value that does not fit the line breaks after the colon, and a
  string with an apostrophe uses double quotes. **A property is measured together with its trailing
  comma**, so the limit is `printWidth − indent` — 78 columns for a top-level property, not 80.
  `es_ES` at 79 columns must break; `en_US` at 74 and `pl_PL` at 76 stay inline.
- **The page heading uses `class="eyebrow"` too.** `tests/test_health_check_form.py` asserts the
  eyebrow lists of `health-check.html` and `settings.html` **exactly**, so a new eyebrow breaks it, and
  so does a removed one. The secret warnings deliberately use `class="secret-warning"`, not an eyebrow.
- **A static help line that the script overwrites is dead text.** `#software-help` in
  `health-check.html` is empty, because `lockSoftwareFields()` fills it before the user can read it. A
  test pins both halves: the empty element in the markup and `softwareHelp.textContent` in the script.
- **`aria-labelledby` may point at the eyebrow.** `login.html`'s first form has no `h2`; its
  `aria-labelledby="login-form-title"` points at the eyebrow `<p>` that carries the same `id`.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes
  for constant selectors and template literals where a `${...}` substitution is needed, and
  `static/settings.js` uses double quotes. Assert on the selector text and on quote-free substrings.
- **A test string that spans a line break needs the escape, not a literal backslash.** Two assertions
  in `tests/test_health_check_form.py` once carried `\\n` where the script has a real newline, so they
  looked for a backslash and a letter and failed. Prefer an assertion that names the two halves on
  either side of the break, or normalise with `" ".join(script.split())`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list and carries the key on the
  security rows.** Each `ai_security_checks` entry is a dict with `provider`, `key_id` and `status`: the
  entry whose provider is the key's own name carries the key number, and the others carry `None`. The
  alert texts are asserted there, and **not** in `tests/test_app.py`, which checks the code, the
  severity, the source, the actions and the `key_id` only.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`,
  `tests/test_database.py`, `tests/test_app.py`, `tests/test_maintenance.py` and
  `tests/test_secret_guard.py`.** They must send the key's **own** `address_path`, because the server
  compares it with the stored one.
- **Every test fixture uses one address path per key** (`ADDRESS_PATH`, `SECOND_ADDRESS_PATH`,
  `THIRD_ADDRESS_PATH`). `tests/test_app.py` also has `ROTATION_PATHS` and the `rotate()` helper. With
  schema 13 a rotation retires the key row, so a test that rotates and then records a check has to use
  the **new** key id — `rotate()` hands it back under `key_id`.
- **`validate_health_check()` takes a third argument** (the wallet software list), and
  `validate_rotation()` takes a fourth for the same reason.
- **`tests/test_app.py` has seven test classes.** A new test must go in the class whose setup it needs:
  `ServerTestCase`, `AppHandlerTests`, `RenamedSetupTests`, `SettingsApiTests`, `RotationApiTests`,
  `AcknowledgementApiTests`, `AuthApiTests` and `KeySetupApiTests`. Every request helper sends the
  cookies and the CSRF header, and `assert_status()` is the one place an error status is expected.
- **The other server test modules share `tests/server_session.py`.** `test_export_filename.py`,
  `test_key_model.py`, `test_key_status.py`, `test_multisig_setup.py`, `test_pwa.py` and
  `test_secret_guard.py` mix in `SessionMixin`, which signs in through the API; each class calls
  `authenticate()` at the end of its own `setUp`. **A test that switches `DATABASE_PATH` to another
  file has to call `authenticate()` again**, because the session secret lives in the database.
- **A login lockout test has to clear the counter.** `AuthApiTests` shares one database per test, and
  the lockout lives in `app_settings`, so a test that trips it leaves the account locked for the tests
  that follow unless it resets the two rows or uses its own database file.
- **The export link and its note live on the history page, and four tests moved with them.**
  `tests/test_export_filename.py` asserts the dashboard has no `/api/export` link;
  `tests/test_app.py`'s `test_the_dashboard_carries_no_navigation_link_of_its_own`;
  `test_the_history_page_offers_the_export_in_its_own_section` in `tests/test_health_check_form.py`
  pins the `Export` section, the title bar, the note under the button and the absent
  `.page-heading > .secondary-button` rule; and `test_the_history_links_to_the_detail_section` pins
  both anchors.
- **`#key-count` still exists in `setup.html`, but not on the dashboard.** The two are on different
  pages and were never the same element, so assert per file.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three
  keys only for rows saved before section 19.
- **The database path default is repeated in sixteen places.** `database.py` carries
  `database_path="data/vardkey.sqlite3"` as the default of every storage function (fifteen of them),
  and `app.py` carries it in `get_database_path()`. A missed one makes a single code path read or
  create the other file, silently.

## Tooling — what the agent can and cannot do

- The Gitea tools write a **whole file** at a time (`gitea_update_file`, auto-SHA, one file per call),
  and there is no preview step and no shell. There is no branch delete either.
- The agent therefore **cannot** run the suite, `make x86`, `tsc --noEmit` or `prettier --check`. The
  user runs them, and the user is the one who rasterizes an image or deletes a branch by hand.
- Keep the documents short. `TODO.md` and this note are read by every future model, and their size is
  context the next round cannot spend.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software
choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as
its software. A key is identified by its type and its address path, while the name is only a label
that the user may change. The address path is unique per key, and a rotation replaces the key with a
new one that must carry a new address path and may carry the other type. A rotation creates a new
wallet, so the funds have to be moved from the old multisig setup to the new one before the old keys
are discarded. An alert is closed by the user with the action that belongs to it, and a key with an
open alert cannot be checked until the alert is closed. **Since §32.8 point 5, a rotation also retires
the old key row**: the multisig slot number stays, the old checks keep the name and type they were
recorded with, and the new row starts with an empty history.
