from django.contrib import admin

from .models import SupportConfig, SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["subject", "user__mobile_number"]


@admin.register(SupportConfig)
class SupportConfigAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "whatsapp_number", "reply_time_label"]

    def has_add_permission(self, request):
        # Singleton — one row only, created lazily by SupportConfig.load().
        return not SupportConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
