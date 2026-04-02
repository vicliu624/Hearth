from __future__ import annotations

from pathlib import Path
from typing import Any

from hearth.core.config import HearthSettings, InterfaceSettings


class RuntimeConfigBridge:
    def __init__(self, settings: HearthSettings) -> None:
        self.settings = settings

    def _bool(self, value: Any) -> str:
        return "yes" if bool(value) else "no"

    def _line(self, key: str, value: Any) -> str:
        if isinstance(value, bool):
            rendered = self._bool(value)
        elif isinstance(value, (int, float)):
            rendered = str(value)
        elif isinstance(value, (list, tuple, set)):
            rendered = ",".join(str(item) for item in value if str(item).strip())
        else:
            rendered = str(value)
        return f"  {key} = {rendered}"

    def _common_options(self, payload: dict[str, Any], *, enabled_key: str = "enabled") -> list[str]:
        lines = [self._line(enabled_key, payload.get("enabled", True))]
        for key in (
            "mode",
            "network_name",
            "passphrase",
            "announce_cap",
            "bitrate",
            "bootstrap_only",
            "discoverable",
            "discovery_name",
            "announce_interval",
            "reachable_on",
            "discovery_stamp_value",
            "discovery_encrypt",
            "publish_ifac",
            "latitude",
            "longitude",
            "height",
            "discovery_frequency",
            "discovery_bandwidth",
            "discovery_modulation",
            "prefer_ipv6",
            "ifac_size",
        ):
            value = payload.get(key)
            if value is not None and str(value).strip() != "":
                lines.append(self._line(key, value))
        return lines

    def _render_local_interface(self, item: InterfaceSettings) -> list[str]:
        payload = item.model_dump(mode="python")
        lines = [f"  [[{item.name}]]", "    type = AutoInterface"]
        for option in self._common_options(payload):
            lines.append("  " + option)
        mapping = {
            "group_id": "group_id",
            "multicast_address_type": "multicast_address_type",
            "devices": "devices",
            "ignored_devices": "ignored_devices",
            "discovery_scope": "discovery_scope",
            "discovery_port": "discovery_port",
            "data_port": "data_port",
        }
        for source_key, target_key in mapping.items():
            value = payload.get(source_key)
            if value is not None and str(value).strip() != "":
                lines.append("  " + self._line(target_key, value))
        if payload.get("device"):
            lines.append("  " + self._line("devices", [payload.get("device")]))
        if payload.get("subnet"):
            lines.append("  " + self._line("group_id", payload.get("subnet")))
        return lines

    def _render_tcp_interface(self, item: InterfaceSettings) -> list[str]:
        payload = item.model_dump(mode="python")
        host = payload.get("host") or payload.get("target_host") or payload.get("remote")
        port = payload.get("port") or payload.get("target_port") or payload.get("listen_port")
        listen_on = payload.get("listen_on") or payload.get("listen_ip")
        server_mode = bool(listen_on or payload.get("server") or payload.get("device") and not host)
        interface_type = "TCPServerInterface" if server_mode else "TCPClientInterface"

        lines = [f"  [[{item.name}]]", f"    type = {interface_type}"]
        for option in self._common_options(payload):
            lines.append("  " + option)
        if server_mode:
            if payload.get("device"):
                lines.append("  " + self._line("device", payload.get("device")))
            elif listen_on:
                lines.append("  " + self._line("listen_ip", listen_on))
            lines.append("  " + self._line("listen_port", int(port or 4242)))
        else:
            lines.append("  " + self._line("target_host", host or "127.0.0.1"))
            lines.append("  " + self._line("target_port", int(port or 4242)))
            for key in ("kiss_framing", "fixed_mtu", "i2p_tunneled"):
                value = payload.get(key)
                if value is not None and str(value).strip() != "":
                    lines.append("  " + self._line(key, value))
        return lines

    def _render_serial_interface(self, item: InterfaceSettings) -> list[str]:
        payload = item.model_dump(mode="python")
        lines = [f"  [[{item.name}]]", "    type = SerialInterface"]
        for option in self._common_options(payload):
            lines.append("  " + option)
        lines.append("  " + self._line("port", payload.get("device") or payload.get("port")))
        lines.append("  " + self._line("speed", int(payload.get("baudrate") or payload.get("speed") or 115200)))
        for key, default in (("databits", 8), ("parity", "none"), ("stopbits", 1)):
            lines.append("  " + self._line(key, payload.get(key, default)))
        return lines

    def _render_rnode_interface(self, item: InterfaceSettings) -> list[str]:
        payload = item.model_dump(mode="python")
        lines = [f"  [[{item.name}]]", "    type = RNodeInterface"]
        for option in self._common_options(payload):
            lines.append("  " + option)
        lines.append("  " + self._line("port", payload.get("device") or payload.get("port")))
        mapping = {
            "frequency": payload.get("frequency"),
            "bandwidth": payload.get("bandwidth"),
            "txpower": payload.get("txpower"),
            "spreadingfactor": payload.get("spreadingfactor"),
            "codingrate": payload.get("codingrate"),
            "id_callsign": payload.get("id_callsign"),
            "id_interval": payload.get("id_interval"),
            "flow_control": payload.get("flow_control"),
            "airtime_limit_long": payload.get("airtime_limit_long"),
            "airtime_limit_short": payload.get("airtime_limit_short"),
        }
        for key, value in mapping.items():
            if value is not None and str(value).strip() != "":
                lines.append("  " + self._line(key, value))
        return lines

    def _render_custom_interface(self, item: InterfaceSettings) -> list[str]:
        payload = item.model_dump(mode="python")
        interface_type = str(payload.get("reticulum_type") or "PipeInterface")
        lines = [f"  [[{item.name}]]", f"    type = {interface_type}"]
        for option in self._common_options(payload):
            lines.append("  " + option)
        if payload.get("command"):
            lines.append("  " + self._line("command", payload.get("command")))
        if payload.get("respawn_delay") is not None:
            lines.append("  " + self._line("respawn_delay", payload.get("respawn_delay")))
        return lines

    def render(self) -> str:
        lines = [
            "# Managed by Hearth. Changes may be overwritten.",
            "[reticulum]",
            f"  enable_transport = {self._bool(self.settings.reticulum.transport_enabled)}",
            f"  share_instance = {self._bool(self.settings.reticulum.shared_instance)}",
            f"  instance_name = {self.settings.reticulum.instance_name}",
            f"  discover_interfaces = {self._bool(self.settings.reticulum.discover_interfaces)}",
            f"  autoconnect_discovered_interfaces = {self.settings.reticulum.autoconnect_discovered_interfaces}",
            "",
            "[logging]",
            f"  loglevel = {self.settings.reticulum.loglevel}",
            "",
            "[interfaces]",
        ]
        renderers = {
            "local": self._render_local_interface,
            "tcp": self._render_tcp_interface,
            "serial": self._render_serial_interface,
            "rnode": self._render_rnode_interface,
            "custom": self._render_custom_interface,
        }
        for item in self.settings.interfaces:
            renderer = renderers.get(item.type, self._render_custom_interface)
            lines.extend(renderer(item))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def sync(self) -> dict[str, Any]:
        self.settings.reticulum_config_path.mkdir(parents=True, exist_ok=True)
        target = self.settings.runtime_managed_config_path
        content = self.render()
        target.write_text(content, encoding="utf-8")
        return {
            "rendered": True,
            "config_dir": str(self.settings.reticulum_config_path),
            "config_file": str(target),
            "interface_count": len(self.settings.interfaces),
        }


__all__ = ["RuntimeConfigBridge"]

