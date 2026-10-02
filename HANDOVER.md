# HANDOVER — Helsesjekk

Handover for the next AI model. The repository is `ai-bot/helsesjekk` on Gitea, branch `main`.

**Language rule:** the requirement list `TODO.md` is intentionally written in Norwegian. Everything else — UI text, source code, variable and function names, comments, and technical documentation — must be in English.

**Status of this document:** written after step 5 of `TODO.md` section 18 was implemented but before the test suite was run. Nothing in `TODO.md` has been ticked off yet. Section 5 of this document lists exactly what can be ticked.

---

## 1. The task

Build a small local web application that runs as a **StartOS 0.4.0 service**. The app helps a single user perform and document an annual health check of a fixed **2-of-3 multisig setup**:

| Key | Type | Device |
|---|---|---|
| 1 | Hardware | SeedSigner |
| 2 | Hardware | Blockstream Jade |
| 3 | Cloud | Nunchuk |

The app **only records results and history**. It must never ask for or store seed phrases, private keys, PINs, passwords, cloud tokens, or contact details — contact information is recorded only as a verified/not-verified flag. It must not sign transactions, build or sign PSBTs, or perform any wallet operation.

`TODO.md` is the only requirement specification. Section 18 gives the work order (steps 1–12).

---

## 2. Repository layout

```
.gitignore
README.md                 English. Status, run instructions, HTTP API table.
TODO.md                   Norwegian. The requirement list. NOT updated, NOT ticked.
app.py                    HTTP server and routing.
database.py               SQLite schema, migrations, and storage.
validation.py             Payload validation for the POST endpoint.
static/index.html         Dashboard.
static/app.js             Dashboard behaviour.
static/health-check.html  Annual health check form.
static/health-check.js    Form behaviour, review summary, save.
static/history.html       Saved checks list and read-only detail.
static/history.js         History rendering.
static/styles.css         Shared responsive stylesheet.
tests/test_app.py         HTTP route and API tests.
tests/test_database.py    Schema, migration, and storage tests.
tests/test_health_check_form.py  Form content tests.
tests/test_validation.py  Payload validation tests.
```

`data/` holds the SQLite file and is git-ignored.

---

## 3. What has been implemented

### Backend

- **`app.py`** — standard-library HTTP server.
  - Routes: `GET /health`, `GET /api/keys`, `GET /api/health-checks`, `GET /api/health-checks/<id>`, `POST /api/health-checks`.
  - Pages: `/`, `/health-check`, `/history`, plus `/styles.css`, `/app.js`, `/health-check.js`, `/history.js`.
  - Static assets are served from an explicit allowlist in `STATIC_FILES`. **New static files must be registered there.**
  - The POST body is capped at 256 KiB. Missing or invalid `Content-Length` and invalid JSON return `400`.
  - Responses set `X-Content-Type-Options`, a restrictive `Content-Security-Policy`, and `Referrer-Policy`. Pages are sent with `Cache-Control: no-store`.
- **`validation.py`** — validation of the POST payload.
  - Requires valid ISO dates, known status values, known `key_id` values, all three keys, all four products (BIP327/SLIP39), and a security status for all four providers.
  - Rejects unknown statuses, unknown key ids, duplicate entries, invalid flags, and over-long text with a `ValidationError` (mapped to `400`).
- **`database.py`** — SQLite with a versioned schema (`PRAGMA user_version`, currently **4**).
  - Tables: `keys`, `health_checks`, `key_checks`, `tool_checks`, `ai_security_checks`.
  - Upgrades are additive and idempotent: `OPTIONAL_COLUMNS` plus `_ensure_column` adds only missing columns, so partially migrated databases are repaired instead of failing.
  - Functions: `initialize_database`, `seed_fixed_keys`, `list_keys`, `save_health_check`, `list_health_checks`, `get_health_check`.
  - The three fixed key profiles are seeded idempotently at startup; a user-changed name is preserved.

### Frontend

- **Dashboard** (`/`) — shows 2-of-3, the three key cards, the last completed and next check dates fetched from the API, a link to `/history`, and a link to the form.
- **Health check form** (`/health-check`) — English form covering every checklist point, a `Review check` button that builds a summary of missing assessments and results needing follow-up, and a `Save health check` button that POSTs structured JSON and then navigates to `/history?id=<id>`.
- **History** (`/history`) — list of saved checks, newest first, and a read-only detail view of every part of a check.

### Tests in the repository

`tests/test_app.py`, `tests/test_database.py`, `tests/test_health_check_form.py`, `tests/test_validation.py`.

### How this round was committed

`validation.py`, `database.py`, `app.py`, and `static/health-check.html` were saved first. Then, one file at a time: `static/health-check.js`, `static/history.html`, `static/history.js`, `static/app.js`, `static/styles.css`. The maintainer then edited `static/index.html`, `tests/test_validation.py`, `tests/test_database.py`, `tests/test_app.py`, and `README.md` directly. The current content of those five files has **not** been reviewed here — verify by reading them and by running the test suite.

---

## 4. What must be tested

### Automated

1. Run `python -m unittest discover -s tests`. All tests must pass. The last known run before this round was 13 tests; the suite is now larger.
2. Confirm coverage for `validation.py` (dates, statuses, key ids, products, flags, text length) and for the POST → GET round trip in `test_app.py`.

### Integration points that are easy to break

3. `static/index.html` must keep the ids `#last-check-title`, `#next-check-title`, `#key-list`, `#key-count`, and the `href="/history"` link — `static/app.js` and `tests/test_app.py` depend on them.
4. `static/health-check.html` must contain `#save-check` and `#save-status` — `static/health-check.js` depends on them.
5. `static/history.html` must contain `#history-list`, `#history-detail`, `#history-detail-title`, and `#history-detail-body` — `static/history.js` depends on them.

### Manual functional test (TODO section 16)

6. Start the app, fill in the form, press `Review check`, then `Save health check` — the browser should land on the history entry with the correct id.
7. The history list shows the check; the detail view shows the summary, all three keys, BIP327/SLIP39, security status, and comments.
8. Save a second check and confirm the first one still exists and was not overwritten.
9. The dashboard shows the last and next check dates after saving.
10. Restart the app and confirm the data is still present (`DATABASE_PATH`, default `data/helsesjekk.sqlite3`).

### Failure paths (TODO section 16, problem tests)

11. Test key unavailable, hardware failure, seed backup failure, address verification failure, software incompatibility, BIP327 result, SLIP39 result, security status `SÅRBAR` and `KOMPROMITTERT`, and contact info `NEI` — and confirm they are stored correctly.
12. Test that a POST with missing fields or an unknown status returns `400` with a readable message, and that an unknown id returns `404`.

---

## 5. `TODO.md` — current status and what can be ticked

**`TODO.md` has not been modified at all.** No item is ticked, and the language requirement has not been added to it. Two housekeeping actions are needed:

1. Add a language-requirement section stating that the UI, source code, comments, and technical documentation must be in English, and that `TODO.md` is the only Norwegian exception.
2. Tick the items below, which are implemented and verified as far as this handover goes.

### Items that can be ticked now

**Section 1, "Dette skal vere med":**
- A simple web app with a dashboard.
- Registration of the three keys (seeded into SQLite and shown on the dashboard).
- Registration of the annual health check (form plus `POST /api/health-checks`).
- Control of all points in the annual checklist (all fields exist in the form and are saved).
- History of completed health checks (list plus read-only detail view).
- Automatic suggestion of the next check, about one year ahead (computed in the form).
- Local SQLite database.

**Section 2, "Viktige reglar":** all items. The app never asks for a seed phrase or private keys, never stores PINs or passwords, stores contact information only as a verified flag, does not pretend to have tested hardware, and stays local and simple.

**Section 3:** showing 2-of-3 in the dashboard, three key profiles, and no general multi-setup support. The item "let the user give the keys readable names" stays unticked — there is no rename UI.

**Section 4:** all field items in 4.1, 4.3, and 4.4, and all rules in 4.3. In 4.2 every field is present except that `ai_security_status` is modelled as a separate `ai_security_checks` table with one row per provider (see section 7 below).

**Section 5:** all items. The general statuses and the four security statuses are used both in the database constraints and in the UI.

**Section 6:** all items in steps 1 through 10, including the summary shown before saving and the requirement that the user presses `Save health check`.

**Section 8, dashboard:** 2-of-3, the last and next health check dates, the start button, and the history link. "Show status per key" and "show active alerts" stay unticked.

**Section 9, history:** all items.

**Section 11, backend:** SQLite, database initialization/migration, storing keys, storing health checks, history, the health endpoint, and every minimum endpoint except `GET /api/export`.

**Section 12, frontend:** simple responsive UI, simplicity over visual complexity, clear status fields, fixed choices for constrained values, showing problems clearly, and showing what remains before saving. The StartOS-browser item stays unticked until the package is tested.

**Section 15, security and privacy:** all items.

**Section 18:** steps 1, 2, 3, 4, and 5.

### Items that must stay unticked

- Section 1: alerts on a point needing follow-up, report export, persistent storage on StartOS, StartOS health check, StartOS backup and restore.
- Section 3: readable key names.
- Section 7: the entire alert and follow-up section.
- Section 8: status per key, active alerts.
- Section 10: the entire report export section.
- Section 11: alert logic, report export, `GET /api/export`.
- Section 12: works well in a normal StartOS browser.
- Sections 13, 14, 16, and 17.
- Section 18: steps 6 through 12.

---

## 6. The way forward

Following `TODO.md` section 18:

- **Step 6 — alert logic (section 7).** Nothing of this is built. The rules in section 7 (key unavailable, hardware failure, missing or damaged seed backup pointing at PROTOCOL 3, address verification failure against BSMS, software no longer supporting the hardware, positive BIP327 or SLIP39, security status, unconfirmed contact information) must be derived from stored data, exposed (for example as `GET /api/alerts`), and rendered in the dashboard `Alerts` card, which is currently a static placeholder. The app must not perform any of these actions itself.
- **Step 7 — finish the dashboard (section 8).** Remaining: per-key status derived from the last check, and active alerts. 2-of-3, last and next dates, the start button, and the history link are done.
- **Step 8 — report export (section 10).** `GET /api/export` does not exist. CSV with explicit Excel compatibility documentation is the simple path; XLSX only if it is genuinely easy.
- **Step 9 — StartOS package (section 13).** Not started. Requires the StartOS package structure (`startos/manifest`, `startos/main.ts`, `interfaces.ts`, `backups.ts`, `init/`, `instructions.md`, `icon.svg`, `Makefile`, and either a prebuilt image or a `Dockerfile`) and an `.s9pk` build. Use the StartOS packaging guide and an existing package repository as the pattern.
- **Step 10 — persistent volume and backup (section 14).** Not started.
- **Step 11 — restart and restore testing (section 16).** Not started.
- **Step 12 — final `.s9pk` and first release (section 17).** Not started.

---

## 7. Open questions and decisions to confirm

- **`ai_security_status` modelling.** `TODO.md` section 4.2 lists `ai_security_status` as a column on `health_checks`, but the implementation stores one row per provider in a dedicated `ai_security_checks` table. This satisfies section 6 step 7, which asks for a status per provider. Confirm the choice and note it in `TODO.md`.
- **Extra columns beyond the specification.** `key_checks.address_verified`, `key_checks.seed_backup_verified`, `key_checks.derivation_height`, and `health_checks.software_comments` are not in the section 4 field lists. Either document them in `TODO.md` or remove them.
- **Norwegian stored enum values.** `IKKJE_VURDERT`, `TRYGG`, `PATCHA`, `SÅRBAR`, and `KOMPROMITTERT` are stored and displayed as data values, while all UI copy around them is English. This follows the specification, but should be recorded as an explicit decision so it is not mistaken for a language-rule violation.
- **Strict save requirements.** The POST endpoint requires all three keys, all four products, and a security status for all four providers. Confirm this is the intended behaviour, or relax it so a partially assessed check can be saved.
- **No authentication.** The app has no authentication of its own. That is reasonable for a local StartOS service behind StartOS access control, but it should be considered explicitly during step 9.
- **No CSRF protection.** The POST endpoint accepts any same-origin request. Acceptable for a single-user local service, but worth an explicit decision.
- **Static asset allowlist.** `STATIC_FILES` in `app.py` must be updated whenever a new static file is added, or it will return `404`.
