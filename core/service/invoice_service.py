from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_INK = colors.HexColor("#0A1F3C")
_MUTED = colors.HexColor("#75777C")
_DIVIDER = colors.HexColor("#DDD5C4")


class InvoiceService:
    """Renders an order's GST tax invoice as a PDF — generated on demand
    straight from the order's own stored/snapshotted data (address, item
    prices, GST slabs), so it's available the instant an order is placed
    and never needs a separate "generate" step or file storage. See
    `OrderViewSet.invoice` (the shared endpoint every role — customer,
    delivery partner, admin — hits, each scoped to the orders their JWT
    already lets them see via `OrderViewSet.get_queryset`)."""

    @staticmethod
    def render_pdf(order) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=_INK, fontSize=20, spaceAfter=2)
        muted = ParagraphStyle("muted", parent=styles["Normal"], textColor=_MUTED, fontSize=9, leading=13)
        label = ParagraphStyle("label", parent=styles["Normal"], textColor=_MUTED, fontSize=8, leading=11)
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)

        story = []
        story.append(Paragraph(settings.INVOICE_SELLER_NAME, h1))
        if settings.INVOICE_SELLER_ADDRESS:
            story.append(Paragraph(settings.INVOICE_SELLER_ADDRESS, muted))
        story.append(Paragraph(f"GSTIN: {settings.INVOICE_SELLER_GSTIN or '—'}", muted))
        story.append(Spacer(1, 10 * mm))

        meta_table = Table(
            [
                [Paragraph("TAX INVOICE", ParagraphStyle("title", parent=styles["Heading2"], textColor=_INK, fontSize=13)),
                 Paragraph(f"Invoice #: <b>{order.order_number}</b><br/>Date: {order.created_at.strftime('%d %b %Y')}", body)],
            ],
            colWidths=[95 * mm, 77 * mm],
        )
        meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(meta_table)
        story.append(Spacer(1, 6 * mm))

        bill_to = "<br/>".join(filter(None, [
            f"<b>Bill to:</b> {order.customer.name or 'Customer'}",
            order.customer.mobile_number,
            order.address_line1,
            order.address_line2,
            ", ".join(filter(None, [order.city, order.state, order.pincode])),
            f"GSTIN: {order.gstin}" if order.gstin else "B2C supply (no buyer GSTIN)",
        ]))
        story.append(Paragraph(bill_to, body))
        story.append(Spacer(1, 8 * mm))

        header = ["#", "Item", "Pack", "Qty", "Rate", "Amount", "GST%", "CGST", "SGST"]
        rows = [header]
        for i, item in enumerate(order.items.all(), start=1):
            rows.append([
                str(i), item.product_name, item.pack or "—", str(item.qty),
                f"Rs {item.rate}", f"Rs {item.amount}", f"{item.gst_slab}%", f"Rs {item.cgst}", f"Rs {item.sgst}",
            ])

        items_table = Table(rows, colWidths=[8 * mm, 48 * mm, 20 * mm, 12 * mm, 18 * mm, 20 * mm, 14 * mm, 18 * mm, 18 * mm], repeatRows=1)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, _DIVIDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF5EC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 8 * mm))

        totals_rows = [["Subtotal", f"Rs {order.subtotal}"]]
        if order.discount:
            totals_rows.append(["Discount", f"-Rs {order.discount}"])
        totals_rows += [
            ["CGST", f"Rs {order.cgst}"],
            ["SGST", f"Rs {order.sgst}"],
            ["Delivery fee", f"Rs {order.delivery_fee}"],
            ["Grand total", f"Rs {order.total}"],
        ]
        totals_table = Table(totals_rows, colWidths=[40 * mm, 30 * mm])
        totals_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, _INK),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 11),
            ("TOPPADDING", (0, -1), (-1, -1), 6),
        ]))
        story.append(Table([[None, totals_table]], colWidths=[105 * mm, 70 * mm]))
        story.append(Spacer(1, 8 * mm))

        payment_line = f"Payment: {order.get_payment_mode_display()} ({order.get_payment_status_display()})"
        if order.payment_transaction_id:
            payment_line += f" · Txn {order.payment_transaction_id}"
        story.append(Paragraph(payment_line, muted))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph("This is a computer-generated invoice and does not require a signature.", label))

        doc.build(story)
        return buffer.getvalue()
