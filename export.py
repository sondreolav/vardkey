"""CSV export of saved health checks.

One row per key check. A submission records one key, so a new export has one row
per submission; records saved before section 19 can have up to three rows that
share a ``check_id``. The security statuses have more than one value per
submission, so they are joined into a single cell as ``Label: value; Label:
value``. The closures that belong to a key are joined the same way, into the
last column (section 27).

Status values are written exactly as stored. The contact confirmation is one of
the stored statuses (section 23.1), so it is written as text like every other
status, while the yes/no columns keep their ``No``/``Yes`` wording.

The two derived cloud columns are gone, together with the fields they described:
a cloud key records only its availability (section 25.6).

The user-controlled text cells (the key name, the wallet software, the address
path, the comments, and the closure list) are neutralized before they are
written, because a spreadsheet reads a cell that starts with ``=``, ``+``, ``-``,
``@`` or a control character as a formula. The guard is a leading apostrophe,
which makes the cell text again, and it is added only where it is needed, so the
header row, the column order, and every ordinary value are unchanged.
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
    ("address_path_verified", "Address path verified"),
    ("address_path", "Address path"),
    ("key_comments", "Key comments"),
    ("wallet_software", "Wallet software"),
    ("software_version", "Software version"),
    ("software_compatibility_status", "Software compatibility"),
    ("software_comments", "Software comments"),
    ("security_status", "Security status"),
    ("contact_info_verified", "Contact details confirmed"),
    ("comments", "Overall comments"),
    ("closed_alerts", "Follow-up closed"),
)
HEADERS = tuple(header for _, header in COLUMNS)
# Stored as 0/1 and written as No/Yes, matching the history view.
FLAG_KEYS = frozenset({
    "available",
    "hardware_works",
})

# A cell that starts with one of these is read as a formula by a spreadsheet, and
# the CSV quoting alone does not stop it: a quoted ``"=1+1"`` is still a formula
# once the file is opened (section 10).
FORMULA_PREFIXES = ("=", "+", "-", "@")
# The guard that turns such a cell back into text. It is only added to a cell
# that needs it, so ordinary content is written exactly as it is stored.
FORMULA_GUARD = "'"


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
    return _guard_formula(str(value))


def _guard_formula(text):
    """Return text that a spreadsheet reads as text, never as a formula.

    The key name, the wallet software, the address path and the comments are
    written as they are stored, so one of them can begin with a character a
    spreadsheet treats as the start of a formula. The value is prefixed with an
    apostrophe then, which is what makes the cell text again; a value that does
    not need the guard is returned unchanged (section 10).
    """
    if text and _needs_guard(text):
        return FORMULA_GUARD + text
    return text


def _needs_guard(text):
    """Return True when a spreadsheet would read the cell as a formula.

    The first character decides, and a leading space does not stop a spreadsheet
    from looking at the next one, so the first character after any leading space
    is checked as well. A control character counts, because a tab or a carriage
    return in front of a value is treated the same way as a formula prefix.
    """
    first = text[0]
    if first in FORMULA_PREFIXES or first < " " or first == "\x7f":
        return True
    candidate = text.lstrip(" ")
    if not candidate:
        return False
    return candidate[0] in FORMULA_PREFIXES or candidate[0] < " "
