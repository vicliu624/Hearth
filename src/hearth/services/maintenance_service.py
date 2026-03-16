from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hearth.storage.db import Database


class MaintenanceService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_state(self) -> dict[str, Any]:
        state = self.database.get_maintenance_state()
        until_at = state.get("until_at")
        if state.get("enabled") and until_at:
            try:
                deadline = datetime.fromisoformat(until_at)
            except ValueError:
                deadline = None
            if deadline is not None:
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if deadline.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                    return self.disable(actor="maintenance.expired")
        return state

    def is_enabled(self) -> bool:
        return bool(self.get_state().get("enabled"))

    def enable(self, *, reason: str | None = None, until_at: datetime | None = None, actor: str = "system") -> dict[str, Any]:
        state = self.database.set_maintenance_state(enabled=True, reason=reason, until_at=until_at)
        self.database.record_event(
            "maintenance.enabled",
            "maintenance mode enabled",
            source="maintenance_service",
            payload={"actor": actor, "reason": reason, "until_at": state.get("until_at")},
        )
        return state

    def disable(self, *, actor: str = "system") -> dict[str, Any]:
        previous = self.database.get_maintenance_state()
        state = self.database.set_maintenance_state(enabled=False, reason=None, until_at=None)
        self.database.record_event(
            "maintenance.disabled",
            "maintenance mode disabled",
            source="maintenance_service",
            payload={"actor": actor, "previous_reason": previous.get("reason")},
        )
        return state
