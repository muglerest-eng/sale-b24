"""Модели данных для вебхуков и CRM."""

from pydantic import BaseModel, Field


class BitrixWebhookAuth(BaseModel):
    """Блок auth в событии локального приложения Битрикс24."""

    access_token: str = Field(default="")
    client_endpoint: str = Field(default="")
    domain: str = Field(default="")
    application_token: str = Field(default="")
    member_id: str = Field(default="")
    server_endpoint: str = Field(default="")
    refresh_token: str = Field(default="")


class BitrixWebhookPayload(BaseModel):
    """Тело события CRM от Битрикс24."""

    event: str
    data: dict[str, object] = Field(default_factory=dict)
    auth: BitrixWebhookAuth = Field(default_factory=BitrixWebhookAuth)


class BitrixSession(BaseModel):
    """OAuth-сессия из события для REST-запросов."""

    access_token: str
    client_endpoint: str
    domain: str
    server_endpoint: str = ""
    refresh_token: str = ""


class MaxUser(BaseModel):
    """Пользователь MAX в событии update."""

    user_id: int | None = None
    name: str | None = None
    first_name: str | None = None


class MaxMessageBody(BaseModel):
    """Текст сообщения MAX."""

    text: str | None = None


class MaxRecipient(BaseModel):
    """Получатель сообщения MAX."""

    chat_id: int | None = None
    chat_type: str | None = None


class MaxMessage(BaseModel):
    """Сообщение в событии message_created."""

    sender: MaxUser | None = None
    recipient: MaxRecipient | None = None
    body: MaxMessageBody | None = None


class MaxUpdate(BaseModel):
    """Обновление от MAX Bot API."""

    update_type: str
    chat_id: int | None = None
    timestamp: int | None = None
    payload: str | None = None
    user: MaxUser | None = None
    message: MaxMessage | None = None
