from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("", dependencies=[Depends(require_permission("read"))])
async def get_diagnostics(context: ApplicationContext = Depends(get_context)) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    return await context.diagnostics_service.snapshot(summary)
