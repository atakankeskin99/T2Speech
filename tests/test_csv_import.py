import unittest

from app.services.csv_import import (
    MAX_DATA_ROWS,
    MAX_FILE_SIZE_BYTES,
    CsvImportError,
    parse_csv,
)


class ParseCsvTests(unittest.TestCase):
    def test_parses_comma_delimited_csv(self):
        result = parse_csv(b"Front,Back\nHallo,Hello\n")

        self.assertEqual(result.headers, ("Front", "Back"))
        self.assertEqual(result.rows, (("Hallo", "Hello"),))
        self.assertEqual(result.delimiter, ",")

    def test_parses_semicolon_delimited_csv(self):
        result = parse_csv("Ön;Arka\nMerhaba;Hello\n".encode("utf-8"))

        self.assertEqual(result.headers, ("Ön", "Arka"))
        self.assertEqual(result.rows, (("Merhaba", "Hello"),))
        self.assertEqual(result.delimiter, ";")

    def test_removes_utf8_bom_and_preserves_unicode(self):
        content = "\ufeffFront,Back\nçağrı,merhaba\n".encode("utf-8")

        result = parse_csv(content)

        self.assertEqual(result.headers, ("Front", "Back"))
        self.assertEqual(result.rows, (("çağrı", "merhaba"),))

    def test_preserves_commas_inside_quoted_cells(self):
        result = parse_csv(
            b'Front,Back\n"Hello, there","Merhaba, nasilsin"\n'
        )

        self.assertEqual(
            result.rows,
            (("Hello, there", "Merhaba, nasilsin"),),
        )

    def test_rejects_empty_file(self):
        with self.assertRaises(CsvImportError):
            parse_csv(b"")

    def test_rejects_non_utf8_file(self):
        with self.assertRaises(CsvImportError):
            parse_csv(b"Front,Back\ncaf\xe9,coffee\n")

    def test_rejects_file_over_size_limit(self):
        content = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        with self.assertRaises(CsvImportError):
            parse_csv(content)

    def test_rejects_file_over_row_limit(self):
        content = (
            b"Front,Back\n"
            + b"front,back\n" * (MAX_DATA_ROWS + 1)
        )

        with self.assertRaises(CsvImportError):
            parse_csv(content)

    def test_rejects_malformed_quoted_csv(self):
        content = b'Front,Back\n"unfinished,answer'

        with self.assertRaises(CsvImportError):
            parse_csv(content)


if __name__ == "__main__":
    unittest.main()