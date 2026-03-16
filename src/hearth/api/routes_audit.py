from __future__ import annotations

from fastapi import APIRouter, Depends

from hearth.api.deps import get_context
from hearth.api.security import require_permission
from hearth.core.lifecycle import ApplicationContext


router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", dependencies=[Depends(require_permission("read"))])
async def list_audit_events(
    limit: int = 100,
    severity: str | None = None,
    source: str | None = None,
    search: str | None = None,
    context: ApplicationContext = Depends(get_context),
) -> list[dict]:
    bounded_limit = max(1, min(limit, 500))
    events = context.database.list_events(limit=max(bounded_limit * 3, 200), severity=severity or None, source=source or None)
    if search:
        needle = search.strip().lower()
        if needle:
            events = [
                item
                for item in events
                if needle in str(item.get("event_type") or "").lower()
                or needle in str(item.get("message") or "").lower()
                or needle in str(item.get("source") or "").lower()
            ]
    return events[:bounded_limit]
