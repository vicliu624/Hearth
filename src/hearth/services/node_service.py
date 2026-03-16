from __future__ import annotations

from typing import Any

from hearth.core.config import HearthSettings
from hearth.core.events import EventBus
from hearth.interfaces.registry import InterfaceRegistry
from hearth.monitor.health import HealthStatusEvaluator
from hearth.monitor.metrics import MetricsCollector
from hearth.reticulum.adapter import ReticulumAdapter
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

    async def start(self, reason: str = "manual") -> dict[str, Any]:
        await self.adapter.start()
        await self.interface_registry.start_enabled()
        self.database.record_event("node.started", "node started", source="node_service", payload={"reason": reason})
        self.events.publish("node.started", reason=reason)
        return await self.status_summary(persist=True)

    async def stop(self, reason: str = "manual") -> dict[str, Any]:
        await self.interface_registry.stop_all()
        await self.adapter.stop()
        await self.observation_service.sync()
        self.database.record_event("node.stopped", "node stopped", source="node_service", payload={"reason": reason})
        self.events.publish("node.stopped", reason=reason)
        return await self.status_summary(persist=True)

    async def restart(self, reason: str = "manual") -> dict[str, Any]:
        await self.adapter.restart()
        await self.interface_registry.start_enabled()
        self.database.record_restart("runtime", self.settings.system.node_name, reason)
        self.database.record_event("node.restarted", "node restarted", source="node_service", payload={"reason": reason})
        self.events.publish("node.restarted", reason=reason)
        return await self.status_summary(persist=True)

    async def refresh_state(self) -> dict[str, Any]:
        return await self.status_summary(persist=True)

    async def status_summary(self, persist: bool = False) -> dict[str, Any]:
        runtime = await self.adapter.refresh()
        runtime_status = runtime.to_dict()

        interface_objects = [await self.interface_registry.get(name).get_status() for name in self.interface_registry.driver_names()]
        self.adapter.set_interfaces(interface_objects)
        interfaces = [item.to_dict() for item in interface_objects]
        if not runtime_status["running"]:
            interfaces = [
                {
                    **item,
                    "status": "stopped" if item["enabled"] else item["status"],
                    "health_status": "warning" if item["enabled"] else item["health_status"],
                }
                for item in interfaces
            ]

        observation_counts = await self.observation_service.sync()
        peers = [peer.to_dict() for peer in self.observation_service.peer_store.list_recent()]
        routes = [entry.to_dict() for entry in self.observation_service.path_store.list()]
        announces = [entry.to_dict() for entry in self.observation_service.announce_store.recent(100)]
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
                "last_seen_at": item["last_seen_at"].isoformat() if item["last_seen_at"] else None,
            }
            for item in interfaces
        ]
        summary = {
            "node_name": self.settings.system.node_name,
            "runtime_status": runtime_status["status"],
            "runtime": runtime_status,
            "health_status": health["status"],
            "issues": health["issues"],
            "maintenance": self.database.get_maintenance_state(),
            "uptime_seconds": runtime_status["uptime_seconds"],
            "started_at": runtime_status["started_at"],
            "interface_summary": {
                "total": len(interface_rows),
                "online": sum(1 for item in interface_rows if item["status"] == "running"),
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
            self.database.record_interface_metric_snapshots(interfaces)
        return summary
