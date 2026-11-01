"""Excel and PDF transfer workflows with role checks at the application boundary."""
from typing import Any, List, Tuple

from app.application.dto import (ExcelExportRequest, PdfExportRequest, WorkbookReadRequest,
                                WorkbookTemplateRequest)
from app.application.ports import PdfExporterPort, WorkbookPort
from app.domain.errors import ValidationError
from app.domain.permissions import require_access


class TransferUseCases:
    def __init__(self, workbook: WorkbookPort = None, pdf_exporter: PdfExporterPort = None):
        self._workbook = workbook
        self._pdf_exporter = pdf_exporter

    def read_excel_rows(self, request: WorkbookReadRequest) -> List[Tuple[Any, ...]]:
        require_access(request.actor, "import", request.collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        return self._workbook.read_rows(request.path)

    def write_excel_template(self, request: WorkbookTemplateRequest) -> None:
        require_access(request.actor, "read", request.collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        self._workbook.write_template(request.path, request.collection, request.headings)

    def export_excel(self, request: ExcelExportRequest) -> None:
        require_access(request.actor, "read", request.collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        self._workbook.write_workbook(request.path, request.collection, request.headings, request.rows)

    def print_pdf(self, request: PdfExportRequest) -> None:
        require_access(request.actor, "read", request.collection)
        if self._pdf_exporter is None:
            raise ValidationError("Adapter PDF belum disiapkan.")
        self._pdf_exporter.write_pdf(request.path, request.title, request.headings, request.rows)
