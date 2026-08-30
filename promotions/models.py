from datetime import timedelta

from django.conf import settings
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
    is_active = models.BooleanField(default=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="personal_coupons",
        help_text="Set for personal one-time coupons (e.g. referral rewards) — only this user may apply it, and only once.",
    )

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
        if self.assigned_to_id and self.used_count >= 1:
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


class FestivalSetting(BaseModel):
    """Admin-editable theme for one festival takeover of the customer app's
    home header (see the Flutter `FestivalTheme`/`FestivalCalendar`
    classes). One row per [Key] — seeded by a data migration so the admin
    console always has all of them ready to edit, no "add new" step
    needed. A key with no matching row (shouldn't normally happen) just
    means the app falls back to its own built-in defaults for that
    festival — this table only ever overrides, never gates, the app
    working at all.
    """

    class Key(models.TextChoices):
        DIWALI = "diwali", "Diwali"
        HOLI = "holi", "Holi"
        CHRISTMAS = "christmas", "Christmas"
        NEW_YEAR = "new_year", "New Year"
        INDEPENDENCE_DAY = "independence_day", "Independence Day"
        RAKSHA_BANDHAN = "raksha_bandhan", "Raksha Bandhan"

    class Motif(models.TextChoices):
        DIYA_LIGHTS = "diyaLights", "Diya / string lights"
        COLOR_SPLASH = "colorSplash", "Colour splash"
        SNOWFALL = "snowfall", "Snowfall"
        CONFETTI = "confetti", "Confetti"

    class OverrideMode(models.TextChoices):
        AUTO = "auto", "Auto — by calendar date"
        FORCE_ON = "force_on", "Always on"
        FORCE_OFF = "force_off", "Always off"

    key = models.CharField(max_length=30, choices=Key.choices, unique=True)
    override_mode = models.CharField(max_length=10, choices=OverrideMode.choices, default=OverrideMode.AUTO)
    starts_on = models.DateField(
        null=True, blank=True,
        help_text="'Auto' mode only. Overrides the app's built-in date window for this year "
                  "(handy for Diwali/Holi/Raksha Bandhan, which move every year). Leave both "
                  "dates blank to keep using the app's built-in window.",
    )
    ends_on = models.DateField(null=True, blank=True)
    accent_color = models.CharField(max_length=9, default="#F3B14A", help_text="Hex, e.g. #F3B14A")
    gradient_start = models.CharField(max_length=9, default="#173C6E", help_text="Header gradient, near corner.")
    gradient_end = models.CharField(max_length=9, default="#0A1F3C", help_text="Header gradient, far corner.")
    motif = models.CharField(max_length=15, choices=Motif.choices, default=Motif.DIYA_LIGHTS)
    greeting_text = models.CharField(max_length=120, blank=True, help_text="Short badge shown in the home header.")
    popup_enabled = models.BooleanField(default=True, help_text="Show the one-time popup on app open, not just the header badge.")
    popup_title = models.CharField(max_length=120, blank=True)
    popup_message = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.get_key_display()


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

    def _audience_queryset(self):
        """Resolves `self.audience` to the matching User queryset. Deferred
        imports of orders/cart avoid a circular import at module load time
        (promotions is imported by cart/orders serializers)."""
        from accounts.models import User

        qs = User.objects.filter(role=User.Role.CUSTOMER, is_active=True)

        if self.audience == self.Audience.CART_ABANDONERS:
            from cart.models import Cart

            cutoff = timezone.now() - timedelta(hours=2)
            abandoned_user_ids = (
                Cart.objects.filter(items__isnull=False, updated_at__lt=cutoff)
                .values_list("user_id", flat=True)
                .distinct()
            )
            return qs.filter(id__in=abandoned_user_ids)

        if self.audience == self.Audience.GOLD_PLATINUM:
            from django.db.models import Count, Q

            from orders.models import Order

            # Matches accounts.views._tier_for's Gold threshold (25+ orders)
            # — Gold and Platinum are both "25 or more", so one filter covers
            # both tiers.
            return qs.annotate(
                orders_count=Count("orders", filter=~Q(orders__status=Order.Status.CANCELLED))
            ).filter(orders_count__gte=25)

        # ALL and TRANSACTIONAL (a content distinction, not a different
        # recipient set — see Audience.TRANSACTIONAL) both target every
        # active customer.
        return qs

    def send(self):
        """Marks the campaign sent, resolves the target audience, and pushes
        to every registered device of matching users via FCM (see
        core.service.push_service — a no-op log line if push isn't
        configured). Tokens FCM reports as unregistered get pruned from
        DeviceToken so future campaigns don't keep hitting them. Per-user
        open tracking doesn't exist, so `opened_count` stays
        admin-editable/manual."""
        from accounts.models import DeviceToken
        from core.service.push_service import PushService

        users = self._audience_queryset()
        tokens = DeviceToken.objects.filter(user__in=users).values_list("token", flat=True)

        _, invalid_tokens = PushService.send_to_tokens(
            tokens, self.title, self.body, data={"notification_id": str(self.id)}
        )
        if invalid_tokens:
            DeviceToken.objects.filter(token__in=invalid_tokens).delete()

        self.sent_count = users.count()
        self.sent_at = timezone.now()
        self.save(update_fields=["sent_count", "sent_at", "updated_at"])
