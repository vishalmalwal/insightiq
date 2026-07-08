"""Project API schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceKind = Literal["sample", "duckdb", "postgres"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: SourceKind = "duckdb"


class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    data_source: str
    created_at: datetime
