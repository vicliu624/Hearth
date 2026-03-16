from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/services", tags=["services"])


class ServiceActionRequest(BaseModel):
    action: str


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_services(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return await context.service_host_service.list_services()


@router.get("/{name}", dependencies=[Depends(require_permission("read"))])
async def get_service(name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    service = await context.service_host_service.get_service(name)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")
    return service


@router.post("/{name}", dependencies=[Depends(require_permission("operate"))])
async def control_service(name: str, payload: ServiceActionRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return await context.service_host_service.control(name, payload.action)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
