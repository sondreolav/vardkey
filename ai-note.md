# AI Agent Note — Per-Key Health Check Changes

## Status

The requirements below have been agreed with the user and added to section 19 of `TODO.md`. They are **not yet implemented**. Treat section 19 as authoritative wherever older requirements elsewhere in `TODO.md` conflict with it. Do not mark TODO items complete until code and tests have been implemented and verified.

## Product behavior

- Each form submission records one selected key only: SeedSigner (key 1), Blockstream Jade (key 2), or Nunchuk (key 3).
- All key-specific checks and notes in that submission apply only to the selected key.
- The user chooses the check date. Next check due is automatically one calendar year later, is not editable in the UI, and must be calculated/validated on the server too.
- Contact confirmation and overall comments remain available for each submission.
- Software compatibility: select one wallet software (Sparrow or Nunchuk), and record its compatibility status and version for the selected key. Remove the separate Sparrow/Nunchuk version inputs.
- BIP327/SLIP39: record only the two statuses for the selected key/product. Remove version, date checked, and notes/source fields. Do not require statuses for other keys/products in the same submission.
- Security status fields are contextual:
  - SeedSigner status appears only for key 1.
  - Blockstream Jade status appears only for key 2.
  - Sparrow Wallet and Nunchuk software statuses are included with every submission.
  - There is only one Nunchuk status per submission. For key 3, it covers both the Nunchuk key/provider and Nunchuk wallet software; do not duplicate it.
  - Show and require only statuses relevant to the selected key and software. Use the four existing allowed values: `TRYGG`, `PATCHA`, `SÅRBAR`, `KOMPROMITTERT`.
- History must clearly show the selected key and its associated results. Preserve existing saved history and provide a safe, backward-compatible database migration if needed.

## Implementation guidance

1. Read the existing form, API validation, database schema/storage, history UI, alerts, and tests before changing them.
2. Keep the current local SQLite and simple architecture. Avoid unrelated features and do not add AI/network integrations.
3. Update the form and payload so one key is selected and submitted, rather than serializing all three key checks and all four products/providers.
4. Update server-side validation so exactly one configured key is accepted, selected software is valid, and only the relevant key/product/security results are required. Reject invalid or duplicate records.
5. Compute next-check date server-side as one calendar year after `checked_at`; handle leap day consistently (for example, clamp to the last valid day of February). Do not trust a client-provided due date.
6. Update persistence and read APIs as required, retaining compatibility with old records. Old records may contain multiple key, tool, and security rows; continue rendering them safely.
7. Update history rendering and alert logic to work for both legacy multi-key records and new single-key records.
8. Add/update tests for each key selection, relevance/omission of security fields, Sparrow/Nunchuk software choice and version, BIP327/SLIP39 statuses, server-derived due date including leap day, invalid payloads, alerts/history, and legacy database/history compatibility.
9. Run the full test suite and report results. Do not edit `TODO.md` beyond its agreed section 19 without asking the user.

## Likely files to inspect/update

- `static/health-check.html`
- `static/health-check.js`
- `validation.py`
- `database.py` (only if needed; preserve old data)
- `static/history.js`
- `alerts.py`
- Relevant tests: `tests/test_health_check_form.py`, `tests/test_validation.py`, `tests/test_database.py`, `tests/test_app.py`, `tests/test_alerts.py`

## Important product clarification

Nunchuk has two roles: it is the third key/provider and also wallet software. Still record only one Nunchuk security status per submission. Sparrow is software only and is checked on every submission. Software compatibility is a separate selection where the user chooses Sparrow or Nunchuk.
