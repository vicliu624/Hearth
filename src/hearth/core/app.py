from __future__ import annotations

import logging
import os

import uvicorn

from hearth.api.main import create_app


def main() -> None:
    config_path = os.getenv("HEARTH_CONFIG")
    app = create_app(settings_path=config_path)
    settings = app.state.context.settings
    logging.basicConfig(
        level=getattr(logging, settings.system.log_level.upper(), logging.INFO)
    )
    uvicorn.run(app, host=settings.web.host, port=settings.web.port)
