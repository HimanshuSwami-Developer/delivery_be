from rest_framework import status
from rest_framework.response import Response


class ReadAfterWriteMixin:
    """
    For viewsets whose `get_serializer_class()` returns a narrower write
    serializer for create/update (accepting plain FK ids, no nested/derived
    fields) than the one used for list/retrieve. Without this, `create`'s
    response body only has the write serializer's fields — missing derived
    data like `cat`/`discount_pct` (`ProductWriteSerializer`) or
    `zone_name`/`trips_today` (`DeliveryPartnerWriteSerializer`) that
    clients reasonably expect from any endpoint returning "the object".

    Set `read_serializer_class` on the viewset; `create`/`update` then
    re-serialize the saved instance with it before responding, while still
    validating the request body with the narrower write serializer.
    """

    read_serializer_class = None

    def _read_serializer(self, instance):
        cls = self.read_serializer_class or self.get_serializer_class()
        return cls(instance, context=self.get_serializer_context())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = self._read_serializer(serializer.instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = self._read_serializer(serializer.instance)
        return Response(read_serializer.data)
