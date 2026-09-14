from io import BytesIO

from reports.models import StoreSettings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_INK = colors.HexColor("#0A1F3C")
_MUTED = colors.HexColor("#75777C")
_DIVIDER = colors.HexColor("#DDD5C4")


class GstReportService:
    """Renders the monthly GSTR-3B summary (slab-wise taxable value/CGST/
    SGST + net payable) as a PDF, from the same numbers `GstReportView`
    returns to the app — see `reports/views.py`."""

    @staticmethod
    def render_gstr3b_pdf(month_label: str, data: dict) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=_INK, fontSize=20, spaceAfter=2)
        muted = ParagraphStyle("muted", parent=styles["Normal"], textColor=_MUTED, fontSize=9, leading=13)

        seller = StoreSettings.load()
        story = [
            Paragraph(seller.resolved_business_name, h1),
            Paragraph(f"GSTIN: {seller.resolved_gstin or '—'}", muted),
            Spacer(1, 6 * mm),
            Paragraph(
                f"GSTR-3B Summary · {month_label}",
                ParagraphStyle("title", parent=styles["Heading2"], textColor=_INK, fontSize=14),
            ),
            Spacer(1, 8 * mm),
        ]

        header = ["Tax slab", "Taxable value", "CGST", "SGST", "Total tax", "Invoices"]
        rows = [header]
        for row in data["slabs"]:
            rows.append([
                row["slab"], f"Rs {row['taxable_value']}", f"Rs {row['cgst']}",
                f"Rs {row['sgst']}", f"Rs {row['total_tax']}", str(row["invoices"]),
            ])
        table = Table(rows, colWidths=[25 * mm, 32 * mm, 25 * mm, 25 * mm, 28 * mm, 22 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, _DIVIDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF5EC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 8 * mm))

        totals_rows = [
            ["Taxable turnover", f"Rs {data['taxable_turnover']}"],
            ["Output GST (CGST + SGST)", f"Rs {data['output_gst']}"],
            ["Input tax credit", f"Rs {data['input_credit']}"],
            ["Net GST payable", f"Rs {data['net_payable']}"],
        ]
        totals_table = Table(totals_rows, colWidths=[55 * mm, 35 * mm])
        totals_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, _INK),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TOPPADDING", (0, -1), (-1, -1), 6),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph(
            "Input tax credit isn't tracked in this system (no purchases/procurement ledger), so it's reported "
            "as ₹0 — verify separately before filing. This is a computer-generated summary and does not require "
            "a signature.",
            muted,
        ))

        doc.build(story)
        return buffer.getvalue()
