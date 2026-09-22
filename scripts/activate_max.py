#!/usr/bin/env python3
"""Подключает MAX к серверу после прохождения модерации бота."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.max_client import MaxClient


async def _activate(public_base_url: str, bot_username: str | None) -> None:
    settings = get_settings()
    client = MaxClient(settings)

    me = await client.get_me()
    bot_name = me.get("username") or me.get("name") or "bot"
    print(f"Бот доступен: {bot_name}")

    base = public_base_url.rstrip("/")
    prefix = settings.webhook_path_secret.strip().strip("/")
    webhook_path = f"/{prefix}/max/webhook" if prefix else "/max/webhook"
    webhook_url = f"{base}{webhook_path}"

    result = await client.register_webhook(
        url=webhook_url,
        secret=settings.max_webhook_secret,
        update_types=["bot_started", "message_created", "bot_stopped"],
    )
    print("Webhook зарегистрирован:")
    print(result)

    subscriptions = await client.list_subscriptions()
    print(f"Активных подписок: {len(subscriptions)}")

    nick = bot_username or str(bot_name).lstrip("@")
    code = settings.max_subscribe_code
    print("\nПодписка для менеджеров:")
    print(f"  В чате с ботом: /start {code}")
    print(f"  Deeplink: https://max.ru/{nick}?start={code}")


def main() -> None:
    """CLI."""
    parser = argparse.ArgumentParser(description="Активация MAX после модерации")
    parser.add_argument(
        "public_base_url",
        help="Публичный URL сервера, например https://bot.example.com",
    )
    parser.add_argument(
        "--bot-username",
        help="Ник бота в MAX для deeplink (если отличается от /me)",
    )
    args = parser.parse_args()
    asyncio.run(_activate(args.public_base_url, args.bot_username))


if __name__ == "__main__":
    main()
