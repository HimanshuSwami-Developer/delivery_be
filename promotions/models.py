from django.db import models
from django.db.models import Sum
from django.utils import timezone

from core.helper.base import BaseModel


class Coupon(BaseModel):
    code = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=255)
    min_order_value = models.PositiveIntegerField(default=0)
    flat_discount = models.PositiveIntegerField(null=True, blank=True)
    percent_discount = models.PositiveIntegerField(null=True, blank=True, help_text="0-100")
    max_discount = models.PositiveIntegerField(null=True, blank=True, help_text="Cap applied to percent_discount.")
    valid_until = models.DateField(null=True, blank=True)
    terms = models.CharField(max_length=255, blank=True)
    zones = models.ManyToManyField("zones.Zone", blank=True, related_name="coupons", help_text="Empty = all zones.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def discount_for(self, subtotal):
        if subtotal < self.min_order_value:
            return 0
        if self.percent_discount:
            amount = round(subtotal * self.percent_discount / 100)
            return min(amount, self.max_discount) if self.max_discount else amount
        return self.flat_discount or 0

    def is_valid_now(self):
        if not self.is_active:
            return False
        if self.valid_until and timezone.localdate() > self.valid_until:
            return False
        return True

    @property
    def used_count(self):
        return self.orders.exclude(status="cancelled").count()

    @property
    def discount_given(self):
        return self.orders.exclude(status="cancelled").aggregate(total=Sum("discount"))["total"] or 0


class Banner(BaseModel):
    class Placement(models.TextChoices):
        HOME_CAROUSEL = "home_carousel", "Home carousel"
        CATEGORY_STRIP = "category_strip", "Category strip"
        PROFILE = "profile", "Profile"

    title = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)
    placement = models.CharField(max_length=20, choices=Placement.choices, default=Placement.HOME_CAROUSEL)
    category = models.ForeignKey(
        "catalog.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="banners"
    )
    link_screen = models.CharField(max_length=100, blank=True, help_text="Deep-link target, e.g. 'category_list'.")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateField(null=True, blank=True)
    impressions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    def track_impression(self):
        Banner.objects.filter(pk=self.pk).update(impressions=models.F("impressions") + 1)


class Notification(BaseModel):
    class Audience(models.TextChoices):
        ALL = "all", "All users"
        CART_ABANDONERS = "cart_abandoners", "Cart abandoners"
        GOLD_PLATINUM = "gold_platinum", "Gold + Platinum"
        TRANSACTIONAL = "transactional", "Transactional"

    title = models.CharField(max_length=255)
    body = models.CharField(max_length=500)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def send(self):
        """Marks the campaign sent and stamps `sent_count` from the matching
        customer count. No real push-notification transport is wired up
        here (and per-user open tracking doesn't exist), so `opened_count`
        stays admin-editable/manual — this models the campaign ledger, not
        an actual delivery pipeline."""
        from accounts.models import User

        qs = User.objects.filter(role=User.Role.CUSTOMER, is_active=True)
        self.sent_count = qs.count()
        self.sent_at = timezone.now()
        self.save(update_fields=["sent_count", "sent_at", "updated_at"])
