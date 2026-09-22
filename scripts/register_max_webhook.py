#!/usr/bin/env python3
"""Регистрирует webhook MAX на URL вашего сервера."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.max_client import MaxClient


async def _run(public_base_url: str) -> None:
    settings = get_settings()
    base = public_base_url.rstrip("/")
    prefix = settings.webhook_path_secret.strip().strip("/")
    path = f"/{prefix}/max/webhook" if prefix else "/max/webhook"
    url = f"{base}{path}"

    client = MaxClient(settings)
    result = await client.register_webhook(
        url=url,
        secret=settings.max_webhook_secret,
        update_types=["bot_started", "message_created", "bot_stopped"],
    )
    print("Подписка MAX создана:")
    print(result)


def main() -> None:
    """CLI для POST /subscriptions."""
    parser = argparse.ArgumentParser(description="Зарегистрировать MAX webhook")
    parser.add_argument(
        "public_base_url",
        help="Публичный URL сервера, например https://bot.example.com",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.public_base_url))


if __name__ == "__main__":
    main()
