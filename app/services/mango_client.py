"""Интеграция обратного звонка Mango Office."""

import logging

import httpx

logger = logging.getLogger(__name__)


async def request_mango_callback(phone: str, url_template: str) -> None:
    """
    Инициирует обратный звонок через Mango Office.

    Args:
        phone: Номер телефона из лида.
        url_template: Шаблон URL с плейсхолдером {phone}.
    """
    if not url_template.strip() or not phone.strip():
        return

    url = url_template.replace("{phone}", phone.strip())
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        logger.info("Mango callback запрошен для %s", phone)
    except Exception:
        logger.exception("Ошибка Mango callback для %s", phone)
