"""Tests for the CSV export."""

import csv
import io
import os
import tempfile
import unittest

from database import (
    initialize_database,
    list_export_rows,
    list_keys,
    rotate_key,
    save_alert_acknowledgement,
    save_health_check,
    save_key_setup,
)
from export import COLUMNS, FLAG_KEYS, HEADERS, build_csv
from validation import validate_health_check


def parse(text):
    """Return the CSV text as a list of rows."""
    return list(csv.reader(io.StringIO(text)))


# The address path each key slot is configured with. Every key has its own one,
# so the setup the API would accept is the setup the export reads back
# (sections 25.1 and 26.2).
ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
SETUP = (
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
)
# The wallet software list the settings hold, and that the app passes to the
# validator (section 25.4).
WALLET_SOFTWARE = ("Sparrow Wallet",)


def sample_payload(key):
    """Return a valid payload for one key, dated in the past (section 32.8 point 3)."""
    wallet_software = key["name"] if key["type"] == "cloud" else "Sparrow Wallet"
    labels = list(dict.fromkeys((key["name"], wallet_software)))
    entry = {
        "key_id": key["id"],
        "available": 1,
        "address_path": key["address_path"],
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


class ExportTests(unittest.TestCase):
    def test_empty_export_has_only_the_header_row(self):
        self.assertEqual(parse(build_csv([])), [list(HEADERS)])

    def test_every_column_is_written_in_order(self):
        row = {
            key: (1 if key in FLAG_KEYS else f"value-{key}")
            for key, _ in COLUMNS
        }

        rows = parse(build_csv([row]))

        self.assertEqual(rows[0], list(HEADERS))
        self.assertEqual(
            rows[1],
            ["Yes" if key in FLAG_KEYS else f"value-{key}" for key, _ in COLUMNS],
        )

    def test_missing_values_become_empty_cells(self):
        rows = parse(build_csv([{"check_id": 1}]))

        self.assertEqual(rows[1][0], "1")
        self.assertEqual(rows[1][1:], [""] * (len(COLUMNS) - 1))

    def test_flag_columns_are_rendered_as_yes_and_no(self):
        rows = parse(build_csv([{
            "available": 1,
            "hardware_works": 0,
        }]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Available"], "Yes")
        self.assertEqual(values["Hardware works"], "No")

    def test_the_bip327_and_slip39_columns_are_gone(self):
        # The whole BIP327/SLIP39 function is removed (section 24.2), so the two
        # columns are gone from the export as well.
        self.assertNotIn("BIP327", HEADERS)
        self.assertNotIn("SLIP39", HEADERS)

    def test_the_removed_cloud_columns_are_gone(self):
        # A cloud key records only its availability, so the two derived columns
        # are gone (section 25.6).
        self.assertNotIn("Cloud health status", HEADERS)
        self.assertNotIn("Cloud provider operational", HEADERS)
        self.assertNotIn("cloud_health_status", dict(COLUMNS))
        self.assertNotIn("cloud_provider_operational", FLAG_KEYS)

    def test_contact_status_is_written_as_stored_text(self):
        # The contact confirmation is a status, not a yes/no flag (section 23.1).
        self.assertNotIn("contact_info_verified", FLAG_KEYS)
        for value in ("Confirmed current", "Needs external update"):
            rows = parse(build_csv([{"contact_info_verified": value}]))
            values = dict(zip(HEADERS, rows[1]))
            self.assertEqual(values["Contact details confirmed"], value)

    def test_the_follow_up_closed_column_is_last_and_reads_back(self):
        # Every closure of a check is joined into the last column, like the
        # security statuses (sections 27 and 32.8 point 6).
        joined = "key_unavailable: rotate (2026-10-05); software_incompatible: remove_software (2026-10-06)"
        rows = parse(build_csv([{"closed_alerts": joined}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(HEADERS[-1], "Follow-up closed")
        self.assertEqual(dict(COLUMNS)["closed_alerts"], "Follow-up closed")
        self.assertEqual(values["Follow-up closed"], joined)

    def test_text_with_separators_is_quoted_and_read_back(self):
        comment = 'note, with "quotes"; and more'
        rows = parse(build_csv([{"key_comments": comment}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Key comments"], comment)

    def test_joined_multi_value_cells_survive_the_round_trip(self):
        joined = "SeedSigner: SECURE; Sparrow Wallet: VULNERABLE"
        rows = parse(build_csv([{"security_status": joined}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Security status"], joined)

    def test_status_values_are_written_as_stored(self):
        rows = parse(build_csv([{
            "seed_backup_verified": "PROBLEM",
            "address_path_verified": "PROBLEM",
            "software_compatibility_status": "NOT_ASSESSED",
        }]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Seed backup verified"], "PROBLEM")
        # The address path result is derived by the server, and it is written as
        # it is stored (sections 25.1 and 25.6).
        self.assertEqual(values["Address path verified"], "PROBLEM")
        self.assertEqual(values["Software compatibility"], "NOT_ASSESSED")


class ExportHistoryTests(unittest.TestCase):
    """The exported rows are read from the stored history.

    The key name and the key type come from the snapshot the check carries, so a
    rotation cannot rewrite an older row, and every closure of a check is joined
    into the last column, whether it belongs to a key or to a software entry in
    the settings list (sections 10, 27 and 32.8 points 5 and 6).
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        save_key_setup(SETUP, self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def keys(self):
        """Return the active key profiles of the stored setup."""
        return list_keys(self.database_path)

    def store_check(self, key):
        """Store one valid check for a key and return its id."""
        return save_health_check(
            validate_health_check(sample_payload(key), self.keys(), WALLET_SOFTWARE),
            self.database_path,
        )

    def export_rows(self):
        """Return the exported CSV as a list of header-keyed data rows."""
        rows = parse(build_csv(list_export_rows(self.database_path)))
        self.assertEqual(rows[0], list(HEADERS))
        return [dict(zip(HEADERS, row)) for row in rows[1:]]

    def test_a_closed_software_alert_is_written_into_the_last_column(self):
        # A software alert raised by the settings list belongs to no key, but its
        # closure still hangs on the check it closed through its check_id, so it
        # is listed as well (sections 10, 27 and 32.8 point 6).
        key = self.keys()[0]
        saved_id = self.store_check(key)
        save_alert_acknowledgement(
            "software_incompatible",
            "Sparrow Wallet",
            None,
            saved_id,
            "remove_software",
            self.database_path,
        )

        rows = self.export_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(HEADERS[-1], "Follow-up closed")
        self.assertRegex(
            rows[0]["Follow-up closed"],
            r"^software_incompatible: remove_software \(\d{4}-\d{2}-\d{2}\)$",
        )

    def test_an_older_row_keeps_the_name_and_the_type_of_its_snapshot(self):
        # A rotation retires the key row and inserts a new one for the same
        # multisig slot, so the export row that was already written keeps the name
        # and the type it was recorded with (section 32.8 point 5).
        key = self.keys()[0]
        self.store_check(key)

        rotate_key(key["id"], "ColdCard", "m/48'/7'/0'/2'", self.database_path)

        rows = self.export_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Key number"], "1")
        self.assertEqual(rows[0]["Key name"], "SeedSigner")
        self.assertEqual(rows[0]["Key type"], "hardware")
        # The active row carries the new name, which the next check records.
        self.assertEqual(self.keys()[0]["name"], "ColdCard")
        self.assertEqual(self.keys()[0]["address_path"], "m/48'/7'/0'/2'")


class FormulaInjectionTests(unittest.TestCase):
    """A user-controlled text cell is never written as a spreadsheet formula.

    A cell that starts with ``=``, ``+``, ``-``, ``@`` or a control character is
    read as a formula when the file is opened, and the CSV quoting alone does not
    stop it. Every text cell is neutralized with a leading apostrophe, while an
    ordinary value is written exactly as it is stored (section 10).
    """

    def cell(self, value):
        """Return the exported ``Key comments`` cell for one value."""
        rows = parse(build_csv([{"key_comments": value}]))
        return dict(zip(HEADERS, rows[1]))["Key comments"]

    def test_a_formula_prefix_is_neutralized(self):
        for prefix in ("=", "+", "-", "@"):
            value = f"{prefix}SUM(A1:A2)"
            self.assertEqual(self.cell(value), "'" + value)

    def test_a_leading_control_character_is_neutralized(self):
        # A tab, a carriage return or a line feed in front of a value is treated
        # the same way as a formula prefix.
        for prefix in ("\t", "\r", "\n"):
            value = f"{prefix}=SUM(A1:A2)"
            self.assertEqual(self.cell(value), "'" + value)

    def test_a_formula_prefix_after_a_space_is_neutralized(self):
        # A leading space does not stop a spreadsheet from reading the cell.
        for prefix in ("=", "+", "-", "@"):
            value = f"  {prefix}SUM(A1:A2)"
            self.assertEqual(self.cell(value), "'" + value)

    def test_ordinary_text_is_written_exactly_as_stored(self):
        # The guard is only added where it is needed, so ordinary content, an
        # empty cell and the stored status values are untouched.
        for value in (
            "Annual review",
            'note, with "quotes"; and more',
            "SeedSigner: SECURE; Sparrow Wallet: VULNERABLE",
            "1.8.0",
            "PROBLEM",
            "",
        ):
            self.assertEqual(self.cell(value), value)

    def test_the_header_row_and_the_flags_are_not_guarded(self):
        # The column names are the export agreement, and the yes/no columns keep
        # their wording (section 10).
        rows = parse(build_csv([{"available": 1, "hardware_works": 0}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(rows[0], list(HEADERS))
        self.assertEqual(values["Available"], "Yes")
        self.assertEqual(values["Hardware works"], "No")


if __name__ == "__main__":
    unittest.main()
