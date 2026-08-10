from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.helper.cloudinary_service import upload_image as cloudinary_upload_image
from core.mixins import ReadAfterWriteMixin
from core.permissions import IsAdminRole, IsAdminRoleOrReadOnly

from .filters import ProductFilter
from .models import Category, Product, ProductImage, ProductReview, ProductStock, Subcategory
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductReviewSerializer,
    ProductStockAdjustSerializer,
    ProductStockSerializer,
    ProductWriteSerializer,
    SubcategorySerializer,
)


@extend_schema(tags=["Catalog - Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    """Public read (home/category screens); admin-only write (category management)."""

    queryset = Category.objects.prefetch_related("subcategories", "products")
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    lookup_field = "key"
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "key"]


@extend_schema(tags=["Catalog - Categories"])
class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.select_related("category")
    serializer_class = SubcategorySerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category"]


@extend_schema(
    tags=["Catalog - Products"],
    summary="Upload an image to Cloudinary",
    description="Admin-only. Uploads `file` (multipart) straight to Cloudinary and "
    "returns its `secure_url` — pass that back as `main_image_url` / "
    "`ProductImage.image_url`, or use the per-product/`product-images` "
    "shortcuts below which do the save for you.",
)
class ImageUploadView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"url": cloudinary_upload_image(file)})


@extend_schema(tags=["Catalog - Products"])
class ProductViewSet(ReadAfterWriteMixin, viewsets.ModelViewSet):
    """
    Public read (browse/search/PDP); admin-only write (products/add-product
    screens). List/retrieve use lighter/heavier serializers respectively —
    matches `BasketProduct` (list) vs the PDP's extra description/images/
    reviews fields. `create`/`update` accept the narrower
    `ProductWriteSerializer` shape but respond with `ProductDetailSerializer`
    (see `ReadAfterWriteMixin`), so callers always get `cat`/`discount_pct`/
    etc. back — not just the plain FK ids they posted.
    """

    queryset = Product.objects.select_related("category", "subcategory").prefetch_related("images", "reviews")
    permission_classes = [IsAdminRoleOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "sku"]
    ordering_fields = ["price", "ratings_count", "name", "created_at"]
    read_serializer_class = ProductDetailSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        return ProductListSerializer

    @extend_schema(
        summary="Search products",
        description="Same as `?search=<query>`, kept as its own path to match "
        "the customer app's `search_view` 1:1 (top-8 results, name/brand/sub match).",
    )
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def search(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([])
        qs = self.filter_queryset(self.get_queryset()).filter(name__icontains=query)[:8]
        return Response(ProductListSerializer(qs, many=True).data)

    @extend_schema(
        summary="Upload the product's main image",
        description="Admin-only. Uploads `file` (multipart) to Cloudinary and saves "
        "the returned secure_url as `main_image_url` on this product.",
        responses=ProductDetailSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole], parser_classes=[MultiPartParser])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        product.main_image_url = cloudinary_upload_image(file)
        product.save(update_fields=["main_image_url", "updated_at"])
        return Response(ProductDetailSerializer(product).data)


@extend_schema(tags=["Catalog - Products"])
class ProductImageViewSet(viewsets.ModelViewSet):
    """Supports two ways to attach an image: POST JSON with `image_url`
    (already-hosted image), or POST multipart with `file` (uploaded to
    Cloudinary here, then saved as `image_url`)."""

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def create(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return super().create(request, *args, **kwargs)
        data = request.data.copy()
        data["image_url"] = cloudinary_upload_image(file)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(tags=["Catalog - Reviews"])
class ProductReviewViewSet(viewsets.ModelViewSet):
    """Anyone can read a product's reviews; only an authenticated customer
    can post one (one review per product per user)."""

    queryset = ProductReview.objects.select_related("user")
    serializer_class = ProductReviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=["Catalog - Inventory"])
class ProductStockViewSet(viewsets.ModelViewSet):
    """Admin-only: the Inventory screen's stock table + the +/- adjust
    control (`incAdjust`/`decAdjust` in the Flutter cubit, done server-side
    here instead of as a client-only draft delta)."""

    queryset = ProductStock.objects.select_related("product", "zone")
    serializer_class = ProductStockSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["zone", "product"]

    @extend_schema(request=ProductStockAdjustSerializer, responses=ProductStockSerializer)
    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        stock = self.get_object()
        serializer = ProductStockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stock.on_hand = max(0, stock.on_hand + serializer.validated_data["delta"])
        stock.save(update_fields=["on_hand", "updated_at"])
        return Response(ProductStockSerializer(stock).data)
