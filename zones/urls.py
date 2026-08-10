from rest_framework.routers import DefaultRouter

from .views import ZoneViewSet

app_name = "zones"

router = DefaultRouter()
router.register("zones", ZoneViewSet, basename="zone")

urlpatterns = router.urls
