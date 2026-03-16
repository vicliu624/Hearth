from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/interfaces", tags=["interfaces"])


@router.get("")
async def list_interfaces(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.interface_service.list_interfaces()


@router.get("/{name}")
async def get_interface(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.interface_service.get_interface(name)


@router.post("/{name}/start", dependencies=[Depends(require_permission("operate"))])
async def start_interface(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.interface_service.start(name)


@router.post("/{name}/stop", dependencies=[Depends(require_permission("operate"))])
async def stop_interface(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.interface_service.stop(name)


@router.post("/{name}/restart", dependencies=[Depends(require_permission("operate"))])
async def restart_interface(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.interface_service.restart(name)


@router.get("/{name}/metrics")
async def interface_metrics(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    return await context.interface_service.metrics(name)
