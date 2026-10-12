import unittest

from app.services.csv_import import (
    CsvImportError,
    ParsedImportData,
    analyze_import,
)


def make_csv(rows, headers=("Front", "Back")):
    return ParsedImportData(
        headers=headers,
        rows=tuple(tuple(row) for row in rows),
        delimiter=",",
    )


class AnalyzeImportTests(unittest.TestCase):
    def test_trims_whitespace_and_marks_card_ready(self):
        result = analyze_import(
            make_csv([("  Hallo ", " Hello  ")]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(result.rows[0].front, "Hallo")
        self.assertEqual(result.rows[0].back, "Hello")
        self.assertEqual(result.rows[0].status, "ready")
        self.assertEqual(result.ready_to_import, 1)

    def test_marks_card_already_in_destination_deck(self):
        result = analyze_import(
            make_csv([("Hallo", "Hello")]),
            front_index=0,
            back_index=1,
            existing_cards=((" Hallo ", "Hello "),),
        )

        self.assertEqual(result.rows[0].status, "already_in_deck")
        self.assertEqual(result.already_in_deck, 1)

    def test_marks_repeated_file_card_as_duplicate(self):
        result = analyze_import(
            make_csv([
                ("Hallo", "Hello"),
                (" Hallo ", "Hello "),
            ]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(result.rows[0].status, "ready")
        self.assertEqual(result.rows[1].status, "duplicate_in_file")
        self.assertEqual(result.duplicates_in_file, 1)

    def test_comparison_preserves_case_and_punctuation(self):
        result = analyze_import(
            make_csv([
                ("Hello", "Hi!"),
                ("hello", "Hi!"),
                ("Hello", "Hi"),
            ]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(
            [row.status for row in result.rows],
            ["ready", "ready", "ready"],
        )

    def test_same_front_with_different_back_is_not_duplicate(self):
        result = analyze_import(
            make_csv([
                ("bank", "a financial institution"),
                ("bank", "the side of a river"),
            ]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(result.ready_to_import, 2)
        self.assertEqual(result.duplicates_in_file, 0)

    def test_marks_missing_front_or_back_as_invalid(self):
        result = analyze_import(
            make_csv([
                ("", "answer"),
                ("front", ""),
                ("front-only",),
            ]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(result.invalid_rows, 3)
        self.assertTrue(
            all(row.status == "invalid" for row in result.rows)
        )

    def test_skips_completely_empty_rows(self):
        result = analyze_import(
            make_csv([
                ("", ""),
                ("  ", "\t"),
            ]),
            front_index=0,
            back_index=1,
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.empty_rows, 2)
        self.assertEqual(result.invalid_rows, 0)

    def test_summary_counts_each_row_category(self):
        result = analyze_import(
            make_csv([
                ("A", "one"),
                ("B", "two"),
                ("B", "two"),
                ("front-only", ""),
                ("", ""),
            ]),
            front_index=0,
            back_index=1,
            existing_cards=(("A", "one"),),
        )

        self.assertEqual(result.total_rows, 5)
        self.assertEqual(result.ready_to_import, 1)
        self.assertEqual(result.already_in_deck, 1)
        self.assertEqual(result.duplicates_in_file, 1)
        self.assertEqual(result.invalid_rows, 1)
        self.assertEqual(result.empty_rows, 1)

    def test_rejects_same_front_and_back_column(self):
        with self.assertRaises(CsvImportError):
            analyze_import(
                make_csv([("value", "other")]),
                front_index=0,
                back_index=0,
            )

    def test_rejects_out_of_range_column(self):
        with self.assertRaises(CsvImportError):
            analyze_import(
                make_csv([("value", "other")]),
                front_index=0,
                back_index=2,
            )

    def test_row_number_starts_at_one_without_header(self):
        parsed = ParsedImportData(
            headers=("Column 1", "Column 2"),
            rows=(("a", "b"),),
            delimiter=",",
        )

        analysis = analyze_import(
            parsed,
            front_index=0,
            back_index=1,
            has_header=False,
        )

        self.assertEqual(analysis.rows[0].row_number, 1)


if __name__ == "__main__":
    unittest.main()