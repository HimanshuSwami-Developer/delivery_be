import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    Sends the OTP (and order-invoice notifications) as plain SMS.

    settings.SMS_BACKEND controls the implementation:
      - "console"  : just logs/prints the message (local dev, no real send)
      - "fast2sms" : sends via Fast2SMS's Quick SMS route
    """

    @staticmethod
    def send_otp_sms(mobile_number: str, otp_code: str) -> bool:
        backend = getattr(settings, "SMS_BACKEND", "console")
        message = f"Your OTP is {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes."

        if backend == "console":
            logger.info("[SMS -> %s]: %s", mobile_number, message)
            print(f"[SMS -> {mobile_number}]: {message}")
            return True

        if backend == "fast2sms":
            return SMSService._send_via_fast2sms(mobile_number, message)

        logger.error("Unknown SMS_BACKEND '%s'", backend)
        return False

    @staticmethod
    def send_order_invoice_sms(invoice_text: str) -> bool:
        """
        Notifies the business's own mobile (settings.ORDER_NOTIFY_MOBILE_NUMBER)
        with a freshly-placed order's full invoice, so every order (QR or
        COD) gets flagged immediately regardless of payment_status. Never
        raises; a misconfigured/unreachable send just gets logged.
        """
        backend = getattr(settings, "SMS_BACKEND", "console")
        recipient = getattr(settings, "ORDER_NOTIFY_MOBILE_NUMBER", "")
        if not recipient:
            logger.info("[Order invoice SMS] ORDER_NOTIFY_MOBILE_NUMBER not configured, skipping")
            return False

        if backend == "console":
            logger.info("[Order invoice SMS -> %s]:\n%s", recipient, invoice_text)
            print(f"[Order invoice SMS -> {recipient}]:\n{invoice_text}")
            return True

        if backend == "fast2sms":
            return SMSService._send_via_fast2sms(recipient, invoice_text)

        logger.error("Unknown SMS_BACKEND '%s'", backend)
        return False

    @staticmethod
    def _send_via_fast2sms(mobile_number: str, message: str) -> bool:
        """
        Fast2SMS's Quick SMS route ("q") — plain SMS, no DLT template
        registration needed for this route.

        Prerequisites (fast2sms.com dashboard -> Dev API -> API Keys):
          1. Sign up / log in, add balance (Quick SMS is a paid per-message
             route, billed per SMS -- there's no free tier for it).
          2. Copy your API key -> FAST2SMS_API_KEY.

        Fast2SMS expects Indian 10-digit numbers with no country code and
        no '+', e.g. "9718751020" not "+919718751020".

        Required settings: FAST2SMS_API_KEY
        """
        try:
            import requests
        except ImportError:
            logger.error("requests package not installed. Run: pip install requests")
            return False

        api_key = getattr(settings, "FAST2SMS_API_KEY", "")
        if not api_key:
            logger.error("FAST2SMS_API_KEY not configured.")
            return False

        # Strip any '+91'/'91' country-code prefix Fast2SMS doesn't want.
        clean_mobile = mobile_number.lstrip("+").replace(" ", "")
        if clean_mobile.startswith("91") and len(clean_mobile) == 12:
            clean_mobile = clean_mobile[2:]

        try:
            response = requests.get(
                "https://www.fast2sms.com/dev/bulkV2",
                params={"message": message, "route": "q", "numbers": clean_mobile},
                headers={"Authorization": api_key},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("Fast2SMS request failed for %s", mobile_number)
            return False

        if response.status_code != 200:
            logger.error(
                "Fast2SMS send failed for %s: HTTP %s - %s",
                mobile_number, response.status_code, response.text,
            )
            return False

        try:
            data = response.json()
        except ValueError:
            logger.error("Fast2SMS returned a non-JSON response for %s: %s", mobile_number, response.text)
            return False

        if not data.get("return"):
            logger.error("Fast2SMS send failed for %s: %s", mobile_number, data)
            return False

        return True
