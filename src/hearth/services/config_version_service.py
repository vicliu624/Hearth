from __future__ import annotations

from hashlib import sha256
import difflib
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select

from hearth.core.config import HearthSettings, dump_settings
from hearth.storage.db import Database
from hearth.storage.models import ConfigRevisionRecord


class ConfigVersionService:
    def __init__(self, settings: HearthSettings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def _config_path(self) -> Path | None:
        return Path(self.settings.config_path) if self.settings.config_path else None

    def current_raw(self) -> str:
        config_path = self._config_path()
        if config_path and config_path.exists():
            return config_path.read_text(encoding="utf-8")
        return dump_settings(self.settings)

    def _serialize(self, row: ConfigRevisionRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "revision_label": row.revision_label,
            "source": row.source,
            "actor": row.actor,
            "summary": row.summary,
            "checksum": row.checksum,
            "raw_text": row.raw_text,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def _affected_modules(self, diff_lines: list[str]) -> list[str]:
        joined = "\n".join(diff_lines)
        module_markers = [
            ("[[interfaces]]", "interfaces"),
            ("[reticulum]", "runtime"),
            ("[monitor]", "watchdog"),
            ("[security]", "security"),
            ("[web]", "web"),
            ("[plugins]", "plugins"),
            ("[system]", "system"),
        ]
        modules: list[str] = []
        for marker, module in module_markers:
            if marker in joined and module not in modules:
                modules.append(module)
        if not modules and any(line.startswith(("+", "-")) and not line.startswith(("+++", "---")) for line in diff_lines):
            modules.append("settings")
        return modules

    def list_revisions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = session.scalars(select(ConfigRevisionRecord).order_by(desc(ConfigRevisionRecord.id)).limit(limit)).all()
        return [self._serialize(row) for row in rows]

    def get_revision(self, revision_id: int) -> dict[str, Any] | None:
        with self.database.session() as session:
            row = session.scalar(select(ConfigRevisionRecord).where(ConfigRevisionRecord.id == revision_id))
        return self._serialize(row) if row else None

    def record_revision(self, raw_text: str, *, source: str, actor: str, summary: str | None = None) -> dict[str, Any]:
        checksum = sha256(raw_text.encode("utf-8")).hexdigest()
        with self.database.session() as session:
            latest = session.scalar(select(ConfigRevisionRecord).order_by(desc(ConfigRevisionRecord.id)))
            if latest is not None and latest.checksum == checksum:
                return self._serialize(latest)
            label = f"{source}:{checksum[:8]}"
            row = ConfigRevisionRecord(
                revision_label=label,
                source=source,
                actor=actor,
                summary=summary,
                checksum=checksum,
                raw_text=raw_text,
            )
            session.add(row)
            session.flush()
            return self._serialize(row)

    def ensure_baseline_revision(self) -> dict[str, Any]:
        return self.record_revision(self.current_raw(), source="baseline", actor="startup", summary="initial configuration snapshot")

    def compare_with_current(self, revision_id: int) -> dict[str, Any] | None:
        revision = self.get_revision(revision_id)
        if revision is None:
            return None
        current_raw = self.current_raw()
        revision_lines = revision["raw_text"].splitlines()
        current_lines = current_raw.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                revision_lines,
                current_lines,
                fromfile=f"revision-{revision_id}",
                tofile="current",
                lineterm="",
            )
        )
        added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
        affected_modules = self._affected_modules(diff_lines)
        changed = revision["checksum"] != sha256(current_raw.encode("utf-8")).hexdigest()
        return {
            "revision_id": revision_id,
            "changed": changed,
            "added_lines": added,
            "removed_lines": removed,
            "affected_modules": affected_modules,
            "restart_required": changed,
            "diff_preview": diff_lines[:80],
        }
