"""HTTP-клиент MAX Bot API."""

from app.config import Settings
from app.services.http_client import build_async_client


class MaxClient:
    """Отправка сообщений через MAX Bot API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.max_api_base_url.rstrip("/")
        self._token = settings.max_bot_token

    async def send_text_to_chat(self, chat_id: int, text: str) -> None:
        """Отправляет текстовое сообщение в диалог или чат."""
        await self._send_message(chat_id=chat_id, user_id=None, text=text)

    async def send_text_to_user(self, user_id: int, text: str) -> None:
        """Отправляет текстовое сообщение пользователю по user_id."""
        await self._send_message(chat_id=None, user_id=user_id, text=text)

    async def get_me(self) -> dict[str, object]:
        """
        Проверяет токен бота (GET /me).

        Returns:
            Информация о боте из MAX API.
        """
        async with build_async_client(self._settings) as client:
            response = await client.get(
                f"{self._base}/me",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("MAX /me: неожиданный формат ответа")
            return data

    async def list_subscriptions(self) -> list[dict[str, object]]:
        """Возвращает активные webhook-подписки (GET /subscriptions)."""
        async with build_async_client(self._settings) as client:
            response = await client.get(
                f"{self._base}/subscriptions",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                subscriptions = data.get("subscriptions", data.get("items", []))
                if isinstance(subscriptions, list):
                    return [item for item in subscriptions if isinstance(item, dict)]
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            return []

    async def register_webhook(
        self,
        url: str,
        secret: str,
        update_types: list[str],
    ) -> dict[str, object]:
        """
        Регистрирует webhook подписку (POST /subscriptions).

        Returns:
            JSON-ответ API.
        """
        body = {
            "url": url,
            "secret": secret,
            "update_types": update_types,
        }
        async with build_async_client(self._settings) as client:
            response = await client.post(
                f"{self._base}/subscriptions",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("MAX /subscriptions: неожиданный формат ответа")
            return data

    async def _send_message(
        self,
        chat_id: int | None,
        user_id: int | None,
        text: str,
    ) -> None:
        params: dict[str, str] = {}
        if chat_id is not None:
            params["chat_id"] = str(chat_id)
        elif user_id is not None:
            params["user_id"] = str(user_id)
        else:
            raise ValueError("Нужен chat_id или user_id для отправки сообщения")

        async with build_async_client(self._settings) as client:
            response = await client.post(
                f"{self._base}/messages",
                params=params,
                headers=self._headers(),
                json={"text": text},
            )
            response.raise_for_status()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }
