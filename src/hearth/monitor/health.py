from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class HealthReport:
    status: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HealthStatusEvaluator:
    def __init__(self, runtime_health_timeout_sec: int = 10) -> None:
        self.runtime_health_timeout_sec = runtime_health_timeout_sec

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def evaluate(self, runtime_status: dict[str, Any], interfaces: list[dict[str, Any]]) -> HealthReport:
        issues: list[str] = []
        if runtime_status["status"] in {"stopped", "crashed"}:
            issues.append("reticulum runtime is not running")
            return HealthReport(status="critical", issues=issues)

        if runtime_status["status"] == "starting":
            issues.append("reticulum runtime is still starting")
            return HealthReport(status="warning", issues=issues)

        heartbeat_at = self._parse_datetime(runtime_status.get("last_heartbeat_at"))
        backend = runtime_status.get("backend")
        if backend == "mock_process" and heartbeat_at is not None:
            heartbeat_age = (datetime.now(timezone.utc) - heartbeat_at).total_seconds()
            if heartbeat_age > self.runtime_health_timeout_sec:
                issues.append("reticulum runtime heartbeat is stale")
                return HealthReport(status="degraded", issues=issues)

        degraded_count = sum(
            1
            for item in interfaces
            if item["enabled"] and (item["health_status"] in {"degraded", "critical"} or item["status"] == "error")
        )
        warning_count = sum(
            1
            for item in interfaces
            if item["enabled"] and item["status"] == "stopped"
        ) + sum(1 for item in interfaces if item["enabled"] and item["health_status"] == "warning")

        if degraded_count:
            issues.append("one or more interfaces are degraded")
            return HealthReport(status="degraded", issues=issues)
        if warning_count:
            issues.append("one or more interfaces are in warning state")
            return HealthReport(status="warning", issues=issues)
        return HealthReport(status="healthy", issues=issues)
