from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
import tomllib

from pydantic import BaseModel, ConfigDict, Field, ValidationError
import tomli_w


class SystemSettings(BaseModel):
    node_name: str = "hearth-node"
    data_dir: Path = Path("./.data")
    log_level: str = "INFO"
    timezone: str = "UTC"


class ReticulumSettings(BaseModel):
    enabled: bool = True
    config_path: Path = Path("./reticulum-config")
    identity_path: Path = Path("./.data/identity")
    auto_start: bool = True
    backend: Literal["mock_process", "external_process", "managed_rnsd"] = "mock_process"
    command: list[str] = Field(default_factory=list)
    heartbeat_interval_sec: int = 2
    health_timeout_sec: int = 10
    shutdown_timeout_sec: int = 5
    transport_enabled: bool = True
    shared_instance: bool = True
    instance_name: str = "default"
    discover_interfaces: bool = False
    autoconnect_discovered_interfaces: int = 0
    loglevel: int = 4
    render_managed_config: bool = True
    managed_command: str | None = None


class WebSettings(BaseModel):
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8480
    auth_mode: str = "local_token"


class SecuritySettings(BaseModel):
    admin_token: str = "change-me"
    allow_lan: bool = True
    allow_wan: bool = False


class MonitorSettings(BaseModel):
    health_check_interval_sec: int = 15
    metrics_refresh_sec: int = 10
    watchdog_enabled: bool = True
    auto_restart_runtime: bool = True
    auto_restart_interface: bool = True
    restart_cooldown_sec: int = 30


class AlertsSettings(BaseModel):
    webhook_enabled: bool = False
    webhook_url: str | None = None
    include_resolved: bool = True
    delivery_timeout_sec: int = 5
    sync_interval_sec: int = 30


class InterfaceSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    enabled: bool = True
    role: str | None = None


class PluginSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    enabled: bool = False


class PluginSourceSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    index_url: str
    label: str | None = None
    description: str | None = None
    trusted: bool = False
    expected_sha256: str | None = None
    public_key: str | None = None
    signature: str | None = None
    signature_algorithm: str | None = None
    signature_required: bool = False


class RoleSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    label: str | None = None
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class HearthSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    system: SystemSettings = Field(default_factory=SystemSettings)
    reticulum: ReticulumSettings = Field(default_factory=ReticulumSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)
    alerts: AlertsSettings = Field(default_factory=AlertsSettings)
    interfaces: list[InterfaceSettings] = Field(default_factory=list)
    plugins: list[PluginSettings] = Field(default_factory=list)
    plugin_sources: list[PluginSourceSettings] = Field(default_factory=list)
    roles: list[RoleSettings] = Field(default_factory=list)
    config_path: Path | None = Field(default=None, exclude=True)

    def resolve_path(self, value: Path) -> Path:
        if value.is_absolute():
            return value
        base = self.config_path.parent if self.config_path else Path.cwd()
        return (base / value).resolve()

    @property
    def data_dir(self) -> Path:
        return self.resolve_path(self.system.data_dir)

    @property
    def reticulum_config_path(self) -> Path:
        return self.resolve_path(self.reticulum.config_path)

    @property
    def identity_path(self) -> Path:
        return self.resolve_path(self.reticulum.identity_path)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "hearth.db"

    @property
    def runtime_dir(self) -> Path:
        return self.data_dir / "runtime"

    @property
    def runtime_state_path(self) -> Path:
        return self.runtime_dir / "reticulum-state.json"

    @property
    def runtime_managed_config_path(self) -> Path:
        return self.reticulum_config_path / "config"

    @property
    def runtime_observations_path(self) -> Path:
        return self.runtime_dir / "reticulum-observations.json"

    @property
    def runtime_pid_path(self) -> Path:
        return self.runtime_dir / "reticulum.pid"

    @property
    def runtime_stdout_path(self) -> Path:
        return self.runtime_dir / "reticulum.stdout.log"

    @property
    def runtime_stderr_path(self) -> Path:
        return self.runtime_dir / "reticulum.stderr.log"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def plugin_runtime_dir(self) -> Path:
        return self.data_dir / "plugins"

    @property
    def plugin_state_path(self) -> Path:
        return self.plugin_runtime_dir / "installed-plugins.json"

    @property
    def remote_logs_dir(self) -> Path:
        return self.data_dir / "remote-logs"

    @property
    def remote_actions_dir(self) -> Path:
        return self.data_dir / "remote-actions"

    @property
    def backup_snapshots_path(self) -> Path:
        return self.backups_dir / "snapshots.json"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.plugin_runtime_dir.mkdir(parents=True, exist_ok=True)
        self.remote_logs_dir.mkdir(parents=True, exist_ok=True)
        self.remote_actions_dir.mkdir(parents=True, exist_ok=True)
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        self.reticulum_config_path.mkdir(parents=True, exist_ok=True)
        if self.config_path:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def to_display_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["system"]["data_dir"] = str(self.system.data_dir)
        data["reticulum"]["config_path"] = str(self.reticulum.config_path)
        data["reticulum"]["identity_path"] = str(self.reticulum.identity_path)
        return data


def default_settings() -> HearthSettings:
    return HearthSettings()


def load_settings(path: str | Path | None = None) -> HearthSettings:
    config_path = Path(path).resolve() if path else None
    if config_path is None:
        settings = default_settings()
        settings.config_path = None
        return settings

    if not config_path.exists():
        settings = default_settings()
        settings.config_path = config_path
        return settings

    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)

    settings = HearthSettings.model_validate(payload)
    settings.config_path = config_path
    return settings


def validate_settings(payload: dict[str, Any]) -> HearthSettings:
    return HearthSettings.model_validate(payload)


def parse_settings_text(raw_text: str) -> HearthSettings:
    payload = tomllib.loads(raw_text)
    return HearthSettings.model_validate(payload)


def dump_settings(payload: HearthSettings | dict[str, Any]) -> str:
    if isinstance(payload, HearthSettings):
        data = payload.model_dump(mode="json", exclude={"config_path"}, exclude_none=True)
    else:
        data = HearthSettings.model_validate(payload).model_dump(mode="json", exclude={"config_path"}, exclude_none=True)
    return tomli_w.dumps(data)


__all__ = [
    "HearthSettings",
    "InterfaceSettings",
    "PluginSettings",
    "PluginSourceSettings",
    "RoleSettings",
    "AlertsSettings",
    "ValidationError",
    "default_settings",
    "dump_settings",
    "load_settings",
    "parse_settings_text",
    "validate_settings",
]
