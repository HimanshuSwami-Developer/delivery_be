from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

app_name = "orders"

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

urlpatterns = router.urls
