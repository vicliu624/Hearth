from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_alerts(context: ApplicationContext = Depends(get_context)) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    return await context.alert_service.refresh(summary)


@router.get("/history", dependencies=[Depends(require_permission("read"))])
async def alert_history(
    limit: int = Query(default=50, ge=1, le=500),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return {"history": context.alert_service.history(limit=limit), "hooks": context.alert_service.hook_status()}
