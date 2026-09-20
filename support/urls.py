from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SupportConfigView, SupportTicketViewSet

app_name = "support"

router = DefaultRouter()
router.register("tickets", SupportTicketViewSet, basename="support-ticket")

urlpatterns = [
    path("support-contact/", SupportConfigView.as_view(), name="support-contact"),
    *router.urls,
]
