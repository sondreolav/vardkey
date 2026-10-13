"""Minimal HTTP server for the VardKey dashboard."""

from datetime import datetime
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from alerts import (
    REMOVE_SOFTWARE,
    ROTATE,
    build_alerts,
    collect_alerts,
    rotation_alert_targets,
    software_alert_targets,
)
from auth import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    admin_configured,
    authenticate,
    create_session_token,
    csrf_tokens_match,
    new_csrf_token,
    set_admin,
    validate_admin_credentials,
    verify_session_token,
)
from database import (
    get_health_check,
    get_multisig_settings,
    initialize_database,
    key_has_check,
    list_alert_acknowledgements,
    list_export_rows,
    list_health_checks,
    list_key_status,
    list_keys,
    list_previous_values,
    list_wallet_software,
    save_alert_acknowledgement,
    save_health_check,
    save_key_settings,
    save_key_setup,
    save_wallet_software,
)
from export import build_csv
from validation import (
    DuplicateAddressPath,
    ValidationError,
    WalletSoftwareNameInUse,
    validate_acknowledgement,
    validate_health_check,
    validate_key_settings,
    validate_key_setup,
    validate_multisig_settings,
    validate_rotation,
    validate_wallet_software,
)


ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/setup": ("setup.html", "text/html; charset=utf-8"),
    "/settings": ("settings.html", "text/html; charset=utf-8"),
    "/health-check": ("health-check.html", "text/html; charset=utf-8"),
    "/history": ("history.html", "text/html; charset=utf-8"),
    "/login": ("login.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/setup.js": ("setup.js", "text/javascript; charset=utf-8"),
    "/settings.js": ("settings.js", "text/javascript; charset=utf-8"),
    "/health-check.js": ("health-check.js", "text/javascript; charset=utf-8"),
    "/history.js": ("history.js", "text/javascript; charset=utf-8"),
    "/session.js": ("session.js", "text/javascript; charset=utf-8"),
    "/login.js": ("login.js", "text/javascript; charset=utf-8"),
    "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
}
# The five application pages are served only to a signed-in user, and every API
# endpoint answers 401 without one. ``GET /health``, the login page, the two
# endpoints that establish a session, and the static assets stay open: StartOS
# polls /health and reports the service as unhealthy otherwise, and the login
# page has to be reachable before a session exists (section 31 point 1).
PROTECTED_PAGES = {"/", "/setup", "/settings", "/health-check", "/history"}
HEALTH_CHECK_PATH = re.compile(r"^/api/health-checks/([1-9][0-9]*)$")
ROTATE_PATH = re.compile(r"^/api/keys/([1-9][0-9]*)/rotate$")
# The export file is dated with the server's own date, so two downloads never
# look like the same report (section 31 point 3).
EXPORT_FILENAME_SUFFIX = "vardkey-export.csv"
MAX_REQUEST_BYTES = 262144
# Errors that mean the stored data cannot be served as it stands.
STORAGE_ERRORS = (OSError, sqlite3.Error, ValueError, RuntimeError)
# An alert is closed by the action that belongs to it, and the stored
# acknowledgement carries the action name as its reason (section 26.4). A
# rotation replaces the key, while the removal of a failing software from the
# settings closes the alerts that software raised (sections 26.3 and 26.7).
ROTATION_REASON = ROTATE
REMOVAL_REASON = REMOVE_SOFTWARE


def _cookie_header(name, value, max_age=None, http_only=True):
    """Return a ``Set-Cookie`` header value for one cookie.

    The session cookie is ``HttpOnly`` and ``SameSite=Strict``, so a script
    cannot read it and another site cannot send it (section 31 point 1). The
    CSRF cookie is deliberately readable, because the page has to copy it into
    the request header, and it is compared with that header on every
    state-changing POST. Neither is marked ``Secure``: StartOS terminates TLS
    and proxies plain HTTP into the container, and a ``Secure`` cookie would be
    dropped on ``http://localhost``.
    """
    jar = SimpleCookie()
    jar[name] = value
    morsel = jar[name]
    morsel["path"] = "/"
    morsel["samesite"] = "Strict"
    if http_only:
        morsel["httponly"] = True
    if max_age is not None:
        morsel["max-age"] = int(max_age)
    return morsel.OutputString()


def get_database_path():
    """Return the configured SQLite database path."""
    return os.environ.get("DATABASE_PATH", "data/vardkey.sqlite3")


def export_filename(now=None):
    """Return the dated export filename the server sends (section 31 point 3).

    The date is the server's own, taken when the download is answered, so the
    name is ``YYYY-MM-DD-vardkey-export.csv``.
    """
    today = (now or datetime.now()).date()
    return f"{today.isoformat()}-{EXPORT_FILENAME_SUFFIX}"


def cloud_key_names(keys):
    """Return the configured names of the cloud keys.

    A cloud key offers its own name as a wallet software choice, so the alert
    rules need these names to tell the two forms of ``software_incompatible``
    apart (section 27).
    """
    return tuple(key["name"] for key in keys if key["type"] == "cloud")


def closed_alerts(acknowledgements):
    """Return the closures that belong to a key, ready for the history view.

    A closure is shown when it carries a key id: a rotation, a replaced hardware,
    an updated contact, and an ignored alert whose source is a key. A closure of
    a software alert is left out, because it belongs to the settings list rather
    than to the checked key (section 27).
    """
    return [
        {
            "code": entry["code"],
            "source": entry["source"],
            "action": entry["reason"],
            "acknowledged_at": entry["acknowledged_at"],
        }
        for entry in acknowledgements
        if entry.get("key_id") is not None
    ]


def newest_alert_check_id(records, code, source, cloud_names=()):
    """Return the id of the newest check that raised one alert, or None.

    The acknowledgement stores this id, so a newer check for the same code and
    source raises the alert again (section 25.3). ``cloud_names`` has to be the
    same list the caller passed to ``collect_alerts``, because the source of a
    software alert depends on it: a source that is built differently finds no
    check, and an acknowledgement without a check id hides nothing, so the alert
    could never be closed (section 27).
    """
    newest = None
    for record in records:
        check_id = record.get("id")
        if check_id is None:
            continue
        for alert in build_alerts(record, cloud_names):
            if alert["code"] != code or alert["source"] != source:
                continue
            if newest is None or check_id > newest:
                newest = check_id
    return newest


def blocking_alert(alerts, key_id):
    """Return the open alert that blocks a key, or None.

    A key with an open alert cannot get a new check until the alert is closed
    (section 26.1). The alert is returned, so the caller can name it in the
    answer.
    """
    for alert in alerts:
        if alert.get("key_id") == key_id:
            return alert
    return None


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the pages, key profiles, saved checks, alerts, and the health endpoint."""
        path = urlsplit(self.path).path
        # The readiness endpoint stays open, because StartOS polls it and
        # reports the service as unhealthy otherwise (section 31 point 1).
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        # The login step is open too: the page and the two endpoints that
        # establish a session are what a request without one needs.
        if path == "/api/session":
            self._send_session()
            return
        if path == "/login":
            self._serve_static(*STATIC_FILES["/login"])
            return
        if path in PROTECTED_PAGES or path.startswith("/api/"):
            if not self._require_session(path):
                return
        if path == "/api/setup":
            self._send_setup()
            return
        if path == "/api/keys":
            self._send_keys()
            return
        if path == "/api/key-status":
            self._send_key_status()
            return
        if path == "/api/previous-values":
            self._send_previous_values()
            return
        if path == "/api/settings":
            self._send_settings()
            return
        if path == "/api/health-checks":
            self._send_health_check_list()
            return
        if path == "/api/alerts":
            self._send_alerts()
            return
        if path == "/api/export":
            self._send_export()
            return

        detail = HEALTH_CHECK_PATH.match(path)
        if detail:
            self._send_health_check(int(detail.group(1)))
            return

        asset = STATIC_FILES.get(path)
        if asset is None:
            self.send_error(404, "Not Found")
            return

        self._serve_static(*asset)

    def do_POST(self):
        """Store the key setup once, one health check, or one settings change."""
        path = urlsplit(self.path).path
        # Creating the admin and signing in are the two POSTs that run before a
        # session exists, so they cannot require one (section 31 point 1).
        if path == "/api/admin":
            self._create_admin()
            return
        if path == "/api/login":
            self._login()
            return
        if not self._require_session(path):
            return
        # Every other POST changes state, so it needs the double-submit CSRF
        # token as well, or another site could post for the signed-in user
        # (section 31 point 1).
        if not self._csrf_ok():
            self._send_json(403, {"error": "The CSRF token is missing or invalid"})
            return
        if path == "/api/logout":
            self._logout()
            return
        if path == "/api/setup":
            self._save_setup()
            return
        if path == "/api/health-checks":
            self._save_health_check()
            return
        if path == "/api/settings/keys":
            self._save_key_settings()
            return
        if path == "/api/settings/wallet-software":
            self._save_wallet_software()
            return
        if path == "/api/alerts/acknowledge":
            self._acknowledge_alert()
            return

        rotation = ROTATE_PATH.match(path)
        if rotation:
            self._rotate_key(int(rotation.group(1)))
            return

        self.send_error(404, "Not Found")

    # -- sessions, cookies, and CSRF --------------------------------------

    def _cookie_value(self, name):
        """Return one cookie from the request, or None."""
        header = self.headers.get("Cookie")
        if not header:
            return None
        jar = SimpleCookie()
        try:
            jar.load(header)
        except CookieError:
            return None
        morsel = jar.get(name)
        return morsel.value if morsel is not None else None

    def _session_valid(self):
        """Return True when the request carries a signed, unexpired session."""
        token = self._cookie_value(SESSION_COOKIE)
        if not token:
            return False
        try:
            return verify_session_token(token, get_database_path())
        except STORAGE_ERRORS:
            return False

    def _csrf_ok(self):
        """Return True when the CSRF cookie and the CSRF header are the same token."""
        return csrf_tokens_match(
            self._cookie_value(CSRF_COOKIE), self.headers.get(CSRF_HEADER)
        )

    def _require_session(self, path):
        """Answer a request that has no session, and report whether to stop.

        A page redirects to the login page, while an API call answers ``401``
        (section 31 point 1). A broken database is a failed session, so the
        request is refused rather than served.
        """
        if self._session_valid():
            return True
        if path.startswith("/api/"):
            self._send_json(401, {"error": "Authentication required"})
        else:
            self._redirect("/login")
        return False

    def _session_cookies(self, database_path):
        """Return the session and CSRF ``Set-Cookie`` headers of a new session."""
        return (
            _cookie_header(
                SESSION_COOKIE,
                create_session_token(database_path),
                max_age=SESSION_TTL_SECONDS,
            ),
            _cookie_header(
                CSRF_COOKIE,
                new_csrf_token(),
                max_age=SESSION_TTL_SECONDS,
                http_only=False,
            ),
        )

    def _send_session(self):
        """Report whether an admin exists and whether this request is signed in.

        The login page reads this before it shows either form, so it is open
        like the login step itself (section 31 point 1).
        """
        try:
            configured = admin_configured(get_database_path())
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The admin state is unavailable"})
            return
        self._send_json(200, {
            "admin_configured": configured,
            "authenticated": self._session_valid(),
        })

    def _create_admin(self):
        """Create the single admin account, once, on the first run.

        The first run has no admin, so the app shows the create-admin step
        instead of the login form, and the step cannot be skipped because every
        other route needs a session (section 31 point 1).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            if admin_configured(database_path):
                self._send_json(409, {"error": "An admin is already configured"})
                return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The admin state is unavailable"})
            return

        try:
            username, password = validate_admin_credentials(payload)
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        try:
            set_admin(username, password, database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The admin could not be stored"})
            return

        self._send_json(
            201,
            {"configured": True, "username": username},
            cookies=self._session_cookies(database_path),
        )

    def _login(self):
        """Sign in with the stored admin credential and start a session."""
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            if not admin_configured(database_path):
                self._send_json(409, {"error": "No admin is configured yet"})
                return
            username = payload.get("username") if isinstance(payload, dict) else None
            password = payload.get("password") if isinstance(payload, dict) else None
            signed_in = authenticate(username, password, database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The login could not be checked"})
            return

        if not signed_in:
            self._send_json(401, {"error": "Invalid username or password"})
            return

        self._send_json(
            200,
            {"authenticated": True},
            cookies=self._session_cookies(database_path),
        )

    def _logout(self):
        """End the session and clear both cookies."""
        self._send_json(
            200,
            {"authenticated": False},
            cookies=(
                _cookie_header(SESSION_COOKIE, "", max_age=0),
                _cookie_header(CSRF_COOKIE, "", max_age=0, http_only=False),
            ),
        )

    # -- health checks, setup, settings, and alerts -----------------------

    def _save_setup(self):
        """Store the key setup once, because the names, types, and paths are locked.

        A new database has no key rows yet, so the first-run setup step is the
        only way they are written (section 23.2). The address path is part of the
        setup and is locked with the rest, and no two keys may share one
        (sections 25.1 and 26.2). The setup also carries the multisig threshold
        and the number of key slots, which decide how many keys are configured
        (section 31 point 7), and the optional model of each key
        (section 31 point 5).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            existing = list_keys(database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key setup is unavailable"})
            return
        if existing:
            self._send_json(409, {"error": "The key setup is already stored"})
            return

        try:
            entries = validate_key_setup(payload)
            threshold, key_count = validate_multisig_settings(payload)
            save_key_setup(
                entries, database_path, threshold=threshold, key_count=key_count
            )
            keys = list_keys(database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key setup could not be saved"})
            return

        self._send_json(201, {"configured": True, "keys": keys})

    def _save_health_check(self):
        """Store one validated health check for a single selected key.

        A key with an open alert cannot get a new check, and the rule is enforced
        here as well as in the form, so a direct API call cannot bypass it
        (section 26.1).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            blocked = self._blocking_alert(payload, keys, database_path)
            if blocked is not None:
                self._send_json(409, {
                    "error": (
                        f"This key has an open alert ({blocked['code']}). "
                        "Close the alert before recording a new check."
                    )
                })
                return
            # The wallet software choices are the settings list and the name of
            # every configured cloud key (section 25.4).
            software_names = list_wallet_software(database_path)
            data = validate_health_check(payload, keys, software_names)
            health_check_id = save_health_check(data, database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The health check could not be saved"})
            return

        self._send_json(201, {"id": health_check_id})

    def _blocking_alert(self, payload, keys, database_path):
        """Return the open alert that blocks the submitted key, or None.

        The key id is read straight from the payload, so the rule is applied
        before the rest of the submission is validated and a blocked key always
        answers ``409``. The contact alert belongs to its key as well, so it
        blocks that key too (section 27). A payload without a usable key id is
        left to validation, which reports it as a ``400`` (section 26.1).
        """
        entry = payload.get("key_check") if isinstance(payload, dict) else None
        key_id = entry.get("key_id") if isinstance(entry, dict) else None
        if isinstance(key_id, bool) or not isinstance(key_id, int):
            return None
        records = self._health_check_records(database_path)
        acknowledgements = list_alert_acknowledgements(database_path)
        alerts = collect_alerts(records, acknowledgements, cloud_key_names(keys))
        return blocking_alert(alerts, key_id)

    def _save_key_settings(self):
        """Store the name and the model of one key, and its path while it is unlocked.

        The name and the model are only labels. The address path is part of the
        key's identity, so it may only be changed while the key has no saved
        check, and it may never belong to another key (sections 25.1, 25.2, 26.2
        and 31.5). The type is never part of the payload, because only a rotation
        replaces the key (section 28).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            entry = validate_key_settings(payload, keys)
            stored = next(key for key in keys if key["id"] == entry["key_id"])
            locked = key_has_check(entry["key_id"], database_path)
            if locked and entry["address_path"] != (stored["address_path"] or "").strip():
                self._send_json(409, {
                    "error": "The address path is locked because this key has a saved check"
                })
                return
            save_key_settings(
                entry["key_id"],
                entry["name"],
                entry["address_path"],
                database_path,
                model=entry["model"],
            )
            settings = self._settings_payload(database_path)
        except DuplicateAddressPath as error:
            # The path already belongs to another key, which the settings answer
            # with 409 (section 26.2).
            self._send_json(409, {"error": str(error)})
            return
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key settings could not be saved"})
            return

        self._send_json(200, settings)

    def _save_wallet_software(self):
        """Replace the whole wallet software list (section 25.4).

        The list is stored whole, so removing an entry never touches a saved
        check: the selected software is kept as free text there. Removing an
        entry closes the alerts that software raised, because the failing
        software is gone from the settings (section 26.7).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            stored = list_wallet_software(database_path)
            names = validate_wallet_software(payload, keys)
            save_wallet_software(names, database_path)
            closed = self._close_removed_software(stored, names, keys, database_path)
            software = list_wallet_software(database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The wallet software list could not be saved"})
            return

        self._send_json(200, {
            "wallet_software": software,
            "acknowledged": [
                {"code": code, "source": source} for code, source, _ in closed
            ],
        })

    def _close_removed_software(self, stored, names, keys, database_path):
        """Close the alerts of the wallet software that was removed.

        A software alert is closed by removing the failing software from the
        settings, which is exactly what the alert offers (section 26.7). The
        stored acknowledgement carries the action name as its reason, and the key
        the alert belonged to, which is None for a software alert raised by the
        settings list (sections 26.4 and 27).
        """
        kept = {name.casefold() for name in names}
        removed = [name for name in stored if name.casefold() not in kept]
        if not removed:
            return []
        cloud_names = cloud_key_names(keys)
        records = self._health_check_records(database_path)
        acknowledgements = list_alert_acknowledgements(database_path)
        targets = software_alert_targets(records, acknowledgements, removed, cloud_names)
        for code, source, key_id in targets:
            save_alert_acknowledgement(
                code,
                source,
                key_id,
                newest_alert_check_id(records, code, source, cloud_names),
                REMOVAL_REASON,
                database_path,
            )
        return targets

    def _rotate_key(self, key_id):
        """Replace one key with a new one, keep or change its name, and close its alerts.

        The rotation replaces the key, so it requires a new, unique address path:
        the old path is refused, and no earlier check is changed (sections 26.2
        and 26.3). The replacement may also carry the other type, because a
        rotation is what replaces the key, and the type is part of its identity
        (section 28). The model is a label, so it is written when the payload
        carries one and the stored value is kept otherwise (section 31 point 5).
        The acknowledgement carries the key, so a rotation that changes the name
        still keeps the closed alerts closed (section 27).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The keys are unavailable"})
            return
        if not any(entry["id"] == key_id for entry in keys):
            self._send_json(404, {"error": "Key not found"})
            return

        try:
            # A key that becomes a cloud key may not take a name the wallet
            # software list already holds, so the rotation needs the list
            # (sections 25.4 and 28).
            software_names = list_wallet_software(database_path)
            rotation = validate_rotation(payload, keys, key_id, software_names)
            key = next(entry for entry in keys if entry["id"] == rotation["key_id"])
            cloud_names = cloud_key_names(keys)
            records = self._health_check_records(database_path)
            targets = rotation_alert_targets(records, key, cloud_names)
            # The model is only a label, so a rotation that does not mention it
            # keeps the stored one (section 31 point 5).
            model = rotation["model"] if "model" in payload else key.get("model")
            save_key_settings(
                key["id"],
                rotation["name"] or key["name"],
                rotation["address_path"],
                database_path,
                key_type=rotation["type"],
                model=model,
            )
            for code, source in targets:
                save_alert_acknowledgement(
                    code,
                    source,
                    key["id"],
                    newest_alert_check_id(records, code, source, cloud_names),
                    ROTATION_REASON,
                    database_path,
                )
            settings = self._settings_payload(database_path)
        except WalletSoftwareNameInUse as error:
            # The replacement would be a cloud key under a name the wallet
            # software list already holds, which the rotation answers with 409
            # (section 28).
            self._send_json(409, {"error": str(error)})
            return
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key could not be rotated"})
            return

        self._send_json(200, {
            "settings": settings,
            "acknowledged": [
                {"code": code, "source": source} for code, source in targets
            ],
        })

    def _acknowledge_alert(self):
        """Close one alert with the action that belongs to it.

        The action is stored as the reason, and the acknowledgement stores the
        newest check that raised the alert, so a newer check for the same code
        and source raises it again (sections 25.3 and 26.4). The key the alert
        belonged to is stored too, so the alert stays hidden across a rename
        (section 27).
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        try:
            entry = validate_acknowledgement(payload)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            cloud_names = cloud_key_names(keys)
            records = self._health_check_records(database_path)
            acknowledgements = list_alert_acknowledgements(database_path)
            alerts = collect_alerts(records, acknowledgements, cloud_names)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Alerts are unavailable"})
            return

        alert = next(
            (
                item for item in alerts
                if item["code"] == entry["code"] and item["source"] == entry["source"]
            ),
            None,
        )
        if alert is None:
            self._send_json(404, {"error": "Alert not found"})
            return
        # The action has to belong to the alert, so a control that this alert does
        # not offer cannot close it (section 26.4).
        if entry["action"] not in alert["actions"]:
            self._send_json(400, {
                "error": f"{entry['action']} does not close this alert"
            })
            return

        try:
            save_alert_acknowledgement(
                entry["code"],
                entry["source"],
                alert.get("key_id"),
                newest_alert_check_id(records, entry["code"], entry["source"], cloud_names),
                entry["action"],
                database_path,
            )
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The alert could not be acknowledged"})
            return

        self._send_json(201, {
            "acknowledged": True,
            "code": entry["code"],
            "source": entry["source"],
            "action": entry["action"],
        })

    def _send_setup(self):
        """Return whether the key setup is stored, the stored keys, and its shape.

        A database that holds only part of the setup is reported as an error, so
        it is never answered with the first-run setup step (section 23.2). The
        multisig threshold and key count are returned with the keys, so the setup
        page and the dashboard know how many key slots the single setup has
        (section 31 point 7).
        """
        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            multisig = get_multisig_settings(database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key setup is unavailable"})
            return
        self._send_json(200, {
            "configured": bool(keys),
            "threshold": multisig["threshold"],
            "key_count": multisig["key_count"],
            "keys": keys,
        })

    def _send_keys(self):
        try:
            self._send_json(200, list_keys(get_database_path()))
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Key profiles are unavailable"})

    def _send_key_status(self):
        """Return each key with the dates of its newest saved check."""
        try:
            self._send_json(200, list_key_status(get_database_path()))
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Key status is unavailable"})

    def _send_previous_values(self):
        """Return the last saved values, so the form can pre-fill itself."""
        try:
            self._send_json(200, list_previous_values(get_database_path()))
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Previous values are unavailable"})

    def _send_settings(self):
        """Return the keys with their address paths and the wallet software list.

        The settings page needs both, and the check form reads the wallet
        software list from here as well (section 25.4).
        """
        try:
            settings = self._settings_payload(get_database_path())
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The settings are unavailable"})
            return
        self._send_json(200, settings)

    def _settings_payload(self, database_path):
        """Return the keys with their settings and the wallet software list.

        ``has_checks`` tells the settings page whether the address path of a key
        is still editable, because the path is locked after the first saved check
        (section 25.1).
        """
        keys = list_keys(database_path)
        return {
            "keys": [
                {**key, "has_checks": key_has_check(key["id"], database_path)}
                for key in keys
            ],
            "wallet_software": list_wallet_software(database_path),
        }

    def _send_health_check_list(self):
        try:
            self._send_json(200, list_health_checks(get_database_path()))
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Saved health checks are unavailable"})

    def _send_alerts(self):
        """Return the merged follow-up alerts of every saved health check.

        Every saved check is read, so a warning is never lost when a newer check
        for another key is saved. Identical alerts are merged by
        ``collect_alerts``, and acknowledged alerts are left out until a newer
        check raises them again (sections 21 and 25.3). Every alert names the
        actions that close it and the software it is about, when it is about one
        (sections 26.4 and 26.7). The configured cloud key names are passed in,
        because a wallet software that carries one of them can never be removed
        from the settings (section 27).
        """
        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            records = self._health_check_records(database_path)
            acknowledgements = list_alert_acknowledgements(database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Alerts are unavailable"})
            return

        self._send_json(
            200, collect_alerts(records, acknowledgements, cloud_key_names(keys))
        )

    def _health_check_records(self, database_path):
        """Return every saved check with its related rows."""
        records = []
        for summary in list_health_checks(database_path):
            record = get_health_check(summary["id"], database_path)
            if record is not None:
                records.append(record)
        return records

    def _send_export(self):
        """Return every saved key check as a CSV download.

        The file is named with the server's date, so a download is identifiable
        and two downloads never carry the same name (section 31 point 3).
        """
        try:
            body = build_csv(list_export_rows(get_database_path())).encode("utf-8")
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The export is unavailable"})
            return

        filename = export_filename()
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_health_check(self, health_check_id):
        """Return one saved check with its related rows and the closures it has.

        A closure that belongs to a key is shown in the history, so the user can
        see what was closed on this check, with the action and the date
        (section 27).
        """
        database_path = get_database_path()
        try:
            record = get_health_check(health_check_id, database_path)
            if record is None:
                self._send_json(404, {"error": "Health check not found"})
                return
            record["closed_alerts"] = closed_alerts(
                list_alert_acknowledgements(database_path, check_id=health_check_id)
            )
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Saved health checks are unavailable"})
            return
        self._send_json(200, record)

    # -- request and response plumbing ------------------------------------

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Content-Length is not valid") from error
        if length <= 0:
            raise ValueError("a request body is required")
        if length > MAX_REQUEST_BYTES:
            raise ValueError("the request body is too large")

        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("the request body must be valid JSON") from error

    def _serve_static(self, filename, content_type):
        """Serve one file from ``static/`` as the response body."""
        try:
            body = (ROOT / "static" / filename).read_bytes()
        except OSError:
            self.send_error(500, "Application page unavailable")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location):
        """Answer with a redirect to another page."""
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(self, status, payload, cookies=()):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_security_headers()
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")


def main():
    database_path = get_database_path()
    initialize_database(database_path)

    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")

    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"VardKey listening on port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
