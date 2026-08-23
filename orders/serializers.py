from django.db import transaction
from rest_framework import serializers

from core.helper.cloudinary_service import upload_image as cloudinary_upload_image
from core.service import groq_service
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
            "subtotal", "discount", "cgst", "sgst", "delivery_fee", "total", "address", "latitude", "longitude",
            "created_at",
        ]

    def get_address(self, obj):
        return ", ".join(p for p in [obj.address_line1, obj.address_line2, obj.city] if p)


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default=None)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "items", "coupon", "coupon_code", "gstin", "address_line1", "address_line2", "city", "state",
            "pincode", "delivery_slot_date", "delivery_slot_label", "payment_screenshot_url",
            "payment_transaction_id", "packed_at", "out_for_delivery_at", "delivered_at", "cancelled_at",
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
    # Drop-pin, for the delivery partner's map view — pulled from the saved
    # address when `address_id` is used (see `validate()`), otherwise taken
    # from these directly (e.g. a manually-typed address with a GPS pin).
    latitude = serializers.FloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, allow_null=True, min_value=-180, max_value=180)
    zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.filter(is_open=True))
    payment_mode = serializers.ChoiceField(choices=Order.PaymentMode.choices, default=Order.PaymentMode.QR)
    delivery_slot_date = serializers.DateField(required=False, allow_null=True)
    delivery_slot_label = serializers.CharField(required=False, allow_blank=True)
    gstin = serializers.CharField(required=False, allow_blank=True)
    # QR checkout only: a screenshot of the completed UPI payment, uploaded
    # to Cloudinary and stored as proof for admin review — see
    # `Order.payment_screenshot_url`. Absent for COD.
    payment_screenshot = serializers.ImageField(required=False, allow_null=True)

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
            # `.get(key, "")` only falls back when the key is *missing* — these
            # come from the profile's stored address JSON, where an optional
            # field like address_line2 (landmark) is often present but `None`
            # rather than absent, so that still leaves `None` here without the
            # explicit `or ""`.
            attrs["address_line1"] = addr.get("address_line1") or ""
            attrs["address_line2"] = addr.get("address_line2") or ""
            attrs["city"] = addr.get("city") or ""
            attrs["state"] = addr.get("state") or ""
            attrs["pincode"] = addr.get("pincode") or ""
            attrs["latitude"] = addr.get("latitude")
            attrs["longitude"] = addr.get("longitude")
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

        screenshot = validated_data.get("payment_screenshot")
        screenshot_url = cloudinary_upload_image(screenshot, folder="payment_screenshots") if screenshot else ""

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                zone=validated_data["zone"],
                payment_mode=validated_data["payment_mode"],
                # `or ""` (not just `.get(key, "")`) so this stays safe even if
                # a future caller passes an explicit `None` for one of these —
                # matches the same guard in `validate()`, kept here too since
                # this is the actual point these hit a NOT NULL column.
                address_line1=validated_data.get("address_line1") or "",
                address_line2=validated_data.get("address_line2") or "",
                city=validated_data.get("city") or "",
                state=validated_data.get("state") or "",
                pincode=validated_data.get("pincode") or "",
                latitude=validated_data.get("latitude"),
                longitude=validated_data.get("longitude"),
                gstin=validated_data.get("gstin", ""),
                delivery_slot_date=validated_data.get("delivery_slot_date"),
                delivery_slot_label=validated_data.get("delivery_slot_label", ""),
                payment_screenshot_url=screenshot_url,
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

        if screenshot_url:
            self._verify_qr_payment(order, screenshot_url)
        return order

    def _verify_qr_payment(self, order, screenshot_url):
        """Best-effort, run after the order (and its `total`) already exist:
        reads the uploaded screenshot via Groq and auto-marks the order paid
        only when both a transaction ID and a matching amount come back.
        Anything short of that — Groq not configured, an unreadable
        screenshot, an amount mismatch — leaves `payment_status` at its
        default 'pending' for an admin to verify by hand instead of
        auto-approving on a guess. Runs outside the placement transaction
        since it's a network call, not something that should hold a DB
        transaction open or roll back order placement if it fails.
        """
        details = groq_service.extract_payment_details(screenshot_url)
        if not details:
            return

        update_fields = []
        if details["transaction_id"]:
            order.payment_transaction_id = details["transaction_id"][:64]
            update_fields.append("payment_transaction_id")

        amount = details["amount"]
        if details["success"] and amount is not None and abs(amount - order.total) <= 1:
            order.payment_status = Order.PaymentStatus.PAID
            update_fields.append("payment_status")

        if update_fields:
            order.save(update_fields=[*update_fields, "updated_at"])


class SetOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class AssignDeliveryPartnerSerializer(serializers.Serializer):
    delivery_partner = serializers.PrimaryKeyRelatedField(queryset=DeliveryPartner.objects.all())
