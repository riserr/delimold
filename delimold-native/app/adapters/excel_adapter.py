"""Excel file I/O adapter."""
from openpyxl import Workbook, load_workbook

from app.application.ports import WorkbookPort
from app.domain.errors import StorageError


class OpenpyxlWorkbookAdapter(WorkbookPort):
    def read_rows(self, path):
        try:
            book = load_workbook(path, read_only=True, data_only=True)
            try:
                return list(book.active.iter_rows(values_only=True))
            finally:
                book.close()
        except Exception as exc:
            raise StorageError("Workbook Excel tidak dapat dibaca.") from exc

    def write_workbook(self, path, sheet_name, headings, rows):
        book = Workbook()
        sheet = book.active
        sheet.title = str(sheet_name)[:31]
        sheet.append(list(headings))
        for row in rows:
            sheet.append(list(row))
        try:
            book.save(path)
        except Exception as exc:
            raise StorageError("Workbook Excel tidak dapat disimpan.") from exc

    def write_template(self, path, sheet_name, headings):
        self.write_workbook(path, sheet_name, headings, ())
