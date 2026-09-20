from urllib.parse import quote

from rest_framework import serializers

from .models import SupportConfig, SupportTicket


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


class SupportConfigSerializer(serializers.ModelSerializer):
    whatsapp_link = serializers.SerializerMethodField()

    class Meta:
        model = SupportConfig
        fields = ["phone_number", "whatsapp_number", "whatsapp_link", "reply_time_label"]

    def get_whatsapp_link(self, obj) -> str:
        if not obj.whatsapp_number:
            return ""
        text = quote(obj.whatsapp_message)
        return f"https://wa.me/{obj.whatsapp_number}?text={text}"
