"""Data access for projects. Routers/services never touch the ORM directly."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(self, *, name: str, data_source: str) -> Project:
        base = slugify(name)
        slug = base
        i = 2
        while self._s.scalar(select(Project).where(Project.slug == slug)):
            slug = f"{base}-{i}"
            i += 1
        project = Project(name=name, slug=slug, data_source=data_source)
        self._s.add(project)
        self._s.flush()
        return project

    def get(self, project_id: uuid.UUID) -> Project | None:
        return self._s.get(Project, project_id)

    def get_by_slug(self, slug: str) -> Project | None:
        return self._s.scalar(select(Project).where(Project.slug == slug))

    def list(self) -> list[Project]:
        return list(self._s.scalars(select(Project).order_by(Project.created_at.desc())))

    def delete(self, project: Project) -> None:
        self._s.delete(project)
        self._s.flush()
