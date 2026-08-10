from rest_framework.routers import DefaultRouter

from .views import DeliveryPartnerViewSet

app_name = "delivery"

router = DefaultRouter()
router.register("partners", DeliveryPartnerViewSet, basename="delivery-partner")

urlpatterns = router.urls
