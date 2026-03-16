from __future__ import annotations

from hearth.reticulum.adapter import PathEntry


class PathSnapshotStore:
    def __init__(self) -> None:
        self._entries: list[PathEntry] = []

    def replace(self, entries: list[PathEntry]) -> None:
        self._entries = list(entries)

    def list(self) -> list[PathEntry]:
        return list(self._entries)

    def summary(self) -> dict:
        return {"count": len(self._entries), "routes": [entry.to_dict() for entry in self._entries]}

