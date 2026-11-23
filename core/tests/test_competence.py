"""competence.py reproduces src/engine/competence.ts (OF-BLD-013 §2.1).

The fixture is what the TypeScript engine answered, written by
`pnpm export:competence-fixtures`; `pnpm test:core` regenerates it first, so
it never lags the engine. Every status on every ledger in it has to come out
the same here, field for field. A second file holds a skill kept in the
project's skill catalogue with no policy (alpha 2.2 E.12), which both sides
leave out of every level.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core.competence import all_statuses, unrated
from openferment_core.models import GuildEvidence, GuildPerson

FIXTURE = Path(__file__).parent / "fixtures" / "competence.json"
UNRATED = Path(__file__).parent / "fixtures" / "competence-unrated.json"


def _load(path: Path = FIXTURE):
    if not path.exists():
        pytest.fail(f"{path} is missing; run `pnpm export:competence-fixtures` (pnpm test:core does)")
    return json.loads(path.read_text())


def _compared(data) -> int:
    """How many statuses came out the same here as the TypeScript side wrote them, field for field."""
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
    return compared


def test_every_status_matches_the_reference():
    assert _compared(_load()) > 500


def test_a_skill_with_no_policy_matches_the_reference():
    data = _load(UNRATED)
    open_ = next(s for s in data["skills"] if s["id"] == "SK-OPEN")
    assert unrated(open_) is not None, "the fixture's skill keeps no policy"
    for case in data["cases"]:
        held = [s for s in case["statuses"] if s["skillId"] == "SK-OPEN"]
        assert held and all(s["level"] == 0 and s["effective"] == 0 for s in held), case["name"]
        assert not any(p["skillId"] == "SK-OPEN" for p in case["pairs"]), case["name"]
    assert _compared(data) > 50
