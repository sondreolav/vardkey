"""CSV export of saved health checks.

One row per key check. A submission records one key, so a new export has one row
per submission; records saved before section 19 can have up to three rows that
share a ``check_id``. Results with more than one value per submission (BIP327,
SLIP39, and the security statuses) are joined into a single cell as
``Label: value; Label: value``.

Status values are written exactly as stored. The contact confirmation is one of
the stored statuses (section 23.1), so it is written as text like every other
status, while the yes/no columns keep their ``No``/``Yes`` wording.
"""

import csv
import io


# (row key, column header). The order is the column order in the file.
COLUMNS = (
    ("check_id", "Check id"),
    ("checked_at", "Check date"),
    ("next_check_due", "Next check due"),
    ("key_number", "Key number"),
    ("key_name", "Key name"),
    ("key_type", "Key type"),
    ("available", "Available"),
    ("hardware_works", "Hardware works"),
    ("firmware_version", "Firmware version"),
    ("seed_backup_verified", "Seed backup verified"),
    ("cloud_health_status", "Cloud health status"),
    ("cloud_provider_operational", "Cloud provider operational"),
    ("address_path_verified", "Address path verified"),
    ("address_path", "Address path"),
    ("key_comments", "Key comments"),
    ("wallet_software", "Wallet software"),
    ("software_version", "Software version"),
    ("software_compatibility_status", "Software compatibility"),
    ("software_comments", "Software comments"),
    ("bip327_status", "BIP327"),
    ("slip39_status", "SLIP39"),
    ("security_status", "Security status"),
    ("contact_info_verified", "Contact details confirmed"),
    ("comments", "Overall comments"),
)
HEADERS = tuple(header for _, header in COLUMNS)
# Stored as 0/1 and written as No/Yes, matching the history view.
FLAG_KEYS = frozenset({
    "available",
    "hardware_works",
    "cloud_provider_operational",
})


def build_csv(rows):
    """Return the export as CSV text with a header row."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow([_cell(row.get(key), key in FLAG_KEYS) for key, _ in COLUMNS])
    return buffer.getvalue()


def _cell(value, is_flag):
    """Render one value as CSV text. Missing values become an empty cell."""
    if value is None:
        return ""
    if is_flag:
        return "Yes" if value == 1 else "No"
    return str(value)
