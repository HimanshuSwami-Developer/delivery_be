from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from core.mixins import ReadAfterWriteMixin

from .models import SupportTicket
from .serializers import SupportTicketAdminUpdateSerializer, SupportTicketSerializer


@extend_schema(tags=["Support"])
class SupportTicketViewSet(ReadAfterWriteMixin, viewsets.ModelViewSet):
    """Customers see/create only their own tickets (`support_view`);
    admins see every ticket and can set `status`/`admin_reply`. An admin's
    PATCH accepts the narrow `SupportTicketAdminUpdateSerializer` shape but
    responds with the full ticket (see `ReadAfterWriteMixin`)."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    read_serializer_class = SupportTicketSerializer

    def get_queryset(self):
        qs = SupportTicket.objects.select_related("user", "order")
        user = self.request.user
        if user.role == User.Role.ADMIN or user.is_superuser:
            return qs
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action in ("update", "partial_update") and self.request.user.role == User.Role.ADMIN:
            return SupportTicketAdminUpdateSerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
