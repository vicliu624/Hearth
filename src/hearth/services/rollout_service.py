from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, select

from hearth.core.config import HearthSettings
from hearth.services.config_service import ConfigService
from hearth.services.fleet_service import FleetService
from hearth.storage.db import Database
from hearth.storage.models import RolloutRecord, utcnow


class RolloutService:
    def __init__(
        self,
        settings: HearthSettings,
        database: Database,
        fleet_service: FleetService,
        config_service: ConfigService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.fleet_service = fleet_service
        self.config_service = config_service

    def _parse_nodes(self, target_nodes: list[str] | str | None) -> list[str]:
        if target_nodes is None:
            return []
        items = target_nodes.split(",") if isinstance(target_nodes, str) else target_nodes
        return sorted({str(item).strip() for item in items if str(item).strip()})

    def _serialize(self, row: RolloutRecord) -> dict[str, Any]:
        target_nodes = json.loads(row.target_nodes_json or "[]")
        resolved_nodes = json.loads(row.resolved_nodes_json or "[]")
        return {
            "id": row.id,
            "action": row.action,
            "template_name": row.template_name,
            "target_group": row.target_group,
            "target_nodes": target_nodes,
            "resolved_nodes": resolved_nodes,
            "target_count": len(resolved_nodes),
            "status": row.status,
            "actor": row.actor,
            "summary": row.summary,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def _resolve_template(self, template_name: str | None) -> dict[str, Any] | None:
        if not template_name:
            return None
        templates = await self.fleet_service.list_templates()
        return next((template for template in templates if str(template.get("name") or "") == template_name), None)

    async def _resolve_targets(
        self,
        *,
        template_name: str | None = None,
        target_group: str | None = None,
        target_nodes: list[str] | str | None = None,
    ) -> tuple[list[str], str | None, dict[str, Any] | None]:
        nodes = await self.fleet_service.list_nodes()
        template = await self._resolve_template(template_name)
        resolved_group = target_group or (str(template.get("target_group") or "").strip() if template else None) or None
        candidates = self._parse_nodes(target_nodes)
        if template:
            candidates.extend(self._parse_nodes(template.get("target_nodes") or []))
            candidates.extend(self._parse_nodes(template.get("applied_nodes") or []))
        if resolved_group:
            candidates.extend(
                str(node.get("node_name") or "")
                for node in nodes
                if str(node.get("group_name") or "") == resolved_group
            )
        resolved = sorted({item for item in candidates if item})
        if not resolved:
            raise ValueError("no target nodes resolved for rollout")
        return resolved, resolved_group, template

    async def list_rollouts(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = session.scalars(select(RolloutRecord).order_by(desc(RolloutRecord.id)).limit(limit)).all()
        return [self._serialize(row) for row in rows]

    async def create_rollout(
        self,
        *,
        action: str = "apply_template",
        template_name: str | None = None,
        target_group: str | None = None,
        target_nodes: list[str] | str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        resolved_nodes, resolved_group, template = await self._resolve_targets(
            template_name=template_name,
            target_group=target_group,
            target_nodes=target_nodes,
        )
        summary = (
            f"{action} for {len(resolved_nodes)} node(s)"
            + (f" using template {template_name}" if template_name else "")
            + (f" in group {resolved_group}" if resolved_group else "")
        )
        with self.database.session() as session:
            row = RolloutRecord(
                action=action,
                template_name=template_name or None,
                target_group=resolved_group,
                target_nodes_json=json.dumps(self._parse_nodes(target_nodes), ensure_ascii=False),
                resolved_nodes_json=json.dumps(resolved_nodes, ensure_ascii=False),
                status="planned",
                actor=actor,
                summary=summary,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(row)
            session.flush()
            rollout_id = row.id
            payload = self._serialize(row)

        dispatch_results: list[dict[str, Any]] = []
        success_count = 0
        total_targets = len(resolved_nodes)

        if action == "apply_template" and template is not None:
            raw_text = str(template.get("template_text") or "")
            for node_name in resolved_nodes:
                if node_name == self.settings.system.node_name:
                    result = self.config_service.save_raw(
                        raw_text,
                        source="rollout",
                        actor=actor,
                        summary=f"rollout #{rollout_id} applied template {template_name or template.get('name')}",
                    )
                    saved = bool(result.get("saved"))
                    if saved:
                        success_count += 1
                    dispatch_results.append({"node_name": node_name, "mode": "local", "saved": saved, **result})
                    continue

                remote_result = await self.fleet_service.dispatch_remote_request(
                    node_name=node_name,
                    method="POST",
                    api_path="/config/save-raw",
                    payload={"raw": raw_text},
                    timeout=12,
                )
                response = remote_result.get("response") if isinstance(remote_result.get("response"), dict) else {}
                saved = bool(response.get("saved"))
                if saved:
                    success_count += 1
                dispatch_results.append({**remote_result, "saved": saved})

        if dispatch_results:
            actionable_results = [
                item
                for item in dispatch_results
                if item.get("mode") == "local" or item.get("status") not in {"unreachable", "skipped"}
            ]
            if not actionable_results:
                status = "planned"
            elif success_count == total_targets:
                status = "completed"
            elif success_count == 0:
                status = "failed"
            else:
                status = "partial"
            with self.database.session() as session:
                row = session.scalar(select(RolloutRecord).where(RolloutRecord.id == rollout_id))
                if row is not None:
                    row.status = status
                    row.summary = f"{action} executed on {success_count}/{total_targets} node(s)"
                    row.updated_at = utcnow()
            payload["status"] = status
            payload["dispatch_results"] = dispatch_results
            payload["success_count"] = success_count
            payload["failure_count"] = max(total_targets - success_count, 0)

        self.database.record_event(
            "rollout.created",
            summary,
            source="rollout_service",
            payload={
                "rollout_id": rollout_id,
                "action": action,
                "template_name": template_name,
                "target_group": resolved_group,
                "resolved_nodes": resolved_nodes,
                "template_description": template.get("description") if template else None,
                "actor": actor,
                "dispatch_results": dispatch_results,
            },
        )
        return payload

    async def template_catalog(self) -> list[dict[str, Any]]:
        return await self.fleet_service.list_templates()
