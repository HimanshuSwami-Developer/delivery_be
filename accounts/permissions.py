from rest_framework.permissions import BasePermission

from .models import User


class IsAdminRole(BasePermission):
    """Allows access only to users with role='admin' (e.g. product management)."""

    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsDeliveryBoyRole(BasePermission):
    """Allows access only to users with role='delivery_boy'."""

    message = "Only delivery agents can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.DELIVERY_BOY
        )


class IsCustomerRole(BasePermission):
    """Allows access only to users with role='customer'."""

    message = "Only customers can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.CUSTOMER
        )