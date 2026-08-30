from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, CouponViewSet, FestivalSettingViewSet, NotificationViewSet

app_name = "promotions"

router = DefaultRouter()
router.register("coupons", CouponViewSet, basename="coupon")
router.register("banners", BannerViewSet, basename="banner")
router.register("festival-settings", FestivalSettingViewSet, basename="festival-setting")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls
