from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hearth.core.config import HearthSettings
from hearth.services.fleet_service import FleetService
from hearth.storage.db import Database


class RemoteLogService:
    def __init__(self, settings: HearthSettings, database: Database, fleet_service: FleetService) -> None:
        self.settings = settings
        self.database = database
        self.fleet_service = fleet_service

    def _severity_for_node(self, node: dict[str, Any]) -> str:
        runtime = str(node.get("runtime_status") or "offline")
        health = str(node.get("health_status") or "warning")
        if health == "critical" or runtime in {"crashed", "error"}:
            return "critical"
        if health in {"warning", "degraded"} or runtime in {"offline", "stopped"}:
            return "warning"
        return "info"

    def _sort_key(self, value: str | None) -> float:
        if not value:
            return 0.0
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return 0.0
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).timestamp()

    def _node_log_path(self, node_name: str) -> Path:
        safe_name = "".join(character if character.isalnum() or character in {"-", "_", "."} else "_" for character in node_name)
        return self.settings.remote_logs_dir / f"{safe_name}.json"

    def _stored_node_names(self) -> list[str]:
        directory = self.settings.remote_logs_dir
        if not directory.exists():
            return []
        names: set[str] = set()
        for path in directory.glob("*.json"):
            if path.is_file():
                names.add(path.stem)
        return sorted(names)

    def _read_node_entries(self, node_name: str) -> list[dict[str, Any]]:
        path = self._node_log_path(node_name)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _write_node_entries(self, node_name: str, entries: list[dict[str, Any]]) -> None:
        path = self._node_log_path(node_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def ingest_entries(self, *, node_name: str, entries: list[dict[str, Any]], origin: str = "push") -> dict[str, Any]:
        existing = self._read_node_entries(node_name)
        fingerprints = {
            f"{item.get('created_at')}|{item.get('source')}|{item.get('message')}"
            for item in existing
        }
        merged = list(existing)
        accepted = 0
        for item in entries:
            created_at = str(item.get("created_at") or datetime.now(timezone.utc).isoformat())
            source = str(item.get("source") or "remote")
            message = str(item.get("message") or "")
            fingerprint = f"{created_at}|{source}|{message}"
            if fingerprint in fingerprints:
                continue
            merged.append(
                {
                    "id": item.get("id"),
                    "event_type": item.get("event_type") or "remote.log",
                    "severity": item.get("severity") or "info",
                    "source": source,
                    "message": message,
                    "payload": item.get("payload") if isinstance(item.get("payload"), dict) else {},
                    "created_at": created_at,
                    "node_name": node_name,
                    "origin": origin,
                }
            )
            fingerprints.add(fingerprint)
            accepted += 1
        merged.sort(key=lambda item: self._sort_key(str(item.get("created_at") or "")), reverse=True)
        self._write_node_entries(node_name, merged[:2000])
        self.database.record_event(
            "remote_logs.ingested",
            f"ingested {accepted} remote log entries for {node_name}",
            source="remote_log_service",
            payload={"node_name": node_name, "accepted": accepted, "origin": origin},
        )
        return {"ingested": accepted, "node_name": node_name, "origin": origin}

    async def sync_nodes(self, *, limit: int = 100) -> dict[str, Any]:
        fleet_nodes = await self.fleet_service.list_nodes()
        results: list[dict[str, Any]] = []
        total = 0
        for node in fleet_nodes:
            if bool(node.get("local")) or not node.get("dashboard_url"):
                continue
            result = await self.fleet_service.dispatch_remote_request(
                node_name=str(node.get("node_name") or ""),
                method="GET",
                api_path=f"/logs?limit={max(limit, 1)}",
                timeout=10,
            )
            response = result.get("response") if isinstance(result.get("response"), dict) else {}
            entries = response.get("items") if isinstance(response.get("items"), list) else []
            ingest_result = self.ingest_entries(
                node_name=str(node.get("node_name") or ""),
                entries=entries,
                origin="pull",
            )
            total += int(ingest_result.get("ingested") or 0)
            results.append({**result, **ingest_result})
        return {"synced": True, "ingested": total, "results": results}

    async def list_entries(self, *, node_name: str | None = None, level: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        fleet_nodes = await self.fleet_service.list_nodes()
        entries: list[dict[str, Any]] = []
        local_name = self.settings.system.node_name
        fleet_index = {
            str(node.get("node_name") or ""): node
            for node in fleet_nodes
            if str(node.get("node_name") or "")
        }
        for event in self.database.list_events(limit=max(limit * 3, 50)):
            severity = str(event.get("severity") or "info")
            if level and severity != level:
                continue
            entries.append({**event, "node_name": local_name, "origin": "local"})

        remote_names = {
            name
            for name, node in fleet_index.items()
            if not bool(node.get("local"))
        }
        remote_names.update(self._stored_node_names())
        if node_name and node_name != local_name:
            remote_names.add(node_name)

        for current_name in sorted(remote_names):
            if node_name and current_name != node_name:
                continue
            node = fleet_index.get(current_name)
            if node and bool(node.get("local")):
                continue
            for item in self._read_node_entries(current_name):
                severity = str(item.get("severity") or "info")
                if level and severity != level:
                    continue
                entries.append(item)
            if node is not None:
                severity = self._severity_for_node(node)
                if level and severity != level:
                    continue
                entries.append(
                    {
                        "id": None,
                        "event_type": "fleet.status",
                        "severity": severity,
                        "source": "fleet_inventory",
                        "message": f"{current_name} runtime={node.get('runtime_status')} health={node.get('health_status')}",
                        "payload": {
                            "group_name": node.get("group_name"),
                            "dashboard_url": node.get("dashboard_url"),
                            "region": node.get("region"),
                        },
                        "created_at": node.get("last_seen_at") or node.get("updated_at"),
                        "node_name": current_name,
                        "origin": "inventory",
                    }
                )
        if node_name:
            entries = [item for item in entries if str(item.get("node_name") or "") == node_name]
        entries.sort(key=lambda item: self._sort_key(str(item.get("created_at") or "")), reverse=True)
        return entries[:limit]
