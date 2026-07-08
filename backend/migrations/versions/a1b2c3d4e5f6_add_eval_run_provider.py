"""add provider to eval_run

Revision ID: a1b2c3d4e5f6
Revises: d02ec6cd14f2
Create Date: 2026-07-06

"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d02ec6cd14f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_run",
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="mock"),
    )


def downgrade() -> None:
    op.drop_column("eval_run", "provider")
