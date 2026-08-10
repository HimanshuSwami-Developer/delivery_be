from rest_framework import serializers

from .models import Zone


class ZoneSerializer(serializers.ModelSerializer):
    riders_count = serializers.ReadOnlyField()
    orders_today = serializers.ReadOnlyField()
    fill_rate_pct = serializers.ReadOnlyField()

    class Meta:
        model = Zone
        fields = [
            "id", "name", "address", "pincodes", "avg_eta_minutes", "is_open",
            "riders_count", "orders_today", "fill_rate_pct", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
