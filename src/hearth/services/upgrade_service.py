from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from sqlalchemy import desc, select

from hearth import __version__
from hearth.core.config import HearthSettings
from hearth.services.config_service import ConfigService
from hearth.services.config_version_service import ConfigVersionService
from hearth.services.fleet_service import FleetService
from hearth.services.maintenance_service import MaintenanceService
from hearth.storage.db import Database
from hearth.storage.models import UpgradeOperationRecord, utcnow


class UpgradeService:
    def __init__(
        self,
        settings: HearthSettings,
        database: Database,
        fleet_service: FleetService,
        maintenance_service: MaintenanceService,
        config_version_service: ConfigVersionService,
        config_service: ConfigService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.fleet_service = fleet_service
        self.maintenance_service = maintenance_service
        self.config_version_service = config_version_service
        self.config_service = config_service

    def _parse_nodes(self, target_nodes: list[str] | str | None) -> list[str]:
        if target_nodes is None:
            return []
        items = target_nodes.split(",") if isinstance(target_nodes, str) else target_nodes
        return sorted({str(item).strip() for item in items if str(item).strip()})

    def _serialize(self, row: UpgradeOperationRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "action": row.action,
            "current_version": row.current_version,
            "target_version": row.target_version,
            "channel": row.channel,
            "target_group": row.target_group,
            "target_nodes": json.loads(row.target_nodes_json or "[]"),
            "resolved_nodes": json.loads(row.resolved_nodes_json or "[]"),
            "status": row.status,
            "maintenance_enabled": row.maintenance_enabled,
            "notes": row.notes,
            "actor": row.actor,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def _resolve_targets(
        self,
        target_group: str | None = None,
        target_nodes: list[str] | str | None = None,
    ) -> tuple[list[str], str | None]:
        nodes = await self.fleet_service.list_nodes()
        resolved_group = (target_group or "").strip() or None
        candidates = self._parse_nodes(target_nodes)
        if resolved_group:
            candidates.extend(
                str(node.get("node_name") or "")
                for node in nodes
                if str(node.get("group_name") or "") == resolved_group
            )
        resolved = sorted({item for item in candidates if item})
        if not resolved:
            resolved = [self.settings.system.node_name]
        return resolved, resolved_group

    def _operation_file(self, operation_id: int) -> Path:
        return self.settings.remote_actions_dir / f"upgrade-{operation_id}.json"

    def _workspace_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    async def list_operations(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = session.scalars(select(UpgradeOperationRecord).order_by(desc(UpgradeOperationRecord.id)).limit(limit)).all()
        return [self._serialize(row) for row in rows]

    async def execute_local_operation(
        self,
        *,
        action: str,
        target_version: str,
        channel: str = "stable",
        notes: str | None = None,
        enable_maintenance: bool = False,
        actor: str = "system",
        operation_id: int | None = None,
    ) -> dict[str, Any]:
        normalized_action = action.strip().lower()
        if normalized_action not in {"upgrade", "rollback"}:
            raise ValueError("unsupported upgrade action")
        if enable_maintenance:
            self.maintenance_service.enable(reason=f"{normalized_action}:{target_version}", actor=actor)

        plan: dict[str, Any] = {
            "action": normalized_action,
            "target_version": target_version,
            "channel": channel,
            "notes": notes,
            "actor": actor,
            "workspace": str(self._workspace_root()),
        }

        if normalized_action == "rollback" and str(target_version).startswith("config-revision:"):
            revision_id = int(str(target_version).split(":", 1)[1])
            revision = self.config_version_service.get_revision(revision_id)
            if revision is None:
                return {"status": "failed", "detail": "revision not found", "revision_id": revision_id}
            result = self.config_service.save_raw(
                revision["raw_text"],
                source="upgrade.rollback",
                actor=actor,
                summary=f"rollback to config revision #{revision_id}",
            )
            return {
                "status": "completed" if result.get("saved") else "failed",
                "mode": "config_revision",
                "revision_id": revision_id,
                **result,
            }

        workspace_root = self._workspace_root()
        if normalized_action == "upgrade" and target_version.strip().lower() in {"workspace", "local", __version__.lower()}:
            command = [sys.executable, "-m", "pip", "install", "-e", "."]
        else:
            package_spec = f"hearth=={target_version}"
            command = [sys.executable, "-m", "pip", "install", "--upgrade", package_spec]

        plan["command"] = command
        if operation_id is not None:
            self._operation_file(operation_id).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "status": "completed" if completed.returncode == 0 else "failed",
            "mode": "pip",
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }

    async def schedule_operation(
        self,
        *,
        action: str,
        target_version: str,
        channel: str = "stable",
        target_group: str | None = None,
        target_nodes: list[str] | str | None = None,
        notes: str | None = None,
        enable_maintenance: bool = False,
        actor: str = "system",
    ) -> dict[str, Any]:
        normalized_action = action.strip().lower()
        if normalized_action not in {"upgrade", "rollback"}:
            raise ValueError("unsupported upgrade action")
        resolved_nodes, resolved_group = await self._resolve_targets(target_group=target_group, target_nodes=target_nodes)
        with self.database.session() as session:
            row = UpgradeOperationRecord(
                action=normalized_action,
                current_version=__version__,
                target_version=(target_version or "unknown").strip() or "unknown",
                channel=(channel or "stable").strip() or "stable",
                target_group=resolved_group,
                target_nodes_json=json.dumps(self._parse_nodes(target_nodes), ensure_ascii=False),
                resolved_nodes_json=json.dumps(resolved_nodes, ensure_ascii=False),
                status="planned",
                maintenance_enabled=bool(enable_maintenance and self.settings.system.node_name in resolved_nodes),
                notes=(notes or "").strip() or None,
                actor=actor,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(row)
            session.flush()
            operation_id = row.id
            payload = self._serialize(row)

        dispatch_results: list[dict[str, Any]] = []
        success_count = 0
        for node_name in resolved_nodes:
            if node_name == self.settings.system.node_name:
                result = await self.execute_local_operation(
                    action=normalized_action,
                    target_version=target_version,
                    channel=channel,
                    notes=notes,
                    enable_maintenance=enable_maintenance,
                    actor=actor,
                    operation_id=operation_id,
                )
                dispatch_results.append({"node_name": node_name, "mode": "local", **result})
                if result.get("status") == "completed":
                    success_count += 1
                continue

            result = await self.fleet_service.dispatch_remote_request(
                node_name=node_name,
                method="POST",
                api_path="/upgrades/execute",
                payload={
                    "action": normalized_action,
                    "target_version": target_version,
                    "channel": channel,
                    "notes": notes,
                    "enable_maintenance": enable_maintenance,
                },
                timeout=20,
            )
            response = result.get("response") if isinstance(result.get("response"), dict) else {}
            if response.get("status") == "completed":
                success_count += 1
            dispatch_results.append(result)

        total = len(resolved_nodes)
        actionable_results = [
            item
            for item in dispatch_results
            if item.get("mode") == "local" or item.get("status") not in {"unreachable", "skipped"}
        ]
        if not actionable_results:
            status = "planned"
        elif success_count == total:
            status = "completed"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        with self.database.session() as session:
            row = session.scalar(select(UpgradeOperationRecord).where(UpgradeOperationRecord.id == operation_id))
            if row is not None:
                row.status = status
                row.updated_at = utcnow()

        payload["status"] = status
        payload["dispatch_results"] = dispatch_results
        payload["success_count"] = success_count
        payload["failure_count"] = max(total - success_count, 0)

        self.database.record_event(
            f"upgrade.{normalized_action}",
            f"{normalized_action} executed for {len(resolved_nodes)} node(s) to {payload['target_version']}",
            source="upgrade_service",
            payload={
                "operation_id": operation_id,
                "action": normalized_action,
                "target_version": payload["target_version"],
                "channel": payload["channel"],
                "target_group": resolved_group,
                "resolved_nodes": resolved_nodes,
                "maintenance_enabled": enable_maintenance,
                "notes": payload["notes"],
                "actor": actor,
                "dispatch_results": dispatch_results,
                "status": status,
            },
        )
        return payload

    def recent_revisions(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.config_version_service.list_revisions(limit=limit)
