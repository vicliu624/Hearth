from __future__ import annotations

from typing import Any


class MetricsCollector:
    def collect(
        self,
        runtime_status: dict[str, Any],
        interfaces: list[dict[str, Any]],
        peer_count: int,
        route_count: int,
        announce_count: int,
    ) -> dict[str, int]:
        return {
            "uptime_seconds": runtime_status["uptime_seconds"],
            "interface_count": len(interfaces),
            "active_interfaces": sum(1 for item in interfaces if item["status"] == "running"),
            "active_peers": peer_count,
            "route_count": route_count,
            "announce_count": announce_count,
            "restart_count": runtime_status["restart_count"],
            "error_count": sum(item["metrics"].get("error_count", 0) for item in interfaces),
        }

