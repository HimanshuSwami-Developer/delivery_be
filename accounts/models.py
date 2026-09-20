import random
import string

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.helper.base import BaseModel


class UserManager(BaseUserManager):
    """Manager for the mobile-number-based User model (no username/email/password login)."""

    def create_user(self, mobile_number, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError("Mobile number is required")
        user = self.model(mobile_number=mobile_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(mobile_number, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """A user identified by mobile number instead of username/email."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        DELIVERY_BOY = "delivery_boy", "Delivery Boy"
        ADMIN = "admin", "Admin"  # app-level admin (e.g. can add/manage products)

    mobile_number = models.CharField(max_length=15, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "mobile_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.mobile_number} ({self.role})"


class DeviceToken(BaseModel):
    """
    One row per device the app was ever registered on, keyed by the FCM
    registration token itself (not per-user) — a token can only ever be
    live on one device, so re-registering an existing token (a different
    account logging in on the same phone, or the OS rotating the token)
    reassigns the row instead of creating a duplicate.
    """

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True, db_index=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)

    def __str__(self):
        return f"{self.user.mobile_number} ({self.platform})"


class OTP(models.Model):
    """
    Stores every OTP that was generated (for real sends and resends).
    Master-OTP logins do NOT create rows here, since no OTP is actually sent.
    """

    mobile_number = models.CharField(max_length=15, db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)
    resend_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["mobile_number", "-created_at"])]

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def generate_otp():
        length = getattr(settings, "OTP_LENGTH", 4)
        return "".join(str(random.randint(0, 9)) for _ in range(length))

    def __str__(self):
        return f"{self.mobile_number} - {self.otp_code} ({'verified' if self.is_verified else 'pending'})"


class Profile(BaseModel):
    """
    One profile per User (linked via OneToOne), filled in after the first
    OTP/master-OTP login. Addresses and GPS locations both live here as
    JSON lists on this same row, rather than as their own tables — so
    there are only two tables total: User and Profile.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)

    referral_code = models.CharField(max_length=12, unique=True, editable=False)
    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals",
        help_text="The profile whose referral code this user signed up with, if any.",
    )

    loyalty_points = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized balance, kept in sync with LoyaltyTransaction via F()-expression "
                   "updates (see LoyaltyTransaction.award_for_order/redeem) — never edit directly.",
    )

    addresses = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of address dicts, e.g. "
            '[{"id": "...", "address_type": "home", "address_line1": "...", '
            '"address_line2": "...", "city": "...", "state": "...", '
            '"country": "...", "pincode": "...", "is_default": true, '
            '"created_at": "...", "updated_at": "..."}]'
        ),
    )

    gps_locations = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of GPS location dicts, e.g. "
            '[{"id": "...", "label": "current", "latitude": 28.6139, '
            '"longitude": 77.2090, "accuracy": 12.5, '
            '"created_at": "...", "updated_at": "..."}]'
        ),
    )

    def __str__(self):
        return f"{self.name} ({self.user.mobile_number})"

    @staticmethod
    def _generate_referral_code():
        """8 chars, uppercase letters + digits — short enough to read out
        loud/type in by hand, long enough that brute-forcing someone else's
        code isn't practical."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(alphabet, k=8))
            if not Profile.objects.filter(referral_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)


class LoyaltyTransaction(BaseModel):
    """One row per point-earning or point-spending event — the audit trail
    behind `Profile.loyalty_points` (kept in sync via F()-expression updates
    here, never edited directly). Points are earned automatically when an
    order is delivered (see `award_for_order`, called from
    `Order.set_status`) and spent by converting them into a personal
    flat-discount `Coupon` (see `redeem`) — the same reward mechanism
    already used for referral bonuses, so redeeming applies at checkout
    exactly like any other coupon."""

    class Reason(models.TextChoices):
        ORDER_REWARD = "order_reward", "Order reward"
        REDEEMED = "redeemed", "Redeemed for coupon"

    # 1 point per this many rupees spent (order total, floor division).
    POINTS_PER_RUPEES = 20
    # 1 point = this many rupees off when redeemed.
    POINTS_TO_RUPEE = 1
    MIN_REDEEM_POINTS = 50

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty_transactions")
    points = models.IntegerField(help_text="Positive = earned, negative = redeemed.")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="loyalty_transactions"
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.mobile_number}: {self.points:+d} ({self.reason})"

    @classmethod
    def award_for_order(cls, order):
        """Idempotent — safe to call more than once for the same order
        (e.g. if a status webhook/admin action re-fires `set_status`)."""
        profile = getattr(order.customer, "profile", None)
        if not profile:
            return
        if cls.objects.filter(order=order, reason=cls.Reason.ORDER_REWARD).exists():
            return
        points = order.total // cls.POINTS_PER_RUPEES
        if points <= 0:
            return
        cls.objects.create(
            user=order.customer, points=points, reason=cls.Reason.ORDER_REWARD,
            order=order, note=f"Order {order.order_number}",
        )
        Profile.objects.filter(pk=profile.pk).update(loyalty_points=models.F("loyalty_points") + points)

    @classmethod
    def redeem(cls, user, points):
        """Raises ValueError (caller turns this into a 400) for any
        business-rule failure — insufficient balance, below the minimum,
        etc. — never a silent no-op, unlike the best-effort
        `award_for_order`, since this is a direct user action."""
        if points < cls.MIN_REDEEM_POINTS:
            raise ValueError(f"Redeem at least {cls.MIN_REDEEM_POINTS} points at a time.")
        profile = getattr(user, "profile", None)
        if not profile or points > profile.loyalty_points:
            raise ValueError("Not enough points.")

        from promotions.models import Coupon

        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        coupon = Coupon.objects.create(
            code=f"LOYALTY{user.id}{suffix}",
            title=f"Redeemed {points} loyalty points",
            flat_discount=points * cls.POINTS_TO_RUPEE,
            assigned_to=user,
        )
        cls.objects.create(
            user=user, points=-points, reason=cls.Reason.REDEEMED, note=f"Redeemed for coupon {coupon.code}",
        )
        Profile.objects.filter(pk=profile.pk).update(loyalty_points=models.F("loyalty_points") - points)
        return coupon