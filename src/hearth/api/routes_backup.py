from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Query

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(require_permission("configure"))])


@router.get("")
async def backup_plan(context: ApplicationContext = Depends(get_context)) -> dict:
    return {
        "plan": context.backup_service.export_plan(),
        "archives": context.backup_service.list_archives(),
        "snapshots": context.backup_service.list_snapshots(),
    }


@router.post("/export")
async def export_backup(
    payload: dict[str, Any] = Body(default={}),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    destination_path = payload.get("destination_path")
    return context.backup_service.export(destination_path=destination_path)


@router.post("/snapshot")
async def create_snapshot(
    payload: dict[str, Any] = Body(default={}),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    destination_path = payload.get("destination_path")
    return context.backup_service.create_snapshot(destination_path=destination_path)


@router.post("/import")
async def import_backup(
    payload: dict[str, Any] = Body(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.backup_service.import_archive(payload["archive_path"])


@router.get("/detail")
async def backup_detail(
    archive_path: str = Query(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.backup_service.inspect_archive(archive_path)


@router.get("/snapshots")
async def backup_snapshots(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.backup_service.list_snapshots()


@router.post("/prune")
async def prune_snapshots(
    keep: int = Body(default=10),
    max_age_days: int | None = Body(default=None),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.backup_service.prune_snapshots(keep=keep, max_age_days=max_age_days)


@router.get("/dr")
async def disaster_recovery_helper(
    archive_path: str | None = Query(default=None),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.backup_service.disaster_recovery_helper(archive_path=archive_path)
