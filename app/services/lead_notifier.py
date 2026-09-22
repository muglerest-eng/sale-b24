"""Доставка уведомления о новом лиде подписчикам MAX."""

import logging

from app.config import Settings
from app.models import BitrixSession
from app.services.bitrix_client import BitrixClient
from app.services.lead_formatter import format_lead_notification, lead_phone
from app.services.mango_client import request_mango_callback
from app.services.max_client import MaxClient
from app.storage import JsonIdStore, list_all_subscriber_ids

logger = logging.getLogger(__name__)


def _portal_domain(session: BitrixSession, bitrix: BitrixClient) -> str:
    """Домен портала для ссылки на карточку лида."""
    if session.domain.strip():
        return session.domain.strip()
    return bitrix.portal_domain_from_incoming_webhook()


async def notify_subscribers_about_lead(
    lead_id: int,
    session: BitrixSession,
    settings: Settings,
    bitrix: BitrixClient,
    max_client: MaxClient,
    subscribers: JsonIdStore,
    processed: JsonIdStore,
) -> None:
    """
    Загружает лид, форматирует текст и рассылает подписчикам.

    При наличии MANGO_CALL_URL_TEMPLATE инициирует обратный звонок.
    """
    chat_ids = list_all_subscriber_ids(
        subscribers,
        settings.parsed_default_subscriber_ids(),
    )
    logger.info("Обработка лида %s, подписчиков: %s", lead_id, len(chat_ids))

    if processed.contains(lead_id):
        logger.info("Лид %s уже обработан, пропуск", lead_id)
        return
    if not chat_ids:
        logger.warning("Нет подписчиков MAX — лид %s не отправлен", lead_id)
        return

    lead = await bitrix.get_lead(session, lead_id)
    domain = _portal_domain(session, bitrix)
    text = format_lead_notification(lead, settings, domain)
    logger.info("Лид %s загружен, отправка в MAX (%s получателей)", lead_id, len(chat_ids))

    phone = lead_phone(lead)
    if phone and settings.mango_call_url_template.strip():
        await request_mango_callback(phone, settings.mango_call_url_template)

    failed: list[int] = []
    for recipient_id in chat_ids:
        try:
            await max_client.send_text_to_chat(recipient_id, text)
        except Exception:
            try:
                await max_client.send_text_to_user(recipient_id, text)
            except Exception:
                logger.exception(
                    "Не удалось отправить лид %s получателю %s",
                    lead_id,
                    recipient_id,
                )
                failed.append(recipient_id)

    if not failed:
        processed.add(lead_id)
        logger.info("Лид %s успешно отправлен в MAX", lead_id)
    else:
        logger.error(
            "Лид %s: ошибки отправки в %s чат(ов), повтор возможен",
            lead_id,
            len(failed),
        )
