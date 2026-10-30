"""Postdoc drafts a runbook, and the service writes every number
(OF-BLD-014 §9.2). The pool is test_tools' stand-in fixture; the evidence
items are built here. Nothing here is a measurement."""
from __future__ import annotations

import pytest

from openferment_core import runbook_draft, tools
from openferment_core.models import ComputedBasis, DraftItem, DraftMeasure, Evidence, Range
from openferment_core.validate import SeenSet
from test_postdoc_agent import Script, ask, plan
from test_tools import pool  # noqa: F401

# A strain no archived program holds: with the switch off the tool refuses
# an archived one before it drafts anything (OF-BLD-016 §2.R, test_programs).
PRODUCT, STRAIN = "taq-dna-polymerase", "s-cerevisiae-s288c"


def ev(eid, value, *, figure, interval=None, unit="g g-1"):
    return Evidence(id=eid, label=f"stand-in {figure}", value=value, unit=unit, provenance="computed", figure=figure,
                    interval=Range(low=interval[0], high=interval[1]) if interval else None,
                    basis=ComputedBasis(tool="t", toolVersion="1", inputs=[], artifactId=f"art-{eid}", at="2026-10-15T00:00:00Z"))


def seen_with(*evidence, records=()):
    s = SeenSet()
    for e in evidence:
        s.evidence[e.id] = e
    s.records.update(records)
    return s


def build(pool, seen, items, measures=(), title="Polymer on xylose hydrolysate"):  # noqa: F811
    return runbook_draft.build(title, PRODUCT, STRAIN, list(items), list(measures), seen, pool,
                               {PRODUCT}, {STRAIN})


def test_a_ceiling_becomes_a_bound_and_a_forecast_an_interval_with_the_artifacts_numbers(pool):  # noqa: F811
    c, f = ev("ev-c", 0.593, figure="ceiling"), ev("ev-f", 7.2, figure="trajectory", interval=(6.1, 8.4), unit="g L-1")
    d, left = build(pool, seen_with(c, f), [DraftItem(label="Yield ceiling", evidenceId="ev-c"),
                                            DraftItem(label="Final polymer", evidenceId="ev-f")],
                    [DraftMeasure(label="Polymer at harvest", unit="g/L", timepoint="harvest", itemLabel="Final polymer")])
    bound, interval = d.predictions
    assert (bound.kind, bound.value, bound.artifactId) == ("bound", 0.593, "art-ev-c")
    assert (interval.kind, interval.value, interval.interval.low, interval.interval.high) == ("interval", 7.2, 6.1, 8.4)
    assert d.measures[0].predictionId == interval.id and d.measures[0].timepoint == "harvest" and left == []


def test_records_become_their_range_and_median_with_a_basis_code_wrote(pool):  # noqa: F811
    ids = ["cl1-X1-0000000a", "cl1-X1-0000000c"]
    d, _ = build(pool, seen_with(records=ids), [DraftItem(label="Secreted titre", field="titer_secreted", recordIds=ids)])
    p = d.predictions[0]
    # 900 mg L-1 in the field's canonical unit.
    assert p.kind == "interval" and p.interval.low == p.interval.high == p.value == pytest.approx(0.9)
    assert p.unit == "g L⁻¹" and p.basis == f"Range of 2 reported values: {', '.join(ids)}" and p.recordIds == ids


def test_an_id_the_run_never_saw_is_refused(pool):  # noqa: F811
    with pytest.raises(runbook_draft.DraftRefused, match="was not returned in this run"):
        build(pool, SeenSet(), [DraftItem(label="Yield ceiling", evidenceId="ev-c")])
    with pytest.raises(runbook_draft.DraftRefused, match="were not returned"):
        build(pool, SeenSet(), [DraftItem(label="Secreted titre", field="titer_secreted", recordIds=["cl1-X1-0000000a"])])


def test_a_rejected_record_does_not_enter_the_range(pool):  # noqa: F811
    with pytest.raises(runbook_draft.DraftRefused, match="passes the statistics gate"):
        build(pool, seen_with(records=["cl1-X1-0000000b"]),
              [DraftItem(label="Secreted titre", field="titer_secreted", recordIds=["cl1-X1-0000000b"])])


def test_words_with_a_number_and_unknown_ids_are_refused(pool):  # noqa: F811
    s = seen_with(ev("ev-c", 0.593, figure="ceiling"))
    item = [DraftItem(label="Yield ceiling", evidenceId="ev-c")]
    with pytest.raises(runbook_draft.DraftRefused, match="title holds a number"):
        build(pool, s, item, title="Reach 8 g/L")
    with pytest.raises(runbook_draft.DraftRefused, match="holds a number"):
        build(pool, s, [DraftItem(label="Titre above 5 g/L", evidenceId="ev-c")])
    with pytest.raises(runbook_draft.DraftRefused, match="no product"):
        runbook_draft.build("t", "nothing", STRAIN, item, [], s, pool, {PRODUCT}, {STRAIN})
    with pytest.raises(runbook_draft.DraftRefused, match="does not normalise"):
        build(pool, s, item, [DraftMeasure(label="Yield", unit="furlongs", timepoint="harvest", itemLabel="Yield ceiling")])


def test_a_typed_number_in_the_tool_input_is_refused_by_the_registry(pool):  # noqa: F811
    r = tools.run("draft_runbook", {"title": "t", "productId": PRODUCT, "strainId": STRAIN,
                                    "items": [{"label": "x", "evidenceId": "", "field": "titer_secreted", "recordIds": [], "value": 8}],
                                    "measures": []}, tools.ToolContext(pool_factory=lambda: pool))
    assert r.error and r.draft is None


def test_outside_a_loop_the_tool_refuses(pool):  # noqa: F811
    r = tools.run("draft_runbook", {"title": "t", "productId": PRODUCT, "strainId": STRAIN, "items": [], "measures": []},
                  tools.ToolContext(pool_factory=lambda: pool))
    assert "inside Postdoc's loop" in r.error


def test_the_loop_puts_the_draft_on_the_plan(pool, monkeypatch):  # noqa: F811
    # The catalogues a draft may name come from a project's records; here, the test's own.
    from openferment_core.tools import runbook as runbook_tool

    monkeypatch.setattr(runbook_tool, "_ids", lambda: (frozenset({PRODUCT}), frozenset({STRAIN})))
    draft_call = ("draft_runbook", {"title": "Secreted titre on xylose", "productId": PRODUCT, "strainId": STRAIN,
                                    "items": [{"label": "Secreted titre", "evidenceId": "", "field": "titer_secreted",
                                               "recordIds": ["cl1-X1-0000000a"]}],
                                    "measures": [{"label": "Titre at harvest", "unit": "mg/L", "timepoint": "harvest",
                                                  "itemLabel": "Secreted titre"}]})
    by_field = ("search_records", {"query": "", "field": "titer_secreted", "organism": "", "limit": 10})
    out = ask(Script([by_field], [draft_call], plan()), pool)
    assert out.runbookDraft is not None and out.runbookDraft.predictions[0].value == pytest.approx(0.9)
    unseen = ask(Script([draft_call], plan()), pool)
    assert unseen.runbookDraft is None


# ── §9.R ───────────────────────────────────────────────────────────────


def test_r1_a_measure_must_be_in_its_predictions_units(pool):  # noqa: F811
    s = seen_with(ev("ev-c", 0.593, figure="ceiling"))
    d, left = build(pool, s, [DraftItem(label="Yield ceiling", evidenceId="ev-c")],
                    [DraftMeasure(label="Titre", unit="g/L", timepoint="harvest", itemLabel="Yield ceiling")])
    assert d.measures == [] and any("cannot test" in x for x in left)


def test_r1_a_measure_of_the_same_dimension_records_in_the_predictions_unit(pool):  # noqa: F811
    f = ev("ev-f", 7.2, figure="trajectory", interval=(6.1, 8.4), unit="g L-1")
    d, _ = build(pool, seen_with(f), [DraftItem(label="Final polymer", evidenceId="ev-f")],
                 [DraftMeasure(label="Polymer", unit="mg/L", timepoint="harvest", itemLabel="Final polymer")])
    assert d.measures[0].unit == "g L-1"
