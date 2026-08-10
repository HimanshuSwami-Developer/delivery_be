from rest_framework import serializers

from accounts.models import User

from .models import DeliveryPartner


class DeliveryPartnerSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    trips_today = serializers.ReadOnlyField()
    on_time_pct = serializers.ReadOnlyField()
    earnings_this_month_paise = serializers.ReadOnlyField()
    mobile_number = serializers.CharField(source="user.mobile_number", read_only=True)

    class Meta:
        model = DeliveryPartner
        fields = [
            "id", "user", "mobile_number", "partner_code", "name", "vehicle", "zone", "zone_name",
            "rating", "status", "photo_url", "trips_today", "on_time_pct", "earnings_this_month_paise",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "mobile_number", "created_at", "updated_at"]


class DeliveryPartnerWriteSerializer(serializers.ModelSerializer):
    """Admin create/update. `mobile_number` on create either attaches an
    existing (role=delivery_boy) user or provisions a brand new one — the
    partner still logs in later via the normal OTP flow on that number."""

    mobile_number = serializers.CharField(write_only=True)

    class Meta:
        model = DeliveryPartner
        fields = ["id", "mobile_number", "partner_code", "name", "vehicle", "zone", "rating", "status", "photo_url"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        mobile_number = validated_data.pop("mobile_number")
        user, _ = User.objects.get_or_create(
            mobile_number=mobile_number, defaults={"role": User.Role.DELIVERY_BOY, "name": validated_data.get("name", "")}
        )
        if user.role != User.Role.DELIVERY_BOY:
            user.role = User.Role.DELIVERY_BOY
            user.save(update_fields=["role"])
        return DeliveryPartner.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("mobile_number", None)
        return super().update(instance, validated_data)
