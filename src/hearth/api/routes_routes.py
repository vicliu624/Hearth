from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("")
async def list_routes(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.route_service.list_routes()


@router.get("/summary")
async def route_summary(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.route_service.summary()


@router.get("/{destination_hash}")
async def get_route(destination_hash: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.route_service.get_route(destination_hash)
