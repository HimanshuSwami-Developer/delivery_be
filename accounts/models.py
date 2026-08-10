import random

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
        length = getattr(settings, "OTP_LENGTH", 6)
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