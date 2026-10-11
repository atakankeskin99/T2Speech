import csv
import io
from dataclasses import dataclass


MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_DATA_ROWS = 10_000


class CsvImportError(ValueError):
    """Raised when a CSV file cannot be safely parsed for import."""


@dataclass(frozen=True)
class ParsedCsv:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    delimiter: str


def parse_csv(file_bytes: bytes) -> ParsedCsv:
    if not file_bytes:
        raise CsvImportError("The CSV file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise CsvImportError("The CSV file exceeds the 5 MB limit.")

    try:
        # utf-8-sig also removes the BOM added by some spreadsheet apps.
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CsvImportError(
            "The CSV file must use UTF-8 encoding."
        ) from error

    try:
        dialect = csv.Sniffer().sniff(
            text[:8192],
            delimiters=",;\t",
        )
    except csv.Error:
        # Use the standard comma delimiter if automatic detection is unclear.
        dialect = csv.excel

    reader = csv.reader(
        io.StringIO(text, newline=""),
        dialect=dialect,
        strict=True,
    )

    try:
        headers = next(reader)
    except StopIteration as error:
        raise CsvImportError("The CSV file has no header row.") from error
    except csv.Error as error:
        raise CsvImportError("The CSV file format is invalid.") from error

    rows: list[tuple[str, ...]] = []

    try:
        for row in reader:
            if len(rows) >= MAX_DATA_ROWS:
                raise CsvImportError(
                    "The CSV file exceeds the 10,000 row limit."
                )
            rows.append(tuple(row))
    except csv.Error as error:
        raise CsvImportError("The CSV file format is invalid.") from error

    return ParsedCsv(
        headers=tuple(header.strip() for header in headers),
        rows=tuple(rows),
        delimiter=dialect.delimiter,
    )