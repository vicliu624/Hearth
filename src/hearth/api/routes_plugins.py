from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class PluginUpdateRequest(BaseModel):
    enabled: bool


class PluginInstallRequest(BaseModel):
    name: str
    enabled: bool = True


class PluginCatalogQuery(BaseModel):
    refresh_sources: bool = False


class PluginUninstallRequest(BaseModel):
    remove_dependents: bool = False


class PluginRefreshRequest(BaseModel):
    enabled: bool | None = None


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_plugins(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.plugin_service.list_plugins()


@router.get("/catalog", dependencies=[Depends(require_permission("read"))])
async def list_plugin_catalog(refresh_sources: bool = False, context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.plugin_service.list_available_plugins(refresh_sources=refresh_sources)


@router.get("/history", dependencies=[Depends(require_permission("read"))])
async def plugin_history(limit: int = 50, context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.plugin_service.plugin_history(limit=limit)


@router.get("/sources", dependencies=[Depends(require_permission("read"))])
async def list_plugin_sources(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.plugin_service.list_sources()


@router.post("/sources/refresh", dependencies=[Depends(require_permission("configure"))])
async def refresh_plugin_sources(context: ApplicationContext = Depends(get_context)) -> dict:
    return context.plugin_service.refresh_sources()


@router.get("/{name}", dependencies=[Depends(require_permission("read"))])
async def get_plugin(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    plugin = context.plugin_service.get_plugin(name)
    if plugin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plugin not found")
    return plugin


@router.post("/install", dependencies=[Depends(require_permission("configure"))])
async def install_plugin(payload: PluginInstallRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.plugin_service.install_plugin(payload.name, enable=payload.enabled)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{name}", dependencies=[Depends(require_permission("configure"))])
async def update_plugin(name: str, payload: PluginUpdateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.plugin_service.set_plugin_enabled(name, payload.enabled)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{name}/refresh", dependencies=[Depends(require_permission("configure"))])
async def refresh_plugin(name: str, payload: PluginRefreshRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.plugin_service.update_plugin(name, enable=payload.enabled)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{name}", dependencies=[Depends(require_permission("configure"))])
async def uninstall_plugin(name: str, remove_dependents: bool = False, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.plugin_service.uninstall_plugin(name, remove_dependents=remove_dependents)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
