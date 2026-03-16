from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from hearth.core.config import HearthSettings
from hearth.storage.db import Database


class AlertService:
    ALERT_EVENT_TYPES = {"alert.activated", "alert.resolved", "alert.hook_delivered", "alert.hook_failed"}

    def __init__(self, settings: HearthSettings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _now_iso(self) -> str:
        return self._now().isoformat()

    def _fingerprint(self, alert: dict[str, Any]) -> str:
        payload = {
            "category": alert.get("category"),
            "source": alert.get("source"),
            "title": alert.get("title"),
            "message": alert.get("message"),
            "rule_source": alert.get("rule_source"),
        }
        return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    def _normalize_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(alert)
        normalized["fingerprint"] = self._fingerprint(normalized)
        normalized["created_at"] = str(normalized.get("created_at") or self._now_iso())
        normalized["rule_source"] = str(normalized.get("rule_source") or normalized.get("category") or "alert_rule")
        return normalized

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _alert_history_events(self, limit: int | None = 500) -> list[dict[str, Any]]:
        rows = self.database.list_events(limit=limit)
        return [item for item in rows if str(item.get("event_type") or "") in self.ALERT_EVENT_TYPES]

    def _latest_activation_payloads(self) -> dict[str, dict[str, Any]]:
        payloads: dict[str, dict[str, Any]] = {}
        for item in self._alert_history_events(limit=1000):
            if str(item.get("event_type") or "") != "alert.activated":
                continue
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            fingerprint = str(payload.get("fingerprint") or "")
            if fingerprint and fingerprint not in payloads:
                payloads[fingerprint] = payload
        return payloads

    def _active_fingerprint_state(self) -> dict[str, bool]:
        state: dict[str, bool] = {}
        for item in self._alert_history_events(limit=1000):
            event_type = str(item.get("event_type") or "")
            if event_type not in {"alert.activated", "alert.resolved"}:
                continue
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            fingerprint = str(payload.get("fingerprint") or "")
            if not fingerprint or fingerprint in state:
                continue
            state[fingerprint] = event_type == "alert.activated"
        return state

    def build_alerts(self, summary: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        runtime_status = str(summary.get("runtime_status") or "unknown")
        health_status = str(summary.get("health_status") or "unknown")
        if runtime_status != "running":
            alerts.append(
                {
                    "severity": "critical",
                    "source": "runtime",
                    "category": "runtime",
                    "rule_source": "runtime_status",
                    "title": "Reticulum runtime is not running",
                    "message": f"Current runtime status is {runtime_status}.",
                    "created_at": self._now_iso(),
                }
            )
        elif health_status in {"warning", "degraded", "critical"}:
            alerts.append(
                {
                    "severity": "critical" if health_status == "critical" else "warning",
                    "source": "health",
                    "category": "health",
                    "rule_source": "node_health",
                    "title": "Node health needs attention",
                    "message": f"Current health status is {health_status}.",
                    "created_at": self._now_iso(),
                }
            )
        for issue in summary.get("issues", [])[:6]:
            alerts.append(
                {
                    "severity": "warning",
                    "source": "health",
                    "category": "issue",
                    "rule_source": "health_issues",
                    "title": "Health issue detected",
                    "message": str(issue),
                    "created_at": self._now_iso(),
                }
            )
        for interface in summary.get("interfaces", []):
            if not interface.get("enabled"):
                continue
            if interface.get("status") in {"stopped", "error", "crashed"}:
                alerts.append(
                    {
                        "severity": "warning",
                        "source": "interface",
                        "category": "interface",
                        "rule_source": "interface_runtime",
                        "title": f"Interface {interface['name']} is not running",
                        "message": f"Status is {interface.get('status')} with health {interface.get('health_status')}.",
                        "created_at": interface.get("last_seen_at") or self._now_iso(),
                    }
                )
        maintenance = summary.get("maintenance") or self.database.get_maintenance_state()
        if maintenance.get("enabled"):
            alerts.append(
                {
                    "severity": "warning",
                    "source": "maintenance",
                    "category": "maintenance",
                    "rule_source": "maintenance_mode",
                    "title": "Maintenance mode is enabled",
                    "message": str(maintenance.get("reason") or "Automatic recovery is currently paused."),
                    "created_at": maintenance.get("updated_at") or self._now_iso(),
                }
            )
        configured_token = self.settings.security.admin_token.strip()
        if configured_token in {"", "change-me"}:
            alerts.append(
                {
                    "severity": "warning",
                    "source": "security",
                    "category": "security",
                    "rule_source": "security_policy",
                    "title": "Admin token is unsafe",
                    "message": "The admin token is missing or still using the default value.",
                    "created_at": self._now_iso(),
                }
            )
        if self.settings.security.allow_wan:
            alerts.append(
                {
                    "severity": "warning",
                    "source": "security",
                    "category": "security",
                    "rule_source": "security_policy",
                    "title": "WAN management is enabled",
                    "message": "Confirm reverse-proxy and token protections before exposing management remotely.",
                    "created_at": self._now_iso(),
                }
            )
        if self.settings.web.auth_mode == "none":
            alerts.append(
                {
                    "severity": "critical",
                    "source": "security",
                    "category": "security",
                    "rule_source": "security_policy",
                    "title": "Authentication is disabled",
                    "message": "Management endpoints are open to allowed network origins.",
                    "created_at": self._now_iso(),
                }
            )
        recent_events = self.database.list_events(limit=80)
        for entry in recent_events:
            severity = str(entry.get("severity") or "").lower()
            if severity not in {"warning", "error", "critical"}:
                continue
            alerts.append(
                {
                    "severity": severity if severity != "error" else "critical",
                    "source": entry.get("source") or "event",
                    "category": "event",
                    "rule_source": "event_stream",
                    "title": str(entry.get("event_type") or "event"),
                    "message": str(entry.get("message") or ""),
                    "created_at": entry.get("created_at") or self._now_iso(),
                }
            )
            if len(alerts) >= 24:
                break
        normalized = [self._normalize_alert(alert) for alert in alerts]
        unique_alerts: list[dict[str, Any]] = []
        seen = set()
        for alert in normalized:
            fingerprint = str(alert.get("fingerprint") or "")
            if not fingerprint or fingerprint in seen:
                continue
            seen.add(fingerprint)
            unique_alerts.append(alert)
        return unique_alerts

    def summarize(self, alerts: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(alerts),
            "critical": sum(1 for alert in alerts if alert.get("severity") == "critical"),
            "warning": sum(1 for alert in alerts if alert.get("severity") == "warning"),
            "healthy": 0 if alerts else 1,
        }

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in self._alert_history_events(limit=limit * 4):
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            event_type = str(item.get("event_type") or "")
            row = {
                "id": item.get("id"),
                "event_type": event_type,
                "severity": item.get("severity"),
                "source": item.get("source"),
                "created_at": item.get("created_at"),
                "fingerprint": payload.get("fingerprint"),
                "title": payload.get("title") or item.get("message"),
                "message": payload.get("message") or item.get("message"),
                "rule_source": payload.get("rule_source"),
                "transition": payload.get("transition") or event_type.split(".")[-1],
                "endpoint": payload.get("endpoint"),
                "status_code": payload.get("status_code"),
                "error": payload.get("error"),
            }
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows

    def hook_status(self) -> dict[str, Any]:
        latest_delivery = None
        for item in self._alert_history_events(limit=200):
            event_type = str(item.get("event_type") or "")
            if event_type not in {"alert.hook_delivered", "alert.hook_failed"}:
                continue
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            latest_delivery = {
                "event_type": event_type,
                "severity": item.get("severity"),
                "created_at": item.get("created_at"),
                "endpoint": payload.get("endpoint"),
                "status_code": payload.get("status_code"),
                "error": payload.get("error"),
                "transition": payload.get("transition"),
                "fingerprint": payload.get("fingerprint"),
            }
            break
        return {
            "enabled": bool(self.settings.alerts.webhook_enabled and self.settings.alerts.webhook_url),
            "webhook_url": self.settings.alerts.webhook_url,
            "include_resolved": self.settings.alerts.include_resolved,
            "delivery_timeout_sec": self.settings.alerts.delivery_timeout_sec,
            "last_delivery": latest_delivery,
        }

    def _webhook_is_enabled(self) -> bool:
        return bool(self.settings.alerts.webhook_enabled and str(self.settings.alerts.webhook_url or "").strip())

    def _deliver_webhook_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib_request.Request(
            str(self.settings.alerts.webhook_url),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "Hearth/alerts"},
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=max(int(self.settings.alerts.delivery_timeout_sec), 1)) as response:
            body = response.read(4096).decode("utf-8", errors="ignore")
            return {"status_code": getattr(response, "status", response.getcode()), "body": body}

    async def _deliver_transition(self, transition: str, alert: dict[str, Any]) -> None:
        if not self._webhook_is_enabled():
            return
        if transition == "resolved" and not self.settings.alerts.include_resolved:
            return
        payload = {
            "sent_at": self._now_iso(),
            "node_name": self.settings.system.node_name,
            "transition": transition,
            "alert": alert,
        }
        endpoint = str(self.settings.alerts.webhook_url or "")
        try:
            response = await asyncio.to_thread(self._deliver_webhook_sync, payload)
            self.database.record_event(
                "alert.hook_delivered",
                f"alert webhook delivered for {alert.get('fingerprint')}",
                source="alert_hook",
                payload={
                    "fingerprint": alert.get("fingerprint"),
                    "transition": transition,
                    "endpoint": endpoint,
                    "status_code": response.get("status_code"),
                },
            )
        except (OSError, urllib_error.URLError, urllib_error.HTTPError, ValueError) as exc:
            self.database.record_event(
                "alert.hook_failed",
                f"alert webhook failed for {alert.get('fingerprint')}",
                severity="warning",
                source="alert_hook",
                payload={
                    "fingerprint": alert.get("fingerprint"),
                    "transition": transition,
                    "endpoint": endpoint,
                    "error": str(exc),
                },
            )

    async def refresh(self, summary: dict[str, Any]) -> dict[str, Any]:
        alerts = self.build_alerts(summary)
        active_map = self._active_fingerprint_state()
        current_fingerprints = {str(alert.get("fingerprint") or "") for alert in alerts}
        current_fingerprints.discard("")

        for alert in alerts:
            fingerprint = str(alert.get("fingerprint") or "")
            if not fingerprint or active_map.get(fingerprint) is True:
                continue
            self.database.record_event(
                "alert.activated",
                f"alert activated: {alert.get('title')}",
                severity=str(alert.get("severity") or "warning"),
                source="alert_service",
                payload={**alert, "transition": "activated"},
            )
            await self._deliver_transition("activated", alert)

        activation_payloads = self._latest_activation_payloads()
        for fingerprint, is_active in active_map.items():
            if not is_active or fingerprint in current_fingerprints:
                continue
            previous = activation_payloads.get(fingerprint) or {"fingerprint": fingerprint, "title": "resolved alert"}
            resolved_payload = {
                **previous,
                "transition": "resolved",
                "resolved_at": self._now_iso(),
            }
            self.database.record_event(
                "alert.resolved",
                f"alert resolved: {previous.get('title')}",
                source="alert_service",
                payload=resolved_payload,
            )
            await self._deliver_transition("resolved", resolved_payload)

        return {
            "summary": self.summarize(alerts),
            "alerts": alerts,
            "history": self.history(limit=50),
            "hooks": self.hook_status(),
            "rule_sources": sorted({str(alert.get("rule_source") or "") for alert in alerts if alert.get("rule_source")}),
        }
