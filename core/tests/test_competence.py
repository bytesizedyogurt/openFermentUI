"""competence.py reproduces src/engine/competence.ts (OF-BLD-013 §2.1).

The fixture is what the TypeScript engine answered, written by
`pnpm export:competence-fixtures`; `pnpm test:core` regenerates it first, so
it never lags the engine. Every status on every ledger in it has to come out
the same here, field for field.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core.competence import all_statuses
from openferment_core.models import GuildEvidence, GuildPerson

FIXTURE = Path(__file__).parent / "fixtures" / "competence.json"


def _load():
    if not FIXTURE.exists():
        pytest.fail(f"{FIXTURE} is missing; run `pnpm export:competence-fixtures` (pnpm test:core does)")
    return json.loads(FIXTURE.read_text())


def test_every_status_matches_the_reference():
    data = _load()
    skills = {s["id"]: s for s in data["skills"]}
    compared = 0
    for case in data["cases"]:
        people = [GuildPerson(**p) for p in case["people"]]
        evidence = [GuildEvidence(**e) for e in case["evidence"]]
        mine = all_statuses(evidence, people, skills, case["today"])
        assert len(mine) == len(case["statuses"]), case["name"]
        for want in case["statuses"]:
            got = mine[(want["personId"], want["skillId"])]
            for field in ("level", "effective", "lapsed", "suspended", "lapsesAt", "supervisedCount", "knowledgeComplete", "confidence"):
                assert getattr(got, field) == want[field], (
                    f"{case['name']}: {want['personId']} {want['skillId']} {field}: "
                    f"python {getattr(got, field)!r}, typescript {want[field]!r}"
                )
            compared += 1
    assert compared > 500
