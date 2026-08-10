from django.contrib import admin

from .models import Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ["name", "is_open", "avg_eta_minutes", "riders_count"]
    list_filter = ["is_open"]
    search_fields = ["name", "address"]
