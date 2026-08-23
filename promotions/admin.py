from django.contrib import admin

from .models import Banner, Coupon, Notification


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "min_order_value", "flat_discount", "percent_discount", "assigned_to", "is_active", "valid_until"]
    list_filter = ["is_active"]
    search_fields = ["code", "title", "assigned_to__mobile_number"]


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["title", "placement", "order", "is_active", "impressions"]
    list_filter = ["placement", "is_active"]
    search_fields = ["title"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "audience", "sent_at", "sent_count", "opened_count"]
    list_filter = ["audience"]
    search_fields = ["title", "body"]
    readonly_fields = ["sent_at", "sent_count"]
