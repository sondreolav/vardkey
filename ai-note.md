# AI Agent Note — Per-Key Health Check Changes

## Status

The requirements below have been agreed with the user and added to section 19 of `TODO.md`. They are **not yet implemented**. Treat section 19 as authoritative wherever older requirements elsewhere in `TODO.md` conflict with it. Do not mark TODO items complete until code and tests have been implemented and verified.

The open questions that blocked implementation have now been answered by the user. The answers are recorded in "Decisions confirmed with the user" and are authoritative together with section 19.

**Do not edit `TODO.md` outside section 19 without asking the user.** Several sections are now stale; see "TODO.md sections that are now stale" at the end of this note.

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

8. **Unavailable key.** When `available = No`, the remaining key fields (hardware works, firmware version, seed backup, address path) are hidden and not required. The key note stays available, for example to record why the key is missing or that a replacement has been ordered. The only alert in this case is the critical one: *"This key was not available. Replace the key before continuing; the remaining checks for this key cannot be recorded."* The app must not raise a seed-backup or address alert for an unavailable key, because those checks could not be performed.

9. **Legacy records stay readable.** Existing multi-key records must keep rendering in the history. The migration must map old boolean flags to the new status values (`1` → `OK`, `0` → `Problem`) and fold the old `seed_backup_status` into `seed_backup_verified`.

---

## Product behavior

- Each form submission records one selected key only: SeedSigner (key 1), Blockstream Jade (key 2), or Nunchuk (key 3).
- All key-specific checks and notes in that submission apply only to the selected key.
- The user chooses the check date. Next check due is automatically one calendar year later, is not editable in the UI, and must be calculated/validated on the server too. Handle 29 February consistently, for example by clamping to the last valid day of February.
- Contact confirmation and overall comments remain available for each submission.
- Software compatibility: select one wallet software (Sparrow Wallet or Nunchuk) and record its compatibility status and version for the selected key. Key 3 is fixed to Nunchuk.
- BIP327/SLIP39: record only the two statuses for the selected key's product and the selected software. Do not require statuses for other keys or products in the same submission.
- Security status fields are contextual, as described in decision 4. Use only `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`.
- History must clearly show the selected key and its associated results. Preserve existing saved history and provide a safe, backward-compatible database migration.

---

## Still open (use these defaults unless the user says otherwise)

- `hardware_works` and `firmware_version` for keys 1 and 2: keep the current behaviour, that is, not required.
- `cloud_health_status` and `cloud_provider_operational` for key 3: keep the current behaviour, that is, not required.
- `contact_info_verified`: stays optional with a "not assessed" choice, as today.
- New column names for the software choice: `wallet_software` and `software_version` on `health_checks`, while the legacy `sparrow_version` and `nunchuk_version` columns stay for old rows.

---

## Implementation guidance

1. Read the existing form, API validation, database schema/storage, history UI, alerts, and tests before changing them.
2. Keep the current local SQLite and simple architecture. Avoid unrelated features and do not add AI/network integrations.
3. Update the form and payload so one key is selected and submitted, rather than serializing all three key checks and all four products/providers.
4. Update server-side validation so exactly one configured key is accepted, the selected software is valid, and only the relevant key/product/security results are required. Reject invalid or duplicate records.
5. Compute the next-check date server-side as one calendar year after `checked_at`. Do not trust a client-provided due date.
6. Update persistence and read APIs as required, retaining compatibility with old records. Old records may contain multiple key, tool, and security rows; continue rendering them safely.
7. Update history rendering and alert logic to work for both legacy multi-key records and new single-key records.
8. Add/update tests for each key selection, relevance/omission of security fields, Sparrow/Nunchuk software choice and version, BIP327/SLIP39 statuses, server-derived due date including leap day, unavailable-key handling, invalid payloads, alerts/history, and legacy database/history compatibility.
9. Run the full test suite and report results. Do not edit `TODO.md` beyond its agreed section 19 without asking the user.

### Migration notes

This change touches four tables, so the migration is the riskiest part. Plan it as one explicit, idempotent, additive migration that preserves every existing row:

- `ai_security_checks`: rebuild to allow only `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`, mapping the old Norwegian values.
- `key_checks`: change `seed_backup_verified` and `address_path_verified` from `0`/`1` to `OK`/`Problem`; drop `seed_backup_status`, `address_verified`, and `derivation_height`.
- `health_checks`: add `wallet_software` and `software_version`; keep `sparrow_version` and `nunchuk_version` for legacy rows.
- `tool_checks`: drop `version`, `checked_at`, and `notes` from new submissions.

Verify with a test that starts from a database written by the current code, runs the migration, and then reads both the old rows and a newly saved single-key row.

---

## TODO.md sections that are now stale

Report these to the user and wait for approval before editing them:

- Section 4.2 and 4.3: field lists no longer match the merged fields and the new software columns.
- Section 5.2: still lists the Norwegian security status values.
- Section 6 steps 5, 6, and 7: still describe two version inputs, per-product version/date/notes, and all four providers.
- Section 8: the two summary cards assume a single last and next date.
- Section 9: history does not yet show the selected key.
- Section 11: the POST contract no longer requires all three keys.
- Items already ticked in these sections describe the code as it was before section 19 and will need reworking.

---

## Likely files to inspect/update

- `static/health-check.html`
- `static/health-check.js`
- `validation.py`
- `database.py` (only if needed; preserve old data)
- `static/history.js`
- `alerts.py`
- Relevant tests: `tests/test_health_check_form.py`, `tests/test_validation.py`, `tests/test_database.py`, `tests/test_app.py`, `tests/test_alerts.py`

---

## Important product clarification

Nunchuk has two roles: it is the third key/provider and also wallet software. Still record only one Nunchuk security status per submission, and only one Nunchuk BIP327/SLIP39 row. Sparrow is software only and is checked on every submission. Software compatibility is a separate selection where the user chooses Sparrow Wallet or Nunchuk, except for key 3, which is fixed to Nunchuk.
