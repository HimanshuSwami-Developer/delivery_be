from django.db import transaction
from rest_framework import serializers

from delivery.models import DeliveryPartner
from zones.models import Zone

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    amount = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "pack", "rate", "gst_slab", "qty", "amount"]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    customer_mobile = serializers.CharField(source="customer.mobile_number", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    delivery_partner_name = serializers.CharField(source="delivery_partner.name", read_only=True, default=None)
    item_count = serializers.ReadOnlyField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "customer_name", "customer_mobile", "zone", "zone_name",
            "delivery_partner", "delivery_partner_name", "status", "payment_mode", "payment_status", "item_count",
            "subtotal", "discount", "cgst", "sgst", "delivery_fee", "total", "address", "created_at",
        ]

    def get_address(self, obj):
        return ", ".join(p for p in [obj.address_line1, obj.address_line2, obj.city] if p)


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default=None)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "items", "coupon", "coupon_code", "gstin", "address_line1", "address_line2", "city", "state",
            "pincode", "delivery_slot_date", "delivery_slot_label", "razorpay_order_id",
            "packed_at", "out_for_delivery_at", "delivered_at", "cancelled_at",
        ]


class PlaceOrderSerializer(serializers.Serializer):
    """Places an order from the customer's current cart (server-side —
    the client never posts line items directly), mirroring the Flutter
    checkout flow: cart -> address -> slot -> payment -> place."""

    address_id = serializers.CharField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(required=False, allow_blank=True)
    address_line2 = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True)
    zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.filter(is_open=True))
    payment_mode = serializers.ChoiceField(choices=Order.PaymentMode.choices, default=Order.PaymentMode.UPI)
    delivery_slot_date = serializers.DateField(required=False, allow_null=True)
    delivery_slot_label = serializers.CharField(required=False, allow_blank=True)
    gstin = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        if attrs.get("address_id"):
            profile = getattr(request.user, "profile", None)
            addr = None
            if profile:
                addr = next(
                    (a for a in profile.addresses if a.get("id") == attrs["address_id"] and not a.get("is_delete")),
                    None,
                )
            if not addr:
                raise serializers.ValidationError({"address_id": "Address not found."})
            attrs["address_line1"] = addr.get("address_line1", "")
            attrs["address_line2"] = addr.get("address_line2", "")
            attrs["city"] = addr.get("city", "")
            attrs["state"] = addr.get("state", "")
            attrs["pincode"] = addr.get("pincode", "")
        elif not attrs.get("address_line1"):
            raise serializers.ValidationError("Provide either address_id, or address_line1/city/state/pincode.")
        return attrs

    def create(self, validated_data):
        from cart.models import Cart  # deferred: avoids a hard orders<->cart import cycle

        request = self.context["request"]
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = list(cart.items.select_related("product"))
        if not cart_items:
            raise serializers.ValidationError("Your cart is empty.")

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                zone=validated_data["zone"],
                payment_mode=validated_data["payment_mode"],
                address_line1=validated_data.get("address_line1", ""),
                address_line2=validated_data.get("address_line2", ""),
                city=validated_data.get("city", ""),
                state=validated_data.get("state", ""),
                pincode=validated_data.get("pincode", ""),
                gstin=validated_data.get("gstin", ""),
                delivery_slot_date=validated_data.get("delivery_slot_date"),
                delivery_slot_label=validated_data.get("delivery_slot_label", ""),
                coupon=cart.coupon,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=ci.product,
                        product_name=ci.product.name,
                        pack=ci.product.pack,
                        rate=ci.product.price,
                        gst_slab=ci.product.gst_slab,
                        qty=ci.qty,
                    )
                    for ci in cart_items
                ]
            )
            order.recalculate_totals()
            cart.items.all().delete()
            cart.coupon = None
            cart.save(update_fields=["coupon", "updated_at"])
        return order


class VerifyPaymentSerializer(serializers.Serializer):
    """Posted once Razorpay's checkout popup calls back with a successful
    payment — verified server-side against RAZORPAY_KEY_SECRET before the
    order is ever marked paid (never trust the client's word alone)."""

    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class PaymentFailedSerializer(serializers.Serializer):
    """Best-effort client telemetry for a failed/cancelled Razorpay
    checkout — every field optional since this must never itself fail to
    validate (the client is already in an error state when it posts here)."""

    reason = serializers.CharField(required=False, allow_blank=True, default="")
    razorpay_payment_id = serializers.CharField(required=False, allow_blank=True, default="")


class SetOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class AssignDeliveryPartnerSerializer(serializers.Serializer):
    delivery_partner = serializers.PrimaryKeyRelatedField(queryset=DeliveryPartner.objects.all())
