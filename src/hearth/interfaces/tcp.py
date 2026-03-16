from __future__ import annotations

from hearth.interfaces.base import BasicInterfaceDriver


class TCPDriver(BasicInterfaceDriver):
    driver_type = "tcp"

    def validate_configuration(self) -> list[str]:
        errors: list[str] = []
        if not self.config.get("host"):
            errors.append("host is required")
        port = self.config.get("port")
        if port is None:
            errors.append("port is required")
        elif not isinstance(port, int) or port <= 0:
            errors.append("port must be a positive integer")
        return errors

