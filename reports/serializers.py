from rest_framework import serializers

from .models import StoreSettings


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = ["business_name", "address", "gstin", "invoice_prefix"]


class DeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = ["delivery_fee", "free_delivery_enabled", "free_delivery_above"]
