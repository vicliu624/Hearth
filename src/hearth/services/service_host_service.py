from __future__ import annotations

from typing import Any

from hearth.core.config import HearthSettings
from hearth.core.scheduler import AsyncScheduler
from hearth.services.maintenance_service import MaintenanceService
from hearth.storage.db import Database


class ServiceHostService:
    def __init__(
        self,
        settings: HearthSettings,
        scheduler: AsyncScheduler,
        node_service: Any,
        observation_service: Any,
        maintenance_service: MaintenanceService,
        database: Database,
    ) -> None:
        self.settings = settings
        self.scheduler = scheduler
        self.node_service = node_service
        self.observation_service = observation_service
        self.maintenance_service = maintenance_service
        self.database = database

    def _recent_logs(self, *, source: str | None = None, event_prefix: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        entries = self.database.list_events(limit=200, source=source)
        logs: list[dict[str, Any]] = []
        for entry in entries:
            event_type = str(entry.get("event_type") or "")
            if event_prefix and not event_type.startswith(event_prefix):
                continue
            logs.append(
                {
                    "event_type": event_type,
                    "message": entry.get("message"),
                    "severity": entry.get("severity"),
                    "created_at": entry.get("created_at"),
                }
            )
            if len(logs) >= limit:
                break
        return logs

    async def list_services(self) -> list[dict[str, Any]]:
        summary = await self.node_service.status_summary(persist=False)
        maintenance = self.maintenance_service.get_state()
        task_names = set(self.scheduler.task_names())
        runtime_status = str(summary.get("runtime_status") or "unknown")
        watchdog_enabled = bool(self.settings.monitor.watchdog_enabled)
        interface_total = int(summary.get("interface_summary", {}).get("total", 0))
        interface_online = int(summary.get("interface_summary", {}).get("online", 0))

        return [
            {
                "name": "reticulum_runtime",
                "label": "Reticulum Runtime",
                "category": "core",
                "status": runtime_status,
                "health": summary.get("health_status") if runtime_status == "running" else "warning",
                "summary": f"PID {summary.get('runtime', {}).get('pid') or '-'} ? {interface_online}/{interface_total} interfaces online",
                "actions": ["start", "stop", "restart"],
                "details": summary.get("runtime", {}),
                "dependencies": [
                    "identity_store",
                    *[f"interface:{item['name']}" for item in summary.get("interfaces", []) if item.get("enabled")],
                ],
                "config": {
                    "backend": self.settings.reticulum.backend,
                    "auto_start": self.settings.reticulum.auto_start,
                    "config_path": str(self.settings.reticulum_config_path),
                    "identity_path": str(self.settings.identity_path),
                },
                "health_checks": [
                    {
                        "name": "runtime_process",
                        "status": "healthy" if runtime_status == "running" else "warning",
                        "detail": f"Runtime state is {runtime_status}.",
                    },
                    {
                        "name": "interfaces_online",
                        "status": "healthy" if interface_online else "warning",
                        "detail": f"{interface_online} of {interface_total} interfaces are online.",
                    },
                ],
                "resource_summary": {
                    "pid": summary.get("runtime", {}).get("pid"),
                    "uptime_seconds": summary.get("uptime_seconds"),
                    "restart_count": summary.get("restart_count"),
                    "peer_count": summary.get("peer_count"),
                    "route_count": summary.get("route_count"),
                },
                "logs": self._recent_logs(source="node_service", event_prefix="node."),
            },
            {
                "name": "web_console",
                "label": "Web Console",
                "category": "control-plane",
                "status": "running" if self.settings.web.enabled else "disabled",
                "health": "healthy" if self.settings.web.enabled else "warning",
                "summary": f"{self.settings.web.host}:{self.settings.web.port} ? auth {self.settings.web.auth_mode}",
                "actions": [],
                "details": {
                    "host": self.settings.web.host,
                    "port": self.settings.web.port,
                    "auth_mode": self.settings.web.auth_mode,
                },
                "dependencies": ["security_policy", "http_stack"],
                "config": {
                    "enabled": self.settings.web.enabled,
                    "host": self.settings.web.host,
                    "port": self.settings.web.port,
                    "auth_mode": self.settings.web.auth_mode,
                    "allow_lan": self.settings.security.allow_lan,
                    "allow_wan": self.settings.security.allow_wan,
                },
                "health_checks": [
                    {
                        "name": "listener_enabled",
                        "status": "healthy" if self.settings.web.enabled else "warning",
                        "detail": "Web listener is enabled." if self.settings.web.enabled else "Web listener is disabled.",
                    },
                    {
                        "name": "auth_policy",
                        "status": "healthy" if self.settings.web.auth_mode != "none" else "warning",
                        "detail": f"Authentication mode is {self.settings.web.auth_mode}.",
                    },
                ],
                "resource_summary": {
                    "host": self.settings.web.host,
                    "port": self.settings.web.port,
                    "auth_mode": self.settings.web.auth_mode,
                },
                "logs": self._recent_logs(source="web_auth"),
            },
            {
                "name": "watchdog",
                "label": "Watchdog",
                "category": "monitor",
                "status": "paused" if maintenance.get("enabled") else "running" if watchdog_enabled else "disabled",
                "health": "warning" if maintenance.get("enabled") or not watchdog_enabled else "healthy",
                "summary": f"cooldown {self.settings.monitor.restart_cooldown_sec}s ? interval {self.settings.monitor.health_check_interval_sec}s",
                "actions": [],
                "details": {
                    "watchdog_enabled": watchdog_enabled,
                    "auto_restart_runtime": self.settings.monitor.auto_restart_runtime,
                    "auto_restart_interface": self.settings.monitor.auto_restart_interface,
                    "maintenance_enabled": maintenance.get("enabled"),
                },
                "dependencies": ["reticulum_runtime", "maintenance_mode"],
                "config": {
                    "watchdog_enabled": watchdog_enabled,
                    "auto_restart_runtime": self.settings.monitor.auto_restart_runtime,
                    "auto_restart_interface": self.settings.monitor.auto_restart_interface,
                    "restart_cooldown_sec": self.settings.monitor.restart_cooldown_sec,
                    "health_check_interval_sec": self.settings.monitor.health_check_interval_sec,
                },
                "health_checks": [
                    {
                        "name": "maintenance_gate",
                        "status": "warning" if maintenance.get("enabled") else "healthy",
                        "detail": "Maintenance mode pauses recovery actions." if maintenance.get("enabled") else "Recovery actions are permitted.",
                    },
                    {
                        "name": "scheduler_task",
                        "status": "healthy" if self.scheduler.running and "scheduler:watchdog" in task_names else "warning",
                        "detail": "Watchdog task is scheduled." if self.scheduler.running and "scheduler:watchdog" in task_names else "Watchdog task is not currently scheduled.",
                    },
                ],
                "resource_summary": {
                    "scheduled": "scheduler:watchdog" in task_names,
                    "maintenance_enabled": maintenance.get("enabled"),
                },
                "logs": self._recent_logs(source="watchdog"),
            },
            {
                "name": "state_refresh",
                "label": "State Refresh Job",
                "category": "scheduler",
                "status": "running" if self.scheduler.running and "scheduler:state_refresh" in task_names else "idle",
                "health": "healthy" if self.scheduler.running else "warning",
                "summary": f"{self.settings.monitor.metrics_refresh_sec}s interval ? {len(task_names)} active tasks",
                "actions": [],
                "details": {"tasks": sorted(task_names)},
                "dependencies": ["scheduler", "reticulum_runtime"],
                "config": {
                    "interval_seconds": self.settings.monitor.metrics_refresh_sec,
                    "scheduler_running": self.scheduler.running,
                },
                "health_checks": [
                    {
                        "name": "scheduler_running",
                        "status": "healthy" if self.scheduler.running else "warning",
                        "detail": "Background scheduler is running." if self.scheduler.running else "Background scheduler is not running.",
                    },
                    {
                        "name": "refresh_task",
                        "status": "healthy" if "scheduler:state_refresh" in task_names else "warning",
                        "detail": "State refresh task is registered." if "scheduler:state_refresh" in task_names else "State refresh task is missing.",
                    },
                ],
                "resource_summary": {
                    "task_count": len(task_names),
                    "tasks": sorted(task_names),
                },
                "logs": [],
            },
            {
                "name": "observation_sync",
                "label": "Observation Sync",
                "category": "discovery",
                "status": "ready" if runtime_status == "running" else "idle",
                "health": "healthy" if runtime_status == "running" else "warning",
                "summary": f"{summary.get('peer_count', 0)} peers / {summary.get('route_count', 0)} routes / {summary.get('announce_count', 0)} announces",
                "actions": ["sync"],
                "details": {
                    "peer_count": summary.get("peer_count", 0),
                    "route_count": summary.get("route_count", 0),
                    "announce_count": summary.get("announce_count", 0),
                },
                "dependencies": ["reticulum_runtime", "peer_store", "path_store", "announce_store"],
                "config": {
                    "mode": "on-demand",
                    "auto_snapshot": True,
                },
                "health_checks": [
                    {
                        "name": "runtime_available",
                        "status": "healthy" if runtime_status == "running" else "warning",
                        "detail": "Runtime is available for discovery sync." if runtime_status == "running" else "Runtime is not currently running.",
                    },
                    {
                        "name": "dataset_visibility",
                        "status": "healthy" if int(summary.get("peer_count", 0)) or int(summary.get("route_count", 0)) else "warning",
                        "detail": f"Current snapshot includes {summary.get('peer_count', 0)} peers and {summary.get('route_count', 0)} routes.",
                    },
                ],
                "resource_summary": {
                    "peer_count": summary.get("peer_count", 0),
                    "route_count": summary.get("route_count", 0),
                    "announce_count": summary.get("announce_count", 0),
                },
                "logs": [],
            },
            {
                "name": "backup_manager",
                "label": "Backup Manager",
                "category": "operations",
                "status": "ready",
                "health": "healthy",
                "summary": f"data dir {self.settings.data_dir}",
                "actions": [],
                "details": {},
                "dependencies": ["filesystem", "database"],
                "config": {
                    "data_dir": str(self.settings.data_dir),
                    "database_path": str(self.settings.database_path),
                },
                "health_checks": [
                    {
                        "name": "data_directory",
                        "status": "healthy",
                        "detail": f"Backup source directory is {self.settings.data_dir}.",
                    },
                    {
                        "name": "database_visible",
                        "status": "healthy",
                        "detail": f"Database path is {self.settings.database_path}.",
                    },
                ],
                "resource_summary": {
                    "data_dir": str(self.settings.data_dir),
                    "database_path": str(self.settings.database_path),
                },
                "logs": [],
            },
        ]

    async def get_service(self, name: str) -> dict[str, Any] | None:
        return next((item for item in await self.list_services() if item["name"] == name), None)

    async def control(self, name: str, action: str) -> dict[str, Any]:
        service = await self.get_service(name)
        if service is None:
            raise LookupError("service not found")

        normalized = action.strip().lower()
        if name == "reticulum_runtime":
            if normalized == "start":
                result = await self.node_service.start(reason="service-control")
            elif normalized == "stop":
                result = await self.node_service.stop(reason="service-control")
            elif normalized == "restart":
                result = await self.node_service.restart(reason="service-control")
            else:
                raise ValueError("unsupported action")
            return {"service": name, "action": normalized, "result": result}

        if name == "observation_sync":
            if normalized != "sync":
                raise ValueError("unsupported action")
            result = await self.observation_service.sync()
            return {"service": name, "action": normalized, "result": result}

        raise ValueError("unsupported service action")
