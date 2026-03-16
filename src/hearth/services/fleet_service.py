from __future__ import annotations

import asyncio
import json
import re
from typing import Any, TYPE_CHECKING
from urllib import request as urllib_request
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.error import HTTPError, URLError

from sqlalchemy import desc, select

from hearth import __version__
from hearth.core.config import HearthSettings
from hearth.storage.db import Database
from hearth.storage.models import ConfigTemplateRecord, FleetNodeRecord, NodeGroupRecord, utcnow

if TYPE_CHECKING:
    from hearth.services.node_service import NodeService


NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.:-]{2,80}$")
FLEET_EVENT_SOURCES = {"fleet_service", "rollout_service", "upgrade_service", "maintenance_service", "node_service"}


class FleetService:
    def __init__(self, settings: HearthSettings, database: Database, node_service: NodeService) -> None:
        self.settings = settings
        self.database = database
        self.node_service = node_service

    def _normalize_dashboard_url(self, value: str | None) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if "://" not in text:
            text = f"http://{text}"
        return text

    def _management_target(self, node: dict[str, Any]) -> dict[str, Any] | None:
        raw_url = self._normalize_dashboard_url(node.get("dashboard_url"))
        if not raw_url:
            return None
        parsed = urlparse(raw_url)
        query = parse_qs(parsed.query)
        token = None
        for key in ("token", "api_token", "hearth_token", "x_hearth_token"):
            values = query.get(key)
            if values:
                token = str(values[0]).strip()
                break
        clean_query = {
            key: value
            for key, value in query.items()
            if key not in {"token", "api_token", "hearth_token", "x_hearth_token"}
        }
        base_path = parsed.path.rstrip("/")
        base_url = urlunparse((parsed.scheme, parsed.netloc, base_path, "", urlencode(clean_query, doseq=True), ""))
        return {
            "base_url": base_url.rstrip("/"),
            "token": token,
        }

    def _build_management_url(self, node: dict[str, Any], api_path: str) -> tuple[str, str | None]:
        target = self._management_target(node)
        if target is None:
            raise ValueError("node does not have a dashboard_url for remote management")
        base_url = str(target["base_url"])
        normalized_path = api_path if api_path.startswith("/") else f"/{api_path}"
        if normalized_path.startswith("/api"):
            url = f"{base_url}{normalized_path}"
        elif base_url.endswith("/api"):
            url = f"{base_url}{normalized_path}"
        else:
            url = f"{base_url}/api{normalized_path}"
        return url, target.get("token")

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        token: str | None = None,
        payload: dict[str, Any] | None = None,
        timeout: int = 8,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json", "User-Agent": "Hearth/1.x"}
        if token:
            headers["X-Hearth-Token"] = token
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib_request.Request(url, data=body, headers=headers, method=method.upper())
        with urllib_request.urlopen(request, timeout=max(timeout, 1)) as response:
            raw = response.read().decode("utf-8")
            if not raw.strip():
                return {"status": response.status}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"items": data}

    async def dispatch_remote_request(
        self,
        *,
        node_name: str,
        method: str,
        api_path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 8,
    ) -> dict[str, Any]:
        node = await self.get_node(node_name)
        if node is None:
            raise LookupError("fleet node not found")
        if node.get("local"):
            return {
                "node_name": node_name,
                "status": "skipped",
                "reason": "local node should be handled directly",
            }
        try:
            url, token = self._build_management_url(node, api_path)
        except ValueError as exc:
            return {
                "node_name": node_name,
                "status": "unreachable",
                "reason": str(exc),
                "response": {"status": "error", "detail": str(exc)},
            }
        try:
            response = await asyncio.to_thread(
                self._request_json,
                method=method,
                url=url,
                token=token,
                payload=payload,
                timeout=timeout,
            )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            response = {"status": "error", "http_status": exc.code, "detail": detail}
        except URLError as exc:
            response = {"status": "error", "detail": str(exc.reason)}
        self.database.record_event(
            "fleet.remote_dispatch",
            f"remote dispatch {method.upper()} {api_path} for {node_name}",
            source="fleet_service",
            payload={
                "node_name": node_name,
                "method": method.upper(),
                "api_path": api_path,
                "request_payload": payload,
                "response": response,
                "actor": "fleet_service",
            },
        )
        return {
            "node_name": node_name,
            "url": url,
            "response": response,
            "status": response.get("status") if isinstance(response, dict) else "ok",
        }

    async def dispatch_batch(
        self,
        *,
        node_names: list[str],
        method: str,
        api_path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 8,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for node_name in node_names:
            results.append(
                await self.dispatch_remote_request(
                    node_name=node_name,
                    method=method,
                    api_path=api_path,
                    payload=payload,
                    timeout=timeout,
                )
            )
        return results

    def _parse_tags(self, tags: list[str] | str | None) -> list[str]:
        if tags is None:
            return []
        if isinstance(tags, str):
            items = tags.split(",")
        else:
            items = tags
        return sorted({str(item).strip() for item in items if str(item).strip()})

    def _serialize_node(self, row: FleetNodeRecord) -> dict[str, Any]:
        return {
            "node_key": row.node_key,
            "node_name": row.node_name,
            "display_name": row.display_name,
            "group_name": row.group_name,
            "tags": json.loads(row.tags_json or "[]"),
            "version": row.version,
            "health_status": row.health_status,
            "runtime_status": row.runtime_status,
            "uptime_seconds": row.uptime_seconds,
            "dashboard_url": row.dashboard_url,
            "region": row.region,
            "notes": row.notes,
            "local": row.local,
            "source": row.source,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _serialize_group(self, row: NodeGroupRecord, node_count: int) -> dict[str, Any]:
        return {
            "name": row.name,
            "description": row.description,
            "group_type": row.group_type,
            "node_count": node_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _serialize_template(self, row: ConfigTemplateRecord, applied_nodes: list[str]) -> dict[str, Any]:
        target_nodes = json.loads(row.target_nodes_json or "[]")
        return {
            "name": row.name,
            "description": row.description,
            "template_text": row.template_text,
            "target_group": row.target_group,
            "target_nodes": target_nodes,
            "applied_nodes": applied_nodes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _event_nodes(self, payload: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        for key in ("node_name", "target_name"):
            value = str(payload.get(key) or "").strip()
            if value:
                candidates.append(value)
        for key in ("resolved_nodes", "target_nodes", "targets"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, str):
                candidates.extend(self._parse_tags(value))
        return sorted(set(candidates))

    def _decorate_event(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = dict(event.get("payload") or {})
        related_nodes = self._event_nodes(payload)
        related_group = str(payload.get("group_name") or payload.get("target_group") or "").strip()
        actor = str(payload.get("actor") or "").strip()
        origin = str(payload.get("origin") or payload.get("source") or event.get("source") or "").strip()
        return {
            **event,
            "node_name": related_nodes[0] if len(related_nodes) == 1 else None,
            "nodes": related_nodes,
            "group_name": related_group or None,
            "actor": actor or None,
            "origin": origin or None,
            "targets": related_nodes,
        }

    async def _sync_local_node(self) -> dict[str, Any]:
        summary = await self.node_service.status_summary(persist=False)
        node_name = self.settings.system.node_name
        node_key = f"local:{node_name}"
        with self.database.session() as session:
            row = session.scalar(select(FleetNodeRecord).where(FleetNodeRecord.node_key == node_key))
            if row is None:
                row = FleetNodeRecord(node_key=node_key, node_name=node_name, local=True, source="self")
                session.add(row)
            row.node_name = node_name
            row.display_name = row.display_name or node_name
            row.version = __version__
            row.health_status = str(summary.get("health_status") or "warning")
            row.runtime_status = str(summary.get("runtime_status") or "offline")
            row.uptime_seconds = int(summary.get("uptime_seconds") or 0)
            row.dashboard_url = row.dashboard_url or "/"
            row.local = True
            row.source = "self"
            row.last_seen_at = utcnow()
            row.updated_at = utcnow()
            session.flush()
            payload = self._serialize_node(row)
        return payload

    async def list_nodes(self) -> list[dict[str, Any]]:
        await self._sync_local_node()
        with self.database.session() as session:
            rows = session.scalars(select(FleetNodeRecord).order_by(desc(FleetNodeRecord.local), FleetNodeRecord.node_name.asc())).all()
        return [self._serialize_node(row) for row in rows]

    async def register_node(
        self,
        *,
        node_name: str,
        display_name: str | None = None,
        group_name: str | None = None,
        tags: list[str] | str | None = None,
        version: str | None = None,
        health_status: str = "warning",
        runtime_status: str = "offline",
        uptime_seconds: int = 0,
        dashboard_url: str | None = None,
        region: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        candidate = node_name.strip()
        if not NAME_PATTERN.match(candidate):
            raise ValueError("node name must be 2-80 chars using letters, numbers, dot, dash, underscore, or colon")
        node_key = f"inventory:{candidate}"
        normalized_tags = self._parse_tags(tags)
        with self.database.session() as session:
            row = session.scalar(select(FleetNodeRecord).where(FleetNodeRecord.node_key == node_key))
            if row is None:
                row = FleetNodeRecord(node_key=node_key, node_name=candidate, local=False, source="inventory")
                session.add(row)
                row.created_at = utcnow()
            row.node_name = candidate
            row.display_name = display_name or candidate
            row.group_name = group_name or None
            row.tags_json = json.dumps(normalized_tags, ensure_ascii=False)
            row.version = (version or "unknown").strip() or "unknown"
            row.health_status = health_status
            row.runtime_status = runtime_status
            row.uptime_seconds = max(0, int(uptime_seconds or 0))
            row.dashboard_url = self._normalize_dashboard_url(dashboard_url)
            row.region = region or None
            row.notes = notes or None
            row.local = False
            row.source = "inventory"
            row.last_seen_at = utcnow()
            row.updated_at = utcnow()
            session.flush()
            payload = self._serialize_node(row)
        self.database.record_event(
            "fleet.node_saved",
            f"fleet node {candidate} saved",
            source="fleet_service",
            payload={"node_name": candidate, "group_name": payload.get("group_name"), "tags": payload.get("tags")},
        )
        return payload

    async def list_groups(self) -> list[dict[str, Any]]:
        nodes = await self.list_nodes()
        counts: dict[str, int] = {}
        for node in nodes:
            group_name = node.get("group_name")
            if group_name:
                counts[str(group_name)] = counts.get(str(group_name), 0) + 1
        with self.database.session() as session:
            rows = session.scalars(select(NodeGroupRecord).order_by(NodeGroupRecord.name.asc())).all()
        return [self._serialize_group(row, counts.get(row.name, 0)) for row in rows]

    def create_group(self, *, name: str, description: str | None = None, group_type: str = "custom") -> dict[str, Any]:
        candidate = name.strip()
        if not NAME_PATTERN.match(candidate):
            raise ValueError("group name must be 2-80 chars using letters, numbers, dot, dash, underscore, or colon")
        with self.database.session() as session:
            row = session.scalar(select(NodeGroupRecord).where(NodeGroupRecord.name == candidate))
            if row is None:
                row = NodeGroupRecord(name=candidate)
                session.add(row)
                row.created_at = utcnow()
            row.description = description or None
            row.group_type = (group_type or "custom").strip() or "custom"
            row.updated_at = utcnow()
            session.flush()
            payload = self._serialize_group(row, 0)
        self.database.record_event(
            "fleet.group_saved",
            f"fleet group {candidate} saved",
            source="fleet_service",
            payload={"group_name": candidate, "group_type": payload.get("group_type")},
        )
        return payload

    async def list_templates(self) -> list[dict[str, Any]]:
        nodes = await self.list_nodes()
        by_group: dict[str, list[str]] = {}
        for node in nodes:
            group_name = str(node.get("group_name") or "").strip()
            if group_name:
                by_group.setdefault(group_name, []).append(node["node_name"])
        with self.database.session() as session:
            rows = session.scalars(select(ConfigTemplateRecord).order_by(ConfigTemplateRecord.name.asc())).all()
        payloads: list[dict[str, Any]] = []
        for row in rows:
            target_nodes = json.loads(row.target_nodes_json or "[]")
            applied = sorted(set(target_nodes + by_group.get(row.target_group or "", [])))
            payloads.append(self._serialize_template(row, applied))
        return payloads

    def create_template(
        self,
        *,
        name: str,
        description: str | None = None,
        template_text: str,
        target_group: str | None = None,
        target_nodes: list[str] | str | None = None,
    ) -> dict[str, Any]:
        candidate = name.strip()
        if not NAME_PATTERN.match(candidate):
            raise ValueError("template name must be 2-80 chars using letters, numbers, dot, dash, underscore, or colon")
        normalized_nodes = self._parse_tags(target_nodes)
        with self.database.session() as session:
            row = session.scalar(select(ConfigTemplateRecord).where(ConfigTemplateRecord.name == candidate))
            if row is None:
                row = ConfigTemplateRecord(name=candidate, template_text=template_text)
                session.add(row)
                row.created_at = utcnow()
            row.description = description or None
            row.template_text = template_text.strip()
            row.target_group = target_group or None
            row.target_nodes_json = json.dumps(normalized_nodes, ensure_ascii=False)
            row.updated_at = utcnow()
            session.flush()
            payload = self._serialize_template(row, normalized_nodes)
        self.database.record_event(
            "fleet.template_saved",
            f"fleet template {candidate} saved",
            source="fleet_service",
            payload={"template_name": candidate, "target_group": payload.get("target_group"), "target_nodes": payload.get("target_nodes")},
        )
        return payload

    async def dashboard(self) -> dict[str, Any]:
        nodes = await self.list_nodes()
        total = len(nodes)
        online = sum(1 for node in nodes if node.get("runtime_status") == "running")
        degraded = sum(1 for node in nodes if node.get("health_status") == "warning")
        critical = sum(1 for node in nodes if node.get("health_status") == "critical")
        offline = total - online
        version_distribution: dict[str, int] = {}
        group_summary: dict[str, int] = {}
        for node in nodes:
            version = str(node.get("version") or "unknown")
            group_name = str(node.get("group_name") or "ungrouped")
            version_distribution[version] = version_distribution.get(version, 0) + 1
            group_summary[group_name] = group_summary.get(group_name, 0) + 1
        alerts: list[dict[str, Any]] = []
        for entry in self.database.list_events(limit=120):
            if entry.get("severity") not in {"warning", "error", "critical"}:
                continue
            alerts.append(
                {
                    "event_type": entry.get("event_type"),
                    "severity": entry.get("severity"),
                    "message": entry.get("message"),
                    "created_at": entry.get("created_at"),
                }
            )
            if len(alerts) >= 6:
                break
        return {
            "total_nodes": total,
            "online": online,
            "offline": offline,
            "degraded": degraded,
            "critical": critical,
            "recent_alerts": alerts,
            "version_distribution": [{"version": key, "count": value} for key, value in sorted(version_distribution.items())],
            "group_summary": [{"group_name": key, "count": value} for key, value in sorted(group_summary.items())],
            "nodes": nodes,
        }

    async def get_node(self, node_name: str) -> dict[str, Any] | None:
        candidate = node_name.strip()
        if not candidate:
            return None
        nodes = await self.list_nodes()
        node = next((item for item in nodes if str(item.get("node_name") or "") == candidate), None)
        if node is None:
            return None
        templates = [
            template
            for template in await self.list_templates()
            if candidate in list(template.get("applied_nodes") or [])
        ]
        recent_events: list[dict[str, Any]] = []
        for event in self.database.list_events(limit=160):
            decorated = self._decorate_event(event)
            related_nodes = set(decorated.get("nodes") or [])
            if candidate not in related_nodes:
                continue
            recent_events.append(decorated)
            if len(recent_events) >= 12:
                break
        return {
            **node,
            "templates": templates,
            "recent_events": recent_events,
        }

    async def list_tags(self) -> list[dict[str, Any]]:
        nodes = await self.list_nodes()
        tag_map: dict[str, list[str]] = {}
        for node in nodes:
            node_name = str(node.get("node_name") or "")
            for tag in list(node.get("tags") or []):
                tag_map.setdefault(str(tag), []).append(node_name)
        return [
            {"name": tag, "count": len(sorted(set(node_names))), "nodes": sorted(set(node_names))}
            for tag, node_names in sorted(tag_map.items(), key=lambda item: item[0])
        ]

    async def health_view(self) -> dict[str, Any]:
        nodes = await self.list_nodes()
        groups = await self.list_groups()
        at_risk = [
            node for node in nodes
            if node.get("health_status") != "healthy" or node.get("runtime_status") != "running"
        ]
        summary = {
            "total_nodes": len(nodes),
            "healthy": sum(1 for node in nodes if node.get("health_status") == "healthy"),
            "warning": sum(1 for node in nodes if node.get("health_status") == "warning"),
            "critical": sum(1 for node in nodes if node.get("health_status") == "critical"),
            "running": sum(1 for node in nodes if node.get("runtime_status") == "running"),
            "offline": sum(1 for node in nodes if node.get("runtime_status") != "running"),
            "at_risk": len(at_risk),
        }
        group_rows: list[dict[str, Any]] = []
        for group in groups:
            group_name = str(group.get("name") or "")
            members = [node for node in nodes if str(node.get("group_name") or "") == group_name]
            group_rows.append(
                {
                    **group,
                    "healthy": sum(1 for node in members if node.get("health_status") == "healthy"),
                    "warning": sum(1 for node in members if node.get("health_status") == "warning"),
                    "critical": sum(1 for node in members if node.get("health_status") == "critical"),
                    "running": sum(1 for node in members if node.get("runtime_status") == "running"),
                    "members": members,
                }
            )
        return {
            "summary": summary,
            "at_risk": at_risk,
            "groups": group_rows,
        }

    async def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        nodes = await self.list_nodes()
        known_names = {str(node.get("node_name") or "") for node in nodes}
        entries: list[dict[str, Any]] = []
        for event in self.database.list_events(limit=max(limit * 4, 120)):
            decorated = self._decorate_event(event)
            related_nodes = set(decorated.get("nodes") or [])
            related_group = decorated.get("group_name")
            if event.get("source") not in FLEET_EVENT_SOURCES and not (known_names.intersection(related_nodes) or related_group):
                continue
            entries.append(decorated)
            if len(entries) >= limit:
                break
        return entries
