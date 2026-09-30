from __future__ import annotations
from fastapi import HTTPException

from hearth.interfaces.registry import InterfaceRegistry
from hearth.reticulum.adapter import (
    InterfaceRuntimeInfo,
    ReticulumAdapter,
    project_interfaces,
)
from hearth.storage.db import Database


class InterfaceService:
    def __init__(
        self, registry: InterfaceRegistry, database: Database, adapter: ReticulumAdapter
    ) -> None:
        self.registry = registry
        self.database = database
        self.adapter = adapter

    def _merge_interfaces(
        self,
        configured: list[InterfaceRuntimeInfo],
        observed: list[InterfaceRuntimeInfo],
    ) -> list[dict]:
        settings = self.adapter.settings.reticulum
        return project_interfaces(
            configured,
            observed,
            desired=self.adapter.control_state().get("interfaces", {}),
            running=self.adapter.status().running,
            observation_valid=bool(
                self.adapter._observed_runtime.get("interfaces_valid")
            ),
            simulated=settings.backend == "mock_process",
            can_control=settings.backend == "mock_process"
            or (settings.backend == "managed_rnsd" and settings.render_managed_config),
        )

    async def list_interfaces(self) -> list[dict]:
        configured = [
            await self.registry.get(name).get_status()
            for name in self.registry.driver_names()
        ]
        self.adapter.set_interfaces(configured)
        items = self._merge_interfaces(configured, self.adapter.get_interfaces())
        return [
            {
                **item,
                "last_seen_at": item["last_seen_at"].isoformat()
                if item["last_seen_at"]
                else None,
            }
            for item in items
        ]

    async def get_interface(self, name: str) -> dict:
        configured = [
            await self.registry.get(driver_name).get_status()
            for driver_name in self.registry.driver_names()
        ]
        self.adapter.set_interfaces(configured)
        merged = {
            item["name"]: item
            for item in self._merge_interfaces(
                configured, self.adapter.get_interfaces()
            )
        }
        item = merged.get(name)
        if item is None:
            raise HTTPException(status_code=404, detail=f"unknown interface: {name}")
        item["last_seen_at"] = (
            item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        )
        return item

    async def start(self, name: str) -> dict:
        if self.adapter.settings.reticulum.backend != "mock_process":
            return await self._control_real(name, "start")
        self._mock_desired(name, "running")
        item = await self.registry.start(name)
        if item["status"] != "running":
            raise RuntimeError(
                item.get("last_error") or f"interface {name} failed to start"
            )
        self.adapter._changed()
        self.database.record_event(
            "interface.started", f"interface {name} started", source="interface_service"
        )
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = (
            item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        )
        return item

    async def stop(self, name: str) -> dict:
        if self.adapter.settings.reticulum.backend != "mock_process":
            return await self._control_real(name, "stop")
        self._mock_desired(name, "stopped")
        item = await self.registry.stop(name)
        self.adapter._changed()
        self.database.record_event(
            "interface.stopped", f"interface {name} stopped", source="interface_service"
        )
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = (
            item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        )
        return item

    async def restart(self, name: str) -> dict:
        if self.adapter.settings.reticulum.backend != "mock_process":
            return await self._control_real(name, "restart")
        self._mock_desired(name, "running")
        item = await self.registry.restart(name)
        if item["status"] != "running":
            raise RuntimeError(
                item.get("last_error") or f"interface {name} failed to restart"
            )
        self.adapter._changed()
        self.database.record_restart("interface", name, "manual")
        self.database.record_event(
            "interface.restarted",
            f"interface {name} restarted",
            source="interface_service",
        )
        self.database.upsert_interface_runtime(item)
        item["last_seen_at"] = (
            item["last_seen_at"].isoformat() if item["last_seen_at"] else None
        )
        return item

    async def metrics(self, name: str) -> dict:
        interface = await self.get_interface(name)
        return interface["metrics"]

    async def _control_real(self, name: str, action: str) -> dict:
        result = await self.adapter.control_interface(name, action)
        self.database.record_event(
            f"interface.{action}.verified",
            f"interface {name}: {action} verified",
            source="interface_service",
            payload=result,
        )
        return result

    def _mock_desired(self, name: str, desired: str) -> None:
        with self.adapter.operations.hold():
            driver = self.registry.get(name)
            control = self.adapter.control_state()
            control.setdefault("interfaces", {})[name] = desired
            self.adapter._save_control(control)
            driver.enabled = desired == "running"
