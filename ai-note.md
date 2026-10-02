# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification. This note is the handover.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** section 19 (one key per submission) and section 18 steps 1–8.
- **Done and verified:** section 20 (hidden fields that are derived or carried forward).
- **Done, NOT verified:** section 21 (English status values, on-demand address path, all alerts on the dashboard). The code and the tests are written and committed; nobody has run the suite yet. If a test fails, fix the code, not the test, unless the test itself is wrong.
- **Tests:** 111 test methods (87 passed before section 21). The user runs them: `python3 -m unittest discover -s tests` from `/home/snes/start9/helsesjekk`.
- **Then:** steps 9–12 (StartOS package, persistent volume, backup/restore, `.s9pk`).

## Ground rules

- English everywhere except `TODO.md`.
- Read the existing files first. Work one file at a time and finish each file before starting the next.
- Do not start a new step without asking. Do not edit `TODO.md` outside the section you are working on without asking.
- The user runs the tests and reports the result. Wait for it.
- Ask one question at a time, with concrete options.
- Never add fields for seed phrases, private keys, PINs, passwords, cloud tokens, or contact details. The app records results only.
- The HTTP tests create their own database and server per test. Keep them order-independent; a shared database already caused one order-dependent failure.
- Record a new decision in `TODO.md` and this note **before** implementing it, and mark it as not implemented until the tests pass.
- `gitea_update_file` needs a fresh `preview_id` from `gitea_preview_file` for the same path and content. `gitea_create_file` returns `422` on an existing file.

## Settled decisions — do not re-open

1. Security statuses are English: `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`. Old rows are migrated.
2. One submission records **one key**. There is no "round" grouping. Each key's next check is its own `checked_at` plus one calendar year, computed on the server (29 February → 28 February), not editable in the form.
3. BIP327/SLIP39 rows are the key's product plus the chosen software, deduplicated: at most two rows, and Nunchuk alone for key 3.
4. Security status per submission: for keys 1 and 2 the form shows the key's product and the chosen software only; the third provider is hidden and its last saved status is carried forward, and it becomes visible again when that status was `VULNERABLE` or `COMPROMISED`. The stored rows are unchanged, so alerts, history and export are unaffected.
5. Wallet software is `Sparrow Wallet` or `Nunchuk`; key 3 is fixed to Nunchuk. One software field plus one version field (`wallet_software`, `software_version`).
6. `seed_backup_verified` (keys 1–2 only) and `address_path_verified` are `OK`/`PROBLEM` and mandatory when the key is available. Removed: `seed_backup_status`, `address_verified`, `derivation_height`.
7. An unavailable key hides and empties the other key fields; the key note stays. The only alert is `key_unavailable` (see decision 18 for the cloud key).
8. Legacy rows keep rendering. The migration maps `1` → `OK`, `0` → `PROBLEM` and folds the old status into `seed_backup_verified`.
9. A negative cloud result (`cloud_health_status = PROBLEM` or `cloud_provider_operational = 0`) raises the critical `cloud_provider_problem`; it stays for rows where the key was available.
10. The prohibition lists in sections 1 and 13 stay unticked. They are standing prohibitions, to be re-confirmed before release.
11. Readable user-defined key names are not built; the section 3 item stays unticked.
12. The dashboard shows status and dates per key on the key cards. The summary cards are "Next check" (earliest due, naming the key) and "Attention" (how many keys are overdue). Whether a date is overdue is decided in the browser, so the API stays independent of the current date.
13. The export is **plain CSV only**, one row per key check, with `Check id` grouping the rows of one submission. XLSX is not built and the app does not promise Excel compatibility. `export.py` holds the column list and the writer; `database.list_export_rows()` builds the rows and joins BIP327, SLIP39, and the security statuses into one cell per column.
14. **Key 3 collects only `Availability`.** `Cloud health check` and `Provider operational` left the form and are derived: `Availability` = Yes → `cloud_health_status` = `OK` and `cloud_provider_operational` = `1`; No → `PROBLEM` and `0`; unanswered → both empty. Server validation keeps the derived cloud values for the cloud key when `available` is `0`. The columns stay for old rows.
15. **Key 3 software compatibility is hidden and derived:** `Availability` = Yes → `OK`, No → `NOT_ASSESSED` (was `IKKJE_VURDERT`, renamed by decision 19). Consequence: key 3 can no longer raise `software_incompatible`.
16. **Placeholders:** `firmware_version` and `address_path` show the previously saved value; `software_version` only when the same software is chosen again. Every derived or carried-forward value is listed in the review panel before saving, marked as such.
17. **One merged critical alert for key 3** when the key was unavailable: *"This key was not available and the cloud provider is recorded as not operating. Check the provider status and replace the key before continuing; the remaining checks for this key cannot be recorded."* `cloud_provider_problem` stays for rows where the key was available.
18. **General statuses are English:** `OK`, `PROBLEM`, `NOT_ASSESSED`. `NOT_ASSESSED` replaced `IKKJE_VURDERT` on all four columns that used it: `health_checks.software_compatibility_status`, `key_checks.cloud_health_status`, `tool_checks.bip327_status`, `tool_checks.slip39_status`. The form and validation reject the old value.
19. **BIP327 and SLIP39 are `YES`/`NO`/`NOT_ASSESSED`**, not `OK`/`PROBLEM`/`IKKJE_VURDERT`, because "not assessed" must not read as "no". `validation.STANDARDS_STATUSES` holds the set; the form has its own `standardsStatuses` option list. Only `YES` raises the informational alert — a reported `NO` is a negative result and raises nothing.
20. **`Address path` is only recorded when `Address path verified` is `OK`.** The field is hidden and cleared otherwise. The server does not enforce this; the form does.
21. **`/api/alerts` covers every saved check**, not only the newest, so a warning is never lost when a newer check for another key is saved. Each alert carries `check_id` and `checked_at`. Identical alerts (same `code` and `source`) are merged and only the newest is listed. Critical first, then newest first. `alerts.collect_alerts()` holds the merge; `app.py` only loads the records.
22. **`Helsesjekk` and `data/helsesjekk.sqlite3` are deliberate exceptions** to the English rule and are documented as such in `README.md`.

## Data model (schema version 6)

- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status` (`OK`/`PROBLEM`/`NOT_ASSESSED`), `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified` (OK/PROBLEM), `cloud_health_status` (`OK`/`PROBLEM`/`NOT_ASSESSED`), `cloud_provider_operational`, `address_path_verified` (OK/PROBLEM), `address_path`, `comments`.
- `tool_checks`: `product`, `bip327_status`, `slip39_status` (`YES`/`NO`/`NOT_ASSESSED`). The legacy `version`, `checked_at`, `notes` are kept for old rows but never written.
- `ai_security_checks`: `provider`, `status` (English), `comments`.
- Startup migration rebuilds `key_checks` and `ai_security_checks` when they still use the old layout, and rebuilds `health_checks`, `key_checks`, and `tool_checks` when their `CHECK` constraints still allow `IKKJE_VURDERT`.
- The table definitions are `{table}` templates so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure. `test_status_values_migrate_to_english` and `test_the_rebuilt_parent_table_keeps_its_foreign_keys` cover this.

## API

`GET /health`, `GET /api/keys`, `GET /api/key-status`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Two things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`.
- `/api/alerts` and `/api/key-status` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.

## Remaining work

- **Verify section 21.** Run the tests. If they pass, tick section 21 and re-confirm steps 4 and 6 in section 18, then update this note.
- **Steps 9–12.** StartOS package (`startos/manifest`, `main.ts`, `interfaces.ts`, `backups.ts`, `init/`, `instructions.md`, `icon.svg`, `Makefile`), persistent volume, backup/restore, restart testing, and the final `.s9pk`.

## Product clarification

Nunchuk has two roles: it is the third key and also wallet software. Record only one Nunchuk security status per submission and only one Nunchuk BIP327/SLIP39 row. Sparrow is software only and is checked on every submission.
