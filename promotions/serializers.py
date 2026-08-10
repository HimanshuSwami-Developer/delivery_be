from rest_framework import serializers

from .models import Banner, Coupon, Notification


class CouponSerializer(serializers.ModelSerializer):
    used_count = serializers.ReadOnlyField()
    discount_given = serializers.ReadOnlyField()
    is_valid_now = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            "id", "code", "title", "min_order_value", "flat_discount", "percent_discount", "max_discount",
            "valid_until", "terms", "zones", "is_active", "used_count", "discount_given", "is_valid_now",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "used_count", "discount_given", "created_at", "updated_at"]

    def get_is_valid_now(self, obj):
        return obj.is_valid_now()


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField()
    subtotal = serializers.IntegerField(min_value=0)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = [
            "id", "title", "image_url", "placement", "category", "link_screen", "order",
            "is_active", "starts_at", "impressions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "impressions", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "title", "body", "audience", "sent_at", "sent_count", "opened_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sent_at", "sent_count", "opened_count", "created_at", "updated_at"]
