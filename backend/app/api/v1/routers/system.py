"""System metadata endpoint (surfaces environment + configured models)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.common import SystemInfo

router = APIRouter()


@router.get("/system/info", response_model=SystemInfo, summary="System info")
async def system_info(settings: SettingsDep) -> SystemInfo:
    return SystemInfo(
        app_name=settings.app_name,
        version="0.1.0",
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        planner_model=settings.llm_model_planner,
    )
