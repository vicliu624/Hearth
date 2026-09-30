from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from pydantic import ValidationError

from hearth.core.config import (
    HearthSettings,
    dump_settings,
    parse_settings_text,
    validate_settings,
    load_settings,
)
from hearth.core.operations import OperationLock, atomic_write
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
        self.operations = OperationLock(settings.data_dir / "operations.lock")

    @property
    def active_path(self) -> Path:
        return self._config_path().with_suffix(".active.toml")

    def mark_active(self) -> None:
        atomic_write(self.active_path, dump_settings(self.settings))

    def activation_status(self) -> dict:
        pending = load_settings(self._config_path())
        return {
            "pending": dump_settings(pending) != dump_settings(self.settings),
            "active": self.settings.to_display_dict(),
            "saved": pending.to_display_dict(),
        }

    def save_live_section(self, section: str, value: Any) -> dict:
        # These sections have no runtime-owned resources or scheduler bindings.
        if section not in {"roles", "plugins", "plugin_sources"}:
            raise ValueError("This section requires explicit configuration apply")
        with self.operations.hold():
            pending = load_settings(self._config_path()).model_dump(
                mode="json", exclude_none=True
            )
            pending[section] = value
            active = self.settings.model_dump(mode="json", exclude_none=True)
            active[section] = value
            candidate = validate_settings(active)
            result = self.save(pending)
            if result.get("saved"):
                setattr(self.settings, section, getattr(candidate, section))
                self.mark_active()
            return result

    def _config_path(self) -> Path:
        if self.settings.config_path is None:
            raise ValueError(
                "config_path is not set; use --config or HEARTH_CONFIG first"
            )
        return Path(self.settings.config_path)

    def _snapshot_name(self) -> str:
        return datetime.now(timezone.utc).strftime("config-%Y%m%d-%H%M%S-%f.toml.bak")

    def _backup_existing_config(self, config_path: Path) -> str | None:
        if not config_path.exists():
            return None
        backup_path = self.settings.backups_dir / self._snapshot_name()
        backup_path.write_text(
            config_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
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

    def show(self) -> dict[str, Any]:
        return self.settings.to_display_dict()

    def show_raw(self) -> dict[str, Any]:
        config_path = self._config_path()
        raw = (
            config_path.read_text(encoding="utf-8")
            if config_path.exists()
            else dump_settings(self.settings)
        )
        return {
            "path": str(config_path),
            "raw": raw,
            "pending": self.activation_status()["pending"],
        }

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
            return {
                "valid": False,
                "errors": [{"msg": str(exc)}],
                "semantic_errors": [],
            }
        return self._validation_payload(settings)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.save_raw(
            dump_settings(payload), source="save", summary="settings payload saved"
        )

    def save_raw(
        self,
        raw_text: str,
        *,
        source: str = "save_raw",
        actor: str = "config_service",
        summary: str = "raw configuration saved",
    ) -> dict[str, Any]:
        with self.operations.hold():
            return self._save_raw(raw_text, source=source, actor=actor, summary=summary)

    def _save_raw(
        self, raw_text: str, *, source: str, actor: str, summary: str
    ) -> dict:
        validation = self.validate_raw(raw_text)
        if not validation["valid"]:
            validation["saved"] = False
            return validation
        config_path = self._config_path()
        backup_path = self._backup_existing_config(config_path)
        atomic_write(config_path, raw_text)
        revision = None
        if self.version_service is not None:
            revision = self.version_service.record_revision(
                raw_text, source=source, actor=actor, summary=summary
            )
        return {
            "saved": True,
            "path": str(config_path),
            "backup_path": backup_path,
            "restart_required": True,
            "applied": False,
            "pending": True,
            "revision": revision,
        }
