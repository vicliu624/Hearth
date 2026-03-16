from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/upgrades", tags=["upgrades"])


class UpgradeRequest(BaseModel):
    action: str
    target_version: str
    channel: str = "stable"
    target_group: str | None = None
    target_nodes: list[str] = Field(default_factory=list)
    notes: str | None = None
    enable_maintenance: bool = False


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_upgrades(context: ApplicationContext = Depends(get_context)) -> dict:
    return {
        "operations": await context.upgrade_service.list_operations(),
        "revisions": context.upgrade_service.recent_revisions(),
    }


@router.post("", dependencies=[Depends(require_permission("operate"))])
async def create_upgrade(payload: UpgradeRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.upgrade_service.schedule_operation(**payload.model_dump(), actor="api")


@router.post("/execute", dependencies=[Depends(require_permission("operate"))])
async def execute_upgrade(payload: UpgradeRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.upgrade_service.execute_local_operation(**payload.model_dump(), actor="api")
