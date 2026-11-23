"""A project's protocols as a table of their own (alpha 2.2 E.12a; ADR-017; protocols.py).

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-05

Alpha 2.0 deleted the TypeScript protocols with the seed (ADR-010), and every
reader of a protocol's steps read an empty list: Guild found no step a skill
is needed at, and Practice no step to build on. A project now keeps each
protocol as a row of `protocols`, kept whole by its id, its versions appended
and each kept as it was kept.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0010'
down_revision: str | Sequence[str] | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('protocols',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_protocols_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_protocols')),
    schema='openferment'
    )


def downgrade() -> None:
    op.drop_table('protocols', schema='openferment')
