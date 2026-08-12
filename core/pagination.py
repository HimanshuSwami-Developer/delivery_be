from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Same default page size as before (20), but now actually honors the
    `page_size` query param — every list endpoint's client (the Flutter
    app's `fetchProducts`/`fetchStocks`/etc.) already sends it expecting a
    bigger page, but plain `PageNumberPagination` silently ignores that
    param unless `page_size_query_param` is set, so every listing was
    capped at 20 regardless of what callers asked for."""

    page_size_query_param = "page_size"
    max_page_size = 200
