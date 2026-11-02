"""SFF flowsheet records: the file, its hash and its origin (ADR-003).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30

The `flowsheets` table gains what an SFF record is kept and listed by: the
file whole (`document`), its sha256 and its origin (run, library or
imported). Nothing wrote the table before stage 4, so the columns are added
without defaults; a table holding rows refuses the migration rather than
take values nobody computed. `test_db.py` holds a database at head equal to
`db/models.py`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('flowsheets', sa.Column('origin', sa.Text(), nullable=False), schema='openferment')
    op.add_column('flowsheets', sa.Column('sha256', sa.Text(), nullable=False), schema='openferment')
    op.add_column('flowsheets', sa.Column('document', sa.Text(), nullable=False), schema='openferment')


def downgrade() -> None:
    op.drop_column('flowsheets', 'document', schema='openferment')
    op.drop_column('flowsheets', 'sha256', schema='openferment')
    op.drop_column('flowsheets', 'origin', schema='openferment')
