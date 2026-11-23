"""Each engine's last conformance verdict (alpha 2.2 stage B; ADR-015).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-03

`python -m openferment_core.engine.conform <name>` checks an installed engine
against docs/api/engines.md on a database of its own and keeps its verdict
here, where `GET /api/engines` and `pnpm ready` read it. The engines are the
machine's, so the table belongs to no project: one row per engine, replaced by
its next check.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0009'
down_revision: str | Sequence[str] | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('engine_checks',
    sa.Column('engine', sa.Text(), nullable=False),
    sa.Column('version', sa.Text(), nullable=False),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('body', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.PrimaryKeyConstraint('engine', name=op.f('pk_engine_checks')),
    schema='openferment'
    )


def downgrade() -> None:
    op.drop_table('engine_checks', schema='openferment')
