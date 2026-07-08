"""Common response schemas shared across routers."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class SystemInfo(BaseModel):
    app_name: str
    version: str
    environment: str
    llm_provider: str
    planner_model: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
