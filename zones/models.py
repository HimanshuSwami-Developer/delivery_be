from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.helper.base import BaseModel


class Zone(BaseModel):
    """A dark store + the delivery zone it serves — the admin console's
    "Zones & stores" screen and the header's zone switcher both read this."""

    name = models.CharField(max_length=150, help_text="e.g. 'Koramangala dark store'")
    address = models.CharField(max_length=255, blank=True)
    pincodes = models.JSONField(default=list, blank=True, help_text='e.g. ["560034", "560095"]')
    avg_eta_minutes = models.PositiveIntegerField(default=12)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def riders_count(self):
        return self.delivery_partners.filter(is_active=True).count()

    @property
    def orders_today(self):
        # Deferred import: avoids a circular import at app-load time
        # (orders.models references Zone via the "zones.Zone" string, but
        # Zone itself wants to read Order counts back).
        from orders.models import Order

        return Order.objects.filter(zone=self, created_at__date=timezone.localdate()).count()

    @property
    def fill_rate_pct(self):
        """% of orders in the last 30 days that were delivered (not cancelled)."""
        from orders.models import Order

        since = timezone.localdate() - timedelta(days=30)
        qs = Order.objects.filter(zone=self, created_at__date__gte=since)
        total = qs.count()
        if not total:
            return None
        delivered = qs.filter(status=Order.Status.DELIVERED).count()
        return round(100 * delivered / total, 1)
