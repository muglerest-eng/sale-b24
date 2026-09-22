"""Отправка ответов пользователю MAX из события update."""

from app.models import MaxUpdate
from app.services.max_client import MaxClient


def resolve_reply_target(update: MaxUpdate) -> tuple[int | None, int | None]:
    """
    Определяет chat_id или user_id для ответа.

    В личном диалоге MAX часто нет recipient.chat_id — используем user_id.
    """
    if update.chat_id is not None:
        return update.chat_id, None

    if update.message:
        recipient = update.message.recipient
        if recipient and recipient.chat_id is not None:
            return recipient.chat_id, None

        sender = update.message.sender
        if sender and sender.user_id is not None:
            return None, sender.user_id

    if update.user and update.user.user_id is not None:
        return None, update.user.user_id

    return None, None


async def send_reply(
    max_client: MaxClient,
    update: MaxUpdate,
    text: str,
) -> bool:
    """
    Отправляет текстовый ответ пользователю.

    Returns:
        True, если сообщение отправлено.
    """
    chat_id, user_id = resolve_reply_target(update)
    if chat_id is not None:
        await max_client.send_text_to_chat(chat_id, text)
        return True
    if user_id is not None:
        await max_client.send_text_to_user(user_id, text)
        return True
    return False
