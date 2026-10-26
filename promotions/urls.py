from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AppUpdateConfigView, BannerViewSet, CouponViewSet, FestivalSettingViewSet, NotificationViewSet

app_name = "promotions"

router = DefaultRouter()
router.register("coupons", CouponViewSet, basename="coupon")
router.register("banners", BannerViewSet, basename="banner")
router.register("festival-settings", FestivalSettingViewSet, basename="festival-setting")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("app-update/", AppUpdateConfigView.as_view(), name="app-update"),
] + router.urls
