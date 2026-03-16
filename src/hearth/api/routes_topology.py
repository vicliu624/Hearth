from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/topology", tags=["topology"])


@router.get("", dependencies=[Depends(require_permission("read"))])
async def get_topology(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.topology_service.snapshot()


@router.get("/network-map", dependencies=[Depends(require_permission("read"))])
async def get_network_map(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.topology_service.network_map()


@router.get("/route-heatmap", dependencies=[Depends(require_permission("read"))])
async def get_route_heatmap(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.topology_service.route_heatmap()


@router.get("/critical-nodes", dependencies=[Depends(require_permission("read"))])
async def get_critical_nodes(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.topology_service.critical_nodes()


@router.get("/insights", dependencies=[Depends(require_permission("read"))])
async def get_network_insights(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.topology_service.insights()


@router.get("/path-changes", dependencies=[Depends(require_permission("read"))])
async def get_path_changes(
    recent_limit: int = Query(default=80, ge=1, le=500),
    since_minutes: int = Query(default=10080, ge=0, le=43200),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return await context.topology_service.path_changes(recent_limit=recent_limit, since_minutes=since_minutes)
