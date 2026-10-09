# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification. Sections 1–18 are the binding spec; sections 19–28 are short summaries of the rounds. The full reasoning is in the git history.
- The binding rules live in `TODO.md` and `README.md`. This note does not repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–28 and section 18 steps 1–8. Schema version 11. 345 green tests.
- **Next work:** section 18 steps 9–12 — the StartOS package, the persistent volume, backup/restore, and `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`. **Not started.** Do not start the StartOS part before the user says so.
- **Verified how:** the automated suite and the user's manual browser testing. The remaining manual tests are the ones in section 16 of `TODO.md`; the StartOS test there is still open.
- **Tests:** the user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Future work, deliberately not built:** more than three keys, and another threshold than 2-of-3.

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

`remove_software` is still a dead end in two places: a software-sourced `security_vulnerable` offers it next to `ignore` (so the alert stays closable, but one button leads nowhere), and a software-sourced `security_compromised` offers it as its only action, so an alert whose "software" is a cloud key name can never be closed. Neither is fixed.

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
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.
- **`/api/previous-values` still returns a `security` map** that nothing consumes any more, and its `address_path` per key is no longer used by the form, which pre-fills the path from `keys.address_path`. Both are deliberate: removing them would shrink the endpoint, but nothing breaks while they stay.

## Data model (schema version 11)

- `keys`: `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `address_path`, `created_at`. There is no `device` column. The name is editable in the settings; the type and the address path are the identity of the key, the path must be unique across the three rows, and the type only changes through a rotation.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`. The two cloud columns are gone.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- `wallet_software`: `name`, `created_at`. Stored whole, seeded with `Sparrow Wallet` when the list is empty, never emptied through the API.
- `alert_acknowledgements`: `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`. `reason` holds the action name that closed the alert, and `key_id` holds the key the alert belonged to, or `NULL` for a software alert from the settings list.
- `tool_checks` no longer exists.
- Startup migration rebuilds `keys` when it still has `device`, `key_checks` when it uses the old layout or still holds the two cloud columns, and `health_checks` and `key_checks` when their `CHECK` constraints still allow the old values. It then drops `tool_checks` if it is there, and adds the newer columns through `OPTIONAL_COLUMNS` — including `alert_acknowledgements.key_id`.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5`, `SCHEMA_VERSION_8` and `SCHEMA_VERSION_9` as literal older schemas. Copy that pattern for a new migration test: write the old schema, run `initialize_database()`, then assert on the migrated rows.
- There is **no data migration** for an older test database: the user deletes the `data` folder and configures the setup again. An acknowledgement written before version 11 has no key, and the older contact alert used the source `Contact information`, which no longer matches, so the alert it closed is raised again.

## API

Pages: `/`, `/setup`, `/settings`, `/health-check`, `/history`. Endpoints: `GET /health`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `POST /api/alerts/acknowledge`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

The rotate payload is `replaced` + `keep_name` + `name` + `type` + `address_path`, and `type` is optional. `GET /api/health-checks/<id>` also returns `closed_alerts`. The settings page has two sections, and `POST /api/settings/keys` is what a rename alone goes through.

Five things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. That includes `/settings` and `/settings.js`.
- `/api/setup`, `/api/settings`, `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`.
- The settings, rotation and acknowledgement endpoints keep the same error handling as the existing ones: a bad payload is a `400`, an unknown key or alert is a `404`, a locked or duplicate address path is a `409`, and a broken database is a `500`. `DuplicateAddressPath` and `WalletSoftwareNameInUse` must be caught before the general `ValidationError` — in `_save_key_settings` and `_rotate_key` respectively — or the `409` turns into a `400`.
- `newest_alert_check_id()` in `app.py` derives the check id for the acknowledgement, the rotation and the software removal, so the same comparison rule is used in all three places. `blocking_alert()` is the module-level helper the `409` is built on, and `_blocking_alert()` reads the key id straight from the payload, so the rule applies before validation.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form field is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderSecurityChecks()` shows an empty note instead of cards when a key could not be checked, why `syncUncheckableState()` clears the flags on the wallet software and the compatibility select — also for a cloud key, whose grid is hidden — and why `syncRequiredFields()` clears the flag on `hardware_works` and `seed_backup_verified`. The rotation fields follow the same rule: the type is `disabled` until the key is marked for rotation, the path is `disabled` when the key has a saved check and is not marked, and the script refuses to send an empty path.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while `#address-path-warning` is visible, so the browser itself stops the submission and a required control is never hidden.
- **The page heading uses `class="eyebrow"` too.** A regex over `health-check.html` finds `Annual security check` before the numbered sections. `settings.html` starts with `Settings`, then `01 / Wallet software` and `02 / Key rotation`. A test on the section order must expect that first.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed, and `static/settings.js` uses double quotes. Assert on the selector text, e.g. `[name="address_path"]`, and on quote-free substrings such as `/api/settings` and `/settings?rotate=`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list and carries `key_id` and `wallet_software`.** A test that needs another provider must replace the entry itself, and the recorded software is `Sparrow Wallet`, which is what a software alert names. A test that exercises the cloud-key form of `software_incompatible` has to pass `cloud_names` to `build_alerts()`.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, they always send `contact_info_verified`, and for a hardware key `hardware_works`. They must send the key's **own** `address_path`, because the server compares it with the stored one.
- **Every test fixture uses one address path per key** (`ADDRESS_PATH`, `SECOND_ADDRESS_PATH`, `THIRD_ADDRESS_PATH`), because the setup refuses duplicates. `tests/test_app.py` also has `ROTATION_PATHS` and the `rotate()` helper, which picks an unused path per key so a test can rotate several keys in one run.
- **`validate_health_check()` takes a third argument** (the wallet software list), and `validate_rotation()` takes a fourth for the same reason. `tests/test_validation.py` and `tests/test_database.py` wrap the first one in a small `validate()` helper.
- **`tests/test_app.py` has six test classes.** `ServerTestCase` starts the server, `AppHandlerTests` stores the default setup in `setUp`, `RenamedSetupTests` stores the renamed one, `SettingsApiTests`, `RotationApiTests` and `AcknowledgementApiTests` store the default one, and `KeySetupApiTests` leaves the database empty. A new test must go in the class whose setup it needs.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19. A legacy record with several `key_checks` is read through its first one when an alert needs the key it belongs to.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software. A key is identified by its type and its address path, while the name is only a label that the user may change. The address path is unique per key, and a rotation replaces the key with a new one that must carry a new address path and may carry the other type. A rotation creates a new wallet, so the funds have to be moved from the old multisig setup to the new one before the old keys are discarded. An alert is closed by the user with the action that belongs to it, and a key with an open alert cannot be checked until the alert is closed.
