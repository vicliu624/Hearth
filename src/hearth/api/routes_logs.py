from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hearth.api.deps import get_context
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def list_logs(
    level: str | None = Query(default=None),
    module: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    context: ApplicationContext = Depends(get_context),
) -> list[dict]:
    return context.log_service.list_entries(limit=limit, severity=level, source=module)


@router.get("/timeline")
async def logs_timeline(
    level: str | None = Query(default=None),
    module: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    since_minutes: int = Query(default=1440, ge=0, le=43200),
    bucket_minutes: int = Query(default=120, ge=1, le=1440),
    context: ApplicationContext = Depends(get_context),
) -> dict[str, object]:
    return context.log_service.timeline(
        limit=limit,
        severity=level,
        source=module,
        since_minutes=since_minutes,
        bucket_minutes=bucket_minutes,
    )
