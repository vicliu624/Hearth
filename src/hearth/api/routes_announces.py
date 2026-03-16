from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hearth.api.deps import get_context
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/announces", tags=["announces"])


@router.get("")
async def list_announces(
    limit: int = Query(default=100, ge=1, le=500),
    context: ApplicationContext = Depends(get_context),
) -> list[dict]:
    return await context.announce_service.list_announces(limit=limit)


@router.get("/recent")
async def recent_announces(
    limit: int = Query(default=20, ge=1, le=100),
    context: ApplicationContext = Depends(get_context),
) -> list[dict]:
    return await context.announce_service.recent(limit=limit)


@router.get("/{announce_id}")
async def get_announce(announce_id: int, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.announce_service.get_announce(announce_id)
