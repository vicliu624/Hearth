from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/peers", tags=["peers"])


@router.get("")
async def list_peers(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.peer_service.list_recent()


@router.get("/recent")
async def recent_peers(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.peer_service.list_recent()


@router.get("/{peer_hash}")
async def get_peer(peer_hash: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.peer_service.get_peer(peer_hash)

