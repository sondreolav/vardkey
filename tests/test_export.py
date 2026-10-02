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
            "cloud_provider_operational": 1,
            "contact_info_verified": 0,
        }]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Available"], "Yes")
        self.assertEqual(values["Hardware works"], "No")
        self.assertEqual(values["Cloud provider operational"], "Yes")
        self.assertEqual(values["Contact details confirmed"], "No")

    def test_text_with_separators_is_quoted_and_read_back(self):
        comment = 'note, with "quotes"; and more'
        rows = parse(build_csv([{"key_comments": comment}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["Key comments"], comment)

    def test_joined_multi_value_cells_survive_the_round_trip(self):
        joined = "SeedSigner: OK; Sparrow Wallet: PROBLEM"
        rows = parse(build_csv([{"bip327_status": joined}]))
        values = dict(zip(HEADERS, rows[1]))

        self.assertEqual(values["BIP327"], joined)


if __name__ == "__main__":
    unittest.main()
