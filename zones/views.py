from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from core.permissions import IsAdminRoleOrReadOnly

from .models import Zone
from .serializers import ZoneSerializer


@extend_schema(tags=["Zones & Stores"])
class ZoneViewSet(viewsets.ModelViewSet):
    """Public read (customer app's zone picker); admin-only write ("Zones &
    stores" screen, including the open/closed toggle via PATCH)."""

    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [IsAdminRoleOrReadOnly]
