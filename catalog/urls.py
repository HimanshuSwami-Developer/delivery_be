from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ImageUploadView,
    ProductImageViewSet,
    ProductReviewViewSet,
    ProductStockViewSet,
    ProductViewSet,
    SubcategoryViewSet,
)

app_name = "catalog"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("subcategories", SubcategoryViewSet, basename="subcategory")
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("reviews", ProductReviewViewSet, basename="product-review")
router.register("stocks", ProductStockViewSet, basename="product-stock")

urlpatterns = [
    path("images/upload/", ImageUploadView.as_view(), name="image-upload"),
] + router.urls
