"""Tests for the admin credential, the signed session, and the CSRF token.

The password is stored only as a scrypt hash with a random salt per password,
the session is a signed cookie with no session table, and the CSRF token is a
double-submit value (section 31 point 1).
"""

from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest

from auth import (
    admin_configured,
    authenticate,
    create_session_token,
    csrf_tokens_match,
    get_admin,
    hash_password,
    new_csrf_token,
    session_secret,
    set_admin,
    verify_password,
    verify_session_token,
)
from database import initialize_database


class PasswordTests(unittest.TestCase):
    def test_a_password_round_trips_through_its_hash(self):
        stored = hash_password("correct horse battery staple")

        self.assertTrue(stored.startswith("scrypt$"))
        self.assertTrue(verify_password("correct horse battery staple", stored))
        self.assertFalse(verify_password("wrong password", stored))

    def test_two_hashes_of_the_same_password_differ(self):
        # The salt is random per password, so equal passwords never share a hash
        # (section 31 point 1).
        first = hash_password("same password")
        second = hash_password("same password")

        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("same password", first))
        self.assertTrue(verify_password("same password", second))

    def test_the_stored_hash_never_contains_the_password(self):
        stored = hash_password("hunter2")

        self.assertNotIn("hunter2", stored)

    def test_a_malformed_or_missing_hash_is_a_failed_match(self):
        # A broken row is never turned into a traceback (section 31 point 1).
        for stored in (None, "", "not-a-hash", "scrypt$1$2$3", "md5$aa$bb$cc$dd$ee", 12):
            self.assertFalse(verify_password("hunter2", stored))

        self.assertFalse(verify_password(None, hash_password("hunter2")))


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_a_new_database_has_no_admin(self):
        self.assertFalse(admin_configured(self.database_path))
        self.assertEqual(get_admin(self.database_path), (None, None))
        self.assertFalse(authenticate("admin", "anything", self.database_path))

    def test_the_admin_is_stored_and_authenticated(self):
        set_admin("admin", "s3cret", self.database_path)

        self.assertTrue(admin_configured(self.database_path))
        username, password_hash = get_admin(self.database_path)
        self.assertEqual(username, "admin")
        self.assertTrue(password_hash.startswith("scrypt$"))
        self.assertTrue(authenticate("admin", "s3cret", self.database_path))

    def test_a_wrong_username_or_password_is_refused(self):
        set_admin("admin", "s3cret", self.database_path)

        self.assertFalse(authenticate("root", "s3cret", self.database_path))
        self.assertFalse(authenticate("admin", "wrong", self.database_path))
        self.assertFalse(authenticate(None, "s3cret", self.database_path))
        self.assertFalse(authenticate("admin", None, self.database_path))

    def test_setting_the_admin_again_replaces_the_credential(self):
        set_admin("admin", "first", self.database_path)
        set_admin("keeper", "second", self.database_path)

        self.assertTrue(authenticate("keeper", "second", self.database_path))
        self.assertFalse(authenticate("admin", "first", self.database_path))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_a_token_verifies_and_a_tampered_one_does_not(self):
        token = create_session_token(self.database_path)

        self.assertTrue(verify_session_token(token, self.database_path))
        self.assertFalse(verify_session_token(f"{token}x", self.database_path))
        self.assertFalse(verify_session_token("", self.database_path))
        self.assertFalse(verify_session_token(None, self.database_path))
        self.assertFalse(verify_session_token("no-dot", self.database_path))

    def test_a_token_expires(self):
        now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
        token = create_session_token(self.database_path, now)

        self.assertTrue(verify_session_token(token, self.database_path, now))
        # The token is valid for a month, and not for two.
        self.assertTrue(
            verify_session_token(
                token, self.database_path, now + timedelta(days=29)
            )
        )
        self.assertFalse(
            verify_session_token(
                token, self.database_path, now + timedelta(days=31)
            )
        )

    def test_the_secret_is_generated_once_and_kept(self):
        # The session survives a restart because the secret is stored, and no
        # session table exists (section 31 point 1).
        secret = session_secret(self.database_path)
        token = create_session_token(self.database_path)

        self.assertEqual(secret, session_secret(self.database_path))
        self.assertTrue(verify_session_token(token, self.database_path))

    def test_a_token_signed_with_another_secret_is_refused(self):
        other = os.path.join(self.temp_dir.name, "other.sqlite3")
        initialize_database(other)
        token = create_session_token(other)

        self.assertFalse(verify_session_token(token, self.database_path))


class CsrfTests(unittest.TestCase):
    def test_only_two_equal_tokens_match(self):
        token = new_csrf_token()

        self.assertTrue(csrf_tokens_match(token, token))
        self.assertFalse(csrf_tokens_match(token, new_csrf_token()))
        self.assertFalse(csrf_tokens_match(token, None))
        self.assertFalse(csrf_tokens_match(None, token))
        self.assertFalse(csrf_tokens_match("", ""))
        self.assertFalse(csrf_tokens_match(token, 12))


if __name__ == "__main__":
    unittest.main()
