"""Tests for SQLite schema, migration, storage, and constraints."""

from contextlib import contextmanager
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import (
    DEFAULT_WALLET_SOFTWARE,
    SCHEMA_VERSION,
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
    rotate_key,
    save_alert_acknowledgement,
    save_health_check,
    save_key_settings,
    save_key_setup,
    save_multisig_settings,
    save_wallet_software,
)
from validation import validate_health_check


# The address path each key slot is configured with, and the path a submission
# records (sections 25.1 and 26.2). Every key has its own one, so the fixtures
# match a setup the API accepts.
DEFAULT_ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
# The wallet software list the settings hold, and that the app passes to the
# validator (section 25.4).
SOFTWARE_NAMES = (DEFAULT_WALLET_SOFTWARE,)
# The key setup every test starts from, unless it tests the setup itself.
DEFAULT_SETUP = (
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": DEFAULT_ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
)
# A setup with the cloud key in the first slot, renamed hardware keys, and a
# different address path per key, so the comparison is proven to be per key.
RENAMED_SETUP = (
    {"key_number": 1, "name": "Coinbase", "type": "cloud", "address_path": DEFAULT_ADDRESS_PATH},
    {"key_number": 2, "name": "ColdCard", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Jade", "type": "hardware", "address_path": THIRD_ADDRESS_PATH},
)


def sample_payload(key, wallet_software=None, address_path=None):
    """Return a valid single-key payload for the given key profile.

    The recorded address path matches the stored one unless a test asks for
    another one (section 25.1).
    """
    if wallet_software is None:
        wallet_software = key["name"] if key["type"] == "cloud" else "Sparrow Wallet"
    labels = list(dict.fromkeys((key["name"], wallet_software)))
    entry = {
        "key_id": key["id"],
        "available": 1,
        "address_path": address_path if address_path is not None else key["address_path"],
        "comments": "",
    }
    if key["type"] == "hardware":
        entry.update({
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "OK",
        })
    return {
        "checked_at": "2026-10-01",
        "wallet_software": wallet_software,
        "software_version": "1.8.0",
        "software_compatibility_status": "OK",
        "software_comments": "",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": entry,
        "ai_security_checks": [
            {"provider": label, "status": "SECURE", "comments": ""} for label in labels
        ],
    }


def mismatch_payload(key, address_path):
    """Return the minimal payload the form sends when the path does not match.

    Everything else about the key is left out, because the key could not be
    checked (section 25.1).
    """
    return {
        "checked_at": "2026-10-01",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 1,
            "address_path": address_path,
            "comments": "Path read from the device",
        },
    }


def validate(payload, keys):
    """Return a validated payload, with the wallet software list the app passes.

    The wallet software choices are the settings list and the configured cloud
    key names, so the list must be passed in (section 25.4).
    """
    return validate_health_check(payload, keys, SOFTWARE_NAMES)


LEGACY_SCHEMA = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        device TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        software_compatibility_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified INTEGER,
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL,
        key_id INTEGER NOT NULL,
        available INTEGER,
        hardware_works INTEGER,
        firmware_version TEXT,
        seed_backup_status TEXT,
        cloud_health_status TEXT,
        cloud_provider_operational INTEGER,
        address_verified INTEGER,
        seed_backup_verified INTEGER,
        address_path_verified INTEGER,
        derivation_height TEXT,
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE tool_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL,
        product TEXT NOT NULL,
        bip327_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
        slip39_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT',
        version TEXT,
        checked_at TEXT,
        notes TEXT,
        UNIQUE (health_check_id, product)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('TRYGG', 'PATCHA', 'SÅRBAR', 'KOMPROMITTERT')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type, device) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'SeedSigner'),
        (2, 2, 'Blockstream Jade', 'hardware', 'Blockstream Jade'),
        (3, 3, 'Nunchuk', 'cloud', 'Nunchuk');
    INSERT INTO health_checks (id, checked_at, next_check_due, sparrow_version)
        VALUES (1, '2026-01-01', '2027-01-01', '1.7.0');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_status, seed_backup_verified, address_verified,
        address_path_verified, derivation_height, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 1, 1, 1, 'm/48''/0''/0''/2''', 'm/48''/0''/0''/2''/0/0');
    INSERT INTO key_checks (
        health_check_id, key_id, available, seed_backup_status,
        seed_backup_verified, address_verified, address_path_verified
    ) VALUES (1, 2, 1, 'PROBLEM', 0, 0, 0);
    INSERT INTO tool_checks (health_check_id, product, bip327_status, slip39_status)
        VALUES (1, 'SeedSigner', 'OK', 'PROBLEM');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'TRYGG'),
        (1, 'Nunchuk', 'SÅRBAR');
    PRAGMA user_version = 4;
"""

# The layout introduced by section 19, before the status values became English,
# before the contact flag became a stored status, and before the fixed device,
# product, provider, and wallet-software lists were dropped. It still holds the
# tool_checks table, which the migration drops (sections 24.2 and 24.4), and the
# two derived cloud results, which section 25.6 drops.
SCHEMA_VERSION_5 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        device TEXT NOT NULL CHECK (device IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT CHECK (wallet_software IN ('Sparrow Wallet', 'Nunchuk')),
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified INTEGER CHECK (contact_info_verified IN (0, 1)),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        cloud_health_status TEXT CHECK (cloud_health_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        cloud_provider_operational INTEGER CHECK (cloud_provider_operational IN (0, 1)),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE tool_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        product TEXT NOT NULL CHECK (product IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        bip327_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (bip327_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        slip39_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (slip39_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        version TEXT,
        checked_at TEXT,
        notes TEXT,
        UNIQUE (health_check_id, product)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK (provider IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type, device) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'SeedSigner'),
        (2, 2, 'Blockstream Jade', 'hardware', 'Blockstream Jade'),
        (3, 3, 'Nunchuk', 'cloud', 'Nunchuk');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'IKKJE_VURDERT', 1, 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, cloud_health_status, cloud_provider_operational
    ) VALUES (1, 3, 1, 'IKKJE_VURDERT', 1);
    INSERT INTO tool_checks (health_check_id, product, bip327_status, slip39_status) VALUES
        (1, 'SeedSigner', 'OK', 'PROBLEM'),
        (1, 'Sparrow Wallet', 'IKKJE_VURDERT', 'OK');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'Nunchuk', 'SECURE');
    PRAGMA user_version = 5;
"""

# The schema version 8 layout, which is the current one except that it still
# holds the tool_checks table and its rows. The migration drops that table and
# nothing else (sections 24.2 and 24.4).
SCHEMA_VERSION_8 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT,
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified TEXT
            CHECK (contact_info_verified IN ('Confirmed current', 'Needs external update')),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        cloud_health_status TEXT CHECK (cloud_health_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        cloud_provider_operational INTEGER CHECK (cloud_provider_operational IN (0, 1)),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE tool_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        product TEXT NOT NULL,
        bip327_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (bip327_status IN ('YES', 'NO', 'NOT_ASSESSED')),
        slip39_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (slip39_status IN ('YES', 'NO', 'NOT_ASSESSED')),
        version TEXT,
        checked_at TEXT,
        notes TEXT,
        UNIQUE (health_check_id, product)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type) VALUES
        (1, 1, 'SeedSigner', 'hardware'),
        (2, 2, 'Blockstream Jade', 'hardware'),
        (3, 3, 'Nunchuk', 'cloud');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'OK', 'Confirmed current', 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_verified, address_path_verified, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 'OK', 'm/48''/0''/0''/2''/0/0');
    INSERT INTO tool_checks (health_check_id, product, bip327_status, slip39_status) VALUES
        (1, 'SeedSigner', 'YES', 'NO'),
        (1, 'Sparrow Wallet', 'NOT_ASSESSED', 'NOT_ASSESSED');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'SECURE'),
        (1, 'Sparrow Wallet', 'SECURE');
    PRAGMA user_version = 8;
"""

# The schema version 9 layout, which is the current one except that it still
# holds the two derived cloud results in key_checks and has no key address path,
# no wallet software list, and no alert acknowledgements (section 25.6).
SCHEMA_VERSION_9 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT,
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified TEXT
            CHECK (contact_info_verified IN ('Confirmed current', 'Needs external update')),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        cloud_health_status TEXT CHECK (cloud_health_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        cloud_provider_operational INTEGER CHECK (cloud_provider_operational IN (0, 1)),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    INSERT INTO keys (id, key_number, name, type) VALUES
        (1, 1, 'SeedSigner', 'hardware'),
        (2, 2, 'Blockstream Jade', 'hardware'),
        (3, 3, 'Nunchuk', 'cloud');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'OK', 'Confirmed current', 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_verified, cloud_health_status, cloud_provider_operational,
        address_path_verified, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 'OK', 1, 'OK', 'm/48''/0''/0''/2''');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'SECURE'),
        (1, 'Sparrow Wallet', 'SECURE');
    PRAGMA user_version = 9;
"""

# The schema version 10 layout, which is the current one except that
# alert_acknowledgements has no key_id column. The migration adds that column
# and rebuilds no table (section 27).
SCHEMA_VERSION_10 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        address_path TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT,
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified TEXT
            CHECK (contact_info_verified IN ('Confirmed current', 'Needs external update')),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    CREATE TABLE wallet_software (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE alert_acknowledgements (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL,
        source TEXT NOT NULL,
        check_id INTEGER,
        reason TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL
    );
    INSERT INTO keys (id, key_number, name, type, address_path) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'm/48''/0''/0''/2'''),
        (2, 2, 'Blockstream Jade', 'hardware', 'm/48''/1''/0''/2'''),
        (3, 3, 'Nunchuk', 'cloud', 'm/48''/2''/0''/2''');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'OK', 'Confirmed current', 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_verified, address_path_verified, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 'OK', 'm/48''/0''/0''/2''');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'SECURE'),
        (1, 'Sparrow Wallet', 'SECURE');
    INSERT INTO wallet_software (name) VALUES ('Sparrow Wallet');
    INSERT INTO alert_acknowledgements (code, source, check_id, reason, acknowledged_at) VALUES
        ('key_unavailable', 'Key 1: SeedSigner', 1, 'rotate', '2026-02-01T09:00:00');
    PRAGMA user_version = 10;
"""

# The schema version 11 layout, which is the current one before section 31: the
# key_number CHECK still bounds the three fixed slots, there is no model column,
# and there is no app_settings table. The migration loosens the CHECK, which
# rebuilds keys, and creates app_settings (sections 31.5 and 31.7).
SCHEMA_VERSION_11 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        address_path TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT,
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified TEXT
            CHECK (contact_info_verified IN ('Confirmed current', 'Needs external update')),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    CREATE TABLE wallet_software (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE alert_acknowledgements (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL,
        source TEXT NOT NULL,
        key_id INTEGER,
        check_id INTEGER,
        reason TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL
    );
    INSERT INTO keys (id, key_number, name, type, address_path) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'm/48''/0''/0''/2'''),
        (2, 2, 'Blockstream Jade', 'hardware', 'm/48''/1''/0''/2'''),
        (3, 3, 'Nunchuk', 'cloud', 'm/48''/2''/0''/2''');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'OK', 'Confirmed current', 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_verified, address_path_verified, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 'OK', 'm/48''/0''/0''/2''');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'SECURE'),
        (1, 'Sparrow Wallet', 'SECURE');
    INSERT INTO wallet_software (name) VALUES ('Sparrow Wallet');
    INSERT INTO alert_acknowledgements (code, source, key_id, check_id, reason, acknowledged_at) VALUES
        ('key_unavailable', 'Key 1: SeedSigner', 1, 1, 'rotate', '2026-02-01T09:00:00');
    PRAGMA user_version = 11;
"""

# The schema version 12 layout, which is the current one before section 32.8:
# ``key_number`` is still UNIQUE, there is no active flag and no rotated_at,
# key_checks carries no snapshot of the key it belongs to, and
# ai_security_checks carries no key_id. The migration rebuilds keys to drop the
# UNIQUE and add the two columns, adds the snapshot columns and the security key
# id, and backfills the snapshot from the linked key (section 32.8 points 5
# and 6).
SCHEMA_VERSION_12 = """
    CREATE TABLE keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        address_path TEXT NOT NULL DEFAULT '',
        model TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        wallet_software TEXT,
        software_version TEXT,
        software_compatibility_status TEXT NOT NULL DEFAULT 'NOT_ASSESSED'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'NOT_ASSESSED')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        software_comments TEXT,
        contact_info_verified TEXT
            CHECK (contact_info_verified IN ('Confirmed current', 'Needs external update')),
        comments TEXT
    );
    CREATE TABLE key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_verified TEXT CHECK (seed_backup_verified IN ('OK', 'PROBLEM')),
        address_path_verified TEXT CHECK (address_path_verified IN ('OK', 'PROBLEM')),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    );
    CREATE TABLE ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    );
    CREATE TABLE wallet_software (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE alert_acknowledgements (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL,
        source TEXT NOT NULL,
        key_id INTEGER,
        check_id INTEGER,
        reason TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL
    );
    CREATE TABLE app_settings (
        name TEXT PRIMARY KEY,
        value TEXT
    );
    INSERT INTO keys (id, key_number, name, type, address_path, model) VALUES
        (1, 1, 'SeedSigner', 'hardware', 'm/48''/0''/0''/2''', 'ColdCard Q'),
        (2, 2, 'Blockstream Jade', 'hardware', 'm/48''/1''/0''/2''', NULL),
        (3, 3, 'Nunchuk', 'cloud', 'm/48''/2''/0''/2''', 'Casa');
    INSERT INTO health_checks (
        id, checked_at, next_check_due, wallet_software, software_version,
        software_compatibility_status, contact_info_verified, comments
    ) VALUES (1, '2026-01-01', '2027-01-01', 'Sparrow Wallet', '1.8.0', 'OK', 'Confirmed current', 'Annual review');
    INSERT INTO key_checks (
        health_check_id, key_id, available, hardware_works, firmware_version,
        seed_backup_verified, address_path_verified, address_path
    ) VALUES (1, 1, 1, 1, '1.0.0', 'OK', 'OK', 'm/48''/0''/0''/2''');
    INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES
        (1, 'SeedSigner', 'SECURE'),
        (1, 'Sparrow Wallet', 'SECURE');
    INSERT INTO wallet_software (name) VALUES ('Sparrow Wallet');
    INSERT INTO alert_acknowledgements (code, source, key_id, check_id, reason, acknowledged_at) VALUES
        ('key_unavailable', 'Key 1: SeedSigner', 1, 1, 'rotate', '2026-02-01T09:00:00');
    PRAGMA user_version = 12;
"""


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "nested" / "test.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def prepare(self, setup=DEFAULT_SETUP):
        """Create the schema and store a key setup."""
        initialize_database(self.database_path)
        save_key_setup(setup, self.database_path)
        return list_keys(self.database_path)

    def write_schema(self, script):
        """Create a database from an explicit older schema script.

        The connection is closed explicitly: using it as a context manager only
        commits the transaction, and Windows keeps the database file locked
        until every connection is closed.
        """
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.executescript(script)
        finally:
            connection.close()

    def table_names(self):
        """Return the table names of the migrated database."""
        with self.connect() as connection:
            return {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

    def columns_of(self, table):
        """Return the column names of one table in the migrated database."""
        with self.connect() as connection:
            return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}

    def table_sql(self, table):
        """Return the stored CREATE statement of one table, or an empty string."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
        return row[0] if row else ""

    def index_names(self):
        """Return the index names of the migrated database."""
        with self.connect() as connection:
            return {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                )
            }

    def test_initialization_creates_versioned_schema_and_is_idempotent(self):
        initialize_database(self.database_path)
        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 13)
        self.assertTrue(
            {
                "keys",
                "health_checks",
                "key_checks",
                "ai_security_checks",
                "wallet_software",
                "alert_acknowledgements",
                "app_settings",
            } <= tables
        )
        # The BIP327/SLIP39 table is not part of the schema any more
        # (sections 24.2 and 24.4).
        self.assertNotIn("tool_checks", tables)

    def test_a_new_database_has_no_key_setup(self):
        initialize_database(self.database_path)

        self.assertEqual(list_keys(self.database_path), [])

    def test_a_new_database_has_no_stored_multisig_shape(self):
        initialize_database(self.database_path)

        # A database without the two settings falls back to the 2-of-3 default
        # the app was built for (section 31 point 7).
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 2, "key_count": 3},
        )

    def test_a_new_database_starts_with_one_wallet_software_entry(self):
        initialize_database(self.database_path)

        # The list is stored whole and the user may replace the entry once
        # another one has been added (section 25.4).
        self.assertEqual(list_wallet_software(self.database_path), [DEFAULT_WALLET_SOFTWARE])

    def test_the_wallet_software_list_is_stored_whole(self):
        initialize_database(self.database_path)

        save_wallet_software(["Sparrow Wallet", "BlueWallet"], self.database_path)
        self.assertEqual(
            list_wallet_software(self.database_path), ["Sparrow Wallet", "BlueWallet"]
        )

        # Replacing the list removes the entries that are not sent again.
        save_wallet_software(["BlueWallet"], self.database_path)
        self.assertEqual(list_wallet_software(self.database_path), ["BlueWallet"])

        # A database whose list is not empty is never seeded again.
        initialize_database(self.database_path)
        self.assertEqual(list_wallet_software(self.database_path), ["BlueWallet"])

    def test_the_key_setup_is_stored_once_and_locked(self):
        keys = self.prepare(RENAMED_SETUP)

        self.assertEqual(
            [
                (key["key_number"], key["name"], key["type"], key["address_path"])
                for key in keys
            ],
            [
                (1, "Coinbase", "cloud", DEFAULT_ADDRESS_PATH),
                (2, "ColdCard", "hardware", SECOND_ADDRESS_PATH),
                (3, "Jade", "hardware", THIRD_ADDRESS_PATH),
            ],
        )

        with self.assertRaises(RuntimeError):
            save_key_setup(DEFAULT_SETUP, self.database_path)

        # The refused write left the stored setup untouched.
        self.assertEqual([key["name"] for key in list_keys(self.database_path)],
                         ["Coinbase", "ColdCard", "Jade"])

    def test_a_five_key_setup_is_stored_and_read_back(self):
        # The number of key slots is configurable, so a setup with more than the
        # three default slots is stored and read back with its own shape
        # (section 31 point 7).
        initialize_database(self.database_path)
        setup = [
            {
                "key_number": number,
                "name": f"Key {number}",
                "type": "hardware",
                "address_path": f"m/48'/{number}'/0'/2'",
            }
            for number in range(1, 6)
        ]

        save_key_setup(setup, self.database_path, threshold=3, key_count=5)

        keys = list_keys(self.database_path)
        self.assertEqual([key["key_number"] for key in keys], [1, 2, 3, 4, 5])
        self.assertEqual([key["name"] for key in keys], [f"Key {n}" for n in range(1, 6)])
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 3, "key_count": 5},
        )

    def test_the_multisig_settings_can_be_stored_on_their_own(self):
        initialize_database(self.database_path)

        save_multisig_settings(2, 3, self.database_path)
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 2, "key_count": 3},
        )

        # A stored setting replaces the earlier one.
        save_multisig_settings(4, 7, self.database_path)
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 4, "key_count": 7},
        )

    def test_a_partial_key_setup_is_reported_as_an_error(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO keys (key_number, name, type) VALUES (1, 'ColdCard', 'hardware')"
            )

        # A database that holds part of a setup is never treated as a new one.
        with self.assertRaises(RuntimeError):
            list_keys(self.database_path)

    def test_partial_schema_is_repaired_idempotently(self):
        self.write_schema(
            """
            CREATE TABLE key_checks (
                id INTEGER PRIMARY KEY,
                address_verified INTEGER,
                derivation_height TEXT,
                seed_backup_verified INTEGER
            );
            CREATE TABLE health_checks (
                id INTEGER PRIMARY KEY,
                software_comments TEXT
            );
            INSERT INTO key_checks (address_verified, derivation_height) VALUES (1, '0');
            PRAGMA user_version = 0;
            """
        )

        initialize_database(self.database_path)
        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {row[1] for row in connection.execute("PRAGMA table_info(key_checks)")}

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertTrue({"available", "seed_backup_verified", "address_path_verified"} <= columns)
        self.assertFalse({"address_verified", "derivation_height"} & columns)

    def test_legacy_database_migrates_to_per_key_checks(self):
        self.write_schema(LEGACY_SCHEMA)

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {row[1] for row in connection.execute("PRAGMA table_info(key_checks)")}
            key_columns = {row[1] for row in connection.execute("PRAGMA table_info(keys)")}
            rows = connection.execute(
                "SELECT key_id, seed_backup_verified, address_path_verified "
                "FROM key_checks ORDER BY key_id"
            ).fetchall()
            statuses = connection.execute(
                "SELECT provider, status FROM ai_security_checks ORDER BY provider"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertFalse({"seed_backup_status", "address_verified", "derivation_height"} & columns)
        self.assertFalse({"cloud_health_status", "cloud_provider_operational"} & columns)
        self.assertNotIn("device", key_columns)
        self.assertIn("address_path", key_columns)
        self.assertEqual(rows, [(1, "OK", "OK"), (2, "PROBLEM", "PROBLEM")])
        self.assertEqual(statuses, [("Nunchuk", "VULNERABLE"), ("SeedSigner", "SECURE")])
        # The BIP327/SLIP39 rows are dropped with their table, and the rest of
        # the history is kept (sections 24.2 and 24.4).
        self.assertNotIn("tool_checks", self.table_names())

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["checked_at"], "2026-01-01")
        self.assertEqual(record["sparrow_version"], "1.7.0")
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertIsNone(record["contact_info_verified"])
        self.assertEqual(record["key_checks"][0]["seed_backup_verified"], "OK")
        self.assertEqual(record["key_checks"][0]["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(record["key_checks"][1]["seed_backup_verified"], "PROBLEM")
        self.assertEqual([entry["status"] for entry in record["ai_security_checks"]], ["SECURE", "VULNERABLE"])
        # The snapshot of a migrated check comes from the key it belongs to, so
        # the history keeps the name it had at the migration (section 32.8
        # point 5).
        self.assertEqual(record["key_checks"][0]["name"], "SeedSigner")
        self.assertEqual(record["key_checks"][0]["type"], "hardware")

        # The existing installation keeps its keys, and can record new checks.
        keys = list_keys(self.database_path)
        self.assertEqual([key["name"] for key in keys], ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        new_id = save_health_check(validate(sample_payload(keys[2]), keys), self.database_path)
        new_record = get_health_check(new_id, self.database_path)
        self.assertEqual(new_record["wallet_software"], "Nunchuk")
        self.assertEqual(len(new_record["key_checks"]), 1)
        self.assertEqual(new_record["key_checks"][0]["key_number"], 3)
        self.assertEqual([entry["provider"] for entry in new_record["ai_security_checks"]], ["Nunchuk"])

    def test_a_version_8_database_drops_the_tool_checks_table_and_the_cloud_columns(self):
        self.write_schema(SCHEMA_VERSION_8)
        # The old database really holds the table and its rows before the
        # migration runs (sections 24.2 and 24.4).
        self.assertIn("tool_checks", self.table_names())

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            checks = connection.execute("SELECT COUNT(*) FROM health_checks").fetchone()[0]
            key_checks = connection.execute("SELECT COUNT(*) FROM key_checks").fetchone()[0]
            security = connection.execute(
                "SELECT provider, status FROM ai_security_checks ORDER BY provider"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertNotIn("tool_checks", self.table_names())
        self.assertFalse(
            {"cloud_health_status", "cloud_provider_operational"} & self.columns_of("key_checks")
        )
        # Everything else survives the drop.
        self.assertEqual((checks, key_checks), (1, 1))
        self.assertEqual(security, [("SeedSigner", "SECURE"), ("Sparrow Wallet", "SECURE")])

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["checked_at"], "2026-01-01")
        self.assertEqual(record["wallet_software"], "Sparrow Wallet")
        self.assertEqual(record["contact_info_verified"], "Confirmed current")
        self.assertEqual(record["key_checks"][0]["seed_backup_verified"], "OK")
        self.assertEqual(record["key_checks"][0]["address_path"], "m/48'/0'/0'/2'/0/0")
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )

        # The migrated database still records new checks.
        keys = list_keys(self.database_path)
        new_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )
        self.assertEqual(get_health_check(new_id, self.database_path)["wallet_software"],
                         "Sparrow Wallet")

    def test_a_version_9_database_gains_the_address_path_and_the_new_tables(self):
        self.write_schema(SCHEMA_VERSION_9)
        self.assertNotIn("wallet_software", self.table_names())
        self.assertIn("cloud_health_status", self.columns_of("key_checks"))

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            checks = connection.execute("SELECT COUNT(*) FROM health_checks").fetchone()[0]
            key_checks = connection.execute("SELECT COUNT(*) FROM key_checks").fetchone()[0]
            address_paths = connection.execute(
                "SELECT address_path FROM keys ORDER BY key_number"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 13)
        self.assertIn("wallet_software", self.table_names())
        self.assertIn("alert_acknowledgements", self.table_names())
        # The two derived cloud results are gone, and the rest of the history is
        # kept (section 25.6).
        self.assertFalse(
            {"cloud_health_status", "cloud_provider_operational"} & self.columns_of("key_checks")
        )
        self.assertEqual((checks, key_checks), (1, 1))
        # The address path of a migrated key starts empty, because the old
        # database never recorded one (section 25.1).
        self.assertEqual(address_paths, [("",), ("",), ("",)])
        self.assertEqual(list_wallet_software(self.database_path), [DEFAULT_WALLET_SOFTWARE])

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["checked_at"], "2026-01-01")
        self.assertEqual(record["wallet_software"], "Sparrow Wallet")
        self.assertEqual(record["key_checks"][0]["address_path_verified"], "OK")
        self.assertEqual(record["key_checks"][0]["address_path"], "m/48'/0'/0'/2'")

    def test_a_version_10_database_gains_the_acknowledgement_key_id(self):
        self.write_schema(SCHEMA_VERSION_10)
        self.assertNotIn("key_id", self.columns_of("alert_acknowledgements"))

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            stored = connection.execute(
                "SELECT code, source, key_id, check_id, reason FROM alert_acknowledgements"
            ).fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 13)
        self.assertIn("key_id", self.columns_of("alert_acknowledgements"))
        # The older acknowledgement survives, with an empty key id, because it
        # predates the column (section 27).
        self.assertEqual(
            stored,
            [("key_unavailable", "Key 1: SeedSigner", None, 1, "rotate")],
        )

    def test_a_version_11_database_gains_app_settings_and_a_free_key_number(self):
        self.write_schema(SCHEMA_VERSION_11)
        # The old table really bounds key_number before the migration runs
        # (section 31 point 7).
        with self.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO keys (key_number, name, type, address_path) "
                    "VALUES (4, 'Fourth', 'hardware', 'm/48''/9''/0''/2''')"
                )

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            keys = connection.execute(
                "SELECT key_number, name, type, address_path FROM keys ORDER BY key_number"
            ).fetchall()
            acknowledgements = connection.execute(
                "SELECT code, key_id FROM alert_acknowledgements"
            ).fetchall()
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 13)
        self.assertIn("app_settings", self.table_names())
        self.assertIn("model", self.columns_of("keys"))
        # The rebuilt table kept the rows and did not break a foreign key.
        self.assertEqual(violations, [])
        self.assertEqual(
            keys,
            [
                (1, "SeedSigner", "hardware", "m/48'/0'/0'/2'"),
                (2, "Blockstream Jade", "hardware", "m/48'/1'/0'/2'"),
                (3, "Nunchuk", "cloud", "m/48'/2'/0'/2'"),
            ],
        )
        self.assertEqual(acknowledgements, [("key_unavailable", 1)])
        # A database without the stored shape still falls back to 2-of-3.
        self.assertEqual(
            get_multisig_settings(self.database_path),
            {"threshold": 2, "key_count": 3},
        )

        # The loosened CHECK accepts a key number above three now. The row is
        # rolled back, so the stored setup stays the three migrated keys.
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "INSERT INTO keys (key_number, name, type, address_path) "
                "VALUES (4, 'Fourth', 'hardware', 'm/48''/9''/0''/2''')"
            )
            connection.rollback()
        finally:
            connection.close()

        # The migrated database still records new checks for its three keys.
        keys = list_keys(self.database_path)
        self.assertEqual([key["key_number"] for key in keys], [1, 2, 3])
        new_id = save_health_check(validate(sample_payload(keys[0]), keys), self.database_path)
        self.assertEqual(get_health_check(new_id, self.database_path)["checked_at"], "2026-10-01")

    def test_a_version_12_database_gains_the_active_flag_and_the_frozen_history(self):
        self.write_schema(SCHEMA_VERSION_12)
        # The old table really refuses a second row for one slot before the
        # migration drops the UNIQUE (section 32.8 point 5).
        with self.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO keys (key_number, name, type, address_path) "
                    "VALUES (1, 'Duplicate', 'hardware', 'm/48''/9''/0''/2''')"
                )

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            keys = connection.execute(
                "SELECT key_number, name, active, rotated_at FROM keys ORDER BY key_number"
            ).fetchall()
            snapshot = connection.execute(
                "SELECT key_name, key_type, key_model FROM key_checks WHERE id = 1"
            ).fetchone()
            security = connection.execute(
                "SELECT provider, key_id FROM ai_security_checks ORDER BY provider"
            ).fetchall()
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 13)
        self.assertEqual(violations, [])
        # The UNIQUE is gone, and the one-active-row-per-slot rule is a partial
        # unique index now.
        self.assertNotIn("UNIQUE", self.table_sql("keys"))
        self.assertIn("idx_keys_active_key_number", self.index_names())
        self.assertIn("active", self.columns_of("keys"))
        self.assertIn("rotated_at", self.columns_of("keys"))
        for name in ("key_name", "key_type", "key_model"):
            self.assertIn(name, self.columns_of("key_checks"))
        self.assertIn("key_id", self.columns_of("ai_security_checks"))
        # Every row of a database that predates the flag is active, because it
        # was written before a rotation could add a second row for the slot.
        self.assertEqual(
            keys,
            [
                (1, "SeedSigner", 1, None),
                (2, "Blockstream Jade", 1, None),
                (3, "Nunchuk", 1, None),
            ],
        )
        # The snapshot is backfilled from the key the check belongs to, so an
        # older record keeps the name, the type, and the model it had at the
        # migration (section 32.8 point 5).
        self.assertEqual(snapshot, ("SeedSigner", "hardware", "ColdCard Q"))
        # A security row written before the column exists keeps a NULL key, so
        # the source of its alert is unchanged by the migration (section 32.8
        # point 6).
        self.assertEqual(security, [("SeedSigner", None), ("Sparrow Wallet", None)])

        # The migrated database still records new checks, and the new row
        # carries its own snapshot and the key of its own provider.
        keys = list_keys(self.database_path)
        new_id = save_health_check(validate(sample_payload(keys[0]), keys), self.database_path)
        new_record = get_health_check(new_id, self.database_path)
        self.assertEqual(new_record["key_checks"][0]["name"], "SeedSigner")
        self.assertEqual(new_record["key_checks"][0]["model"], "ColdCard Q")
        self.assertEqual(
            [(entry["provider"], entry["key_id"]) for entry in new_record["ai_security_checks"]],
            [("SeedSigner", keys[0]["id"]), ("Sparrow Wallet", None)],
        )

    def test_only_one_active_key_row_may_use_a_slot(self):
        self.prepare()

        with self.connect() as connection:
            # A second active row for the same multisig slot is refused by the
            # partial unique index (section 32.8 point 5).
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO keys (key_number, name, type) "
                    "VALUES (1, 'Duplicate', 'hardware')"
                )
            # A retired row may share the slot, because the index is partial.
            connection.execute(
                "INSERT INTO keys (key_number, name, type, active) "
                "VALUES (1, 'Retired', 'hardware', 0)"
            )
            retired = connection.execute(
                "SELECT COUNT(*) FROM keys WHERE key_number = 1 AND active = 0"
            ).fetchone()[0]

        self.assertEqual(retired, 1)
        # The retired row is invisible to the setup and to the dashboard.
        self.assertEqual([key["name"] for key in list_keys(self.database_path)],
                         ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        self.assertEqual(
            [entry["key_number"] for entry in list_key_status(self.database_path)],
            [1, 2, 3],
        )

    def test_a_rotation_inserts_a_new_active_row_and_retires_the_old_one(self):
        keys = self.prepare()
        first = keys[0]
        saved_id = save_health_check(
            validate(sample_payload(first), keys), self.database_path
        )

        new_id = rotate_key(
            first["id"], "ColdCard", "m/48'/7'/0'/2'", self.database_path
        )

        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, key_number, name, active, rotated_at FROM keys "
                "WHERE key_number = 1 ORDER BY id"
            ).fetchall()

        self.assertNotEqual(new_id, first["id"])
        # The multisig slot stays, the old row is retired, and the new one is
        # the active row (section 32.8 point 5).
        self.assertEqual(
            [(row[0], row[1], row[2], row[3]) for row in rows],
            [(first["id"], 1, "SeedSigner", 0), (new_id, 1, "ColdCard", 1)],
        )
        self.assertTrue(rows[0][4])

        # The setup, the settings, and the dashboard read the active row only.
        active = list_keys(self.database_path)
        self.assertEqual([key["key_number"] for key in active], [1, 2, 3])
        self.assertEqual(active[0]["name"], "ColdCard")
        self.assertEqual(active[0]["address_path"], "m/48'/7'/0'/2'")
        self.assertEqual(active[0]["type"], "hardware")
        # The replacement is a new key with an empty history, so its path is not
        # locked yet.
        self.assertFalse(key_has_check(new_id, self.database_path))

        # The older check keeps the snapshot it was recorded with, so a rotation
        # cannot rewrite the history.
        record = get_health_check(saved_id, self.database_path)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(record["key_checks"][0]["name"], "SeedSigner")
        self.assertEqual(record["key_checks"][0]["type"], "hardware")
        rows = list_export_rows(self.database_path)
        self.assertEqual(rows[0]["key_name"], "SeedSigner")

    def test_a_rename_does_not_change_an_older_check(self):
        keys = self.prepare()
        first = keys[0]
        saved_id = save_health_check(
            validate(sample_payload(first), keys), self.database_path
        )

        save_key_settings(
            first["id"],
            "ColdCard",
            first["address_path"],
            self.database_path,
            model="ColdCard Mk4",
        )

        # The live key carries the new label, while the saved check keeps the
        # snapshot it was recorded with (section 32.8 point 5).
        self.assertEqual(list_keys(self.database_path)[0]["name"], "ColdCard")
        record = get_health_check(saved_id, self.database_path)
        self.assertEqual(record["key_checks"][0]["name"], "SeedSigner")
        self.assertIsNone(record["key_checks"][0]["model"])
        self.assertEqual(list_export_rows(self.database_path)[0]["key_name"], "SeedSigner")

    def test_a_security_row_of_the_checked_key_carries_its_key(self):
        keys = self.prepare()

        saved_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )
        cloud_id = save_health_check(
            validate(sample_payload(keys[2]), keys), self.database_path
        )

        with self.connect() as connection:
            hardware = connection.execute(
                "SELECT provider, key_id FROM ai_security_checks "
                "WHERE health_check_id = ? ORDER BY provider",
                (saved_id,),
            ).fetchall()
            cloud = connection.execute(
                "SELECT provider, key_id FROM ai_security_checks "
                "WHERE health_check_id = ?",
                (cloud_id,),
            ).fetchall()

        # The key's own configured name carries the checked key, so its alert
        # belongs to that key; the selected wallet software does not, so its
        # alert belongs to the settings list (section 32.8 point 6).
        self.assertEqual(
            hardware, [("SeedSigner", keys[0]["id"]), ("Sparrow Wallet", None)]
        )
        # A cloud key records its own name as its software, so the single row is
        # the key itself.
        self.assertEqual(cloud, [("Nunchuk", keys[2]["id"])])

    def test_status_values_migrate_to_english(self):
        self.write_schema(SCHEMA_VERSION_5)

        initialize_database(self.database_path)

        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            compatibility = connection.execute(
                "SELECT software_compatibility_status FROM health_checks"
            ).fetchone()[0]

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(compatibility, "NOT_ASSESSED")
        self.assertNotIn("tool_checks", self.table_names())
        self.assertFalse(
            {"cloud_health_status", "cloud_provider_operational"} & self.columns_of("key_checks")
        )

        record = get_health_check(1, self.database_path)
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["comments"], "Annual review")
        self.assertEqual(record["ai_security_checks"][0]["status"], "SECURE")

    def test_the_device_column_is_dropped(self):
        self.write_schema(SCHEMA_VERSION_5)

        initialize_database(self.database_path)

        with self.connect() as connection:
            key_columns = {row[1] for row in connection.execute("PRAGMA table_info(keys)")}
            keys = connection.execute("SELECT key_number, name, type FROM keys ORDER BY key_number").fetchall()

        # The configured name is the product label, so the fixed device value is
        # gone and the stored keys are kept (section 23.2).
        self.assertNotIn("device", key_columns)
        self.assertEqual(
            keys,
            [(1, "SeedSigner", "hardware"), (2, "Blockstream Jade", "hardware"), (3, "Nunchuk", "cloud")],
        )

    def test_the_contact_flag_migrates_to_the_stored_statuses(self):
        self.write_schema(SCHEMA_VERSION_5)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (id, checked_at, next_check_due, contact_info_verified) "
                "VALUES (2, '2025-01-01', '2026-01-01', 0), (3, '2024-01-01', '2025-01-01', NULL)"
            )

        initialize_database(self.database_path)

        with self.connect() as connection:
            stored = connection.execute(
                "SELECT id, contact_info_verified FROM health_checks ORDER BY id"
            ).fetchall()

        # 1 meant "confirmed", 0 meant "not confirmed", and an empty value stays
        # empty (section 23.1).
        self.assertEqual(
            stored,
            [(1, "Confirmed current"), (2, "Needs external update"), (3, None)],
        )

    def test_the_migrated_schema_rejects_the_old_status_values(self):
        self.write_schema(SCHEMA_VERSION_5)
        initialize_database(self.database_path)

        with self.connect() as connection:
            for statement, parameters in (
                (
                    "INSERT INTO health_checks (checked_at, next_check_due, software_compatibility_status) "
                    "VALUES ('2026-01-01', '2027-01-01', ?)",
                    ("IKKJE_VURDERT",),
                ),
                (
                    "INSERT INTO health_checks (checked_at, next_check_due, contact_info_verified) "
                    "VALUES ('2026-01-01', '2027-01-01', ?)",
                    (1,),
                ),
            ):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(statement, parameters)

    def test_the_migrated_schema_accepts_a_free_provider_name(self):
        self.write_schema(SCHEMA_VERSION_5)
        initialize_database(self.database_path)

        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (checked_at, next_check_due, wallet_software) "
                "VALUES ('2026-01-01', '2027-01-01', 'Coinbase')"
            )
            health_check_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO ai_security_checks (health_check_id, provider, status) "
                "VALUES (?, 'ColdCard', 'SECURE')",
                (health_check_id,),
            )
            stored = connection.execute(
                "SELECT wallet_software FROM health_checks WHERE id = ?", (health_check_id,)
            ).fetchone()[0]

        # The configured name and the selected software are free text, so the
        # old provider and wallet-software lists no longer reject them
        # (section 23.3).
        self.assertEqual(stored, "Coinbase")

    def test_the_rebuilt_parent_table_keeps_its_foreign_keys(self):
        self.write_schema(SCHEMA_VERSION_5)
        initialize_database(self.database_path)

        with self.connect() as connection:
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO key_checks (health_check_id, key_id) VALUES (999, 1)"
                )
            children = connection.execute(
                "SELECT COUNT(*) FROM key_checks WHERE health_check_id = 1"
            ).fetchone()[0]

        self.assertEqual(violations, [])
        self.assertEqual(children, 1)

    def test_saved_health_checks_are_stored_and_never_overwritten(self):
        keys = self.prepare()
        data = validate(sample_payload(keys[0]), keys)

        first_id = save_health_check(data, self.database_path)
        second_id = save_health_check(data, self.database_path)

        self.assertNotEqual(first_id, second_id)
        summaries = list_health_checks(self.database_path)
        self.assertEqual([entry["id"] for entry in summaries], [second_id, first_id])
        self.assertEqual(summaries[0]["key_numbers"], [1])

        record = get_health_check(first_id, self.database_path)
        self.assertEqual(record["checked_at"], "2026-10-01")
        self.assertEqual(record["next_check_due"], "2027-10-01")
        self.assertEqual(record["comments"], "Annual review")
        self.assertEqual(record["contact_info_verified"], "Confirmed current")
        self.assertEqual(len(record["key_checks"]), 1)
        self.assertEqual(record["key_checks"][0]["key_number"], 1)
        self.assertEqual(record["key_checks"][0]["seed_backup_verified"], "OK")
        self.assertEqual(record["key_checks"][0]["address_path"], DEFAULT_ADDRESS_PATH)
        self.assertEqual(record["key_checks"][0]["address_path_verified"], "OK")
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]],
            ["SeedSigner", "Sparrow Wallet"],
        )
        self.assertEqual(record["ai_security_checks"][0]["status"], "SECURE")
        self.assertIsNone(get_health_check(9999, self.database_path))

    def test_a_mismatched_address_path_is_stored_as_an_uncheckable_key(self):
        keys = self.prepare()

        saved_id = save_health_check(
            validate(mismatch_payload(keys[0], "m/48'/9'/0'/2'"), keys),
            self.database_path,
        )
        record = get_health_check(saved_id, self.database_path)
        key_check = record["key_checks"][0]

        # The recorded path and the key note are kept, while everything else
        # stays empty (section 25.1).
        self.assertEqual(key_check["address_path"], "m/48'/9'/0'/2'")
        self.assertEqual(key_check["address_path_verified"], "PROBLEM")
        self.assertEqual(key_check["comments"], "Path read from the device")
        self.assertIsNone(key_check["hardware_works"])
        self.assertIsNone(key_check["firmware_version"])
        self.assertIsNone(key_check["seed_backup_verified"])
        self.assertIsNone(record["wallet_software"])
        self.assertEqual(record["software_compatibility_status"], "NOT_ASSESSED")
        self.assertEqual(record["ai_security_checks"], [])
        self.assertEqual(record["comments"], "Annual review")

    def test_the_stored_name_is_recorded_as_the_provider_label(self):
        keys = self.prepare(RENAMED_SETUP)
        cloud_key = keys[0]

        saved_id = save_health_check(
            validate(sample_payload(cloud_key), keys), self.database_path
        )
        record = get_health_check(saved_id, self.database_path)

        self.assertEqual(record["wallet_software"], "Coinbase")
        self.assertEqual(
            [entry["provider"] for entry in record["ai_security_checks"]], ["Coinbase"]
        )
        self.assertEqual(record["key_checks"][0]["name"], "Coinbase")
        self.assertEqual(record["key_checks"][0]["type"], "cloud")

    def test_the_settings_rename_a_key_and_change_its_path(self):
        keys = self.prepare()
        first = keys[0]

        save_key_settings(first["id"], "ColdCard", "m/48'/3'/0'/2'", self.database_path)
        stored = list_keys(self.database_path)[0]

        # The name is only a label, so it can be changed at any time
        # (sections 25.1 and 25.2).
        self.assertEqual(stored["name"], "ColdCard")
        self.assertEqual(stored["address_path"], "m/48'/3'/0'/2'")
        self.assertEqual(stored["type"], "hardware")

    def test_key_has_check_reports_a_saved_check(self):
        keys = self.prepare()

        self.assertFalse(key_has_check(keys[0]["id"], self.database_path))

        save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )

        self.assertTrue(key_has_check(keys[0]["id"], self.database_path))
        self.assertFalse(key_has_check(keys[1]["id"], self.database_path))

    def test_saving_the_settings_of_an_unknown_key_is_an_error(self):
        self.prepare()

        with self.assertRaises(ValueError):
            save_key_settings(999, "ColdCard", DEFAULT_ADDRESS_PATH, self.database_path)

    def test_rotating_an_unknown_key_is_an_error(self):
        self.prepare()

        with self.assertRaises(ValueError):
            rotate_key(999, "ColdCard", "m/48'/7'/0'/2'", self.database_path)

    def test_an_acknowledgement_is_stored_with_the_check_and_the_key_it_closed(self):
        keys = self.prepare()
        saved_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )

        acknowledgement_id = save_alert_acknowledgement(
            "address_path_mismatch",
            "Key 1: SeedSigner",
            keys[0]["id"],
            saved_id,
            "rotate",
            self.database_path,
        )

        self.assertIsNotNone(acknowledgement_id)
        stored = list_alert_acknowledgements(self.database_path)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["code"], "address_path_mismatch")
        self.assertEqual(stored[0]["source"], "Key 1: SeedSigner")
        self.assertEqual(stored[0]["check_id"], saved_id)
        # The stored reason is the action that closed the alert, and the key is
        # the key the alert belonged to (sections 26.4 and 27).
        self.assertEqual(stored[0]["reason"], "rotate")
        self.assertEqual(stored[0]["key_id"], keys[0]["id"])
        self.assertTrue(stored[0]["acknowledged_at"])

    def test_a_software_acknowledgement_is_stored_without_a_key(self):
        keys = self.prepare()
        saved_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )

        save_alert_acknowledgement(
            "software_incompatible",
            "Sparrow Wallet",
            None,
            saved_id,
            "remove_software",
            self.database_path,
        )

        stored = list_alert_acknowledgements(self.database_path)
        # A software alert raised by the settings list belongs to no key
        # (section 27).
        self.assertIsNone(stored[0]["key_id"])

    def test_acknowledgements_can_be_filtered_by_the_check_they_closed(self):
        keys = self.prepare()
        first_id = save_health_check(validate(sample_payload(keys[0]), keys), self.database_path)
        second_id = save_health_check(validate(sample_payload(keys[1]), keys), self.database_path)
        save_alert_acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", keys[0]["id"], first_id, "rotate", self.database_path
        )
        save_alert_acknowledgement(
            "hardware_failure", "Key 2: Blockstream Jade", keys[1]["id"], second_id,
            "replace_hardware", self.database_path,
        )
        save_alert_acknowledgement(
            "software_incompatible", "Sparrow Wallet", None, second_id,
            "remove_software", self.database_path,
        )

        self.assertEqual(
            [
                entry["code"]
                for entry in list_alert_acknowledgements(self.database_path, check_id=first_id)
            ],
            ["key_unavailable"],
        )
        self.assertEqual(
            [
                entry["code"]
                for entry in list_alert_acknowledgements(self.database_path, check_id=second_id)
            ],
            ["software_incompatible", "hardware_failure"],
        )

    def test_each_key_can_be_recorded_separately(self):
        keys = self.prepare()

        for key in keys:
            data = validate(sample_payload(key), keys)
            saved_id = save_health_check(data, self.database_path)
            record = get_health_check(saved_id, self.database_path)
            self.assertEqual(record["key_checks"][0]["key_number"], key["key_number"])

        summaries = list_health_checks(self.database_path)
        self.assertEqual([entry["key_numbers"] for entry in summaries], [[3], [2], [1]])

    def test_key_status_has_no_dates_before_anything_is_saved(self):
        self.prepare()

        status = list_key_status(self.database_path)

        self.assertEqual([entry["key_number"] for entry in status], [1, 2, 3])
        self.assertEqual([entry["name"] for entry in status], ["SeedSigner", "Blockstream Jade", "Nunchuk"])
        self.assertEqual([entry["type"] for entry in status], ["hardware", "hardware", "cloud"])
        self.assertEqual([entry["last_checked_at"] for entry in status], [None, None, None])
        self.assertEqual([entry["next_check_due"] for entry in status], [None, None, None])

    def test_key_status_reports_the_newest_check_per_key(self):
        keys = self.prepare()

        older = sample_payload(keys[0])
        older["checked_at"] = "2025-10-01"
        save_health_check(validate(older, keys), self.database_path)

        newer = sample_payload(keys[0])
        newer["checked_at"] = "2026-10-01"
        save_health_check(validate(newer, keys), self.database_path)

        cloud = sample_payload(keys[2])
        cloud["checked_at"] = "2026-05-01"
        save_health_check(validate(cloud, keys), self.database_path)

        status = {entry["key_number"]: entry for entry in list_key_status(self.database_path)}

        self.assertEqual(status[1]["last_checked_at"], "2026-10-01")
        self.assertEqual(status[1]["next_check_due"], "2027-10-01")
        self.assertEqual(status[3]["last_checked_at"], "2026-05-01")
        self.assertEqual(status[3]["next_check_due"], "2027-05-01")
        self.assertIsNone(status[2]["last_checked_at"])
        self.assertIsNone(status[2]["next_check_due"])

    def test_previous_values_are_empty_before_anything_is_saved(self):
        self.prepare()

        values = list_previous_values(self.database_path)

        self.assertEqual([entry["key_id"] for entry in values["keys"]], [1, 2, 3])
        self.assertEqual([entry["firmware_version"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["address_path"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["wallet_software"] for entry in values["keys"]], [None, None, None])
        self.assertEqual([entry["software_version"] for entry in values["keys"]], [None, None, None])

    def test_previous_values_return_the_newest_saved_values(self):
        keys = self.prepare()

        older = sample_payload(keys[0])
        older["checked_at"] = "2025-10-01"
        older["software_version"] = "1.7.0"
        older["key_check"]["firmware_version"] = "0.9.0"
        save_health_check(validate(older, keys), self.database_path)

        newer = sample_payload(keys[0])
        newer["checked_at"] = "2026-10-01"
        newer["software_version"] = "1.8.0"
        newer["key_check"]["firmware_version"] = "1.0.0"
        save_health_check(validate(newer, keys), self.database_path)

        cloud = sample_payload(keys[2])
        cloud["checked_at"] = "2026-05-01"
        cloud["software_version"] = "1.9.0"
        save_health_check(validate(cloud, keys), self.database_path)

        values = list_previous_values(self.database_path)
        by_key = {entry["key_id"]: entry for entry in values["keys"]}

        self.assertEqual(by_key[1]["firmware_version"], "1.0.0")
        self.assertEqual(by_key[1]["address_path"], DEFAULT_ADDRESS_PATH)
        self.assertEqual(by_key[1]["wallet_software"], "Sparrow Wallet")
        self.assertEqual(by_key[1]["software_version"], "1.8.0")
        self.assertEqual(by_key[3]["wallet_software"], "Nunchuk")
        self.assertEqual(by_key[3]["software_version"], "1.9.0")
        self.assertIsNone(by_key[2]["firmware_version"])

    def test_export_rows_are_empty_before_anything_is_saved(self):
        self.prepare()

        self.assertEqual(list_export_rows(self.database_path), [])

    def test_export_rows_join_the_security_statuses(self):
        keys = self.prepare()

        saved_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )
        save_health_check(
            validate(sample_payload(keys[2]), keys), self.database_path
        )

        rows = list_export_rows(self.database_path)

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["check_id"], saved_id)
        self.assertEqual(first["checked_at"], "2026-10-01")
        self.assertEqual(first["next_check_due"], "2027-10-01")
        self.assertEqual(first["key_number"], 1)
        self.assertEqual(first["key_name"], "SeedSigner")
        self.assertEqual(first["key_type"], "hardware")
        self.assertEqual(first["seed_backup_verified"], "OK")
        self.assertEqual(first["address_path_verified"], "OK")
        self.assertEqual(first["address_path"], DEFAULT_ADDRESS_PATH)
        self.assertEqual(first["wallet_software"], "Sparrow Wallet")
        self.assertEqual(first["contact_info_verified"], "Confirmed current")
        self.assertEqual(
            first["security_status"],
            "SeedSigner: SECURE; Sparrow Wallet: SECURE",
        )
        # A check without a closure has an empty cell (section 27).
        self.assertEqual(first["closed_alerts"], "")

        cloud = rows[1]
        self.assertEqual(cloud["key_number"], 3)
        self.assertEqual(cloud["key_name"], "Nunchuk")
        self.assertEqual(cloud["wallet_software"], "Nunchuk")
        self.assertEqual(cloud["security_status"], "Nunchuk: SECURE")

    def test_export_rows_include_every_closure_of_the_check(self):
        keys = self.prepare()
        saved_id = save_health_check(
            validate(sample_payload(keys[0]), keys), self.database_path
        )
        save_alert_acknowledgement(
            "key_unavailable", "Key 1: SeedSigner", keys[0]["id"], saved_id,
            "rotate", self.database_path,
        )
        # A closure of a software alert belongs to no key, but it hangs on the
        # same check through its check_id, so it is listed as well
        # (sections 27 and 32.8 point 6).
        save_alert_acknowledgement(
            "software_incompatible", "Sparrow Wallet", None, saved_id,
            "remove_software", self.database_path,
        )

        rows = list_export_rows(self.database_path)

        self.assertEqual(len(rows), 1)
        closed = rows[0]["closed_alerts"]
        # Both closures are listed, in the order they were written, with the
        # source of the alert, the code, the action and the date. The source is
        # what tells the key form and the software form of one code apart
        # (sections 27, 32.8 point 6 and 32.9 point 1).
        self.assertRegex(
            closed,
            r"^Key 1: SeedSigner — key_unavailable: rotate \(\d{4}-\d{2}-\d{2}\)",
        )
        self.assertRegex(
            closed,
            r"Sparrow Wallet — software_incompatible: remove_software \(\d{4}-\d{2}-\d{2}\)$",
        )

    def test_invalid_status_and_duplicate_key_numbers_are_rejected(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO health_checks (checked_at, next_check_due, software_compatibility_status) "
                    "VALUES ('2026-01-01', '2027-01-01', 'UNKNOWN')"
                )

            connection.execute(
                "INSERT INTO keys (key_number, name, type) VALUES (1, 'ColdCard', 'hardware')"
            )
            # A second active row for the same slot is refused by the partial
            # unique index (section 32.8 point 5).
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO keys (key_number, name, type) VALUES (1, 'Duplicate', 'hardware')"
                )

    def test_ai_security_status_is_limited_to_the_english_values(self):
        initialize_database(self.database_path)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO health_checks (checked_at, next_check_due) VALUES (?, ?)",
                ("2026-01-01", "2027-01-01"),
            )
            health_check_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                (health_check_id, "SeedSigner", "SECURE"),
            )
            for value in ("TRYGG", "UNKNOWN"):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO ai_security_checks (health_check_id, provider, status) VALUES (?, ?, ?)",
                        (health_check_id, "Nunchuk", value),
                    )

    def test_unknown_future_schema_version_is_rejected(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            initialize_database(self.database_path)


if __name__ == "__main__":
    unittest.main()
