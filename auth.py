"""Admin credentials, signed sessions, and CSRF tokens for VardKey.

Section 31 point 1 puts the whole app behind an admin login. This module is the
only place that knows how the credential is stored and how a session is proven:

- The password is stored **only** as a ``hashlib.scrypt`` hash with a random
  salt per password, and compared with ``hmac.compare_digest``. No hand-written
  cryptography is involved, and the admin password is the only credential the
  app stores — it is an app login, not a wallet secret.
- A session is a signed cookie: HMAC-SHA256 over an expiry timestamp, keyed by a
  ``session_secret`` that is generated once and kept in ``app_settings``. There
  is no session table, so a session survives a restart.
- A CSRF token is a double-submit value: the same random token in a readable
  cookie and in a request header, compared with ``hmac.compare_digest``.

The three settings live in the ``app_settings`` table from section 31 point 7,
so no new table is needed.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from database import get_app_settings, save_app_settings


ADMIN_USERNAME_SETTING = "admin_username"
ADMIN_PASSWORD_HASH_SETTING = "admin_password_hash"
SESSION_SECRET_SETTING = "session_secret"

SESSION_COOKIE = "vardkey_session"
CSRF_COOKIE = "vardkey_csrf"
CSRF_HEADER = "X-CSRF-Token"

# A month is long enough that the single local user is not asked to log in again
# on every visit, and the cookie is still bounded.
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60

# The bounds of the admin account. The username is a label; the password is the
# only credential the app stores, and a short one is the easiest way to lose the
# protection the login adds, so a minimum length is enforced on the server and
# not only in the form (sections 15 and 31 point 1).
ADMIN_USERNAME_MAX_LENGTH = 60
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 200

# ``hashlib.scrypt`` parameters. The salt is random per password, so two equal
# passwords never share a hash. 2**14 needs 16 MiB, which is inside OpenSSL's
# default memory limit.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16
SCRYPT_PREFIX = "scrypt"


def hash_password(password):
    """Return a self-describing scrypt hash for the password.

    The stored value carries its own parameters and salt, so the format can be
    changed later without invalidating an existing password.
    """
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return (
        f"{SCRYPT_PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(password, stored):
    """Return True when the password matches the stored hash.

    A malformed stored value is a failed match, never an error, so a broken row
    cannot be turned into a traceback.
    """
    if not isinstance(stored, str) or not isinstance(password, str):
        return False
    parts = stored.split("$")
    if len(parts) != 6 or parts[0] != SCRYPT_PREFIX:
        return False
    _, n, r, p, salt_hex, digest_hex = parts
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def normalize_admin_username(value):
    """Return a trimmed admin username, which must be non-empty text.

    A value that does not fit raises ``ValueError`` with a message the caller
    can show; the HTTP handler maps it to a ``400`` and the maintenance command
    to a failed exit.
    """
    if not isinstance(value, str):
        raise ValueError("admin username must be text")
    username = value.strip()
    if not username:
        raise ValueError("admin username must not be empty")
    if len(username) > ADMIN_USERNAME_MAX_LENGTH:
        raise ValueError("admin username is too long")
    return username


def validate_admin_credentials(payload):
    """Return the normalized ``(username, password)`` of a new admin account.

    The account is created once, on the first run, and the password is stored
    only as a scrypt hash (section 31 point 1). The password is not trimmed:
    what the user typed is what is stored, and what the login form sends back.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    username = normalize_admin_username(payload.get("username"))
    password = payload.get("password")
    if not isinstance(password, str):
        raise ValueError("password must be text")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"password must be at least {PASSWORD_MIN_LENGTH} characters"
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError("password is too long")
    return username, password


def get_admin(database_path="data/vardkey.sqlite3"):
    """Return the stored ``(username, password_hash)``, either of which may be None."""
    settings = get_app_settings(database_path)
    return (
        settings.get(ADMIN_USERNAME_SETTING),
        settings.get(ADMIN_PASSWORD_HASH_SETTING),
    )


def admin_configured(database_path="data/vardkey.sqlite3"):
    """Return True when an admin username and password are stored.

    The first run has none, and the app answers with the create-admin page
    instead of the login form (section 31 point 1).
    """
    username, password_hash = get_admin(database_path)
    return bool(username and password_hash)


def set_admin(username, password, database_path="data/vardkey.sqlite3"):
    """Store the admin username and the scrypt hash of the password."""
    save_app_settings(
        {
            ADMIN_USERNAME_SETTING: username,
            ADMIN_PASSWORD_HASH_SETTING: hash_password(password),
        },
        database_path,
    )


def authenticate(username, password, database_path="data/vardkey.sqlite3"):
    """Return True when the credentials match the stored admin."""
    stored_username, stored_hash = get_admin(database_path)
    if not stored_username or not stored_hash:
        return False
    if not isinstance(username, str):
        return False
    # Both comparisons run, so a wrong username and a wrong password are equally
    # slow.
    username_ok = hmac.compare_digest(username, stored_username)
    password_ok = verify_password(password, stored_hash)
    return username_ok and password_ok


def session_secret(database_path="data/vardkey.sqlite3"):
    """Return the session secret, generating and storing it once."""
    stored = get_app_settings(database_path).get(SESSION_SECRET_SETTING)
    if stored:
        return stored
    secret = secrets.token_hex(32)
    save_app_settings({SESSION_SECRET_SETTING: secret}, database_path)
    return secret


def _sign(secret, payload):
    """Return the HMAC-SHA256 signature of a payload, as hex."""
    return hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def create_session_token(database_path="data/vardkey.sqlite3", now=None):
    """Return a signed session token that expires after the session lifetime."""
    moment = now or datetime.now(timezone.utc)
    expires = int((moment + timedelta(seconds=SESSION_TTL_SECONDS)).timestamp())
    payload = str(expires)
    return f"{payload}.{_sign(session_secret(database_path), payload)}"


def verify_session_token(token, database_path="data/vardkey.sqlite3", now=None):
    """Return True when the token is signed correctly and has not expired."""
    if not isinstance(token, str) or "." not in token:
        return False
    payload, _, signature = token.partition(".")
    expected = _sign(session_secret(database_path), payload)
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        expires = int(payload)
    except ValueError:
        return False
    moment = now or datetime.now(timezone.utc)
    return expires > int(moment.timestamp())


def new_csrf_token():
    """Return a fresh CSRF token."""
    return secrets.token_hex(32)


def csrf_tokens_match(cookie_value, header_value):
    """Return True when the CSRF cookie and the CSRF header are the same token."""
    if not cookie_value or not header_value:
        return False
    if not isinstance(cookie_value, str) or not isinstance(header_value, str):
        return False
    return hmac.compare_digest(cookie_value, header_value)
