from rest_framework import serializers

from .models import SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    user_mobile = serializers.CharField(source="user.mobile_number", read_only=True)

    class Meta:
        model = SupportTicket
        fields = ["id", "user", "user_mobile", "order", "subject", "message", "status", "admin_reply", "created_at"]
        read_only_fields = ["id", "user", "user_mobile", "status", "admin_reply", "created_at"]


class SupportTicketAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["status", "admin_reply"]
