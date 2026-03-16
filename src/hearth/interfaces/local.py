from __future__ import annotations

from ipaddress import ip_network

from hearth.interfaces.base import BasicInterfaceDriver


class LocalNetworkDriver(BasicInterfaceDriver):
    driver_type = "local"

    def validate_configuration(self) -> list[str]:
        errors: list[str] = []
        discovery_port = self.config.get("discovery_port")
        if discovery_port is not None and (not isinstance(discovery_port, int) or discovery_port <= 0):
            errors.append("discovery_port must be a positive integer")

        subnet = self.config.get("subnet")
        if subnet:
            try:
                ip_network(str(subnet), strict=False)
            except ValueError:
                errors.append("subnet must be a valid CIDR network")

        device = self.config.get("device")
        if device is not None and not str(device).strip():
            errors.append("device must not be empty")
        return errors

