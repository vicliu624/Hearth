from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/rollouts", tags=["rollouts"])


class RolloutRequest(BaseModel):
    action: str = "apply_template"
    template_name: str | None = None
    target_group: str | None = None
    target_nodes: list[str] = Field(default_factory=list)


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_rollouts(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.rollout_service.list_rollouts()


@router.post("", dependencies=[Depends(require_permission("configure"))])
async def create_rollout(payload: RolloutRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.rollout_service.create_rollout(**payload.model_dump(), actor="api")
