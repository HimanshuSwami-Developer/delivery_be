import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None
_client_init_failed = False


def _get_client():
    """
    Lazily builds the groq.Client exactly once, from settings.GROQ_API_KEY.
    Returns None (never raises) when that isn't configured — matches
    razorpay_service.py's "degrade to a no-op instead of crashing the
    request" convention: a QR order still places fine either way, it just
    stays payment_status='pending' for an admin to verify by hand instead
    of getting auto-approved.
    """
    global _client, _client_init_failed
    if _client is not None or _client_init_failed:
        return _client

    if not settings.GROQ_API_KEY:
        _client_init_failed = True
        return None

    import groq

    _client = groq.Client(api_key=settings.GROQ_API_KEY)
    return _client


_EXTRACT_PROMPT = (
    "This image is a screenshot of a completed UPI payment, from an app like "
    "Google Pay, PhonePe, Paytm, or a bank app. Read it carefully and respond "
    "with ONLY a JSON object with exactly these three keys:\n"
    '"success": true if the screenshot clearly shows a completed/successful payment '
    "(not pending, not failed), false otherwise.\n"
    '"transaction_id": the UPI transaction ID / UTR number / reference number shown '
    "on the screenshot, as a plain string, or null if none is visible.\n"
    '"amount": the paid amount as a plain number in rupees (e.g. 199 or 199.50, no '
    "currency symbol, no commas), or null if not visible.\n"
    "Respond with the JSON object only — no other text, no markdown."
)


def extract_payment_details(image_url):
    """
    Reads a UPI payment screenshot at `image_url` (a public Cloudinary URL)
    via Groq's vision model and returns
    `{"success": bool, "transaction_id": str | None, "amount": float | None}`.

    Returns None — never raises — if Groq isn't configured, the request
    fails, or the response can't be parsed as expected. The caller treats
    that identically to "couldn't verify": the order's payment_status is
    left untouched (pending) rather than auto-approved on a guess.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _EXTRACT_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        data = json.loads(response.choices[0].message.content)
        amount = data.get("amount")
        transaction_id = (data.get("transaction_id") or "").strip() or None
        return {
            "success": bool(data.get("success")),
            "transaction_id": transaction_id,
            "amount": float(amount) if amount is not None else None,
        }
    except Exception:
        logger.exception("Groq payment-screenshot extraction failed for %s", image_url)
        return None
