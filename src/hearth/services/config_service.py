from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from pydantic import ValidationError

from hearth.core.config import HearthSettings, dump_settings, parse_settings_text, validate_settings
from hearth.interfaces.registry import InterfaceRegistry

if TYPE_CHECKING:
    from hearth.services.config_version_service import ConfigVersionService


class ConfigService:
    def __init__(
        self,
        settings: HearthSettings,
        interface_registry: InterfaceRegistry,
        version_service: ConfigVersionService | None = None,
    ) -> None:
        self.settings = settings
        self.interface_registry = interface_registry
        self.version_service = version_service

    def _config_path(self) -> Path:
        if self.settings.config_path is None:
            raise ValueError("config_path is not set; use --config or HEARTH_CONFIG first")
        return Path(self.settings.config_path)

    def _snapshot_name(self) -> str:
        return datetime.now(timezone.utc).strftime("config-%Y%m%d-%H%M%S.toml.bak")

    def _backup_existing_config(self, config_path: Path) -> str | None:
        if not config_path.exists():
            return None
        backup_path = self.settings.backups_dir / self._snapshot_name()
        backup_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
        return str(backup_path)

    def _semantic_errors(self, candidate: HearthSettings) -> list[dict[str, Any]]:
        return self.interface_registry.validate_interfaces(candidate.interfaces)

    def _validation_payload(self, candidate: HearthSettings) -> dict[str, Any]:
        semantic_errors = self._semantic_errors(candidate)
        return {
            "valid": len(semantic_errors) == 0,
            "config": candidate.model_dump(mode="json", exclude={"config_path"}),
            "semantic_errors": semantic_errors,
        }

    def _apply_settings(self, candidate: HearthSettings) -> None:
        self.settings.system = candidate.system
        self.settings.reticulum = candidate.reticulum
        self.settings.web = candidate.web
        self.settings.security = candidate.security
        self.settings.monitor = candidate.monitor
        self.settings.alerts = candidate.alerts
        self.settings.interfaces = candidate.interfaces
        self.settings.plugins = candidate.plugins
        self.settings.plugin_sources = candidate.plugin_sources
        self.settings.roles = candidate.roles
        self.settings.config_path = self._config_path()

    def show(self) -> dict[str, Any]:
        return self.settings.to_display_dict()

    def show_raw(self) -> dict[str, Any]:
        config_path = self._config_path()
        raw = config_path.read_text(encoding="utf-8") if config_path.exists() else dump_settings(self.settings)
        return {"path": str(config_path), "raw": raw}

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            settings = validate_settings(payload)
        except ValidationError as exc:
            return {"valid": False, "errors": exc.errors(), "semantic_errors": []}
        return self._validation_payload(settings)

    def validate_raw(self, raw_text: str) -> dict[str, Any]:
        try:
            settings = parse_settings_text(raw_text)
        except (ValidationError, Exception) as exc:
            if isinstance(exc, ValidationError):
                return {"valid": False, "errors": exc.errors(), "semantic_errors": []}
            return {"valid": False, "errors": [{"msg": str(exc)}], "semantic_errors": []}
        return self._validation_payload(settings)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = validate_settings(payload)
        semantic_errors = self._semantic_errors(settings)
        if semantic_errors:
            return {"saved": False, "semantic_errors": semantic_errors}
        config_path = self._config_path()
        backup_path = self._backup_existing_config(config_path)
        raw_text = dump_settings(settings)
        config_path.write_text(raw_text, encoding="utf-8")
        self._apply_settings(settings)
        revision = None
        if self.version_service is not None:
            revision = self.version_service.record_revision(raw_text, source="save", actor="config_service", summary="settings payload saved")
        return {
            "saved": True,
            "path": str(config_path),
            "backup_path": backup_path,
            "restart_required": True,
            "revision": revision,
        }

    def save_raw(
        self,
        raw_text: str,
        *,
        source: str = "save_raw",
        actor: str = "config_service",
        summary: str = "raw configuration saved",
    ) -> dict[str, Any]:
        validation = self.validate_raw(raw_text)
        if not validation["valid"]:
            validation["saved"] = False
            return validation
        settings = parse_settings_text(raw_text)
        config_path = self._config_path()
        backup_path = self._backup_existing_config(config_path)
        config_path.write_text(raw_text, encoding="utf-8")
        self._apply_settings(settings)
        revision = None
        if self.version_service is not None:
            revision = self.version_service.record_revision(raw_text, source=source, actor=actor, summary=summary)
        return {
            "saved": True,
            "path": str(config_path),
            "backup_path": backup_path,
            "restart_required": True,
            "revision": revision,
        }
