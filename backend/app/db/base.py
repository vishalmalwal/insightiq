"""Declarative base + cross-dialect type helpers.

Uses generic types that map cleanly to both Postgres (production/Neon) and
SQLite (tests/CI, no server needed): UUID → native uuid on PG, CHAR(32) on
SQLite; JSON → JSONB on PG, JSON on SQLite.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# JSONB on Postgres, plain JSON elsewhere.
JSONType = sa.JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass
