"""Tests for the installable PWA shell (section 31 point 6).

Only the service worker is in place so far: the manifest and the PWA icons wait
for the artwork of section 31 point 8, because the manifest needs a 192 and a
512 px icon. The worker must cache only the shell, so it never names an API
route, the health endpoint or the login page at all.
"""

from http.server import ThreadingHTTPServer
import threading
import unittest
from urllib.request import urlopen

from app import ROOT, STATIC_FILES, AppHandler


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

    def test_the_service_worker_is_served_from_the_root(self):
        # The scope of a service worker is bounded by its path, so it has to be
        # served from the root.
        with urlopen(f"{self.base_url}/sw.js") as response:
            body = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
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
        self.assertNotIn('"/health"', body)
        self.assertNotIn('"/login"', body)
        # The shell it does cache is the five pages and their assets.
        for path in ("/", "/setup", "/settings", "/health-check", "/history", "/styles.css"):
            self.assertIn(f'"{path}"', body)

    def test_the_dashboard_registers_the_service_worker(self):
        body = self.read_static("app.js")

        self.assertIn('serviceWorker.register("/sw.js")', body)

    def test_the_dashboard_shows_an_offline_state(self):
        # The shell may come from the cache while every fetch fails, so the UI
        # says so plainly instead of leaving empty cards (section 31 point 6).
        body = self.read_static("app.js")

        self.assertIn('addEventListener("offline"', body)
        self.assertIn("You are offline", body)


if __name__ == "__main__":
    unittest.main()
