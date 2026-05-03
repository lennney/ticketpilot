"""Working and episodic memory for agent runs."""

from __future__ import annotations

import copy
from typing import Any


class WorkingMemory:
    """Per-run context store.

    Provides key-value storage for intermediate step outputs.
    """

    def __init__(self, run_id: str) -> None:
        if not run_id or not run_id.strip():
            raise ValueError("run_id must not be empty")
        self._run_id = run_id
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        if not key or not key.strip():
            raise ValueError("key must not be empty")
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def clear(self) -> None:
        self._data.clear()


class EpisodicMemory:
    """Append-only in-memory store for event / run summaries.

    Records are stored as copies. No update or delete methods exposed.
    clear() is provided for test/reset use only.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        self._records.append(copy.deepcopy(record))

    def get_all(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._records)

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
