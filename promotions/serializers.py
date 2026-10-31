from django.utils import timezone
from rest_framework import serializers

from .models import AppUpdateConfig, Banner, Coupon, FestivalSetting, Notification


class CouponSerializer(serializers.ModelSerializer):
    used_count = serializers.ReadOnlyField()
    discount_given = serializers.ReadOnlyField()
    is_valid_now = serializers.SerializerMethodField()
    usable_by_me = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            "id", "code", "title", "min_order_value", "flat_discount", "percent_discount", "max_discount",
            "valid_until", "terms", "is_active", "used_count", "discount_given", "is_valid_now",
            "usable_by_me", "unavailable_reason", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "used_count", "discount_given", "created_at", "updated_at"]

    def get_is_valid_now(self, obj):
        return obj.is_valid_now()

    def get_usable_by_me(self, obj):
        return self.get_unavailable_reason(obj) is None

    def get_unavailable_reason(self, obj):
        """Why the requesting customer can't apply this coupon right now —
        None when they can. The same rules `CartCouponView` enforces on
        apply, surfaced up front so the app can show the coupon disabled
        instead of letting the customer find out on tap. The cart-dependent
        minimum-order rule is left to the app, which knows the live
        subtotal."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is not None and not user.is_authenticated:
            user = None
        if not obj.is_active:
            return "Not active"
        if obj.valid_until and timezone.localdate() > obj.valid_until:
            return "Expired"
        if obj.assigned_to_id and user is not None and obj.assigned_to_id != user.id:
            return "Not available for your account"
        if obj.assigned_to_id and obj.used_count >= 1:
            return "Already used"
        if user is not None and obj.already_used_by(user):
            return "Already used"
        return None


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


class FestivalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FestivalSetting
        fields = [
            "id", "key", "override_mode", "starts_on", "ends_on", "accent_color", "gradient_start",
            "gradient_end", "motif", "greeting_text", "popup_enabled", "popup_title", "popup_message",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "key", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "title", "body", "audience", "sent_at", "sent_count", "opened_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sent_at", "sent_count", "opened_count", "created_at", "updated_at"]


class AppUpdateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUpdateConfig
        fields = ["min_version_code", "latest_version_code", "title", "message", "updated_at"]
        read_only_fields = ["updated_at"]
