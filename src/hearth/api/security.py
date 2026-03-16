from __future__ import annotations

from ipaddress import ip_address

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from hearth.api.deps import get_context
from hearth.core.lifecycle import ApplicationContext
from hearth.web.i18n import resolve_locale, translate


TOKEN_COOKIE_NAME = "hearth_token"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testclient"}


def localized_message(request: Request, key: str) -> str:
    locale = resolve_locale(request)
    return translate(locale, key)


def get_query_token(request: Request) -> str | None:
    token = request.query_params.get("token")
    return token.strip() if token else None


def extract_admin_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    header_token = request.headers.get("X-Hearth-Token")
    if header_token:
        return header_token.strip()

    query_token = get_query_token(request)
    if query_token:
        return query_token

    cookie_token = request.cookies.get(TOKEN_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip()

    return None


def auth_is_enabled(context: ApplicationContext) -> bool:
    return context.settings.web.auth_mode != "none"


def authenticate_principal(request: Request, context: ApplicationContext) -> dict | None:
    provided = extract_admin_token(request)
    if not provided:
        return None
    return context.security_service.authenticate_token(provided)


async def require_authenticated_principal(
    request: Request,
    context: ApplicationContext = Depends(get_context),
) -> dict | None:
    if not auth_is_enabled(context):
        request.state.admin_token_authenticated = False
        request.state.security_principal = None
        return None

    provided = extract_admin_token(request)
    if not provided:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localized_message(request, "auth.required"))

    principal = authenticate_principal(request, context)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localized_message(request, "auth.invalid"))

    request.state.admin_token_authenticated = True
    request.state.admin_token_value = provided
    request.state.security_principal = principal
    return principal


def require_permission(permission: str):
    async def dependency(
        request: Request,
        context: ApplicationContext = Depends(get_context),
    ) -> dict | None:
        principal = await require_authenticated_principal(request, context)
        if principal is None:
            return None
        if not context.security_service.principal_has_permission(principal, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=localized_message(request, "auth.forbidden"))
        return principal

    return dependency


async def require_admin_token(
    request: Request,
    context: ApplicationContext = Depends(get_context),
) -> None:
    await require_permission("operate")(request, context)


def classify_client_host(host: str | None) -> str:
    if not host:
        return "loopback"

    candidate = host.strip().lower()
    if candidate in _LOCAL_HOSTS:
        return "loopback"

    try:
        address = ip_address(candidate.split("%", 1)[0])
    except ValueError:
        return "public"

    if address.is_loopback:
        return "loopback"
    if address.is_private:
        return "lan"
    return "public"


def is_client_host_allowed(host: str | None, allow_lan: bool, allow_wan: bool) -> bool:
    classification = classify_client_host(host)
    if classification == "loopback":
        return True
    if classification == "lan":
        return allow_lan
    return allow_wan


def is_request_host_allowed(request: Request, context: ApplicationContext) -> bool:
    client_host = request.client.host if request.client else None
    return is_client_host_allowed(
        client_host,
        allow_lan=context.settings.security.allow_lan,
        allow_wan=context.settings.security.allow_wan,
    )


def build_access_denied_response(request: Request) -> Response:
    message = localized_message(request, "network.denied")
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api") or "application/json" in accept:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": message})
    return PlainTextResponse(message, status_code=status.HTTP_403_FORBIDDEN)


def apply_security_headers(response: Response) -> Response:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def set_admin_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(TOKEN_COOKIE_NAME, token, httponly=True, samesite="strict", path="/")


def clear_admin_token_cookie(response: Response) -> None:
    response.delete_cookie(TOKEN_COOKIE_NAME, path="/")
