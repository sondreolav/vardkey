"""Tests for the CSV export."""

import csv
import io
import unittest

from export import COLUMNS, FLAG_KEYS, HEADERS, build_csv


def parse(text):
    """Return the CSV text as a list of rows."""
    return list(csv.reader(io.StringIO(text)))


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
        # The closures that belong to a key are joined into the last column,
        # like the security statuses (section 27).
        joined = "key_unavailable: rotate (2026-10-05); hardware_failure: replace_hardware (2026-10-06)"
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
