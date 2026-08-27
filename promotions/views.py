from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.permissions import IsAdminRole, IsAdminRoleOrReadOnly

from .models import Banner, Coupon, Notification
from .serializers import BannerSerializer, CouponSerializer, NotificationSerializer, ValidateCouponSerializer


@extend_schema(tags=["Promotions - Coupons"])
class CouponViewSet(viewsets.ModelViewSet):
    """Public read (customer "My coupons" screen); admin-only write (coupon
    management, including the active/paused toggle via PATCH)."""

    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    lookup_field = "code"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]

    @extend_schema(
        summary="Validate a coupon code against a cart subtotal",
        request=ValidateCouponSerializer,
        responses={200: OpenApiResponse(description="{'valid': bool, 'discount': int, ...}")},
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def validate_code(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"].strip().upper()
        subtotal = serializer.validated_data["subtotal"]

        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon or not coupon.is_valid_now():
            return Response({"valid": False, "detail": f'"{code}" is not a valid code.'}, status=status.HTTP_400_BAD_REQUEST)
        if subtotal < coupon.min_order_value:
            return Response(
                {
                    "valid": False,
                    "detail": f"Add ₹{coupon.min_order_value - subtotal} more to use {code}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"valid": True, "code": coupon.code, "discount": coupon.discount_for(subtotal), "label": coupon.title})


@extend_schema(tags=["Promotions - Banners"])
class BannerViewSet(viewsets.ModelViewSet):
    """Public read (home carousel/category strips); admin-only write."""

    queryset = Banner.objects.select_related("category")
    serializer_class = BannerSerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["placement", "is_active", "category"]

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def impression(self, request, pk=None):
        banner = self.get_object()
        banner.track_impression()
        return Response({"detail": "tracked"})


@extend_schema(tags=["Promotions - Notifications"])
class NotificationViewSet(viewsets.ModelViewSet):
    """Admin composes/sends campaigns here; customers get a read-only feed
    of the ones that have actually gone out (`sent_at` is set)."""

    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["audience"]

    def get_queryset(self):
        qs = Notification.objects.all()
        user = self.request.user
        from accounts.models import User

        if user.is_authenticated and (user.role == User.Role.ADMIN or user.is_superuser):
            return qs
        return qs.filter(sent_at__isnull=False)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdminRole()]

    @extend_schema(summary="[Admin] Send a draft campaign now", responses={200: NotificationSerializer})
    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def send_now(self, request, pk=None):
        notification = self.get_object()
        notification.send()
        return Response(NotificationSerializer(notification).data)
