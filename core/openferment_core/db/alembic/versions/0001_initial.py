"""The openferment schema of execution prompt section 7.4.

Revision ID: 0001
Revises:
Create Date: 2026-10-30

Written by alembic's autogenerate from `db/models.py` on an empty database,
then read. `test_db.py` holds the two equal: a database migrated to head
differs from the models in nothing.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('projects',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), server_default='', nullable=False),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_projects')),
    schema='openferment'
    )
    op.create_table('artifacts',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('tool', sa.Text(), nullable=False),
    sa.Column('version', sa.Text(), nullable=False),
    sa.Column('output_hash', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_artifacts_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_artifacts')),
    schema='openferment'
    )
    op.create_index(op.f('ix_artifacts_project_id_tool'), 'artifacts', ['project_id', 'tool'], unique=False, schema='openferment')
    op.create_table('audit',
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('project_id', sa.Text(), nullable=True),
    sa.Column('agent', sa.Text(), nullable=False),
    sa.Column('who', sa.Text(), nullable=False),
    sa.Column('module', sa.Text(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('target', sa.Text(), nullable=True),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_audit_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('seq', name=op.f('pk_audit')),
    schema='openferment'
    )
    op.create_index(op.f('ix_audit_project_id'), 'audit', ['project_id'], unique=False, schema='openferment')
    op.create_table('candidates',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('document_id', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_candidates_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'document_id', 'source', name=op.f('pk_candidates')),
    schema='openferment'
    )
    op.create_table('comparisons',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_comparisons_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_comparisons')),
    schema='openferment'
    )
    op.create_table('conversations',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), server_default='', nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_conversations_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_conversations')),
    schema='openferment'
    )
    op.create_table('decisions',
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('record_id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_decisions_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('seq', name=op.f('pk_decisions')),
    schema='openferment'
    )
    op.create_index(op.f('ix_decisions_project_id'), 'decisions', ['project_id'], unique=False, schema='openferment')
    op.create_index(op.f('ix_decisions_project_id_record_id'), 'decisions', ['project_id', 'record_id'], unique=False, schema='openferment')
    op.create_table('depositions',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('runbook_id', sa.Text(), nullable=True),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_depositions_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_depositions')),
    schema='openferment'
    )
    op.create_index(op.f('ix_depositions_project_id_runbook_id'), 'depositions', ['project_id', 'runbook_id'], unique=False, schema='openferment')
    op.create_table('documents_link',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('document_id', sa.Text(), nullable=False),
    sa.Column('selection', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_documents_link_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'document_id', name=op.f('pk_documents_link')),
    schema='openferment'
    )
    op.create_table('fits',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_fits_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_fits')),
    schema='openferment'
    )
    op.create_table('flowsheets',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('schema_version', sa.Text(), nullable=False),
    sa.Column('recipe', sa.Text(), nullable=True),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_flowsheets_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_flowsheets')),
    schema='openferment'
    )
    op.create_table('guild_checks',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_guild_checks_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_guild_checks')),
    schema='openferment'
    )
    op.create_table('guild_evidence',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('person_id', sa.Text(), nullable=False),
    sa.Column('skill_id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_guild_evidence_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_guild_evidence')),
    schema='openferment'
    )
    op.create_index(op.f('ix_guild_evidence_project_id_person_id'), 'guild_evidence', ['project_id', 'person_id'], unique=False, schema='openferment')
    op.create_table('guild_people',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_guild_people_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_guild_people')),
    schema='openferment'
    )
    op.create_table('jobs',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_jobs_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_jobs')),
    schema='openferment'
    )
    op.create_table('measured_evidence',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_measured_evidence_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_measured_evidence')),
    schema='openferment'
    )
    op.create_table('overrides',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_overrides_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'scope', 'key', name=op.f('pk_overrides')),
    schema='openferment'
    )
    op.create_table('practice_scenarios',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_practice_scenarios_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_practice_scenarios')),
    schema='openferment'
    )
    op.create_table('practice_sessions',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_practice_sessions_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_practice_sessions')),
    schema='openferment'
    )
    op.create_table('project_members',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('person', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), server_default='member', nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_project_members_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'person', name=op.f('pk_project_members')),
    schema='openferment'
    )
    op.create_table('proposals',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_proposals_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_proposals')),
    schema='openferment'
    )
    op.create_table('records',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('document_id', sa.Text(), nullable=False),
    sa.Column('field', sa.Text(), nullable=False),
    sa.Column('value', sa.Float(), nullable=True),
    sa.Column('value_text', sa.Text(), nullable=True),
    sa.Column('unit', sa.Text(), nullable=True),
    sa.Column('basis', sa.Text(), nullable=True),
    sa.Column('quote', sa.Text(), nullable=False),
    sa.Column('section', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('provenance', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_records_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', 'version', name=op.f('pk_records')),
    schema='openferment'
    )
    op.create_index(op.f('ix_records_project_id_document_id'), 'records', ['project_id', 'document_id'], unique=False, schema='openferment')
    op.create_index(op.f('ix_records_project_id_field'), 'records', ['project_id', 'field'], unique=False, schema='openferment')
    op.create_table('runbook_locks',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('runbook_id', sa.Text(), nullable=False),
    sa.Column('lock_hash', sa.Text(), nullable=False),
    sa.Column('locked_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_runbook_locks_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'runbook_id', name=op.f('pk_runbook_locks')),
    schema='openferment'
    )
    op.create_table('runbooks',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_runbooks_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_runbooks')),
    schema='openferment'
    )
    op.create_table('runs',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('flowsheet_id', sa.Text(), nullable=True),
    sa.Column('scenario_id', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_runs_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_runs')),
    schema='openferment'
    )
    op.create_index(op.f('ix_runs_project_id_scenario_id'), 'runs', ['project_id', 'scenario_id'], unique=False, schema='openferment')
    op.create_table('scenarios',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('pinned', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_scenarios_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_scenarios')),
    schema='openferment'
    )
    op.create_table('spend',
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('usd', sa.Numeric(precision=14, scale=6), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('reservation', sa.Text(), nullable=True),
    sa.Column('project_id', sa.Text(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_spend_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('seq', name=op.f('pk_spend')),
    sa.UniqueConstraint('reservation', name=op.f('uq_spend_reservation')),
    schema='openferment'
    )
    op.create_index(op.f('ix_spend_day'), 'spend', ['day'], unique=False, schema='openferment')
    op.create_table('tool_calls',
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('turn_id', sa.Text(), nullable=True),
    sa.Column('tool', sa.Text(), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_tool_calls_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('seq', name=op.f('pk_tool_calls')),
    schema='openferment'
    )
    op.create_index(op.f('ix_tool_calls_project_id'), 'tool_calls', ['project_id'], unique=False, schema='openferment')
    op.create_table('trains',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_trains_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_trains')),
    schema='openferment'
    )
    op.create_table('turns',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('conversation_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by', sa.Text(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id', 'conversation_id'], ['openferment.conversations.project_id', 'openferment.conversations.id'], name=op.f('fk_turns_project_id_conversation_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['openferment.projects.id'], name=op.f('fk_turns_project_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('project_id', 'id', name=op.f('pk_turns')),
    schema='openferment'
    )
    op.create_index(op.f('ix_turns_project_id_conversation_id_seq'), 'turns', ['project_id', 'conversation_id', 'seq'], unique=False, schema='openferment')


def downgrade() -> None:
    op.drop_index(op.f('ix_turns_project_id_conversation_id_seq'), table_name='turns', schema='openferment')
    op.drop_table('turns', schema='openferment')
    op.drop_table('trains', schema='openferment')
    op.drop_index(op.f('ix_tool_calls_project_id'), table_name='tool_calls', schema='openferment')
    op.drop_table('tool_calls', schema='openferment')
    op.drop_index(op.f('ix_spend_day'), table_name='spend', schema='openferment')
    op.drop_table('spend', schema='openferment')
    op.drop_table('scenarios', schema='openferment')
    op.drop_index(op.f('ix_runs_project_id_scenario_id'), table_name='runs', schema='openferment')
    op.drop_table('runs', schema='openferment')
    op.drop_table('runbooks', schema='openferment')
    op.drop_table('runbook_locks', schema='openferment')
    op.drop_index(op.f('ix_records_project_id_field'), table_name='records', schema='openferment')
    op.drop_index(op.f('ix_records_project_id_document_id'), table_name='records', schema='openferment')
    op.drop_table('records', schema='openferment')
    op.drop_table('proposals', schema='openferment')
    op.drop_table('project_members', schema='openferment')
    op.drop_table('practice_sessions', schema='openferment')
    op.drop_table('practice_scenarios', schema='openferment')
    op.drop_table('overrides', schema='openferment')
    op.drop_table('measured_evidence', schema='openferment')
    op.drop_table('jobs', schema='openferment')
    op.drop_table('guild_people', schema='openferment')
    op.drop_index(op.f('ix_guild_evidence_project_id_person_id'), table_name='guild_evidence', schema='openferment')
    op.drop_table('guild_evidence', schema='openferment')
    op.drop_table('guild_checks', schema='openferment')
    op.drop_table('flowsheets', schema='openferment')
    op.drop_table('fits', schema='openferment')
    op.drop_table('documents_link', schema='openferment')
    op.drop_index(op.f('ix_depositions_project_id_runbook_id'), table_name='depositions', schema='openferment')
    op.drop_table('depositions', schema='openferment')
    op.drop_index(op.f('ix_decisions_project_id_record_id'), table_name='decisions', schema='openferment')
    op.drop_index(op.f('ix_decisions_project_id'), table_name='decisions', schema='openferment')
    op.drop_table('decisions', schema='openferment')
    op.drop_table('conversations', schema='openferment')
    op.drop_table('comparisons', schema='openferment')
    op.drop_table('candidates', schema='openferment')
    op.drop_index(op.f('ix_audit_project_id'), table_name='audit', schema='openferment')
    op.drop_table('audit', schema='openferment')
    op.drop_index(op.f('ix_artifacts_project_id_tool'), table_name='artifacts', schema='openferment')
    op.drop_table('artifacts', schema='openferment')
    op.drop_table('projects', schema='openferment')
