from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name", "pack", "rate", "gst_slab", "qty"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "customer", "zone", "status", "payment_mode", "payment_status",
        "payment_transaction_id", "total", "created_at",
    ]
    list_filter = ["status", "payment_mode", "payment_status", "zone"]
    search_fields = ["order_number", "customer__mobile_number", "payment_transaction_id"]
    readonly_fields = [
        "order_number", "subtotal", "discount", "cgst", "sgst", "total", "payment_screenshot_preview",
    ]
    inlines = [OrderItemInline]

    @admin.display(description="Payment screenshot")
    def payment_screenshot_preview(self, obj):
        if not obj.payment_screenshot_url:
            return "—"
        return format_html(
            '<a href="{0}" target="_blank"><img src="{0}" style="max-height:200px;"></a>', obj.payment_screenshot_url
        )
