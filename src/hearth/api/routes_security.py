from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/security", tags=["security"])


class UserCreateRequest(BaseModel):
    username: str
    display_name: str | None = None
    role: str = "viewer"


class UserUpdateRequest(BaseModel):
    role: str | None = None
    enabled: bool | None = None


class TokenCreateRequest(BaseModel):
    token_name: str
    owner_username: str | None = None
    role: str = "viewer"
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = None


class TokenUpdateRequest(BaseModel):
    enabled: bool


class RoleCreateRequest(BaseModel):
    name: str
    label: str | None = None
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    label: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


@router.get("/roles", dependencies=[Depends(require_permission("security"))])
async def list_roles(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.security_service.list_roles()


@router.post("/roles", dependencies=[Depends(require_permission("security"))])
async def create_role(payload: RoleCreateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.security_service.create_role(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/roles/{role_name}", dependencies=[Depends(require_permission("security"))])
async def update_role(role_name: str, payload: RoleUpdateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.security_service.update_role(role_name, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/roles/{role_name}", dependencies=[Depends(require_permission("security"))])
async def delete_role(role_name: str, context: ApplicationContext = Depends(get_context)) -> dict:
    try:
        return context.security_service.delete_role(role_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/users", dependencies=[Depends(require_permission("security"))])
async def list_users(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.security_service.list_users()


@router.post("/users", dependencies=[Depends(require_permission("security"))])
async def create_user(payload: UserCreateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.security_service.create_user(
        username=payload.username,
        display_name=payload.display_name,
        role=payload.role,
    )


@router.post("/users/{username}", dependencies=[Depends(require_permission("security"))])
async def update_user(username: str, payload: UserUpdateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    if payload.role is not None:
        return context.security_service.set_user_role(username, payload.role)
    if payload.enabled is not None:
        return context.security_service.set_user_enabled(username, payload.enabled)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no update fields provided")


@router.get("/tokens", dependencies=[Depends(require_permission("tokens"))])
async def list_tokens(context: ApplicationContext = Depends(get_context)) -> list[dict]:
    return context.security_service.list_api_tokens()


@router.post("/tokens", dependencies=[Depends(require_permission("tokens"))])
async def create_token(payload: TokenCreateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.security_service.create_api_token(
        token_name=payload.token_name,
        owner_username=payload.owner_username,
        role=payload.role,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )


@router.post("/tokens/{token_name}", dependencies=[Depends(require_permission("tokens"))])
async def update_token(token_name: str, payload: TokenUpdateRequest, context: ApplicationContext = Depends(get_context)) -> dict:
    return context.security_service.set_api_token_enabled(token_name, payload.enabled)
