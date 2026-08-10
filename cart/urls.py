from django.urls import path

from .views import CartCouponView, CartItemDetailView, CartItemsView, CartView, WishlistDetailView, WishlistView

app_name = "cart"

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemsView.as_view(), name="cart-items"),
    path("cart/items/<int:product_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("cart/coupon/", CartCouponView.as_view(), name="cart-coupon"),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("wishlist/<int:product_id>/", WishlistDetailView.as_view(), name="wishlist-detail"),
]
