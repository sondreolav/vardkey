"""Shared session handling for the server test cases.

Section 31 point 1 puts every route except ``GET /health`` behind an admin
session, so a test module that talks to the server signs in once and sends the
session and CSRF cookies with every request, exactly as the browser does.

``tests/test_app.py`` has its own, larger ``ServerTestCase``; this module is the
smaller helper the other server test modules share. A class that uses the mixin
sets ``self.base_url`` and ``self.database_path`` in its own ``setUp`` and then
calls ``authenticate()``.
"""

from http.cookies import SimpleCookie
import json
from urllib.request import Request, urlopen

from auth import CSRF_COOKIE, CSRF_HEADER, set_admin


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "test-password"


class SessionMixin:
    """Sign in through the API and carry the cookies on every request."""

    def authenticate(self):
        """Store the admin, sign in, and keep the session and CSRF cookies.

        The session secret lives in the database, so a test that switches
        ``DATABASE_PATH`` to another file has to call this again for that file,
        or its cookie is signed with the wrong secret.
        """
        self.cookies = {}
        set_admin(ADMIN_USERNAME, ADMIN_PASSWORD, self.database_path)
        request = self.request(
            "/api/login",
            method="POST",
            payload={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        with urlopen(request) as response:
            if response.status != 200:
                raise AssertionError(f"The sign-in answered {response.status}")
            self._remember_cookies(response)
        return self.cookies

    def _remember_cookies(self, response):
        for header in response.headers.get_all("Set-Cookie") or []:
            jar = SimpleCookie()
            jar.load(header)
            for name, morsel in jar.items():
                self.cookies[name] = morsel.value

    def cookie_header(self):
        return "; ".join(f"{name}={value}" for name, value in self.cookies.items())

    def request(self, path, method="GET", payload=None):
        """Build a request that carries the session and the CSRF token."""
        headers = {"Accept": "application/json"}
        if self.cookies:
            headers["Cookie"] = self.cookie_header()
        if method == "POST" and self.cookies.get(CSRF_COOKIE):
            headers[CSRF_HEADER] = self.cookies[CSRF_COOKIE]
        if payload is not None:
            headers["Content-Type"] = "application/json"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        return Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

    def get(self, path):
        return urlopen(self.request(path))

    def get_json(self, path):
        with self.get(path) as response:
            if response.status != 200:
                raise AssertionError(f"{path} answered {response.status}")
            return json.load(response)

    def post_json(self, path, payload):
        return urlopen(self.request(path, method="POST", payload=payload))
