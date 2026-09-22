"""Обработка подписки пользователей MAX по секретному коду."""

import logging
import re

from app.config import Settings
from app.models import MaxUpdate
from app.services.max_client import MaxClient
from app.services.max_reply import resolve_reply_target, send_reply
from app.storage import JsonIdStore

logger = logging.getLogger(__name__)

_START_WITH_CODE = re.compile(
    r"^/start(?:@\w+)?\s+(\S+)$",
    re.IGNORECASE,
)
_START_PLAIN = re.compile(r"^/start(?:@\w+)?$", re.IGNORECASE)
_PING = re.compile(r"^(?:/ping|ping|привет|hello|hi)$", re.IGNORECASE)


def _subscribe_prompt(settings: Settings) -> str:
    """Текст-подсказка для подписки."""
    return (
        "Бот на связи.\n"
        f"Для уведомлений о новых лидах отправьте:\n"
        f"/start {settings.max_subscribe_code}"
    )


def extract_subscribe_code_from_update(update: MaxUpdate) -> str | None:
    """
    Извлекает код подписки из deeplink payload или текста сообщения.

    Поддерживает: ?start=CODE, «/start CODE», «start CODE», сообщение «CODE».
    """
    if update.update_type == "bot_started":
        if update.payload and update.payload.strip():
            return update.payload.strip()
        return None

    if update.update_type != "message_created" or not update.message:
        return None

    text = (update.message.body.text if update.message.body else None) or ""
    normalized = text.strip()
    if not normalized:
        return None

    match = _START_WITH_CODE.match(normalized)
    if match:
        return match.group(1)

    if _START_PLAIN.match(normalized):
        return None

    lower = normalized.lower()
    if lower.startswith("start "):
        parts = normalized.split(maxsplit=1)
        if len(parts) == 2:
            return parts[1].strip()

    if " " not in normalized and "\n" not in normalized:
        return normalized

    return None


def _message_text(update: MaxUpdate) -> str:
    """Текст входящего сообщения."""
    if not update.message or not update.message.body:
        return ""
    return (update.message.body.text or "").strip()


async def handle_max_update(
    update: MaxUpdate,
    settings: Settings,
    subscribers: JsonIdStore,
    max_client: MaxClient,
) -> None:
    """Обрабатывает события MAX: подписка, отписка, ответы пользователю."""
    chat_id, user_id = resolve_reply_target(update)
    storage_id = chat_id if chat_id is not None else user_id

    logger.info(
        "MAX update: type=%s chat_id=%s user_id=%s",
        update.update_type,
        chat_id,
        user_id,
    )

    if update.update_type == "bot_stopped":
        if storage_id is not None:
            subscribers.remove(storage_id)
        return

    if update.update_type not in {"bot_started", "message_created"}:
        return

    if storage_id is None:
        logger.warning("MAX update без chat_id/user_id: %s", update.update_type)
        return

    code = extract_subscribe_code_from_update(update)

    if update.update_type == "message_created" and code is None:
        text = _message_text(update)
        if _START_PLAIN.match(text) or _PING.match(text):
            await send_reply(max_client, update, _subscribe_prompt(settings))
            return
        if text:
            await send_reply(
                max_client,
                update,
                "Бот работает. " + _subscribe_prompt(settings).split("\n", 1)[1],
            )
        return

    if update.update_type == "bot_started" and code is None:
        await send_reply(max_client, update, _subscribe_prompt(settings))
        return

    if code is None:
        return

    if code != settings.max_subscribe_code:
        await send_reply(max_client, update, "Неверный код подписки.")
        return

    is_new = subscribers.add(storage_id)
    logger.info("Подписка MAX: chat/user_id=%s, новый=%s", storage_id, is_new)
    if is_new:
        await send_reply(
            max_client,
            update,
            "Вы подписаны на уведомления о новых лидах.",
        )
    else:
        await send_reply(
            max_client,
            update,
            "Вы уже подписаны. Бот на связи — ждём новые заявки.",
        )
