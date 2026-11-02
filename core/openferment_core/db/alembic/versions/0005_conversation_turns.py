"""A Live conversation's turns as rows of their own (execution prompt §4.8; ADR-008; stage 6).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-30

Until stage 6 a page kept each Live conversation whole, its turns inside the row's body
(project_state.py). Postdoc now keeps a conversation as a row of `conversations` (its title,
when it began, who began it) and each turn as a row of `turns` in order, beside the tool
calls it made (postdoc/conversations.py). Each conversation kept whole is split so: every turn
its body holds becomes a row of `turns` with its place, its status and its body as the page
wrote it, and the conversation's body keeps its id, its title and when it began. A turn
whose id another conversation's turn already took is kept under the id with its
conversation's appended. Nothing is dropped. The downgrade puts each conversation's turns
back inside its body, in order, and empties `turns`.
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | Sequence[str] | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "openferment"
STATUSES = ("running", "answered", "failed", "stopped", "interrupted")


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        f"SELECT project_id, id, CAST(body AS text) AS body, created_by FROM {SCHEMA}.conversations "
        "ORDER BY project_id, created_at, id")).mappings().all()
    for row in rows:
        body = json.loads(row["body"])
        turns = body.get("turns")
        if not isinstance(turns, list):
            continue
        for seq, turn in enumerate(t for t in turns if isinstance(t, dict)):
            tid = str(turn.get("id") or f"{row['id']}-{seq + 1}")
            taken = bind.execute(sa.text(f"SELECT 1 FROM {SCHEMA}.turns WHERE project_id = :p AND id = :i"),
                                 {"p": row["project_id"], "i": tid}).first()
            if taken is not None:
                tid = f"{tid}-{row['id']}"
            status = turn.get("status") if turn.get("status") in STATUSES else "interrupted"
            bind.execute(sa.text(
                f"INSERT INTO {SCHEMA}.turns (project_id, id, conversation_id, seq, status, body, created_by) "
                "VALUES (:p, :i, :c, :s, :status, CAST(:body AS json), :by)"),
                {"p": row["project_id"], "i": tid, "c": row["id"], "s": seq + 1, "status": status,
                 "body": json.dumps({**turn, "id": tid, "status": status}, ensure_ascii=False), "by": row["created_by"]})
        head = {"id": row["id"], "title": body.get("title", ""), "startedAt": body.get("startedAt", ""), "by": row["created_by"]}
        bind.execute(sa.text(f"UPDATE {SCHEMA}.conversations SET body = CAST(:body AS json) WHERE project_id = :p AND id = :i"),
                     {"body": json.dumps(head, ensure_ascii=False), "p": row["project_id"], "i": row["id"]})


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        f"SELECT project_id, id, CAST(body AS text) AS body FROM {SCHEMA}.conversations")).mappings().all()
    for row in rows:
        body = json.loads(row["body"])
        turns = bind.execute(sa.text(
            f"SELECT CAST(body AS text) AS body FROM {SCHEMA}.turns WHERE project_id = :p AND conversation_id = :c "
            "ORDER BY seq"), {"p": row["project_id"], "c": row["id"]}).scalars().all()
        whole = {"id": body.get("id", row["id"]), "title": body.get("title", ""), "startedAt": body.get("startedAt", ""),
                 "turns": [json.loads(t) for t in turns]}
        bind.execute(sa.text(f"UPDATE {SCHEMA}.conversations SET body = CAST(:body AS json) WHERE project_id = :p AND id = :i"),
                     {"body": json.dumps(whole, ensure_ascii=False), "p": row["project_id"], "i": row["id"]})
    bind.execute(sa.text(f"DELETE FROM {SCHEMA}.tool_calls"))
    bind.execute(sa.text(f"DELETE FROM {SCHEMA}.turns"))
