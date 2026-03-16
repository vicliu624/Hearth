from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/fleet", tags=["fleet"])


class FleetNodeUpsertRequest(BaseModel):
    node_name: str
    display_name: str | None = None
    group_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    version: str | None = None
    health_status: str = "warning"
    runtime_status: str = "offline"
    uptime_seconds: int = 0
    dashboard_url: str | None = None
    region: str | None = None
    notes: str | None = None


class NodeGroupCreateRequest(BaseModel):
    name: str
    description: str | None = None
    group_type: str = "custom"


class ConfigTemplateCreateRequest(BaseModel):
    name: str
    description: str | None = None
    template_text: str
    target_group: str | None = None
    target_nodes: list[str] = Field(default_factory=list)


@router.get("/overview", dependencies=[Depends(require_permission("read"))])
async def get_fleet_overview(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.fleet_service.dashboard()


@router.get("/nodes", dependencies=[Depends(require_permission("read"))])
async def list_fleet_nodes(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.fleet_service.list_nodes()


@router.get("/nodes/{node_name}", dependencies=[Depends(require_permission("read"))])
async def get_fleet_node(node_name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    node = await context.fleet_service.get_node(node_name)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fleet node not found")
    return node


@router.post("/nodes", dependencies=[Depends(require_permission("configure"))])
async def upsert_fleet_node(payload: FleetNodeUpsertRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.fleet_service.register_node(**payload.model_dump())


@router.get("/groups", dependencies=[Depends(require_permission("read"))])
async def list_node_groups(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.fleet_service.list_groups()


@router.post("/groups", dependencies=[Depends(require_permission("configure"))])
async def create_node_group(payload: NodeGroupCreateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.fleet_service.create_group(**payload.model_dump())


@router.get("/templates", dependencies=[Depends(require_permission("read"))])
async def list_config_templates(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.fleet_service.list_templates()


@router.post("/templates", dependencies=[Depends(require_permission("configure"))])
async def create_config_template(payload: ConfigTemplateCreateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.fleet_service.create_template(**payload.model_dump())


@router.get("/tags", dependencies=[Depends(require_permission("read"))])
async def list_fleet_tags(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.fleet_service.list_tags()


@router.get("/health", dependencies=[Depends(require_permission("read"))])
async def get_fleet_health(context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.fleet_service.health_view()


@router.get("/events", dependencies=[Depends(require_permission("read"))])
async def list_fleet_events(limit: int = 100, context: ApplicationContext = Depends(get_context)) -> list[dict]:
    normalized_limit = max(1, min(limit, 500))
    return await context.fleet_service.list_events(limit=normalized_limit)
