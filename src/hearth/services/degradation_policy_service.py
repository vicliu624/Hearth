from __future__ import annotations

from typing import Any

from hearth.core.config import HearthSettings


CRITICAL_INTERFACE_HEALTH = {"degraded", "critical"}
FAILED_INTERFACE_STATUS = {"stopped", "error"}
PRIMARY_ROLES = {"uplink", "gateway", "backbone", "transport"}
OPTIONAL_ROLES = {"optional", "bootstrap", "discovery", "relay"}


class DegradationPolicyService:
    def __init__(self, settings: HearthSettings) -> None:
        self.settings = settings

    def evaluate(self, summary: dict[str, Any]) -> dict[str, Any]:
        interfaces = list(summary.get("interfaces") or [])
        enabled_interfaces = [item for item in interfaces if item.get("enabled")]
        active_interfaces = [item for item in enabled_interfaces if item.get("status") == "running"]
        unhealthy_interfaces = [
            item
            for item in enabled_interfaces
            if item.get("status") in FAILED_INTERFACE_STATUS or item.get("health_status") in CRITICAL_INTERFACE_HEALTH
        ]
        actions: list[dict[str, Any]] = []
        mode = "normal"
        reasons: list[str] = []

        runtime_status = str(summary.get("runtime_status") or "unknown")
        if runtime_status in {"stopped", "crashed"}:
            mode = "runtime_recovery"
            reasons.append("runtime_unavailable")
            actions.append(
                {
                    "action": "restart_runtime",
                    "target_type": "runtime",
                    "target_name": summary.get("node_name"),
                    "reason": "runtime_unavailable",
                    "priority": 100,
                }
            )

        active_primary = [item for item in active_interfaces if str(item.get("role") or "").strip().lower() in PRIMARY_ROLES]
        if not active_interfaces and enabled_interfaces:
            mode = "interface_failover"
            reasons.append("no_active_interfaces")
            actions.append(
                {
                    "action": "restart_runtime",
                    "target_type": "runtime",
                    "target_name": summary.get("node_name"),
                    "reason": "no_active_interfaces",
                    "priority": 90,
                }
            )

        for interface in unhealthy_interfaces:
            name = str(interface.get("name") or "")
            role = str(interface.get("role") or "").strip().lower()
            if not name:
                continue
            if len(active_interfaces) > 1 and role in OPTIONAL_ROLES:
                if mode == "normal":
                    mode = "interface_isolation"
                reasons.append(f"isolate:{name}")
                actions.append(
                    {
                        "action": "quarantine_interface",
                        "target_type": "interface",
                        "target_name": name,
                        "reason": "optional_interface_unhealthy",
                        "priority": 40,
                    }
                )
                continue
            if mode == "normal":
                mode = "interface_recovery"
            reasons.append(f"restart:{name}")
            actions.append(
                {
                    "action": "restart_interface",
                    "target_type": "interface",
                    "target_name": name,
                    "reason": "interface_unhealthy",
                    "priority": 60 if role in PRIMARY_ROLES else 50,
                }
            )

        if len(unhealthy_interfaces) >= 2 and mode == "normal":
            mode = "degraded"
            reasons.append("multiple_interfaces_unhealthy")

        deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
        for action in sorted(actions, key=lambda item: int(item.get("priority") or 0), reverse=True):
            key = (str(action.get("action") or ""), str(action.get("target_name") or ""))
            deduplicated.setdefault(key, action)

        return {
            "mode": mode,
            "reasons": sorted(set(reasons)),
            "actions": list(deduplicated.values()),
            "active_interfaces": len(active_interfaces),
            "unhealthy_interfaces": len(unhealthy_interfaces),
        }


__all__ = ["DegradationPolicyService"]
