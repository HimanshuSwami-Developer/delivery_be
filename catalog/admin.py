from django.contrib import admin

from .models import Category, Product, ProductImage, ProductReview, ProductStock, Subcategory


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "key", "order", "is_active"]
    search_fields = ["name", "key"]
    inlines = [SubcategoryInline]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductStockInline(admin.TabularInline):
    model = ProductStock
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "brand", "category", "subcategory", "price", "mrp", "is_out_of_stock"]
    list_filter = ["category", "subcategory", "is_out_of_stock", "gst_slab"]
    search_fields = ["name", "brand", "sku"]
    inlines = [ProductImageInline, ProductStockInline]


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "created_at"]
    list_filter = ["rating"]


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ["product", "zone", "on_hand", "reserved", "reorder_level", "state"]
    list_filter = ["zone"]
    search_fields = ["product__name", "product__sku"]
