from __future__ import annotations

from hearth.interfaces.base import BasicInterfaceDriver


class TCPDriver(BasicInterfaceDriver):
    driver_type = "tcp"

    def validate_configuration(self) -> list[str]:
        errors: list[str] = []
        host = self.config.get("host") or self.config.get("target_host") or self.config.get("remote")
        listen_ip = self.config.get("listen_ip") or self.config.get("listen_on")
        server_mode = bool(listen_ip or self.config.get("server"))

        if not server_mode and not host:
            errors.append("host is required for TCP client interfaces")

        port = self.config.get("port") or self.config.get("target_port") or self.config.get("listen_port")
        if port is None:
            errors.append("port is required")
        elif not isinstance(port, int) or port <= 0:
            errors.append("port must be a positive integer")
        return errors

