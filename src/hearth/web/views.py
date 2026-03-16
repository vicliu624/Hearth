from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from hearth import __version__
from hearth.api.deps import get_context

from hearth.api.security import (
    SECURITY_HEADERS,
    authenticate_principal,
    auth_is_enabled,
    classify_client_host,
    clear_admin_token_cookie,
    extract_admin_token,
    get_query_token,
    require_permission,
    set_admin_token_cookie,
)
from hearth.core.lifecycle import ApplicationContext
from hearth.services.security_service import KNOWN_PERMISSIONS
from hearth.web.i18n import LANG_COOKIE_NAME, build_locale_options, resolve_locale, translate


router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


NOTICE_KIND_SUCCESS = "success"
NOTICE_KIND_ERROR = "error"
PRESERVED_QUERY_KEYS = {"lang", "token"}


def make_notice(kind: str, message: str) -> dict[str, str]:
    return {"kind": kind, "message": message}


async def read_form_data(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def parse_csv_list(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _preserved_query(request: Request) -> list[tuple[str, str]]:
    return [(key, value) for key, value in request.query_params.multi_items() if key in PRESERVED_QUERY_KEYS]


def build_href(request: Request, path: str) -> str:
    query = urlencode(_preserved_query(request))
    if not query:
        return path
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{query}"


def build_href_with_query(request: Request, path: str, **params: object) -> str:
    query_items = list(_preserved_query(request))
    for key, value in params.items():
        text = str(value).strip() if value is not None else ""
        if text:
            query_items.append((key, text))
    query = urlencode(query_items)
    if not query:
        return path
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{query}"


def normalize_next_path(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate


def is_active_path(current_path: str, target_path: str) -> bool:
    current = current_path.rstrip("/") or "/"
    target = target_path.rstrip("/") or "/"
    if target == "/":
        return current == "/"
    return current == target or current.startswith(f"{target}/")


def is_admin_authenticated(request: Request, context: ApplicationContext) -> bool:
    if not auth_is_enabled(context):
        return False
    principal = authenticate_principal(request, context)
    return principal is not None


def build_nav_links(request: Request, t) -> list[dict[str, str | bool]]:
    items = [
        ("/", "nav.dashboard", False),
        ("/interfaces", "nav.interfaces", False),
        ("/peers", "nav.peers", False),
        ("/routes", "nav.routes", False),
        ("/announces", "nav.announces", False),
        ("/logs", "nav.logs", False),
        ("/timeline", "nav.timeline", False),
        ("/health", "nav.health", False),
        ("/alerts", "nav.alerts", False),
        ("/maintenance", "nav.maintenance", True),
        ("/profile", "nav.profile", True),
        ("/users", "nav.users", True),
        ("/roles", "nav.roles", True),
        ("/tokens", "nav.tokens", True),
        ("/plugins", "nav.plugins", True),
        ("/services", "nav.services", True),
        ("/bridges", "nav.bridges", True),
        ("/metrics-dashboard", "nav.metrics", True),
        ("/fleet", "nav.fleet", True),
        ("/rollout", "nav.rollout", True),
        ("/remote-logs", "nav.remote_logs", True),
        ("/upgrade", "nav.upgrade", True),
        ("/security", "nav.security", True),
        ("/audit", "nav.audit", True),
        ("/diagnostics", "nav.diagnostics", True),
        ("/config", "nav.config", True),
        ("/system", "nav.system", True),
        ("/backup", "nav.backup", True),
        ("/topology", "nav.topology", True),
        ("/path-changes", "nav.path_changes", True),
        ("/api-docs", "nav.docs", True),
    ]
    return [
        {
            "href": build_href(request, path),
            "label": t(label_key),
            "active": is_active_path(request.url.path, path),
            "utility": utility,
        }
        for path, label_key, utility in items
    ]


def translate_value(locale: str, value: str | None) -> str:
    if not value:
        return "-"
    translated = translate(locale, f"value.{value}")
    return value if translated == f"value.{value}" else translated


def relative_time(locale: str, value: str | None) -> str:
    if not value:
        return "-"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    seconds = max(int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()), 0)
    if seconds < 5:
        return translate(locale, "relative.just_now")
    if seconds < 60:
        return translate(locale, "relative.seconds_ago", count=seconds)
    minutes = seconds // 60
    if minutes < 60:
        return translate(locale, "relative.minutes_ago", count=minutes)
    hours = minutes // 60
    if hours < 24:
        return translate(locale, "relative.hours_ago", count=hours)
    days = hours // 24
    return translate(locale, "relative.days_ago", count=days)


def format_bytes(value: int | None) -> str:
    if value is None:
        return "-"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(value)} B"


def format_counter(value: int | None) -> str:
    if value is None:
        return "-"
    size = float(max(int(value), 0))
    units = ["", "k", "M", "B"]
    unit_index = 0
    while size >= 1000 and unit_index < len(units) - 1:
        size /= 1000
        unit_index += 1
    if unit_index == 0:
        return f"{int(size):,}"
    return f"{size:.1f}{units[unit_index]}"


def shorten_label(value: str | None, max_length: int = 10) -> str:
    text = (value or "-").strip()
    if len(text) <= max_length:
        return text
    return f"{text[:max_length - 3]}..."


def get_total_memory() -> int | None:
    try:
        import psutil  # type: ignore

        return int(psutil.virtual_memory().total)
    except Exception:
        pass

    if hasattr(os, "sysconf"):
        try:
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            page_count = int(os.sysconf("SC_PHYS_PAGES"))
            return page_size * page_count
        except (ValueError, OSError):
            pass

    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return int(status.ullTotalPhys)
        except Exception:
            return None

    return None


def get_reticulum_version() -> str:
    for package_name in ("rns", "reticulum"):
        try:
            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return "-"


def filter_recent_logs(logs: list[dict], since_minutes: int | None) -> list[dict]:
    if not since_minutes or since_minutes <= 0:
        return logs
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    filtered: list[dict] = []
    for entry in logs:
        try:
            created_at = datetime.fromisoformat(entry["created_at"])
        except (KeyError, ValueError):
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at.astimezone(timezone.utc) >= cutoff:
            filtered.append(entry)
    return filtered


def format_uptime_compact(seconds: int | None) -> str:
    total_seconds = max(int(seconds or 0), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_uptime_verbose(seconds: int | None) -> str:
    total_seconds = max(int(seconds or 0), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} days")
    if hours:
        parts.append(f"{hours} hours")
    if not parts:
        parts.append(f"{minutes} minutes")
    return " ".join(parts[:2])


def build_header_state(summary: dict) -> dict[str, str]:
    return {
        "node_name": str(summary.get("node_name", "hearth.local")),
        "uptime_compact": format_uptime_compact(summary.get("uptime_seconds")),
        "uptime_verbose": format_uptime_verbose(summary.get("uptime_seconds")),
        "health_status": str(summary.get("health_status", "unknown")),
        "runtime_status": str(summary.get("runtime_status", "unknown")),
    }


def build_tone(value: str | None) -> str:
    normalized = (value or "").lower()
    if normalized in {"healthy", "running", "online", "success"}:
        return "success"
    if normalized in {"warning", "degraded", "starting"}:
        return "warning"
    if normalized in {"error", "critical", "stopped", "crashed", "offline"}:
        return "danger"
    return "info"


def _coerce_history_timestamp(value: str | datetime, target_timezone) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(target_timezone)


def _history_bucket_start(value: datetime, bucket_hours: int) -> datetime:
    bucket_hour = value.hour - (value.hour % bucket_hours)
    return value.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)


def summarize_activity_history(
    snapshots: list[dict[str, object]],
    now: datetime | None = None,
    *,
    total_hours: int = 24,
    bucket_hours: int = 2,
) -> dict[str, object]:
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    target_timezone = reference.tzinfo
    bucket_count = max(total_hours // bucket_hours, 1)
    current_bucket = _history_bucket_start(reference.astimezone(target_timezone), bucket_hours)
    bucket_starts = [
        current_bucket - timedelta(hours=bucket_hours * (bucket_count - index - 1))
        for index in range(bucket_count)
    ]
    buckets = {
        bucket_start: {"rx": 0, "tx": 0, "errors": 0}
        for bucket_start in bucket_starts
    }

    previous_by_interface: dict[str, dict[str, int | datetime]] = {}
    for snapshot in snapshots:
        interface_name = str(snapshot.get("interface_name") or "")
        captured_at = _coerce_history_timestamp(snapshot["captured_at"], target_timezone)
        current = {
            "rx": max(int(snapshot.get("rx_packets", 0) or 0), 0),
            "tx": max(int(snapshot.get("tx_packets", 0) or 0), 0),
            "errors": max(int(snapshot.get("error_count", 0) or 0), 0),
            "captured_at": captured_at,
        }
        previous = previous_by_interface.get(interface_name)
        if previous is not None:
            bucket_start = _history_bucket_start(captured_at, bucket_hours)
            if bucket_start in buckets:
                buckets[bucket_start]["rx"] += max(current["rx"] - int(previous["rx"]), 0)
                buckets[bucket_start]["tx"] += max(current["tx"] - int(previous["tx"]), 0)
                buckets[bucket_start]["errors"] += max(current["errors"] - int(previous["errors"]), 0)
        previous_by_interface[interface_name] = current

    peak = max(
        [1, *[max(values["rx"], values["tx"]) for values in buckets.values()]],
    )
    bars: list[dict[str, int | str]] = []
    total_rx = 0
    total_tx = 0
    total_errors = 0
    for bucket_start in bucket_starts:
        values = buckets[bucket_start]
        total_rx += values["rx"]
        total_tx += values["tx"]
        total_errors += values["errors"]
        bars.append(
            {
                "label": bucket_start.strftime("%H"),
                "title": f"{bucket_start.strftime('%m-%d %H:%M')} - {(bucket_start + timedelta(hours=bucket_hours)).strftime('%H:%M')}",
                "rx_value": format_counter(values["rx"]),
                "tx_value": format_counter(values["tx"]),
                "rx_height": 0 if values["rx"] == 0 else max(8, round(values["rx"] / peak * 100)),
                "tx_height": 0 if values["tx"] == 0 else max(8, round(values["tx"] / peak * 100)),
            }
        )

    return {
        "bars": bars,
        "totals": {
            "rx_packets": format_counter(total_rx),
            "tx_packets": format_counter(total_tx),
            "error_count": total_errors,
        },
    }


def build_activity_bars(history: dict[str, object]) -> list[dict[str, int | str]]:
    return list(history.get("bars", []))


def build_traffic_snapshot(history: dict[str, object]) -> dict[str, str | int]:
    return dict(history.get("totals", {}))


def build_system_snapshot(context: ApplicationContext, summary: dict) -> dict[str, object]:
    disk_usage = shutil.disk_usage(context.settings.data_dir)
    total_memory = get_total_memory()
    cpu_load: str | None = None
    if hasattr(os, "getloadavg"):
        try:
            load1, _, _ = os.getloadavg()
            cpu_load = f"{load1:.2f}"
        except OSError:
            cpu_load = None
    return {
        "hearth_version": __version__,
        "reticulum_version": get_reticulum_version(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu": os.cpu_count() or 0,
        "cpu_load": cpu_load,
        "memory": format_bytes(total_memory) if total_memory is not None else None,
        "disk_total": format_bytes(disk_usage.total),
        "disk_used": format_bytes(disk_usage.used),
        "disk_free": format_bytes(disk_usage.free),
        "backend": context.settings.reticulum.backend,
        "route_count": int(summary.get("route_count", 0)),
        "peer_count": int(summary.get("peer_count", 0)),
        "interface_count": int(summary.get("interface_summary", {}).get("total", 0)),
        "online_interfaces": int(summary.get("interface_summary", {}).get("online", 0)),
    }


def humanize_key(value: str) -> str:
    return value.replace("_", " ").strip().title()


def build_health_score(summary: dict, interfaces: list[dict]) -> int:
    base_score = {
        "healthy": 100,
        "warning": 84,
        "degraded": 62,
        "critical": 28,
    }.get(str(summary.get("health_status", "unknown")), 72)
    issue_penalty = min(len(summary.get("issues", [])) * 8, 32)
    degraded_penalty = sum(
        8
        for item in interfaces
        if item.get("enabled") and item.get("health_status") in {"degraded", "critical"}
    )
    warning_penalty = sum(
        4
        for item in interfaces
        if item.get("enabled") and item.get("health_status") == "warning"
    )
    stopped_penalty = sum(
        6
        for item in interfaces
        if item.get("enabled") and item.get("status") in {"stopped", "crashed", "error"}
    )
    return max(0, min(100, base_score - issue_penalty - degraded_penalty - warning_penalty - stopped_penalty))


def decorate_event_rows(logs: list[dict]) -> list[dict]:
    decorated: list[dict] = []
    for entry in logs:
        decorated.append({
            **entry,
            "tone": build_tone(entry.get("severity") or entry.get("source") or entry.get("event_type")),
        })
    return decorated


def mask_secret(value: str | None) -> str:
    secret = (value or "").strip()
    if not secret:
        return "-"
    if len(secret) <= 4:
        return "****"
    return f"{'*' * max(len(secret) - 4, 4)}{secret[-4:]}"


def bool_label(value: bool) -> str:
    return "enabled" if value else "disabled"


def format_payload(payload: object) -> str:
    if not payload:
        return "-"
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def summarize_payload(payload: object, max_length: int = 88) -> str:
    text = format_payload(payload)
    if text == "-":
        return text
    single_line = " ".join(text.split())
    if len(single_line) <= max_length:
        return single_line
    return f"{single_line[:max_length - 3]}..."


def build_security_findings(context: ApplicationContext) -> list[str]:
    findings: list[str] = []
    configured_token = context.settings.security.admin_token.strip()
    if configured_token in {"", "change-me"}:
        findings.append("security.default_token_warning")
    if context.settings.security.allow_wan:
        findings.append("security.wan_warning")
    if not auth_is_enabled(context):
        findings.append("security.auth_disabled_warning")
    return findings


def filter_audit_entries(request: Request, entries: list[dict]) -> tuple[list[dict], dict[str, object], list[str], list[str]]:
    level = (request.query_params.get("level") or "").strip()
    source = (request.query_params.get("source") or "").strip()
    search = (request.query_params.get("search") or "").strip().lower()
    try:
        limit = max(1, min(int(request.query_params.get("limit", "100")), 500))
    except ValueError:
        limit = 100

    filtered = entries
    if level:
        filtered = [item for item in filtered if str(item.get("severity") or "") == level]
    if source:
        filtered = [item for item in filtered if str(item.get("source") or "") == source]
    if search:
        filtered = [
            item
            for item in filtered
            if search in str(item.get("event_type") or "").lower()
            or search in str(item.get("message") or "").lower()
            or search in str(item.get("source") or "").lower()
        ]

    for item in filtered:
        item["payload_pretty"] = format_payload(item.get("payload"))
        item["payload_summary"] = summarize_payload(item.get("payload"))

    levels = sorted({str(item.get("severity") or "") for item in entries if item.get("severity")})
    sources = sorted({str(item.get("source") or "") for item in entries if item.get("source")})
    filters = {"level": level, "source": source, "search": search, "limit": limit}
    return decorate_event_rows(filtered[:limit]), filters, levels, sources


def filter_peers(request: Request, peers: list[dict]) -> tuple[list[dict], dict[str, object], list[str]]:
    search = (request.query_params.get("search") or "").strip().lower()
    interface_name = (request.query_params.get("interface") or "").strip()
    try:
        limit = max(1, min(int(request.query_params.get("limit", "10")), 100))
    except ValueError:
        limit = 10

    interface_options = sorted({item.get("interface_name") for item in peers if item.get("interface_name")})
    filtered = peers
    if search:
        filtered = [
            item for item in filtered
            if search in (item.get("display_name") or "").lower() or search in (item.get("peer_hash") or "").lower()
        ]
    if interface_name:
        filtered = [item for item in filtered if item.get("interface_name") == interface_name]

    for item in filtered:
        item["tone"] = build_tone(item.get("interface_name") or item.get("source_type") or item.get("peer_hash"))

    return filtered[:limit], {"search": search, "interface": interface_name, "limit": limit}, interface_options


def build_page_context(request: Request, title_key: str, **extra: object) -> dict[str, object]:
    locale = resolve_locale(request)

    def t(key: str, **kwargs: object) -> str:
        return translate(locale, key, **kwargs)

    def tv(value: str | None) -> str:
        return translate_value(locale, value)

    def tr(value: str | None) -> str:
        return relative_time(locale, value)

    nav_links = build_nav_links(request, t)
    primary_nav_links = [item for item in nav_links if not item.get("utility")]
    utility_nav_links = [item for item in nav_links if item.get("utility")]

    return {
        "title": t(title_key),
        "locale": locale,
        "languages": build_locale_options(locale, request),
        "nav_links": nav_links,
        "primary_nav_links": primary_nav_links,
        "utility_nav_links": utility_nav_links,
        "t": t,
        "tv": tv,
        "tr": tr,
        **extra,
    }


def finalize_page_response(request: Request, response: Response, context: ApplicationContext) -> Response:
    if "lang" in request.query_params:
        response.set_cookie(LANG_COOKIE_NAME, resolve_locale(request), httponly=False, samesite="lax", path="/")

    query_token = get_query_token(request)
    if query_token:
        if not auth_is_enabled(context):
            set_admin_token_cookie(response, query_token)
        elif context.security_service.authenticate_token(query_token):
            set_admin_token_cookie(response, query_token)

    return response


def render_page(
    request: Request,
    context: ApplicationContext,
    template_name: str,
    title_key: str,
    status_code: int = 200,
    **extra: object,
) -> Response:
    next_path = normalize_next_path(request.url.path)
    response = templates.TemplateResponse(
        request,
        template_name,
        build_page_context(
            request,
            title_key,
            auth_enabled=auth_is_enabled(context),
            admin_authenticated=is_admin_authenticated(request, context),
            login_href=build_href(request, f"/login?next={next_path}"),
            logout_href=build_href(request, "/logout"),
            **extra,
        ),
        status_code=status_code,
    )
    return finalize_page_response(request, response, context)


async def render_dashboard_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=True)
    logs = decorate_event_rows(context.log_service.list_entries(limit=10))
    history_now = datetime.now().astimezone()
    history_samples = context.database.list_interface_metric_snapshots(
        history_now.astimezone(timezone.utc) - timedelta(hours=26)
    )
    activity_history = summarize_activity_history(history_samples, now=history_now)
    return render_page(
        request,
        context,
        "dashboard.html",
        "page.dashboard",
        summary=summary,
        logs=logs,
        notice=notice,
        header_state=build_header_state(summary),
        activity_bars=build_activity_bars(activity_history),
        traffic_snapshot=build_traffic_snapshot(activity_history),
        system_info=build_system_snapshot(context, summary),
        view_all_logs_href=build_href(request, "/logs"),
    )


async def render_interfaces_page(
    request: Request,
    context: ApplicationContext,
    selected_name: str | None = None,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    interfaces = await context.interface_service.list_interfaces()
    if not selected_name and interfaces:
        selected_name = request.query_params.get("selected") or interfaces[0]["name"]
    selected_metrics = None
    for item in interfaces:
        item["metrics_href"] = build_href(request, f"/interfaces/{item['name']}")
        item["control_href"] = build_href(request, f"/interfaces/{item['name']}/control")
        item["tone"] = build_tone(item.get("status") or item.get("health_status"))
        item["rx_tx"] = f"{item['metrics'].get('rx_packets', 0)} / {item['metrics'].get('tx_packets', 0)}"
        if item["name"] == selected_name:
            selected_metrics = item["metrics"]
    if selected_name and selected_metrics is None:
        try:
            selected_metrics = await context.interface_service.metrics(selected_name)
        except Exception:
            selected_metrics = None
    return render_page(
        request,
        context,
        "interfaces.html",
        "page.interfaces",
        interfaces=interfaces,
        selected_name=selected_name,
        selected_metrics=selected_metrics,
        notice=notice,
        result=result,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_interface_detail_page(
    request: Request,
    context: ApplicationContext,
    name: str,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    interface = await context.interface_service.get_interface(name)
    interface["tone"] = build_tone(interface.get("status") or interface.get("health_status"))
    interface["rx_tx"] = f"{interface['metrics'].get('rx_packets', 0)} / {interface['metrics'].get('tx_packets', 0)}"
    metric_rows = [{"label": humanize_key(key), "value": value} for key, value in interface.get("metrics", {}).items()]
    history_now = datetime.now().astimezone()
    history_samples = [
        sample
        for sample in context.database.list_interface_metric_snapshots(history_now.astimezone(timezone.utc) - timedelta(hours=26))
        if sample.get("interface_name") == name
    ]
    activity_history = summarize_activity_history(history_samples, now=history_now)
    restart_history = context.database.list_restarts(limit=20, target_type="interface", target_name=name)
    return render_page(
        request,
        context,
        "interface_detail.html",
        "page.interface_detail",
        interface=interface,
        metric_rows=metric_rows,
        activity_bars=build_activity_bars(activity_history),
        traffic_snapshot=build_traffic_snapshot(activity_history),
        restart_history=restart_history,
        control_href=build_href(request, f"/interfaces/{name}/control"),
        interfaces_href=build_href(request, "/interfaces"),
        notice=notice,
        result=result,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_health_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    interfaces = summary.get("interfaces", [])
    for item in interfaces:
        item["tone"] = build_tone(item.get("health_status") or item.get("status"))
        item["rx_tx"] = f"{item['metrics'].get('rx_packets', 0)} / {item['metrics'].get('tx_packets', 0)}"
    all_restarts = context.database.list_restarts(limit=100)
    restart_history = all_restarts[:20]
    raw_incidents = context.log_service.list_entries(limit=50)
    incidents = [
        entry
        for entry in raw_incidents
        if str(entry.get("severity") or "").lower() in {"warning", "error", "critical"}
        or "restart" in str(entry.get("event_type") or "").lower()
        or "health" in str(entry.get("source") or "").lower()
        or "watchdog" in str(entry.get("source") or "").lower()
    ]
    if not incidents:
        incidents = raw_incidents[:10]
    incidents = decorate_event_rows(incidents[:20])
    degraded_count = sum(1 for item in interfaces if item.get("enabled") and item.get("health_status") in {"degraded", "critical"})
    warning_count = sum(
        1
        for item in interfaces
        if item.get("enabled") and (item.get("health_status") == "warning" or item.get("status") == "stopped")
    )
    return render_page(
        request,
        context,
        "health.html",
        "page.health",
        summary=summary,
        interfaces=interfaces,
        incidents=incidents,
        restart_history=restart_history,
        health_score=build_health_score(summary, interfaces),
        degraded_count=degraded_count,
        warning_count=warning_count,
        restart_count=len(all_restarts),
        runtime=summary.get("runtime", {}),
        notice=notice,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_login_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    next_path: str | None = None,
    status_code: int = 200,
) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    resolved_next = normalize_next_path(next_path or request.query_params.get("next") or "/profile")
    return render_page(
        request,
        context,
        "login.html",
        "page.login",
        notice=notice,
        next_path=resolved_next,
        login_post_href=build_href(request, "/login"),
        system_href=build_href(request, "/system"),
        header_state=build_header_state(summary),
        shell_summary=summary,
        status_code=status_code,
    )



async def render_peer_detail_page(request: Request, context: ApplicationContext, peer_hash: str) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    peer = await context.peer_service.get_peer(peer_hash)
    announces = [item for item in await context.announce_service.list_announces(limit=200) if item.get("source_hash") == peer_hash]
    for item in announces:
        if item.get("id") is not None:
            item["detail_href"] = build_href(request, f"/announces/{item['id']}")
    routes = [
        item
        for item in await context.route_service.list_routes(limit=200)
        if item.get("destination_hash") == peer_hash or item.get("next_hop") == peer_hash
    ]
    for item in routes:
        item["detail_href"] = build_href(request, f"/routes/{item['destination_hash']}")
    interfaces_seen = sorted(
        {
            value
            for value in [peer.get("interface_name"), *[item.get("via_interface") for item in announces]]
            if value
        }
    )
    return render_page(
        request,
        context,
        "peer_detail.html",
        "page.peer_detail",
        peer=peer,
        announce_history=announces[:20],
        related_routes=routes[:20],
        interfaces_seen=interfaces_seen,
        peers_href=build_href(request, "/peers"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_route_detail_page(request: Request, context: ApplicationContext, destination_hash: str) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    route = await context.route_service.get_route(destination_hash)
    related_announces = [
        item for item in await context.announce_service.list_announces(limit=200) if item.get("source_hash") == destination_hash
    ]
    for item in related_announces:
        if item.get("id") is not None:
            item["detail_href"] = build_href(request, f"/announces/{item['id']}")
    related_peer = None
    for candidate in filter(None, [route.get("next_hop"), route.get("destination_hash")]):
        try:
            related_peer = await context.peer_service.get_peer(str(candidate))
            break
        except Exception:
            continue
    return render_page(
        request,
        context,
        "route_detail.html",
        "page.route_detail",
        route=route,
        related_announces=related_announces[:20],
        related_peer=related_peer,
        routes_href=build_href(request, "/routes"),
        peer_detail_href=build_href(request, f"/peers/{related_peer['peer_hash']}") if related_peer else None,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_announce_detail_page(request: Request, context: ApplicationContext, announce_id: int) -> Response:
    summary = await context.node_service.status_summary(persist=False)
    announce = await context.announce_service.get_announce(announce_id)
    related_peer = None
    related_route = None
    try:
        related_peer = await context.peer_service.get_peer(str(announce.get("source_hash")))
    except Exception:
        related_peer = None
    destination_hash = (announce.get("metadata") or {}).get("destination_hash")
    for candidate in filter(None, [destination_hash, announce.get("source_hash")]):
        try:
            related_route = await context.route_service.get_route(str(candidate))
            break
        except Exception:
            continue
    metadata_rows = [
        {"label": humanize_key(str(key)), "value": value}
        for key, value in sorted((announce.get("metadata") or {}).items())
    ]
    return render_page(
        request,
        context,
        "announce_detail.html",
        "page.announce_detail",
        announce=announce,
        related_peer=related_peer,
        related_route=related_route,
        metadata_rows=metadata_rows,
        announces_href=build_href(request, "/announces"),
        peer_detail_href=build_href(request, f"/peers/{related_peer['peer_hash']}") if related_peer else None,
        route_detail_href=build_href(request, f"/routes/{related_route['destination_hash']}") if related_route else None,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_peers_page(request: Request, context: ApplicationContext) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    all_peers = await context.peer_service.list_recent(limit=200)
    for item in all_peers:
        item["detail_href"] = build_href(request, f"/peers/{item['peer_hash']}")
    peers, filters, peer_interfaces = filter_peers(request, all_peers)
    return render_page(
        request,
        context,
        "peers.html",
        "page.peers",
        peers=peers,
        all_peer_count=len(all_peers),
        filters=filters,
        peer_interfaces=peer_interfaces,
        clear_peers_href=build_href(request, "/peers"),
        topology_href=build_href(request, "/routes"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_routes_page(request: Request, context: ApplicationContext) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    routes = await context.route_service.list_routes(limit=100)
    for item in routes:
        item["detail_href"] = build_href(request, f"/routes/{item['destination_hash']}")
    return render_page(
        request,
        context,
        "routes.html",
        "page.routes",
        routes=routes,
        header_state=build_header_state(summary),
        shell_summary=summary,
        page_total=len(routes),
    )


async def render_announces_page(request: Request, context: ApplicationContext) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    announces = await context.announce_service.list_announces(limit=100)
    for item in announces:
        if item.get("id") is not None:
            item["detail_href"] = build_href(request, f"/announces/{item['id']}")
    return render_page(
        request,
        context,
        "announces.html",
        "page.announces",
        announces=announces,
        header_state=build_header_state(summary),
        shell_summary=summary,
        page_total=len(announces),
    )


async def render_logs_page(request: Request, context: ApplicationContext) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    level = request.query_params.get("level") or None
    module = request.query_params.get("module") or None
    try:
        limit = max(1, min(int(request.query_params.get("limit", "100")), 500))
    except ValueError:
        limit = 100
    try:
        since_minutes = max(0, int(request.query_params.get("since_minutes", "0")))
    except ValueError:
        since_minutes = 0

    logs = context.log_service.list_entries(limit=limit, severity=level, source=module)
    logs = filter_recent_logs(logs, since_minutes)
    logs = decorate_event_rows(logs)
    options_source = context.log_service.list_entries(limit=200)
    levels = sorted({item["severity"] for item in options_source})
    modules = sorted({item["source"] for item in options_source})
    filters = {
        "level": level or "",
        "module": module or "",
        "limit": limit,
        "since_minutes": since_minutes,
    }
    return render_page(
        request,
        context,
        "logs.html",
        "page.logs",
        logs=logs,
        levels=levels,
        modules=modules,
        filters=filters,
        clear_logs_href=build_href(request, "/logs"),
        timeline_href=build_href_with_query(
            request,
            "/timeline",
            level=level or None,
            module=module or None,
            limit=limit,
            since_minutes=since_minutes,
        ),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_timeline_page(request: Request, context: ApplicationContext) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    level = request.query_params.get("level") or None
    module = request.query_params.get("module") or None
    try:
        limit = max(1, min(int(request.query_params.get("limit", "300")), 1000))
    except ValueError:
        limit = 300
    try:
        since_minutes = max(0, int(request.query_params.get("since_minutes", "1440")))
    except ValueError:
        since_minutes = 1440
    try:
        bucket_minutes = max(1, min(int(request.query_params.get("bucket_minutes", "120")), 1440))
    except ValueError:
        bucket_minutes = 120

    timeline = context.log_service.timeline(
        limit=limit,
        severity=level,
        source=module,
        since_minutes=since_minutes,
        bucket_minutes=bucket_minutes,
    )
    peak_count = max(int(timeline.get("peak_count") or 0), 1)
    for bucket in timeline.get("time_buckets", []):
        count = int(bucket.get("count") or 0)
        critical = int(bucket.get("critical") or 0)
        bucket["count_height"] = f"{max(round(count / peak_count * 100), 10)}%" if count else "0%"
        bucket["critical_height"] = f"{max(round(critical / peak_count * 100), 8)}%" if critical else "0%"
    timeline["events"] = decorate_event_rows(list(timeline.get("events", [])))

    options_source = context.log_service.list_entries(limit=200)
    levels = sorted({item["severity"] for item in options_source})
    modules = sorted({item["source"] for item in options_source})
    filters = {
        "level": level or "",
        "module": module or "",
        "limit": limit,
        "since_minutes": since_minutes,
        "bucket_minutes": bucket_minutes,
    }
    return render_page(
        request,
        context,
        "timeline.html",
        "page.timeline",
        timeline=timeline,
        levels=levels,
        modules=modules,
        filters=filters,
        clear_timeline_href=build_href(request, "/timeline"),
        logs_href=build_href_with_query(
            request,
            "/logs",
            level=level or None,
            module=module or None,
            limit=limit,
            since_minutes=since_minutes,
        ),
        header_state=build_header_state(summary),
        shell_summary=summary,
        page_total=int(timeline.get("total") or 0),
    )


async def render_maintenance_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    maintenance = context.maintenance_service.get_state()
    return render_page(
        request,
        context,
        "maintenance.html",
        "page.maintenance",
        notice=notice,
        summary=summary,
        maintenance=maintenance,
        watchdog_state=bool_label(context.settings.monitor.watchdog_enabled),
        auto_restart_runtime_state=bool_label(context.settings.monitor.auto_restart_runtime),
        auto_restart_interface_state=bool_label(context.settings.monitor.auto_restart_interface),
        restart_cooldown_sec=context.settings.monitor.restart_cooldown_sec,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_profile_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    authenticated = is_admin_authenticated(request, context)
    principal = authenticate_principal(request, context) or {}
    client_host = request.client.host if request.client else None
    client_zone = classify_client_host(client_host)
    token_value = extract_admin_token(request)
    quick_links = [
        {"href": build_href(request, "/maintenance"), "label_key": "nav.maintenance"},
        {"href": build_href(request, "/users"), "label_key": "nav.users"},
        {"href": build_href(request, "/tokens"), "label_key": "nav.tokens"},
        {"href": build_href(request, "/audit"), "label_key": "nav.audit"},
    ]
    return render_page(
        request,
        context,
        "profile.html",
        "page.profile",
        notice=notice,
        summary=summary,
        session_status="authenticated" if authenticated else "not_authenticated",
        session_subject=str(principal.get("subject") or "token_session"),
        role_value=str(principal.get("role") or "viewer"),
        auth_mode_value=context.settings.web.auth_mode or "unknown",
        client_host=client_host or "-",
        client_zone=client_zone,
        token_masked=mask_secret(token_value),
        access_scope="public" if context.settings.security.allow_wan else "lan" if context.settings.security.allow_lan else "loopback",
        security_findings=build_security_findings(context),
        quick_links=quick_links,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_users_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    users = context.security_service.list_users()
    role_options = context.security_service.list_roles()
    return render_page(
        request,
        context,
        "users.html",
        "page.users",
        notice=notice,
        result=result,
        summary=summary,
        users=users,
        role_options=role_options,
        page_total=len(users),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_roles_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    roles = context.security_service.list_roles()
    permission_columns = sorted({permission for role in roles for permission in role["permissions"]})
    editable_roles = [role for role in roles if role.get("editable")]
    return render_page(
        request,
        context,
        "roles.html",
        "page.roles",
        notice=notice,
        result=result,
        summary=summary,
        roles=roles,
        permission_columns=permission_columns,
        permission_options=sorted(KNOWN_PERMISSIONS),
        editable_roles=editable_roles,
        page_total=len(roles),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_tokens_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    tokens = context.security_service.list_api_tokens()
    users = context.security_service.list_users()
    role_options = context.security_service.list_roles()
    return render_page(
        request,
        context,
        "tokens.html",
        "page.tokens",
        notice=notice,
        result=result,
        summary=summary,
        tokens=tokens,
        users=users,
        role_options=role_options,
        page_total=len(tokens),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_plugins_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    plugins = context.plugin_service.list_plugins()
    installed_names = {item["name"] for item in plugins}
    catalog_plugins = context.plugin_service.list_available_plugins()
    plugin_history = context.plugin_service.plugin_history(limit=12)
    for item in plugins:
        item["detail_href"] = build_href(request, f"/plugins/{item['name']}")
        item["installed"] = True
        item["state_label"] = "Installed"
    for item in catalog_plugins:
        item["detail_href"] = build_href(request, f"/plugins/{item['name']}")
        item["installed"] = item["name"] in installed_names
        item["state_label"] = "Installed" if item["installed"] else "Available"
    return render_page(
        request,
        context,
        "plugins.html",
        "page.plugins",
        notice=notice,
        result=result,
        summary=summary,
        plugins=plugins,
        catalog_plugins=catalog_plugins,
        plugin_history=plugin_history,
        page_total=len(plugins),
        plugin_sources_href=build_href(request, "/plugin-sources"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_plugin_sources_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    sources = list(result.get("sources") or []) if result else context.plugin_service.list_sources()
    return render_page(
        request,
        context,
        "plugin_sources.html",
        "page.plugin_sources",
        notice=notice,
        result=result,
        summary=summary,
        sources=sources,
        page_total=len(sources),
        plugins_href=build_href(request, "/plugins"),
        refresh_plugin_sources_href=build_href(request, "/plugin-sources"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_plugin_detail_page(
    request: Request,
    context: ApplicationContext,
    name: str,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    plugin = context.plugin_service.get_plugin(name)
    catalog_plugin = context.plugin_service.get_available_plugin(name)
    if plugin is None and catalog_plugin is None:
        locale = resolve_locale(request)
        response = await render_plugins_page(
            request,
            context,
            notice=notice or make_notice(NOTICE_KIND_ERROR, translate(locale, "plugins.not_found")),
        )
        response.status_code = 404
        return response
    plugin_record = dict(catalog_plugin or plugin or {})
    if plugin is not None:
        plugin_record.update(plugin)
    plugin_record["installed"] = plugin is not None
    plugin_record["installable"] = bool(catalog_plugin.get("installable", False)) if catalog_plugin else bool(plugin_record.get("trusted_source"))
    plugin_record["state_label"] = "Installed" if plugin is not None else "Catalog"
    plugin_record["catalog_version"] = catalog_plugin.get("version") if catalog_plugin else None
    plugin_record["catalog_description"] = catalog_plugin.get("description") if catalog_plugin else None
    plugin_record["signature_status"] = (catalog_plugin or plugin_record).get("signature_status") if isinstance(catalog_plugin or plugin_record, dict) else None
    dependency_plan: list[dict] = []
    try:
        dependency_plan = context.plugin_service.resolve_dependencies(name) if catalog_plugin else []
    except Exception:
        dependency_plan = []
    history = [item for item in context.plugin_service.plugin_history(limit=30) if str(item.get("plugin_name") or "") == name][:10]
    return render_page(
        request,
        context,
        "plugin_detail.html",
        "page.plugin_detail",
        notice=notice,
        result=result,
        summary=summary,
        plugin=plugin_record,
        dependency_plan=dependency_plan,
        plugin_history=history,
        plugins_href=build_href(request, "/plugins"),
        plugin_sources_href=build_href(request, "/plugin-sources"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_services_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    services = await context.service_host_service.list_services()
    for item in services:
        item["detail_href"] = build_href(request, f"/services/{item['name']}")
    return render_page(
        request,
        context,
        "services.html",
        "page.services",
        notice=notice,
        result=result,
        summary=summary,
        services=services,
        page_total=len(services),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_service_detail_page(
    request: Request,
    context: ApplicationContext,
    name: str,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    service = await context.service_host_service.get_service(name)
    if service is None:
        locale = resolve_locale(request)
        response = await render_services_page(
            request,
            context,
            notice=notice or make_notice(NOTICE_KIND_ERROR, translate(locale, "services.not_found")),
        )
        response.status_code = 404
        return response
    return render_page(
        request,
        context,
        "service_detail.html",
        "page.service_detail",
        notice=notice,
        result=result,
        summary=summary,
        service=service,
        services_href=build_href(request, "/services"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_dashboard_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    overview = await context.fleet_service.dashboard()
    return render_page(
        request,
        context,
        "fleet.html",
        "page.fleet",
        notice=notice,
        summary=summary,
        overview=overview,
        nodes_href=build_href(request, "/fleet/nodes"),
        groups_href=build_href(request, "/fleet/groups"),
        templates_href=build_href(request, "/fleet/templates"),
        tags_href=build_href(request, "/fleet/tags"),
        health_href=build_href(request, "/fleet/health"),
        events_href=build_href(request, "/fleet/events"),
        api_docs_href=build_href(request, "/api-docs"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_nodes_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    nodes = await context.fleet_service.list_nodes()
    groups = await context.fleet_service.list_groups()
    for node in nodes:
        node["detail_href"] = build_href(request, f"/fleet/nodes/{node['node_name']}")
    return render_page(
        request,
        context,
        "fleet_nodes.html",
        "page.fleet_nodes",
        notice=notice,
        result=result,
        summary=summary,
        nodes=nodes,
        groups=groups,
        page_total=len(nodes),
        fleet_href=build_href(request, "/fleet"),
        groups_href=build_href(request, "/fleet/groups"),
        templates_href=build_href(request, "/fleet/templates"),
        tags_href=build_href(request, "/fleet/tags"),
        health_href=build_href(request, "/fleet/health"),
        events_href=build_href(request, "/fleet/events"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_groups_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    groups = await context.fleet_service.list_groups()
    return render_page(
        request,
        context,
        "fleet_groups.html",
        "page.fleet_groups",
        notice=notice,
        result=result,
        summary=summary,
        groups=groups,
        page_total=len(groups),
        fleet_href=build_href(request, "/fleet"),
        nodes_href=build_href(request, "/fleet/nodes"),
        templates_href=build_href(request, "/fleet/templates"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_templates_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    groups = await context.fleet_service.list_groups()
    templates = await context.fleet_service.list_templates()
    return render_page(
        request,
        context,
        "fleet_templates.html",
        "page.templates",
        notice=notice,
        result=result,
        summary=summary,
        groups=groups,
        templates=templates,
        page_total=len(templates),
        fleet_href=build_href(request, "/fleet"),
        nodes_href=build_href(request, "/fleet/nodes"),
        groups_href=build_href(request, "/fleet/groups"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_node_detail_page(
    request: Request,
    context: ApplicationContext,
    node_name: str,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    node = await context.fleet_service.get_node(node_name)
    if node is None:
        locale = resolve_locale(request)
        response = await render_fleet_nodes_page(
            request,
            context,
            notice=notice or make_notice(NOTICE_KIND_ERROR, translate(locale, "fleet.node_not_found")),
        )
        response.status_code = 404
        return response
    node["tone"] = build_tone(node.get("health_status") or node.get("runtime_status"))
    dashboard_url = str(node.get("dashboard_url") or "").strip()
    dashboard_href = build_href(request, dashboard_url) if dashboard_url.startswith("/") else (dashboard_url or None)
    return render_page(
        request,
        context,
        "fleet_node_detail.html",
        "page.fleet_node_detail",
        notice=notice,
        summary=summary,
        node=node,
        recent_events=decorate_event_rows(list(node.get("recent_events") or [])),
        nodes_href=build_href(request, "/fleet/nodes"),
        tags_href=build_href(request, "/fleet/tags"),
        health_href=build_href(request, "/fleet/health"),
        events_href=build_href(request, "/fleet/events"),
        dashboard_href=dashboard_href,
        remote_logs_href=build_href_with_query(request, "/remote-logs", node_name=node["node_name"]),
        rollout_href=build_href(request, "/rollout"),
        upgrade_href=build_href(request, "/upgrade"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_tags_page(
    request: Request,
    context: ApplicationContext,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    tags = await context.fleet_service.list_tags()
    tagged_nodes = sorted({node_name for item in tags for node_name in list(item.get("nodes") or [])})
    for item in tags:
        item["node_links"] = [
            {"name": node_name, "href": build_href(request, f"/fleet/nodes/{node_name}")}
            for node_name in list(item.get("nodes") or [])
        ]
    return render_page(
        request,
        context,
        "fleet_tags.html",
        "page.tags",
        summary=summary,
        tags=tags,
        tagged_nodes_total=len(tagged_nodes),
        page_total=len(tags),
        fleet_href=build_href(request, "/fleet"),
        nodes_href=build_href(request, "/fleet/nodes"),
        health_href=build_href(request, "/fleet/health"),
        events_href=build_href(request, "/fleet/events"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_health_page(
    request: Request,
    context: ApplicationContext,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    health = await context.fleet_service.health_view()
    for node in health["at_risk"]:
        node["detail_href"] = build_href(request, f"/fleet/nodes/{node['node_name']}")
        node["tone"] = build_tone(node.get("health_status") or node.get("runtime_status"))
    return render_page(
        request,
        context,
        "fleet_health.html",
        "page.fleet_health",
        summary=summary,
        health=health,
        page_total=int(health.get("summary", {}).get("total_nodes") or 0),
        fleet_href=build_href(request, "/fleet"),
        nodes_href=build_href(request, "/fleet/nodes"),
        tags_href=build_href(request, "/fleet/tags"),
        events_href=build_href(request, "/fleet/events"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_fleet_events_page(
    request: Request,
    context: ApplicationContext,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    node_name = (request.query_params.get("node_name") or "").strip()
    severity = (request.query_params.get("severity") or "").strip()
    try:
        limit = max(1, min(int(request.query_params.get("limit", "100")), 500))
    except ValueError:
        limit = 100
    events = decorate_event_rows(await context.fleet_service.list_events(limit=limit))
    if node_name:
        events = [item for item in events if node_name in list(item.get("nodes") or [])]
    if severity:
        events = [item for item in events if str(item.get("severity") or "") == severity]
    nodes = await context.fleet_service.list_nodes()
    node_options = sorted({str(item.get("node_name") or "") for item in nodes if item.get("node_name")})
    filters = {"node_name": node_name, "severity": severity, "limit": limit}
    return render_page(
        request,
        context,
        "fleet_events.html",
        "page.fleet_events",
        summary=summary,
        events=events,
        node_options=node_options,
        levels=["info", "warning", "error", "critical"],
        filters=filters,
        clear_events_href=build_href(request, "/fleet/events"),
        page_total=len(events),
        fleet_href=build_href(request, "/fleet"),
        nodes_href=build_href(request, "/fleet/nodes"),
        tags_href=build_href(request, "/fleet/tags"),
        health_href=build_href(request, "/fleet/health"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_api_docs_page(
    request: Request,
    context: ApplicationContext,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    base_url = str(request.base_url).rstrip("/")
    api_base = f"{base_url}/api"
    endpoints = [
        {"label": "Fleet Overview", "path": "/api/fleet/overview"},
        {"label": "Fleet Health", "path": "/api/fleet/health"},
        {"label": "Fleet Events", "path": "/api/fleet/events"},
        {"label": "Topology", "path": "/api/topology"},
        {"label": "Metrics", "path": "/metrics"},
    ]
    examples = {
        "fleet": f'curl -H "X-Hearth-Token: <token>" {api_base}/fleet/overview',
        "events": f'curl -H "X-Hearth-Token: <token>" "{api_base}/fleet/events?limit=20"',
        "topology": f'curl -H "X-Hearth-Token: <token>" {api_base}/topology',
    }
    return render_page(
        request,
        context,
        "api_docs.html",
        "page.api_docs",
        summary=summary,
        api_base=api_base,
        swagger_href="/docs",
        redoc_href="/redoc",
        openapi_href="/openapi.json",
        examples=examples,
        endpoints=endpoints,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_security_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    client_host = request.client.host if request.client else None
    client_zone = classify_client_host(client_host)
    headers = [
        {
            "name": name,
            "value": value,
            "active": bool(value),
            "status": bool_label(bool(value)),
        }
        for name, value in SECURITY_HEADERS.items()
    ]
    findings = build_security_findings(context)
    token_count = len(context.security_service.list_api_tokens())
    return render_page(
        request,
        context,
        "security.html",
        "page.security",
        notice=notice,
        summary=summary,
        client_host=client_host or "-",
        client_zone=client_zone,
        access_status="protected" if auth_is_enabled(context) else "open",
        auth_mode_value=context.settings.web.auth_mode or "unknown",
        token_status="enabled" if token_count else "disabled",
        token_count=token_count,
        allow_lan_state=bool_label(context.settings.security.allow_lan),
        allow_wan_state=bool_label(context.settings.security.allow_wan),
        watchdog_state=bool_label(context.settings.monitor.watchdog_enabled),
        auto_restart_runtime_state=bool_label(context.settings.monitor.auto_restart_runtime),
        auto_restart_interface_state=bool_label(context.settings.monitor.auto_restart_interface),
        restart_cooldown_sec=context.settings.monitor.restart_cooldown_sec,
        browser_headers=headers,
        browser_header_count=sum(1 for item in headers if item["active"]),
        findings=findings,
        metrics_href=build_href(request, "/metrics"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_audit_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    entries = context.database.list_events(limit=400)
    events, filters, levels, sources = filter_audit_entries(request, entries)
    return render_page(
        request,
        context,
        "audit.html",
        "page.audit",
        notice=notice,
        summary=summary,
        events=events,
        levels=levels,
        sources=sources,
        filters=filters,
        clear_audit_href=build_href(request, "/audit"),
        page_total=len(events),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_config_page(
    request: Request,
    context: ApplicationContext,
    raw_text: str | None = None,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    raw_config = context.config_service.show_raw()
    revision_value = request.query_params.get("revision")
    selected_revision = None
    compare_summary = None
    if revision_value:
        try:
            revision_id = int(revision_value)
        except ValueError:
            revision_id = None
        if revision_id is not None:
            selected_revision = context.config_version_service.get_revision(revision_id)
            compare_summary = context.config_version_service.compare_with_current(revision_id)
    editor_raw = raw_config["raw"] if raw_text is None else raw_text
    if raw_text is None and selected_revision:
        editor_raw = selected_revision["raw_text"]
    return render_page(
        request,
        context,
        "config.html",
        "page.config",
        config_path=raw_config["path"],
        raw=editor_raw,
        revisions=context.config_version_service.list_revisions(limit=12),
        selected_revision=selected_revision,
        compare_summary=compare_summary,
        config_history_href=build_href(request, "/config/history"),
        config_review_href=build_href(request, f"/config/review/{selected_revision['id']}") if selected_revision else None,
        notice=notice,
        result=result,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_config_history_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    revisions = context.config_version_service.list_revisions(limit=50)
    for revision in revisions:
        revision["review_href"] = build_href(request, f"/config/review/{revision['id']}")
    return render_page(
        request,
        context,
        "config_history.html",
        "page.config_history",
        revisions=revisions,
        notice=notice,
        result=result,
        config_href=build_href(request, "/config"),
        header_state=build_header_state(summary),
        shell_summary=summary,
        page_total=len(revisions),
    )


async def render_config_review_page(
    request: Request,
    context: ApplicationContext,
    revision_id: int,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    revision = context.config_version_service.get_revision(revision_id)
    compare_summary = context.config_version_service.compare_with_current(revision_id) if revision else None
    return render_page(
        request,
        context,
        "config_review.html",
        "page.config_review",
        revision=revision,
        compare_summary=compare_summary,
        notice=notice,
        result=result,
        config_href=build_href(request, "/config"),
        config_history_href=build_href(request, "/config/history"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_backup_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    archives = [
        {
            "path": archive,
            "name": Path(archive).name,
            "detail_href": build_href_with_query(request, "/backup/detail", archive=archive),
        }
        for archive in context.backup_service.list_archives()
    ]
    snapshots = context.backup_service.list_snapshots()
    for item in snapshots:
        item["detail_href"] = build_href_with_query(request, "/backup/detail", archive=item.get("archive_path"))
    dr_helper = context.backup_service.disaster_recovery_helper()
    return render_page(
        request,
        context,
        "backup.html",
        "page.backup",
        plan=context.backup_service.export_plan(),
        archives=archives,
        snapshots=snapshots,
        dr_helper=dr_helper,
        notice=notice,
        result=result,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_backup_detail_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    archive_path = str(request.query_params.get("archive") or "").strip()
    detail = context.backup_service.inspect_archive(archive_path) if archive_path else None
    dr_helper = context.backup_service.disaster_recovery_helper(archive_path=archive_path or None) if archive_path else None
    if detail is not None:
        detail["size_pretty"] = format_bytes(int(detail.get("size_bytes") or 0))
    return render_page(
        request,
        context,
        "backup_detail.html",
        "page.backup_detail",
        detail=detail,
        dr_helper=dr_helper,
        notice=notice,
        backup_href=build_href(request, "/backup"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_system_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=True)
    system_info = build_system_snapshot(context, summary)
    return render_page(
        request,
        context,
        "system.html",
        "page.system",
        summary=summary,
        system_info=system_info,
        notice=notice,
        result=result,
        header_state=build_header_state(summary),
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_dashboard_page(request, context)


@router.get("/interfaces", response_class=HTMLResponse)
async def interfaces_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_interfaces_page(request, context)


@router.get("/interfaces/{name}", response_class=HTMLResponse)
async def interface_detail_page(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_interface_detail_page(request, context, name)


@router.post("/interfaces/{name}/control", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def interface_control(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    form = await read_form_data(request)
    action = str(form.get("action", "")).lower()
    selected_name = str(form.get("selected") or name)
    return_view = str(form.get("view") or "list").lower()
    try:
        if action == "start":
            result = await context.interface_service.start(name)
            notice_key = "notice.interface_started"
        elif action == "stop":
            result = await context.interface_service.stop(name)
            notice_key = "notice.interface_stopped"
        elif action == "restart":
            result = await context.interface_service.restart(name)
            notice_key = "notice.interface_restarted"
        else:
            raise ValueError(f"unsupported action: {action}")
        locale = resolve_locale(request)
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        if return_view == "detail":
            return await render_interface_detail_page(request, context, name, notice=notice, result=result)
        return await render_interfaces_page(request, context, selected_name=selected_name, notice=notice, result=result)
    except Exception as exc:
        locale = resolve_locale(request)
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        if return_view == "detail":
            return await render_interface_detail_page(request, context, name, notice=notice)
        return await render_interfaces_page(request, context, selected_name=selected_name, notice=notice)


@router.get("/peers", response_class=HTMLResponse)
async def peers_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_peers_page(request, context)


@router.get("/peers/{peer_hash}", response_class=HTMLResponse)
async def peer_detail_page(peer_hash: str, request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_peer_detail_page(request, context, peer_hash)


@router.get("/routes", response_class=HTMLResponse)
async def routes_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_routes_page(request, context)


@router.get("/routes/{destination_hash}", response_class=HTMLResponse)
async def route_detail_page(destination_hash: str, request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_route_detail_page(request, context, destination_hash)


@router.get("/announces", response_class=HTMLResponse)
async def announces_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_announces_page(request, context)


@router.get("/announces/{announce_id}", response_class=HTMLResponse)
async def announce_detail_page(announce_id: int, request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_announce_detail_page(request, context, announce_id)


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_logs_page(request, context)


@router.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_timeline_page(request, context)


@router.get("/health", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def health_page(request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_health_page(request, context)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    return await render_login_page(request, context)


@router.post("/login", response_class=HTMLResponse)
async def login_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    form = await read_form_data(request)
    next_path = normalize_next_path(form.get("next") or request.query_params.get("next") or "/profile")
    locale = resolve_locale(request)
    client_host = request.client.host if request.client else None
    if not auth_is_enabled(context):
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "auth.not_required"))
        return await render_login_page(request, context, notice=notice, next_path=next_path)

    token = str(form.get("token") or "").strip()
    principal = context.security_service.authenticate_token(token) if token else None
    if principal:
        context.database.record_event(
            "auth.login_succeeded",
            "admin token login succeeded",
            source="web_auth",
            payload={"client_host": client_host, "next": next_path, "subject": principal.get("subject"), "role": principal.get("role")},
        )
        response = RedirectResponse(build_href(request, next_path), status_code=303)
        set_admin_token_cookie(response, token)
        return finalize_page_response(request, response, context)

    context.database.record_event(
        "auth.login_failed",
        "admin token login failed",
        severity="warning",
        source="web_auth",
        payload={"client_host": client_host, "next": next_path},
    )
    notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "auth.login_failed"))
    return await render_login_page(request, context, notice=notice, next_path=next_path, status_code=401)


@router.post("/logout", response_class=HTMLResponse)
async def logout_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> Response:
    client_host = request.client.host if request.client else None
    context.database.record_event(
        "auth.logout",
        "admin token session logged out",
        source="web_auth",
        payload={"client_host": client_host},
    )
    response = RedirectResponse(build_href(request, "/login"), status_code=303)
    clear_admin_token_cookie(response)
    return finalize_page_response(request, response, context)


@router.get("/maintenance", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def maintenance_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_maintenance_page(request, context)


@router.post("/maintenance", response_class=HTMLResponse, dependencies=[Depends(require_permission("maintenance"))])
async def maintenance_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "enable")).lower()
    locale = resolve_locale(request)
    try:
        if action == "enable":
            reason = str(form.get("reason") or "").strip() or None
            try:
                until_hours = max(0, int(form.get("until_hours") or 0))
            except ValueError:
                until_hours = 0
            until_at = datetime.now(timezone.utc) + timedelta(hours=until_hours) if until_hours else None
            result = context.maintenance_service.enable(reason=reason, until_at=until_at, actor="web")
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.maintenance_enabled"))
        elif action == "disable":
            result = context.maintenance_service.disable(actor="web")
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.maintenance_disabled"))
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_maintenance_page(request, context, notice=notice)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_maintenance_page(request, context, notice=notice)


@router.get("/profile", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def profile_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_profile_page(request, context)


@router.get("/users", response_class=HTMLResponse, dependencies=[Depends(require_permission("security"))])
async def users_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_users_page(request, context)


@router.post("/users", response_class=HTMLResponse, dependencies=[Depends(require_permission("security"))])
async def users_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "create_user")).lower()
    username = str(form.get("username") or "").strip()
    locale = resolve_locale(request)
    try:
        if action == "create_user":
            result = context.security_service.create_user(
                username=username,
                display_name=str(form.get("display_name") or "").strip() or None,
                role=str(form.get("role") or "viewer"),
            )
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.user_created"))
        elif action == "enable_user":
            result = context.security_service.set_user_enabled(username, True)
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.user_updated"))
        elif action == "disable_user":
            result = context.security_service.set_user_enabled(username, False)
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.user_updated"))
        elif action == "set_role":
            result = context.security_service.set_user_role(username, str(form.get("role") or "viewer"))
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.user_updated"))
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_users_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_users_page(request, context, notice=notice)


@router.get("/roles", response_class=HTMLResponse, dependencies=[Depends(require_permission("security"))])
async def roles_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_roles_page(request, context)


@router.post("/roles", response_class=HTMLResponse, dependencies=[Depends(require_permission("security"))])
async def roles_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "create_role")).lower()
    role_name = str(form.get("role_name") or form.get("name") or "").strip()
    locale = resolve_locale(request)
    try:
        if action == "create_role":
            result = context.security_service.create_role(
                name=str(form.get("name") or "").strip(),
                label=str(form.get("label") or "").strip() or None,
                description=str(form.get("description") or "").strip() or None,
                permissions=parse_csv_list(form.get("permissions")),
            )
            notice = make_notice(NOTICE_KIND_SUCCESS, "Role created.")
        elif action == "update_role":
            result = context.security_service.update_role(
                role_name,
                label=str(form.get("label") or "").strip() or None,
                description=str(form.get("description") or "").strip() or None,
                permissions=parse_csv_list(form.get("permissions")),
            )
            notice = make_notice(NOTICE_KIND_SUCCESS, "Role updated.")
        elif action == "delete_role":
            result = context.security_service.delete_role(role_name)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Role deleted.")
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_roles_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_roles_page(request, context, notice=notice)
        response.status_code = 400
        return response


@router.get("/tokens", response_class=HTMLResponse, dependencies=[Depends(require_permission("tokens"))])
async def tokens_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_tokens_page(request, context)


@router.post("/tokens", response_class=HTMLResponse, dependencies=[Depends(require_permission("tokens"))])
async def tokens_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "create_token")).lower()
    token_name = str(form.get("token_name") or "").strip()
    locale = resolve_locale(request)
    try:
        if action == "create_token":
            try:
                expires_days = max(0, int(form.get("expires_days") or 0))
            except ValueError:
                expires_days = 0
            scopes = [item.strip() for item in str(form.get("scopes") or "").split(",") if item.strip()]
            token = context.security_service.create_api_token(
                token_name=token_name,
                owner_username=str(form.get("owner_username") or "").strip() or None,
                role=str(form.get("role") or "viewer"),
                scopes=scopes,
                expires_in_days=expires_days or None,
            )
            result = {"token": token}
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.token_created"))
        elif action == "enable_token":
            result = context.security_service.set_api_token_enabled(token_name, True)
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.token_updated"))
        elif action == "disable_token":
            result = context.security_service.set_api_token_enabled(token_name, False)
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.token_updated"))
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_tokens_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_tokens_page(request, context, notice=notice)


@router.get("/plugins", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def plugins_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_plugins_page(request, context)


@router.get("/plugin-sources", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def plugin_sources_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_plugin_sources_page(request, context)


@router.post("/plugin-sources", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def plugin_sources_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    locale = resolve_locale(request)
    try:
        result = context.plugin_service.refresh_sources()
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.plugin_sources_refreshed"))
        return await render_plugin_sources_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_plugin_sources_page(request, context, notice=notice)
        response.status_code = 400
        return response


@router.get("/plugins/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def plugin_detail_page(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_plugin_detail_page(request, context, name)


@router.post("/plugins/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def plugin_detail_page_post(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action") or "enable").lower()
    locale = resolve_locale(request)
    try:
        if action in {"enable", "disable"}:
            enabled = action == "enable"
            result = context.plugin_service.set_plugin_enabled(name, enabled)
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.plugin_updated"))
        elif action == "install":
            enable = str(form.get("enabled", "true")).lower() not in {"0", "false", "off", "no"}
            result = context.plugin_service.install_plugin(name, enable=enable)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Plugin installed.")
        elif action == "update":
            enable_value = str(form.get("enabled") or "").strip().lower()
            enable = None if not enable_value else enable_value in {"1", "true", "on", "yes"}
            result = context.plugin_service.update_plugin(name, enable=enable)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Plugin updated from catalog.")
        elif action == "uninstall":
            remove_dependents = str(form.get("remove_dependents", "")).lower() in {"1", "true", "on", "yes"}
            result = context.plugin_service.uninstall_plugin(name, remove_dependents=remove_dependents)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Plugin uninstalled.")
        elif action == "refresh_sources":
            result = context.plugin_service.refresh_sources()
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.plugin_sources_refreshed"))
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_plugin_detail_page(request, context, name, notice=notice, result=result)
    except LookupError as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_plugins_page(request, context, notice=notice)
        response.status_code = 404
        return response
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_plugin_detail_page(request, context, name, notice=notice)
        response.status_code = 400
        return response


@router.get("/services", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def services_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_services_page(request, context)


@router.get("/services/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def service_detail_page(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_service_detail_page(request, context, name)


@router.post("/services/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def service_detail_page_post(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action") or "sync").lower()
    locale = resolve_locale(request)
    try:
        result = await context.service_host_service.control(name, action)
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.service_updated"))
        return await render_service_detail_page(request, context, name, notice=notice, result=result)
    except LookupError as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_services_page(request, context, notice=notice)
        response.status_code = 404
        return response
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_service_detail_page(request, context, name, notice=notice)
        response.status_code = 400
        return response


@router.get("/fleet", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_dashboard_page(request, context)


@router.get("/fleet/nodes", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_nodes_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_nodes_page(request, context)


@router.post("/fleet/nodes", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def fleet_nodes_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    try:
        result = await context.fleet_service.register_node(
            node_name=str(form.get("node_name") or "").strip(),
            group_name=str(form.get("group_name") or "").strip() or None,
            tags=str(form.get("tags") or ""),
            version=str(form.get("version") or "").strip() or None,
            health_status=str(form.get("health_status") or "warning"),
            runtime_status=str(form.get("runtime_status") or "stopped"),
            region=str(form.get("region") or "").strip() or None,
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.fleet_node_saved"))
        return await render_fleet_nodes_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_fleet_nodes_page(request, context, notice=notice)


@router.get("/fleet/groups", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_groups_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_groups_page(request, context)


@router.post("/fleet/groups", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def fleet_groups_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    try:
        result = context.fleet_service.create_group(
            name=str(form.get("name") or "").strip(),
            description=str(form.get("description") or "").strip() or None,
            group_type=str(form.get("group_type") or "custom"),
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.group_saved"))
        return await render_fleet_groups_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_fleet_groups_page(request, context, notice=notice)


@router.get("/fleet/templates", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_templates_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_templates_page(request, context)


@router.post("/fleet/templates", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def fleet_templates_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    try:
        result = context.fleet_service.create_template(
            name=str(form.get("name") or "").strip(),
            description=str(form.get("description") or "").strip() or None,
            template_text=str(form.get("template_text") or "").strip(),
            target_group=str(form.get("target_group") or "").strip() or None,
            target_nodes=str(form.get("target_nodes") or ""),
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.template_saved"))
        return await render_fleet_templates_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_fleet_templates_page(request, context, notice=notice)


@router.get("/fleet/nodes/{node_name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_node_detail_page(node_name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_node_detail_page(request, context, node_name)


@router.get("/fleet/tags", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_tags_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_tags_page(request, context)


@router.get("/fleet/health", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_health_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_health_page(request, context)


@router.get("/fleet/events", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def fleet_events_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_fleet_events_page(request, context)


@router.get("/api-docs", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def api_docs_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_api_docs_page(request, context)


@router.get("/security", response_class=HTMLResponse, dependencies=[Depends(require_permission("security"))])
async def security_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_security_page(request, context)


@router.get("/audit", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def audit_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_audit_page(request, context)


@router.get("/config", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_config_page(request, context)


@router.get("/config/history", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_history_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_config_history_page(request, context)


@router.post("/config/history", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_history_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    action = str(form.get("action", "restore")).lower()
    try:
        revision_id = int(str(form.get("revision_id", "0") or "0"))
        revision = context.config_version_service.get_revision(revision_id)
        if revision is None:
            raise ValueError("revision not found")
        if action != "restore":
            raise ValueError(f"unsupported action: {action}")
        result = context.config_service.save_raw(
            revision["raw_text"],
            source="restore",
            actor="config_history_web",
            summary=f"restored revision #{revision_id}",
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.config_restored"))
        return await render_config_history_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_config_history_page(request, context, notice=notice)


@router.get("/config/review/{revision_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_review_page(revision_id: int, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_config_review_page(request, context, revision_id)


@router.post("/config/review/{revision_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_review_page_post(revision_id: int, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    locale = resolve_locale(request)
    try:
        revision = context.config_version_service.get_revision(revision_id)
        if revision is None:
            raise ValueError("revision not found")
        result = context.config_service.save_raw(
            revision["raw_text"],
            source="restore",
            actor="config_review_web",
            summary=f"restored revision #{revision_id}",
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.config_restored"))
        return await render_config_review_page(request, context, revision_id, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_config_review_page(request, context, revision_id, notice=notice)


@router.post("/config", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def config_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "validate")).lower()
    raw_text = str(form.get("raw", ""))
    locale = resolve_locale(request)
    try:
        if action == "validate":
            result = context.config_service.validate_raw(raw_text)
            notice_key = "notice.config_valid" if result.get("valid") else "notice.config_invalid"
        elif action == "save":
            result = context.config_service.save_raw(raw_text)
            notice_key = "notice.config_saved" if result.get("saved") else "notice.config_invalid"
        elif action == "restart":
            result = await context.node_service.restart(reason="web-config")
            notice_key = "notice.node_restarted"
        else:
            raise ValueError(f"unsupported action: {action}")
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        return await render_config_page(request, context, raw_text=raw_text, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_config_page(request, context, raw_text=raw_text, notice=notice)


@router.get("/backup", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def backup_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_backup_page(request, context)


@router.get("/backup/detail", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def backup_detail_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_backup_detail_page(request, context)


@router.post("/backup", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def backup_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "export")).lower()
    locale = resolve_locale(request)
    try:
        if action == "export":
            destination_path = str(form.get("destination_path", "")).strip() or None
            result = context.backup_service.export(destination_path=destination_path)
            notice_key = "notice.backup_exported"
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        elif action == "import":
            archive_path = str(form.get("archive_path", "")).strip()
            result = context.backup_service.import_archive(archive_path)
            notice_key = "notice.backup_imported"
            notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        elif action == "snapshot":
            destination_path = str(form.get("destination_path", "")).strip() or None
            result = context.backup_service.create_snapshot(destination_path=destination_path)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Snapshot created.")
        elif action == "prune":
            try:
                keep = max(0, int(form.get("keep") or 10))
            except ValueError:
                keep = 10
            max_age_value = str(form.get("max_age_days") or "").strip()
            max_age_days = int(max_age_value) if max_age_value else None
            result = context.backup_service.prune_snapshots(keep=keep, max_age_days=max_age_days)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Snapshots pruned.")
        elif action == "dr_helper":
            archive_path = str(form.get("archive_path", "")).strip() or None
            result = context.backup_service.disaster_recovery_helper(archive_path=archive_path)
            notice = make_notice(NOTICE_KIND_SUCCESS, "Disaster recovery checklist prepared.")
        else:
            raise ValueError(f"unsupported action: {action}")
        return await render_backup_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_backup_page(request, context, notice=notice)


@router.get("/system", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def system_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_system_page(request, context)


@router.post("/system", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def system_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action", "restart")).lower()
    locale = resolve_locale(request)
    try:
        if action == "start":
            result = await context.node_service.start(reason="web-system")
            notice_key = "notice.node_started"
        elif action == "stop":
            result = await context.node_service.stop(reason="web-system")
            notice_key = "notice.node_stopped"
        elif action == "restart":
            result = await context.node_service.restart(reason="web-system")
            notice_key = "notice.node_restarted"
        else:
            raise ValueError(f"unsupported action: {action}")
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        return await render_system_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_system_page(request, context, notice=notice)


async def render_bridges_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    bridges = context.bridge_catalog_service.list_bridges(str(summary.get("runtime_status") or "unknown"))
    for bridge in bridges:
        bridge["tone"] = build_tone(bridge.get("health") or bridge.get("status"))
        bridge["detail_href"] = build_href(request, f"/bridges/{bridge['name']}")
    configured_count = sum(1 for bridge in bridges if bridge.get("configured"))
    enabled_count = sum(1 for bridge in bridges if bridge.get("enabled"))
    running_count = sum(1 for bridge in bridges if bridge.get("status") == "running")
    return render_page(
        request,
        context,
        "bridges.html",
        "page.bridges",
        notice=notice,
        summary=summary,
        bridges=bridges,
        page_total=len(bridges),
        configured_count=configured_count,
        enabled_count=enabled_count,
        running_count=running_count,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_bridge_detail_page(
    request: Request,
    context: ApplicationContext,
    name: str,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    bridge = context.bridge_catalog_service.get_bridge(name, str(summary.get("runtime_status") or "unknown"))
    if bridge is None:
        locale = resolve_locale(request)
        response = await render_bridges_page(
            request,
            context,
            notice=notice or make_notice(NOTICE_KIND_ERROR, translate(locale, "bridges.not_found")),
        )
        response.status_code = 404
        return response
    bridge["tone"] = build_tone(bridge.get("health") or bridge.get("status"))
    for check in bridge.get("health_checks", []):
        check["tone"] = build_tone(str(check.get("status") or "warning"))
    for operation in bridge.get("recent_operations", []):
        operation["tone"] = build_tone(str(operation.get("status") or "warning"))
    return render_page(
        request,
        context,
        "bridge_detail.html",
        "page.bridge_detail",
        notice=notice,
        result=result,
        summary=summary,
        bridge=bridge,
        bridges_href=build_href(request, "/bridges"),
        plugin_href=build_href(request, f"/plugins/{bridge['plugin_name']}") if bridge.get("configured") else None,
        plugin_sources_href=build_href(request, "/plugin-sources"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_metrics_dashboard_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    history_now = datetime.now().astimezone()
    history_samples = context.database.list_interface_metric_snapshots(
        history_now.astimezone(timezone.utc) - timedelta(hours=26)
    )
    activity_history = summarize_activity_history(history_samples, now=history_now)
    interfaces = list(summary.get("interfaces", []))
    for interface in interfaces:
        metrics = dict(interface.get("metrics") or {})
        interface["tone"] = build_tone(interface.get("status") or interface.get("health_status"))
        interface["rx_packets_display"] = format_counter(metrics.get("rx_packets"))
        interface["tx_packets_display"] = format_counter(metrics.get("tx_packets"))
        interface["error_count_display"] = format_counter(metrics.get("error_count"))
    return render_page(
        request,
        context,
        "metrics_dashboard.html",
        "page.metrics",
        notice=notice,
        summary=summary,
        interfaces=interfaces,
        header_state=build_header_state(summary),
        activity_bars=build_activity_bars(activity_history),
        traffic_snapshot=build_traffic_snapshot(activity_history),
        system_info=build_system_snapshot(context, summary),
        prometheus_href=build_href(request, "/metrics"),
        metrics_summary_href=build_href(request, "/api/metrics/summary"),
        shell_summary=summary,
    )


async def render_alerts_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    alert_snapshot = await context.alert_service.refresh(summary)
    alerts = list(alert_snapshot.get("alerts") or [])
    alerts = sorted(alerts, key=lambda item: str(item.get("created_at") or ""), reverse=True)
    for alert in alerts:
        alert["tone"] = build_tone(alert.get("severity"))
    alert_history = list(alert_snapshot.get("history") or [])
    for row in alert_history:
        row["tone"] = build_tone(row.get("severity"))
    return render_page(
        request,
        context,
        "alerts.html",
        "page.alerts",
        notice=notice,
        summary=summary,
        alerts=alerts,
        alert_summary=dict(alert_snapshot.get("summary") or context.alert_service.summarize(alerts)),
        alert_history=alert_history,
        alert_hooks=dict(alert_snapshot.get("hooks") or {}),
        rule_sources=list(alert_snapshot.get("rule_sources") or []),
        security_findings=build_security_findings(context),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_diagnostics_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    diagnostics = await context.diagnostics_service.snapshot(summary)
    recent_events = decorate_event_rows(list(diagnostics.get("recent_events") or []))
    restart_history = list(diagnostics.get("restart_history") or [])
    latest_revision = (diagnostics.get("config_revisions") or {}).get("latest")
    return render_page(
        request,
        context,
        "diagnostics.html",
        "page.diagnostics",
        notice=notice,
        summary=summary,
        diagnostics=diagnostics,
        recent_events=recent_events,
        restart_history=restart_history,
        latest_revision_pretty=json.dumps(latest_revision, ensure_ascii=False, indent=2) if latest_revision else None,
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


@router.get("/bridges", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def bridges_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_bridges_page(request, context)


@router.get("/bridges/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def bridge_detail_page(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_bridge_detail_page(request, context, name)


@router.post("/bridges/{name}", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def bridge_detail_page_post(name: str, request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    action = str(form.get("action") or "sync").lower()
    locale = resolve_locale(request)
    summary = await context.node_service.status_summary(persist=False)
    try:
        result = context.bridge_catalog_service.control(name, action, str(summary.get("runtime_status") or "unknown"))
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.bridge_updated"))
        return await render_bridge_detail_page(request, context, name, notice=notice, result=result)
    except LookupError as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_bridges_page(request, context, notice=notice)
        response.status_code = 404
        return response
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_bridge_detail_page(request, context, name, notice=notice)
        response.status_code = 400
        return response


@router.get("/metrics-dashboard", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def metrics_dashboard_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_metrics_dashboard_page(request, context)


@router.get("/alerts", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def alerts_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_alerts_page(request, context)


@router.get("/diagnostics", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def diagnostics_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_diagnostics_page(request, context)


async def render_topology_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    topology = await context.topology_service.snapshot()
    return render_page(
        request,
        context,
        "topology.html",
        "page.topology",
        notice=notice,
        summary=summary,
        topology=topology,
        network_map_href=build_href(request, "/network-map"),
        route_heatmap_href=build_href(request, "/route-heatmap"),
        critical_nodes_href=build_href(request, "/critical-nodes"),
        network_insights_href=build_href(request, "/network-insights"),
        path_changes_href=build_href(request, "/path-changes"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_network_map_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    network_map = await context.topology_service.network_map()
    return render_page(
        request,
        context,
        "network_map.html",
        "page.network_map",
        notice=notice,
        summary=summary,
        network_map=network_map,
        topology_href=build_href(request, "/topology"),
        route_heatmap_href=build_href(request, "/route-heatmap"),
        critical_nodes_href=build_href(request, "/critical-nodes"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_route_heatmap_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    heatmap = await context.topology_service.route_heatmap()
    for row in heatmap.get("rows", []):
        row["tone"] = build_tone(row.get("health_status") or row.get("status"))
        row["intensity_width"] = f"max(10%, {max(int(row.get('intensity', 0)), 10)}%)"
    return render_page(
        request,
        context,
        "route_heatmap.html",
        "page.route_heatmap",
        notice=notice,
        summary=summary,
        heatmap=heatmap,
        topology_href=build_href(request, "/topology"),
        network_map_href=build_href(request, "/network-map"),
        network_insights_href=build_href(request, "/network-insights"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_critical_nodes_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    nodes = await context.topology_service.critical_nodes()
    return render_page(
        request,
        context,
        "critical_nodes.html",
        "page.critical_nodes",
        notice=notice,
        summary=summary,
        nodes=nodes,
        topology_href=build_href(request, "/topology"),
        network_map_href=build_href(request, "/network-map"),
        network_insights_href=build_href(request, "/network-insights"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_network_insights_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    insights = await context.topology_service.insights()
    for item in insights.get("findings", []):
        item["tone"] = build_tone(item.get("severity"))
    return render_page(
        request,
        context,
        "network_insights.html",
        "page.network_insights",
        notice=notice,
        summary=summary,
        insights=insights,
        topology_href=build_href(request, "/topology"),
        critical_nodes_href=build_href(request, "/critical-nodes"),
        route_heatmap_href=build_href(request, "/route-heatmap"),
        path_changes_href=build_href(request, "/path-changes"),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_path_changes_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    try:
        recent_limit = max(1, min(int(request.query_params.get("recent_limit", "80")), 500))
    except ValueError:
        recent_limit = 80
    try:
        since_minutes = max(0, min(int(request.query_params.get("since_minutes", "10080")), 43200))
    except ValueError:
        since_minutes = 10080

    path_changes = await context.topology_service.path_changes(recent_limit=recent_limit, since_minutes=since_minutes)
    for item in path_changes.get("recent_changes", []):
        change_type = str(item.get("change_type") or "changed")
        item["tone"] = build_tone("warning" if change_type in {"changed", "removed"} else "info")
    for item in path_changes.get("destinations", []):
        if int(item.get("volatility_score") or 0) >= 70:
            item["tone"] = "danger"
        elif int(item.get("volatility_score") or 0) >= 35:
            item["tone"] = "warning"
        else:
            item["tone"] = "info"
    filters = {"recent_limit": recent_limit, "since_minutes": since_minutes}
    return render_page(
        request,
        context,
        "path_changes.html",
        "page.path_changes",
        notice=notice,
        summary=summary,
        path_changes=path_changes,
        filters=filters,
        topology_href=build_href(request, "/topology"),
        network_insights_href=build_href(request, "/network-insights"),
        clear_path_changes_href=build_href(request, "/path-changes"),
        header_state=build_header_state(summary),
        shell_summary=summary,
        page_total=int(path_changes.get("total_changes") or 0),
    )


@router.get("/topology", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def topology_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_topology_page(request, context)


@router.get("/network-map", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def network_map_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_network_map_page(request, context)


@router.get("/route-heatmap", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def route_heatmap_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_route_heatmap_page(request, context)


@router.get("/critical-nodes", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def critical_nodes_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_critical_nodes_page(request, context)


@router.get("/network-insights", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def network_insights_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_network_insights_page(request, context)


@router.get("/path-changes", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def path_changes_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_path_changes_page(request, context)


async def render_rollout_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    rollouts = await context.rollout_service.list_rollouts()
    templates = await context.rollout_service.template_catalog()
    groups = await context.fleet_service.list_groups()
    for item in rollouts:
        item["tone"] = build_tone(item.get("status"))
    return render_page(
        request,
        context,
        "rollout.html",
        "page.rollout",
        notice=notice,
        result=result,
        summary=summary,
        rollouts=rollouts,
        templates=templates,
        groups=groups,
        page_total=len(rollouts),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_remote_logs_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    level = (request.query_params.get("level") or "").strip()
    node_name = (request.query_params.get("node_name") or "").strip()
    try:
        limit = max(1, min(int(request.query_params.get("limit", "100")), 500))
    except ValueError:
        limit = 100
    entries = await context.remote_log_service.list_entries(node_name=node_name or None, level=level or None, limit=limit)
    entries = decorate_event_rows(entries)
    nodes = await context.fleet_service.list_nodes()
    node_options = sorted(
        {
            *[str(item.get("node_name") or "") for item in nodes if item.get("node_name")],
            *[str(item.get("node_name") or "") for item in entries if item.get("node_name")],
        }
    )
    filters = {"level": level, "node_name": node_name, "limit": limit}
    return render_page(
        request,
        context,
        "remote_logs.html",
        "page.remote_logs",
        notice=notice,
        result=result,
        summary=summary,
        logs=entries,
        node_options=node_options,
        levels=["info", "warning", "critical"],
        filters=filters,
        clear_logs_href=build_href(request, "/remote-logs"),
        sync_remote_logs_href=build_href(request, "/remote-logs"),
        page_total=len(entries),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


async def render_upgrade_page(
    request: Request,
    context: ApplicationContext,
    notice: dict[str, str] | None = None,
    result: dict | None = None,
) -> HTMLResponse:
    summary = await context.node_service.status_summary(persist=False)
    operations = await context.upgrade_service.list_operations()
    groups = await context.fleet_service.list_groups()
    revisions = context.upgrade_service.recent_revisions()
    for item in operations:
        item["tone"] = build_tone(item.get("status"))
    return render_page(
        request,
        context,
        "upgrade.html",
        "page.upgrade",
        notice=notice,
        result=result,
        summary=summary,
        operations=operations,
        groups=groups,
        revisions=revisions,
        page_total=len(operations),
        header_state=build_header_state(summary),
        shell_summary=summary,
    )


@router.get("/rollout", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def rollout_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_rollout_page(request, context)


@router.post("/rollout", response_class=HTMLResponse, dependencies=[Depends(require_permission("configure"))])
async def rollout_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    try:
        result = await context.rollout_service.create_rollout(
            action=str(form.get("action", "apply_template") or "apply_template"),
            template_name=str(form.get("template_name", "")).strip() or None,
            target_group=str(form.get("target_group", "")).strip() or None,
            target_nodes=str(form.get("target_nodes", "")).strip() or None,
            actor="web",
        )
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, "notice.rollout_created"))
        return await render_rollout_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_rollout_page(request, context, notice=notice)


@router.get("/remote-logs", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def remote_logs_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_remote_logs_page(request, context)


@router.post("/remote-logs", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def remote_logs_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    action = str(form.get("action", "sync")).strip().lower()
    try:
        if action != "sync":
            raise ValueError(f"unsupported action: {action}")
        try:
            limit = max(1, min(int(form.get("limit") or 100), 500))
        except ValueError:
            limit = 100
        result = await context.remote_log_service.sync_nodes(limit=limit)
        notice = make_notice(NOTICE_KIND_SUCCESS, "Remote log sync completed.")
        return await render_remote_logs_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        response = await render_remote_logs_page(request, context, notice=notice)
        response.status_code = 400
        return response


@router.get("/upgrade", response_class=HTMLResponse, dependencies=[Depends(require_permission("read"))])
async def upgrade_page(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    return await render_upgrade_page(request, context)


@router.post("/upgrade", response_class=HTMLResponse, dependencies=[Depends(require_permission("operate"))])
async def upgrade_page_post(request: Request, context: ApplicationContext = Depends(get_context)) -> HTMLResponse:
    form = await read_form_data(request)
    locale = resolve_locale(request)
    action = str(form.get("action", "upgrade") or "upgrade").strip().lower()
    enable_maintenance = str(form.get("enable_maintenance", "")).lower() in {"1", "true", "on", "yes"}
    try:
        result = await context.upgrade_service.schedule_operation(
            action=action,
            target_version=str(form.get("target_version", "")).strip() or "unknown",
            channel=str(form.get("channel", "stable")).strip() or "stable",
            target_group=str(form.get("target_group", "")).strip() or None,
            target_nodes=str(form.get("target_nodes", "")).strip() or None,
            notes=str(form.get("notes", "")).strip() or None,
            enable_maintenance=enable_maintenance,
            actor="web",
        )
        notice_key = "notice.rollback_scheduled" if action == "rollback" else "notice.upgrade_scheduled"
        notice = make_notice(NOTICE_KIND_SUCCESS, translate(locale, notice_key))
        return await render_upgrade_page(request, context, notice=notice, result=result)
    except Exception as exc:
        notice = make_notice(NOTICE_KIND_ERROR, translate(locale, "notice.action_failed", error=str(exc)))
        return await render_upgrade_page(request, context, notice=notice)
