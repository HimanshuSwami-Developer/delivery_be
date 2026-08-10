from django.conf import settings
from django.db import models

from core.helper.base import BaseModel


class Cart(BaseModel):
    """One cart per user — matches `BasketState.cart` (a single map of
    productId -> qty), not a multi-cart-per-user design."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    coupon = models.ForeignKey(
        "promotions.Coupon", on_delete=models.SET_NULL, null=True, blank=True, related_name="active_in_carts"
    )

    def __str__(self):
        return f"Cart({self.user.mobile_number})"


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items")
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ["cart", "product"]

    def __str__(self):
        return f"{self.product.sku} x{self.qty}"


class WishlistItem(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        unique_together = ["user", "product"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.mobile_number} ♥ {self.product.sku}"
