from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models

from core.helper.base import BaseModel


class Category(BaseModel):
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, help_text="Cloudinary secure_url — set via /images/upload/.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Subcategory(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, help_text="Cloudinary secure_url — set via /images/upload/.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ["category", "name"]
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class GstRate(BaseModel):
    """An admin-defined GST rate (e.g. "GST 5%" = CGST 2.5% + SGST 2.5%),
    created from the admin console's GST reports screen and picked per
    product on the product form. The customer price is the product's base
    `price` plus CGST + SGST — see `Product.selling_price`."""

    name = models.CharField(max_length=50)
    cgst_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["cgst_pct", "sgst_pct", "name"]

    def __str__(self):
        return f"{self.name} (CGST {self.cgst_pct}% + SGST {self.sgst_pct}%)"

    @property
    def total_pct(self):
        return self.cgst_pct + self.sgst_pct


def _rupees(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class Product(BaseModel):
    class GstSlab(models.TextChoices):
        ZERO = "0", "0%"
        FIVE = "5", "5%"
        TWELVE = "12", "12%"
        EIGHTEEN = "18", "18%"

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    subcategory = models.ForeignKey(
        Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    pack = models.CharField(max_length=50, help_text="e.g. '5 kg', '500 ml'")
    sku = models.CharField(max_length=30, unique=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    mrp = models.PositiveIntegerField(help_text="MRP in rupees (whole number, paise not tracked).")
    price = models.PositiveIntegerField(help_text="Selling price in rupees.")
    cost_price = models.PositiveIntegerField(
        null=True, blank=True, help_text="What we pay for it; used to compute margin_pct. Optional."
    )
    # Legacy fixed slab — only used when `gst_rate` is unset.
    gst_slab = models.CharField(max_length=2, choices=GstSlab.choices, default=GstSlab.FIVE)
    gst_rate = models.ForeignKey(
        GstRate, on_delete=models.PROTECT, null=True, blank=True, related_name="products",
        help_text="CGST/SGST applied on top of `price` to get the customer price.",
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    ratings_count = models.PositiveIntegerField(default=0)
    is_out_of_stock = models.BooleanField(
        default=False, help_text="Manual override; real stock lives in ProductStock."
    )
    main_image_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def cgst_pct(self) -> Decimal:
        if self.gst_rate_id:
            return self.gst_rate.cgst_pct
        return Decimal(self.gst_slab or "0") / 2

    @property
    def sgst_pct(self) -> Decimal:
        if self.gst_rate_id:
            return self.gst_rate.sgst_pct
        return Decimal(self.gst_slab or "0") / 2

    @property
    def gst_pct(self) -> Decimal:
        return self.cgst_pct + self.sgst_pct

    @property
    def selling_price(self) -> int:
        """What the customer sees and pays per unit: base `price` + CGST +
        SGST, rounded to the nearest whole rupee."""
        return _rupees(Decimal(self.price) * (100 + self.gst_pct) / 100)

    @property
    def discount_pct(self):
        if not self.mrp:
            return 0
        return max(round(100 * (1 - self.selling_price / self.mrp)), 0)

    @property
    def margin_pct(self):
        if not self.price or self.cost_price is None:
            return None
        return round(100 * (self.price - self.cost_price) / self.price, 1)

    def recalculate_rating(self):
        """Recomputes the denormalized `rating`/`ratings_count` from live
        `ProductReview` rows — called by `ProductReview.save()`/`delete()`
        so these stay in sync with reviews as they're posted, edited, or
        removed, instead of needing an admin to hand-set them."""
        agg = self.reviews.aggregate(avg=models.Avg("rating"), count=models.Count("id"))
        Product.objects.filter(pk=self.pk).update(
            rating=round(agg["avg"] or 0, 1),
            ratings_count=agg["count"] or 0,
        )


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.sku} image #{self.order}"


class ProductStock(BaseModel):
    """One stock row per product — there's a single store, so this used to
    be keyed by (product, zone) and is now just keyed by product."""

    class State(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        LOW = "low", "Below reorder"
        OUT = "out_of_stock", "Out of stock"

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stock")
    on_hand = models.IntegerField(default=0)
    reserved = models.IntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=20)
    max_stock = models.PositiveIntegerField(default=200)

    class Meta:
        ordering = ["product__name"]

    def __str__(self):
        return f"{self.product.sku}: {self.on_hand}"

    @property
    def state(self):
        if self.on_hand <= 0:
            return self.State.OUT
        if self.on_hand < self.reorder_level:
            return self.State.LOW
        return self.State.HEALTHY


class ProductReview(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ["product", "user"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.sku} - {self.rating}★ by {self.user.mobile_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.recalculate_rating()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.recalculate_rating()
