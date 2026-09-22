"""HTTP-клиент с настройкой SSL."""

import certifi
import httpx

from app.config import Settings


def build_async_client(settings: Settings, timeout: float = 30.0) -> httpx.AsyncClient:
    """
    Создаёт httpx.AsyncClient.

    По умолчанию использует certifi + системные CA (после apt install ca-certificates).
    При HTTP_SSL_VERIFY=false проверка отключена (обход для Timeweb/Docker).
    """
    if settings.http_ca_bundle.strip():
        verify: bool | str = settings.http_ca_bundle.strip()
    elif settings.http_ssl_verify:
        verify = certifi.where()
    else:
        verify = False
    return httpx.AsyncClient(timeout=timeout, verify=verify)
