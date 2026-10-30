"""Carrying an alpha 1.0 data directory into a new project (import_alpha1.py):
each store's records land in their rows and read back through the store,
the whole directory lands or nothing does, and the files stay where they
were. The records are fictional placeholders."""
from __future__ import annotations

import json

import pytest

from openferment_core import artifacts, audit, biorepo, db, extract, guild, import_alpha1, llm, projects, proposals
from openferment_core.models import (
    AuditEntry,
    BioRepo,
    Candidate,
    EvidenceSource,
    ExtractResponse,
    Guild,
    GuildEvidence,
    GuildPerson,
    Proposal,
    Proposals,
    Quantity,
    ReviewDecision,
)

CANDIDATE = Candidate(id="cl1-T7-0a1b2c3d", paperId="T7", sectionId="s1", quote="Placeholder B | 3 | mg L-1",
                      field="titer_secreted", value=3, unit="mg L-1", si=Quantity(value=0.003, unit="g L-1"))
DECISION = ReviewDecision(status="rejected", provenance="unverified", reviewer="Ada Moreno", recordId=CANDIDATE.id,
                          at="2026-10-20T00:00:00Z", rejectReason="a placeholder row")
LEAD = GuildPerson(id="p-ada", name="Ada Moreno", role="lead", joinedAt="2026-10-01", addedAt="2026-10-01T00:00:00Z")
ENTRY = GuildEvidence(id="e-0001", personId="p-ada", skillId="SK-OD", kind="independent", at="2026-10-02",
                      source=EvidenceSource(kind="lead", ref="a placeholder training record"), raw="a placeholder entry", observerId=None)
PROPOSAL = Proposal(id="pr-1", at="2026-10-03T00:00:00Z", module="runbooks", action="lock", gate="lock",
                    title="Runbooks: lock — rb-1", why="w", how="h", by=llm.DEFAULT_PRIMARY, target="rb-1")
LINES = [AuditEntry(at="2026-10-03T00:00:00Z", agent="model", who=llm.DEFAULT_PRIMARY, module="runbooks",
                    action="lock", state="proposed", target="rb-1", askId="ask-1")]


@pytest.fixture
def alpha1(tmp_path):
    data = tmp_path / "data"
    (data / "candidates" / "hand").mkdir(parents=True)
    (data / "biorepo.json").write_text(BioRepo(decisions={CANDIDATE.id: DECISION}, records=[CANDIDATE]).model_dump_json())
    (data / "guild.json").write_text(Guild(people=[LEAD], evidence=[ENTRY]).model_dump_json())
    (data / "proposals.json").write_text(Proposals(proposals=[PROPOSAL]).model_dump_json())
    (data / "audit.jsonl").write_text("".join(line.model_dump_json() + "\n" for line in LINES))
    extraction = ExtractResponse(paperId="T7", extractedAt="2026-10-02T00:00:00Z", candidates=[CANDIDATE])
    (data / "candidates" / "T7.json").write_text(extraction.model_dump_json())
    return data


def test_every_store_lands_in_the_new_project_and_reads_back_through_it(alpha1):
    before = sorted(p.name for p in alpha1.rglob("*"))
    pid, counts = import_alpha1.carry(alpha1, "Alpha 1.0 records", "Ada Moreno")
    assert counts["decisions"] == 1 and counts["people"] == 1 and counts["entries"] == 1
    assert counts["proposals"] == 1 and counts["audit rows"] == 1 and counts["extractions"] == 1
    with projects.using(pid):
        repo = biorepo.read()
        assert repo.decisions == {CANDIDATE.id: DECISION} and repo.records == [CANDIDATE]
        ledger = guild.read()
        assert ledger.people == [LEAD] and [e.id for e in ledger.evidence] == ["e-0001"]
        assert proposals.read().proposals == [PROPOSAL]
        assert extract.cached("T7").candidates == [CANDIDATE]
        assert [a.action for a in audit.read()] == ["create_project", "lock", "import_alpha1"]
    # The test project holds none of it, and the files are where they were.
    assert biorepo.read().decisions == {}
    assert sorted(p.name for p in alpha1.rglob("*")) == before


def test_an_artifact_alpha_1_called_demo_lands_assumed_with_its_outputs_hash(alpha1):
    """ADR-006: the class alpha 1.0 named `demo` is `assumed`. An artifact
    that names it, in its own provenance and in its output, is carried under
    the new name; its output hash is the renamed output's and its id stays."""
    output = {"evidence": {"provenance": "demo", "value": 1.5}, "note": "demo"}
    raw = {"id": "00000000000000ee", "tool": "proforma.run", "toolVersion": "1", "provenance": "demo",
           "inputs": [{"name": "price", "value": 0.5, "unit": "USD/kg",
                       "source": {"kind": "assumption", "by": "Ada Moreno", "note": "typed on 2026-10-02"}}],
           "output": output, "outputHash": artifacts.output_hash(output), "createdAt": "2026-10-02T00:00:00Z",
           "durationMs": 1}
    (alpha1 / "artifacts").mkdir()
    (alpha1 / "artifacts" / "00000000000000ee.json").write_text(json.dumps(raw))
    pid, counts = import_alpha1.carry(alpha1, "Alpha 1.0 records", "Ada Moreno")
    assert counts["artifacts"] == 1
    with projects.using(pid):
        art = artifacts.get("00000000000000ee")
    assert art.provenance == "assumed" and art.output == {"evidence": {"provenance": "assumed", "value": 1.5},
                                                          "note": "demo"}
    assert art.outputHash == artifacts.output_hash(art.output) != raw["outputHash"]


def test_a_file_that_cannot_be_read_refuses_the_whole_directory_and_writes_nothing(alpha1):
    (alpha1 / "audit.jsonl").write_text('{"at": "2026-10-03"}\n')
    with pytest.raises(import_alpha1.ImportRefused, match="audit.jsonl line 1"):
        import_alpha1.carry(alpha1, "Alpha 1.0 records", "Ada Moreno")
    assert [p.id for p in projects.listed()] == ["test-project"]


def test_a_write_that_fails_part_way_leaves_no_project_behind(alpha1, monkeypatch):
    real = db.rows.put
    calls = {"n": 0}

    async def failing(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("the database went away")
        return await real(*args, **kwargs)

    monkeypatch.setattr(import_alpha1.rows, "put", failing)
    with pytest.raises(RuntimeError, match="went away"):
        import_alpha1.carry(alpha1, "Alpha 1.0 records", "Ada Moreno")
    assert [p.id for p in projects.listed()] == ["test-project"]


def test_the_command_reports_what_it_carried_and_refuses_in_words(alpha1, capsys, monkeypatch):
    monkeypatch.setattr(import_alpha1, "load_dotenv", lambda *a, **k: None)
    assert import_alpha1.main(["--name", "Carried", "--by", "Ada Moreno", "--data", str(alpha1)]) == 0
    out = capsys.readouterr().out
    assert "carried" in out and "1  decisions" in out and "left as they were" in out
    assert import_alpha1.main(["--name", "Again", "--by", "Ada Moreno", "--data", str(alpha1 / "nowhere")]) == 2
    assert "is not a directory" in capsys.readouterr().err
    assert json.loads((alpha1 / "proposals.json").read_text())["proposals"][0]["id"] == "pr-1"
