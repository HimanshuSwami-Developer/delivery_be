import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    Sends OTP SMS via MSG91's Flow API.

    settings.SMS_BACKEND controls the implementation:
      - "console" : just logs/prints the OTP (local dev, no real SMS)
      - "msg91"   : sends via MSG91 (fill in MSG91_* settings)
    """

    @staticmethod
    def send_otp_sms(mobile_number: str, otp_code: str) -> bool:
        backend = getattr(settings, "SMS_BACKEND", "console")

        if backend == "console":
            message = f"Your OTP is {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes."
            logger.info("[SMS -> %s]: %s", mobile_number, message)
            print(f"[SMS -> {mobile_number}]: {message}")
            return True

        if backend == "msg91":
            return SMSService._send_via_msg91(mobile_number, otp_code)

        logger.error("Unknown SMS_BACKEND '%s'", backend)
        return False

    @staticmethod
    def _send_via_msg91(mobile_number: str, otp_code: str) -> bool:
        """
        MSG91 Flow API (https://control.msg91.com/api/v5/flow).

        Prerequisite: create a DLT-approved OTP template in MSG91
        (Campaigns -> Flow) with a variable, e.g.
        "Your OTP is ##OTP##. Valid for 5 minutes." -> note the Template ID.

        Our own OTP model still generates the code, tracks expiry, and
        counts attempts -- MSG91 is only used as the delivery pipe.

        Required settings: MSG91_AUTH_KEY, MSG91_TEMPLATE_ID
        Optional settings: MSG91_SENDER_ID, MSG91_OTP_VAR (default "OTP")
        """
        try:
            import requests
        except ImportError:
            logger.error("requests package not installed. Run: pip install requests")
            return False

        auth_key = getattr(settings, "MSG91_AUTH_KEY", "")
        template_id = getattr(settings, "MSG91_TEMPLATE_ID", "")
        if not auth_key or not template_id:
            logger.error("MSG91_AUTH_KEY / MSG91_TEMPLATE_ID not configured.")
            return False

        # MSG91 expects the number with country code and no leading '+' or spaces.
        clean_mobile = mobile_number.lstrip("+").replace(" ", "")
        otp_var = getattr(settings, "MSG91_OTP_VAR", "OTP")

        payload = {
            "template_id": template_id,
            "short_url": "0",
            "recipients": [
                {
                    "mobiles": clean_mobile,
                    otp_var: otp_code,
                }
            ],
        }

        sender_id = getattr(settings, "MSG91_SENDER_ID", "")
        if sender_id:
            payload["sender"] = sender_id

        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                "https://control.msg91.com/api/v5/flow",
                json=payload,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("MSG91 SMS request failed for %s", mobile_number)
            return False

        if response.status_code != 200:
            logger.error(
                "MSG91 SMS send failed for %s: HTTP %s - %s",
                mobile_number, response.status_code, response.text,
            )
            return False

        try:
            data = response.json()
        except ValueError:
            logger.error("MSG91 returned a non-JSON response for %s: %s", mobile_number, response.text)
            return False

        if data.get("type") != "success":
            logger.error("MSG91 SMS send failed for %s: %s", mobile_number, data)
            return False

        return True