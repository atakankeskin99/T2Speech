import io
import unittest
from unittest.mock import patch

from openpyxl import Workbook

from app.services.csv_import import MAX_FILE_SIZE_BYTES
from app.services.xlsx_import import (
    XlsxImportError,
    get_xlsx_sheet_names,
    parse_xlsx,
)


class XlsxImportTests(unittest.TestCase):
    def make_workbook_bytes(self) -> bytes:
        workbook = Workbook()

        vocabulary = workbook.active
        vocabulary.title = "Vocabulary"
        vocabulary.append(("Front", "Back"))
        vocabulary.append(("Grüß Gott", "Hello"))
        vocabulary.append(("Straße", None))
        vocabulary.append(("Danke", "Thank you"))

        archive = workbook.create_sheet("Archive")
        archive.append(("Prompt", "Answer"))
        archive.append(("Hola", "Hello"))

        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def test_returns_all_sheet_names_in_workbook_order(self):
        self.assertEqual(
            get_xlsx_sheet_names(self.make_workbook_bytes()),
            ("Vocabulary", "Archive"),
        )

    def test_parses_the_selected_sheet_and_preserves_unicode(self):
        parsed = parse_xlsx(self.make_workbook_bytes(), "Archive")

        self.assertEqual(parsed.headers, ("Prompt", "Answer"))
        self.assertEqual(parsed.rows, (("Hola", "Hello"),))
        self.assertIsNone(parsed.delimiter)

    def test_keeps_first_row_as_data_without_a_header(self):
        parsed = parse_xlsx(
            self.make_workbook_bytes(),
            "Vocabulary",
            has_header=False,
        )

        self.assertEqual(parsed.headers, ("Column 1", "Column 2"))
        self.assertEqual(
            parsed.rows[0],
            ("Front", "Back"),
        )
        self.assertEqual(parsed.rows[1], ("Grüß Gott", "Hello"))
        self.assertEqual(parsed.rows[2], ("Straße", ""))

    def test_rejects_unknown_sheet_name(self):
        with self.assertRaises(XlsxImportError):
            parse_xlsx(self.make_workbook_bytes(), "Missing")

    def test_rejects_empty_invalid_and_oversized_files(self):
        for file_bytes in (b"", b"not an XLSX workbook"):
            with self.subTest(file_bytes=file_bytes):
                with self.assertRaises(XlsxImportError):
                    get_xlsx_sheet_names(file_bytes)

        oversized_file = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with self.assertRaises(XlsxImportError):
            get_xlsx_sheet_names(oversized_file)

    def test_rejects_worksheet_over_row_limit(self):
        with patch("app.services.xlsx_import.MAX_DATA_ROWS", 2):
            with self.assertRaises(XlsxImportError):
                parse_xlsx(self.make_workbook_bytes(), "Vocabulary")


if __name__ == "__main__":
    unittest.main()