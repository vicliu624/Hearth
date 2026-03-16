from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/remote-logs", tags=["remote-logs"])


class RemoteLogIngestRequest(BaseModel):
    node_name: str
    entries: list[dict] = Field(default_factory=list)


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_remote_logs(
    node_name: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    context: ApplicationContext = Depends(get_context),
) -> list[dict]:
    return await context.remote_log_service.list_entries(node_name=node_name, level=level, limit=limit)


@router.post("/ingest", dependencies=[Depends(require_permission("operate"))])
async def ingest_remote_logs(payload: RemoteLogIngestRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.remote_log_service.ingest_entries(node_name=payload.node_name, entries=payload.entries)


@router.post("/sync", dependencies=[Depends(require_permission("operate"))])
async def sync_remote_logs(limit: int = 100, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.remote_log_service.sync_nodes(limit=limit)
