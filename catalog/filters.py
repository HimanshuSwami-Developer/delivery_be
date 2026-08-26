import django_filters as df

from .models import Product


class ProductFilter(df.FilterSet):
    """Matches the customer app's browse filters (`basket_selectors.dart`
    `visibleListProducts`): category/subcategory by key/name (not numeric
    id, since that's how the Flutter state stores them), a price `band`,
    and an explicit min/max price range for anything finer-grained."""

    category = df.CharFilter(field_name="category__key")
    subcategory = df.CharFilter(field_name="subcategory__name")
    band = df.CharFilter(method="filter_band")
    min_price = df.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = df.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = [
            "category", "subcategory", "band", "min_price", "max_price", "brand",
            "is_out_of_stock", "is_active",
        ]

    def filter_band(self, queryset, name, value):
        if value == "low":
            return queryset.filter(price__lt=50)
        if value == "mid":
            return queryset.filter(price__gte=50, price__lte=200)
        if value == "high":
            return queryset.filter(price__gt=200)
        return queryset
