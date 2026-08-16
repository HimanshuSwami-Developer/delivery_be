from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OTP, DeviceToken, Profile, User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["mobile_number", "name", "role", "is_active", "is_staff", "date_joined"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["mobile_number", "name"]
    fieldsets = (
        (None, {"fields": ("mobile_number", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("mobile_number", "password1", "password2", "role")}),
    )
    readonly_fields = ["date_joined"]

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["mobile_number", "otp_code", "created_at", "expires_at", "is_verified", "attempt_count", "resend_count"]
    list_filter = ["is_verified"]
    search_fields = ["mobile_number"]
    readonly_fields = [f.name for f in OTP._meta.fields]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_active", "is_delete", "created_at"]
    search_fields = ["name", "user__mobile_number"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "token", "created_at", "updated_at"]
    list_filter = ["platform"]
    search_fields = ["user__mobile_number", "token"]
    readonly_fields = ["created_at", "updated_at"]