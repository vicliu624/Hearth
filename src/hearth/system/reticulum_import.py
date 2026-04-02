from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_BOOL_TRUE = {"yes", "true", "on"}
_BOOL_FALSE = {"no", "false", "off"}
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_FLOAT_PATTERN = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)$")
_INTERFACE_TYPE_MAP = {
    "AutoInterface": "local",
    "TCPInterface": "tcp",
    "TCPClientInterface": "tcp",
    "TCPServerInterface": "tcp",
    "SerialInterface": "serial",
    "RNodeInterface": "rnode",
}


@dataclass(slots=True)
class ImportedReticulumConfig:
    reticulum: dict[str, Any]
    logging: dict[str, Any]
    interfaces: list[dict[str, Any]]


def _strip_inline_comment(line: str) -> str:
    quote: str | None = None
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if quote and char == "\\":
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if quote is None and char in {"#", ";"} and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()


def _split_csv(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0

    for char in value:
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            current.append(char)
            continue

        if quote is None:
            if char in "[{(":
                depth += 1
            elif char in "]})" and depth > 0:
                depth -= 1
            elif char == "," and depth == 0:
                rendered = "".join(current).strip()
                if rendered:
                    parts.append(rendered)
                current = []
                continue

        current.append(char)

    rendered = "".join(current).strip()
    if rendered:
        parts.append(rendered)
    return parts


def parse_reticulum_value(raw_value: str) -> Any:
    value = _strip_inline_comment(raw_value).strip()
    if value == "":
        return ""

    lower = value.lower()
    if lower in _BOOL_TRUE:
        return True
    if lower in _BOOL_FALSE:
        return False
    if lower in {"none", "null"}:
        return None
    if _INTEGER_PATTERN.fullmatch(value):
        return int(value)
    if _FLOAT_PATTERN.fullmatch(value):
        return float(value)

    if value[0] in {'"', "'", "[", "{", "("}:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            pass

    csv_parts = _split_csv(value)
    if len(csv_parts) > 1:
        return [parse_reticulum_value(part) for part in csv_parts]

    return value


def parse_reticulum_config(path: str | Path) -> ImportedReticulumConfig:
    config_path = Path(path).expanduser().resolve()
    text = config_path.read_text(encoding="utf-8")

    reticulum: dict[str, Any] = {}
    logging: dict[str, Any] = {}
    interfaces: list[dict[str, Any]] = []
    current_section: str | None = None
    current_interface: dict[str, Any] | None = None

    def finalize_interface() -> None:
        nonlocal current_interface
        if current_interface is not None:
            interfaces.append(current_interface)
            current_interface = None

    for raw_line in text.splitlines():
        line = _strip_inline_comment(raw_line).strip()
        if not line:
            continue

        if line.startswith("[[") and line.endswith("]]"):
            if current_section != "interfaces":
                continue
            finalize_interface()
            current_interface = {"name": line[2:-2].strip()}
            continue

        if line.startswith("[") and line.endswith("]"):
            finalize_interface()
            current_section = line[1:-1].strip()
            continue

        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = parse_reticulum_value(raw_value)

        if current_interface is not None:
            current_interface[key] = value
        elif current_section == "reticulum":
            reticulum[key] = value
        elif current_section == "logging":
            logging[key] = value

    finalize_interface()
    return ImportedReticulumConfig(reticulum=reticulum, logging=logging, interfaces=interfaces)


def _default_interfaces() -> list[dict[str, Any]]:
    return [
        {
            "name": "local_lan",
            "type": "local",
            "enabled": True,
            "role": "transport",
            "devices": ["eth0", "wlan0", "eno1", "enp0s31f6"],
            "discovery_port": 29716,
            "data_port": 42671,
        }
    ]


def _convert_interface(interface_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(interface_payload)
    original_type = str(payload.pop("type", "")).strip()
    converted_type = _INTERFACE_TYPE_MAP.get(original_type, "custom")
    converted: dict[str, Any] = {
        "name": str(payload.pop("name", "interface")).strip() or "interface",
        "type": converted_type,
        "enabled": bool(payload.get("enabled", True)),
    }
    converted.update(payload)

    if converted_type == "local":
        for key in ("devices", "ignored_devices"):
            value = converted.get(key)
            if isinstance(value, str) and value.strip():
                converted[key] = [value.strip()]

    if converted_type == "custom" and original_type:
        converted["reticulum_type"] = original_type

    return converted


def build_deployment_payload(
    *,
    data_dir: str | Path,
    host: str,
    port: int,
    admin_token: str,
    timezone: str,
    node_name: str,
    backend: str,
    import_path: str | Path | None = None,
    reticulum_config_dir: str | Path | None = None,
    identity_path: str | Path | None = None,
    managed_command: str | None = None,
) -> dict[str, Any]:
    data_dir_path = Path(data_dir).expanduser().resolve()
    imported: ImportedReticulumConfig | None = None

    if import_path is not None:
        imported = parse_reticulum_config(import_path)

    if reticulum_config_dir is not None:
        reticulum_config_path = Path(reticulum_config_dir).expanduser().resolve()
    elif import_path is not None:
        reticulum_config_path = Path(import_path).expanduser().resolve().parent
    else:
        reticulum_config_path = data_dir_path / "reticulum-config"

    if identity_path is not None:
        resolved_identity_path = Path(identity_path).expanduser().resolve()
    elif import_path is not None or reticulum_config_dir is not None:
        resolved_identity_path = reticulum_config_path / "identity"
    else:
        resolved_identity_path = data_dir_path / "identity"

    imported_reticulum = imported.reticulum if imported else {}
    imported_logging = imported.logging if imported else {}
    interfaces = [_convert_interface(item) for item in imported.interfaces] if imported else _default_interfaces()

    return {
        "system": {
            "node_name": node_name,
            "data_dir": str(data_dir_path),
            "log_level": "INFO",
            "timezone": timezone,
        },
        "reticulum": {
            "enabled": True,
            "config_path": str(reticulum_config_path),
            "identity_path": str(resolved_identity_path),
            "auto_start": True,
            "backend": backend,
            "managed_command": managed_command or "rnsd",
            "render_managed_config": True,
            "transport_enabled": bool(imported_reticulum.get("enable_transport", True)),
            "shared_instance": bool(imported_reticulum.get("share_instance", True)),
            "instance_name": str(imported_reticulum.get("instance_name", "default")),
            "discover_interfaces": bool(imported_reticulum.get("discover_interfaces", False)),
            "autoconnect_discovered_interfaces": int(imported_reticulum.get("autoconnect_discovered_interfaces", 0) or 0),
            "loglevel": int(imported_logging.get("loglevel", 4) or 4),
            "heartbeat_interval_sec": 2,
            "health_timeout_sec": 10,
            "shutdown_timeout_sec": 5,
        },
        "web": {
            "enabled": True,
            "host": host,
            "port": port,
            "auth_mode": "local_token",
        },
        "security": {
            "admin_token": admin_token,
            "allow_lan": True,
            "allow_wan": False,
        },
        "monitor": {
            "health_check_interval_sec": 15,
            "metrics_refresh_sec": 10,
            "watchdog_enabled": True,
            "auto_restart_runtime": True,
            "auto_restart_interface": True,
            "restart_cooldown_sec": 30,
        },
        "alerts": {
            "webhook_enabled": False,
            "include_resolved": True,
            "delivery_timeout_sec": 5,
            "sync_interval_sec": 30,
        },
        "interfaces": interfaces,
    }


__all__ = [
    "ImportedReticulumConfig",
    "build_deployment_payload",
    "parse_reticulum_config",
    "parse_reticulum_value",
]
