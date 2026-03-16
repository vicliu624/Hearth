from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


class MaintenanceUpdateRequest(BaseModel):
    enabled: bool
    reason: str | None = None
    until_hours: int | None = None


@router.get("", dependencies=[Depends(require_permission("read"))])
async def get_maintenance_state(context: ApplicationContext = Depends(get_context)) -> dict:
    return context.maintenance_service.get_state()


@router.post("", dependencies=[Depends(require_permission("maintenance"))])
async def update_maintenance_state(
    payload: MaintenanceUpdateRequest,
    context: ApplicationContext = Depends(get_context),
) -> dict:
    if payload.enabled:
        until_at = None
        if payload.until_hours and payload.until_hours > 0:
            until_at = datetime.now(timezone.utc) + timedelta(hours=payload.until_hours)
        return context.maintenance_service.enable(reason=payload.reason, until_at=until_at, actor="api")
    return context.maintenance_service.disable(actor="api")
