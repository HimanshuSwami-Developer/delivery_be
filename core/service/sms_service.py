import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    Sends OTP SMS via MSG91's OTP Widget API.

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
        MSG91 OTP Widget API (https://control.msg91.com/api/v5/otp) — NOT
        the Flow/Campaigns API (different product, different endpoint and
        request shape).

        Prerequisite: create an OTP Widget in MSG91 (OTP -> Widget), which
        auto-provisions a DLT-approved OTP template — note the Widget's
        Template ID (MSG91_TEMPLATE_ID).

        Our own OTP model still generates the code, tracks expiry, and
        counts attempts — passing `otp=otp_code` here makes MSG91 send
        *our* code instead of generating its own, so MSG91 stays purely the
        delivery pipe.

        Required settings: MSG91_AUTH_KEY, MSG91_TEMPLATE_ID
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

        params = {
            "template_id": template_id,
            "mobile": clean_mobile,
            "authkey": auth_key,
            "otp": otp_code,
        }

        try:
            response = requests.post(
                "https://control.msg91.com/api/v5/otp",
                params=params,
                headers={"accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("MSG91 OTP request failed for %s", mobile_number)
            return False

        if response.status_code != 200:
            logger.error(
                "MSG91 OTP send failed for %s: HTTP %s - %s",
                mobile_number, response.status_code, response.text,
            )
            return False

        try:
            data = response.json()
        except ValueError:
            logger.error("MSG91 returned a non-JSON response for %s: %s", mobile_number, response.text)
            return False

        if data.get("type") != "success":
            logger.error("MSG91 OTP send failed for %s: %s", mobile_number, data)
            return False

        return True
