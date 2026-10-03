# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification: sections 1–18 are the spec, sections 19–22 a short appendix with the four decisions taken along the way, section 23 the configurable key setup, and section 24 the work that came before steps 9–12.
- The binding rules live in `TODO.md` and `README.md`. This note does **not** repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–22, section 18 steps 1–8, and the whole of sections 23 and 24. Ticked in `TODO.md`.
- **Verified how:** the automated suite only. The browser flows and the migration of a real older database have not been run by hand yet; they are the manual tests in section 16 of `TODO.md`.
- **Tests:** 178, all green. The user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Next work, not started:** section 18 steps 9–12 — the StartOS package, the persistent volume, backup/restore, and `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`. Do not start before the user says so; wait for an explicit go-ahead.
- **Future work, deliberately not built:** more than three keys, another threshold than 2-of-3, a user-defined wallet-software list (section 23), and a way to acknowledge an alert (section 22).

## Section 24 — implemented and verified

Read section 24 of `TODO.md` for the summary. 24.2 and 24.4 were delivered together on purpose, so the schema went to version 9 in one step.

- **24.1:** `Hardware works` is a required `Yes`/`No` with `Select status` as a non-answer first option, for an available hardware key only; the required flag is cleared when the key is unavailable. The contact confirmation is a required `Confirmed current`/`Needs external update`, also for an unavailable key. `NOT_ASSESSED` survives only as the derived `software_compatibility_status` of an unavailable key. No database change was needed.
- **24.2 and 24.4:** the whole BIP327/SLIP39 function is gone (form, validation, alerts, history, CSV columns), and schema version 9 drops the `tool_checks` table with its rows. It is a child table, so nothing else is rebuilt.
- **24.3:** the form is renumbered to 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. `04 / Standards` is gone.
- **24.5:** the BIP327/SLIP39 tests were removed, tests for the required choices and for the version 8 → 9 migration were added, and `README.md` was updated.

## Section 23.2–23.5 — implemented and verified

Sections 23.2 and 23.3 were delivered together on purpose: the type is free, so the checks must follow the type, and a half-done step would handle a cloud key in the first slot wrongly. Section 23.4 added schema version 8 and its migration, and 23.5 the tests.

- **The setup is stored once.** `POST /api/setup` writes the three key rows; a second call is a `409`, because the names and the types are locked (section 23.2). `GET /api/setup` answers `{"configured": …, "keys": […]}`.
- **A new database shows the setup step.** `/setup` is a page in `STATIC_FILES`, and both `static/app.js` and `static/health-check.js` send the browser there when `/api/setup` reports `configured: false`.
- **An existing database is migrated, not replaced.** `list_keys()` reads the stored rows; `seed_fixed_keys()` and the fixed `device` column are gone. A database with 1 or 2 key rows raises `RuntimeError` and is never answered with the setup step.
- **The name is the product label.** `ai_security_checks.provider` holds the configured key name and the selected wallet software, so its old `CHECK` list is gone. `validation.py` builds the list from the key, and `static/health-check.js` does the same in `expectedLabels()`.
- **The type decides, never the number.** `_key_check()` and `_compatibility_status()` switch on `key["type"]`, and `derivedValues()` in the script does too.
- **The wallet software choices are `Sparrow Wallet` plus every configured cloud key name.** `_wallet_software_choices()` builds the list on the server and `walletSoftwareChoices()` in the script. A hardware key name is never a choice. A cloud key records its own name, because the provider is the software for that key.
- **The setup is validated.** `validate_key_setup()` rejects a wrong number of keys, a repeated or out-of-range key number, an empty or over-long name, a name that repeats another one without regard to case, and an unknown type. Name uniqueness is enforced there and not by a `UNIQUE` constraint, so a legacy database with odd rows is refused by the API instead of being impossible to open.

### Known leftovers

- `/api/previous-values` still returns a `security` map that nothing consumes any more. It is deliberate: removing it would shrink the endpoint, but nothing breaks while it stays.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **An unavailable key records nothing else.** When `available` is `0`, `wallet_software` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED` (only `NOT_ASSESSED`, `""` or `null` may accompany it).
- **`Availability` is required and offers only Yes/No.** There is no "not assessed" value for it, and the server rejects a payload without it.
- **A cloud key collects only `Availability`.** Cloud health, "provider operational" and software compatibility are all derived from it, and its own name is the wallet software.
- **A hardware key needs an explicit compatibility status.** `OK` or `PROBLEM`; a missing value and `NOT_ASSESSED` are both a `400` (section 23.1).
- **`Hardware works` needs an explicit `Yes` or `No`** for an available hardware key (section 24.1). A missing value, `""` and `NOT_ASSESSED` are all a `400`; only an unavailable key leaves it empty.
- **The contact confirmation is required** for every submission, including one for an unavailable key, and it has no "not assessed" value (section 24.1).
- **`NOT_ASSESSED` is not offered or accepted anywhere else** (section 24.1). `cloud_health_status` accepts only `OK` or `PROBLEM`; the database `CHECK` still allows the old value so legacy rows stay readable.
- **`Address path` is only recorded when `Address path verified` is `OK`.** The form enforces this; the server does not.
- **`/api/alerts` covers every saved check**, not only the newest, and merges identical alerts by `code` plus `source`. A security alert's `source` is the provider, which is the key's configured name or the software name.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.

## Data model (schema version 9)

- `keys`: `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `created_at`. The name is written once and there is no `device` column.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `cloud_health_status`, `cloud_provider_operational`, `address_path_verified`, `address_path`, `comments`.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- `tool_checks` no longer exists. Version 9 dropped it with its rows (sections 24.2 and 24.4).
- Startup migration rebuilds `keys` when it still has `device`, `key_checks` and `ai_security_checks` when they use the old layout, and `health_checks` and `key_checks` when their `CHECK` constraints still allow the old values — `IKKJE_VURDERT`, `contact_info_verified IN (0, 1)`, or one of the fixed provider and wallet-software lists. It then drops `tool_checks` if it is there.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure. Dropping a child table needs no rebuild.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5` and `SCHEMA_VERSION_8` as literal older schemas. Copy that pattern for a new migration test: write the old schema, run `initialize_database()`, then assert on the migrated rows.

## API

Pages: `/`, `/setup`, `/health-check`, `/history`. Endpoints: `GET /health`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Three things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`.
- `/api/setup`, `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form control is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderSecurityChecks()` shows an empty note instead of cards when the key is unavailable, why `syncUnavailableState()` clears `softwareCompatibilitySelect.required`, and why `syncRequiredFields()` clears the flag on `hardware_works`, `seed_backup_verified` and `address_path_verified` for a key that was not available.
- **The page heading uses `class="eyebrow"` too.** A regex over `health-check.html` finds `Annual security check` before the numbered sections, so a test on the section order must expect it first. See `test_the_form_sections_follow_the_agreed_order`.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed. Assert on the selector text, e.g. `[name="address_path"]`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list.** A test that needs another provider must replace the entry itself.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, and they always send `contact_info_verified` and, for a hardware key, `hardware_works`. There is no `tool_checks` part any more (section 24.2).
- **`tests/test_app.py` has three test classes.** `ServerTestCase` starts the server, `AppHandlerTests` stores the default setup in `setUp`, `RenamedSetupTests` stores the renamed one, and `KeySetupApiTests` leaves the database empty. A new test must go in the class whose setup it needs.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software. Section 24.2 removed the BIP327/SLIP39 rows, so a submission records the security statuses and nothing else.
