"""Every run names the engine that made it (alpha 2.2 stage B; ADR-015).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-03

Engines register through the entry-point group `openferment.engines`
(docs/api/engines.md), and every run the service keeps is one `runs` row of
one shape whatever engine made it. The row gains an `engine` column, its
lookup key for `GET /api/runs?engine=`. Every row kept before this revision
was a BioSTEAM run, so the column's default names it for them; a row whose
body names its engine (one kept at this revision, then downgraded and
upgraded again) takes the body's name. A row's body is left as it was
stored, and `EngineRun.engine` reads `biosteam` where the body has no key.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | Sequence[str] | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('runs', sa.Column('engine', sa.Text(), server_default='biosteam', nullable=False),
                  schema='openferment')
    op.execute("UPDATE openferment.runs SET engine = body->>'engine' "
               "WHERE body->>'engine' IS NOT NULL AND body->>'engine' <> engine")
    op.create_index(op.f('ix_runs_project_id_engine'), 'runs', ['project_id', 'engine'], unique=False,
                    schema='openferment')


def downgrade() -> None:
    op.drop_index(op.f('ix_runs_project_id_engine'), table_name='runs', schema='openferment')
    op.drop_column('runs', 'engine', schema='openferment')
