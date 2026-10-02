# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification. This note is the handover.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** section 19 (one key per submission) and section 18 steps 1–8. Those items are ticked in `TODO.md`.
- **Tests:** 76, all passing. The user runs them: `python3 -m unittest discover -s tests` from `/home/snes/start9/helsesjekk`.
- **Agreed, NOT implemented:** the decisions in "New decisions" below, recorded as section 20 of `TODO.md`. Sections 4.2, 4.3, 6 (steps 4, 5, 7, 10), 7, 11 and 19 carry "Endra i §20" notes, and section 18 steps 4 and 6 are set back to unticked because of them.
- **Then:** steps 9–12 (StartOS package, persistent volume, backup/restore, `.s9pk`).

## Ground rules

- English everywhere except `TODO.md`.
- Read the existing files first. Work one file at a time and finish each file before starting the next.
- Do not start a new step without asking. Do not edit `TODO.md` outside section 19 without asking.
- The user runs the tests and reports the result. Wait for it.
- Ask one question at a time, with concrete options.
- Never add fields for seed phrases, private keys, PINs, passwords, cloud tokens, or contact details. The app records results only.
- The HTTP tests create their own database and server per test. Keep them order-independent; a shared database already caused one order-dependent failure.
- Record a new decision in `TODO.md` and this note **before** implementing it, and mark it as not implemented until the tests pass.

## Settled decisions — do not re-open

1. Security statuses are English: `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`. Old rows are migrated.
2. One submission records **one key**. There is no "round" grouping. Each key's next check is its own `checked_at` plus one calendar year, computed on the server (29 February → 28 February), not editable in the form.
3. BIP327/SLIP39 rows are the key's product plus the chosen software, deduplicated: at most two rows, and Nunchuk alone for key 3.
4. **Revised by decision 14.** Security status per submission: for keys 1 and 2 the form now shows the key's product and the chosen software only; the third provider is hidden and its last saved status is carried forward, and it becomes visible again when that status was `VULNERABLE` or `COMPROMISED`. The stored rows are unchanged, so alerts, history and export are unaffected. (Was: all three providers were shown on every submission.)
5. Wallet software is `Sparrow Wallet` or `Nunchuk`; key 3 is fixed to Nunchuk. One software field plus one version field (`wallet_software`, `software_version`).
6. `seed_backup_verified` (keys 1–2 only) and `address_path_verified` are `OK`/`PROBLEM` and mandatory when the key is available. Removed: `seed_backup_status`, `address_verified`, `derivation_height`.
7. An unavailable key hides and empties the other key fields; the key note stays. The only alert is `key_unavailable` (see decision 18 for the cloud key).
8. Legacy rows keep rendering. The migration maps `1` → `OK`, `0` → `PROBLEM` and folds the old status into `seed_backup_verified`.
9. A negative cloud result (`cloud_health_status = PROBLEM` or `cloud_provider_operational = 0`) raises the critical `cloud_provider_problem`; it stays for rows where the key was available.
10. The prohibition lists in sections 1 and 13 stay unticked. They are standing prohibitions, to be re-confirmed before release.
11. Readable user-defined key names are not built; the section 3 item stays unticked.
12. The dashboard shows status and dates per key on the key cards. The summary cards are "Next check" (earliest due, naming the key) and "Attention" (how many keys are overdue). Whether a date is overdue is decided in the browser, so the API stays independent of the current date.
13. The export is **plain CSV only**, one row per key check, with `Check id` grouping the rows of one submission. XLSX is not built and the app does not promise Excel compatibility. `export.py` holds the column list and the writer; `database.list_export_rows()` builds the rows and joins BIP327, SLIP39, and the security statuses into one cell per column.

## New decisions — agreed, not yet implemented

Recorded as section 20 of `TODO.md`. Do not re-open them either.

14. **Key 3 collects only `Availability`.** `Cloud health check` and `Provider operational` leave the form and are derived: `Availability` = Yes → `cloud_health_status` = `OK` and `cloud_provider_operational` = `1`; No → `PROBLEM` and `0`; unanswered → both empty. Server validation keeps the derived cloud values for the cloud key when `available` is `0` (today it empties them). The columns stay for old rows.
15. **Key 3 software compatibility is hidden and derived:** `Availability` = Yes → `OK`, No → `IKKJE_VURDERT`. Consequence: key 3 can no longer raise `software_incompatible`.
16. **Security status follows the wallet software choice** — see the revised decision 4.
17. **Placeholders:** `firmware_version` and `address_path` show the previously saved value; `software_version` only when the same software is chosen again. Every derived or carried-forward value is listed in the review panel before saving, marked as such.
18. **One merged critical alert for key 3** when the key was unavailable: *"This key was not available and the cloud provider is recorded as not operating. Check the provider status and replace the key before continuing; the remaining checks for this key cannot be recorded."* `cloud_provider_problem` stays for rows where the key was available.

## Data model (schema version 5)

- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified` (OK/PROBLEM), `cloud_health_status`, `cloud_provider_operational`, `address_path_verified` (OK/PROBLEM), `address_path`, `comments`.
- `tool_checks`: `product`, `bip327_status`, `slip39_status`. The legacy `version`, `checked_at`, `notes` are kept for old rows but never written.
- `ai_security_checks`: `provider`, `status` (English), `comments`.
- Startup migration rebuilds `key_checks` and `ai_security_checks` when they still use the old layout. Covered by `test_legacy_database_migrates_to_per_key_checks`.
- No schema change is needed for decisions 14–18; only `GET /api/key-status` is extended with the last saved values per key.

## API

`GET /health`, `GET /api/keys`, `GET /api/key-status`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Two things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`.
- `/api/alerts` and `/api/key-status` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.

## Remaining work

- **Decisions 14–18.** Implement them, run the tests, then tick section 20 and steps 4 and 6 in section 18.
- **Steps 9–12.** StartOS package (`startos/manifest`, `main.ts`, `interfaces.ts`, `backups.ts`, `init/`, `instructions.md`, `icon.svg`, `Makefile`), persistent volume, backup/restore, restart testing, and the final `.s9pk`.

## Product clarification

Nunchuk has two roles: it is the third key and also wallet software. Record only one Nunchuk security status per submission and only one Nunchuk BIP327/SLIP39 row. Sparrow is software only and is checked on every submission.
