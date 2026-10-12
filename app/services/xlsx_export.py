from collections.abc import Iterable
from io import BytesIO

from openpyxl import Workbook


def build_xlsx_export(cards: Iterable[tuple[str, str]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Cards"

    worksheet.append(("Front", "Back"))

    for front, back in cards:
        worksheet.append((front, back))

        for cell in worksheet[worksheet.max_row]:
            cell.data_type = "s"

    buffer = BytesIO()
    workbook.save(buffer)

    return buffer.getvalue()