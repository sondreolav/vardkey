"""SQLite schema, initialization, and storage for Helsesjekk."""

from datetime import datetime
from pathlib import Path
import sqlite3


# Version 10 adds the key address path, the wallet software list, and the alert
# acknowledgements, and drops the two derived cloud results from key_checks
# (sections 25.1, 25.4 and 25.6).
SCHEMA_VERSION = 10
# The app always supports exactly three key slots (section 23.2).
KEY_COUNT = 3
# A database without any wallet software entry starts with this one, so a
# hardware key has a choice from the first check on. The list is stored whole,
# and this entry may be replaced once another one has been added (section 25.4).
DEFAULT_WALLET_SOFTWARE = "Sparrow Wallet"
# Table definitions use a {table} placeholder, so a migration can create the same
# table under a temporary name while it rebuilds it.
KEYS_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY,
        key_number INTEGER NOT NULL UNIQUE CHECK (key_number BETWEEN 1 AND 3),
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('hardware', 'cloud')),
        address_path TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
HEALTH_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
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
    )
    """
# The two derived cloud results are gone: a cloud key records only its
# availability (section 25.6).
KEY_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
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
    )
    """
# The provider is the key's configured name and the selected wallet software, so
# the column holds free text (section 23.3).
AI_SECURITY_CHECKS_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY,
        health_check_id INTEGER NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('SECURE', 'PATCHED', 'VULNERABLE', 'COMPROMISED')),
        comments TEXT,
        UNIQUE (health_check_id, provider)
    )
    """
# The wallet software list the user maintains in the settings, stored whole
# (section 25.4).
WALLET_SOFTWARE_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
# One row per acknowledged alert. ``check_id`` is the newest check that raised
# the alert when it was acknowledged, so a newer check for the same code and
# source raises it again (section 25.3).
ALERT_ACKNOWLEDGEMENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL,
        source TEXT NOT NULL,
        check_id INTEGER,
        reason TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL
    )
    """
TABLES = (
    ("keys", KEYS_TABLE),
    ("health_checks", HEALTH_CHECKS_TABLE),
    ("key_checks", KEY_CHECKS_TABLE),
    ("ai_security_checks", AI_SECURITY_CHECKS_TABLE),
    ("wallet_software", WALLET_SOFTWARE_TABLE),
    ("alert_acknowledgements", ALERT_ACKNOWLEDGEMENTS_TABLE),
)
# The address path is part of the key's identity and is written by the setup
# step (section 25.1). It is added to a database that predates version 10.
OPTIONAL_COLUMNS = (
    ("keys", "address_path", "TEXT NOT NULL DEFAULT ''"),
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
# Columns that were dropped when a cloud key stopped recording derived results
# (section 25.6).
REMOVED_CLOUD_COLUMNS = ("cloud_health_status", "cloud_provider_operational")
# Value mapping used when the security status values became English.
SECURITY_STATUS_MIGRATION = (
    ("TRYGG", "SECURE"),
    ("PATCHA", "PATCHED"),
    ("SÅRBAR", "VULNERABLE"),
    ("KOMPROMITTERT", "COMPROMISED"),
)
# Value mapping used when the general status values became English (section 21).
# "IKKJE_VURDERT" is the marker of a pre-section-21 table.
NOT_ASSESSED_MIGRATION = (("IKKJE_VURDERT", "NOT_ASSESSED"),)
LEGACY_STATUS_VALUE = "IKKJE_VURDERT"
# The contact confirmation was stored as 0/1 before section 23.1 replaced the
# flag with the two contact statuses. This substring marks a pre-section-23.1
# health_checks table.
LEGACY_CONTACT_CHECK = "contact_info_verified IN (0, 1)"
# The provider and the wallet software used to be limited to the four fixed
# product names. A key's configured name is its label, so those lists are gone
# (section 23.3). These substrings mark a table that still has the old CHECK
# constraint.
LEGACY_PROVIDER_CHECK = "CHECK (provider IN ("
LEGACY_WALLET_SOFTWARE_CHECK = "CHECK (wallet_software IN ("
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
        # Section 21 rebuilds health_checks, which is a parent table. Foreign
        # keys are therefore disabled for the whole migration and verified
        # before the transaction commits, so an incomplete migration is never
        # kept.
        connection.execute("PRAGMA foreign_keys = OFF")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than supported version {SCHEMA_VERSION}"
            )

        connection.execute("BEGIN IMMEDIATE")
        try:
            for table, statement in TABLES:
                _create_table(connection, table, statement)
            for table, column, definition in OPTIONAL_COLUMNS:
                _ensure_column(connection, table, column, definition)
            _migrate_keys(connection)
            _migrate_key_checks(connection)
            _migrate_ai_security_checks(connection)
            _migrate_status_values(connection)
            _drop_tool_checks(connection)
            _seed_default_wallet_software(connection)
            for table, column, statement in INDEX_STATEMENTS:
                _ensure_index(connection, table, column, statement)
            _verify_foreign_keys(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        connection.execute("PRAGMA foreign_keys = ON")
    finally:
        connection.close()

    return path


def _create_table(connection, table, statement):
    """Create one table, substituting the {table} placeholder in the definition."""
    connection.execute(statement.format(table=table))


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


def _mapped_status_sql(column, mappings):
    """Build a CASE expression that rewrites one column's legacy status values.

    Values that are already current are passed through, so the expression is
    safe to use even when only part of the table still uses the old values.
    """
    cases = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in mappings)
    return f"CASE {column} {cases} ELSE {column} END"


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


def _contact_status_expression(columns):
    """Build a CASE expression that maps the pre-section-23.1 contact flag.

    The old flag answered a yes/no question, so ``0`` meant the details were not
    confirmed and is now the status ``Needs external update`` (section 23.1). A
    table without the column has no contact result at all.
    """
    if "contact_info_verified" not in columns:
        return "NULL"
    return (
        "CASE contact_info_verified"
        " WHEN 0 THEN 'Needs external update'"
        " WHEN 1 THEN 'Confirmed current'"
        " ELSE contact_info_verified END"
    )


def _create_replacement(connection, table, statement):
    """Create the temporary table a rebuild copies its rows into.

    A leftover table from an interrupted attempt is dropped first, so the copy
    can never run twice into the same table.
    """
    temporary = f"{table}_migrated"
    connection.execute(f"DROP TABLE IF EXISTS {temporary}")
    _create_table(connection, temporary, statement)
    return temporary


def _replace_table(connection, table, temporary):
    """Drop a table and let its rebuilt replacement take its place.

    Foreign keys are disabled while the migration runs, so the references from
    the child tables survive the drop. They are verified before the transaction
    commits.
    """
    connection.execute(f"DROP TABLE {table}")
    connection.execute(f"ALTER TABLE {temporary} RENAME TO {table}")


def _verify_foreign_keys(connection):
    """Abort the migration when a rebuilt table broke a foreign key."""
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(
            f"Foreign key check failed for table {violations[0][0]}"
        )


def _seed_default_wallet_software(connection):
    """Give a database without wallet software one starting entry.

    A new database starts with ``Sparrow Wallet``, so a hardware key has a
    choice from the first check on. The list is stored whole, and the entry may
    be replaced once another one has been added (section 25.4). A database whose
    list is not empty is left untouched.
    """
    count = connection.execute("SELECT COUNT(*) FROM wallet_software").fetchone()[0]
    if count == 0:
        connection.execute(
            "INSERT INTO wallet_software (name) VALUES (?)",
            (DEFAULT_WALLET_SOFTWARE,),
        )


def _migrate_keys(connection):
    """Rebuild keys when it still carries the removed device column.

    The configured name is the product label everywhere, so the fixed device
    value is gone (section 23.2). SQLite cannot drop a column from a table with
    a CHECK constraint, so the table is rebuilt once. The address path is part
    of the current definition and takes its default for the copied rows
    (section 25.1).
    """
    columns = _table_columns(connection, "keys")
    if not columns or "device" not in columns:
        return

    temporary = _create_replacement(connection, "keys", KEYS_TABLE)
    connection.execute(f"""
        INSERT INTO {temporary} (id, key_number, name, type, created_at)
        SELECT id, key_number, name, type, created_at
        FROM keys
    """)
    _replace_table(connection, "keys", temporary)


def _migrate_key_checks(connection):
    """Rebuild key_checks when it still uses the pre-section-19 layout.

    The legacy table stored the verification results as 0/1 flags and kept the
    removed columns seed_backup_status, address_verified, and derivation_height.
    SQLite cannot change a CHECK constraint, so the table is rebuilt once and the
    legacy flags are folded into the OK/PROBLEM values. The two derived cloud
    results are dropped with the rest of the old layout (section 25.6).
    """
    columns = _table_columns(connection, "key_checks")
    if not columns or not set(LEGACY_KEY_CHECK_COLUMNS) & columns:
        return

    connection.execute("ALTER TABLE key_checks RENAME TO key_checks_legacy")
    _create_table(connection, "key_checks", KEY_CHECKS_TABLE)
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
                seed_backup_verified, address_path_verified, address_path, comments
            )
            SELECT
                {_column_or_null(columns, "id")},
                health_check_id,
                key_id,
                {_column_or_null(columns, "available")},
                {_column_or_null(columns, "hardware_works")},
                {_column_or_null(columns, "firmware_version")},
                {seed_backup},
                {address_path},
                {_column_or_null(columns, "address_path")},
                {_column_or_null(columns, "comments")}
            FROM key_checks_legacy
            WHERE health_check_id IS NOT NULL AND key_id IS NOT NULL
        """)
    connection.execute("DROP TABLE key_checks_legacy")


def _migrate_ai_security_checks(connection):
    """Rebuild ai_security_checks when it still uses an older definition.

    Two changes need the same rebuild: the Norwegian status values became
    English (section 21), and the fixed provider list was dropped because the
    key's configured name is the provider label (section 23.3).
    """
    sql = _table_sql(connection, "ai_security_checks")
    if sql is None:
        return
    if "SECURE" in sql and LEGACY_PROVIDER_CHECK not in sql:
        return

    connection.execute("ALTER TABLE ai_security_checks RENAME TO ai_security_checks_legacy")
    _create_table(connection, "ai_security_checks", AI_SECURITY_CHECKS_TABLE)
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


def _migrate_status_values(connection):
    """Rewrite the tables whose stored values or CHECK constraints changed.

    Section 21 made the status values English, section 23.1 replaced the 0/1
    contact flag with the two contact statuses, section 23.3 dropped the fixed
    provider and wallet-software lists, and section 25.6 dropped the two derived
    cloud results. SQLite cannot change a CHECK constraint or drop a column from
    a table with one, so each affected table is rebuilt: the replacement is
    created under a temporary name, the rows are copied with the mapped values,
    and the replacement takes the old table's place.
    """
    if _health_checks_need_rebuild(connection):
        _rebuild_health_checks(connection)
    if _key_checks_need_rebuild(connection):
        _rebuild_key_checks(connection)


def _drop_tool_checks(connection):
    """Drop the tool_checks table and the rows it held.

    The BIP327/SLIP39 function is gone (section 24.2), so the table that held its
    results is removed with its data (section 24.4). The app is not released and
    the database is a test database, so no user history is lost. It is a child
    table, so the drop needs no rebuild of a parent table, and the rest of the
    history is kept. A database that never had the table is left untouched.
    """
    connection.execute("DROP TABLE IF EXISTS tool_checks")


def _uses_legacy_status_values(connection, table):
    """Return True while a table still allows the pre-section-21 status values."""
    sql = _table_sql(connection, table)
    return sql is not None and LEGACY_STATUS_VALUE in sql


def _health_checks_need_rebuild(connection):
    """Return True while health_checks still uses an older column definition.

    That is either the pre-section-21 status values, the pre-section-23.1
    contact flag, or the fixed wallet-software list of section 23.3.
    """
    sql = _table_sql(connection, "health_checks")
    if sql is None:
        return False
    return (
        LEGACY_STATUS_VALUE in sql
        or LEGACY_CONTACT_CHECK in sql
        or LEGACY_WALLET_SOFTWARE_CHECK in sql
    )


def _key_checks_need_rebuild(connection):
    """Return True while key_checks still uses an older column definition.

    That is either the pre-section-21 status values or a table that still holds
    the two derived cloud results (section 25.6).
    """
    sql = _table_sql(connection, "key_checks")
    if sql is None:
        return False
    return (
        LEGACY_STATUS_VALUE in sql
        or any(name in sql for name in REMOVED_CLOUD_COLUMNS)
    )


def _rebuild_health_checks(connection):
    """Rebuild health_checks with the current status, contact, and software values.

    ``IKKJE_VURDERT`` becomes ``NOT_ASSESSED`` (section 21), the 0/1 contact flag
    becomes ``Confirmed current`` or ``Needs external update`` (section 23.1),
    and the wallet software is no longer limited to the two fixed names
    (section 23.3).
    """
    columns = _table_columns(connection, "health_checks")
    temporary = _create_replacement(connection, "health_checks", HEALTH_CHECKS_TABLE)
    compatibility = _mapped_status_sql(
        "software_compatibility_status", NOT_ASSESSED_MIGRATION
    )
    contact = _contact_status_expression(columns)
    connection.execute(f"""
        INSERT INTO {temporary} (
            id, checked_at, next_check_due, wallet_software, software_version,
            software_compatibility_status, sparrow_version, nunchuk_version,
            software_comments, contact_info_verified, comments
        )
        SELECT id, checked_at, next_check_due, wallet_software, software_version,
               {compatibility},
               sparrow_version, nunchuk_version, software_comments,
               {contact}, comments
        FROM health_checks
    """)
    _replace_table(connection, "health_checks", temporary)


def _rebuild_key_checks(connection):
    """Rebuild key_checks with the current column set.

    The pre-section-21 ``IKKJE_VURDERT`` value is gone from the definition, and
    the two derived cloud results are dropped because a cloud key records only
    its availability (sections 21 and 25.6). Every surviving column is copied.
    """
    temporary = _create_replacement(connection, "key_checks", KEY_CHECKS_TABLE)
    connection.execute(f"""
        INSERT INTO {temporary} (
            id, health_check_id, key_id, available, hardware_works, firmware_version,
            seed_backup_verified, address_path_verified, address_path, comments
        )
        SELECT id, health_check_id, key_id, available, hardware_works, firmware_version,
               seed_backup_verified, address_path_verified, address_path, comments
        FROM key_checks
    """)
    _replace_table(connection, "key_checks", temporary)


def list_keys(database_path="data/helsesjekk.sqlite3"):
    """Return the stored key profiles in key order.

    An empty list means a new database, which the app answers with the first-run
    setup step. A database that holds only part of the setup raises an error, so
    an unreadable database is never treated as a new installation
    (section 23.2). The address path is part of the key's identity and is
    compared with every submitted path (section 25.1).
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, key_number, name, type, address_path, created_at
            FROM keys
            ORDER BY key_number
            """
        ).fetchall()
    finally:
        connection.close()

    keys = [dict(row) for row in rows]
    if keys and len(keys) != KEY_COUNT:
        raise RuntimeError(
            f"The stored key setup has {len(keys)} of {KEY_COUNT} keys"
        )
    return keys


def save_key_setup(entries, database_path="data/helsesjekk.sqlite3"):
    """Store the key setup for the three key slots.

    The setup is written once, because the names, the types and the address
    paths are locked after they are saved (sections 23.2 and 25.1). A database
    that already holds a setup is left untouched.
    """
    if list_keys(database_path):
        raise RuntimeError("The key setup is already stored")

    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            connection.executemany(
                "INSERT INTO keys (key_number, name, type, address_path) VALUES (?, ?, ?, ?)",
                [
                    (
                        entry["key_number"],
                        entry["name"],
                        entry["type"],
                        entry["address_path"],
                    )
                    for entry in entries
                ],
            )
    finally:
        connection.close()


def key_has_check(key_id, database_path="data/helsesjekk.sqlite3"):
    """Return True when the key already has a saved check.

    The address path is the identity of a key, so it may only be changed while
    the key has no saved check (section 25.1).
    """
    connection = sqlite3.connect(database_path, timeout=5)
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM key_checks WHERE key_id = ?", (key_id,)
        ).fetchone()[0]
    finally:
        connection.close()
    return count > 0


def save_key_settings(key_id, name, address_path, database_path="data/helsesjekk.sqlite3"):
    """Store the name and the address path of one key.

    The name is only a label, while the address path is part of the key's
    identity (sections 25.1 and 25.2). Whether the path may change is decided by
    the caller, which reads the key's saved checks from the same database.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE keys SET name = ?, address_path = ? WHERE id = ?",
                (name, address_path, key_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Key {key_id} does not exist")
    finally:
        connection.close()


def list_wallet_software(database_path="data/helsesjekk.sqlite3"):
    """Return the stored wallet software names in their stored order.

    The list is maintained in the settings and stored whole; every entry is a
    wallet software choice for a hardware key (section 25.4).
    """
    connection = sqlite3.connect(database_path, timeout=5)
    try:
        rows = connection.execute(
            "SELECT name FROM wallet_software ORDER BY id"
        ).fetchall()
    finally:
        connection.close()
    return [row[0] for row in rows]


def save_wallet_software(names, database_path="data/helsesjekk.sqlite3"):
    """Replace the stored wallet software list with the given names.

    The list is stored whole, not entry by entry (section 25.4). Removing a name
    does not touch any saved check, because ``health_checks`` keeps the selected
    software as free text.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    try:
        with connection:
            connection.execute("DELETE FROM wallet_software")
            connection.executemany(
                "INSERT INTO wallet_software (name) VALUES (?)",
                [(name,) for name in names],
            )
    finally:
        connection.close()


def save_alert_acknowledgement(code, source, check_id, reason, database_path="data/helsesjekk.sqlite3"):
    """Store one acknowledged alert, so it stays hidden until it is raised again.

    ``check_id`` is the newest check that raised the alert when it was
    acknowledged. A newer check for the same code and source gets a higher id
    and therefore raises the alert again (section 25.3).
    """
    connection = sqlite3.connect(database_path, timeout=5)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO alert_acknowledgements (code, source, check_id, reason, acknowledged_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    code,
                    source,
                    check_id,
                    reason,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return cursor.lastrowid
    finally:
        connection.close()


def list_alert_acknowledgements(database_path="data/helsesjekk.sqlite3"):
    """Return every stored acknowledgement, newest first."""
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, code, source, check_id, reason, acknowledged_at
            FROM alert_acknowledgements
            ORDER BY id DESC
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
                    seed_backup_verified, address_path_verified, address_path, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    health_check_id,
                    key_check["key_id"],
                    key_check["available"],
                    key_check["hardware_works"],
                    key_check["firmware_version"],
                    key_check["seed_backup_verified"],
                    key_check["address_path_verified"],
                    key_check["address_path"],
                    key_check["comments"],
                ),
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
            SELECT k.id AS key_id, k.key_number, k.name, k.type,
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
    are used to pre-fill the form.
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
    grouped. The per-provider security results are joined into a single text
    cell, because they have more than one value per submission.
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
                   kc.seed_backup_verified, kc.address_path_verified,
                   kc.address_path, kc.comments AS key_comments
            FROM key_checks AS kc
            JOIN health_checks AS hc ON hc.id = kc.health_check_id
            JOIN keys AS k ON k.id = kc.key_id
            ORDER BY hc.checked_at, hc.id, k.key_number
            """
        ).fetchall()
        result = [dict(row) for row in rows]
        security = _grouped_values(connection, "ai_security_checks", "provider", "status")
        for row in result:
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
    """Return one saved health check with its related rows, or None.

    The key rows are read through ``keys``, so the history, the alerts and the
    export show the name a key has now, which the settings may change
    (section 25.2).
    """
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
                SELECT kc.id, kc.key_id, k.key_number, k.name, k.type,
                       kc.available, kc.hardware_works, kc.firmware_version,
                       kc.seed_backup_verified, kc.address_path_verified,
                       kc.address_path, kc.comments
                FROM key_checks AS kc
                JOIN keys AS k ON k.id = kc.key_id
                WHERE kc.health_check_id = ?
                ORDER BY k.key_number
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
