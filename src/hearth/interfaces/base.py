from __future__ import annotations

from abc import ABC
from datetime import datetime, timezone
from typing import Any

from hearth.reticulum.adapter import InterfaceRuntimeInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InterfaceDriver(ABC):
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.enabled = bool(config.get("enabled", True))
        self.role = config.get("role")
        self._running = False
        self._status = "stopped"
        self._health_status = "healthy" if not self.enabled else "warning"
        self._restart_count = 0
        self._error_count = 0
        self._health_check_count = 0
        self._last_error: str | None = None
        self._last_seen_at: datetime | None = None
        self._last_started_at: datetime | None = None
        self._mock_fail_starts_remaining = int(config.get("mock_fail_starts", 0) or 0)

    @property
    def type(self) -> str:
        raise NotImplementedError

    async def load(self, config: dict[str, Any]) -> None:
        self.config = config
        self.enabled = bool(config.get("enabled", True))
        self.role = config.get("role")
        self._mock_fail_starts_remaining = int(config.get("mock_fail_starts", 0) or 0)

    def validate_configuration(self) -> list[str]:
        return []

    def restore(self, payload: dict[str, Any]) -> None:
        self._status = payload.get("status", self._status)
        self._health_status = payload.get("health_status", self._health_status)
        self._running = self._status == "running"
        self._last_seen_at = payload.get("last_seen_at")
        self._last_error = payload.get("last_error")
        self._error_count = int(payload.get("error_count", self._error_count))
        self._restart_count = int(payload.get("restart_count", self._restart_count))

    def _set_error(self, message: str) -> None:
        self._running = False
        self._status = "error"
        self._health_status = "degraded"
        self._last_error = message
        self._error_count += 1

    async def start(self) -> None:
        if not self.enabled:
            self._running = False
            self._status = "stopped"
            self._health_status = "healthy"
            return

        errors = self.validate_configuration()
        if errors:
            self._set_error("; ".join(errors))
            return

        if self._mock_fail_starts_remaining > 0:
            self._mock_fail_starts_remaining -= 1
            self._set_error("mock start failure")
            return

        now = utcnow()
        self._running = True
        self._status = "running"
        self._health_status = "healthy"
        self._last_started_at = now
        self._last_seen_at = now
        self._last_error = None

    async def stop(self) -> None:
        self._running = False
        self._status = "stopped"
        self._health_status = "healthy" if not self.enabled else "warning"

    async def restart(self) -> None:
        self._restart_count += 1
        await self.stop()
        await self.start()

    async def health_check(self) -> dict[str, Any]:
        self._health_check_count += 1
        forced_status = self.config.get("mock_health_status")
        errors = self.validate_configuration()

        if forced_status:
            self._health_status = str(forced_status)
        elif errors:
            self._health_status = "degraded"
            self._last_error = "; ".join(errors)
        elif not self.enabled:
            self._health_status = "healthy"
        elif self._status == "error":
            self._health_status = "degraded"
        elif self._running:
            self._health_status = "healthy"
            self._last_seen_at = utcnow()
        else:
            self._health_status = "warning"

        return {
            "status": self._health_status,
            "last_seen_at": self._last_seen_at,
            "last_error": self._last_error,
        }

    async def get_status(self) -> InterfaceRuntimeInfo:
        health = await self.health_check()
        return InterfaceRuntimeInfo(
            name=self.name,
            type=self.type,
            enabled=self.enabled,
            status=self._status,
            health_status=health["status"],
            last_seen_at=self._last_seen_at,
            metrics=await self.get_metrics(),
            last_error=self._last_error,
        )

    async def get_metrics(self) -> dict[str, int]:
        return {
            "rx_packets": 0,
            "tx_packets": 0,
            "error_count": self._error_count,
            "restart_count": self._restart_count,
            "health_check_count": self._health_check_count,
        }


class BasicInterfaceDriver(InterfaceDriver):
    driver_type = "custom"

    @property
    def type(self) -> str:
        return self.driver_type

