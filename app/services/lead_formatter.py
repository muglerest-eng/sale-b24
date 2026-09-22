"""Форматирование текста уведомления о лиде."""

from app.config import Settings


def _lead_contact_name(lead: dict[str, object]) -> str | None:
    """Собирает имя контакта из полей лида."""
    parts: list[str] = []
    for key in ("LAST_NAME", "NAME", "SECOND_NAME"):
        value = lead.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    if not parts:
        return None
    return " ".join(parts)


def lead_phone(lead: dict[str, object]) -> str | None:
    """Извлекает первый телефон из мультиполя PHONE."""
    phone_field = lead.get("PHONE")
    if not isinstance(phone_field, list):
        return None
    for item in phone_field:
        if not isinstance(item, dict):
            continue
        value = item.get("VALUE")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _custom_field(lead: dict[str, object], field_code: str) -> str | None:
    """Возвращает строковое значение пользовательского поля, если оно заполнено."""
    if not field_code:
        return None
    value = lead.get(field_code)
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [str(v).strip() for v in value if str(v).strip()]
        if parts:
            return ", ".join(parts)
    return str(value).strip() or None


def format_lead_notification(
    lead: dict[str, object],
    settings: Settings,
    portal_domain: str,
) -> str:
    """
    Собирает текст сообщения для MAX.

    Пустые поля не включаются.
    """
    lead_id_raw = lead.get("ID")
    lead_id = int(lead_id_raw) if lead_id_raw is not None else 0

    lines: list[str] = ["Новый лид с сайта"]

    title = lead.get("TITLE")
    if isinstance(title, str) and title.strip():
        lines.append(f"Название: {title.strip()}")

    contact_name = _lead_contact_name(lead)
    if contact_name:
        lines.append(f"Имя: {contact_name}")

    phone = lead_phone(lead)
    if phone:
        lines.append(f"Телефон: {phone}")

    city = _custom_field(lead, settings.bitrix_field_city.strip())
    if city:
        lines.append(f"Город: {city}")

    visa = _custom_field(lead, settings.bitrix_field_visa_questions.strip())
    if visa:
        lines.append(f"Вопросы по визе: {visa}")

    if lead_id and portal_domain.strip():
        lines.append(
            f"Карточка: {settings.bitrix_lead_card_url(portal_domain, lead_id)}",
        )

    return "\n".join(lines)
