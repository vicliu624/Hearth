from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/bridges", tags=["bridges"])


class BridgeActionRequest(BaseModel):
    action: str


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_bridges(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    summary = await context.node_service.status_summary(persist=False)
    return context.bridge_catalog_service.list_bridges(str(summary.get("runtime_status") or "unknown"))


@router.get("/{name}", dependencies=[Depends(require_permission("read"))])
async def get_bridge(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    bridge = context.bridge_catalog_service.get_bridge(name, str(summary.get("runtime_status") or "unknown"))
    if bridge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bridge not found")
    return bridge


@router.post("/{name}", dependencies=[Depends(require_permission("operate"))])
async def control_bridge(name: str, payload: BridgeActionRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    try:
        return context.bridge_catalog_service.control(name, payload.action, str(summary.get("runtime_status") or "unknown"))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
