from django.contrib import admin

from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["subject", "user__mobile_number"]
