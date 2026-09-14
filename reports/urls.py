from django.urls import path

from .views import (
    DashboardReportView,
    GstReportView,
    Gstr1ExportView,
    Gstr3bExportView,
    SalesReportExportView,
    SalesReportView,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardReportView.as_view(), name="dashboard"),
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("sales/export/", SalesReportExportView.as_view(), name="sales-export"),
    path("gst/", GstReportView.as_view(), name="gst"),
    path("gst/gstr1/", Gstr1ExportView.as_view(), name="gst-gstr1"),
    path("gst/gstr3b/", Gstr3bExportView.as_view(), name="gst-gstr3b"),
]
