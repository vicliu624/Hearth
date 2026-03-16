from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(require_permission("configure"))])


@router.get("")
async def get_config(context: ApplicationContext = Depends(get_context)) -> dict:
    return context.config_service.show()


@router.get("/raw")
async def get_config_raw(context: ApplicationContext = Depends(get_context)) -> dict:
    return context.config_service.show_raw()


@router.post("/validate")
async def validate_config(
    payload: dict[str, Any] = Body(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.config_service.validate(payload)


@router.post("/validate-raw")
async def validate_config_raw(
    payload: dict[str, str] = Body(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.config_service.validate_raw(payload["raw"])


@router.post("/save")
async def save_config(
    payload: dict[str, Any] = Body(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.config_service.save(payload)


@router.post("/save-raw")
async def save_config_raw(
    payload: dict[str, str] = Body(...),
    context: ApplicationContext = Depends(get_context),
) -> dict:
    return context.config_service.save_raw(payload["raw"])


@router.get("/revisions")
async def list_config_revisions(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.config_version_service.list_revisions()


@router.get("/revisions/{revision_id}")
async def get_config_revision(revision_id: int, context: ApplicationContext = Depends(get_context)) -> dict | None:
    return context.config_version_service.get_revision(revision_id)


@router.get("/revisions/{revision_id}/compare")
async def compare_config_revision(revision_id: int, context: ApplicationContext = Depends(get_context)) -> dict | None:
    return context.config_version_service.compare_with_current(revision_id)


@router.post("/revisions/{revision_id}/restore")
async def restore_config_revision(revision_id: int, context: ApplicationContext = Depends(get_context)) -> dict:
    revision = context.config_version_service.get_revision(revision_id)
    if revision is None:
        return {"restored": False, "revision_id": revision_id, "error": "revision not found"}
    result = context.config_service.save_raw(
        revision["raw_text"],
        source="restore",
        actor="config_restore",
        summary=f"restored revision #{revision_id}",
    )
    return {"restored": bool(result.get("saved")), "revision_id": revision_id, **result}
