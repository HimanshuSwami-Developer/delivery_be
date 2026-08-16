import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_app = None
_app_init_failed = False


def _get_app():
    """
    Lazily initializes the firebase-admin App exactly once, from
    settings.FIREBASE_CREDENTIALS_PATH. Returns None (never raises) when
    that isn't configured or fails to load, so push sends degrade to a
    logged no-op instead of crashing whatever request triggered them —
    matches SMSService's "console" backend fallback.
    """
    global _app, _app_init_failed
    if _app is not None or _app_init_failed:
        return _app

    if not settings.FIREBASE_CREDENTIALS_PATH:
        _app_init_failed = True
        return None

    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    try:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _app = firebase_admin.initialize_app(cred)
    except (FileNotFoundError, ValueError):
        logger.exception("Failed to load Firebase credentials from %s", settings.FIREBASE_CREDENTIALS_PATH)
        _app_init_failed = True
        return None

    return _app


class PushService:
    """Sends FCM push notifications to a batch of device tokens."""

    @staticmethod
    def send_to_tokens(tokens, title, body, data=None):
        """
        Sends one push per token in a single batched call. Returns
        `(success_count, invalid_tokens)` — `invalid_tokens` are tokens FCM
        reports as unregistered (uninstalled app / expired token), for the
        caller to prune from DeviceToken so future sends don't keep hitting
        them.
        """
        tokens = list(dict.fromkeys(tokens))  # de-dupe, keep order
        if not tokens:
            return 0, []

        app = _get_app()
        if app is None:
            logger.info("[push -> %d device(s), no FIREBASE_CREDENTIALS_PATH configured] %s: %s", len(tokens), title, body)
            return 0, []

        from firebase_admin import messaging

        str_data = {str(k): str(v) for k, v in (data or {}).items()}
        messages = [
            messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=str_data,
            )
            for token in tokens
        ]

        try:
            response = messaging.send_each(messages, app=app)
        except Exception:
            logger.exception("FCM batch send failed for %d token(s)", len(tokens))
            return 0, []

        invalid_tokens = []
        for token, result in zip(tokens, response.responses):
            if result.success:
                continue
            if isinstance(result.exception, messaging.UnregisteredError):
                invalid_tokens.append(token)
            else:
                logger.warning("FCM send failed for token %s...: %s", token[:12], result.exception)

        return response.success_count, invalid_tokens
