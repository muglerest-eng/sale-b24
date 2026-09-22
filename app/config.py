"""Конфигурация приложения из переменных окружения."""

from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Параметры интеграции Битрикс24 (локальное приложение) и MAX."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    bitrix24_client_id: str = Field(validation_alias="BITRIX24_CLIENT_ID")
    bitrix24_client_secret: str = Field(validation_alias="BITRIX24_CLIENT_SECRET")
    bitrix24_handler_url: str = Field(validation_alias="BITRIX24_HANDLER_URL")
    bitrix24_application_token: str = Field(
        default="",
        validation_alias="BITRIX24_APPLICATION_TOKEN",
    )
    bitrix_incoming_webhook_url: str = Field(
        default="",
        validation_alias="BITRIX_INCOMING_WEBHOOK_URL",
    )

    mango_call_url_template: str = Field(
        default="",
        validation_alias="MANGO_CALL_URL_TEMPLATE",
    )

    bitrix_field_city: str = Field(default="", validation_alias="BITRIX_FIELD_CITY")
    bitrix_field_visa_questions: str = Field(
        default="",
        validation_alias="BITRIX_FIELD_VISA_QUESTIONS",
    )

    max_api_base_url: str = Field(
        default="https://platform-api2.max.ru",
        validation_alias="MAX_API_BASE_URL",
    )
    max_bot_token: str = Field(validation_alias="MAX_BOT_TOKEN")
    max_webhook_secret: str = Field(validation_alias="MAX_WEBHOOK_SECRET")
    max_subscribe_code: str = Field(validation_alias="MAX_SUBSCRIBE_CODE")
    max_default_subscriber_ids: str = Field(
        default="",
        validation_alias="MAX_DEFAULT_SUBSCRIBER_IDS",
    )

    data_dir: str = Field(default="./data", validation_alias="DATA_DIR")
    webhook_path_secret: str = Field(default="", validation_alias="WEBHOOK_PATH_SECRET")
    public_app_url: str = Field(default="", validation_alias="PUBLIC_APP_URL")
    max_auto_register_webhook: bool = Field(
        default=True,
        validation_alias="MAX_AUTO_REGISTER_WEBHOOK",
    )
    http_ssl_verify: bool = Field(default=False, validation_alias="HTTP_SSL_VERIFY")
    http_ca_bundle: str = Field(default="", validation_alias="HTTP_CA_BUNDLE")

    def bitrix_webhook_path(self) -> str:
        """Путь обработчика из BITRIX24_HANDLER_URL."""
        parsed = urlparse(self.bitrix24_handler_url.strip())
        path = parsed.path.strip() or "/webhook/bitrix24"
        if not path.startswith("/"):
            path = f"/{path}"
        return path.rstrip("/") or "/webhook/bitrix24"

    def parsed_default_subscriber_ids(self) -> list[int]:
        """Chat ID из MAX_DEFAULT_SUBSCRIBER_IDS (через запятую), не сбрасываются при redeploy."""
        raw = self.max_default_subscriber_ids.strip()
        if not raw:
            return []
        ids: list[int] = []
        for part in raw.replace(";", ",").split(","):
            piece = part.strip()
            if piece:
                ids.append(int(piece))
        return ids

    def bitrix_lead_card_url(self, portal_domain: str, lead_id: int) -> str:
        """Ссылка на карточку лида в портале Битрикс24."""
        domain = portal_domain.strip().rstrip("/")
        if domain.startswith("http://") or domain.startswith("https://"):
            base = domain
        else:
            base = f"https://{domain}"
        return f"{base}/crm/lead/details/{lead_id}/"


def get_settings() -> Settings:
    """Возвращает экземпляр настроек."""
    return Settings()
