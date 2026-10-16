"""A check brief from the real model (OF-BLD-013 §5.3).

Marked `live`: needs a key and spends one call. Run with `pnpm test:live`.
Prints the brief and what it cost.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

from openferment_core import checks, guild
from openferment_core.models import EvidenceSource, GuildEvidence, GuildPerson

pytestmark = pytest.mark.live

needs_key = pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="live tests need ANTHROPIC_API_KEY in core/.env")


@pytest.fixture(autouse=True)
def _files(monkeypatch, tmp_path):
    monkeypatch.setattr(guild, "PATH", tmp_path / "guild.json")
    monkeypatch.setattr(checks, "PATH", tmp_path / "checks.json")


@needs_key
def test_a_real_brief_passes_every_rule():
    p = lambda pid, name, role="member", by="p-lead": GuildPerson(id=pid, name=name, role=role, joinedAt="2026-01-01", addedBy=by, addedAt="2026-01-01T00:00:00Z")  # noqa: E731
    guild.write_person(p("p-lead", "A Lead", "lead", None))
    guild.write_person(p("p-assessor", "An Assessor"))
    guild.write_person(p("p-trainee", "A Trainee"))
    day = (date.today() - timedelta(days=10)).isoformat()
    src = EvidenceSource(kind="signoff", ref="PR-OD-01")
    e = lambda eid, pid, kind, obs, **kw: GuildEvidence(id=eid, personId=pid, skillId="SK-OD", kind=kind, at=day, observerId=obs, source=kw.pop("source", src), raw=kw.pop("raw", "seen"), **kw)  # noqa: E731
    guild.write_evidence(e("e-live-desig", "p-assessor", "designation", "p-lead", source=EvidenceSource(kind="lead", ref="founding")))
    guild.write_evidence(e("e-live-k", "p-trainee", "knowledge", "p-assessor"))
    for i in range(3):
        guild.write_evidence(e(f"e-live-s{i}", "p-trainee", "supervised", "p-assessor", raw="Read a sample straight after inverting; blanked on fresh medium once and corrected it"))
    (c,) = checks.propose(None)
    try:
        made = checks.brief(c.id, "p-assessor")
    except checks.CheckRefused as err:
        pytest.fail(f"the model's brief was refused on {err.rule}: {err.why}")
    b = made.brief
    print(f"\n{c.id}: {b.model}, ${b.usage.costUsd:.4f}")
    print("  steps:", ", ".join(f"{s.protocolId}:{s.stepId}" for s in b.steps))
    print("  criteria:", ", ".join(f"{x.skillId}#{x.index}" for x in b.criteria))
    for q in b.questions:
        print("  ?", q)
    assert b.criteria and b.questions
