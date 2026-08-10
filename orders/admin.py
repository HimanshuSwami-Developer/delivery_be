from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name", "pack", "rate", "gst_slab", "qty"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "customer", "zone", "status", "payment_mode", "total", "created_at"]
    list_filter = ["status", "payment_mode", "zone"]
    search_fields = ["order_number", "customer__mobile_number"]
    readonly_fields = ["order_number", "subtotal", "discount", "cgst", "sgst", "total"]
    inlines = [OrderItemInline]
