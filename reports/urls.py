from django.urls import path

from .views import DashboardReportView, GstReportView, SalesReportView

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardReportView.as_view(), name="dashboard"),
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("gst/", GstReportView.as_view(), name="gst"),
]
