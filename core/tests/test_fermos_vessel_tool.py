"""`fermos_vessel`, `fermos_write`'s `design_vessel` and `fermos_read`'s
kind `vessel` (OF-BLD-020 §4.2, D13, E.4‴).

Every simulation here is test_vessel's STAND-IN (an artifact in §3.1's shape,
invented numbers), and the worker is its stand-in too; nothing starts
BioSTEAM. A person's plant scale, which the service never holds, is a
STAND-IN person's, laid on by a test double of `vessel.design` where a test
needs a design to go through.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import artifacts, audit, module_stores, proposals, tools, vessel
from openferment_core.models import VesselRequest
from openferment_core.validate import SeenSet, validate_plan
from test_module_tools import ctx_for, read
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)
from test_vessel import AEROBIC_ID, ANAEROBIC_ID, FED_ID, override, store, worker  # noqa: F401  (fixtures)

STANDIN_PERSON = "Stand-In Person"


@pytest.fixture()
def marked(store, worker, monkeypatch):  # noqa: F811
    """The audit log and the proposals in the test's store, and the model the
    writes are marked with."""
    monkeypatch.setattr(audit, "PATH", store / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", store / "proposals.json")
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    return store


@pytest.fixture()
def a_person_typed_a_scale(monkeypatch):
    """STAND-IN for a service that holds a named person's plant scale. This
    service holds none (it is typed in fermOS → Vessel and kept in a
    browser), so a real call is refused until a person designs on screen."""
    real = vessel.design

    def with_a_person(req: VesselRequest):
        aid = req.simulation or req.fit
        return real(req.model_copy(update={"overrides": [*req.overrides,
                                                         override(aid, "plant_scale", 2000.0, by=STANDIN_PERSON)]}))

    monkeypatch.setattr(vessel, "design", with_a_person)


def ctx(archived=True):
    c = tools.ToolContext(include_archived=archived)
    c.ask_id, c.model = "ask-42", "claude-haiku-5-5"
    return c


def ask(**fields):
    return {"simulationArtifact": "", "fitArtifact": "", "vesselType": "", "klaMethod": "", **fields}


# ── the tool's shape ───────────────────────────────────────────────────


def test_fermos_vessel_is_registered_loose_with_ids_and_words_only():
    t = tools.REGISTRY["fermos_vessel"]
    assert "fermos_vessel" in tools.WHITELIST and not t.strict
    props = t.info().inputSchema["properties"]
    assert set(props) == {"simulationArtifact", "fitArtifact", "vesselType", "klaMethod"}
    # E.4‴: no field of a fermos_* schema is numeric.
    assert all(p.get("type") == "string" for p in props.values()), props
    assert "never type a number" in t.description and "named person" in t.description


def test_a_number_or_a_field_it_does_not_take_is_refused_before_anything_runs(marked):
    assert "a number was typed" in tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, klaMethod=3), ctx()).error
    r = tools.run("fermos_vessel", {**ask(simulationArtifact=AEROBIC_ID), "plantScale": "two thousand tonnes"}, ctx())
    assert "refused its input" in r.error
    assert audit.read() == []


# ── refused in words ───────────────────────────────────────────────────


def test_without_a_persons_scale_the_tool_returns_the_refusals_words_and_keeps_nothing(marked):
    r = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID), ctx())
    assert r.error.startswith("fermos_vessel refused: a vessel design needs plant_scale")
    assert "a model never supplies one" in r.error and "fermOS → Vessel" in r.error
    assert r.evidence == [] and audit.read() == []
    assert not [a for a in artifacts.all_artifacts() if a.tool == vessel.TOOL]
    # fermos_write's design_vessel is the same function, refused alike.
    w = tools.run("fermos_write", {"action": "design_vessel", "target": "", "fields": {"simulationArtifact": AEROBIC_ID},
                                   "note": "the batch needs a vessel"}, ctx())
    assert w.error == r.error.replace("fermos_vessel", "fermos_write", 1)


def test_one_source_a_known_vessel_type_and_a_correlation_the_class_runs(marked):
    assert "name one kept simulation" in tools.run("fermos_vessel", ask(), ctx()).error
    both = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, fitArtifact=ANAEROBIC_ID), ctx())
    assert "not both" in both.error
    assert "is neither" in tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, vesselType="airlift"), ctx()).error
    # The stand-in class runs Riet for a stirred tank and Dewes for a bubble column.
    wrong = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, vesselType="bubble-column", klaMethod="Riet"),
                      ctx()).error
    assert "runs Dewes for a bubble column; 'Riet' is not one" in wrong
    idle = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, klaMethod="Labik"), ctx()).error
    assert "Labik" in idle and "not implemented" in idle
    assert "no kLa correlation" in tools.run("fermos_vessel", ask(simulationArtifact=ANAEROBIC_ID, klaMethod="Riet"),
                                             ctx()).error
    assert "fed-batch's feed" in tools.run("fermos_vessel", ask(simulationArtifact=FED_ID), ctx()).error
    assert "no artifact" in tools.run("fermos_vessel", ask(simulationArtifact="ffffffffffffffff"), ctx()).error


# ── a design that goes through ─────────────────────────────────────────


def test_a_design_is_kept_cited_by_its_artifact_id_and_marked_as_the_models(marked, a_person_typed_a_scale, worker):  # noqa: F811
    r = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, vesselType="bubble-column", klaMethod="Dewes"), ctx())
    assert r.error is None, r.error
    (ev,) = r.evidence
    s = r.summary
    art = artifacts.get(ev.id)
    assert art.tool == vessel.TOOL and ev.id == s["artifactId"] == s["evidenceId"]
    assert ev.provenance == art.provenance == s["provenance"] == "demo"  # a person's scale is an assumption
    assert ev.unit == "vessels" and ev.figure == "oxygen-balance" and ev.basis.artifactId == art.id
    assert s["state"] == "open" and s["vesselType"] == "bubble-column" and s["assumedBy"] == [STANDIN_PERSON]
    assert s["design"] and s["cost"]["costIndex"] and len(json.dumps(s, ensure_ascii=False)) <= tools.MAX_SUMMARY_CHARS
    # How BioSTEAM found its duty, and what the cross-check rests on, in the service's words (§4.R).
    assert s["heat"]["dutyNote"] and "heats of formation" in s["heat"]["dutyNote"] and s["heat"]["conventionNote"]
    # The kLa correlation and the vessel type the call named are its conventions, in the basis.
    named = {i.name: i for i in art.inputs}
    assert named["method"].value == "Dewes" and named["method"].source.kind == "convention"
    assert "klaMethod" in named["method"].source.note
    assert named["vessel type"].source.note == "the vessel type the request chose"
    [(_, sent)] = [c for c in worker.calls if c[0] == "vessel_design"]
    assert sent["design"] == "Bubble column" and sent["params"]["method"] == "Dewes"
    [line] = audit.read()
    assert (line.agent, line.who, line.module, line.action, line.state, line.target, line.askId, line.effort) == (
        "model", "claude-haiku-5-5", "fermos", "design_vessel", "open", AEROBIC_ID, "ask-42", "medium")
    assert line.detail["tool"] == "fermos_vessel" and line.detail["artifactId"] == art.id
    # At no gate: nothing was proposed.
    assert proposals.read().proposals == []
    # fermos_write's design_vessel is the same design, marked with its own name.
    w = tools.run("fermos_write", {"action": "design_vessel", "target": "", "note": "again", "fields": {
        "simulationArtifact": AEROBIC_ID, "vesselType": "bubble-column", "klaMethod": "Dewes"}}, ctx())
    assert w.error is None and w.evidence[0].id == ev.id
    assert audit.read()[-1].detail["tool"] == "fermos_write" and audit.read()[-1].detail["note"] == "again"


def test_a_claim_cites_a_design_its_run_returned_and_no_other(marked, a_person_typed_a_scale, pool):  # noqa: F811
    r = tools.run("fermos_vessel", ask(simulationArtifact=ANAEROBIC_ID), ctx())
    assert r.error is None, r.error
    seen = SeenSet()
    seen.add(r)
    ev = r.evidence[0]

    def claim(cid, evidence_ids=(), refs=()):
        return {"id": cid, "text": "The batch needs several vessels of the size the design names.", "recordIds": [],
                "support": "direct", "passages": [], "evidenceIds": list(evidence_ids), "moduleRefs": list(refs)}

    got = validate_plan([claim("c1", [ev.id]), claim("c2", ["0123456789abcdef"])], seen, pool)
    assert [c.id for c in got.claims] == ["c1"] and got.claims[0].provenance == "demo"
    assert "cites what no tool returned in this run: 0123456789abcdef" in got.reasons[0]
    # A refused call teaches the set nothing.
    nothing = SeenSet()
    nothing.add(tools.run("fermos_vessel", ask(simulationArtifact=ANAEROBIC_ID, vesselType="stirred-tank"), ctx()))
    assert not nothing.evidence
    # fermos_read's vessel row is citable once read.
    rows = read("fermos", ctx_for(pool, artifacts=artifacts.all_artifacts), kind="vessel")
    assert [row.ref for row in rows.rows] == [f"fermos/vessel/{ev.id}"]
    seen.add(rows)
    [c] = validate_plan([claim("c3", refs=[f"fermos/vessel/{ev.id}"])], seen, pool).claims
    assert c.provenance == "demo"


def test_a_design_read_as_a_row_is_cited_by_its_ref_and_one_cited_by_evidence_id_is_told_so(
        marked, a_person_typed_a_scale, pool):  # noqa: F811
    """A vessel design is a kept run, as a simulation is (validate.KEPT_RUNS
    maps `fermos.vessel` to the `vessel` row, OF-BLD-020 §3.4 and §4.2):
    SeenSet learns it from the Evidence fermos_vessel returns and from
    fermos_read's row, and a design a read returned only as a row is cited by
    its ref, never by an evidence id no tool returned."""
    made = tools.run("fermos_vessel", ask(simulationArtifact=ANAEROBIC_ID), ctx())
    assert made.error is None, made.error
    aid = made.evidence[0].id
    ref = f"fermos/vessel/{aid}"
    from_tool = SeenSet()
    from_tool.add(made)
    assert from_tool.runs == {aid: ref}, "SeenSet learns the design from the evidence fermos_vessel returns"
    seen = SeenSet()
    seen.add(read("fermos", ctx_for(pool, artifacts=artifacts.all_artifacts), kind="vessel"))
    assert seen.runs == {aid: ref}, "and from fermos_read's row"
    by_ref = {"id": "c1", "text": "The batch needs several vessels of the size the design names.", "recordIds": [],
              "support": "direct", "passages": [], "evidenceIds": [], "moduleRefs": [ref]}
    by_id = dict(by_ref, id="c2", moduleRefs=[], evidenceIds=[aid])
    ghost = dict(by_ref, id="c3", moduleRefs=["fermos/vessel/0123456789abcdef"])
    out = validate_plan([by_ref, by_id, ghost], seen, pool)
    assert [c.id for c in out.claims] == ["c1"] and out.claims[0].provenance == "demo"
    assert out.rejected == 2
    assert out.reasons[0].startswith(f"c2: cites {aid} by evidence id, which a read returned only as a row: cite {ref}")
    assert out.reasons[1].startswith("c3: cites what no tool returned in this run")
    # The tool's own Evidence stays citable by its id.
    [kept] = validate_plan([dict(by_id, id="c4")], from_tool, pool).claims
    assert kept.id == "c4" and kept.evidenceIds == [aid]


def test_fermos_read_lists_kept_designs_by_their_id_or_their_simulations(marked, a_person_typed_a_scale, pool):  # noqa: F811
    made = tools.run("fermos_vessel", ask(simulationArtifact=ANAEROBIC_ID), ctx())
    aid = made.evidence[0].id
    c = ctx_for(pool, artifacts=artifacts.all_artifacts)
    assert "vessel" in module_stores.KINDS["fermos"]
    by_id, by_sim = read("fermos", c, ids=[aid]), read("fermos", c, ids=[ANAEROBIC_ID])
    assert [r.id for r in by_id.rows] == [aid]
    # By the simulation's id: the simulation itself (kind simulation, §3.4) and the design made for it.
    assert [(r.kind, r.id) for r in by_sim.rows] == [("simulation", ANAEROBIC_ID), ("vessel", aid)]
    assert [r.id for r in read("fermos", c, ids=[ANAEROBIC_ID], kind="vessel").rows] == [aid]
    row = by_id.rows[0]
    assert row.kind == "vessel" and row.state == "open" and row.provenance == "demo"
    assert row.detail["unitClass"] == "NRELAnaerobicBatchBioreactor" and row.detail["source"] == ANAEROBIC_ID
    assert "NRELAnaerobicBatchBioreactor" in row.label and ANAEROBIC_ID in row.label
    assert [r.id for r in read("fermos", c, words="fermenter").rows] == [aid]


def test_a_refusal_reads_in_the_trace_with_its_prefix_once(marked):
    """Seen live (2026-10-21 05:50): the trace line of a refused fermos_vessel
    read "fermos_vessel refused: fermos_vessel refused: …". The line is
    written by code from the tool's own error, which already names the tool."""
    from openferment_core import postdoc_agent

    asked = ask(simulationArtifact=AEROBIC_ID)
    r = tools.run("fermos_vessel", asked, ctx())
    assert r.error.startswith("fermos_vessel refused: ")
    line = postdoc_agent._summary_line("fermos_vessel", asked, r)
    assert line.startswith("fermos_vessel refused: ") and line.count("fermos_vessel refused") == 1, line
    assert "plant_scale" in line
    # A tool whose error does not name it still reads as refused, named once.
    other = postdoc_agent._summary_line("search_records", {}, tools.ToolResult(error="the field is unknown"))
    assert other == "search_records refused: the field is unknown"
    # The number refusal tools.run writes names the tool too, and reads once.
    numbered = tools.run("fermos_vessel", ask(simulationArtifact=AEROBIC_ID, klaMethod=3), ctx())
    assert postdoc_agent._summary_line("fermos_vessel", {}, numbered).count("fermos_vessel refused") == 1
    # An error that names the tool another way is the line itself, the tool named once.
    down = tools.ToolResult(error="fermos_vessel could not design the vessel: the simulator is starting")
    assert postdoc_agent._summary_line("fermos_vessel", {}, down) == down.error
