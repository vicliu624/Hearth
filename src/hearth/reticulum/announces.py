from __future__ import annotations

from hearth.reticulum.adapter import AnnounceEvent


class AnnounceStore:
    def __init__(self) -> None:
        self._entries: list[AnnounceEvent] = []

    def replace(self, entries: list[AnnounceEvent]) -> None:
        self._entries = list(entries)

    def append(self, event: AnnounceEvent) -> None:
        self._entries.append(event)

    def recent(self, limit: int = 50) -> list[AnnounceEvent]:
        return list(reversed(self._entries[-limit:]))

    def list(self) -> list[AnnounceEvent]:
        return list(self._entries)

