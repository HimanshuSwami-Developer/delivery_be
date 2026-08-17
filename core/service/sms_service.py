import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    Sends the OTP over WhatsApp.

    settings.SMS_BACKEND controls the implementation:
      - "console"  : just logs/prints the OTP (local dev, no real send)
      - "whatsapp" : sends via MSG91's WhatsApp Business API
    """

    @staticmethod
    def send_otp_sms(mobile_number: str, otp_code: str) -> bool:
        backend = getattr(settings, "SMS_BACKEND", "console")

        if backend == "console":
            message = f"Your OTP is {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes."
            logger.info("[SMS -> %s]: %s", mobile_number, message)
            print(f"[SMS -> {mobile_number}]: {message}")
            return True

        if backend == "whatsapp":
            return SMSService._send_via_msg91_whatsapp(mobile_number, otp_code)

        logger.error("Unknown SMS_BACKEND '%s'", backend)
        return False

    @staticmethod
    def _send_via_msg91_whatsapp(mobile_number: str, otp_code: str) -> bool:
        """
        MSG91's WhatsApp Business API — no TRAI/DLT registration needed.

        Prerequisites (MSG91 dashboard -> WhatsApp):
          1. Connect + verify a WhatsApp Business number via Facebook
             Business Manager -> its number is MSG91_WHATSAPP_NUMBER.
          2. Create an "Authentication" category template containing one
             body variable for the code (Meta's template review for this
             category is normally quick) -> its name is
             MSG91_WHATSAPP_TEMPLATE.

        Our own OTP model still generates the code, tracks expiry, and
        counts attempts -- this call only delivers it.

        Required settings: MSG91_AUTH_KEY, MSG91_WHATSAPP_NUMBER,
        MSG91_WHATSAPP_TEMPLATE
        """
        try:
            import requests
        except ImportError:
            logger.error("requests package not installed. Run: pip install requests")
            return False

        auth_key = getattr(settings, "MSG91_AUTH_KEY", "")
        integrated_number = getattr(settings, "MSG91_WHATSAPP_NUMBER", "")
        template_name = getattr(settings, "MSG91_WHATSAPP_TEMPLATE", "")
        if not auth_key or not integrated_number or not template_name:
            logger.error(
                "MSG91_AUTH_KEY / MSG91_WHATSAPP_NUMBER / MSG91_WHATSAPP_TEMPLATE not configured."
            )
            return False

        # MSG91 expects the number with country code and no leading '+' or spaces.
        clean_mobile = mobile_number.lstrip("+").replace(" ", "")

        payload = {
            "integrated_number": integrated_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en", "policy": "deterministic"},
                    "to_and_components": [
                        {
                            "to": [clean_mobile],
                            "components": {"body_1": {"type": "text", "value": otp_code}},
                        }
                    ],
                },
            },
        }

        try:
            response = requests.post(
                "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/",
                json=payload,
                headers={"authkey": auth_key, "Content-Type": "application/json"},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("MSG91 WhatsApp request failed for %s", mobile_number)
            return False

        if response.status_code != 200:
            logger.error(
                "MSG91 WhatsApp send failed for %s: HTTP %s - %s",
                mobile_number, response.status_code, response.text,
            )
            return False

        try:
            data = response.json()
        except ValueError:
            logger.error("MSG91 returned a non-JSON response for %s: %s", mobile_number, response.text)
            return False

        if data.get("status") != "success" and data.get("type") != "success":
            logger.error("MSG91 WhatsApp send failed for %s: %s", mobile_number, data)
            return False

        return True
