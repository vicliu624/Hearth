from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from hearth.api.routes_backup import router as backup_router
from hearth.api.routes_alerts import router as alerts_router
from hearth.api.routes_announces import router as announces_router
from hearth.api.routes_audit import router as audit_router
from hearth.api.routes_bridges import router as bridges_router
from hearth.api.routes_config import router as config_router
from hearth.api.routes_diagnostics import router as diagnostics_router
from hearth.api.routes_fleet import router as fleet_router
from hearth.api.routes_interfaces import router as interfaces_router
from hearth.api.routes_logs import router as logs_router
from hearth.api.routes_maintenance import router as maintenance_router
from hearth.api.routes_metrics import router as metrics_router
from hearth.api.routes_node import router as node_router
from hearth.api.routes_peers import router as peers_router
from hearth.api.routes_plugins import router as plugins_router
from hearth.api.routes_rollouts import router as rollouts_router
from hearth.api.routes_routes import router as routes_router
from hearth.api.routes_remote_logs import router as remote_logs_router
from hearth.api.routes_security import router as security_router
from hearth.api.routes_services import router as services_router
from hearth.api.routes_upgrade import router as upgrade_router
from hearth.api.routes_topology import router as topology_router
from hearth.api.security import apply_security_headers, build_access_denied_response, is_request_host_allowed
from hearth.core.lifecycle import attach_context, build_context, lifespan_factory
from hearth.web.views import router as web_router


def create_app(settings_path: str | Path | None = None) -> FastAPI:
    context = build_context(settings_path=settings_path)
    app = FastAPI(title="Hearth", version="0.1.0", lifespan=lifespan_factory(context))
    attach_context(app, context)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        if not is_request_host_allowed(request, context):
            return apply_security_headers(build_access_denied_response(request))

        response = await call_next(request)
        return apply_security_headers(response)

    app.include_router(node_router)
    app.include_router(interfaces_router)
    app.include_router(peers_router)
    app.include_router(routes_router)
    app.include_router(announces_router)
    app.include_router(rollouts_router)
    app.include_router(bridges_router)
    app.include_router(alerts_router)
    app.include_router(diagnostics_router)
    app.include_router(logs_router)
    app.include_router(audit_router)
    app.include_router(maintenance_router)
    app.include_router(plugins_router)
    app.include_router(services_router)
    app.include_router(config_router)
    app.include_router(fleet_router)
    app.include_router(backup_router)
    app.include_router(metrics_router)
    app.include_router(remote_logs_router)
    app.include_router(upgrade_router)
    app.include_router(topology_router)
    app.include_router(security_router)
    app.include_router(web_router)

    static_dir = Path(__file__).resolve().parent.parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app
