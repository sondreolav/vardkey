"""Minimal HTTP server for the Helsesjekk dashboard."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from alerts import build_alerts, collect_alerts, rotation_alert_targets
from database import (
    get_health_check,
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
    ValidationError,
    validate_acknowledgement,
    validate_health_check,
    validate_key_settings,
    validate_key_setup,
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
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/setup.js": ("setup.js", "text/javascript; charset=utf-8"),
    "/settings.js": ("settings.js", "text/javascript; charset=utf-8"),
    "/health-check.js": ("health-check.js", "text/javascript; charset=utf-8"),
    "/history.js": ("history.js", "text/javascript; charset=utf-8"),
}
HEALTH_CHECK_PATH = re.compile(r"^/api/health-checks/([1-9][0-9]*)$")
ROTATE_PATH = re.compile(r"^/api/keys/([1-9][0-9]*)/rotate$")
EXPORT_FILENAME = "helsesjekk-export.csv"
MAX_REQUEST_BYTES = 262144
# Errors that mean the stored data cannot be served as it stands.
STORAGE_ERRORS = (OSError, sqlite3.Error, ValueError, RuntimeError)
# A rotation closes the alerts of the key it replaces, so the acknowledgement it
# writes carries the reason it was closed (sections 25.2 and 25.3).
ROTATION_REASON = "The key was replaced by a rotation, so this alert was closed."


def get_database_path():
    """Return the configured SQLite database path."""
    return os.environ.get("DATABASE_PATH", "data/helsesjekk.sqlite3")


def newest_alert_check_id(records, code, source):
    """Return the id of the newest check that raised one alert, or None.

    The acknowledgement stores this id, so a newer check for the same code and
    source raises the alert again (section 25.3).
    """
    newest = None
    for record in records:
        check_id = record.get("id")
        if check_id is None:
            continue
        for alert in build_alerts(record):
            if alert["code"] != code or alert["source"] != source:
                continue
            if newest is None or check_id > newest:
                newest = check_id
    return newest


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the pages, key profiles, saved checks, alerts, and the health endpoint."""
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok"})
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

        filename, content_type = asset
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

    def do_POST(self):
        """Store the key setup once, one health check, or one settings change."""
        path = urlsplit(self.path).path
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

    def _save_setup(self):
        """Store the key setup once, because the names and types are locked.

        A new database has no key rows yet, so the first-run setup step is the
        only way they are written (section 23.2). The address path is part of the
        setup and is locked with the rest (section 25.1).
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
            save_key_setup(entries, database_path)
            keys = list_keys(database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key setup could not be saved"})
            return

        self._send_json(201, {"configured": True, "keys": keys})

    def _save_health_check(self):
        """Store one validated health check for a single selected key."""
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
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

    def _save_key_settings(self):
        """Store the name of one key, and its address path while it is unlocked.

        The name is only a label. The address path is part of the key's identity,
        so it may only be changed while the key has no saved check
        (sections 25.1 and 25.2).
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
                entry["key_id"], entry["name"], entry["address_path"], database_path
            )
            settings = self._settings_payload(database_path)
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
        check: the selected software is kept as free text there.
        """
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            names = validate_wallet_software(payload, keys)
            save_wallet_software(names, database_path)
            software = list_wallet_software(database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The wallet software list could not be saved"})
            return

        self._send_json(200, {"wallet_software": software})

    def _rotate_key(self, key_id):
        """Replace one key, keep or change its name, and close its alerts.

        The type and the address path are locked, and no earlier check is
        changed (section 25.2).
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
            rotation = validate_rotation(payload, keys, key_id)
            key = next(entry for entry in keys if entry["id"] == rotation["key_id"])
            records = self._health_check_records(database_path)
            targets = rotation_alert_targets(records, key)
            save_key_settings(
                key["id"],
                rotation["name"] or key["name"],
                key["address_path"],
                database_path,
            )
            for code, source in targets:
                save_alert_acknowledgement(
                    code,
                    source,
                    newest_alert_check_id(records, code, source),
                    ROTATION_REASON,
                    database_path,
                )
            settings = self._settings_payload(database_path)
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
        """Close one alert until a newer check for the same code and source.

        The acknowledgement stores the newest check that raised the alert, so a
        newer check raises it again (section 25.3).
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
            records = self._health_check_records(database_path)
            acknowledgements = list_alert_acknowledgements(database_path)
            alerts = collect_alerts(records, acknowledgements)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Alerts are unavailable"})
            return

        active = any(
            alert["code"] == entry["code"] and alert["source"] == entry["source"]
            for alert in alerts
        )
        if not active:
            self._send_json(404, {"error": "Alert not found"})
            return

        try:
            save_alert_acknowledgement(
                entry["code"],
                entry["source"],
                newest_alert_check_id(records, entry["code"], entry["source"]),
                entry["reason"],
                database_path,
            )
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The alert could not be acknowledged"})
            return

        self._send_json(201, {
            "acknowledged": True,
            "code": entry["code"],
            "source": entry["source"],
        })

    def _send_setup(self):
        """Return whether the key setup is stored, together with the stored keys.

        A database that holds only part of the setup is reported as an error, so
        it is never answered with the first-run setup step (section 23.2).
        """
        try:
            keys = list_keys(get_database_path())
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The key setup is unavailable"})
            return
        self._send_json(200, {"configured": bool(keys), "keys": keys})

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
        check raises them again (sections 21 and 25.3).
        """
        database_path = get_database_path()
        try:
            records = self._health_check_records(database_path)
            acknowledgements = list_alert_acknowledgements(database_path)
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Alerts are unavailable"})
            return

        self._send_json(200, collect_alerts(records, acknowledgements))

    def _health_check_records(self, database_path):
        """Return every saved check with its related rows."""
        records = []
        for summary in list_health_checks(database_path):
            record = get_health_check(summary["id"], database_path)
            if record is not None:
                records.append(record)
        return records

    def _send_export(self):
        """Return every saved key check as a CSV download."""
        try:
            body = build_csv(list_export_rows(get_database_path())).encode("utf-8")
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "The export is unavailable"})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{EXPORT_FILENAME}"')
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_health_check(self, health_check_id):
        try:
            record = get_health_check(health_check_id, get_database_path())
        except STORAGE_ERRORS:
            self._send_json(500, {"error": "Saved health checks are unavailable"})
            return
        if record is None:
            self._send_json(404, {"error": "Health check not found"})
            return
        self._send_json(200, record)

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

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_security_headers()
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
    print(f"Helsesjekk listening on port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
