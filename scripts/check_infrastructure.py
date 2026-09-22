#!/usr/bin/env python3
"""Проверка готовности инфраструктуры Битрикс24 → MAX."""

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings, get_settings
from app.services.max_client import MaxClient
from app.storage import list_all_subscriber_ids, subscriber_store


class CheckResult:
    """Результат одной проверки."""

    def __init__(self, name: str, ok: bool, detail: str) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail


async def _check_public_health(public_url: str) -> CheckResult:
    """Проверяет доступность /health с интернета."""
    url = f"{public_url.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
        if response.status_code == 200 and response.json().get("status") == "ok":
            return CheckResult("Публичный /health", True, url)
        return CheckResult(
            "Публичный /health",
            False,
            f"{url} → HTTP {response.status_code}",
        )
    except Exception as exc:
        return CheckResult("Публичный /health", False, f"{url} → {exc}")


def _check_bitrix_config(settings: Settings) -> list[CheckResult]:
    """Проверяет конфиг локального приложения Битрикс24."""
    handler_ok = settings.bitrix24_handler_url.startswith("https://")
    return [
        CheckResult(
            "BITRIX24_HANDLER_URL",
            handler_ok,
            f"POST {settings.bitrix_webhook_path()}",
        ),
        CheckResult(
            "BITRIX24_CLIENT_ID",
            settings.bitrix24_client_id.startswith("local."),
            "формат local.xxx",
        ),
        CheckResult(
            "BITRIX24_CLIENT_SECRET",
            bool(settings.bitrix24_client_secret.strip()),
            "заполнен" if settings.bitrix24_client_secret.strip() else "пусто",
        ),
        CheckResult(
            "BITRIX_INCOMING_WEBHOOK_URL",
            bool(settings.bitrix_incoming_webhook_url.strip()),
            "нужен для исходящего webhook" if not settings.bitrix_incoming_webhook_url.strip() else "заполнен",
        ),
    ]


async def _check_max_token(settings: Settings) -> CheckResult:
    """Проверяет токен MAX через GET /me."""
    client = MaxClient(settings)
    try:
        me = await client.get_me()
        name = me.get("name") or me.get("username") or "бот"
        return CheckResult("MAX токен (/me)", True, f"Бот: {name}")
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {401, 403}:
            detail = "Токен отклонён — проверьте MAX_BOT_TOKEN"
        elif status == 404:
            detail = "API недоступен — проверьте MAX_API_BASE_URL"
        else:
            detail = f"HTTP {status}: {exc.response.text[:200]}"
        return CheckResult("MAX токен (/me)", False, detail)
    except Exception as exc:
        return CheckResult("MAX токен (/me)", False, str(exc))


async def _check_max_subscriptions(settings: Settings) -> CheckResult:
    """Проверяет, зарегистрирован ли webhook MAX."""
    client = MaxClient(settings)
    try:
        subscriptions = await client.list_subscriptions()
        if not subscriptions:
            return CheckResult(
                "MAX webhook",
                False,
                "Подписок нет — после модерации: scripts/activate_max.py",
            )
        urls = [str(item.get("url", "")) for item in subscriptions]
        return CheckResult("MAX webhook", True, "; ".join(urls))
    except Exception as exc:
        return CheckResult("MAX webhook", False, str(exc))


def _check_local_data(settings: Settings) -> CheckResult:
    """Проверяет каталог данных и подписчиков."""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    subscribers = list_all_subscriber_ids(
        subscriber_store(data_dir),
        settings.parsed_default_subscriber_ids(),
    )
    return CheckResult(
        "Локальные данные",
        True,
        f"data_dir={data_dir}, подписчиков: {len(subscribers)}",
    )


def _check_env(settings: Settings) -> list[CheckResult]:
    """Проверяет заполненность ключевых переменных."""
    results: list[CheckResult] = []
    checks = [
        ("MAX_BOT_TOKEN", settings.max_bot_token),
        ("MAX_WEBHOOK_SECRET", settings.max_webhook_secret),
        ("MAX_SUBSCRIBE_CODE", settings.max_subscribe_code),
    ]
    for name, value in checks:
        placeholder = "your_" in value or value.endswith("_token") or "xxxxx" in value
        ok = bool(value.strip()) and not placeholder
        detail = "заполнено" if ok else "заполните в .env"
        results.append(CheckResult(f"ENV {name}", ok, detail))
    return results


async def run_checks(public_url: str | None, skip_max: bool) -> int:
    """
    Запускает все проверки.

    Returns:
        0 если все обязательные проверки прошли, иначе 1.
    """
    settings = get_settings()
    results: list[CheckResult] = _check_env(settings)
    results.append(_check_local_data(settings))

    if public_url:
        results.append(await _check_public_health(public_url))

    results.extend(_check_bitrix_config(settings))

    if not skip_max:
        results.append(await _check_max_token(settings))
        results.append(await _check_max_subscriptions(settings))

    failed = 0
    for item in results:
        mark = "OK" if item.ok else "FAIL"
        print(f"[{mark}] {item.name}: {item.detail}")
        if not item.ok:
            failed += 1

    if skip_max:
        print("\nMAX-проверки пропущены (--skip-max). Запустите без флага после модерации.")
    elif failed:
        print("\nЧасть проверок не прошла — это нормально до модерации бота и регистрации webhook.")

    return 0 if failed == 0 else 1


def main() -> None:
    """CLI."""
    parser = argparse.ArgumentParser(description="Проверка инфраструктуры MAX")
    parser.add_argument(
        "--public-url",
        help="Публичный URL сервера, например https://bot.example.com",
    )
    parser.add_argument(
        "--skip-max",
        action="store_true",
        help="Не проверять MAX API (пока бот на модерации)",
    )
    args = parser.parse_args()
    code = asyncio.run(run_checks(args.public_url, args.skip_max))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
