from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.helper.base import BaseModel


class DeliveryPartner(BaseModel):
    class Vehicle(models.TextChoices):
        BIKE = "bike", "Motorbike"
        SCOOTER = "scooter", "Scooter"
        BICYCLE = "bicycle", "Bicycle"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ON_TRIP = "on_trip", "On trip"
        OFF_DUTY = "off_duty", "Off duty"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delivery_partner_profile"
    )
    partner_code = models.CharField(max_length=30, unique=True, help_text="e.g. 'BSK-DP-2210'")
    name = models.CharField(max_length=255)
    vehicle = models.CharField(max_length=20, choices=Vehicle.choices, default=Vehicle.BIKE)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFF_DUTY)
    photo_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.partner_code})"

    @property
    def trips_today(self):
        from orders.models import Order

        return Order.objects.filter(
            delivery_partner=self, out_for_delivery_at__date=timezone.localdate()
        ).count()

    @property
    def on_time_pct(self):
        """% of the partner's delivered orders in the last 30 days that were
        delivered within `Order.ON_TIME_MINUTES` of being handed off."""
        from orders.models import Order

        since = timezone.localdate() - timedelta(days=30)
        qs = Order.objects.filter(
            delivery_partner=self,
            status=Order.Status.DELIVERED,
            delivered_at__isnull=False,
            out_for_delivery_at__isnull=False,
            created_at__date__gte=since,
        )
        total = qs.count()
        if not total:
            return None
        on_time = sum(
            1
            for o in qs
            if (o.delivered_at - o.out_for_delivery_at) <= timedelta(minutes=Order.ON_TIME_MINUTES)
        )
        return round(100 * on_time / total, 1)

    @property
    def earnings_this_month_paise(self):
        """Flat ₹35/delivered-order payout for this calendar month (a simple
        stand-in for a real payout ledger, which is out of scope here)."""
        from orders.models import Order

        now = timezone.localtime()
        count = Order.objects.filter(
            delivery_partner=self,
            status=Order.Status.DELIVERED,
            delivered_at__year=now.year,
            delivered_at__month=now.month,
        ).count()
        return count * 35 * 100
