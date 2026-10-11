import csv
import io
import unittest

from app.services.csv_export import build_csv_export


class CsvExportTests(unittest.TestCase):
    def read_export(self, content: bytes) -> list[list[str]]:
        text = content.decode("utf-8-sig")
        return list(csv.reader(io.StringIO(text, newline="")))

    def test_writes_headers_and_preserves_unicode_and_special_characters(self):
        cards = (
            ("Grüß Gott, こんにちは", 'A "quoted" answer\nwith a new line'),
        )

        content = build_csv_export(cards)

        self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(
            self.read_export(content),
            [
                ["Front", "Back"],
                ["Grüß Gott, こんにちは", 'A "quoted" answer\nwith a new line'],
            ],
        )

    def test_prefixes_values_that_could_be_spreadsheet_formulas(self):
        cards = (
            ("=1+1", "+SUM(A1:A2)"),
            ("-2+3", "@SUM(A1:A2)"),
            ("  =1+1", "ordinary text"),
        )

        rows = self.read_export(build_csv_export(cards))

        self.assertEqual(
            rows[1:],
            [
                ["'=1+1", "'+SUM(A1:A2)"],
                ["'-2+3", "'@SUM(A1:A2)"],
                ["'  =1+1", "ordinary text"],
            ],
        )

    def test_exports_headers_when_deck_has_no_cards(self):
        self.assertEqual(
            self.read_export(build_csv_export(())),
            [["Front", "Back"]],
        )


if __name__ == "__main__":
    unittest.main()