"""Tests for the installable PWA (section 31 point 6).

The service worker caches only the shell, the manifest describes the app, and
every page links the manifest. The icon is the retro SVG of section 32.1, served
with ``sizes: "any"``; the 192 and 512 px PNGs still need a rasterizer, and only
the manifest and its icons entry change when they arrive.
"""

from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from urllib.request import urlopen

from app import ROOT, STATIC_FILES, AppHandler
from database import initialize_database
from server_session import SessionMixin


class ServiceWorkerTests(unittest.TestCase):
    """The service worker is served, registered, and limited to the shell."""

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def read_static(self, filename):
        return (ROOT / "static" / filename).read_text(encoding="utf-8")

    def fetch_text(self, path):
        # /sw.js is a static asset, so it needs no session (section 31 point 1).
        with urlopen(f"{self.base_url}{path}") as response:
            self.assertEqual(response.status, 200)
            return response.read().decode("utf-8")

    def test_the_service_worker_is_served_from_the_root(self):
        # The scope of a service worker is bounded by its path, so it has to be
        # served from the root.
        body = self.fetch_text("/sw.js")

        self.assertIn("vardkey-shell", body)

    def test_the_service_worker_is_listed_in_static_files(self):
        self.assertIn("/sw.js", STATIC_FILES)

    def test_the_service_worker_never_caches_an_api_response(self):
        # An allowlist means the worker does not name the API, the health
        # endpoint or the login page at all, so none of them can ever be cached
        # (section 31 point 6).
        body = self.read_static("sw.js")

        self.assertNotIn("/api/", body)
        # The quoted path is what matters: "/health-check" is a shell path, while
        # "/health" and "/login" are not, and must not appear.
        self.assertNotIn('\"/health\"', body)
        self.assertNotIn('\"/login\"', body)
        # The shell it does cache is the five pages, their assets, and the two
        # files the browser reads when the app is installed.
        for path in (
            "/",
            "/setup",
            "/settings",
            "/health-check",
            "/history",
            "/styles.css",
            "/manifest.webmanifest",
            "/icon.svg",
        ):
            self.assertIn(f'"{path}"', body)

    def test_the_service_worker_only_stores_a_successful_same_origin_answer(self):
        # A page fetched without a session answers 302 -> /login, and fetch
        # follows it, so the login page would replace the cached shell unless the
        # stored answer is checked first. The worker stores a response only when
        # it is successful, same-origin and not redirected (section 31 point 6).
        body = self.read_static("sw.js")

        self.assertIn("isCacheable", body)
        self.assertIn("response.ok", body)
        self.assertIn("response.type", body)
        self.assertIn("!response.redirected", body)

    def test_the_dashboard_registers_the_service_worker(self):
        body = self.read_static("app.js")

        self.assertIn('serviceWorker.register("/sw.js")', body)

    def test_the_dashboard_shows_an_offline_state(self):
        # The shell may come from the cache while every fetch fails, so the UI
        # says so plainly instead of leaving empty cards (section 31 point 6).
        body = self.read_static("app.js")

        self.assertIn('addEventListener("offline"', body)
        self.assertIn("You are offline", body)


class ManifestTests(SessionMixin, unittest.TestCase):
    """The manifest and the icon that make the app installable."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        self.previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.database_path

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        # The manifest and the icon are open, but the page test below reads the
        # five pages, and those need a session (section 31 point 1). Without
        # one the server redirects to the login page and urllib follows it, so
        # the assertion would read the login page's HTML instead.
        self.authenticate()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def fetch_text(self, path):
        with self.get(path) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode("utf-8")

    def test_the_manifest_is_served_and_describes_the_app(self):
        body = self.fetch_text("/manifest.webmanifest")
        manifest = json.loads(body)

        self.assertEqual(manifest["name"], "VardKey")
        self.assertEqual(manifest["short_name"], "VardKey")
        self.assertEqual(manifest["description"], "Bitcoin Multisig Health Monitor")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["display"], "standalone")
        # The colours are the ones the pages already declare in their
        # theme-color meta and use as the page background. They follow the retro
        # theme of section 32.2, so the two move together with the stylesheet.
        self.assertEqual(manifest["theme_color"], "#c0c0c0")
        self.assertEqual(manifest["background_color"], "#c0c0c0")
        self.assertTrue(manifest["icons"])

    def test_the_manifest_lists_the_served_icon(self):
        manifest = json.loads(self.fetch_text("/manifest.webmanifest"))

        entry = manifest["icons"][0]
        self.assertEqual(entry["src"], "/icon.svg")
        self.assertEqual(entry["type"], "image/svg+xml")
        # The icon is served, so the manifest never points at a 404.
        self.assertIn("svg", self.fetch_text(entry["src"]))

    def test_the_manifest_and_the_icon_are_listed_in_static_files(self):
        # A file that is not listed answers 404, which would make the app
        # uninstallable without failing a single page test.
        self.assertIn("/manifest.webmanifest", STATIC_FILES)
        self.assertIn("/icon.svg", STATIC_FILES)

    def test_every_page_links_the_manifest(self):
        for path in ("/", "/setup", "/settings", "/health-check", "/history"):
            body = self.fetch_text(path)
            self.assertIn('<link rel="manifest" href="/manifest.webmanifest">', body)


if __name__ == "__main__":
    unittest.main()
