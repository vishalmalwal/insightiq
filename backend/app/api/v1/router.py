"""Aggregates all v1 routers. New feature routers get registered here."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    ask,
    dashboards,
    data_sources,
    eval,
    health,
    projects,
    semantic_layer,
    system,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(projects.router)
api_router.include_router(data_sources.router)
api_router.include_router(semantic_layer.router)
api_router.include_router(ask.router)
api_router.include_router(dashboards.router)
api_router.include_router(eval.router)
# Phase 5+: api_router.include_router(eval.router)
