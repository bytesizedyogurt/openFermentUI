"""Postdoc's evaluation set as tables (execution prompt §10 stage 6.4; ADR-008).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30

Alpha 1.0 kept an evaluation set as files under core/data/eval/ (stage 1 deleted
it with the seed it named). A project now keeps its questions in
`eval_questions`, each with what a good answer does, and each scored run of one
in `eval_runs` (postdoc/evaluate.py).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0006'
down_revision: str | Sequence[str] | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _scoped(name: str, *extra: sa.Column) -> None:
    op.create_table(name,
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    *extra,
    sa.Column('body', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f(f'fk_{name}_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f(f'pk_{name}')),
    schema='openferment'
    )


def upgrade() -> None:
    _scoped('eval_questions')
    _scoped('eval_runs', sa.Column('question_id', sa.Text(), nullable=False))
    op.create_index(op.f('ix_eval_runs_project_id_question_id'), 'eval_runs', ['project_id', 'question_id'], unique=False,
                    schema='openferment')


def downgrade() -> None:
    op.drop_index(op.f('ix_eval_runs_project_id_question_id'), table_name='eval_runs', schema='openferment')
    op.drop_table('eval_runs', schema='openferment')
    op.drop_table('eval_questions', schema='openferment')
