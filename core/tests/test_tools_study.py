"""The study tools and the registry's quantities (tools/engine.py, studies.py,
literature.py; tools/__init__.py; alpha 2.0 stage 6; ADR-006), offline.

The worker is test_runs.py's STAND-IN (the sugarcane plant's parameters, a
small SFF file). A number stands in a tool's input only inside a quantity, and
the service writes the quantity's origin from who called: the answering
model's estimate, or the person the endpoint names; nobody named, nothing
typed. A model keeps a scenario of its estimates, runs it and reads the run's
numbers as evidence ids on the run's artifact, the run `assumed` and audited as
the model's; it runs a plant at the library's defaults, compares two runs and
lists the project's studies; a refusal is the plant's or the service's words.
The literature tools list the documents the project holds and read one
section's passages, citable as search_passages' are.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from openferment_core import audit, intake, llm, tools
from openferment_core.api import app
from openferment_core.engine import library, simulator
from openferment_core.literature import kit
from openferment_core.models import Origin

from test_runs import StandIn

MODEL = llm.DEFAULT_PRIMARY


class Priced(StandIn):
    """test_runs' stand-in, whose library run solves a selling price that
    rises with the cane's: a run with numbers to cite."""

    def __call__(self, op: str, args: dict):
        out = super().__call__(op, args)
        if op == "library_run":
            cane = (args.get("overrides") or {}).get("stream.sugarcane.price", 0.03455)
            out = {**out, "price": {"priced": True, "solvedPrice": round(0.4 + 10 * cane, 6),
                                    "units": {"solvedPrice": "USD/kg"}}}
        return out


@pytest.fixture
def worker(monkeypatch):
    stand_in = Priced()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def as_model() -> tools.ToolContext:
    return tools.ToolContext(model=MODEL)


def dearer_cane(note: str = "a delivered price above the package's") -> dict:
    return {"title": "A dearer cane", "plant": "sugarcane", "configuration": "", "note": "",
            "values": [{"key": "stream.sugarcane.price", "quantity": {"value": 0.05, "unit": "USD/kg", "note": note}}]}


# ── the registry's quantities ───────────────────────────────────────────


def test_a_number_stands_only_inside_a_quantity_where_the_tool_asks_for_one():
    asked = tools.quantity_paths(tools.REGISTRY["study_scenario"].input_model.model_json_schema())
    assert asked == {"values[].quantity"}
    assert tools.numbers_in({"values": [{"key": "k", "quantity": {"value": 0.05, "unit": "USD/kg"}}]}, quantities=asked) == []
    assert tools.numbers_in({"values": [{"key": "k", "quantity": {"value": 0.05, "unit": "USD/kg"}}]}) == [
        "values[0].quantity.value"], "a quantity where no tool asks for one is a number like any"
    assert tools.numbers_in({"fields": {"value": 2.5, "unit": "g L-1"}}, quantities=asked) == ["fields.value"]
    one = frozenset({"quantity"})
    assert tools.numbers_in({"quantity": {"value": 1, "unit": "kg", "low": 0.5, "high": 2}}, quantities=one) == []
    assert tools.numbers_in({"quantity": {"value": 3}}, quantities=one) == ["quantity.value"], "no unit, no quantity"
    assert tools.numbers_in({"quantity": {"value": 1, "unit": "kg", "step": 2}}, quantities=one) == ["quantity.step"]
    assert tools.numbers_in({"quantity": {"value": float("nan"), "unit": "kg"}}, quantities=one) == ["quantity.value"]
    assert tools.numbers_in({"plant": "sugarcane", "rate": 0.1}, quantities=one) == ["rate"]
    assert all(tools.quantity_paths(t.input_model.model_json_schema()) == set() for n, t in tools.REGISTRY.items()
               if n != "study_scenario"), "study_scenario is the one tool that asks for a quantity"


def test_the_service_writes_a_quantitys_origin_from_who_called():
    wrote = {"value": 0.05, "unit": "USD/kg", "note": "a quoted price",
             "origin": {"kind": "record", "ref": "r-made-up", "note": "ignored when a note stands beside the value"}}
    out = tools.stamped({"values": [{"quantity": wrote}]}, Origin(kind="model-estimate", by=MODEL, at="2026-10-30"),
                        frozenset({"values[].quantity"}))
    origin = out["values"][0]["quantity"]["origin"]
    assert origin == {"kind": "model-estimate", "by": MODEL, "at": "2026-10-30", "note": "a quoted price"}
    assert tools.ToolContext(model=MODEL).author().kind == "model-estimate"
    assert tools.ToolContext(person="Ada Moreno").author().kind == "person-assumption"
    assert tools.ToolContext().author() is None


def test_a_quantity_nobody_can_be_named_for_is_refused(worker):
    r = tools.run("study_scenario", dearer_cane(), tools.ToolContext())
    assert r.error and "names who typed it" in r.error


# ── a scenario of the model's estimates, run and read ──────────────────


def test_a_model_keeps_a_scenario_of_its_estimates_runs_it_and_cites_the_runs_numbers(worker):
    made = tools.run("study_scenario", dearer_cane(), as_model())
    assert made.error is None, made.error
    sid = made.summary["scenarioId"]
    (value,) = made.summary["values"]
    assert (value["origin"], value["by"], value["note"]) == ("model-estimate", MODEL, "a delivered price above the package's")
    ran = tools.run("engine_run", {"plant": "", "configuration": "", "scenario": sid, "note": "the dearer cane"}, as_model())
    assert ran.error is None, ran.error
    s = ran.summary
    assert (s["scenarioId"], s["provenance"], s["by"]) == (sid, "assumed", MODEL)
    assert s["valuesSet"] == [{"key": "stream.sugarcane.price", "value": 0.05, "unit": "USD/kg",
                               "origin": "model-estimate", "by": MODEL}]
    assert ran.evidence and all(e.id.startswith(f"{s['artifactId']}:") and e.basis.artifactId == s["artifactId"]
                                and e.provenance == "assumed" for e in ran.evidence)
    lines = [(a.agent, a.who, a.action, a.target) for a in audit.read() if a.module == "proforma"]
    assert ("model", MODEL, "study_scenario", sid) in lines and ("model", MODEL, "engine_run", s["runId"]) in lines
    again = tools.run("engine_report", {"run": s["runId"]}, as_model())
    assert [e.id for e in again.evidence] == [e.id for e in ran.evidence]
    read = tools.run("study_read", {"kind": "scenario", "words": "", "limit": 20}, as_model())
    assert [(r["id"], r["runIds"]) for r in read.summary["rows"]] == [(sid, [s["runId"]])]


def test_a_plant_runs_at_the_librarys_defaults_and_two_runs_compare(worker):
    base = tools.run("engine_run", {"plant": "sugarcane"}, as_model())
    assert base.error is None and base.summary["provenance"] != "assumed" and base.summary["valuesSet"] == []
    sid = tools.run("study_scenario", dearer_cane(), as_model()).summary["scenarioId"]
    dearer = tools.run("engine_run", {"scenario": sid}, as_model())
    compared = tools.run("study_compare", {"title": "The cane's price", "runs": [base.summary["runId"], dearer.summary["runId"]]},
                         as_model())
    assert compared.error is None, compared.error
    assert compared.summary["provenance"] == "assumed" and compared.summary["runIds"] == [
        base.summary["runId"], dearer.summary["runId"]]
    assert all(e.id.endswith(":2") and e.basis.artifactId == compared.summary["artifactId"] for e in compared.evidence)
    kinds = {r["kind"] for r in tools.run("study_read", {}, as_model()).summary["rows"]}
    assert kinds == {"scenario", "comparison"}


def test_what_a_run_cannot_be_is_refused_in_words(worker):
    assert "one of the two" in tools.run("engine_run", {}, as_model()).error
    assert "one of the two" in tools.run("engine_run", {"plant": "sugarcane", "scenario": "ssc-x"}, as_model()).error
    assert "no scenario ssc-nonesuch" in tools.run("engine_run", {"scenario": "ssc-nonesuch"}, as_model()).error
    assert "engine_report refused" in tools.run("engine_report", {"run": "nonesuch"}, as_model()).error
    wrong = dearer_cane() | {"values": [{"key": "stream.nonesuch", "quantity": {"value": 1, "unit": "kg"}}]}
    assert tools.run("study_scenario", wrong, as_model()).error.startswith("study_scenario refused")
    ranged = dearer_cane() | {"values": [{"key": "stream.sugarcane.price", "quantity": {"value": 0.05, "unit": "USD/kg",
                                                                                      "low": 0.04, "high": 0.06}}]}
    assert "Extra inputs are not permitted" in tools.run("study_scenario", ranged, as_model()).error


def test_a_person_the_endpoint_names_types_an_assumption(worker):
    client = TestClient(app, base_url="http://127.0.0.1")
    made = client.post("/api/tools/study_scenario", params={"by": "Ada Moreno"}, json=dearer_cane()).json()
    assert made["error"] is None and made["summary"]["values"][0]["origin"] == "person-assumption"
    assert made["summary"]["values"][0]["by"] == "Ada Moreno"
    refused = client.post("/api/tools/study_scenario", json=dearer_cane()).json()
    assert "names who typed it" in refused["error"]


def test_the_shelf_and_a_plants_parameters(worker):
    shelf = tools.run("engine_plants", {"words": "", "limit": 40}, as_model())
    ids = [p["plant"] for p in shelf.summary["plants"]]
    assert "sugarcane" in ids and "cellulosic_ethanol_v0" in ids
    assert all(p["kind"] in ("plant", "flowsheet") for p in shelf.summary["plants"])
    narrowed = tools.run("engine_plants", {"words": "sugarcane"}, as_model()).summary["plants"]
    assert [p["plant"] for p in narrowed] == ["sugarcane"]
    params = tools.run("engine_parameters", {"plant": "sugarcane", "words": "price"}, as_model())
    assert params.error is None and any(p["key"] == "stream.sugarcane.price" and p["unit"] == "USD/kg"
                                        for p in params.summary["parameters"])
    assert "refused" in tools.run("engine_parameters", {"plant": "nonesuch"}, as_model()).error


# ── the literature tools ───────────────────────────────────────────────


@dataclass
class _Document:
    title: str = "Polyhydroxybutyrate on xylose hydrolysate"
    authors: list = field(default_factory=lambda: ["A. Moreno"])
    publication_year: int = 2021
    journal: str = "A Journal"
    doi: str = "10.0000/example"
    license_class: str = "open"


@dataclass
class _Held:
    document: _Document
    sections: list


SECTIONS = [
    {"id": "p0", "heading": "Abstract", "text": "Polyhydroxybutyrate accumulated in cells fed xylose hydrolysate.",
     "isTable": False},
    {"id": "p1", "heading": "Results", "text": "The granules filled the cytoplasm.", "isTable": False},
]


def test_the_literature_tools_list_the_documents_and_read_a_sections_passages(monkeypatch):
    monkeypatch.setattr(intake, "held", lambda project_id=None: {
        "doc-1": {"title": "Polyhydroxybutyrate on xylose hydrolysate", "year": 2021, "collector": "europepmc",
                  "licenceClass": "open", "passages": 2}})

    def passages(document_id, *, project_id):
        if document_id != "doc-1":
            raise KeyError(document_id)
        return _Held(_Document(), SECTIONS)

    monkeypatch.setattr(kit, "passages", passages)
    listed = tools.run("literature_sources", {"words": "xylose"}, as_model())
    assert [d["documentId"] for d in listed.summary["documents"]] == ["doc-1"]
    assert tools.run("literature_sources", {"words": "glucose"}, as_model()).summary["documents"] == []
    whole = tools.run("literature_document", {"document": "doc-1"}, as_model())
    assert whole.summary["sections"] == ["Abstract", "Results"] and whole.passages == []
    results = tools.run("literature_document", {"document": "doc-1", "section": "Results"}, as_model())
    (p,) = results.passages
    assert (p.id, p.paperId, p.sectionId, p.text) == ("doc-1:p1:0", "doc-1", "p1", "The granules filled the cytoplasm.")
    assert "no section headed" in tools.run("literature_document", {"document": "doc-1", "section": "Methods"}, as_model()).error
    assert "holds no readable document" in tools.run("literature_document", {"document": "doc-2"}, as_model()).error
