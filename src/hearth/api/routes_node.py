from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/node", tags=["node"])


@router.get("/status")
async def get_status(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.node_service.status_summary(persist=True)


@router.post("/start", dependencies=[Depends(require_permission("operate"))])
async def start_node(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.node_service.start()


@router.post("/stop", dependencies=[Depends(require_permission("operate"))])
async def stop_node(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.node_service.stop()


@router.post("/restart", dependencies=[Depends(require_permission("operate"))])
async def restart_node(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.node_service.restart()
