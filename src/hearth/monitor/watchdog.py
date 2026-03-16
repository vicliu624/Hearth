from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hearth.core.config import MonitorSettings
from hearth.core.events import EventBus
from hearth.storage.db import Database


class WatchdogService:
    def __init__(
        self,
        settings: MonitorSettings,
        node_service: Any,
        interface_service: Any,
        degradation_policy: Any,
        maintenance_service: Any,
        database: Database,
        events: EventBus,
    ) -> None:
        self.settings = settings
        self.node_service = node_service
        self.interface_service = interface_service
        self.degradation_policy = degradation_policy
        self.maintenance_service = maintenance_service
        self.database = database
        self.events = events
        self._last_actions: dict[tuple[str, str], datetime] = {}

    def _cooldown_elapsed(self, target_type: str, target_name: str) -> bool:
        key = (target_type, target_name)
        last_action = self._last_actions.get(key)
        if last_action is None:
            return True
        elapsed = (datetime.now(timezone.utc) - last_action).total_seconds()
        return elapsed >= self.settings.restart_cooldown_sec

    def _mark_action(self, target_type: str, target_name: str) -> None:
        self._last_actions[(target_type, target_name)] = datetime.now(timezone.utc)

    async def run_once(self) -> None:
        if self.maintenance_service.is_enabled():
            return

        summary = await self.node_service.status_summary(persist=True)
        if summary["health_status"] == "healthy":
            return

        severity = "warning" if summary["health_status"] == "warning" else "error"
        self.events.publish("health.degraded", summary=summary)
        self.database.record_event(
            event_type="health.check",
            severity=severity,
            source="watchdog",
            message=f"watchdog observed {summary['health_status']}",
            payload=summary,
        )

        policy = self.degradation_policy.evaluate(summary)
        if policy["mode"] != "normal":
            self.database.record_event(
                event_type="degradation.policy",
                severity="warning",
                source="watchdog",
                message=f"degradation policy entered {policy['mode']}",
                payload=policy,
            )

        for action in policy["actions"]:
            action_name = str(action.get("action") or "")
            target_name = str(action.get("target_name") or "")
            if action_name == "restart_runtime":
                if not self.settings.auto_restart_runtime or not self._cooldown_elapsed("runtime", target_name):
                    continue
                await self.node_service.restart(reason=f"watchdog.{action.get('reason') or 'runtime'}")
                self._mark_action("runtime", target_name)
                self.database.record_event(
                    event_type="watchdog.runtime_restart",
                    severity="warning",
                    source="watchdog",
                    message="watchdog restarted reticulum runtime",
                    payload={"node_name": target_name, "policy_action": action},
                )
                summary = await self.node_service.status_summary(persist=True)
                continue

            if action_name == "restart_interface":
                if not self.settings.auto_restart_interface or not self._cooldown_elapsed("interface", target_name):
                    continue
                await self.interface_service.restart(target_name)
                self._mark_action("interface", target_name)
                self.database.record_event(
                    event_type="watchdog.interface_restart",
                    severity="warning",
                    source="watchdog",
                    message=f"watchdog restarted interface {target_name}",
                    payload={"interface": target_name, "policy_action": action},
                )
                continue

            if action_name == "quarantine_interface":
                if not self._cooldown_elapsed("interface", target_name):
                    continue
                await self.interface_service.stop(target_name)
                self._mark_action("interface", target_name)
                self.database.record_event(
                    event_type="watchdog.interface_quarantine",
                    severity="warning",
                    source="watchdog",
                    message=f"watchdog isolated interface {target_name}",
                    payload={"interface": target_name, "policy_action": action},
                )

        if policy["actions"] or not self.settings.auto_restart_interface or summary["runtime_status"] != "running":
            return

        for interface in summary["interfaces"]:
            needs_restart = interface["enabled"] and (
                interface["status"] in {"stopped", "error"}
                or interface["health_status"] in {"degraded", "critical"}
            )
            if not needs_restart:
                continue
            if not self._cooldown_elapsed("interface", interface["name"]):
                continue

            await self.interface_service.restart(interface["name"])
            self._mark_action("interface", interface["name"])
            self.database.record_event(
                event_type="watchdog.interface_restart",
                severity="warning",
                source="watchdog",
                message=f"watchdog restarted interface {interface['name']}",
                payload={"interface": interface["name"]},
            )
