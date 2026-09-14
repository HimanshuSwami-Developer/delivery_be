import csv
import json
from datetime import date, timedelta
from io import StringIO

from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import ProductStock
from core.permissions import IsAdminRole
from core.service.gst_report_service import GstReportService
from orders.models import Order, OrderItem

from .models import StoreSettings
from .serializers import StoreSettingsSerializer


def _parse_month(request):
    today = timezone.localdate()
    month_param = request.query_params.get("month")
    if month_param:
        year, month = (int(p) for p in month_param.split("-"))
    else:
        year, month = today.year, today.month
    return year, month


def _sales_data(months):
    today = timezone.localdate()
    start_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 1):
        start_month = (start_month - timedelta(days=1)).replace(day=1)

    live_qs = Order.objects.exclude(status=Order.Status.CANCELLED)
    this_month_qs = live_qs.filter(created_at__year=today.year, created_at__month=today.month)
    this_month_revenue = this_month_qs.aggregate(v=Sum("total"))["v"] or 0
    this_month_orders = this_month_qs.count()
    avg_basket = round(this_month_revenue / this_month_orders) if this_month_orders else 0

    since_30 = today - timedelta(days=30)
    recent_customers = (
        live_qs.filter(created_at__date__gte=since_30)
        .values("customer")
        .annotate(n=Count("id"))
    )
    total_recent_customers = recent_customers.count()
    repeat_customers = recent_customers.filter(n__gte=2).count()
    repeat_rate = round(100 * repeat_customers / total_recent_customers, 1) if total_recent_customers else None

    monthly_rows = (
        live_qs.filter(created_at__date__gte=start_month)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(revenue=Sum("total"))
        .order_by("month")
    )
    monthly_revenue = [{"month": row["month"].strftime("%Y-%m"), "revenue": row["revenue"]} for row in monthly_rows]

    top_categories = (
        OrderItem.objects.filter(order__in=live_qs, order__created_at__date__gte=since_30)
        .values("product__category__name")
        .annotate(revenue=Sum(F("rate") * F("qty"), output_field=DecimalField()))
        .order_by("-revenue")[:5]
    )
    top_categories_data = [
        {"category": row["product__category__name"], "revenue": row["revenue"]} for row in top_categories
    ]

    return {
        "stats": {
            "revenue_this_month": this_month_revenue,
            "orders_this_month": this_month_orders,
            "avg_basket": avg_basket,
            "repeat_rate_pct": repeat_rate,
        },
        "monthly_revenue": monthly_revenue,
        "top_categories": top_categories_data,
    }


def _gst_slabs_data(year, month):
    live_qs = Order.objects.exclude(status=Order.Status.CANCELLED).filter(
        created_at__year=year, created_at__month=month
    )
    items = OrderItem.objects.filter(order__in=live_qs)

    rows = []
    output_gst_total = 0
    taxable_total = 0
    for slab, label in [("0", "0%"), ("5", "5%"), ("12", "12%"), ("18", "18%")]:
        slab_items = items.filter(gst_slab=slab)
        taxable = sum(i.amount for i in slab_items)
        tax = sum(i.gst_amount for i in slab_items)
        cgst = tax // 2
        sgst = tax - cgst
        invoices = slab_items.values("order").distinct().count()
        rows.append(
            {"slab": label, "taxable_value": taxable, "cgst": cgst, "sgst": sgst, "total_tax": tax, "invoices": invoices}
        )
        output_gst_total += tax
        taxable_total += taxable

    return {
        "taxable_turnover": taxable_total,
        "output_gst": output_gst_total,
        "input_credit": 0,
        "net_payable": output_gst_total,
        "slabs": rows,
    }


@extend_schema(tags=["Admin Reports"])
class DashboardReportView(APIView):
    """
    GET /api/admin/reports/dashboard/ -> everything the admin console's
    Dashboard screen needs, computed from real `Order`/`ProductStock` data:
    today's KPIs (with a real vs-yesterday delta), a 14-day GMV chart,
    low-stock alerts, and the 6 most recent orders.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        live_qs = Order.objects.exclude(status=Order.Status.CANCELLED)
        today_qs = live_qs.filter(created_at__date=today)
        yesterday_qs = live_qs.filter(created_at__date=yesterday)

        today_gmv = today_qs.aggregate(v=Sum("total"))["v"] or 0
        yesterday_gmv = yesterday_qs.aggregate(v=Sum("total"))["v"] or 0
        today_orders = today_qs.count()
        yesterday_orders = yesterday_qs.count()
        avg_basket = round(today_gmv / today_orders) if today_orders else 0

        since_30 = today - timedelta(days=30)
        on_time_qs = Order.objects.filter(
            status=Order.Status.DELIVERED,
            delivered_at__isnull=False,
            out_for_delivery_at__isnull=False,
            created_at__date__gte=since_30,
        )
        on_time_total = on_time_qs.count()
        on_time_hit = sum(
            1
            for o in on_time_qs
            if (o.delivered_at - o.out_for_delivery_at) <= timedelta(minutes=Order.ON_TIME_MINUTES)
        )
        on_time_rate = round(100 * on_time_hit / on_time_total, 1) if on_time_total else None

        chart_start = today - timedelta(days=13)
        chart_rows = (
            live_qs.filter(created_at__date__gte=chart_start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(gmv=Sum("total"))
            .order_by("day")
        )
        chart_by_day = {row["day"]: row["gmv"] for row in chart_rows}
        chart = [
            {"date": (chart_start + timedelta(days=i)).isoformat(), "gmv": chart_by_day.get(chart_start + timedelta(days=i), 0)}
            for i in range(14)
        ]

        low_stock = (
            ProductStock.objects.select_related("product")
            .filter(on_hand__lt=F("reorder_level"))
            .order_by("on_hand")[:8]
        )
        low_stock_data = [
            {
                "product": s.product.name,
                "sku": s.product.sku,
                "on_hand": s.on_hand,
            }
            for s in low_stock
        ]

        recent = live_qs.select_related("customer", "delivery_partner").order_by("-created_at")[:6]
        recent_data = [
            {
                "id": o.id,
                "order_number": o.order_number,
                "customer": o.customer.name or o.customer.mobile_number,
                "item_count": o.item_count,
                "total": o.total,
                "delivery_partner": o.delivery_partner.name if o.delivery_partner else None,
                "status": o.status,
            }
            for o in recent
        ]

        def pct_delta(now, before):
            if not before:
                return None
            return round(100 * (now - before) / before, 1)

        return Response(
            {
                "kpis": {
                    "gmv_today": today_gmv,
                    "gmv_delta_pct": pct_delta(today_gmv, yesterday_gmv),
                    "orders_today": today_orders,
                    "orders_delta_pct": pct_delta(today_orders, yesterday_orders),
                    "avg_basket": avg_basket,
                    "on_time_rate_pct": on_time_rate,
                },
                "chart_14d": chart,
                "low_stock": low_stock_data,
                "recent_orders": recent_data,
            }
        )


@extend_schema(tags=["Admin Reports"])
class SalesReportView(APIView):
    """GET /api/admin/reports/sales/?months=6 -> monthly revenue trend +
    top categories by revenue, both computed from real `Order`/`OrderItem`
    data."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(parameters=[OpenApiParameter("months", int, description="How many trailing months (default 6).")])
    def get(self, request):
        months = int(request.query_params.get("months", 6))
        return Response(_sales_data(months))


@extend_schema(tags=["Admin Reports"])
class SalesReportExportView(APIView):
    """GET /api/admin/reports/sales/export/?months=6 -> the same numbers as
    `SalesReportView`, as a downloadable CSV (headline stats, then monthly
    revenue, then top categories) for the admin console's "Export CSV"
    button."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        parameters=[OpenApiParameter("months", int, description="How many trailing months (default 6).")],
        responses={200: OpenApiResponse(description="text/csv")},
    )
    def get(self, request):
        months = int(request.query_params.get("months", 6))
        data = _sales_data(months)

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Sales report"])
        writer.writerow([])
        writer.writerow(["Revenue this month", data["stats"]["revenue_this_month"]])
        writer.writerow(["Orders this month", data["stats"]["orders_this_month"]])
        writer.writerow(["Avg basket", data["stats"]["avg_basket"]])
        writer.writerow(["Repeat rate %", data["stats"]["repeat_rate_pct"]])
        writer.writerow([])
        writer.writerow(["Month", "Revenue"])
        for row in data["monthly_revenue"]:
            writer.writerow([row["month"], row["revenue"]])
        writer.writerow([])
        writer.writerow(["Category", "Revenue (last 30 days)"])
        for row in data["top_categories"]:
            writer.writerow([row["category"] or "Uncategorised", row["revenue"]])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="sales-report-{months}m.csv"'
        return response


@extend_schema(tags=["Admin Reports"])
class GstReportView(APIView):
    """
    GET /api/admin/reports/gst/?month=YYYY-MM -> slab-wise (0/5/12/18%)
    taxable value, CGST, SGST and invoice count for the month, computed
    from `OrderItem.gst_slab` snapshots. There's no purchases/procurement
    ledger in this project, so "input credit" genuinely can't be computed —
    it's reported as 0 rather than a fabricated number.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(parameters=[OpenApiParameter("month", str, description="YYYY-MM, defaults to the current month.")])
    def get(self, request):
        year, month = _parse_month(request)
        data = _gst_slabs_data(year, month)
        return Response({"month": f"{year:04d}-{month:02d}", **data})


@extend_schema(tags=["Admin Reports"])
class Gstr1ExportView(APIView):
    """GET /api/admin/reports/gst/gstr1/?month=YYYY-MM -> a GSTR-1-shaped
    JSON export for the month: invoice-wise `b2b` for orders with a buyer
    GSTIN, and slab-wise `b2cs` for everything else. Built straight from
    `OrderItem.gst_slab` snapshots, same source as `GstReportView` — this
    is a working export, not a GSTN-portal-certified filing, so review it
    before filing."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(parameters=[OpenApiParameter("month", str, description="YYYY-MM, defaults to the current month.")])
    def get(self, request):
        year, month = _parse_month(request)
        live_qs = (
            Order.objects.exclude(status=Order.Status.CANCELLED)
            .filter(created_at__year=year, created_at__month=month)
            .prefetch_related("items")
        )

        b2b_invoices_by_gstin = {}
        b2cs_by_slab = {}
        for order in live_qs:
            for item in order.items.all():
                if order.gstin:
                    invoices = b2b_invoices_by_gstin.setdefault(order.gstin, {})
                    invoice = invoices.setdefault(
                        order.order_number,
                        {"inum": order.order_number, "idt": order.created_at.strftime("%d-%m-%Y"), "val": order.total, "itms": []},
                    )
                    invoice["itms"].append(
                        {"rt": float(item.gst_slab), "txval": item.amount, "camt": item.cgst, "samt": item.sgst}
                    )
                else:
                    slab_row = b2cs_by_slab.setdefault(
                        item.gst_slab, {"rt": float(item.gst_slab), "txval": 0, "camt": 0, "samt": 0}
                    )
                    slab_row["txval"] += item.amount
                    slab_row["camt"] += item.cgst
                    slab_row["samt"] += item.sgst

        payload = {
            "gstin": StoreSettings.load().resolved_gstin,
            "fp": f"{month:02d}{year:04d}",
            "b2b": [{"ctin": gstin, "inv": list(invoices.values())} for gstin, invoices in b2b_invoices_by_gstin.items()],
            "b2cs": list(b2cs_by_slab.values()),
        }
        response = HttpResponse(json.dumps(payload, indent=2), content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="gstr1-{year:04d}-{month:02d}.json"'
        return response


@extend_schema(tags=["Admin Reports"])
class Gstr3bExportView(APIView):
    """GET /api/admin/reports/gst/gstr3b/?month=YYYY-MM -> the same
    slab-wise numbers as `GstReportView`, rendered as a downloadable
    GSTR-3B summary PDF."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        parameters=[OpenApiParameter("month", str, description="YYYY-MM, defaults to the current month.")],
        responses={200: OpenApiResponse(description="application/pdf")},
    )
    def get(self, request):
        year, month = _parse_month(request)
        data = _gst_slabs_data(year, month)
        month_label = date(year, month, 1).strftime("%B %Y")
        pdf_bytes = GstReportService.render_gstr3b_pdf(month_label, data)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="gstr3b-{year:04d}-{month:02d}.pdf"'
        return response


@extend_schema(tags=["Admin Reports"])
class StoreSettingsView(RetrieveUpdateAPIView):
    """
    GET/PATCH /api/admin/reports/settings/ -> the seller's own GST profile
    (business name, address, GSTIN) — printed on every generated invoice
    and the GSTR-3B summary. Editing it here (instead of only via server
    env vars) is what makes the admin console's GST settings panel take
    effect on the next invoice/report generated, with no deploy needed.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        return StoreSettings.load()
