from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User
from core.permissions import IsAdminRole

from .models import Order
from .serializers import (
    AssignDeliveryPartnerSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    PlaceOrderSerializer,
    SetOrderStatusSerializer,
)


@extend_schema(tags=["Orders"])
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Customers see only their own orders (`orders_view`/`order_detail_view`/
    `order_tracking_view` all read from here); admins see every order and
    get the extra `set_status`/`assign_partner` actions (order management +
    order detail screens). Orders are never created/edited with a plain
    POST/PUT — `place` builds one from the customer's cart, and every other
    mutation goes through its own explicit action.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "zone", "payment_mode"]

    def get_queryset(self):
        qs = Order.objects.select_related("customer", "zone", "delivery_partner", "coupon").prefetch_related("items")
        user = self.request.user
        if user.is_authenticated and (user.role == User.Role.ADMIN or user.is_superuser):
            return qs
        return qs.filter(customer=user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        if self.action == "place":
            return PlaceOrderSerializer
        if self.action == "set_status":
            return SetOrderStatusSerializer
        if self.action == "assign_partner":
            return AssignDeliveryPartnerSerializer
        return OrderListSerializer

    @extend_schema(summary="Place an order from my current cart", responses={201: OrderDetailSerializer})
    @action(detail=False, methods=["post"])
    def place(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order.send_placed_push()
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Cancel my order (only while New/Packed)", responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.Status.NEW, Order.Status.PACKED):
            return Response(
                {"detail": f"Cannot cancel an order that is already '{order.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.set_status(Order.Status.CANCELLED)
        return Response(OrderDetailSerializer(order).data)

    @extend_schema(summary="[Admin] Update order status", responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["patch"], permission_classes=[IsAdminRole])
    def set_status(self, request, pk=None):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.set_status(serializer.validated_data["status"])
        return Response(OrderDetailSerializer(order).data)

    @extend_schema(summary="[Admin] Assign/reassign a delivery partner", responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def assign_partner(self, request, pk=None):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.delivery_partner = serializer.validated_data["delivery_partner"]
        update_fields = ["delivery_partner", "updated_at"]
        order.save(update_fields=update_fields)
        if order.status == Order.Status.NEW:
            order.set_status(Order.Status.PACKED)
        return Response(OrderDetailSerializer(order).data)
