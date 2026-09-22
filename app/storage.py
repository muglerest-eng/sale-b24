"""Хранение подписчиков и обработанных лидов на диске."""

import json
from pathlib import Path


class JsonIdStore:
    """Набор целочисленных ID в JSON-файле."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def list_ids(self) -> list[int]:
        """Возвращает все сохранённые ID."""
        return sorted(self._read_set())

    def add(self, item_id: int) -> bool:
        """
        Добавляет ID.

        Returns:
            True, если ID был новым.
        """
        items = self._read_set()
        if item_id in items:
            return False
        items.add(item_id)
        self._write_set(items)
        return True

    def remove(self, item_id: int) -> bool:
        """
        Удаляет ID.

        Returns:
            True, если ID существовал.
        """
        items = self._read_set()
        if item_id not in items:
            return False
        items.remove(item_id)
        self._write_set(items)
        return True

    def contains(self, item_id: int) -> bool:
        """Проверяет наличие ID."""
        return item_id in self._read_set()

    def _read_set(self) -> set[int]:
        if not self._path.exists():
            return set()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        ids = raw.get("ids", [])
        return {int(x) for x in ids}

    def _write_set(self, items: set[int]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ids": sorted(items)}
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def subscriber_store(data_dir: Path) -> JsonIdStore:
    """Хранилище chat_id подписанных пользователей MAX."""
    return JsonIdStore(data_dir / "subscribers.json")


def list_all_subscriber_ids(store: JsonIdStore, default_ids: list[int]) -> list[int]:
    """Объединяет подписчиков из файла и MAX_DEFAULT_SUBSCRIBER_IDS."""
    return sorted(set(store.list_ids()) | set(default_ids))


def processed_lead_store(data_dir: Path) -> JsonIdStore:
    """Хранилище ID лидов, по которым уже отправлено уведомление."""
    return JsonIdStore(data_dir / "processed_leads.json")
