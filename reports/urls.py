from django.urls import path

from .views import (
    DashboardReportView,
    DeliveredSalesExportView,
    DeliveredSalesReportView,
    GstReportView,
    Gstr1ExportView,
    Gstr3bExportView,
    SalesReportExportView,
    SalesReportView,
    StoreSettingsView,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardReportView.as_view(), name="dashboard"),
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("sales/export/", SalesReportExportView.as_view(), name="sales-export"),
    path("sales/delivered/", DeliveredSalesReportView.as_view(), name="sales-delivered"),
    path("sales/delivered/export/", DeliveredSalesExportView.as_view(), name="sales-delivered-export"),
    path("gst/", GstReportView.as_view(), name="gst"),
    path("gst/gstr1/", Gstr1ExportView.as_view(), name="gst-gstr1"),
    path("gst/gstr3b/", Gstr3bExportView.as_view(), name="gst-gstr3b"),
    path("settings/", StoreSettingsView.as_view(), name="settings"),
]
