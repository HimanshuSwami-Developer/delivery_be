from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductReview, ProductStock, Subcategory


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = ["id", "category", "name", "image_url", "order"]
        read_only_fields = ["id"]


class CategorySerializer(serializers.ModelSerializer):
    subs = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "key", "name", "image_url", "order",
            "subs", "product_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_subs(self, obj):
        return list(obj.subcategories.values_list("name", flat=True))

    def get_product_count(self, obj):
        return obj.products.count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "product", "image_url", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {"product": {"write_only": True}}


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True, default=None)

    class Meta:
        model = ProductReview
        fields = ["id", "product", "user", "user_name", "rating", "comment", "created_at"]
        read_only_fields = ["id", "user", "user_name", "created_at"]
        extra_kwargs = {"product": {"write_only": True}}


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight shape for grid/list screens (home, category list, search,
    admin products table)."""

    cat = serializers.CharField(source="category.key", read_only=True)
    sub = serializers.CharField(source="subcategory.name", read_only=True, default=None)
    discount_pct = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand", "cat", "sub", "category", "subcategory",
            "pack", "sku", "mrp", "price", "discount_pct", "rating", "ratings_count",
            "is_out_of_stock", "is_active", "main_image_url",
        ]


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    margin_pct = serializers.ReadOnlyField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "hsn_code", "gst_slab", "cost_price", "margin_pct", "images", "reviews",
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Admin create/update — plain FK ids, no nested writes for images
    (use the dedicated ProductImage endpoints for those)."""

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand", "category", "subcategory", "pack", "sku", "hsn_code",
            "description", "mrp", "price", "cost_price", "gst_slab", "is_out_of_stock", "is_active",
            "main_image_url",
        ]
        read_only_fields = ["id"]


class ProductStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    pack = serializers.CharField(source="product.pack", read_only=True)
    main_image_url = serializers.URLField(source="product.main_image_url", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    state = serializers.ReadOnlyField()

    class Meta:
        model = ProductStock
        fields = [
            "id", "product", "product_name", "sku", "pack", "main_image_url",
            "zone", "zone_name", "on_hand", "reserved", "reorder_level", "max_stock", "state",
        ]
        read_only_fields = ["id"]


class ProductStockAdjustSerializer(serializers.Serializer):
    """POST body for `ProductStockViewSet.adjust`: on_hand += delta (delta may be negative)."""

    delta = serializers.IntegerField()
