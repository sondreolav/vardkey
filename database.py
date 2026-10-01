"""SQLite schema, initialization, and storage for Helsesjekk."""

from pathlib import Path
import sqlite3


SCHEMA_VERSION = 4
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
        software_comments TEXT,
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
        address_verified INTEGER CHECK (address_verified IN (0, 1)),
        seed_backup_verified INTEGER CHECK (seed_backup_verified IN (0, 1)),
        address_path_verified INTEGER CHECK (address_path_verified IN (0, 1)),
        derivation_height TEXT,
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
OPTIONAL_COLUMNS = (
    ("key_checks", "address_verified", "INTEGER CHECK (address_verified IN (0, 1))"),
    ("key_checks", "derivation_height", "TEXT"),
    ("health_checks", "software_comments", "TEXT"),
    ("key_checks", "seed_backup_verified", "INTEGER CHECK (seed_backup_verified IN (0, 1))"),
)


def initialize_database(database_path="data/helsesjekk.sqlite3"):
    """Create the schema and safely add missing columns to existing databases."""
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

        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            for table, column, definition in OPTIONAL_COLUMNS:
                _ensure_column(connection, table, column, definition)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    return path


def _ensure_column(connection, table, column, definition):
    """Add a table column only when it is missing."""
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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


def save_health_check(data, database_path="data/helsesjekk.sqlite3"):
    """Store one validated health check together with its related rows."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO health_checks (
                    checked_at, next_check_due, software_compatibility_status,
                    sparrow_version, nunchuk_version, software_comments,
                    contact_info_verified, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["checked_at"],
                    data["next_check_due"],
                    data["software_compatibility_status"],
                    data["sparrow_version"],
                    data["nunchuk_version"],
                    data["software_comments"],
                    data["contact_info_verified"],
                    data["comments"],
                ),
            )
            health_check_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO key_checks (
                    health_check_id, key_id, available, hardware_works, firmware_version,
                    seed_backup_status, seed_backup_verified, cloud_health_status,
                    cloud_provider_operational, address_verified, derivation_height,
                    address_path_verified, address_path, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        health_check_id,
                        entry["key_id"],
                        entry["available"],
                        entry["hardware_works"],
                        entry["firmware_version"],
                        entry["seed_backup_status"],
                        entry["seed_backup_verified"],
                        entry["cloud_health_status"],
                        entry["cloud_provider_operational"],
                        entry["address_verified"],
                        entry["derivation_height"],
                        entry["address_path_verified"],
                        entry["address_path"],
                        entry["comments"],
                    )
                    for entry in data["key_checks"]
                ],
            )
            connection.executemany(
                """
                INSERT INTO tool_checks (
                    health_check_id, product, bip327_status, slip39_status,
                    version, checked_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        health_check_id,
                        entry["product"],
                        entry["bip327_status"],
                        entry["slip39_status"],
                        entry["version"],
                        entry["checked_at"],
                        entry["notes"],
                    )
                    for entry in data["tool_checks"]
                ],
            )
            connection.executemany(
                """
                INSERT INTO ai_security_checks (health_check_id, provider, status, comments)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (health_check_id, entry["provider"], entry["status"], entry["comments"])
                    for entry in data["ai_security_checks"]
                ],
            )
        return health_check_id
    finally:
        connection.close()


def list_health_checks(database_path="data/helsesjekk.sqlite3"):
    """Return saved health check summaries, newest first."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, checked_at, next_check_due, software_compatibility_status,
                   contact_info_verified, comments
            FROM health_checks
            ORDER BY checked_at DESC, id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_health_check(health_check_id, database_path="data/helsesjekk.sqlite3"):
    """Return one saved health check with its related rows, or None."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        record = connection.execute(
            """
            SELECT id, checked_at, next_check_due, software_compatibility_status,
                   sparrow_version, nunchuk_version, software_comments,
                   contact_info_verified, comments
            FROM health_checks WHERE id = ?
            """,
            (health_check_id,),
        ).fetchone()
        if record is None:
            return None

        result = dict(record)
        result["key_checks"] = [
            dict(row)
            for row in connection.execute(
                """
                SELECT kc.id, kc.key_id, k.key_number, k.name, k.type, k.device,
                       kc.available, kc.hardware_works, kc.firmware_version,
                       kc.seed_backup_status, kc.seed_backup_verified,
                       kc.cloud_health_status, kc.cloud_provider_operational,
                       kc.address_verified, kc.derivation_height,
                       kc.address_path_verified, kc.address_path, kc.comments
                FROM key_checks AS kc
                JOIN keys AS k ON k.id = kc.key_id
                WHERE kc.health_check_id = ?
                ORDER BY k.key_number
                """,
                (health_check_id,),
            )
        ]
        result["tool_checks"] = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, product, bip327_status, slip39_status, version, checked_at, notes
                FROM tool_checks WHERE health_check_id = ?
                ORDER BY id
                """,
                (health_check_id,),
            )
        ]
        result["ai_security_checks"] = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, provider, status, comments
                FROM ai_security_checks WHERE health_check_id = ?
                ORDER BY id
                """,
                (health_check_id,),
            )
        ]
        return result
    finally:
        connection.close()
