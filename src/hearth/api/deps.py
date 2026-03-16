from __future__ import annotations

from fastapi import Request

from hearth.core.lifecycle import ApplicationContext


def get_context(request: Request) -> ApplicationContext:
    return request.app.state.context

