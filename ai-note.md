# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification. Sections 1–18 are the binding spec; sections 19–27 are short summaries of the rounds. The full reasoning is in the git history.
- The binding rules live in `TODO.md` and `README.md`. This note does not repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–27 and section 18 steps 1–8. Schema version 11. 337 green tests.
- **Next work:** section 18 steps 9–12 — the StartOS package, the persistent volume, backup/restore, and `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`. Do not start the StartOS part before the user says so.
- **Verified how:** the automated suite and the user's manual browser testing. The remaining manual tests are the ones in section 16 of `TODO.md`; the StartOS test there is still open.
- **Tests:** the user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Future work, deliberately not built:** more than three keys, and another threshold than 2-of-3.

## Section 27 — implemented

Section 27 is implemented and verified, and the schema is version 11. Read section 27 of `TODO.md` for the binding rules; this is the record of what was done. The work was done one file at a time, in this order:

1. `alerts.py`
2. `database.py`
3. `app.py`
4. `export.py`
5. `static/history.js`
6. `static/app.js` (only the last bullet below)
7. `tests/test_alerts.py`, `tests/test_database.py`, `tests/test_app.py`, `tests/test_export.py`, `tests/test_health_check_form.py`
8. `README.md`
9. `ai-note.md`

What changed:

- **Blocking.** An alert that belongs to a key blocks that key until the alert is closed. That now includes `contact_info_unconfirmed`, which has severity `info`. `blocking_alert()` in `app.py` and the `blockingAlerts` filter in `static/health-check.js` already match on `key_id`, so no blocking code changed: the rule is satisfied by giving the two alerts below a `key_id`.
- **The contact alert belongs to a key.** `key_id` is the checked key, `source` becomes `Key N: <name>` (the convention the key alerts already use), and the message names the key: `The contact details for Key 1: SeedSigner need an external update. Update them in your external documentation, then close this alert.` Severity stays `info` and the action stays `contact_updated`.
- **`software_incompatible` gets two forms.** When the recorded `wallet_software` is the name of a configured cloud key: `key_id` is the checked key, `source` is `Key N: <name>`, and the actions are `[replace_hardware]`. Otherwise it stays as it is: `key_id` is `None`, `source` is the software name (or `_SOFTWARE_SOURCE`), and the actions are `[remove_software]`. The reason for the split: a cloud key name can never be removed from the settings — `validate_wallet_software` refuses it — so `remove_software` would be a dead end and the alert could never be closed.
- **The acknowledgement stores the key.** `alert_acknowledgements` gets a new, nullable `key_id` column (INTEGER, no FK, no CHECK). Schema version 11: bump `SCHEMA_VERSION`, add the column to `ALERT_ACKNOWLEDGEMENTS_TABLE` and to `OPTIONAL_COLUMNS` so `ALTER TABLE ... ADD COLUMN` migrates an older database. No table rebuild is needed, and `save_alert_acknowledgement()` takes `key_id` as a new argument. `software_alert_targets()` returns `(code, source, key_id)` triples.
- **Alert identity.** An alert with a `key_id` is acknowledged and hidden by `(code, key_id)`; an alert without one stays as it is, by `(code, source)`. This fixes a real bug: `_is_acknowledged()` matched on `source`, which contains the name the key has *now*, so a `rotate` with `keep_name=false` — or a plain rename in the settings — wrote an acknowledgement with the old name and then rebuilt the alert with the new one, and the closed alert reappeared.
- **Closures in the history and the CSV.** Closures with a `key_id` (that is `rotate`, `replace_hardware`, `contact_updated`, and `ignore` with a key as its source) are visible in `GET /api/health-checks/<id>` and in the CSV export. `remove_software` and a software-sourced `ignore` are not visible. A closure is attached to the check that it closed, through `check_id`.
  - `list_alert_acknowledgements()` takes an optional `check_id` filter, and `app.py` assembles the payload. The detail view gets a `closed_alerts` list with `code`, `source`, `action` and `acknowledged_at`.
  - `static/history.js` gets a card, `Follow-up closed`, with one line per closure: code, source, the action written out as a readable label, and the date. The action labels are duplicated in that file, which is the existing pattern (see `ACTION_LABELS` in `app.js` and `health-check.js`).
  - The CSV gets one new column, last: `Follow-up closed`, with `code: action (YYYY-MM-DD); ...` in one cell per check — the same joining pattern `Security status` uses.
- **One frontend change in `static/app.js`.** A key card with an open alert keeps showing `Last checked` and `Next check due`; the alert note comes in addition, not instead.

### Notes from section 27

- **The `cloud_names` trap.** `alerts.py` cannot tell that `Nunchuk` is a cloud key from the record alone, so `build_alerts()`/`collect_alerts()` take an optional parameter, `cloud_names=()`, threaded through `rotation_alert_targets()`, `software_alert_targets()`, and the call sites in `app.py` (`_send_alerts`, `_blocking_alert`, `_rotate_key`, `_close_removed_software`, `_acknowledge_alert`) plus `newest_alert_check_id()`. If `newest_alert_check_id()` does not receive exactly the same `cloud_names` as `collect_alerts()`, the alert's `source` differs, the acknowledgement stores `check_id = None`, `_is_acknowledged()` refuses to hide an alert without a check id, and the alert can never be closed. `_acknowledge_alert` needs it too, or the cloud form of the alert cannot be found at all. It is commented and covered by a test.
- `build_alerts()` keeps the default `cloud_names=()`, or every existing call in the tests breaks.
- The cloud form of `software_incompatible` carries no `software` field: there is no settings entry to remove, so a software removal must not be able to close it. That is why `software_alert_targets()` never returns it.
- A legacy record saved before section 19 can hold up to three `key_checks`. `_checked_key()` uses the first one to find the key, and says so in a comment.
- **A test broke by design:** `AppHandlerTests.test_alerts_api_merges_identical_alerts_and_keeps_the_newest` used the contact alert precisely because it carried no key and never blocked. It now acknowledges between the two submissions.
- The old `source` value `Contact information` disappeared. Acknowledgements written before the change no longer match; that is acceptable, because the project writes no data migration for a test database, and it is said in this note and in `README.md`.
- **Windows:** keep closing `sqlite3` connections explicitly with `try`/`finally`. `with sqlite3.connect(...)` only commits or rolls back, and the file stays locked so `TemporaryDirectory.cleanup()` fails with `WinError 32`.

### Tests added or changed for section 27

- `tests/test_alerts.py`: the contact alert's `key_id`, `source` and message; a cloud-key software → `[replace_hardware]` plus a `key_id`; a settings-list software → unchanged; an acknowledgement matched by `key_id` after the name changed; a cloud-key software alert hidden by its key. Three tests that mentioned `Contact information` as the source were updated: `test_contact_details_that_need_an_external_update_are_reported`, `AlertActionTests.test_the_agreed_actions_are_offered_for_each_code_and_source`, and `test_an_acknowledgement_covers_one_alert_only` (formerly `..._one_code_and_source_only`). The key-alert acknowledgements in `CollectAlertsTests` now carry a `key_id`, and `software_alert_targets()` is asserted with `(code, source, key_id)` triples.
- `tests/test_database.py`: version 11 in `test_initialization_creates_versioned_schema_and_is_idempotent` and `test_a_version_9_database_gains_the_address_path_and_the_new_tables`; a new `SCHEMA_VERSION_10` literal with a migration test, following the pattern of the older ones; `save_alert_acknowledgement()` with `key_id`; a software acknowledgement without a key; `list_alert_acknowledgements(check_id=...)`; the closure cell in `list_export_rows`.
- `tests/test_app.py`: the history detail holds the closure and leaves out `remove_software`; the CSV cell; the contact alert blocks with `409` and frees the key at `contact_updated`; the cloud-key software flow end to end; the rotation regression with a new name.
- `tests/test_export.py`: the new column is last, and the joined cell reads back.
- `tests/test_health_check_form.py`: the new history card, and the key dates that stay on a card with an open alert.

### Deliberately left out

`remove_software` is a dead end in two more places today, both outside what the user asked for: a software-sourced `security_vulnerable` still offers `remove_software` next to `ignore` (so it stays closable, but one of the buttons leads nowhere), and a software-sourced `security_compromised` offers `remove_software` as its only action, so an alert whose "software" is a cloud key name can never be closed. Not fixed in section 27.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **A key that could not be checked records nothing else.** That covers `available` = `0` and a recorded address path that does not match. `wallet_software` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED`.
- **`Availability` is required and offers only Yes/No.** A cloud key collects only `Availability`; its compatibility is derived from it, and its own name is the wallet software.
- **A hardware key needs an explicit compatibility status**, and `Hardware works` needs an explicit `Yes` or `No`. A missing value, `""` and `NOT_ASSESSED` are all a `400`.
- **The contact confirmation is required** for every submission, including one for a key that could not be checked, and it has no "not assessed" value.
- **`NOT_ASSESSED` is not offered or accepted anywhere else.** No field but the derived `software_compatibility_status` accepts it.
- **`Address path verified` is never a form field again.** The server derives it from the comparison. The stored column stays, so the history, the export and the alerts keep working.
- **The address path is locked after the first saved check**, and no two keys may share one — in the setup, in the settings or in a rotation.
- **An alert is closed by the user, not by a newer check.** A newer check that raises nothing does not clear an older alert, and a key with an open alert cannot get a new check at all.
- **An acknowledgement stores the action name, not a free reason**, and only the actions the endpoint performs are accepted. `rotate` has its own endpoint, because it requires a new address path.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.
- **`/api/previous-values` still returns a `security` map** that nothing consumes any more, and its `address_path` per key is no longer used by the form, which pre-fills the path from `keys.address_path`. Both are deliberate: removing them would shrink the endpoint, but nothing breaks while they stay.

## Data model (schema version 11)

- `keys`: `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `address_path`, `created_at`. There is no `device` column. The name is editable in the settings; the type and the address path are the identity of the key, and the path must be unique across the three rows.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`. The two cloud columns are gone.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- `wallet_software`: `name`, `created_at`. Stored whole, seeded with `Sparrow Wallet` when the list is empty, never emptied through the API.
- `alert_acknowledgements`: `code`, `source`, `key_id` (section 27), `check_id`, `reason`, `acknowledged_at`. `reason` holds the action name that closed the alert, and `key_id` holds the key the alert belonged to, or `NULL` for a software alert from the settings list.
- `tool_checks` no longer exists.
- Startup migration rebuilds `keys` when it still has `device`, `key_checks` when it uses the old layout or still holds the two cloud columns, and `health_checks` and `key_checks` when their `CHECK` constraints still allow the old values. It then drops `tool_checks` if it is there, and adds the new columns through `OPTIONAL_COLUMNS`.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5`, `SCHEMA_VERSION_8`, `SCHEMA_VERSION_9` and `SCHEMA_VERSION_10` as literal older schemas. Copy that pattern for a new migration test: write the old schema, run `initialize_database()`, then assert on the migrated rows.
- There is **no data migration** for an older test database: the user deletes the `data` folder and configures the setup again. An acknowledgement written before section 27 has no `key_id`, and the older contact alert used the source `Contact information`, which no longer matches, so that closure is not carried over.

## API

Pages: `/`, `/setup`, `/settings`, `/health-check`, `/history`. Endpoints: `GET /health`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `POST /api/alerts/acknowledge`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Five things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. That includes `/settings` and `/settings.js`.
- `/api/setup`, `/api/settings`, `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`.
- The settings, rotation and acknowledgement endpoints keep the same error handling as the existing ones: a bad payload is a `400`, an unknown key or alert is a `404`, a locked or duplicate address path is a `409`, and a broken database is a `500`. `DuplicateAddressPath` must be caught before the general `ValidationError` in `_save_key_settings`, or the `409` turns into a `400`.
- `newest_alert_check_id()` in `app.py` derives the check id for the acknowledgement, the rotation and the software removal, so the same comparison rule is used in all three places. `blocking_alert()` is the module-level helper the `409` is built on, and `_blocking_alert()` reads the key id straight from the payload, so the rule applies before validation.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form field is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderSecurityChecks()` shows an empty note instead of cards when a key could not be checked, why `syncUncheckableState()` clears the flags on the wallet software and the compatibility select — also for a cloud key, whose grid is hidden — and why `syncRequiredFields()` clears the flag on `hardware_works` and `seed_backup_verified`. The rotation path field follows the same rule: it is `disabled` until the key is selected, and the script refuses to send an empty one.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while `#address-path-warning` is visible, so the browser itself stops the submission and a required control is never hidden.
- **The page heading uses `class="eyebrow"` too.** A regex over `health-check.html` finds `Annual security check` before the numbered sections, and `settings.html` starts with `Settings`. A test on the section order must expect that first.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed, and `static/settings.js` uses double quotes. Assert on the selector text, e.g. `[name=\"address_path\"]`, and on quote-free substrings such as `/api/settings` and `/settings?rotate=`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list and carries `key_id` and `wallet_software`.** A test that needs another provider must replace the entry itself, and the recorded software is `Sparrow Wallet`, which is what a software alert names.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, they always send `contact_info_verified`, and for a hardware key `hardware_works`. They must send the key's **own** `address_path`, because the server compares it with the stored one.
- **Every test fixture uses one address path per key** (`ADDRESS_PATH`, `SECOND_ADDRESS_PATH`, `THIRD_ADDRESS_PATH`), because the setup refuses duplicates. `tests/test_app.py` also has `ROTATION_PATHS` and the `rotate()` helper, which picks an unused path per key so a test can rotate several keys in one run.
- **`validate_health_check()` takes a third argument.** The wallet software list from the settings must be passed in, or a hardware key that selects a settings name is refused. `tests/test_validation.py` and `tests/test_database.py` wrap it in a small `validate()` helper for that reason.
- **`tests/test_app.py` has six test classes.** `ServerTestCase` starts the server, `AppHandlerTests` stores the default setup in `setUp`, `RenamedSetupTests` stores the renamed one, `SettingsApiTests`, `RotationApiTests` and `AcknowledgementApiTests` store the default one, and `KeySetupApiTests` leaves the database empty. A new test must go in the class whose setup it needs.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software. A key is identified by its type and its address path, while the name is only a label that the user may change. The address path is unique per key, and a rotation replaces the key with a new one that must carry a new address path. A rotation creates a new wallet, so the funds have to be moved from the old multisig setup to the new one before the old keys are discarded. An alert is closed by the user with the action that belongs to it, and a key with an open alert cannot be checked until the alert is closed.
