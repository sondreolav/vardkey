"""Minimal HTTP server for the Helsesjekk dashboard."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from database import initialize_database, list_keys, seed_fixed_keys


ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/health-check": ("health-check.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/health-check.js": ("health-check.js", "text/javascript; charset=utf-8"),
}


def get_database_path():
    """Return the configured SQLite database path."""
    return os.environ.get("DATABASE_PATH", "data/helsesjekk.sqlite3")


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the dashboard, check form, key profiles, and health endpoint."""
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if path == "/api/keys":
            try:
                self._send_json(200, list_keys(get_database_path()))
            except (OSError, sqlite3.Error, ValueError):
                self._send_json(500, {"error": "Key profiles are unavailable"})
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
