from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn

from hearth.api.main import create_app
from hearth.core.config import load_settings


def main() -> None:
    config_path = os.getenv("HEARTH_CONFIG")
    settings = load_settings(Path(config_path) if config_path else None)
    logging.basicConfig(level=getattr(logging, settings.system.log_level.upper(), logging.INFO))
    app = create_app(settings_path=config_path)
    uvicorn.run(app, host=settings.web.host, port=settings.web.port)

