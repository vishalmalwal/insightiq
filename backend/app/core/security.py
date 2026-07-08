"""Project-scoped access boundary.

A single shared secret gates side-effectful / LLM actions. When no secret is
configured the gate is open (public sample-data demo). This is deliberately a
thin dependency: replacing it with real per-user auth later is a one-file change
because isolation already lives at the project_id level, not the user level.
"""
from __future__ import annotations

from fastapi import Header

from app.core.config import get_settings
from app.core.errors import AppError


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


async def verify_app_access(x_app_secret: str | None = Header(default=None)) -> None:
    """Attach to protected routers via `dependencies=[Depends(verify_app_access)]`.

    Read-only sample-data browsing stays open; wire this onto write/LLM routers
    in Phase 1+. Health/system endpoints are never gated.
    """
    secret = get_settings().app_shared_secret
    if not secret:
        return
    if x_app_secret != secret:
        raise UnauthorizedError("Invalid or missing app access secret")
