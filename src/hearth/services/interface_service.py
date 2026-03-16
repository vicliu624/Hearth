from __future__ import annotations

from hearth.interfaces.registry import InterfaceRegistry
from hearth.reticulum.adapter import ReticulumAdapter
from hearth.storage.db import Database


class InterfaceService:
    def __init__(self, registry: InterfaceRegistry, database: Database, adapter: ReticulumAdapter) -> None:
        self.registry = registry
        self.database = database
        self.adapter = adapter

    async def list_interfaces(self) -> list[dict]:
        items = await self.registry.list_statuses()
        for item in items:
            self.database.upsert_interface_runtime(item)
        return [
            {**item, "last_seen_at": item["last_seen_at"].isoformat() if item["last_seen_at"] else None}
            for item in items
        ]

    async def get_interface(self, name: str) -> dict:
        driver = self.registry.get(name)
        item = (await driver.get_status()).to_dict()
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        return item

    async def start(self, name: str) -> dict:
        item = await self.registry.start(name)
        self.database.record_event("interface.started", f"interface {name} started", source="interface_service")
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        return item

    async def stop(self, name: str) -> dict:
        item = await self.registry.stop(name)
        self.database.record_event("interface.stopped", f"interface {name} stopped", source="interface_service")
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        return item

    async def restart(self, name: str) -> dict:
        item = await self.registry.restart(name)
        self.database.record_restart("interface", name, "manual")
        self.database.record_event("interface.restarted", f"interface {name} restarted", source="interface_service")
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        return item

    async def metrics(self, name: str) -> dict:
        return await self.registry.metrics(name)
