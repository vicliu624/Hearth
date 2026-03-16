from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from hearth.core.config import HearthSettings, load_settings
from hearth.core.events import EventBus
from hearth.core.scheduler import AsyncScheduler
from hearth.discovery.peers import PeerStore
from hearth.interfaces.registry import InterfaceRegistry
from hearth.monitor.health import HealthStatusEvaluator
from hearth.monitor.logs import LogService
from hearth.monitor.metrics import MetricsCollector
from hearth.monitor.watchdog import WatchdogService
from hearth.reticulum.announces import AnnounceStore
from hearth.reticulum.identity import IdentityManager
from hearth.reticulum.paths import PathSnapshotStore
from hearth.reticulum.runtime import ManagedReticulumAdapter
from hearth.services.alert_service import AlertService
from hearth.services.announce_service import AnnounceService
from hearth.services.backup_service import BackupService
from hearth.services.bridge_catalog_service import BridgeCatalogService
from hearth.services.config_service import ConfigService
from hearth.services.config_version_service import ConfigVersionService
from hearth.services.diagnostics_service import DiagnosticsService
from hearth.services.degradation_policy_service import DegradationPolicyService
from hearth.services.fleet_service import FleetService
from hearth.services.interface_service import InterfaceService
from hearth.services.maintenance_service import MaintenanceService
from hearth.services.remote_log_service import RemoteLogService
from hearth.services.rollout_service import RolloutService
from hearth.services.node_service import NodeService
from hearth.services.observation_service import ObservationService
from hearth.services.peer_service import PeerService
from hearth.services.plugin_service import PluginService
from hearth.services.route_service import RouteService
from hearth.services.security_service import SecurityService
from hearth.services.service_host_service import ServiceHostService
from hearth.services.topology_service import TopologyService
from hearth.services.upgrade_service import UpgradeService
from hearth.storage.db import Database


class ApplicationContext:
    def __init__(self, settings_path: str | Path | None = None) -> None:
        self.settings: HearthSettings = load_settings(settings_path)
        self.events = EventBus()
        self.scheduler = AsyncScheduler()
        self.database = Database(self.settings.database_url)
        self.identity_manager = IdentityManager(self.settings.identity_path)
        self.adapter = ManagedReticulumAdapter(self.settings)
        self.interface_registry = InterfaceRegistry()
        self.peer_store = PeerStore()
        self.path_store = PathSnapshotStore()
        self.announce_store = AnnounceStore()
        self.health_evaluator = HealthStatusEvaluator(self.settings.reticulum.health_timeout_sec)
        self.metrics_collector = MetricsCollector()
        self.log_service = LogService(self.database)
        self.maintenance_service = MaintenanceService(self.database)
        self.config_version_service = ConfigVersionService(self.settings, self.database)
        self.config_service = ConfigService(self.settings, self.interface_registry, self.config_version_service)
        self.security_service = SecurityService(self.settings, self.database, self.config_service)
        self.degradation_policy_service = DegradationPolicyService(self.settings)
        self.interface_service = InterfaceService(self.interface_registry, self.database, self.adapter)
        self.observation_service = ObservationService(
            adapter=self.adapter,
            peer_store=self.peer_store,
            path_store=self.path_store,
            announce_store=self.announce_store,
            database=self.database,
        )
        self.peer_service = PeerService(self.peer_store, self.database, self.observation_service)
        self.route_service = RouteService(self.path_store, self.database, self.observation_service)
        self.announce_service = AnnounceService(self.announce_store, self.database, self.observation_service)
        self.plugin_service = PluginService(self.settings, self.config_service)
        self.bridge_catalog_service = BridgeCatalogService(self.plugin_service, self.database)
        self.backup_service = BackupService(self.settings, self.database)
        self.node_service = NodeService(
            settings=self.settings,
            adapter=self.adapter,
            interface_registry=self.interface_registry,
            health_evaluator=self.health_evaluator,
            metrics_collector=self.metrics_collector,
            database=self.database,
            events=self.events,
            observation_service=self.observation_service,
        )
        self.watchdog = WatchdogService(
            settings=self.settings.monitor,
            node_service=self.node_service,
            interface_service=self.interface_service,
            degradation_policy=self.degradation_policy_service,
            maintenance_service=self.maintenance_service,
            database=self.database,
            events=self.events,
        )
        self.service_host_service = ServiceHostService(
            settings=self.settings,
            scheduler=self.scheduler,
            node_service=self.node_service,
            observation_service=self.observation_service,
            maintenance_service=self.maintenance_service,
            database=self.database,
        )
        self.alert_service = AlertService(self.settings, self.database)
        self.diagnostics_service = DiagnosticsService(
            self.settings,
            self.database,
            self.scheduler,
            self.config_version_service,
            self.plugin_service,
            self.service_host_service,
        )
        self.fleet_service = FleetService(self.settings, self.database, self.node_service)
        self.rollout_service = RolloutService(self.settings, self.database, self.fleet_service, self.config_service)
        self.remote_log_service = RemoteLogService(self.settings, self.database, self.fleet_service)
        self.upgrade_service = UpgradeService(
            self.settings,
            self.database,
            self.fleet_service,
            self.maintenance_service,
            self.config_version_service,
            self.config_service,
        )
        self.topology_service = TopologyService(
            self.settings,
            self.database,
            self.peer_service,
            self.route_service,
        )

    async def refresh_alerts(self) -> dict:
        summary = await self.node_service.status_summary(persist=False)
        return await self.alert_service.refresh(summary)

    async def startup(
        self,
        *,
        auto_start_runtime: bool | None = None,
        enable_background_jobs: bool = True,
    ) -> None:
        self.settings.ensure_directories()
        self.identity_manager.ensure_identity()
        self.database.init_schema()
        self.config_version_service.ensure_baseline_revision()
        self.interface_registry.register_builtins()
        await self.interface_registry.configure(self.settings.interfaces)
        self.interface_registry.restore_states(self.database.get_interface_runtimes())

        should_auto_start = self.settings.reticulum.enabled and (
            self.settings.reticulum.auto_start if auto_start_runtime is None else auto_start_runtime
        )

        if should_auto_start:
            await self.node_service.start(reason="auto_start")
        else:
            await self.node_service.refresh_state()

        await self.observation_service.sync()

        if enable_background_jobs:
            await self.scheduler.start()
            self.scheduler.add_job(
                "state_refresh",
                self.settings.monitor.metrics_refresh_sec,
                self.node_service.refresh_state,
            )
            self.scheduler.add_job(
                "alerts_refresh",
                self.settings.alerts.sync_interval_sec,
                self.refresh_alerts,
            )
            if self.settings.monitor.watchdog_enabled:
                self.scheduler.add_job(
                    "watchdog",
                    self.settings.monitor.health_check_interval_sec,
                    self.watchdog.run_once,
                )

    async def shutdown(self, *, stop_runtime: bool = True) -> None:
        await self.scheduler.stop()
        if stop_runtime:
            await self.interface_registry.stop_all()
            await self.adapter.stop()


def build_context(settings_path: str | Path | None = None) -> ApplicationContext:
    return ApplicationContext(settings_path=settings_path)


def lifespan_factory(context: ApplicationContext):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await context.startup(auto_start_runtime=None, enable_background_jobs=True)
        try:
            yield
        finally:
            await context.shutdown(stop_runtime=True)

    return lifespan


def attach_context(app: FastAPI, context: ApplicationContext) -> None:
    app.state.context = context
