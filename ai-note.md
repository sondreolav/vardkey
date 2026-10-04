# AI Agent Note — Helsesjekk

Short working handover for the next model. Keep it short.

- `TODO.md` (Norwegian) is the requirement specification: sections 1–18 are the spec, sections 19–22 a short appendix with the four decisions taken along the way, section 23 the configurable key setup, section 24 the required choices and the removal of BIP327/SLIP39, section 25 the address path identity, the key rotation, the alert acknowledgement, and the settings page, and section 26 the blocking rule, the unique address paths, the rotation with a new path, and the per-alert actions.
- The binding rules live in `TODO.md` and `README.md`. This note does **not** repeat them — it carries the handover, the rules that are easy to get wrong, and the traps that already cost time.
- `HANDOVER.md` was deleted as outdated. Do not recreate it.

## Status

- **Done and verified:** sections 19–22, section 18 steps 1–8, and sections 23, 24 and 25.
- **Verified how:** the automated suite — 283 green tests — and the user's manual browser testing, which is also where section 26 came from. The remaining manual tests are the ones in section 16 of `TODO.md`; the StartOS test there is still open.
- **Tests:** 283 green after section 25. The user runs them: `python3 -m unittest discover -s tests`. They run on a Windows copy at `C:\Users\Driftsleiar\Downloads\helsesjekk`, so they must pass there as well as on Linux.
- **Next work:** section 26 — agreed, not implemented, and it comes before section 18 steps 9–12. More small items may be added to section 26 after the user's browser testing.
- **After that:** section 18 steps 9–12 — the StartOS package, the persistent volume, backup/restore, and `.s9pk`. Covered by sections 13, 14, 16 and 17 of `TODO.md`. Do not start the StartOS part before the user says so.
- **Future work, deliberately not built:** more than three keys, and another threshold than 2-of-3 (section 23).

## Section 26 — agreed, not implemented

Read section 26 of `TODO.md` for the full list. The parts that are easy to get wrong:

- **A key with an open alert cannot get a new check.** The form must name the alert that blocks the key and the action that closes it, and must show which keys are free. The server enforces it with `409`, so a direct API call cannot bypass the rule. The blocking applies to that key only.
- **Every alert must stay closable.** An alert must always carry at least one action, or the key would be locked with no way out. An alert without an action is a bug, not a state the user can reach.
- **The merge rule of section 21 stays as it is.** An alert from an older check is not cleared by a newer check that raises nothing, which is exactly why closing the alert is the way out and why the blocking rule is needed.
- **The address path must be unique across the three keys.** Section 25 allowed the same path for two keys; section 26.2 does not. The comparison happens after `strip` and without regard to case. The setup answers `400`, the settings `409`, and the rotation `400`. An older test database may already hold a duplicate: the app must not crash, the settings must show which keys collide, and a check for such a key is refused until the path is changed.
- **A rotation now requires a new address path.** Section 25 asked the user to confirm that the path was unchanged; section 26.3 replaces that with a required, unique, new path, because the rotation replaces the key. The key number stays, the name may be kept or changed (the field is pre-filled with the current name), and `address_path_unchanged` disappears from the API.
- **Every alert code has its own actions.** The generic `acknowledge` is replaced by `rotate`, `replace_hardware`, `remove_software`, `ignore`, and `contact_updated`, each with its own button text and confirmation step. `POST /api/alerts/acknowledge` takes the action instead of a free reason and stores the action name as the reason. See the table in section 26.4 for which code offers what.
- **`hardware_failure` closes with `replace_hardware`**, which is not a rotation: the user buys new hardware and restores the same seed, so the key and the address path stay the same. That is why the alert no longer needs a generic acknowledgement.
- **`software_incompatible` closes by removing the failing software from the settings list.** The alert must name the software that produced the result, so the link and the removal point at the right entry. If it is the only entry, the user must add a replacement first, because the list may never be empty (section 25.4). The same message, link and removal apply to `security_vulnerable` and `security_compromised` when the software is the source. The recommended mechanism is to suppress the alert while the failing software is no longer in the list.
- **The dashboard key card must show the open alert.** Today it shows its ordinary status, such as `Up to date`; a key with an open alert must instead show a clear message that the key needs action, and how many alerts are open.
- **One CSS fix.** In `03 / Key rotation`, `div.warning-note` sits too close to `div.rotation-list`. Only the spacing changes.
- **Three questions are still open for the user** (section 26.8): how an older database with two identical paths is handled, whether `ignore` also applies to a software-sourced `security_compromised`, and which mechanism closes `software_incompatible` when the software is removed.

## Section 25 — implemented and verified

Section 25 of `TODO.md` is the short summary; what follows are the parts that are easy to get wrong.

- **The address path is the identity of a key, together with its type.** `keys.address_path` was added (a non-empty value in the setup, `TEXT NOT NULL DEFAULT ''` in the table), `/setup` asks for it, and the form records only `Address path`, pre-filled from `key.address_path`. The name is a label that the settings may change.
- **The server derives `address_path_verified`.** It compares the recorded path with `keys.address_path` after stripping both: equal gives `OK`, different gives `PROBLEM`. A submitted `address_path_verified` is **ignored** (the user chose alternative A): the server always writes its own value, so a stale client that claims `OK` is overruled and an alert can never be lost. The comparison only happens when `available` is `1`, so an unavailable key never reports a mismatch and never raises the mismatch alert.
- **A mismatch is treated like a key that could not be checked.** `address_path`, the key note, the contact confirmation and the overall comment are stored; the hardware, the software and the security results stay empty, `wallet_software` is `NULL`, and `software_compatibility_status` is `NOT_ASSESSED`. Sending software or security results with a mismatched path is a `400`, exactly as section 22 does for an unavailable key. `software_version` follows section 22 as well: it is read as text and stored.
- **The form warns before it submits.** `#address-path-warning` appears when the recorded path differs, with the checkbox `#address-path-confirmed`. That checkbox is `required` only while the warning is visible, so a required control is never hidden. When the path does not match, the browser builds the minimal payload itself and the review summary marks the choice.
- **The wallet software list replaced the built-in Sparrow choice.** `validation.py` no longer has `SPARROW_SOFTWARE`; the choices are `software_names` from the settings plus the configured cloud key names. `POST /api/settings/wallet-software` stores the whole list, which must hold at least one name, may not repeat a name, and may not contain a name that a cloud key already provides. A new database is seeded with `Sparrow Wallet`, so the user must add an alternative before the list can be emptied.
- **`/settings` is new and is in `STATIC_FILES`.** It holds `01 / Keys`, `02 / Wallet software` and `03 / Key rotation`. The keys section saves one key at a time (`POST /api/settings/keys`), the address path input is `disabled` when the key has checks, and `has_checks` from `GET /api/settings` tells the page which keys those are.
- **Rotation lives only in the settings.** `POST /api/keys/<id>/rotate` takes `replaced`, `address_path_unchanged`, `keep_name` and `name`; both confirmations must be `true` and `keep_name` must be a real boolean. The page can rotate several keys in one action, but it sends one request per key, because section 11 fixes the endpoint per key. The rotation updates the key row, closes the alerts its own checks raised, and changes no earlier check. The page states that rotating a key creates a new wallet, so the funds must be moved from the old multisig setup before the old keys are discarded. (Section 26.3 replaces `address_path_unchanged` with a required new path.)
- **Acknowledging an alert stores a fifth field.** `alert_acknowledgements` holds `code`, `source`, `reason`, `acknowledged_at` and `check_id` (the user chose alternative B). An alert is hidden while `alert.check_id <= acknowledgement.check_id`, so a newer check, which always has a higher id, raises it again whatever date it carries. The date-comparison variant was rejected because a new check saved on the same day as the acknowledgement would stay hidden. (Section 26.4 replaces the free `reason` with the action name.)
- **Every alert carries `actions` and `key_id`.** `actions` is `rotate`, `acknowledge`, or both, and the dashboard renders one control per action. The endpoint does **not** enforce which action may close an alert (the user chose that): the UI shows only the offered controls, and the app never performs an action itself. (Section 26.4 replaces this action set and adds the enforcement.)
- **The two dead alert rules are gone.** `cloud_provider_problem` and `address_verification_failed` were removed, and the merged cloud wording of `key_unavailable` went with them, so one message covers every key.
- **Schema version 10.** `keys.address_path`, the `wallet_software` table and the `alert_acknowledgements` table were added, and `cloud_health_status` and `cloud_provider_operational` were dropped from `key_checks`. There is **no data migration** for an older test database: the user deletes the `data` folder and configures the setup again. `_key_checks_need_rebuild` also rebuilds when it still sees the two cloud columns.
- **The form label and the cloud version field.** `Software version (if used)` became `Software version`, and the version field moved out of the grid that is hidden for a cloud key, so every key has it. The version is still reused from the last saved value for the same key and software.
- **A latent bug was fixed on the way.** The grid with the wallet software and the compatibility result is hidden for a cloud key, and those two controls used to stay `required`, which blocks a submission with "An invalid form control is not focusable". `syncUncheckableState` now clears the flag for a cloud key as well.

## Section 24 — implemented and verified

Read section 24 of `TODO.md` for the summary. 24.2 and 24.4 were delivered together on purpose, so the schema went to version 9 in one step.

- **24.1:** `Hardware works` is a required `Yes`/`No` with `Select status` as a non-answer first option, for an available hardware key only; the required flag is cleared when the key is unavailable. The contact confirmation is a required `Confirmed current`/`Needs external update`, also for an unavailable key. `NOT_ASSESSED` survives only as the derived `software_compatibility_status` of a key that could not be checked.
- **24.2 and 24.4:** the whole BIP327/SLIP39 function is gone (form, validation, alerts, history, CSV columns), and schema version 9 drops the `tool_checks` table with its rows.
- **24.3:** the form is renumbered to 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. `04 / Standards` is gone.
- **24.5:** the BIP327/SLIP39 tests were removed, tests for the required choices and for the version 8 → 9 migration were added, and `README.md` was updated.

## Section 23.2–23.5 — implemented and verified

- **The setup is stored once.** `POST /api/setup` writes the three key rows; a second call is a `409`, because the type and the address path are locked (section 23.2 and 25.1). `GET /api/setup` answers `{"configured": …, "keys": […]}`.
- **A new database shows the setup step.** `/setup` is a page in `STATIC_FILES`, and `static/app.js`, `static/health-check.js` and `static/settings.js` send the browser there when the setup is missing.
- **An existing database is migrated, not replaced.** `list_keys()` reads the stored rows. A database with 1 or 2 key rows raises `RuntimeError` and is never answered with the setup step.
- **The name is the product label.** `ai_security_checks.provider` holds the configured key name and the selected wallet software, so `validation.py` builds the list from the key, and `static/health-check.js` does the same in `expectedLabels()`.
- **The type decides, never the number.** `_key_check()` and `_compatibility_status()` switch on `key["type"]`, and the script does too.
- **The wallet software choices are the settings list plus every configured cloud key name.** A hardware key name is never a choice. A cloud key records its own name, because the provider is the software for that key.
- **The setup is validated.** `validate_key_setup()` rejects a wrong number of keys, a repeated or out-of-range key number, an empty or over-long name, a name that repeats another one without regard to case, an unknown type, and an empty or over-long address path. Name uniqueness is enforced there and not by a `UNIQUE` constraint, so a legacy database with odd rows is refused by the API instead of being impossible to open. The same path for two keys is allowed **today**; section 26.2 changes that.

### Known leftovers

- `/api/previous-values` still returns a `security` map that nothing consumes any more, and its `address_path` per key is no longer used by the form, which pre-fills the path from `keys.address_path`. Both are deliberate: removing them would shrink the endpoint, but nothing breaks while they stay.

## Rules that are easy to get wrong — do not re-open

- **One submission records one key.** There is no "round" grouping, and each key's next check is its own date plus one calendar year, computed on the server and not editable in the form.
- **A key that could not be checked records nothing else.** That covers `available` = `0` and a recorded address path that does not match. `wallet_software` and `ai_security_checks` must be empty; a non-empty value is a `400`, not something dropped silently. Nothing is stored for them, and `software_compatibility_status` becomes `NOT_ASSESSED` (only `NOT_ASSESSED`, `""` or `null` may accompany it).
- **`Availability` is required and offers only Yes/No.** There is no "not assessed" value for it, and the server rejects a payload without it.
- **A cloud key collects only `Availability`.** Cloud health, "provider operational" and software compatibility are all derived from it, and its own name is the wallet software. The two derived cloud columns and their alerts are gone (section 25.6).
- **A hardware key needs an explicit compatibility status.** `OK` or `PROBLEM`; a missing value and `NOT_ASSESSED` are both a `400` (section 23.1).
- **`Hardware works` needs an explicit `Yes` or `No`** for an available hardware key (section 24.1). A missing value, `""` and `NOT_ASSESSED` are all a `400`; only a key that could not be checked leaves it empty.
- **The contact confirmation is required** for every submission, including one for a key that could not be checked, and it has no "not assessed" value (section 24.1).
- **`NOT_ASSESSED` is not offered or accepted anywhere else** (section 24.1). No field but the derived `software_compatibility_status` accepts it.
- **`Address path verified` is never a form field again.** The server derives it from the comparison (section 25.1). The stored column stays, so the history, the export and the alerts keep working.
- **The address path is locked after the first saved check.** `POST /api/settings/keys` accepts the stored path again but answers `409` for a different one. A rotation is the way to give a key a new path (section 26.3).
- **`/api/alerts` covers every saved check**, not only the newest, merges identical alerts by `code` plus `source`, and leaves out the acknowledged ones. A security alert's `source` is the provider, which is the key's configured name or the software name.
- **An alert is closed by the user, not by a newer check.** A newer check that raises nothing does not clear an older alert; the alert is closed by the action that belongs to it. Section 26.1 adds that a key with an open alert cannot get a new check at all.
- **The export is plain CSV only.** XLSX is not built and the app does not promise Excel compatibility.
- **The prohibition lists** in sections 1 and 13 of `TODO.md` stay unticked. They are standing prohibitions, to be re-confirmed before release.
- **Whether a date is overdue is decided in the browser**, so `/api/key-status` stays independent of the current date.

## Data model (schema version 10)

- `keys`: `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `address_path`, `created_at`. There is no `device` column. The name is editable in the settings; the type and the address path are the identity of the key. Section 26.2 adds that the path must be unique across the three rows.
- `health_checks`: `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `contact_info_verified`, `comments`, plus the legacy `sparrow_version` / `nunchuk_version`. `wallet_software` and `contact_info_verified` are free text.
- `key_checks`: one row per submission — `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`. The two cloud columns are gone.
- `ai_security_checks`: `provider` (free text), `status`, `comments`, with `UNIQUE (health_check_id, provider)`.
- `wallet_software`: `name`, `created_at`. Stored whole, seeded with `Sparrow Wallet` when the list is empty, never emptied through the API.
- `alert_acknowledgements`: `code`, `source`, `check_id`, `reason`, `acknowledged_at`. Section 26.4 stores the action name in `reason`, so no schema change is needed.
- `tool_checks` no longer exists. Version 9 dropped it with its rows (sections 24.2 and 24.4).
- Startup migration rebuilds `keys` when it still has `device`, `key_checks` when it uses the old layout or still holds the two cloud columns, and `health_checks` and `key_checks` when their `CHECK` constraints still allow the old values. It then drops `tool_checks` if it is there.
- The table definitions are `{table}` templates, so a rebuild can create the same table under a temporary name. `health_checks` is a parent table, so the whole migration runs with `PRAGMA foreign_keys = OFF`, checks `PRAGMA foreign_key_check` before committing, and rolls back on any failure.
- `tests/test_database.py` carries `LEGACY_SCHEMA`, `SCHEMA_VERSION_5`, `SCHEMA_VERSION_8` and `SCHEMA_VERSION_9` as literal older schemas. Copy that pattern for a new migration test: write the old schema, run `initialize_database()`, then assert on the migrated rows.

## API

Pages: `/`, `/setup`, `/settings`, `/health-check`, `/history`. Endpoints: `GET /health`, `GET /api/setup`, `POST /api/setup`, `GET /api/keys`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `GET /api/alerts`, `POST /api/alerts/acknowledge`, `GET /api/export`, `POST /api/health-checks`. Field details are in `README.md`.

Section 26 changes the rotation payload, adds the uniqueness rule to three endpoints, makes `POST /api/health-checks` answer `409` for a blocked key, and makes `POST /api/alerts/acknowledge` take an action name.

Five things that are easy to break:

- New static files must be added to `STATIC_FILES` in `app.py`, or they return `404`. That includes `/settings` and `/settings.js`.
- `/api/setup`, `/api/settings`, `/api/alerts`, `/api/key-status` and `/api/previous-values` are extra endpoints that are not in the minimum list in section 11. They are noted in section 11 but not in the specification itself.
- `STORAGE_ERRORS` in `app.py` includes `RuntimeError`, because `list_keys()` raises it for a partial setup. Keep it there, or a broken database answers with a traceback instead of a `500`.
- The settings, rotation and acknowledgement endpoints keep the same error handling as the existing ones: a bad payload is a `400`, an unknown key or alert is a `404`, a locked address path is a `409`, and a broken database is a `500`.
- `newest_alert_check_id()` in `app.py` derives the check id for both the acknowledgement and the rotation, so the same comparison rule is used in both places. The blocking rule of section 26.1 needs the same derived list of open alerts, so it should reuse it rather than rebuild the merge.

## Traps that already cost time — do not repeat

- **`with sqlite3.connect(...)` does not close the connection.** It only commits or rolls back the transaction. On Windows the database file stays locked and `TemporaryDirectory.cleanup()` fails with `WinError 32`. Always close explicitly with `try`/`finally`; see `write_schema()` in `tests/test_database.py`.
- **A `required` control inside a `display:none` container still blocks submission.** The browser refuses to submit and logs "An invalid form control is not focusable". Hiding a section is not enough: the required flags must be cleared, or the section must render something other than required fields. That is why `renderSecurityChecks()` shows an empty note instead of cards when a key could not be checked, why `syncUncheckableState()` clears the flags on the wallet software and the compatibility select — also for a cloud key, whose grid is hidden — and why `syncRequiredFields()` clears the flag on `hardware_works` and `seed_backup_verified`. The new rotation path field must follow the same rule if it can ever be hidden.
- **The mismatch confirmation follows its warning.** `#address-path-confirmed` is `required` only while `#address-path-warning` is visible, so the browser itself stops the submission and a required control is never hidden.
- **The page heading uses `class="eyebrow"` too.** A regex over `health-check.html` finds `Annual security check` before the numbered sections, and `settings.html` starts with `Settings`. A test on the section order must expect that first.
- **Do not assert on the quoting style of the JavaScript.** `static/health-check.js` uses single quotes for constant selectors and template literals where a `${...}` substitution is needed, and `static/settings.js` uses double quotes. Assert on the selector text, e.g. `[name="address_path"]`, and on quote-free substrings such as `/api/settings` and `/settings?rotate=`.
- **`clean_record()` in `tests/test_alerts.py` has a fixed provider list and now carries `key_id`.** A test that needs another provider must replace the entry itself. The cloud fields are gone from it, so a test that wants to prove the removed rules cannot be triggered adds them to the record itself.
- **`sample_payload()` / `unavailable_payload()` are duplicated in `tests/test_validation.py`, `tests/test_database.py` and `tests/test_app.py`.** They build the labels from the key's name and the selected software, they always send `contact_info_verified`, and for a hardware key `hardware_works`. They must send the key's **own** `address_path`, because the server compares it with the stored one; `tests/test_app.py` and `tests/test_database.py` also have a `mismatch_payload()` for the minimal mismatching submission.
- **`validate_health_check()` takes a third argument.** The wallet software list from the settings must be passed in, or a hardware key that selects a settings name is refused. `tests/test_validation.py` and `tests/test_database.py` wrap it in a small `validate()` helper for that reason.
- **`tests/test_app.py` has six test classes.** `ServerTestCase` starts the server, `AppHandlerTests` stores the default setup in `setUp`, `RenamedSetupTests` stores the renamed one, `SettingsApiTests`, `RotationApiTests` and `AcknowledgementApiTests` store the default one, and `KeySetupApiTests` leaves the database empty. A new test must go in the class whose setup it needs.
- **Section 19 records one key per submission**, so a `Check id` in the export can cover up to three keys only for rows saved before section 19.

## Product clarification

The key's configured name is its product label, and a cloud key's name is also a wallet-software choice. A hardware key name is never a wallet-software choice, and a cloud key records its own name as its software. A key is identified by its type and its address path, while the name is only a label that the user may change. Section 26 makes the address path unique per key and makes a rotation replace the key with a new one that must carry a new address path. A rotation creates a new wallet, so the funds have to be moved from the old multisig setup to the new one before the old keys are discarded.
