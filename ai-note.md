# AI Agent Note — Per-Key Health Check Changes

## Status

The requirements in section 19 of `TODO.md` are **implemented and verified**. The full test suite passes (60 tests, run by the user with `python3 -m unittest discover -s tests`). Section 19 of `TODO.md` and the items that section 19 changed in sections 4, 5, 6, 7, 9, 11 and 18 are ticked.

A follow-up round of questions was then answered by the user; see "Decisions of the follow-up round". The cloud provider alert from that round is implemented, and 62 tests pass.

Treat section 19 as authoritative wherever older requirements elsewhere in `TODO.md` conflict with it. Do not re-open the decisions below; they are settled and built.

**Do not edit `TODO.md` outside section 19 without asking the user.** Section 8 is still stale; see "Remaining work" at the end of this note.

---

## Decisions confirmed with the user

These were settled in a question-by-question review. Do not re-open them.

1. **Security status values become English.** Replace the Norwegian stored values with `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`. Existing rows must be migrated. SQLite cannot alter a `CHECK` constraint, so `ai_security_checks` has to be rebuilt and its rows copied with a value mapping. `README.md` and `TODO.md` section 5.2 must be updated to the English values.

2. **No check "round" grouping.** Each submission stands alone; there is no concept that ties three submissions into one annual check. Every key has its own next-due date, derived from its own last submission as `checked_at` plus one calendar year. Registering one key never changes another key's interval. Consequence: there is no single "next check" — there are three, one per key. The dashboard summary cards in section 8 must be reworked for this (step 7).

3. **BIP327/SLIP39 scope.** Recorded for the selected key's product plus the selected wallet software, deduplicated:
   - Key 1 → SeedSigner + (Sparrow Wallet or Nunchuk)
   - Key 2 → Blockstream Jade + (Sparrow Wallet or Nunchuk)
   - Key 3 → Nunchuk only, one row, because Nunchuk is both the key and the software
   At most two rows per submission. This keeps the section 17 criterion satisfiable for Sparrow.

4. **Security status fields per submission.**
   - Key 1: SeedSigner + Sparrow Wallet + Nunchuk (three fields)
   - Key 2: Blockstream Jade + Sparrow Wallet + Nunchuk (three fields)
   - Key 3: Nunchuk only (one field)
   Sparrow Wallet is not offered for key 3. Sparrow Wallet and Nunchuk follow every submission because they are wallet software used regardless of which key is being checked. Consequence: a `VULNERABLE` or `COMPROMISED` status on Sparrow Wallet raises an alert on every submission, not only when Sparrow is the selected compatibility software.

5. **Software compatibility.** Per submission. Keys 1 and 2 let the user choose Sparrow Wallet or Nunchuk; key 3 is fixed to Nunchuk. Record the compatibility status and the version of the chosen software. The separate Sparrow and Nunchuk version inputs are removed and replaced by one software field plus one version field.

6. **Merged key-check fields.** The user confirmed the `TODO.md` section 4.3 names, with new value semantics:
   - `seed_backup_verified` → status OK / Problem. Keys 1 and 2 only; a cloud key has no seed backup.
   - `address_path_verified` → status OK / Problem.
   - `address_path` → text, the verified address path.
   - `software_comments` → free-text note.
   Removed: `seed_backup_status`, `address_verified`, `derivation_height`. The checklist point "Verifiser derivasjonshøgd" is covered by `address_path`.

7. **OK / Problem is mandatory for the two verification fields.** There is no "not assessed" option and an empty value is rejected at save. They are required only when the key is available, per decision 8.

8. **Unavailable key.** When `available = No`, the remaining key fields (hardware works, firmware version, seed backup, address path) are hidden and not required. The key note stays available, for example to record why the key is missing or that a replacement has been ordered. The only alert in this case is the critical one: *"This key was not available. Replace the key before continuing; the remaining checks for this key could not be recorded."* The app must not raise a seed-backup or address alert for an unavailable key, because those checks could not be performed.

9. **Legacy records stay readable.** Existing multi-key records must keep rendering in the history. The migration must map old boolean flags to the new status values (`1` → `OK`, `0` → `Problem`) and fold the old `seed_backup_status` into `seed_backup_verified`.

---

## Decisions of the follow-up round

Settled after section 19 was implemented and verified.

10. **A negative cloud result is a critical alert.** `cloud_health_status = PROBLEM` or `cloud_provider_operational = 0` on the cloud key raises the new critical alert `cloud_provider_problem`: *"The cloud provider is not operating normally. Check the provider status before continuing."* It is implemented in `alerts.py`, documented in section 7 of `TODO.md` and in `README.md`, and covered by two tests in `tests/test_alerts.py`. It is suppressed for an unavailable key, like the other key-level alerts.

11. **The two negative requirement lists stay unticked.** The "Dette skal ikkje vere med i første versjon" list in section 1 and the "Unngå" list in section 13 are standing prohibitions, not tasks, so they are never ticked. A note in each section says they must be confirmed again before release.

12. **Readable user-defined key names are not built.** Section 3 keeps its item unticked. The three fixed names are enough for the MVP; the database and `seed_fixed_keys` already preserve a custom name if one is ever set.

---

## How it was implemented

Schema version 5. All application code is Python's standard library plus vanilla JavaScript; no new dependencies.

- `database.py` — `SCHEMA_VERSION = 5`. New columns `health_checks.wallet_software` and `health_checks.software_version` (the legacy `sparrow_version` and `nunchuk_version` columns stay). `key_checks` now stores `seed_backup_verified` and `address_path_verified` as `OK`/`PROBLEM` and no longer has `seed_backup_status`, `address_verified`, or `derivation_height`. `ai_security_checks` accepts only the four English values. Two explicit, idempotent rebuilds run inside the existing `BEGIN IMMEDIATE` transaction: `_migrate_key_checks` and `_migrate_ai_security_checks`. Each detects the old layout (legacy column names, or a `CREATE TABLE` statement without `SECURE`) and copies every row with a value mapping. `tool_checks` keeps its `version`, `checked_at`, and `notes` columns for legacy rows but no longer writes them.
- `validation.py` — `validate_health_check(payload, keys)` now takes the key profiles instead of key ids, and normalizes one `key_check` object. `next_check_due()` is a module-level helper that adds one calendar year and clamps 29 February to 28 February; the payload's `next_check_due` is ignored. Irrelevant products and providers, duplicate rows, unknown keys, a non-Nunchuk software choice for key 3, and a missing verification status for an available key are all rejected.
- `app.py` — passes `list_keys(...)` to the validator. No other routing change.
- `alerts.py` — `seed_backup_problem` reads `seed_backup_verified`, `address_verification_failed` reads `address_path_verified`, `cloud_provider_problem` reads `cloud_health_status` and `cloud_provider_operational`, the security statuses are English, and an unavailable key returns only the single critical `key_unavailable` alert.
- `static/health-check.html`, `static/health-check.js` — the form selects one key and one wallet software, renders the key, BIP327/SLIP39 and security fields for that selection, hides the key fields when the key is unavailable, and shows the derived next check date as read-only text.
- `static/history.js` — the detail view shows the checked key and the software selection; the legacy version columns are rendered only when an old record actually has them.
- `README.md` — documents the per-key POST contract, the alert rules, and the migration.

Two implementation choices worth knowing:

- The POST payload uses a single `key_check` object, not a `key_checks` list, because one submission records one key.
- `GET /api/health-checks` summaries now include `key_numbers`, so the history list can show which key a submission belongs to.

---

## Product behavior

- Each form submission records one selected key only: SeedSigner (key 1), Blockstream Jade (key 2), or Nunchuk (key 3).
- All key-specific checks and notes in that submission apply only to the selected key.
- The user chooses the check date. Next check due is automatically one calendar year later, is not editable in the UI, and is calculated/validated on the server too. 29 February is clamped to the last valid day of February.
- Contact confirmation and overall comments remain available for each submission.
- Software compatibility: select one wallet software (Sparrow Wallet or Nunchuk) and record its compatibility status and version for the selected key. Key 3 is fixed to Nunchuk.
- BIP327/SLIP39: record only the two statuses for the selected key's product and the selected software. Do not require statuses for other keys or products in the same submission.
- Security status fields are contextual, as described in decision 4. Only `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED` are accepted.
- History clearly shows the selected key and its associated results. Existing saved history is preserved through a safe, backward-compatible database migration.

---

## Defaults applied

These were the open items with a stated default; the defaults were implemented.

- `hardware_works` and `firmware_version` for keys 1 and 2: not required.
- `cloud_health_status` and `cloud_provider_operational` for key 3: not required. A negative value does raise the critical alert from decision 10.
- `contact_info_verified`: optional, with a "not assessed" choice.
- New column names for the software choice: `wallet_software` and `software_version` on `health_checks`, while the legacy `sparrow_version` and `nunchuk_version` columns stay for old rows.

---

## Migration notes

The migration touches four tables, and it is the riskiest part of the change:

- `ai_security_checks`: rebuilt to allow only `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`, with the old Norwegian values mapped.
- `key_checks`: rebuilt so `seed_backup_verified` and `address_path_verified` hold `OK`/`PROBLEM`; `seed_backup_status`, `address_verified`, and `derivation_height` are dropped.
- `health_checks`: `wallet_software` and `software_version` added; `sparrow_version` and `nunchuk_version` kept for legacy rows.
- `tool_checks`: `version`, `checked_at`, and `notes` are no longer written for new submissions.

`tests/test_database.py` contains `test_legacy_database_migrates_to_per_key_checks`, which starts from a database written by the previous code (schema version 4, Norwegian security statuses, boolean verification flags), runs the migration, and then reads both the old rows and a newly saved single-key row.

---

## Remaining work

- **Step 7 — dashboard.** The cards still show `Profile configured` for each key, and the two overview cards ("Last completed" and "Next check") still use the single latest saved check. They must become per-key status plus per-key last/next dates. Section 8 of `TODO.md` is therefore still stale and is left unticked.
- **Step 8 — `GET /api/export`.** CSV with clear Excel documentation is the simple route; XLSX only if it is genuinely simple.
- **Steps 9–12.** StartOS package (`startos/manifest`, `main.ts`, `interfaces.ts`, `backups.ts`, `init/`, `instructions.md`, `icon.svg`, `Makefile`), persistent volume, backup/restore, restart testing, and the final `.s9pk`.

### Still not in the specification

- `/api/alerts` is an extra endpoint that is not in the minimum list in section 11. It is described in `README.md` and noted in `TODO.md` section 11, but the specification itself has not been extended.

---

## Important product clarification

Nunchuk has two roles: it is the third key/provider and also wallet software. Still record only one Nunchuk security status per submission, and only one Nunchuk BIP327/SLIP39 row. Sparrow is software only and is checked on every submission. Software compatibility is a separate selection where the user chooses Sparrow Wallet or Nunchuk, except for key 3, which is fixed to Nunchuk.
