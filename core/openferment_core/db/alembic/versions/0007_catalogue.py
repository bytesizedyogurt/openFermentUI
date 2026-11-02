"""A project's catalogues as one table (alpha 2.1 stage D, debt 1; catalogues.py).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-02

Alpha 2.0 deleted the TypeScript catalogues with the seed (ADR-010), and every
reader of the strains, the products, Guild's skills and Primer's lessons read
an empty list. A project now keeps each entry as a row of `catalogue`, its kind
a column, kept whole by `<kind>/<id>`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0007'
down_revision: str | Sequence[str] | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('catalogue',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_catalogue_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_catalogue')),
    schema='openferment'
    )
    op.create_index(op.f('ix_catalogue_project_id_kind'), 'catalogue', ['project_id', 'kind'], unique=False,
                    schema='openferment')


def downgrade() -> None:
    op.drop_index(op.f('ix_catalogue_project_id_kind'), table_name='catalogue', schema='openferment')
    op.drop_table('catalogue', schema='openferment')
