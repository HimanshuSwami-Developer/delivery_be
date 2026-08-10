from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User


def _has_role(request, role):
    return bool(
        request.user
        and request.user.is_authenticated
        and (request.user.role == role or request.user.is_superuser)
    )


class IsAdminRoleOrReadOnly(BasePermission):
    """Anyone (even anonymous) can read; only role='admin' (or superuser) can write.

    Used for browse-first resources (categories, products, banners, coupons,
    zones) that the customer app must be able to list without logging in,
    but that only the admin console can create/update/delete.
    """

    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _has_role(request, User.Role.ADMIN)


class IsAdminRole(BasePermission):
    """Allows access only to role='admin' (or superuser) users, for every method."""

    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        return _has_role(request, User.Role.ADMIN)


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: the request.user owns the object (via `.user`/`.customer`
    attribute) or is an admin. Pair with `IsAuthenticated` at the view level.
    """

    def has_object_permission(self, request, view, obj):
        if _has_role(request, User.Role.ADMIN):
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        return owner_id_matches(owner, request.user)


def owner_id_matches(owner, user):
    return bool(owner and user and owner.pk == user.pk)
