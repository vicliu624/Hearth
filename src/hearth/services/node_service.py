from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from hearth.core.config import HearthSettings
from hearth.core.events import EventBus
from hearth.interfaces.registry import InterfaceRegistry
from hearth.monitor.health import HealthStatusEvaluator
from hearth.monitor.metrics import MetricsCollector
from hearth.reticulum.adapter import (
    InterfaceRuntimeInfo,
    ReticulumAdapter,
    project_interfaces,
)
from hearth.storage.db import Database


class NodeService:
    def __init__(
        self,
        settings: HearthSettings,
        adapter: ReticulumAdapter,
        interface_registry: InterfaceRegistry,
        health_evaluator: HealthStatusEvaluator,
        metrics_collector: MetricsCollector,
        database: Database,
        events: EventBus,
        observation_service,
    ) -> None:
        self.settings = settings
        self.adapter = adapter
        self.interface_registry = interface_registry
        self.health_evaluator = health_evaluator
        self.metrics_collector = metrics_collector
        self.database = database
        self.events = events
        self.observation_service = observation_service
        self._summary: dict[str, Any] | None = None
        self._sampled_at = 0.0
        self._refresh_lock = asyncio.Lock()
        self.adapter.on_change = self.invalidate

    def invalidate(self) -> None:
        self._summary = None

    def sample_metadata(self) -> dict:
        return {
            "observed_at": (self._summary or {}).get("observed_at"),
            "stale": self._summary is None
            or monotonic() - self._sampled_at
            > max(1, self.settings.monitor.metrics_refresh_sec) * 2,
            "status": (self._summary or {})
            .get("runtime", {})
            .get("details", {})
            .get("observation_status"),
        }

    def _merge_interfaces(
        self,
        configured: list[InterfaceRuntimeInfo],
        observed: list[InterfaceRuntimeInfo],
        *,
        runtime_running: bool,
    ) -> list[dict[str, Any]]:
        return project_interfaces(
            configured,
            observed,
            desired=self.adapter.control_state().get("interfaces", {}),
            running=runtime_running,
            observation_valid=bool(
                self.adapter._observed_runtime.get("interfaces_valid")
            ),
            simulated=self.settings.reticulum.backend == "mock_process",
            can_control=self.settings.reticulum.backend == "mock_process"
            or (
                self.settings.reticulum.backend == "managed_rnsd"
                and self.settings.reticulum.render_managed_config
            ),
        )

    async def start(self, reason: str = "manual") -> dict[str, Any]:
        async with self.adapter.operations.acquire():
            return await self._start(reason)

    async def _start(self, reason: str) -> dict[str, Any]:
        if reason == "auto_start" and self.adapter.desired_state() != "running":
            return await self.status_summary(persist=True, force=True)
        await self.adapter.start(recovery=reason == "auto_start")
        await self.interface_registry.start_enabled()
        self.database.record_event(
            "node.started",
            "node started",
            source="node_service",
            payload={"reason": reason},
        )
        self.events.publish("node.started", reason=reason)
        return await self.status_summary(persist=True, force=True)

    async def stop(self, reason: str = "manual") -> dict[str, Any]:
        async with self.adapter.operations.acquire():
            return await self._stop(reason)

    async def _stop(self, reason: str) -> dict[str, Any]:
        await self.interface_registry.stop_all()
        await self.adapter.stop(intentional=True)
        await self.observation_service.sync()
        self.database.record_event(
            "node.stopped",
            "node stopped",
            source="node_service",
            payload={"reason": reason},
        )
        self.events.publish("node.stopped", reason=reason)
        return await self.status_summary(persist=True, force=True)

    async def restart(self, reason: str = "manual") -> dict[str, Any]:
        async with self.adapter.operations.acquire():
            return await self._restart(reason)

    async def _restart(self, reason: str) -> dict[str, Any]:
        if reason.startswith("watchdog.") and self.adapter.desired_state() != "running":
            return await self.status_summary(persist=True, force=True)
        await self.adapter.restart(recovery=reason.startswith("watchdog."))
        await self.interface_registry.start_enabled()
        self.database.record_restart("runtime", self.settings.system.node_name, reason)
        self.database.record_event(
            "node.restarted",
            "node restarted",
            source="node_service",
            payload={"reason": reason},
        )
        self.events.publish("node.restarted", reason=reason)
        return await self.status_summary(persist=True, force=True)

    async def refresh_state(self) -> dict[str, Any]:
        return await self.status_summary(persist=True, force=True)

    async def status_summary(
        self, persist: bool = False, *, force: bool = False
    ) -> dict[str, Any]:
        # Requests read the last completed sample. Only the sampler and control
        # operations run external commands; slow probes never hold up warm pages.
        if force or self._summary is None:
            async with self._refresh_lock:
                if force or self._summary is None:
                    sampled = await self._collect_summary(persist=persist)
                    sampled["observed_at"] = datetime.now(timezone.utc).isoformat()
                    self._summary = sampled
                    self._sampled_at = monotonic()
        summary = deepcopy(self._summary)
        summary["observation_age_seconds"] = max(0.0, monotonic() - self._sampled_at)
        summary["observation_stale"] = (
            summary["observation_age_seconds"]
            > max(1, self.settings.monitor.metrics_refresh_sec) * 2
        )
        if summary.get("runtime", {}).get("details", {}).get("observation_status") in {
            "unavailable",
            "partial",
        }:
            summary["observation_stale"] = True
        summary["maintenance"] = self.database.get_maintenance_state()
        summary["desired_state"] = self.adapter.desired_state()
        return summary

    async def _collect_summary(self, persist: bool = False) -> dict[str, Any]:
        interface_objects = [
            await self.interface_registry.get(name).get_status()
            for name in self.interface_registry.driver_names()
        ]
        self.adapter.set_interfaces(interface_objects)
        runtime = await self.adapter.refresh()
        runtime_status = runtime.to_dict()
        runtime_status["desired_state"] = self.adapter.desired_state()
        interfaces = self._merge_interfaces(
            interface_objects,
            self.adapter.get_interfaces(),
            runtime_running=runtime_status["running"],
        )

        observation_counts = await self.observation_service.sync()
        peers = [
            peer.to_dict() for peer in self.observation_service.peer_store.list_recent()
        ]
        routes = [
            entry.to_dict() for entry in self.observation_service.path_store.list()
        ]
        announces = [
            entry.to_dict()
            for entry in self.observation_service.announce_store.recent(100)
        ]
        health = self.health_evaluator.evaluate(runtime_status, interfaces).to_dict()
        metrics = self.metrics_collector.collect(
            runtime_status=runtime_status,
            interfaces=interfaces,
            peer_count=observation_counts["peer_count"],
            route_count=observation_counts["route_count"],
            announce_count=observation_counts["announce_count"],
        )
        interface_rows = [
            {
                **item,
                "last_seen_at": item["last_seen_at"].isoformat()
                if item["last_seen_at"]
                else None,
            }
            for item in interfaces
        ]
        summary = {
            "node_name": self.settings.system.node_name,
            "runtime_status": runtime_status["status"],
            "runtime": runtime_status,
            "desired_state": self.adapter.desired_state(),
            "health_status": health["status"],
            "issues": health["issues"],
            "maintenance": self.database.get_maintenance_state(),
            "uptime_seconds": runtime_status["uptime_seconds"],
            "started_at": runtime_status["started_at"],
            "interface_summary": {
                "total": len(interface_rows),
                "online": sum(
                    1 for item in interface_rows if item["status"] == "running"
                ),
            },
            "peer_count": observation_counts["peer_count"],
            "route_count": observation_counts["route_count"],
            "announce_count": observation_counts["announce_count"],
            "restart_count": runtime_status["restart_count"],
            "metrics": metrics,
            "interfaces": interface_rows,
            "recent_peers": peers[:5],
            "recent_routes": routes[:5],
            "recent_announces": announces[:5],
        }
        if persist:
            self.database.save_node_state(
                runtime_status=summary["runtime_status"],
                health_status=summary["health_status"],
                uptime_seconds=summary["uptime_seconds"],
                started_at=runtime.started_at,
                restart_count=summary["restart_count"],
            )
            for item in interfaces:
                self.database.upsert_interface_runtime(item)
            if runtime_status["running"] and (
                self.settings.reticulum.backend == "mock_process"
                or runtime_status.get("details", {}).get("observation_status") == "ok"
            ):
                self.database.record_interface_metric_snapshots(interfaces)
        return summary
