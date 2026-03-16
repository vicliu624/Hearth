from __future__ import annotations

import platform
import sys
from typing import Any

from hearth import __version__
from hearth.core.config import HearthSettings
from hearth.core.scheduler import AsyncScheduler
from hearth.services.config_version_service import ConfigVersionService
from hearth.services.plugin_service import PluginService
from hearth.services.service_host_service import ServiceHostService
from hearth.storage.db import Database


class DiagnosticsService:
    def __init__(
        self,
        settings: HearthSettings,
        database: Database,
        scheduler: AsyncScheduler,
        config_version_service: ConfigVersionService,
        plugin_service: PluginService,
        service_host_service: ServiceHostService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.scheduler = scheduler
        self.config_version_service = config_version_service
        self.plugin_service = plugin_service
        self.service_host_service = service_host_service

    async def snapshot(self, summary: dict[str, Any]) -> dict[str, Any]:
        revisions = self.config_version_service.list_revisions(limit=5)
        services = await self.service_host_service.list_services()
        plugins = self.plugin_service.list_plugins()
        return {
            "hearth_version": __version__,
            "python": sys.version,
            "platform": platform.platform(),
            "runtime": {
                "node_name": summary.get("node_name"),
                "runtime_status": summary.get("runtime_status"),
                "health_status": summary.get("health_status"),
                "uptime_seconds": summary.get("uptime_seconds"),
                "issues": summary.get("issues"),
            },
            "paths": {
                "data_dir": str(self.settings.data_dir),
                "database_path": str(self.settings.database_path),
                "runtime_dir": str(self.settings.runtime_dir),
                "config_path": str(self.settings.config_path) if self.settings.config_path else None,
                "reticulum_config_path": str(self.settings.reticulum_config_path),
                "identity_path": str(self.settings.identity_path),
            },
            "scheduler": {
                "running": self.scheduler.running,
                "tasks": self.scheduler.task_names(),
            },
            "config_revisions": {
                "count": len(self.config_version_service.list_revisions(limit=100)),
                "latest": revisions[0] if revisions else None,
                "recent": revisions,
            },
            "plugins": [
                {
                    "name": plugin.get("name"),
                    "enabled": plugin.get("enabled"),
                    "type": plugin.get("type"),
                    "source": plugin.get("source"),
                    "diagnostics": plugin.get("diagnostics"),
                }
                for plugin in plugins
            ],
            "services": [
                {
                    "name": service.get("name"),
                    "status": service.get("status"),
                    "health": service.get("health"),
                    "actions": service.get("actions"),
                }
                for service in services
            ],
            "recent_events": self.database.list_events(limit=10),
            "restart_history": self.database.list_restarts(limit=10),
        }
