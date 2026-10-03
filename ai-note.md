# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification: sections 1–18 are the spec, sections 19–22 a short appendix with the four decisions taken along the way, and section 23 agreed work that comes before steps 9–12.
- The binding rules live in `TODO.md` and `README.md`. This note does **not** repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–22, section 18 steps 1–8, and section 23.1. All ticked in `TODO.md`.
- **Tests:** 138, all green. The user runs them: `python3 -m unittest discover -s tests`. They now run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Agreed next work, not started:** section 23.2–23.5 — configurable key setup, type-driven checks, dynamic wallet-software choices, and the matching migration and tests.
- **Remaining after that:** steps 9–12 — StartOS package, persistent volume, backup/restore, `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`.

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

## Section 23.1 — implemented and verified

Read section 23.1 of `TODO.md` for the requirement. What the code now does:

- **Pre-filled values.** `Firmware version`, `Address path`, and `Software version` are set as real input values from `/api/previous-values`, not as HTML placeholders, so an untouched field is saved as it stands. `previousText()` in `static/health-check.js` guards against a `null` becoming the string `"null"`. The software version is reused only for the same key and the same wallet software, and never for the cloud key.
- **`Address path` while hidden.** The field is disabled instead of cleared while the verification is not `OK`, so a pre-filled path survives and still is not submitted with an unverified result. Disabled controls are left out of `FormData`.
- **Compatibility is required.** The form needs an explicit `OK` or `PROBLEM`; `NOT_ASSESSED` is not an option any more and a missing value is a `400`. Old rows with `NOT_ASSESSED` still render and export.
- **Cloud-key compatibility is derived on the server.** `_compatibility_status()` returns the derived value (`OK` when available, `NOT_ASSESSED` when not) and rejects any other value, so the client can no longer claim a result for the cloud key. The hidden control carries the derived `OK` so a hidden `required` select cannot block the submission; `compatibilityDerived` in the script clears it again for another key.
- **Contact statuses.** `contact_info_verified` stores `Confirmed current` or `Needs external update`; the empty option stays, and an empty value is still `NULL`. `Needs external update` shows a reminder in the form and raises the informational `contact_info_unconfirmed` alert. The old `0`/`1` flag is no longer accepted.
- **Schema version 7.** `_health_checks_need_rebuild()` triggers the existing rebuild for either the pre-section-21 status values or the pre-section-23.1 contact check. `_contact_status_expression()` maps `1` to `Confirmed current`, `0` to `Needs external update`, and leaves `NULL` empty. The `health_checks` rebuild applies the status mapping and the contact mapping in one pass.

## Section 23.2–23.5 — agreed direction, not implemented

Read section 23 of `TODO.md` for the full list. The parts that are easy to get wrong:

- **Three keys stay, but the type is free.** Each of the three keys is `hardware` or `cloud` in any combination. More than three keys is future work only.
- **The user names each key once.** That name is the product label everywhere: form, alerts, history, CSV. Show the key number too where it helps, e.g. `Key 1: ColdCard`, and the name alone where the context already makes the key clear. Names must be unique, and both name and type are **immutable** once setup is saved.
- **The type decides the checks, never the key number.** Hardware keys use today's key 1 and 2 checks. Cloud keys use the Nunchuk model but display the configured name.
- **Wallet software choices are `Sparrow` plus the name of each configured cloud key.** Hardware key names are never added to that list. `Nunchuk` therefore appears as a software choice only when a cloud key is actually named Nunchuk.
- **Setup lives in the same SQLite database as the history.** A new database shows first-run setup. An existing database is migrated from its stored key rows and keeps all history. An unreadable database must raise a clear error and must never be treated as a new installation.
- **Security status is recorded for the selected key name and the selected wallet software.** The section 20 carry-forward of a third provider's status is removed. Skip duplicate rows when the key name and the software name are the same.
- **`KEY_PRODUCTS`, `_expected_products()` and `_expected_providers()` are still keyed by key number** in `validation.py`, `static/health-check.js`, `database.py` and `export.py`. Section 23.3 replaces them with the configured name and type.
- **`keys.device` is still `NOT NULL` with a `CHECK` for the three fixed products**, and `seed_fixed_keys()` still writes the fixed profiles on every start. Section 23.2 must decide what happens to both.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **An unavailable key records nothing else.** When `available` is `0`, `wallet_software`, `tool_checks` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED` (only `NOT_ASSESSED`, `""` or `null` may accompany it).
- **`Availability` is required and offers only Yes/No.** There is no "not assessed" value for it, and the server rejects a payload without it.
- **Key 3 collects only `Availability`.** Cloud health, "provider operational" and software compatibility are all derived from it.
- **Security status follows the wallet software choice.** For keys 1 and 2 the third provider is hidden and its last saved status carried forward, and it reappears by itself when that status was `VULNERABLE` or `COMPROMISED`. Section 23 removes this carry-forward, but only once section 23.3 is implemented.
- **BIP327 and SLIP39 are `YES`/`NO`/`NOT_ASSESSED`.** Only `YES` raises the informational alert; a reported `NO` is a negative result and raises nothing.
- **`Address path` is only recorded when `Address path verified` is `OK`.** The form enforces this; the server does not.
- **`/api/alerts` covers every saved check**, not only the newest, and merges identical alerts by `code` plus `source`. A security alert's `source` is the provider, not the key — so two keys' Nunchuk results merge into one alert, which is intended.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Readable user-defined key names are not built.** Section 23.2 adds them; the section 3 item stays unticked until then.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.

## Data model (schema version 7)

- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `contact_info_verified` is text (`Confirmed current` / `Needs external update` / `NULL`).
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `cloud_health_status`, `cloud_provider_operational`, `address_path_verified`, `address_path`, `comments`.
- `tool_checks`: `product`, `bip327_status`, `slip39_status`. The legacy `version`, `checked_at`, `notes` are kept for old rows but never written.
- `ai_security_checks`: `provider`, `status`, `comments`.
- Startup migration rebuilds `key_checks` and `ai_security_checks` when they still use the old layout, and rebuilds `health_checks`, `key_checks` and `tool_checks` when their `CHECK` constraints still allow the old values — for `health_checks` that is either `IKKJE_VURDERT` or `contact_info_verified IN (0, 1)`.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.
- Section 23.4 still adds storage for the key setup (name and type) and its migration.

## API

`GET /health`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Two things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`.
- `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form control is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderToolChecks()` and `renderSecurityChecks()` show an empty note instead of cards when the key is unavailable, and why `syncUnavailableState()` clears `softwareCompatibilitySelect.required` and the cloud key carries a derived value.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed. Assert on the selector text, e.g. `[name="address_path"]`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list.** A test that needs another provider must replace the entry itself.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** Change the contact value in all three when the stored values change again.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19.

## Product clarification

Nunchuk has two roles today: it is the third key and also wallet software. Record only one Nunchuk security status per submission and only one Nunchuk BIP327/SLIP39 row. Sparrow is software only and is checked on every submission.

Section 23 generalises this: the key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice.
