from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from core.mixins import ReadAfterWriteMixin
from core.permissions import IsAdminRole

from .models import DeliveryPartner
from .serializers import DeliveryPartnerSerializer, DeliveryPartnerWriteSerializer


@extend_schema(tags=["Delivery Partners"])
class DeliveryPartnerViewSet(ReadAfterWriteMixin, viewsets.ModelViewSet):
    """Admin-only: the "Delivery partners" screen's roster table, and the
    source of the assignable-partner list shown in the order-detail assign
    modal (`?status=available`). `create`/`update` accept
    `DeliveryPartnerWriteSerializer`'s plain-id shape but respond with the
    full `DeliveryPartnerSerializer` (see `ReadAfterWriteMixin`), so the
    response always has `zone_name`/`trips_today`/etc., not just what was
    posted."""

    queryset = DeliveryPartner.objects.select_related("user", "zone")
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["zone", "status", "vehicle"]
    read_serializer_class = DeliveryPartnerSerializer

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DeliveryPartnerWriteSerializer
        return DeliveryPartnerSerializer
