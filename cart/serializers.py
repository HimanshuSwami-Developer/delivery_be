from rest_framework import serializers

from catalog.models import Product
from catalog.serializers import ProductListSerializer

from .models import Cart, CartItem, WishlistItem

# Matches BasketCubit.freeDeliveryAbove / the flat delivery fee below it.
FREE_DELIVERY_ABOVE = 199
DELIVERY_FEE = 29


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_detail", "qty", "amount"]
        read_only_fields = ["id"]

    def get_amount(self, obj):
        return obj.product.price * obj.qty


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default=None)
    subtotal = serializers.SerializerMethodField()
    mrp_total = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    delivery_fee = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id", "items", "coupon", "coupon_code", "subtotal", "mrp_total",
            "discount", "delivery_fee", "item_count", "total",
        ]
        read_only_fields = ["id", "coupon"]

    def _subtotal(self, obj):
        return sum(ci.product.price * ci.qty for ci in obj.items.all())

    def get_subtotal(self, obj):
        return self._subtotal(obj)

    def get_mrp_total(self, obj):
        return sum(ci.product.mrp * ci.qty for ci in obj.items.all())

    def get_item_count(self, obj):
        return sum(ci.qty for ci in obj.items.all())

    def get_discount(self, obj):
        subtotal = self._subtotal(obj)
        if obj.coupon and subtotal >= obj.coupon.min_order_value:
            return obj.coupon.discount_for(subtotal)
        return 0

    def get_delivery_fee(self, obj):
        subtotal = self._subtotal(obj)
        return 0 if (subtotal == 0 or subtotal >= FREE_DELIVERY_ABOVE) else DELIVERY_FEE

    def get_total(self, obj):
        subtotal = self._subtotal(obj)
        discount = self.get_discount(obj)
        fee = self.get_delivery_fee(obj)
        return max(subtotal - discount, 0) + fee


class AddCartItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_out_of_stock=False))
    qty = serializers.IntegerField(default=1, min_value=1)


class SetCartItemQtySerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=0, help_text="0 removes the item.")


class ApplyCartCouponSerializer(serializers.Serializer):
    code = serializers.CharField()


class WishlistItemSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "product_detail", "created_at"]
        read_only_fields = ["id", "created_at"]
