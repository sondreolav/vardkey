"""SQLite schema, initialization, and storage for Helsesjekk."""

from pathlib import Path
import sqlite3


SCHEMA_VERSION = 5
FIXED_KEYS = (
    (1, "SeedSigner", "hardware", "SeedSigner"),
    (2, "Blockstream Jade", "hardware", "Blockstream Jade"),
    (3, "Nunchuk", "cloud", "Nunchuk"),
)
KEYS_TABLE = """
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        device TEXT NOT NULL CHECK (device IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
HEALTH_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS health_checks (
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
    )
    """
KEY_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS key_checks (
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
    )
    """
TOOL_CHECKS_TABLE = """
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
    """
AI_SECURITY_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS ai_security_checks (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK (provider IN ('SeedSigner', 'Blockstream Jade', 'Nunchuk', 'Sparrow Wallet')),
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    )
    """
SCHEMA_STATEMENTS = (
    KEYS_TABLE,
    HEALTH_CHECKS_TABLE,
    KEY_CHECKS_TABLE,
    TOOL_CHECKS_TABLE,
    AI_SECURITY_CHECKS_TABLE,
)
OPTIONAL_COLUMNS = (
    ("health_checks", "software_comments", "TEXT"),
    ("health_checks", "wallet_software", "TEXT"),
    ("health_checks", "software_version", "TEXT"),
)
INDEX_STATEMENTS = (
    (
        "health_checks",
        "checked_at",
        "CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON health_checks(checked_at DESC)",
    ),
)
# Columns that only exist in the pre-section-19 key_checks layout.
LEGACY_KEY_CHECK_COLUMNS = ("seed_backup_status", "address_verified", "derivation_height")
# Value mapping used when the security status values became English.
SECURITY_STATUS_MIGRATION = (
    ("TRYGG", "SECURE"),
    ("PATCHA", "PATCHED"),
    ("SÅRBAR", "VULNERABLE"),
    ("KOMPROMITTERT", "COMPROMISED"),
)
# The newest saved check per key, used by the dashboard and the form. Duplicated
# on purpose so the queries stay readable without a window function.
_LATEST_CHECK_QUERY = """
    SELECT {expression}
    FROM key_checks AS kc
    JOIN health_checks AS hc ON hc.id = kc.health_check_id
    WHERE kc.key_id = k.id
    ORDER BY hc.checked_at DESC, hc.id DESC
    LIMIT 1
"""


def initialize_database(database_path="data/helsesjekk.sqlite3"):
    """Create the schema and safely migrate existing databases."""
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
            _migrate_key_checks(connection)
            _migrate_ai_security_checks(connection)
            for table, column, statement in INDEX_STATEMENTS:
                _ensure_index(connection, table, column, statement)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    return path


def _table_columns(connection, table):
    """Return the column names of a table, or an empty set when it is missing."""
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def _table_sql(connection, table):
    """Return the stored CREATE statement of a table, or None when it is missing."""
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row[0] if row else None


def _ensure_column(connection, table, column, definition):
    """Add a table column only when it is missing."""
    if column not in _table_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_index(connection, table, column, statement):
    """Create an index only when its table has the indexed column.

    A partially migrated database can contain the table without the column, and
    creating the index would then fail. Such a database cannot serve health
    checks until the column exists, so the index is skipped instead.
    """
    if column in _table_columns(connection, table):
        connection.execute(statement)


def _column_or_null(columns, name):
    """Return the column name, or a NULL literal when the column is missing."""
    return name if name in columns else "NULL"


def _verification_expression(columns, mappings):
    """Build a CASE expression that maps legacy values to OK or PROBLEM.

    Each mapping is a (column, SQL value, result) triple. Mappings are evaluated
    in order, so the preferred source column must come first.
    """
    cases = [
        f"WHEN {column} = {value} THEN '{result}'"
        for column, value, result in mappings
        if column in columns
    ]
    if not cases:
        return "NULL"
    return "CASE " + " ".join(cases) + " ELSE NULL END"


def _migrate_key_checks(connection):
    """Rebuild key_checks when it still uses the pre-section-19 layout.

    The legacy table stored the verification results as 0/1 flags and kept the
    removed columns seed_backup_status, address_verified, and derivation_height.
    SQLite cannot change a CHECK constraint, so the table is rebuilt once and the
    legacy flags are folded into the OK/PROBLEM values.
    """
    columns = _table_columns(connection, "key_checks")
    if not columns or not set(LEGACY_KEY_CHECK_COLUMNS) & columns:
        return

    connection.execute("ALTER TABLE key_checks RENAME TO key_checks_legacy")
    connection.execute(KEY_CHECKS_TABLE)
    if {"health_check_id", "key_id"} <= columns:
        seed_backup = _verification_expression(columns, (
            ("seed_backup_verified", 1, "OK"),
            ("seed_backup_verified", 0, "PROBLEM"),
            ("seed_backup_status", "'OK'", "OK"),
            ("seed_backup_status", "'PROBLEM'", "PROBLEM"),
        ))
        address_path = _verification_expression(columns, (
            ("address_path_verified", 1, "OK"),
            ("address_path_verified", 0, "PROBLEM"),
            ("address_verified", 1, "OK"),
            ("address_verified", 0, "PROBLEM"),
        ))
        connection.execute(f"""
            INSERT INTO key_checks (
                id, health_check_id, key_id, available, hardware_works, firmware_version,
                seed_backup_verified, cloud_health_status, cloud_provider_operational,
                address_path_verified, address_path, comments
            )
            SELECT
                {_column_or_null(columns, "id")},
                health_check_id,
                key_id,
                {_column_or_null(columns, "available")},
                {_column_or_null(columns, "hardware_works")},
                {_column_or_null(columns, "firmware_version")},
                {seed_backup},
                {_column_or_null(columns, "cloud_health_status")},
                {_column_or_null(columns, "cloud_provider_operational")},
                {address_path},
                {_column_or_null(columns, "address_path")},
                {_column_or_null(columns, "comments")}
            FROM key_checks_legacy
            WHERE health_check_id IS NOT NULL AND key_id IS NOT NULL
        """)
    connection.execute("DROP TABLE key_checks_legacy")


def _migrate_ai_security_checks(connection):
    """Rebuild ai_security_checks when it still allows the Norwegian values."""
    sql = _table_sql(connection, "ai_security_checks")
    if sql is None or "SECURE" in sql:
        return

    connection.execute("ALTER TABLE ai_security_checks RENAME TO ai_security_checks_legacy")
    connection.execute(AI_SECURITY_CHECKS_TABLE)
    cases = " ".join(
        f"WHEN '{old}' THEN '{new}'" for old, new in SECURITY_STATUS_MIGRATION
    )
    connection.execute(f"""
        INSERT INTO ai_security_checks (id, health_check_id, provider, status, comments)
        SELECT id, health_check_id, provider,
               CASE status {cases} ELSE status END,
               comments
        FROM ai_security_checks_legacy
    """)
    connection.execute("DROP TABLE ai_security_checks_legacy")


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
    """Store one validated health check for a single key together with its rows."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO health_checks (
                    checked_at, next_check_due, wallet_software, software_version,
                    software_compatibility_status, software_comments,
                    contact_info_verified, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["checked_at"],
                    data["next_check_due"],
                    data["wallet_software"],
                    data["software_version"],
                    data["software_compatibility_status"],
                    data["software_comments"],
                    data["contact_info_verified"],
                    data["comments"],
                ),
            )
            health_check_id = cursor.lastrowid
            key_check = data["key_check"]
            connection.execute(
                """
                INSERT INTO key_checks (
                    health_check_id, key_id, available, hardware_works, firmware_version,
                    seed_backup_verified, cloud_health_status, cloud_provider_operational,
                    address_path_verified, address_path, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    health_check_id,
                    key_check["key_id"],
                    key_check["available"],
                    key_check["hardware_works"],
                    key_check["firmware_version"],
                    key_check["seed_backup_verified"],
                    key_check["cloud_health_status"],
                    key_check["cloud_provider_operational"],
                    key_check["address_path_verified"],
                    key_check["address_path"],
                    key_check["comments"],
                ),
            )
            connection.executemany(
                """
                INSERT INTO tool_checks (
                    health_check_id, product, bip327_status, slip39_status
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        health_check_id,
                        entry["product"],
                        entry["bip327_status"],
                        entry["slip39_status"],
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
    """Return saved health check summaries, newest first.

    Each summary carries the key numbers of the check, so the history can show
    which key a submission belongs to.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, checked_at, next_check_due, software_compatibility_status,
                   wallet_software, contact_info_verified, comments
            FROM health_checks
            ORDER BY checked_at DESC, id DESC
            """
        ).fetchall()
        summaries = [dict(row) for row in rows]
        if summaries:
            placeholders = ", ".join("?" for _ in summaries)
            key_rows = connection.execute(
                f"""
                SELECT kc.health_check_id, k.key_number
                FROM key_checks AS kc
                JOIN keys AS k ON k.id = kc.key_id
                WHERE kc.health_check_id IN ({placeholders})
                ORDER BY k.key_number
                """,
                [entry["id"] for entry in summaries],
            ).fetchall()
            numbers = {}
            for row in key_rows:
                numbers.setdefault(row["health_check_id"], []).append(row["key_number"])
            for entry in summaries:
                entry["key_numbers"] = numbers.get(entry["id"], [])
        return summaries
    finally:
        connection.close()


def list_key_status(database_path="data/helsesjekk.sqlite3"):
    """Return each key with the dates of its newest saved check.

    A key that has never been checked has no dates. Whether a date is overdue is
    left to the caller, so this function stays independent of the current date.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            f"""
            SELECT k.id AS key_id, k.key_number, k.name, k.type, k.device,
                   ({_LATEST_CHECK_QUERY.format(expression="hc.checked_at")}) AS last_checked_at,
                   ({_LATEST_CHECK_QUERY.format(expression="hc.next_check_due")}) AS next_check_due
            FROM keys AS k
            ORDER BY k.key_number
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def list_previous_values(database_path="data/helsesjekk.sqlite3"):
    """Return the most recently saved values, for pre-filling the form.

    ``keys`` carries the last recorded firmware version, address path, wallet
    software, and software version for each key. ``security`` carries the last
    recorded security status for each provider, whatever key recorded it. Both
    are used for the placeholders and for carrying hidden fields forward.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        keys = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT k.id AS key_id,
                       ({_LATEST_CHECK_QUERY.format(expression="kc.firmware_version")}) AS firmware_version,
                       ({_LATEST_CHECK_QUERY.format(expression="kc.address_path")}) AS address_path,
                       ({_LATEST_CHECK_QUERY.format(expression="hc.wallet_software")}) AS wallet_software,
                       ({_LATEST_CHECK_QUERY.format(expression="hc.software_version")}) AS software_version
                FROM keys AS k
                ORDER BY k.key_number
                """
            ).fetchall()
        ]
        security = {}
        for row in connection.execute(
            """
            SELECT acs.provider, acs.status
            FROM ai_security_checks AS acs
            JOIN health_checks AS hc ON hc.id = acs.health_check_id
            ORDER BY hc.checked_at DESC, hc.id DESC, acs.id DESC
            """
        ):
            security.setdefault(row["provider"], row["status"])
        return {"keys": keys, "security": security}
    finally:
        connection.close()


def list_export_rows(database_path="data/helsesjekk.sqlite3"):
    """Return one row per key check for the report export, oldest first.

    Every row is one key check. ``check_id`` identifies the submission it belongs
    to, so rows saved before section 19 (up to three keys in one submission) stay
    grouped. The per-product and per-provider results are joined into a single
    text cell, because they have more than one value per submission.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT hc.id AS check_id, hc.checked_at, hc.next_check_due,
                   hc.wallet_software, hc.software_version,
                   hc.software_compatibility_status, hc.software_comments,
                   hc.contact_info_verified, hc.comments,
                   kc.key_id, k.key_number, k.name AS key_name, k.type AS key_type,
                   kc.available, kc.hardware_works, kc.firmware_version,
                   kc.seed_backup_verified, kc.cloud_health_status,
                   kc.cloud_provider_operational, kc.address_path_verified,
                   kc.address_path, kc.comments AS key_comments
            FROM key_checks AS kc
            JOIN health_checks AS hc ON hc.id = kc.health_check_id
            JOIN keys AS k ON k.id = kc.key_id
            ORDER BY hc.checked_at, hc.id, k.key_number
            """
        ).fetchall()
        result = [dict(row) for row in rows]
        bip327 = _grouped_values(connection, "tool_checks", "product", "bip327_status")
        slip39 = _grouped_values(connection, "tool_checks", "product", "slip39_status")
        security = _grouped_values(connection, "ai_security_checks", "provider", "status")
        for row in result:
            row["bip327_status"] = bip327.get(row["check_id"], "")
            row["slip39_status"] = slip39.get(row["check_id"], "")
            row["security_status"] = security.get(row["check_id"], "")
        return result
    finally:
        connection.close()


def _grouped_values(connection, table, label_column, value_column):
    """Return {check_id: "Label: value; Label: value"} for one related table."""
    rows = connection.execute(
        f"SELECT health_check_id, {label_column}, {value_column} FROM {table} ORDER BY id"
    ).fetchall()
    grouped = {}
    for row in rows:
        entry = f"{row[label_column]}: {row[value_column]}"
        grouped.setdefault(row["health_check_id"], []).append(entry)
    return {check_id: "; ".join(values) for check_id, values in grouped.items()}


def get_health_check(health_check_id, database_path="data/helsesjekk.sqlite3"):
    """Return one saved health check with its related rows, or None."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        record = connection.execute(
            """
            SELECT id, checked_at, next_check_due, wallet_software, software_version,
                   software_compatibility_status, sparrow_version, nunchuk_version,
                   software_comments, contact_info_verified, comments
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
                       kc.seed_backup_verified, kc.cloud_health_status,
                       kc.cloud_provider_operational, kc.address_path_verified,
                       kc.address_path, kc.comments
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
