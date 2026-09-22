"""Проверка подлинности событий Битрикс24."""

import logging
from urllib.parse import urlparse

from app.config import Settings
from app.models import BitrixWebhookAuth

logger = logging.getLogger(__name__)


def is_outgoing_webhook_event(auth: BitrixWebhookAuth) -> bool:
    """Событие исходящего webhook: есть application_token, нет access_token."""
    return bool(auth.application_token.strip()) and not auth.access_token.strip()


def verify_bitrix_auth(auth: BitrixWebhookAuth, settings: Settings) -> bool:
    """
    Проверяет блок auth из события Битрикс24.

    Поддерживает:
    - локальное приложение (access_token + client_endpoint + domain);
    - исходящий webhook (application_token + BITRIX_INCOMING_WEBHOOK_URL).
    """
    app_token_cfg = settings.bitrix24_application_token.strip()
    event_token = auth.application_token.strip()

    if event_token and app_token_cfg and event_token == app_token_cfg:
        return True

    if auth.access_token.strip() and auth.client_endpoint.strip() and auth.domain.strip():
        return True

    if _accept_outgoing_by_portal_domain(auth, settings):
        if not event_token and app_token_cfg:
            logger.warning(
                "application_token не пришёл в событии Битрикс — принято по domain=%s",
                auth.domain,
            )
        elif event_token and app_token_cfg and event_token != app_token_cfg:
            logger.warning(
                "application_token в событии не совпал с env — принято по domain=%s",
                auth.domain,
            )
        else:
            logger.info("Исходящий webhook Битрикс24 (REST через входящий webhook)")
        return True

    if app_token_cfg:
        if not event_token:
            logger.warning(
                "BITRIX24_APPLICATION_TOKEN задан, но application_token не пришёл в событии "
                "(domain=%s, member_id=%s)",
                auth.domain or "-",
                bool(auth.member_id.strip()),
            )
        else:
            logger.warning(
                "BITRIX24_APPLICATION_TOKEN не совпал с токеном события (domain=%s)",
                auth.domain or "-",
            )
        return False

    logger.warning(
        "Auth отклонён: access_token=%s domain=%s application_token=%s incoming_webhook=%s",
        bool(auth.access_token.strip()),
        auth.domain or "-",
        bool(event_token),
        bool(settings.bitrix_incoming_webhook_url.strip()),
    )
    return False


def _accept_outgoing_by_portal_domain(auth: BitrixWebhookAuth, settings: Settings) -> bool:
    """Принимает исходящий webhook по domain портала без OAuth."""
    if auth.access_token.strip():
        return False
    if not auth.domain.strip():
        return False
    if not settings.bitrix_incoming_webhook_url.strip():
        return False
    expected = _portal_domain_from_incoming_webhook(settings)
    return _domains_match(auth.domain, expected)


def _portal_domain_from_incoming_webhook(settings: Settings) -> str:
    """Домен портала из URL входящего webhook."""
    parsed = urlparse(settings.bitrix_incoming_webhook_url.strip())
    return parsed.netloc.lower()


def _domains_match(event_domain: str, expected: str) -> bool:
    """Сравнивает домены портала Битрикс24."""
    left = event_domain.strip().lower().rstrip("/")
    right = expected.strip().lower().rstrip("/")
    if left.startswith("http://") or left.startswith("https://"):
        left = urlparse(left).netloc.lower()
    return bool(left and right and left == right)
