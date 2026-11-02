"""Scenarios of two kinds (execution prompt §7.4; studies/, stage 5).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30

The `scenarios` table keeps the Proforma screens' scenarios (project_state.py)
and, from stage 5, a study's scenarios on a library plant or an openFerment
flowsheet (studies/scenarios.py). The `kind` column says which: every row
written before this revision is a Proforma scenario, so the column comes with
that default. An index on the project and the kind serves each reader.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: str | Sequence[str] | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('scenarios', sa.Column('kind', sa.Text(), server_default='proforma', nullable=False),
                  schema='openferment')
    op.create_index('ix_scenarios_project_id_kind', 'scenarios', ['project_id', 'kind'], unique=False,
                    schema='openferment')


def downgrade() -> None:
    op.drop_index('ix_scenarios_project_id_kind', table_name='scenarios', schema='openferment')
    op.drop_column('scenarios', 'kind', schema='openferment')
