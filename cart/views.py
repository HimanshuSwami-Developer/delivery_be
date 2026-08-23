from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from promotions.models import Coupon

from .models import Cart, CartItem, WishlistItem
from .serializers import (
    AddCartItemSerializer,
    ApplyCartCouponSerializer,
    CartSerializer,
    SetCartItemQtySerializer,
    WishlistItemSerializer,
)


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@extend_schema(tags=["Cart"])
class CartView(APIView):
    """
    GET    /api/cart/  -> my cart (items + totals)
    DELETE /api/cart/  -> empty my cart (items + coupon)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get my cart", responses=CartSerializer)
    def get(self, request):
        return Response(CartSerializer(_get_cart(request.user)).data)

    @extend_schema(summary="Empty my cart", responses={204: None})
    def delete(self, request):
        cart = _get_cart(request.user)
        cart.items.all().delete()
        cart.coupon = None
        cart.save(update_fields=["coupon", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Cart"])
class CartItemsView(APIView):
    """POST /api/cart/items/ {product, qty=1} -> add to cart (increments if already present)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Add a product to my cart", request=AddCartItemSerializer, responses=CartSerializer)
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = _get_cart(request.user)
        product = serializer.validated_data["product"]
        qty = serializer.validated_data["qty"]

        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"qty": qty})
        if not created:
            item.qty += qty
            item.save(update_fields=["qty", "updated_at"])

        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Cart"])
class CartItemDetailView(APIView):
    """
    PATCH  /api/cart/items/{product_id}/  {qty}  -> set absolute quantity (0 removes it)
    DELETE /api/cart/items/{product_id}/         -> remove entirely
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Set a cart line's quantity", request=SetCartItemQtySerializer, responses=CartSerializer)
    def patch(self, request, product_id):
        serializer = SetCartItemQtySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = _get_cart(request.user)
        product = get_object_or_404(Product, pk=product_id)
        qty = serializer.validated_data["qty"]

        if qty <= 0:
            CartItem.objects.filter(cart=cart, product=product).delete()
        else:
            CartItem.objects.update_or_create(cart=cart, product=product, defaults={"qty": qty})

        return Response(CartSerializer(cart).data)

    @extend_schema(summary="Remove a product from my cart", responses=CartSerializer)
    def delete(self, request, product_id):
        cart = _get_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return Response(CartSerializer(cart).data)


@extend_schema(tags=["Cart"])
class CartCouponView(APIView):
    """
    POST   /api/cart/coupon/  {code}  -> validate + apply a coupon to my cart
    DELETE /api/cart/coupon/          -> remove the applied coupon
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Apply a coupon to my cart", request=ApplyCartCouponSerializer, responses=CartSerializer)
    def post(self, request):
        serializer = ApplyCartCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"].strip().upper()

        cart = _get_cart(request.user)
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon or not coupon.is_valid_now():
            return Response({"detail": f'"{code}" is not a valid code.'}, status=status.HTTP_400_BAD_REQUEST)
        if coupon.assigned_to_id and coupon.assigned_to_id != request.user.id:
            return Response(
                {"detail": f'"{code}" isn\'t available for your account.'}, status=status.HTTP_403_FORBIDDEN
            )

        subtotal = sum(ci.product.price * ci.qty for ci in cart.items.all())
        if subtotal < coupon.min_order_value:
            return Response(
                {"detail": f"Add ₹{coupon.min_order_value - subtotal} more to use {code}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart.coupon = coupon
        cart.save(update_fields=["coupon", "updated_at"])
        return Response(CartSerializer(cart).data)

    @extend_schema(summary="Remove my cart's coupon", responses=CartSerializer)
    def delete(self, request):
        cart = _get_cart(request.user)
        cart.coupon = None
        cart.save(update_fields=["coupon", "updated_at"])
        return Response(CartSerializer(cart).data)


@extend_schema(tags=["Wishlist"])
class WishlistView(APIView):
    """
    GET  /api/wishlist/  -> my saved products
    POST /api/wishlist/  {product}  -> save a product
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="List my wishlist", responses=WishlistItemSerializer(many=True))
    def get(self, request):
        items = WishlistItem.objects.filter(user=request.user).select_related("product")
        return Response(WishlistItemSerializer(items, many=True).data)

    @extend_schema(summary="Add a product to my wishlist", responses={201: WishlistItemSerializer})
    def post(self, request):
        product = get_object_or_404(Product, pk=request.data.get("product"))
        item, _ = WishlistItem.objects.get_or_create(user=request.user, product=product)
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Wishlist"])
class WishlistDetailView(APIView):
    """DELETE /api/wishlist/{product_id}/ -> remove a product from my wishlist."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Remove a product from my wishlist", responses={204: None})
    def delete(self, request, product_id):
        WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
