"""
Social Pulse API — PDF Utilities
Uses reportlab for all PDF generation.
"""
import io
from xml.sax.saxutils import escape
from flask import Response
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# Brand colours
BRAND_INDIGO = colors.HexColor("#4f46e5")
BRAND_DARK = colors.HexColor("#0e172a")
LIGHT_INDIGO = colors.HexColor("#ede9fe")


def _build_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SPTitle",
        parent=styles["Title"],
        textColor=BRAND_INDIGO,
        fontSize=18,
        spaceAfter=12,
    )
    header_style = ParagraphStyle(
        "SPHeader",
        parent=styles["Heading2"],
        textColor=BRAND_DARK,
        fontSize=13,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "SPBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )
    return styles, title_style, header_style, body_style


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.line(doc.leftMargin, 1.25 * cm, doc.pagesize[0] - doc.rightMargin, 1.25 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 0.8 * cm, "Social Pulse · YouTube Audience Intelligence")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()


def table_pdf_response(filename: str, title: str, headers: list, rows: list) -> Response:
    """
    Render a titled table PDF and return as a Flask attachment response.

    :param filename: Attachment filename
    :param title: Report title displayed at the top
    :param headers: Column header names
    :param rows: List of data rows (list of lists/tuples)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1 * cm,
    )
    styles, title_style, header_style, _ = _build_styles()
    elements = []

    # Title
    elements.append(Paragraph(escape(str(title)), title_style))
    elements.append(Spacer(1, 0.4 * cm))

    # Table data
    data = [headers] + [list(map(str, row)) for row in rows]
    col_count = len(headers)
    col_width = (doc.width / col_count) if col_count > 0 else doc.width

    table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_INDIGO]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def document_pdf_response(filename: str, title: str, sections: list) -> Response:
    """
    Render a document-style PDF with label/value pairs (for suggestion reports, dashboard summaries).

    :param filename: Attachment filename
    :param title: Document title
    :param sections: List of dicts with keys 'heading' and 'fields'.
                     'fields' is a list of (label, value) tuples.
                     A section may also have 'body' (a raw text block).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles, title_style, header_style, body_style = _build_styles()
    elements = []

    # Title
    elements.append(Paragraph(escape(str(title)), title_style))
    elements.append(Spacer(1, 0.5 * cm))

    for section in sections:
        heading = section.get("heading")
        if heading:
            elements.append(Paragraph(escape(str(heading)), header_style))
            elements.append(Spacer(1, 0.2 * cm))

        fields = section.get("fields", [])
        if fields:
            field_data = [[Paragraph(f"<b>{escape(str(label))}</b>", body_style), Paragraph(escape(str(value)), body_style)]
                          for label, value in fields]
            field_table = Table(field_data, colWidths=[6 * cm, 11 * cm])
            field_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ]))
            elements.append(field_table)
            elements.append(Spacer(1, 0.3 * cm))

        body = section.get("body")
        if body:
            elements.append(Paragraph(escape(str(body)), body_style))
            elements.append(Spacer(1, 0.4 * cm))

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
