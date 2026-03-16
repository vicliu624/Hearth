from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(tags=["metrics"])


def _escape_label(value: Any) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _metric_line(name: str, value: int | float, labels: dict[str, Any] | None = None) -> str:
    if labels:
        rendered_labels = ",".join(f'{key}="{_escape_label(label_value)}"' for key, label_value in labels.items())
        return f"{name}{{{rendered_labels}}} {value}"
    return f"{name} {value}"


def _unix_timestamp(value: str | None) -> int:
    if not value:
        return 0
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp())


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(context: ApplicationContext = Depends(get_context)) -> PlainTextResponse:
    summary = await context.node_service.status_summary(persist=False)
    node_name = summary["node_name"]
    runtime_status = str(summary.get("runtime_status") or "unknown")
    health_status = str(summary.get("health_status") or "unknown")
    interface_summary = summary.get("interface_summary", {})
    metrics = summary.get("metrics", {})

    lines = [
        "# HELP hearth_runtime_up Reticulum runtime availability.",
        "# TYPE hearth_runtime_up gauge",
        _metric_line("hearth_runtime_up", 1 if runtime_status == "running" else 0, {"node": node_name}),
        "# HELP hearth_runtime_status Runtime status info metric.",
        "# TYPE hearth_runtime_status gauge",
        _metric_line("hearth_runtime_status", 1, {"node": node_name, "status": runtime_status}),
        "# HELP hearth_health_status Node health status info metric.",
        "# TYPE hearth_health_status gauge",
        _metric_line("hearth_health_status", 1, {"node": node_name, "status": health_status}),
        "# HELP hearth_uptime_seconds Runtime uptime in seconds.",
        "# TYPE hearth_uptime_seconds gauge",
        _metric_line("hearth_uptime_seconds", int(summary.get("uptime_seconds") or 0), {"node": node_name}),
        "# HELP hearth_interfaces_total Total configured interfaces.",
        "# TYPE hearth_interfaces_total gauge",
        _metric_line("hearth_interfaces_total", int(interface_summary.get("total") or 0), {"node": node_name}),
        "# HELP hearth_interfaces_online Online interfaces.",
        "# TYPE hearth_interfaces_online gauge",
        _metric_line("hearth_interfaces_online", int(interface_summary.get("online") or 0), {"node": node_name}),
        "# HELP hearth_peers_total Total discovered peers.",
        "# TYPE hearth_peers_total gauge",
        _metric_line("hearth_peers_total", int(summary.get("peer_count") or 0), {"node": node_name}),
        "# HELP hearth_routes_total Total learned routes.",
        "# TYPE hearth_routes_total gauge",
        _metric_line("hearth_routes_total", int(summary.get("route_count") or 0), {"node": node_name}),
        "# HELP hearth_announces_total Total announcements observed.",
        "# TYPE hearth_announces_total gauge",
        _metric_line("hearth_announces_total", int(summary.get("announce_count") or 0), {"node": node_name}),
        "# HELP hearth_restarts_total Runtime restart count.",
        "# TYPE hearth_restarts_total counter",
        _metric_line("hearth_restarts_total", int(summary.get("restart_count") or 0), {"node": node_name}),
        "# HELP hearth_errors_total Aggregated interface error count.",
        "# TYPE hearth_errors_total counter",
        _metric_line("hearth_errors_total", int(metrics.get("error_count") or 0), {"node": node_name}),
        "# HELP hearth_interface_up Interface status.",
        "# TYPE hearth_interface_up gauge",
        "# HELP hearth_interface_health_status Interface health info metric.",
        "# TYPE hearth_interface_health_status gauge",
        "# HELP hearth_interface_rx_packets_total Interface received packets.",
        "# TYPE hearth_interface_rx_packets_total counter",
        "# HELP hearth_interface_tx_packets_total Interface transmitted packets.",
        "# TYPE hearth_interface_tx_packets_total counter",
        "# HELP hearth_interface_errors_total Interface error count.",
        "# TYPE hearth_interface_errors_total counter",
        "# HELP hearth_interface_last_seen_timestamp_seconds Interface last seen timestamp.",
        "# TYPE hearth_interface_last_seen_timestamp_seconds gauge",
    ]

    for interface in summary.get("interfaces", []):
        labels = {
            "node": node_name,
            "name": interface.get("name") or "unknown",
            "type": interface.get("type") or "unknown",
            "enabled": str(bool(interface.get("enabled", False))).lower(),
        }
        interface_metrics = interface.get("metrics", {})
        lines.append(_metric_line("hearth_interface_up", 1 if interface.get("status") == "running" else 0, labels))
        lines.append(
            _metric_line(
                "hearth_interface_health_status",
                1,
                {**labels, "status": interface.get("health_status") or "unknown"},
            )
        )
        lines.append(_metric_line("hearth_interface_rx_packets_total", int(interface_metrics.get("rx_packets") or 0), labels))
        lines.append(_metric_line("hearth_interface_tx_packets_total", int(interface_metrics.get("tx_packets") or 0), labels))
        lines.append(_metric_line("hearth_interface_errors_total", int(interface_metrics.get("error_count") or 0), labels))
        lines.append(_metric_line("hearth_interface_last_seen_timestamp_seconds", _unix_timestamp(interface.get("last_seen_at")), labels))

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/api/metrics/summary", dependencies=[Depends(require_permission("read"))])
async def metrics_summary(context: ApplicationContext = Depends(get_context)) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    return {
        "node_name": summary["node_name"],
        "runtime_status": summary.get("runtime_status"),
        "health_status": summary.get("health_status"),
        "interface_summary": summary.get("interface_summary"),
        "metrics": summary.get("metrics"),
        "peer_count": summary.get("peer_count"),
        "route_count": summary.get("route_count"),
        "announce_count": summary.get("announce_count"),
        "restart_count": summary.get("restart_count"),
        "interfaces": summary.get("interfaces"),
    }
