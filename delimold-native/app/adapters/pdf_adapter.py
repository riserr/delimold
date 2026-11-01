"""PDF printing adapter for the filtered DELIMOLD table view."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.application.ports import PdfExporterPort
from app.domain.errors import StorageError


class ReportLabPdfAdapter(PdfExporterPort):
    def write_pdf(self, path, title, headings, rows):
        table_rows = [list(headings)] + [list(row) for row in rows]
        table = Table(table_rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#55ad7e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#dce5d8")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8f4")]),
        ]))
        story = [Paragraph(str(title), getSampleStyleSheet()["Title"]), Spacer(1, 12), table]
        try:
            SimpleDocTemplate(path, pagesize=landscape(A4), title="DELIMOLD").build(story)
        except Exception as exc:
            raise StorageError("Dokumen PDF tidak dapat dibuat.") from exc
