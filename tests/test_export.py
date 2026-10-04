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


if __name__ == "__main__":
    unittest.main()
