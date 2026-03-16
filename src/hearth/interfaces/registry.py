from __future__ import annotations

from datetime import datetime
from typing import Any

from hearth.core.config import InterfaceSettings
from hearth.interfaces.base import InterfaceDriver
from hearth.interfaces.custom import CustomDriver
from hearth.interfaces.local import LocalNetworkDriver
from hearth.interfaces.rnode import RNodeDriver
from hearth.interfaces.serial import SerialDriver
from hearth.interfaces.tcp import TCPDriver


class InterfaceRegistry:
    def __init__(self) -> None:
        self._driver_types: dict[str, type[InterfaceDriver]] = {}
        self._drivers: dict[str, InterfaceDriver] = {}

    def register(self, driver_type: str, driver_cls: type[InterfaceDriver]) -> None:
        self._driver_types[driver_type] = driver_cls

    def register_builtins(self) -> None:
        self.register("tcp", TCPDriver)
        self.register("serial", SerialDriver)
        self.register("rnode", RNodeDriver)
        self.register("local", LocalNetworkDriver)
        self.register("custom", CustomDriver)

    def validate_interfaces(self, interfaces: list[InterfaceSettings]) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        for item in interfaces:
            if item.name in seen_names:
                errors.append({"interface": item.name, "error": "duplicate interface name"})
                continue
            seen_names.add(item.name)
            driver_cls = self._driver_types.get(item.type)
            if driver_cls is None:
                errors.append({"interface": item.name, "error": f"unsupported interface type: {item.type}"})
                continue
            payload = item.model_dump(mode="python")
            driver = driver_cls(item.name, payload)
            for message in driver.validate_configuration():
                errors.append({"interface": item.name, "error": message})
        return errors

    async def configure(self, interfaces: list[InterfaceSettings]) -> None:
        self._drivers.clear()
        seen_names: set[str] = set()
        for item in interfaces:
            if item.name in seen_names:
                raise ValueError(f"duplicate interface name: {item.name}")
            seen_names.add(item.name)
            driver_cls = self._driver_types.get(item.type)
            if driver_cls is None:
                raise ValueError(f"unsupported interface type: {item.type}")
            payload = item.model_dump(mode="python")
            driver = driver_cls(item.name, payload)
            await driver.load(payload)
            self._drivers[item.name] = driver

    def restore_states(self, snapshots: dict[str, dict[str, Any]]) -> None:
        for name, snapshot in snapshots.items():
            driver = self._drivers.get(name)
            if driver is None:
                continue
            payload = dict(snapshot)
            last_seen_at = payload.get("last_seen_at")
            if isinstance(last_seen_at, str):
                payload["last_seen_at"] = datetime.fromisoformat(last_seen_at)
            driver.restore(payload)

    def get(self, name: str) -> InterfaceDriver:
        try:
            return self._drivers[name]
        except KeyError as exc:
            raise KeyError(f"unknown interface: {name}") from exc

    def driver_names(self) -> list[str]:
        return list(self._drivers.keys())

    async def runtime_infos(self) -> list[InterfaceDriver]:
        return [self._drivers[name] for name in self.driver_names()]

    async def list_statuses(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for driver in self._drivers.values():
            items.append((await driver.get_status()).to_dict())
        return items

    async def start_enabled(self) -> None:
        for driver in self._drivers.values():
            if driver.enabled:
                await driver.start()

    async def stop_all(self) -> None:
        for driver in self._drivers.values():
            await driver.stop()

    async def start(self, name: str) -> dict[str, Any]:
        driver = self.get(name)
        await driver.start()
        return (await driver.get_status()).to_dict()

    async def stop(self, name: str) -> dict[str, Any]:
        driver = self.get(name)
        await driver.stop()
        return (await driver.get_status()).to_dict()

    async def restart(self, name: str) -> dict[str, Any]:
        driver = self.get(name)
        await driver.restart()
        return (await driver.get_status()).to_dict()

    async def metrics(self, name: str) -> dict[str, int]:
        return await self.get(name).get_metrics()
