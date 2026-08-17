import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None
_client_init_failed = False


def _get_client():
    """
    Lazily builds the razorpay.Client exactly once, from
    settings.RAZORPAY_KEY_ID/SECRET. Returns None (never raises) when those
    aren't configured, matching push_service.py's "degrade to a no-op
    instead of crashing the request" convention — checkout still works via
    Cash on Delivery without Razorpay keys.
    """
    global _client, _client_init_failed
    if _client is not None or _client_init_failed:
        return _client

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        _client_init_failed = True
        return None

    import razorpay

    _client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return _client


def create_order(amount_rupees, receipt):
    """Creates a Razorpay Order for `amount_rupees` (converted to paise —
    Razorpay's amounts are always the smallest currency unit) and returns
    its dict, or None if Razorpay isn't configured or the API call fails."""
    client = _get_client()
    if client is None:
        return None
    try:
        return client.order.create(
            {
                "amount": amount_rupees * 100,
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1,
            }
        )
    except Exception:
        logger.exception("Razorpay order creation failed for receipt=%s", receipt)
        return None


def verify_signature(params):
    """Verifies a completed checkout's order_id/payment_id/signature triple
    against Razorpay. `params` is the exact
    {razorpay_order_id, razorpay_payment_id, razorpay_signature} dict their
    SDK expects. Returns False (never raises) on any failure, including
    Razorpay not being configured."""
    client = _get_client()
    if client is None:
        return False
    import razorpay

    try:
        client.utility.verify_payment_signature(params)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
