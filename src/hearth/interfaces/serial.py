from __future__ import annotations

from hearth.interfaces.base import BasicInterfaceDriver


class SerialDriver(BasicInterfaceDriver):
    driver_type = "serial"

    def validate_configuration(self) -> list[str]:
        errors: list[str] = []
        if not self.config.get("device"):
            errors.append("device is required")
        baudrate = self.config.get("baudrate")
        if baudrate is not None and (not isinstance(baudrate, int) or baudrate <= 0):
            errors.append("baudrate must be a positive integer")
        return errors

