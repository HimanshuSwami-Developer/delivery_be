from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.models import User
from core.mixins import ReadAfterWriteMixin

from .models import SupportConfig, SupportTicket
from .serializers import SupportConfigSerializer, SupportTicketAdminUpdateSerializer, SupportTicketSerializer


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


@extend_schema(tags=["Support"])
class SupportConfigView(generics.RetrieveAPIView):
    """Public read of the admin-set call/WhatsApp/chat contact info (Django
    admin is where it's edited — see `SupportConfigAdmin`). No write
    endpoint on purpose: this is app-config, not user data."""

    serializer_class = SupportConfigSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return SupportConfig.load()
