"""Minimal HTTP server for the Helsesjekk dashboard."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from alerts import build_alerts
from database import (
    get_health_check,
    initialize_database,
    list_export_rows,
    list_health_checks,
    list_key_status,
    list_keys,
    save_health_check,
    seed_fixed_keys,
)
from export import build_csv
from validation import ValidationError, validate_health_check


ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/health-check": ("health-check.html", "text/html; charset=utf-8"),
    "/history": ("history.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/health-check.js": ("health-check.js", "text/javascript; charset=utf-8"),
    "/history.js": ("history.js", "text/javascript; charset=utf-8"),
}
HEALTH_CHECK_PATH = re.compile(r"^/api/health-checks/([1-9][0-9]*)$")
EXPORT_FILENAME = "helsesjekk-export.csv"
MAX_REQUEST_BYTES = 262144


def get_database_path():
    """Return the configured SQLite database path."""
    return os.environ.get("DATABASE_PATH", "data/helsesjekk.sqlite3")


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the pages, key profiles, saved checks, alerts, and the health endpoint."""
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if path == "/api/keys":
            self._send_keys()
            return
        if path == "/api/key-status":
            self._send_key_status()
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
        """Store one validated health check for a single selected key."""
        path = urlsplit(self.path).path
        if path != "/api/health-checks":
            self.send_error(404, "Not Found")
            return

        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return

        database_path = get_database_path()
        try:
            keys = list_keys(database_path)
            data = validate_health_check(payload, keys)
            health_check_id = save_health_check(data, database_path)
        except ValidationError as error:
            self._send_json(400, {"error": str(error)})
            return
        except (OSError, sqlite3.Error, ValueError):
            self._send_json(500, {"error": "The health check could not be saved"})
            return

        self._send_json(201, {"id": health_check_id})

    def _send_keys(self):
        try:
            self._send_json(200, list_keys(get_database_path()))
        except (OSError, sqlite3.Error, ValueError):
            self._send_json(500, {"error": "Key profiles are unavailable"})

    def _send_key_status(self):
        """Return each key with the dates of its newest saved check."""
        try:
            self._send_json(200, list_key_status(get_database_path()))
        except (OSError, sqlite3.Error, ValueError):
            self._send_json(500, {"error": "Key status is unavailable"})

    def _send_health_check_list(self):
        try:
            self._send_json(200, list_health_checks(get_database_path()))
        except (OSError, sqlite3.Error, ValueError):
            self._send_json(500, {"error": "Saved health checks are unavailable"})

    def _send_alerts(self):
        """Return the follow-up alerts of the most recent saved health check."""
        database_path = get_database_path()
        try:
            summaries = list_health_checks(database_path)
            if not summaries:
                self._send_json(200, [])
                return
            record = get_health_check(summaries[0]["id"], database_path)
        except (OSError, sqlite3.Error, ValueError):
            self._send_json(500, {"error": "Alerts are unavailable"})
            return

        self._send_json(200, build_alerts(record) if record else [])

    def _send_export(self):
        """Return every saved key check as a CSV download."""
        try:
            body = build_csv(list_export_rows(get_database_path())).encode("utf-8")
        except (OSError, sqlite3.Error, ValueError):
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
        except (OSError, sqlite3.Error, ValueError):
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
    seed_fixed_keys(database_path)

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
