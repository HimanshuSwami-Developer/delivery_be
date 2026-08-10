from django.contrib import admin

from .models import DeliveryPartner


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "partner_code", "zone", "vehicle", "status", "rating"]
    list_filter = ["zone", "status", "vehicle"]
    search_fields = ["name", "partner_code", "user__mobile_number"]
