"""SQLite schema and initialization for Helsesjekk."""

from pathlib import Path
import sqlite3


SCHEMA_VERSION = 1
FIXED_KEYS = (
    (1, "SeedSigner", "hardware", "SeedSigner"),
    (2, "Blockstream Jade", "hardware", "Blockstream Jade"),
    (3, "Nunchuk", "cloud", "Nunchuk"),
)
SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        device TEXT NOT NULL CHECK (device IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS health_checks (
        id INTEGER PRIMARY KEY,
        checked_at TEXT NOT NULL,
        next_check_due TEXT NOT NULL,
        software_compatibility_status TEXT NOT NULL DEFAULT 'IKKJE_VURDERT'
            CHECK (software_compatibility_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        sparrow_version TEXT,
        nunchuk_version TEXT,
        contact_info_verified INTEGER CHECK (contact_info_verified IN (0, 1)),
        comments TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS key_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        key_id INTEGER NOT NULL REFERENCES keys(id) ON DELETE RESTRICT,
        available INTEGER CHECK (available IN (0, 1)),
        hardware_works INTEGER CHECK (hardware_works IN (0, 1)),
        firmware_version TEXT,
        seed_backup_status TEXT CHECK (seed_backup_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        cloud_health_status TEXT CHECK (cloud_health_status IN ('OK', 'PROBLEM', 'IKKJE_VURDERT')),
        cloud_provider_operational INTEGER CHECK (cloud_provider_operational IN (0, 1)),
        address_path_verified INTEGER CHECK (address_path_verified IN (0, 1)),
        address_path TEXT,
        comments TEXT,
        UNIQUE (health_check_id, key_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_checks (
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK (provider IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        status TEXT NOT NULL CHECK (status IN ('TRYGG', 'PATCHA', 'SÅRBAR', 'KOMPROMITTERT')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON health_checks(checked_at DESC)",
)


def initialize_database(database_path="data/helsesjekk.sqlite3"):
    """Create the database and apply schema migrations up to the current version."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=5)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than supported version {SCHEMA_VERSION}"
            )

        if version < 1:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for statement in SCHEMA_STATEMENTS:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    finally:
        connection.close()

    return path


def seed_fixed_keys(database_path="data/helsesjekk.sqlite3"):
    """Ensure the three fixed key profiles exist without overwriting custom names."""
    connection = sqlite3.connect(database_path, timeout=5)
    try:
        with connection:
            for key_number, name, key_type, device in FIXED_KEYS:
                connection.execute(
                    """
                    INSERT INTO keys (key_number, name, type, device)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key_number) DO UPDATE SET
                        type = excluded.type,
                        device = excluded.device
                    """,
                    (key_number, name, key_type, device),
                )
    finally:
        connection.close()


def list_keys(database_path="data/helsesjekk.sqlite3"):
    """Return the configured key profiles in display order."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, key_number, name, type, device, created_at
            FROM keys
            ORDER BY key_number
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
