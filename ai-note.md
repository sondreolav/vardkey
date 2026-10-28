# AI agent note — VardKey

Short working handover for the next model. Keep it short.

- **`docs/spec.md` is the specification** (English). §1–§18 are binding and describe the app as it is
  now, §19–§33 are history as one line per round, and §32 holds nothing. **The section numbers are
  stable** — the code, the tests and the documents cite them — so a section is never renumbered and
  never reused.
- The full reasoning for every round is in the git history, as are the earlier Norwegian revision of
  the specification and the deleted bug report. Do not recreate either file.
- This note carries only what the spec does not: the status, the way to work in this repository, and
  the traps that have already cost time. Do not repeat the spec here.

## Status

- **Done and verified:** everything in §1–§33. Schema version **13**. **534 green tests.** The
  StartOS package is built, sideloaded and running on a StartOS 0.4.0 box.
- **The package version is `2026.10.28:0`**, tag `v2026.10.28_0`. The version scheme is date based,
  `YYYY.MM.DD:revision`; `UPDATING.md` carries the rule.
- **What is left:** nothing in the spec. Two things only the user can close are listed at the top of
  `docs/spec.md`: the box and backup tests have to be re-run before the first release, and the
  prohibition lists are re-confirmed before release.
- **A round stops when it is done.** Do not start the next item unless the user asks.
- **Verified how:** the automated suite, the user's manual browser testing, and the install and test
  round on a StartOS 0.4.0 box. **The user runs the suite; the agent has no shell.**
- **Tests:** `python3 -m unittest discover -s tests`. They run on a Windows copy at
  `C:\Users\<brukarnamn>\Downloads\vardkey`, so they must pass there as well as on Linux.

## Working in this repository

- The Gitea tools write a **whole file** at a time (`gitea_update_file`, auto-SHA, one file per call),
  and there is no preview step and no shell. There is no branch delete either.
- The agent therefore **cannot** run the suite, `make x86`, `tsc --noEmit` or `prettier --check`. The
  user runs them, and the user is the one who rasterizes an image or deletes a branch by hand.
- Keep the documents short. `docs/spec.md` and this note are read by every future model, and their
  size is context the next round cannot spend.

## The wallet-secret guard

`secret_guard.py` is the one place that decides whether a piece of text looks like a wallet secret. It
is local (no network call), silent (the text never reaches a log, a message or an exception) and
narrow (it matches only unmistakable shapes, so an ordinary note is not refused). It recognises a PEM
private-key block; an extended private key with any SLIP-132 prefix (`xprv`, `yprv`, `zprv`, `tprv`,
`uprv`, `vprv`) at 100 base58 characters or more; a WIF key; a BIP38 key; and a run of twelve or more
consecutive BIP39 words. It returns a short English label such as `"a seed phrase"`, never the value.

- **The embedded wordlist is pinned by the suite** — 2048 words, alphabetical, 3–8 lower-case
  letters, and no two words sharing their first four letters. That last check is the strong one. Do
  not edit the list without that test.
- **The refusal must stay a `ValidationError`** (`SecretDetected`), so the existing handlers answer
  `400`. `app.py` needs no handler for it. A plain `ValueError` would be caught by `STORAGE_ERRORS`
  and answered `500`.
- **The guard runs before the field's length limit.** A seed phrase pasted into a 60-character label
  is answered with "looks like a seed phrase", not with "too long". **This order is deliberate and
  pinned by tests; do not swap it back.**
- **The UI reminder is one line, in the key setup**, and nowhere else; the page notice is a different
  thing. A test pins exactly one `class="secret-warning"` in `setup.html` and none in the other two
  pages.
- **The limitations are in the module docstring and are not to be played down:** a bare 64-character
  hex string is not refused (it is indistinguishable from a transaction id); only the English
  wordlist is used; a secret split across several fields, or in a shape outside the patterns, is not
  caught; and a note that happens to be twelve or more BIP39 words in a row is a false positive.

## Alerts and key identity — the parts that are easy to get wrong

The rules are in `docs/spec.md` §7; these are the mechanisms that have already cost time.

- **The acknowledgement stores the key.** `alert_acknowledgements.key_id` is nullable and holds the
  key the alert belonged to, or `NULL` for a software alert raised by the settings list. An alert with
  a key is hidden by `(code, key_id)`; one without a key stays on `(code, source)`. This closed a real
  bug: a rename used to reopen a closed alert, because `source` carries the name the key has *now*.
- **The row in `ai_security_checks` decides the source, never the configured names.**
  `_security_alerts()` looks the row's own `key_id` up in a lookup built by `build_alerts()`, so a
  rename or a rotation cannot turn a key alert into a software one.
- **`build_alerts()` and `collect_alerts()` take `cloud_names=()`, and every caller must pass the same
  tuple.** It is threaded through `rotation_alert_targets()`, `software_alert_targets()`,
  `newest_alert_check_id()` and the four call sites in `app.py`, and `app.cloud_key_names(keys)` builds
  it. If `newest_alert_check_id()` sees different names, the alert's `source` differs, the
  acknowledgement stores `check_id = None`, `_is_acknowledged()` refuses to hide an alert without a
  check id, and the alert can never be closed. Keep the default `()` on `build_alerts()`.
  `_send_health_check_list()` passes the same tuple for `needs_follow_up` and `follow_up_open`.
- **`software_incompatible` has two forms.** A software from the settings list keeps `source` = the
  software name, `key_id` = `None`, actions `[remove_software]`, and carries `software`. A wallet
  software that is the name of a configured cloud key can never be removed from the settings, so that
  form belongs to the checked key instead: `key_id` = the checked key, `source` = `Key N: <name>`,
  actions `[replace_hardware]`, and **no** `software` value. Only that form names the software in its
  message, because its source is the key.
- **Every closure carries its source**, because the two forms of a security code are otherwise
  indistinguishable: the CSV writes `<source> — <code>: <action> (YYYY-MM-DD)`, and the history table
  shows `Source`, `Alert`, `Action` and `Closed`.
- **`needs_follow_up` is frozen and `follow_up_open` is current.** Do not "fix" `needs_follow_up` to
  follow `collect_alerts()`, which hides acknowledged alerts and would rewrite history.
- **Deliberately left out:** a software-sourced `security_vulnerable` offers `remove_software` next to
  `ignore` (one button leads nowhere), and a software-sourced `security_compromised` offers it as its
  only action, so an alert whose "software" is a cloud key name can never be closed. Neither is fixed.

## Data model and migration (schema version 13)

The tables and columns are in `docs/spec.md` §4. What matters here:

- Startup migration rebuilds `keys` when it still has `device`, the old `key_number` CHECK, or no
  `active` flag; `key_checks` when it uses the old layout or still holds the two cloud columns; and
  `health_checks` when its `CHECK` constraints still allow the old values. It then drops `tool_checks`
  if it is there, adds the newer columns through `OPTIONAL_COLUMNS`, backfills the key snapshot on
  every check from the key it belongs to, and creates the partial unique index over the active row.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a
  temporary name. `health_checks` is a parent table, so the migration runs with
  `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on
  any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA` and `SCHEMA_VERSION_5`, `_8`, `_9`, `_10`, `_11`
  and `_12` as literal older schemas. Copy that pattern for a new migration test: write the old
  schema, run `initialize_database()`, then assert on the migrated rows.
- There is **no data migration** for an older test database: the user deletes the `data` folder and
  configures the setup again.

## API

The endpoint list and the field details are in `docs/spec.md` §11 and `docs/application.md`. Six
things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. `/robots.txt` is
  `text/plain; charset=utf-8` and is deliberately absent from the service worker's shell list.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial
  setup, and `ValueError`. Keep both, or a broken database answers with a traceback instead of a
  `500`. It is also why `validate_admin_credentials()` is called in its own `try`, and why a refused
  secret has to be a `ValidationError` rather than a bare `ValueError`.
- `DuplicateAddressPath` and `WalletSoftwareNameInUse` must be caught before the general
  `ValidationError` — in `_save_key_settings` and `_rotate_key` — or the `409` turns into a `400`.
- `newest_alert_check_id()` derives the check id for the acknowledgement, the rotation and the
  software removal, so all three use the same comparison rule. `blocking_alert()` is the module-level
  helper the `409` is built on, and `_blocking_alert()` reads the key id straight from the payload, so
  the rule applies before validation.
- The rotate payload is `replaced` + `keep_name` + `name` + `type` + `address_path`, and `type` is
  optional. A rotation inserts a new row and retires the old one, and the acknowledgements are written
  against the **old** key id.
- The `#history-detail` anchor and the `?id=` query on `/history` are client-side only: they never
  reach the server, so no route changed for them.

## The StartOS package — the parts that bite

One service: one daemon, one container, one SQLite database on the persistent `main` volume, mounted
at `/data`. No Postgres, no Redis, no external backend, no extra container.

- **The application and the package share one repository, at the root.** A deliberate deviation from
  the guide's "a package repo is not a fork of the application": the rule assumes a published upstream
  image or a git submodule, and VardKey has neither. `AGENTS.md` states the deviation so nobody adds
  an `upstream-project/` submodule to "fix" it.
- **Anything the `Dockerfile` does not `COPY` is not in the image.** The modules go in with
  `COPY *.py ./` and the assets with `COPY static ./static`. `static/` must be copied: `app.py`
  answers `/health` from code, but every page is read from `ROOT/static`, so an image without it
  reports a healthy service whose whole UI answers `404`.
- **Three things must agree.** `startos/utils.ts` holds `uiPort` (8080); `startos/main.ts` passes it as
  `PORT` and uses it in the readiness URL; `startos/interfaces.ts` binds it. A red
  `ECONNREFUSED 127.0.0.1:8080` blip before `VardKey listening on port 8080` is just the first poll
  landing before Python has bound the socket; nothing to fix.
- **Two actions**, registered through `Actions.of()` in `startos/actions/index.ts`, with their strings
  in `startos/i18n/dictionaries/`: `delete-all-data` and `set-admin-password`. Both run
  `maintenance.py` in a `withTemp` subcontainer, behind a confirmation the handler enforces, and the
  generated password never travels into the container.
- **The admin task** in `startos/init/requireAdmin.ts` raises and clears itself, because SDK 3.0.4 has
  no condition for "the admin password is unset", and its probe fails open. **On the box it shows on
  Tasks as *recommended* and does not hold the service back** — the app's own login gate is what
  refuses everything. `README.md` documents that behaviour.
- **Backups.** `startos/backups.ts` is `sdk.Backups.ofVolumes('main')`. StartOS stops the service for
  the duration of a backup, so the database file is quiescent while it is copied — no snapshot hook is
  needed.
- **No CI.** The guide assumes GitHub Actions; this repository is on Gitea, so there are no
  `.github/workflows/` and there must not be any. The `.s9pk` is built locally with `make`.
- **The skeleton** was written to match the Start9 template rather than generated by
  `s9pk init-workspace`, because that command was not available where it was written. The successful
  build and install confirm they are equivalent; `@start9labs/start-sdk` is pinned to `3.0.4`.
  `node_modules/` is not in the repository.
- **The root `icon.svg` is the package artwork**, read from the repository root by the build, the same
  retro drawing as `static/icon.svg`, and it must stay under 40 KiB.
- **Documentation layout.** `README.md` is the StartOS package README, with the guide's fixed heading
  set. `docs/spec.md` is the specification, `docs/application.md` the application and API reference,
  `instructions.md` the user quick start, and `AGENTS.md` the repo-specific agent context
  (`CLAUDE.md` is the one-line `@AGENTS.md` import). Development happens on
  `https://gitea.sondreolav.com/ai-bot/vardkey` (the `origin` remote), and
  `https://github.com/sondreolav/vardkey` is its public mirror; `AGENTS.md` says which links point
  where and why. **Do not point the manifest or the README links back at Gitea.**

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the
  transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with
  `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in
  `tests/test_database.py`.
- **A module the image is missing is a runtime error, not a build error.** `auth.py` was once left out
  of the `Dockerfile`, and both `app.py` and `maintenance.py` then died with `ModuleNotFoundError`
  inside the container while every test stayed green. The `COPY *.py ./` line is what stops that
  recurring.
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
  saved check and is not marked, and the script refuses to send an empty path.
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
  moment an ancestor gets `overflow: hidden` or `auto`.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while
  `#address-path-warning` is visible, so the browser itself stops the submission.
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
  reads `icons[0]`. The PNG entries must carry the real size and `type: "image/png"`.
- **The favicon link sits next to the manifest link, and `/login` has no manifest.** `IconTests`
  asserts the exact string `<link rel="icon" type="image/svg+xml" href="/icon.svg">` on all six pages.
- **The prettier config is the SDK's own, and `make x86` does not run the check.** `.prettierrc` is the
  single line `"@start9labs/start-sdk/prettier.config.json"`, which is
  `{ trailingComma: "all", tabWidth: 2, semi: false, singleQuote: true }` — everything else is
  prettier's default, so `printWidth` is 80 and `quoteProps` is `"as-needed"`. The SDK makefile defines
  the check as `FORMAT_CHECK`, but `make x86` packs without it, so write the TypeScript the way
  prettier would **and** run
  `npx prettier --config node_modules/@start9labs/start-sdk/prettier.config.json --check startos`
  before you hand the round back; `--write` fixes the files.
  In `startos/manifest/i18n.ts` a value that does not fit the line breaks after the colon, and a string
  with an apostrophe uses double quotes. **A property is measured together with its trailing comma**,
  so the limit is `printWidth − indent` — 78 columns for a top-level property, not 80. `es_ES` at 79
  columns must break; `en_US` at 74 and `pl_PL` at 76 stay inline.
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
- **`sample_payload()` / `unavailable_payload()` are duplicated in five test modules.** They must send
  the key's **own** `address_path`, because the server compares it with the stored one.
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
- **The other server test modules share `tests/server_session.py`.** They mix in `SessionMixin`, which
  signs in through the API, and each class calls `authenticate()` at the end of its own `setUp`. **A
  test that switches `DATABASE_PATH` to another file has to call `authenticate()` again**, because the
  session secret lives in the database.
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
- **`/api/previous-values` still returns a `security` map** that nothing consumes any more, and its
  `address_path` per key is no longer used by the form, which pre-fills the path from
  `keys.address_path`. Both are deliberate.
- **`delete_all_data()` deletes the checks before the keys.** `key_checks.key_id` is
  `ON DELETE RESTRICT`, so the other order fails. The acknowledgements are deleted explicitly, because
  they have no foreign key at all, and the delete has to clear every row of `keys`, active and retired
  alike.
- **The PWA cache stores only a valid shell answer.** `isCacheable()` in `static/sw.js` requires
  `response.ok`, `response.type === "basic"` and `!response.redirected`. The allow-list is the other
  half: the worker never names `/api/*`, `/health`, `/login` or `/robots.txt`.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three
  keys only for rows saved before section 19.
- **The database path default is repeated in sixteen places.** `database.py` carries
  `database_path="data/vardkey.sqlite3"` as the default of every storage function (fifteen of them),
  and `app.py` carries it in `get_database_path()`. A missed one makes a single code path read or
  create the other file, silently.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software
choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as
its software. A key is identified by its type and its address path, while the name is only a label the
user may change. The address path is unique per key, and a rotation replaces the key with a new one
that must carry a new address path and may carry the other type. A rotation creates a new wallet, so
the funds have to be moved from the old multisig setup to the new one before the old keys are
discarded. An alert is closed by the user with the action that belongs to it, and a key with an open
alert cannot be checked until the alert is closed. **A rotation also retires the old key row**: the
multisig slot number stays, the old checks keep the name and type they were recorded with, and the new
row starts with an empty history.
