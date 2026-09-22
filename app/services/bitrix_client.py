"""HTTP-клиент Битрикс24 REST."""

import httpx

from app.config import Settings
from app.models import BitrixSession


class BitrixClient:
    """REST-запросы к Битрикс24."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._incoming_webhook = settings.bitrix_incoming_webhook_url.strip().rstrip("/") + "/"

    async def get_lead(self, session: BitrixSession, lead_id: int) -> dict[str, object]:
        """
        Загружает лид по ID.

        OAuth из события или входящий webhook, если OAuth нет.
        """
        if session.access_token.strip() and session.client_endpoint.strip():
            return await self._get_lead_oauth(session, lead_id)
        if self._settings.bitrix_incoming_webhook_url.strip():
            return await self._get_lead_incoming(lead_id)
        raise ValueError(
            "Нет access_token в событии и не задан BITRIX_INCOMING_WEBHOOK_URL",
        )

    async def _get_lead_oauth(self, session: BitrixSession, lead_id: int) -> dict[str, object]:
        """Загрузка лида через OAuth-токен события."""
        base = session.client_endpoint.rstrip("/") + "/"
        params = {"auth": session.access_token, "id": lead_id}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base}crm.lead.get", params=params)
            if response.status_code == 401 and session.refresh_token:
                new_token = await self._refresh_access_token(session)
                params["auth"] = new_token
                response = await client.get(f"{base}crm.lead.get", params=params)
            response.raise_for_status()
            payload = response.json()

        return self._extract_lead_result(payload, lead_id)

    async def _get_lead_incoming(self, lead_id: int) -> dict[str, object]:
        """Загрузка лида через входящий webhook URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._incoming_webhook}crm.lead.get",
                params={"id": lead_id},
            )
            response.raise_for_status()
            payload = response.json()

        return self._extract_lead_result(payload, lead_id)

    async def _refresh_access_token(self, session: BitrixSession) -> str:
        """Обновляет access_token через client_id/client_secret."""
        endpoint = session.server_endpoint.strip() or "https://oauth.bitrix.info/rest/"
        url = f"{endpoint.rstrip('/')}/oauth/token/"
        data = {
            "grant_type": "refresh_token",
            "client_id": self._settings.bitrix24_client_id,
            "client_secret": self._settings.bitrix24_client_secret,
            "refresh_token": session.refresh_token,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("Не удалось обновить access_token Битрикс24")
        return token

    def _extract_lead_result(self, payload: dict[str, object], lead_id: int) -> dict[str, object]:
        """Достаёт result из ответа crm.lead.get."""
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ValueError(f"crm.lead.get: неожиданный ответ для лида {lead_id}")
        return result

    def portal_domain_from_incoming_webhook(self) -> str:
        """Домен портала из URL входящего webhook."""
        from urllib.parse import urlparse

        parsed = urlparse(self._settings.bitrix_incoming_webhook_url.strip())
        return parsed.netloc
