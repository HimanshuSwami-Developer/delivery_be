from urllib.parse import quote

from rest_framework import serializers

from .models import SupportConfig, SupportFAQ, SupportTicket


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
        request = self.context.get("request")
        name = None
        if request is not None and request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            name = (profile.name if profile and profile.name else None) or request.user.name
        try:
            message = obj.whatsapp_message.format(name=name or "a customer")
        except (KeyError, IndexError):
            # Admin edited the template and dropped/broke the `{name}`
            # placeholder — fall back to the raw text rather than 500ing.
            message = obj.whatsapp_message
        text = quote(message)
        return f"https://wa.me/{obj.whatsapp_number}?text={text}"


class SupportFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportFAQ
        fields = ["id", "question", "answer", "order"]
        read_only_fields = ["id"]
