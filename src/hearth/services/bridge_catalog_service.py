from __future__ import annotations

from time import perf_counter
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
import json

from hearth.services.plugin_service import PluginService
from hearth.storage.db import Database


BRIDGE_DEFINITIONS = [
    {
        "name": "matrix_bridge",
        "label": "Matrix Bridge",
        "transport": "matrix",
        "plugin_names": ["matrix_bridge", "matrix-bridge"],
        "summary": "Bridge Reticulum traffic into Matrix rooms and homeservers.",
    },
    {
        "name": "mqtt_bridge",
        "label": "MQTT Bridge",
        "transport": "mqtt",
        "plugin_names": ["mqtt_bridge", "mqtt-bridge"],
        "summary": "Bridge telemetry and events into MQTT topics.",
    },
    {
        "name": "webhook_bridge",
        "label": "Webhook Bridge",
        "transport": "webhook",
        "plugin_names": ["webhook_bridge", "webhook-bridge"],
        "summary": "Deliver selected events to HTTP webhook endpoints.",
    },
]


class BridgeCatalogService:
    def __init__(self, plugin_service: PluginService, database: Database) -> None:
        self.plugin_service = plugin_service
        self.database = database

    def _match_plugin(self, plugin_names: list[str]) -> dict[str, Any] | None:
        plugins = self.plugin_service.list_plugins()
        for plugin in plugins:
            plugin_name = str(plugin.get("name") or "")
            if plugin_name in plugin_names:
                return plugin
        for plugin in plugins:
            if str(plugin.get("type") or "").lower() != "bridge":
                continue
            plugin_name = str(plugin.get("name") or "")
            if any(name.split("_")[0] in plugin_name for name in plugin_names):
                return plugin
        return None

    def _status_for_bridge(self, enabled: bool, runtime_status: str) -> tuple[str, str]:
        status = "running" if enabled and runtime_status == "running" else "idle" if enabled else "disabled"
        health = "healthy" if status == "running" else "warning" if enabled else "disabled"
        return status, health

    def _endpoint_for_config(self, config: dict[str, Any]) -> str:
        return str(config.get("endpoint") or config.get("url") or config.get("server") or config.get("topic") or "-")

    def _actions_for_bridge(self, configured: bool, enabled: bool) -> list[str]:
        actions = ["sync"]
        if configured:
            actions.insert(0, "disable" if enabled else "enable")
            actions.append("test_delivery")
        return actions

    def _transport_configuration_check(self, transport: str, config: dict[str, Any]) -> tuple[str, str]:
        if transport == "matrix":
            if str(config.get("server") or config.get("url") or "").strip():
                return "healthy", "Matrix homeserver is configured."
            return "error", "Matrix homeserver is missing."
        if transport == "mqtt":
            has_server = bool(str(config.get("server") or "").strip())
            has_topic = bool(str(config.get("topic") or config.get("endpoint") or "").strip())
            if has_server and has_topic:
                return "healthy", "MQTT broker and topic are configured."
            if has_server or has_topic:
                return "warning", "MQTT bridge is partially configured."
            return "error", "MQTT broker or topic is missing."
        if transport == "webhook":
            if str(config.get("url") or config.get("endpoint") or "").strip():
                return "healthy", "Webhook endpoint is configured."
            return "error", "Webhook endpoint is missing."
        return "warning", "Bridge transport configuration could not be validated."

    def _health_checks_for_bridge(self, bridge: dict[str, Any]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        configured = bool(bridge.get("configured"))
        enabled = bool(bridge.get("enabled"))
        source_details = dict(bridge.get("source_details") or {})
        endpoint = str(bridge.get("endpoint") or "-")
        transport_status, transport_detail = self._transport_configuration_check(str(bridge.get("transport") or ""), dict(bridge.get("config") or {}))
        signature_status = str(source_details.get("signature_status") or "not_required")
        if signature_status in {"verified", "trusted"}:
            source_status = "healthy"
            source_detail = "Source trust and signature checks passed."
        elif signature_status == "missing":
            source_status = "warning"
            source_detail = "A signature is required but was not present."
        elif signature_status == "invalid":
            source_status = "error"
            source_detail = str(source_details.get("sync_error") or "Source signature validation failed.")
        elif signature_status == "not_required" and configured:
            source_status = "warning"
            source_detail = "Source verification has not been completed yet."
        else:
            source_status = "disabled"
            source_detail = "Bridge source verification is not required."
        checks.append(
            {
                "name": "plugin_enabled",
                "status": "healthy" if enabled else ("disabled" if configured else "warning"),
                "detail": "Bridge plugin is enabled." if enabled else ("Bridge plugin is currently disabled." if configured else "Bridge plugin is not configured."),
            }
        )
        checks.append(
            {
                "name": "runtime_ready",
                "status": "healthy" if bridge.get("status") == "running" else ("warning" if enabled else "disabled"),
                "detail": "Reticulum runtime is available for bridge delivery."
                if bridge.get("status") == "running"
                else ("Runtime is not active enough for live delivery." if enabled else "Bridge runtime is disabled."),
            }
        )
        checks.append({"name": "source_trust", "status": source_status, "detail": source_detail})
        checks.append(
            {
                "name": "endpoint_configured",
                "status": "healthy" if endpoint != "-" else ("error" if configured else "disabled"),
                "detail": "A delivery endpoint is configured." if endpoint != "-" else "No delivery endpoint is configured.",
            }
        )
        checks.append({"name": "transport_config", "status": transport_status, "detail": transport_detail})
        return checks

    def _recent_operations_for_bridge(self, bridge_name: str, plugin_name: str, *, limit: int = 8) -> list[dict[str, Any]]:
        recent = self.database.list_events(limit=max(limit * 8, 40), source="bridge_service")
        operations: list[dict[str, Any]] = []
        for event in recent:
            payload = dict(event.get("payload") or {})
            if payload.get("bridge") not in {bridge_name, plugin_name} and payload.get("plugin_name") != plugin_name:
                continue
            operations.append(
                {
                    "created_at": event.get("created_at"),
                    "action": str(payload.get("action") or "sync"),
                    "status": str(payload.get("status") or "warning"),
                    "message": str(event.get("message") or "Bridge action recorded."),
                    "detail": payload.get("detail"),
                    "result": payload.get("result") or {},
                }
            )
            if len(operations) >= limit:
                break
        return operations

    def _record_operation(
        self,
        *,
        bridge_name: str,
        plugin_name: str,
        action: str,
        status: str,
        message: str,
        detail: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        severity = "info" if status in {"healthy", "success"} else "warning" if status == "warning" else "error"
        self.database.record_event(
            event_type=f"bridge.{action}",
            message=message,
            severity=severity,
            source="bridge_service",
            payload={
                "bridge": bridge_name,
                "plugin_name": plugin_name,
                "action": action,
                "status": status,
                "detail": detail,
                "result": result or {},
            },
        )

    def _build_test_payload(self, bridge: dict[str, Any]) -> dict[str, Any]:
        return {
            "sent_at": self.plugin_service._now_iso(),
            "node_name": self.plugin_service.settings.system.node_name,
            "bridge": bridge.get("name"),
            "plugin_name": bridge.get("plugin_name"),
            "transport": bridge.get("transport"),
            "mode": bridge.get("mode"),
            "test": True,
            "message": f"Hearth test delivery for {bridge.get('name')}",
        }

    def _perform_webhook_delivery_test(self, bridge: dict[str, Any]) -> dict[str, Any]:
        endpoint = str(bridge.get("config", {}).get("url") or bridge.get("config", {}).get("endpoint") or "").strip()
        if not endpoint:
            return {
                "status": "error",
                "message": "Webhook delivery test failed.",
                "detail": "Webhook endpoint is missing.",
                "result": {"transport": "webhook", "mode": "live", "endpoint": None},
            }
        timeout_seconds = max(int(bridge.get("config", {}).get("timeout_sec") or self.plugin_service.settings.alerts.delivery_timeout_sec or 5), 1)
        payload = self._build_test_payload(bridge)
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "Hearth/bridge-test"},
            method="POST",
        )
        start = perf_counter()
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read(4096).decode("utf-8", errors="ignore")
                duration_ms = int((perf_counter() - start) * 1000)
                return {
                    "status": "healthy",
                    "message": "Webhook delivery test succeeded.",
                    "detail": f"Delivered test payload to {endpoint}.",
                    "result": {
                        "transport": "webhook",
                        "mode": "live",
                        "endpoint": endpoint,
                        "status_code": getattr(response, "status", response.getcode()),
                        "duration_ms": duration_ms,
                        "body": body,
                    },
                }
        except (OSError, urllib_error.URLError, urllib_error.HTTPError, ValueError) as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            return {
                "status": "error",
                "message": "Webhook delivery test failed.",
                "detail": str(exc),
                "result": {
                    "transport": "webhook",
                    "mode": "live",
                    "endpoint": endpoint,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            }

    def _perform_delivery_test(self, bridge: dict[str, Any]) -> dict[str, Any]:
        transport = str(bridge.get("transport") or "bridge").lower()
        if transport == "webhook":
            return self._perform_webhook_delivery_test(bridge)
        endpoint = str(bridge.get("endpoint") or "-")
        detail = "Delivery endpoint is not configured." if endpoint == "-" else f"{transport.title()} delivery test currently validates configuration only."
        status = "warning" if endpoint != "-" else "error"
        return {
            "status": status,
            "message": f"{transport.title()} delivery test simulated.",
            "detail": detail,
            "result": {
                "transport": transport,
                "mode": "simulated",
                "endpoint": None if endpoint == "-" else endpoint,
                "supported": transport == "webhook",
            },
        }

    def _build_bridge_entry(
        self,
        *,
        bridge_name: str,
        label: str,
        transport: str,
        summary_text: str,
        plugin: dict[str, Any] | None,
        runtime_status: str,
    ) -> dict[str, Any]:
        plugin_name = str(plugin.get("name") or bridge_name) if plugin else bridge_name
        enabled = bool(plugin.get("enabled")) if plugin else False
        config = dict(plugin.get("config") or {}) if plugin else {}
        status, health = self._status_for_bridge(enabled, runtime_status)
        source_name = str(plugin.get("source") or "catalog") if plugin else "catalog"
        source_details = self.plugin_service.get_source(source_name)
        bridge = {
            "name": bridge_name,
            "label": label,
            "plugin_name": plugin_name,
            "configured": plugin is not None,
            "enabled": enabled,
            "status": status,
            "health": health,
            "transport": transport,
            "summary": str(plugin.get("description") or summary_text) if plugin else summary_text,
            "source": source_name,
            "endpoint": self._endpoint_for_config(config),
            "mode": str(config.get("mode") or "bridge"),
            "actions": self._actions_for_bridge(plugin is not None, enabled),
            "permissions": list(plugin.get("permissions") or []) if plugin else [],
            "dependencies": list(plugin.get("depends_on") or []) if plugin else [],
            "config": config,
            "diagnostics": dict(plugin.get("diagnostics") or {}) if plugin else {},
            "plugin": plugin,
            "source_details": source_details,
        }
        bridge["health_checks"] = self._health_checks_for_bridge(bridge)
        bridge["recent_operations"] = self._recent_operations_for_bridge(bridge_name, plugin_name)
        return bridge

    def list_bridges(self, runtime_status: str) -> list[dict[str, Any]]:
        bridges: list[dict[str, Any]] = []
        seen_plugins: set[str] = set()
        for definition in BRIDGE_DEFINITIONS:
            plugin = self._match_plugin(definition["plugin_names"])
            if plugin:
                seen_plugins.add(str(plugin.get("name") or definition["name"]))
            bridges.append(
                self._build_bridge_entry(
                    bridge_name=definition["name"],
                    label=definition["label"],
                    transport=definition["transport"],
                    summary_text=definition["summary"],
                    plugin=plugin,
                    runtime_status=runtime_status,
                )
            )

        for plugin in self.plugin_service.list_plugins():
            if str(plugin.get("type") or "").lower() != "bridge":
                continue
            plugin_name = str(plugin.get("name") or "")
            if plugin_name in seen_plugins:
                continue
            config = dict(plugin.get("config") or {})
            bridges.append(
                self._build_bridge_entry(
                    bridge_name=plugin_name,
                    label=plugin_name.replace("_", " ").title(),
                    transport=str(config.get("transport") or "bridge"),
                    summary_text=str(plugin.get("description") or "Custom bridge plugin"),
                    plugin=plugin,
                    runtime_status=runtime_status,
                )
            )
        return bridges

    def get_bridge(self, name: str, runtime_status: str) -> dict[str, Any] | None:
        candidate = name.strip().lower()
        for bridge in self.list_bridges(runtime_status):
            if bridge["name"].lower() == candidate or bridge["plugin_name"].lower() == candidate:
                return bridge
        return None

    def control(self, name: str, action: str, runtime_status: str) -> dict[str, Any]:
        bridge = self.get_bridge(name, runtime_status)
        if bridge is None:
            raise LookupError("bridge not found")

        normalized = action.strip().lower()
        if normalized == "sync":
            refresh_result = self.plugin_service.refresh_sources()
            refreshed_bridge = self.get_bridge(name, runtime_status) or bridge
            response = {
                "bridge": refreshed_bridge["name"],
                "plugin_name": refreshed_bridge["plugin_name"],
                "action": normalized,
                "result": {
                    "source": refreshed_bridge.get("source_details"),
                    "refreshed_at": refresh_result.get("refreshed_at"),
                    "source_count": refresh_result.get("source_count"),
                },
                "state": {
                    "enabled": refreshed_bridge.get("enabled"),
                    "status": refreshed_bridge.get("status"),
                    "health": refreshed_bridge.get("health"),
                },
            }
            self._record_operation(
                bridge_name=refreshed_bridge["name"],
                plugin_name=refreshed_bridge["plugin_name"],
                action=normalized,
                status="healthy",
                message="Bridge source sync completed.",
                detail="Plugin source metadata was refreshed.",
                result=response["result"],
            )
            return response

        if not bridge.get("configured"):
            raise LookupError("bridge plugin not configured")

        plugin_name = str(bridge.get("plugin_name") or "").strip()
        if normalized == "enable":
            result = self.plugin_service.set_plugin_enabled(plugin_name, True)
            action_status = "healthy"
            message = "Bridge enabled."
            detail = "Bridge plugin was enabled in configuration."
        elif normalized == "disable":
            result = self.plugin_service.set_plugin_enabled(plugin_name, False)
            action_status = "healthy"
            message = "Bridge disabled."
            detail = "Bridge plugin was disabled in configuration."
        elif normalized == "test_delivery":
            outcome = self._perform_delivery_test(bridge)
            refreshed_bridge = self.get_bridge(name, runtime_status) or bridge
            response = {
                "bridge": refreshed_bridge["name"],
                "plugin_name": plugin_name,
                "action": normalized,
                "result": outcome["result"],
                "state": {
                    "enabled": refreshed_bridge.get("enabled"),
                    "status": refreshed_bridge.get("status"),
                    "health": refreshed_bridge.get("health"),
                },
            }
            self._record_operation(
                bridge_name=refreshed_bridge["name"],
                plugin_name=plugin_name,
                action=normalized,
                status=str(outcome["status"]),
                message=str(outcome["message"]),
                detail=str(outcome.get("detail") or ""),
                result=outcome["result"],
            )
            return response
        else:
            raise ValueError("unsupported bridge action")

        refreshed_bridge = self.get_bridge(name, runtime_status) or bridge
        response = {
            "bridge": refreshed_bridge["name"],
            "plugin_name": plugin_name,
            "action": normalized,
            "result": result,
            "state": {
                "enabled": refreshed_bridge.get("enabled"),
                "status": refreshed_bridge.get("status"),
                "health": refreshed_bridge.get("health"),
            },
        }
        self._record_operation(
            bridge_name=refreshed_bridge["name"],
            plugin_name=plugin_name,
            action=normalized,
            status=action_status,
            message=message,
            detail=detail,
            result=response["state"],
        )
        return response
