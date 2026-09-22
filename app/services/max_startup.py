"""Регистрация MAX webhook при старте приложения."""

import logging

import httpx

from app.config import Settings
from app.services.max_client import MaxClient

logger = logging.getLogger(__name__)

MAX_UPDATE_TYPES = ["bot_started", "message_created", "bot_stopped"]


def public_base_url(settings: Settings) -> str:
    """Базовый публичный URL приложения."""
    if settings.public_app_url.strip():
        return settings.public_app_url.strip().rstrip("/")

    parsed = settings.bitrix24_handler_url.strip()
    if parsed.startswith("http://") or parsed.startswith("https://"):
        from urllib.parse import urlparse

        parts = urlparse(parsed)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"

    raise ValueError(
        "Не удалось определить публичный URL. "
        "Задайте PUBLIC_APP_URL или корректный BITRIX24_HANDLER_URL.",
    )


def max_webhook_url(settings: Settings, base_url: str) -> str:
    """Полный URL webhook MAX."""
    prefix = settings.webhook_path_secret.strip().strip("/")
    path = f"/{prefix}/max/webhook" if prefix else "/max/webhook"
    return f"{base_url.rstrip('/')}{path}"


async def ensure_max_webhook(settings: Settings) -> dict[str, object]:
    """
    Регистрирует webhook MAX.

    Returns:
        Статус операции для /health/max.
    """
    if not settings.max_auto_register_webhook:
        return {"registered": False, "reason": "MAX_AUTO_REGISTER_WEBHOOK=false"}

    base_url = public_base_url(settings)
    webhook_url = max_webhook_url(settings, base_url)
    client = MaxClient(settings)

    try:
        me = await client.get_me()
        bot_label = me.get("username") or me.get("name") or "bot"
        result = await client.register_webhook(
            url=webhook_url,
            secret=settings.max_webhook_secret,
            update_types=MAX_UPDATE_TYPES,
        )
        logger.info(
            "MAX webhook зарегистрирован для %s: %s → %s",
            bot_label,
            webhook_url,
            result,
        )
        return {
            "registered": True,
            "bot": bot_label,
            "webhook_url": webhook_url,
            "result": result,
        }
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        logger.error(
            "MAX API HTTP %s при регистрации webhook %s: %s",
            exc.response.status_code,
            webhook_url,
            body,
        )
        return {
            "registered": False,
            "webhook_url": webhook_url,
            "detail": f"HTTP {exc.response.status_code}: {body}",
        }
    except Exception as exc:
        logger.exception(
            "Не удалось зарегистрировать MAX webhook на %s",
            webhook_url,
        )
        return {
            "registered": False,
            "webhook_url": webhook_url,
            "detail": str(exc),
        }
