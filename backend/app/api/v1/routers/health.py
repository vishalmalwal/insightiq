"""Health/readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="API health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
