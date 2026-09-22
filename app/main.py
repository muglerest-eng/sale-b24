"""Точка входа FastAPI: вебхуки Битрикс24 и MAX."""

import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.models import BitrixSession, MaxUpdate
from app.services.bitrix_auth import verify_bitrix_auth
from app.services.bitrix_client import BitrixClient
from app.services.bitrix_webhook_parser import extract_lead_id, parse_bitrix_webhook_body
from app.services.lead_notifier import notify_subscribers_about_lead
from app.services.max_client import MaxClient
from app.services.max_startup import ensure_max_webhook, max_webhook_url, public_base_url
from app.services.max_subscription import handle_max_update
from app.storage import list_all_subscriber_ids, processed_lead_store, subscriber_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Стартовые задачи: регистрация MAX webhook."""
    try:
        await ensure_max_webhook(get_settings())
    except Exception:
        logger.exception("Ошибка при старте MAX webhook")
    yield


app = FastAPI(
    title="Bitrix24 → MAX lead notifier",
    version="1.2.0",
    lifespan=_lifespan,
)


@lru_cache
def _settings() -> Settings:
    return get_settings()


def _data_dir() -> Path:
    return Path(_settings().data_dir)


@app.get("/health")
async def health() -> dict[str, str]:
    """Проверка доступности сервиса после деплоя."""
    return {"status": "ok"}


@app.get("/health/bitrix")
async def health_bitrix() -> dict[str, object]:
    """Диагностика интеграции Битрикс24."""
    settings = _settings()
    data_dir = _data_dir()
    return {
        "status": "ok",
        "handler_url": settings.bitrix24_handler_url,
        "handler_path": settings.bitrix_webhook_path(),
        "has_incoming_webhook": bool(settings.bitrix_incoming_webhook_url.strip()),
        "has_application_token": bool(settings.bitrix24_application_token.strip()),
        "max_subscribers": list_all_subscriber_ids(
            subscriber_store(data_dir),
            settings.parsed_default_subscriber_ids(),
        ),
        "max_subscribers_from_env": settings.parsed_default_subscriber_ids(),
        "hint": (
            "В Битриксе handler = handler_url, событие ONCRMLEADADD. "
            "Если исходящий webhook — нужен BITRIX_INCOMING_WEBHOOK_URL."
        ),
    }


@app.get("/health/max")
async def health_max(reregister: bool = False) -> JSONResponse:
    """Проверка MAX: токен, webhook, подписчики. ?reregister=1 — повторная регистрация."""
    settings = _settings()
    client = MaxClient(settings)
    base = public_base_url(settings)
    expected_webhook = max_webhook_url(settings, base)

    try:
        me = await client.get_me()
        subscriptions = await client.list_subscriptions()
        register_info: dict[str, object] | None = None

        has_webhook = any(
            expected_webhook in str(item.get("url", ""))
            for item in subscriptions
        )
        if reregister or not has_webhook:
            register_info = await ensure_max_webhook(settings)
            subscriptions = await client.list_subscriptions()
            has_webhook = any(
                expected_webhook in str(item.get("url", ""))
                for item in subscriptions
            )

        ok = has_webhook and bool(me)
        payload = {
            "status": "ok" if ok else "degraded",
            "bot": me.get("username") or me.get("name"),
            "expected_webhook": expected_webhook,
            "webhooks": subscriptions,
            "subscribers": list_all_subscriber_ids(
                subscriber_store(_data_dir()),
                settings.parsed_default_subscriber_ids(),
            ),
            "ssl_verify": settings.http_ssl_verify,
            "register": register_info,
        }
        return JSONResponse(payload, status_code=200 if ok else 503)
    except Exception as exc:
        return JSONResponse(
            {
                "status": "error",
                "expected_webhook": expected_webhook,
                "detail": str(exc),
                "hint": "Попробуйте HTTP_SSL_VERIFY=false в переменных Timeweb",
            },
            status_code=503,
        )


async def _handle_bitrix_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """Обработчик локального приложения / исходящего webhook Битрикс24."""
    settings = _settings()
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    try:
        payload = parse_bitrix_webhook_body(raw, content_type)
    except ValueError as exc:
        logger.warning("Некорректный webhook Битрикс: %s", exc)
        raise HTTPException(status_code=400, detail="Bad request") from exc

    logger.info(
        "Битрикс webhook: event=%s domain=%s oauth=%s app_token=%s",
        payload.event,
        payload.auth.domain or "-",
        bool(payload.auth.access_token.strip()),
        "yes" if payload.auth.application_token.strip() else "missing",
    )

    if not verify_bitrix_auth(payload.auth, settings):
        logger.warning("Отклонён webhook Битрикс: невалидный auth")
        raise HTTPException(status_code=403, detail="Forbidden")

    event = payload.event.upper()
    if event != "ONCRMLEADADD":
        logger.info("Битрикс событие проигнорировано: %s", event)
        return Response(content="ignored", media_type="text/plain")

    lead_id = extract_lead_id(payload)
    if lead_id is None:
        logger.warning("ONCRMLEADADD без ID лида, data=%s", payload.data)
        return Response(content="no lead id", media_type="text/plain")

    session = BitrixSession(
        access_token=payload.auth.access_token,
        client_endpoint=payload.auth.client_endpoint,
        domain=payload.auth.domain,
        server_endpoint=payload.auth.server_endpoint,
        refresh_token=payload.auth.refresh_token,
    )
    logger.info("Новый лид %s — постановка в очередь MAX", lead_id)
    background_tasks.add_task(_process_new_lead, lead_id, session)
    return Response(content="ok", media_type="text/plain")


async def _handle_max_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """Общая логика webhook MAX."""
    settings = _settings()
    secret_header = request.headers.get("X-Max-Bot-Api-Secret", "")
    if secret_header != settings.max_webhook_secret:
        logger.warning("Отклонён webhook MAX: неверный secret")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        data = await request.json()
        update = MaxUpdate.model_validate(data)
    except Exception as exc:
        logger.warning("Некорректный JSON MAX: %s", exc)
        raise HTTPException(status_code=400, detail="Bad request") from exc

    logger.info("MAX webhook получен: update_type=%s", update.update_type)
    background_tasks.add_task(_process_max_update, update)
    return Response(content="ok", media_type="text/plain")


async def _process_new_lead(lead_id: int, session: BitrixSession) -> None:
    settings = _settings()
    data_dir = _data_dir()
    try:
        await notify_subscribers_about_lead(
            lead_id=lead_id,
            session=session,
            settings=settings,
            bitrix=BitrixClient(settings),
            max_client=MaxClient(settings),
            subscribers=subscriber_store(data_dir),
            processed=processed_lead_store(data_dir),
        )
    except Exception:
        logger.exception("Ошибка обработки лида %s", lead_id)


async def _process_max_update(update: MaxUpdate) -> None:
    settings = _settings()
    await handle_max_update(
        update=update,
        settings=settings,
        subscribers=subscriber_store(_data_dir()),
        max_client=MaxClient(settings),
    )


def _register_bitrix_route() -> None:
    """Регистрирует путь из BITRIX24_HANDLER_URL и фиксированный alias."""
    paths = {"/webhook/bitrix24"}
    try:
        paths.add(get_settings().bitrix_webhook_path())
    except Exception:
        pass

    for index, path in enumerate(sorted(paths)):
        app.add_api_route(
            path,
            _handle_bitrix_webhook,
            methods=["POST"],
            name=f"bitrix24_handler_{index}",
        )
        logger.info("Битрикс handler: POST %s", path)


def _register_prefixed_max_webhooks() -> None:
    """Регистрирует MAX webhook с опциональным секретным префиксом."""
    secret = os.getenv("WEBHOOK_PATH_SECRET", "").strip().strip("/")
    if not secret:
        return

    @app.post(f"/{secret}/max/webhook")
    async def max_webhook_secret(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        return await _handle_max_webhook(request, background_tasks)


@app.post("/max/webhook")
async def max_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """Принимает обновления MAX Bot API."""
    return await _handle_max_webhook(request, background_tasks)


_register_bitrix_route()
_register_prefixed_max_webhooks()
