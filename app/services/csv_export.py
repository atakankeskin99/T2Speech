import csv
import io
from collections.abc import Iterable


def _safe_spreadsheet_value(value: str) -> str:
    formula_prefixes = ("=", "+", "-", "@")

    if value.lstrip(" \t\r\n").startswith(formula_prefixes):
        return "'" + value

    return value


def build_csv_export(cards: Iterable[tuple[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    writer.writerow(("Front", "Back"))

    for front, back in cards:
        writer.writerow(
            (
                _safe_spreadsheet_value(front),
                _safe_spreadsheet_value(back),
            )
        )

    return buffer.getvalue().encode("utf-8-sig")