# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification: sections 1–18 are the spec, sections 19–22 a short appendix with the four decisions taken along the way, and section 23 agreed work that comes before steps 9–12.
- The binding rules live in `TODO.md` and `README.md`. This note does **not** repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–22, section 18 steps 1–8, and the whole of section 23 (23.1–23.5). Ticked in `TODO.md`.
- **Tests:** 178, all green. The user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Next work, not started:** section 18 steps 9–12 — the StartOS package, the persistent volume, backup/restore, and `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`.
- **Future work, deliberately not built:** more than three keys, another threshold than 2-of-3, and a user-defined wallet-software list (section 23.6).

## Ground rules

- English everywhere except `TODO.md`.
- Read the existing files first. Work one file at a time and finish each file before starting the next.
- Do not start a new step without asking.
- The user runs the tests and reports the result. Wait for it.
- Ask one question at a time, with concrete options.
- Never add fields for seed phrases, private keys, PINs, passwords, cloud tokens, or contact details. The app records results only.
- The HTTP tests create their own database and server per test. Keep them order-independent; a shared database already caused one order-dependent failure.
- Record a new decision in `TODO.md` and this note **before** implementing it, and mark it as not implemented until the tests pass.
- `gitea_update_file` needs a fresh `preview_id` from `gitea_preview_file` for the same path and content. `gitea_create_file` returns `422` on an existing file.

## Section 23.2 and 23.3 — implemented and verified

Sections 23.2 and 23.3 were delivered together on purpose: the type is free, so the checks must follow the type, and a half-done step would handle a cloud key in the first slot wrongly.

- **The setup is stored once.** `POST /api/setup` writes the three key rows; a second call is a `409`, because the names and the types are locked (section 23.2). `GET /api/setup` answers `{"configured": …, "keys": […]}`.
- **A new database shows the setup step.** `/setup` is a page in `STATIC_FILES`, and both `static/app.js` and `static/health-check.js` send the browser there when `/api/setup` reports `configured: false`.
- **An existing database is migrated, not replaced.** `list_keys()` reads the stored rows; `seed_fixed_keys()` and the fixed `device` column are gone. A database with 1 or 2 key rows raises `RuntimeError` and is never answered with the setup step.
- **The name is the product label.** `tool_checks.product` and `ai_security_checks.provider` hold the configured key name and the selected wallet software, so their old `CHECK` lists are gone. `validation.py` builds both lists from the key, and `static/health-check.js` does the same in `expectedLabels()`.
- **The type decides, never the number.** `_key_check()` and `_compatibility_status()` switch on `key["type"]`, and `derivedValues()` in the script does too.
- **The wallet software choices are `Sparrow Wallet` plus every configured cloud key name.** `_wallet_software_choices()` builds the list on the server and `walletSoftwareChoices()` in the script. A hardware key name is never a choice. A cloud key records its own name, because the provider is the software for that key. Section 23.3 writes the choice as `Sparrow`, but the stored value stayed `Sparrow Wallet`, so no data migration was needed.
- **The section 20 carry-forward is gone.** A submission records the selected key and the selected software only, so `carriedSecurity` and the "Carried forward from the last saved check" summary are removed from the script. `/api/previous-values` still returns a `security` map that nothing consumes any more.
- **The setup is validated.** `validate_key_setup()` rejects a wrong number of keys, a repeated or out-of-range key number, an empty or over-long name, a name that repeats another one without regard to case, and an unknown type. Name uniqueness is enforced there and not by a `UNIQUE` constraint, so a legacy database with odd rows is refused by the API instead of being impossible to open.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **An unavailable key records nothing else.** When `available` is `0`, `wallet_software`, `tool_checks` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED` (only `NOT_ASSESSED`, `""` or `null` may accompany it).
- **`Availability` is required and offers only Yes/No.** There is no "not assessed" value for it, and the server rejects a payload without it.
- **A cloud key collects only `Availability`.** Cloud health, "provider operational" and software compatibility are all derived from it, and its own name is the wallet software.
- **A hardware key needs an explicit compatibility status.** `OK` or `PROBLEM`; a missing value and `NOT_ASSESSED` are both a `400` (section 23.1).
- **BIP327 and SLIP39 are `YES`/`NO`/`NOT_ASSESSED`.** Only `YES` raises the informational alert; a reported `NO` is a negative result and raises nothing.
- **`Address path` is only recorded when `Address path verified` is `OK`.** The form enforces this; the server does not.
- **`/api/alerts` covers every saved check**, not only the newest, and merges identical alerts by `code` plus `source`. A security alert's `source` is the provider, which is now the key's configured name or the software name.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.

## Data model (schema version 8)

- `keys`: `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `created_at`. The name is written once and there is no `device` column.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `cloud_health_status`, `cloud_provider_operational`, `address_path_verified`, `address_path`, `comments`.
- `tool_checks`: `product` (free text), `bip327_status`, `slip39_status`, with `UNIQUE (health_check_id, product)`. The legacy `version`, `checked_at`, `notes` are kept for old rows but never written.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- Startup migration rebuilds `keys` when it still has `device`, `key_checks` and `ai_security_checks` when they use the old layout, and `health_checks`, `key_checks` and `tool_checks` when their `CHECK` constraints still allow the old values — `IKKJE_VURDERT`, `contact_info_verified IN (0, 1)`, or one of the fixed product, provider, and wallet-software lists.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.

## API

Pages: `/`, `/setup`, `/health-check`, `/history`. Endpoints: `GET /health`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Three things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`.
- `/api/setup`, `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form control is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderToolChecks()` and `renderSecurityChecks()` show an empty note instead of cards when the key is unavailable, and why `syncUnavailableState()` clears `softwareCompatibilitySelect.required` and the cloud key carries a derived value.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed. Assert on the selector text, e.g. `[name="address_path"]`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list.** A test that needs another provider must replace the entry itself.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, so a renamed key works without further changes.
- **`tests/test_app.py` has three test classes.** `ServerTestCase` starts the server, `AppHandlerTests` stores the default setup in `setUp`, `RenamedSetupTests` stores the renamed one, and `KeySetupApiTests` leaves the database empty. A new test must go in the class whose setup it needs.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software, so it contributes one label to the standards and the security statuses.
