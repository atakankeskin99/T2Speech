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


def parse_csv(file_bytes: bytes, *, has_header: bool = True) -> ParsedCsv:
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
        first_row = next(reader)
    except StopIteration as error:
        raise CsvImportError("The CSV file has no rows.") from error
    except csv.Error as error:
        raise CsvImportError("The CSV file format is invalid.") from error

    rows: list[tuple[str, ...]] = []

    if has_header:
        raw_headers = first_row
    else:
        # Headerless files keep their first record as card data.
        raw_headers = []
        rows.append(tuple(first_row))

    try:
        for row in reader:
            if len(rows) >= MAX_DATA_ROWS:
                raise CsvImportError(
                    "The CSV file exceeds the 10,000 row limit."
                )
            rows.append(tuple(row))
    except csv.Error as error:
        raise CsvImportError("The CSV file format is invalid.") from error

    if has_header:
        headers = tuple(header.strip() for header in raw_headers)
    else:
        column_count = max((len(row) for row in rows), default=0)
        headers = tuple(
            f"Column {index + 1}"
            for index in range(column_count)
        )

    if not headers:
        raise CsvImportError("The CSV file has no columns.")

    return ParsedCsv(
        headers=headers,
        rows=tuple(rows),
        delimiter=dialect.delimiter,
    )


@dataclass(frozen=True)
class ImportRowResult:
    row_number: int
    front: str
    back: str
    status: str
    reason: str = ""


@dataclass(frozen=True)
class ImportAnalysis:
    rows: tuple[ImportRowResult, ...]
    total_rows: int
    ready_to_import: int
    already_in_deck: int
    duplicates_in_file: int
    invalid_rows: int
    empty_rows: int

def analyze_import(
    parsed_csv: ParsedCsv,
    front_index: int,
    back_index: int,
    existing_cards: tuple[tuple[str, str], ...] = (),
    has_header: bool = True,
) -> ImportAnalysis:
    column_count = len(parsed_csv.headers)

    if front_index == back_index:
        raise CsvImportError("Front and Back must use different columns.")

    if not 0 <= front_index < column_count:
        raise CsvImportError("The selected Front column is invalid.")

    if not 0 <= back_index < column_count:
        raise CsvImportError("The selected Back column is invalid.")

    existing_pairs = {
        (front.strip(), back.strip())
        for front, back in existing_cards
    }
    seen_in_file: set[tuple[str, str]] = set()
    results: list[ImportRowResult] = []

    ready_to_import = 0
    already_in_deck = 0
    duplicates_in_file = 0
    invalid_rows = 0
    empty_rows = 0

    start_row = 2 if has_header else 1

    for row_number, row in enumerate(parsed_csv.rows, start=start_row):

        front = row[front_index].strip() if front_index < len(row) else ""
        back = row[back_index].strip() if back_index < len(row) else ""

        if not front and not back:
            status = "empty"
            reason = "Empty row skipped."
            empty_rows += 1

        elif not front or not back:
            status = "invalid"
            reason = "Both Front and Back are required."
            invalid_rows += 1

        else:
            pair = (front, back)

            if pair in seen_in_file:
                status = "duplicate_in_file"
                reason = "This card already appears earlier in the file."
                duplicates_in_file += 1

            elif pair in existing_pairs:
                status = "already_in_deck"
                reason = "This card is already in the destination deck."
                already_in_deck += 1

            else:
                status = "ready"
                reason = ""
                ready_to_import += 1

            seen_in_file.add(pair)

        results.append(
            ImportRowResult(
                row_number=row_number,
                front=front,
                back=back,
                status=status,
                reason=reason,
            )
        )

    return ImportAnalysis(
        rows=tuple(results),
        total_rows=len(parsed_csv.rows),
        ready_to_import=ready_to_import,
        already_in_deck=already_in_deck,
        duplicates_in_file=duplicates_in_file,
        invalid_rows=invalid_rows,
        empty_rows=empty_rows,
    )