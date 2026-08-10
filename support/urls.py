from rest_framework.routers import DefaultRouter

from .views import SupportTicketViewSet

app_name = "support"

router = DefaultRouter()
router.register("tickets", SupportTicketViewSet, basename="support-ticket")

urlpatterns = router.urls
