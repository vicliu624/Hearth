from __future__ import annotations

from hearth.interfaces.registry import InterfaceRegistry
from hearth.reticulum.adapter import InterfaceRuntimeInfo, ReticulumAdapter
from hearth.storage.db import Database


class InterfaceService:
    def __init__(self, registry: InterfaceRegistry, database: Database, adapter: ReticulumAdapter) -> None:
        self.registry = registry
        self.database = database
        self.adapter = adapter

    def _merge_interfaces(
        self,
        configured: list[InterfaceRuntimeInfo],
        observed: list[InterfaceRuntimeInfo],
    ) -> list[dict]:
        configured_map = {item.name: item for item in configured}
        observed_map = {item.name: item for item in observed}

        merged: list[dict] = []
        for name in [item.name for item in configured]:
            item = observed_map.get(name) or configured_map.get(name)
            if item is None:
                continue
            payload = item.to_dict()
            if name in configured_map:
                payload["enabled"] = configured_map[name].enabled
            merged.append(payload)
        return merged

    async def list_interfaces(self) -> list[dict]:
        configured = [await self.registry.get(name).get_status() for name in self.registry.driver_names()]
        self.adapter.set_interfaces(configured)
        await self.adapter.refresh()
        items = self._merge_interfaces(configured, self.adapter.get_interfaces())
        for item in items:
            self.database.upsert_interface_runtime(item)
        return [
            {**item, "last_seen_at": item["last_seen_at"].isoformat() if item["last_seen_at"] else None}
            for item in items
        ]

    async def get_interface(self, name: str) -> dict:
        configured = [await self.registry.get(driver_name).get_status() for driver_name in self.registry.driver_names()]
        self.adapter.set_interfaces(configured)
        await self.adapter.refresh()
        merged = {item["name"]: item for item in self._merge_interfaces(configured, self.adapter.get_interfaces())}
        item = merged.get(name)
        if item is None:
            raise KeyError(f"unknown interface: {name}")
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
        interface = await self.get_interface(name)
        return interface["metrics"]
