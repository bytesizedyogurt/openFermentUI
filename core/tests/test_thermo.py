"""thermosteam answers property questions (OF-BLD-019 §4.2, D9).

Offline, the Proforma worker is replaced by a STAND-IN that records what it
was asked and answers in the worker's shape with invented numbers, so these
tests check what the service sends and keeps, never what thermosteam says.
Marked `sim` (`pnpm test:sim`), the real worker answers: thermosteam's water,
an ethanol-water stream and a chemical it lacks. Nothing here reads a key or
the network.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma, thermo, tools
from openferment_core.models import Artifact, BasisInput, BasisSource, ThermoProps, ThermoPropsRequest
from openferment_core.validate import SeenSet, validate_plan
from openferment_core.workers import WorkerError

CORE = Path(__file__).resolve().parent.parent
PROTOTYPE = Path(__file__).parent / "fixtures" / "prototype"
RUN_ID = "bbbbbbbbbbbbbbb1"
STANDIN = "STAND-IN for this test: invented numbers in the worker's shape"


def _stream(sid, flows, phase="l", T=305.0, P=101325.0):
    return {"id": sid, "source": "R", "sink": None, "phase": phase, "T": T, "P": P,
            "massFlow": sum(flows.values()), "massFlows": flows, "price": None}


STREAMS = [_stream("beer", {"Water": 90.0, "Ethanol": 10.0}), _stream("vent", {"CO2": 5.0}, phase="g", T=310.0),
           _stream("mixed", {"Water": 1.0}, phase="lg"), _stream("nothing", {"Water": 0.0})]


def _run(aid=RUN_ID, provenance="computed", tool="proforma.run") -> Artifact:
    out = {"flowsheet": "test_line", "streams": STREAMS, "units": [], "tableUnits": {"T": "K", "P": "Pa", "massFlow": "kg/hr"}}
    return Artifact(id=aid, tool=tool, toolVersion="test", output=out, outputHash="0" * 64, provenance=provenance,
                    createdAt="2026-10-20T10:00:00Z", durationMs=0,
                    inputs=[BasisInput(name="flowsheet", value="test_line", unit="", source=BasisSource(kind="convention"))])


def _keep(art: Artifact) -> None:
    folder = artifacts.folder()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{art.id}.json").write_text(art.model_dump_json(), encoding="utf-8")


class StandIn:
    """The worker's `thermo_props` op, in its shape, with invented numbers;
    `refuse` names chemicals to refuse as the worker refuses them."""

    def __init__(self, refuse=()):
        self.calls: list[dict] = []
        self.refuse = set(refuse)

    def __call__(self, op, args):
        assert op == "thermo_props"
        self.calls.append(args)
        names = set(args.get("components") or {}) | ({"Water", "Ethanol"} if args.get("solve") else set())
        lacking = sorted(names & self.refuse)
        if lacking:
            raise WorkerError(f"Refused: thermosteam's chemical library has no chemical named {', '.join(lacking)}")
        if "boom" in names:
            raise WorkerError("RuntimeError: something else went wrong")
        return {"library": STANDIN, "T": args.get("T") or 298.15, "P": args.get("P") or 101325.0,
                "phase": args.get("phase") or "l", "TSource": "given" if args.get("T") is not None else thermo.LIBRARY_DEFAULT,
                "PSource": "given" if args.get("P") is not None else thermo.LIBRARY_DEFAULT,
                "massFractions": {n: 1.0 / len(names) for n in names}, "density": 1.5, "Cp": 2.5, "viscosity": None,
                "bubblePoint": 350.0, "dewPoint": 360.0, "vapourAtBubble": None,
                "units": {"density": "kg/m^3", "Cp": "J/g/K", "viscosity": "Pa*s", "T": "K", "P": "Pa",
                          "bubblePoint": "K", "dewPoint": "K"},
                "solved": {"kind": args["solve"]["kind"], "how": STANDIN} if args.get("solve") else None,
                "notes": ["viscosity: thermosteam could not compute it for this mixture (a test's words)"]}


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    _keep(_run())
    return tmp_path


@pytest.fixture()
def worker(monkeypatch):
    w = StandIn(refuse={"PHB"})
    monkeypatch.setattr(proforma, "call", w)
    return w


def _titres(*records):
    by = {r["id"]: r for r in records}
    return SimpleNamespace(records=list(records), records_by_id=by, record=by.get)


TITRE = {"id": "cl1-Q9-0000000a", "paperId": "Q9", "field": "ethanol_titre", "value": 80.0, "unit": "g L⁻¹",
         "provenance": "unverified", "status": "unverified"}
YIELD = {**TITRE, "id": "cl1-Q9-0000000b", "field": "ethanol_yield_substrate", "value": 0.4, "unit": "g g⁻¹"}


# ── the question names a mixture on file ────────────────────────────────


@pytest.mark.parametrize("req, kind", [
    (dict(artifactId=RUN_ID, streamId="beer"), "stream"),
    (dict(preset="ethanol-water-azeotrope"), "ethanol-water-azeotrope"),
    (dict(preset="beer-at-titre-of", recordId="r-1"), "beer-at-titre-of"),
    (dict(preset="beer-at-titre-of r-1"), "beer-at-titre-of"),
])
def test_a_question_names_a_stream_or_a_preset(req, kind):
    assert thermo.question(ThermoPropsRequest(**req))[0] == kind


@pytest.mark.parametrize("req, words", [
    (dict(), "name a run's stream"),
    (dict(artifactId=RUN_ID), "both"),
    (dict(artifactId=RUN_ID, streamId="beer", preset="ethanol-water-azeotrope"), "not both"),
    (dict(preset="beer-at-titre-of"), "names an ethanol titre record"),
    (dict(preset="ethanol-water-azeotrope", recordId="r-1"), "names no record"),
    (dict(preset="brine"), "there is no preset 'brine'"),
])
def test_a_question_that_names_nothing_on_file_is_refused_in_words(req, words):
    with pytest.raises(thermo.ThermoRefused, match=words):
        thermo.question(ThermoPropsRequest(**req))


# ── a run's stream ───────────────────────────────────────────────────────


def test_a_stream_is_read_from_the_run_and_its_answer_kept(store, worker):
    art = thermo.props(ThermoPropsRequest(artifactId=RUN_ID, streamId="beer"))
    [sent] = worker.calls
    # The worker is sent the row as the run's table holds it, and no number of ours.
    assert sent == {"T": 305.0, "P": 101325.0, "components": {"Ethanol": 10.0, "Water": 90.0}, "phase": "l"}
    assert art.tool == "thermo_props" and art.toolVersion.startswith("thermo props 1 · thermosteam ")
    named = {i.name: i for i in art.inputs}
    assert named["stream"].source.kind == "artifact" and named["stream"].source.id == RUN_ID
    assert named["flow Water"].value == 90.0 and named["flow Water"].unit == "kg/hr"
    assert named["library"].source.kind == "model" and named["library"].source.id.startswith("thermosteam@")
    o = thermo.output_of(art)
    assert o.kind == "stream" and o.subject == f"stream beer of run {RUN_ID}" and o.runArtifactId == RUN_ID
    assert o.density == 1.5 and o.library == STANDIN and o.TSource == "given"
    # The run is the answer's source: computed from a computed run is computed.
    assert art.provenance == "computed"
    # Asked again, the stored answer comes back and the worker is not asked.
    again = thermo.props(ThermoPropsRequest(artifactId=RUN_ID, streamId="beer"))
    assert again.id == art.id and len(worker.calls) == 1


def test_a_run_resting_on_an_assumption_makes_its_streams_answers_demo(store, worker):
    _keep(_run("bbbbbbbbbbbbbbb2", provenance="demo"))
    art = thermo.props(ThermoPropsRequest(artifactId="bbbbbbbbbbbbbbb2", streamId="beer"))
    assert art.provenance == "demo"


def test_stored_reads_without_asking_the_worker(store, worker):
    q = ThermoPropsRequest(artifactId=RUN_ID, streamId="beer")
    assert thermo.stored(q) is None and worker.calls == []
    art = thermo.props(q)
    assert thermo.stored(q).id == art.id and len(worker.calls) == 1


@pytest.mark.parametrize("req, err, words", [
    (dict(artifactId="cccccccccccccccc", streamId="beer"), thermo.ThermoNotFound, "no artifact 'cccccccccccccccc'"),
    (dict(artifactId=RUN_ID, streamId="broth"), thermo.ThermoNotFound, "has no stream 'broth'; its streams are beer, vent"),
    (dict(artifactId=RUN_ID, streamId="mixed"), thermo.ThermoRefused, "keeps no split by phase"),
    (dict(artifactId=RUN_ID, streamId="nothing"), thermo.ThermoRefused, "carries nothing"),
])
def test_a_stream_not_on_file_or_not_one_phase_is_refused_before_the_worker(store, worker, req, err, words):
    with pytest.raises(err, match=words):
        thermo.props(ThermoPropsRequest(**req))
    assert worker.calls == []


def test_an_artifact_that_is_no_run_has_no_stream_table(store, worker):
    _keep(_run("bbbbbbbbbbbbbbb3", tool="geneos.ceiling"))
    with pytest.raises(thermo.ThermoRefused, match="geneos.ceiling artifact, not a Proforma run"):
        thermo.props(ThermoPropsRequest(artifactId="bbbbbbbbbbbbbbb3", streamId="beer"))


def test_a_chemical_the_library_lacks_is_refused_in_words_and_nothing_is_kept(store, worker):
    _keep(Artifact.model_validate({**_run("bbbbbbbbbbbbbbb4").model_dump(), "output": {
        "streams": [_stream("cells", {"Water": 1.0, "PHB": 1.0})], "units": [], "tableUnits": {}}}))
    with pytest.raises(thermo.ThermoRefused, match="no chemical named PHB"):
        thermo.props(ThermoPropsRequest(artifactId="bbbbbbbbbbbbbbb4", streamId="cells"))
    assert [a.tool for a in artifacts.all_artifacts()].count("thermo_props") == 0


# ── the presets ──────────────────────────────────────────────────────────


def test_the_azeotrope_is_the_librarys_own_and_computed(store, worker):
    art = thermo.props(ThermoPropsRequest(preset="ethanol-water-azeotrope"))
    [sent] = worker.calls
    assert sent == {"T": None, "P": None, "components": {}, "solve": {"kind": "azeotrope", "light": "Ethanol", "heavy": "Water"}}
    assert {i.source.kind for i in art.inputs} == {"convention", "model"} and art.provenance == "computed"
    named = {i.name: i for i in art.inputs}
    assert named["T"].value == thermo.LIBRARY_DEFAULT and named["P"].value == thermo.LIBRARY_DEFAULT
    assert thermo.output_of(art).preset == "ethanol-water-azeotrope"


def test_a_beer_reads_the_records_titre_through_units_and_takes_its_provenance(store, worker):
    art = thermo.props(ThermoPropsRequest(preset="beer-at-titre-of", recordId=TITRE["id"]), pool=_titres(TITRE))
    [sent] = worker.calls
    # g L⁻¹ is kg m⁻³: the record's own value, through units.py.
    assert sent["solve"] == {"kind": "titre", "solute": "Ethanol", "solvent": "Water", "kgPerM3": 80.0}
    named = {i.name: i for i in art.inputs}
    assert named["titre"].source.kind == "record" and named["titre"].source.id == TITRE["id"] and named["titre"].value == 80.0
    assert art.provenance == "unverified"  # the weakest of computed and the record's own
    o = thermo.output_of(art)
    assert o.recordId == TITRE["id"] and thermo.BEER_LEAVES_OUT in o.notes


def test_a_beer_of_a_record_that_is_no_titre_or_not_on_file_is_refused(store, worker):
    with pytest.raises(thermo.ThermoRefused, match="not an ethanol titre"):
        thermo.props(ThermoPropsRequest(preset="beer-at-titre-of", recordId=YIELD["id"]), pool=_titres(YIELD))
    with pytest.raises(thermo.ThermoNotFound, match="no record 'r-gone'"):
        thermo.props(ThermoPropsRequest(preset="beer-at-titre-of", recordId="r-gone"), pool=_titres(TITRE))
    assert worker.calls == []


def test_a_worker_failure_that_is_no_refusal_stays_a_worker_error(store, monkeypatch):
    monkeypatch.setattr(proforma, "call", StandIn())
    _keep(Artifact.model_validate({**_run("bbbbbbbbbbbbbbb5").model_dump(), "output": {
        "streams": [_stream("odd", {"boom": 1.0})], "units": [], "tableUnits": {}}}))
    with pytest.raises(WorkerError, match="something else"):
        thermo.props(ThermoPropsRequest(artifactId="bbbbbbbbbbbbbbb5", streamId="odd"))


# ── evidence a claim may cite ────────────────────────────────────────────


def test_each_property_is_its_own_evidence_with_the_artifacts_basis(store, worker):
    art = thermo.props(ThermoPropsRequest(artifactId=RUN_ID, streamId="beer"))
    ev = thermo.evidence_of(art)
    # viscosity came back as None, so it is no evidence.
    assert [e.id for e in ev] == [f"{art.id}:{k}" for k in ("density", "Cp", "bubblePoint", "dewPoint")]
    assert all(e.basis.artifactId == art.id and e.provenance == art.provenance for e in ev)
    assert ev[0].unit == "kg/m^3" and ev[0].value == 1.5 and STANDIN in ev[0].label


# ── the tool ─────────────────────────────────────────────────────────────


def _tool(**fields):
    raw = {"artifactId": "", "streamId": "", "preset": "", "recordId": "", **fields}
    return tools.run("thermo_props", raw, tools.ToolContext(pool_factory=lambda: _titres(TITRE), include_archived=True))


def test_the_tool_is_a_loose_read_in_the_closed_registry_of_thirty():
    assert "thermo_props" in tools.WHITELIST and len(tools.WHITELIST) == 30
    assert tools.REGISTRY["thermo_props"].strict is False
    schema = next(t for t in tools.infos() if t.name == "thermo_props").inputSchema
    assert set(schema["properties"]) == {"artifactId", "streamId", "preset", "recordId"}
    assert all(p["type"] == "string" for p in schema["properties"].values())


def test_the_tool_refuses_a_number_and_answers_ids_with_citable_evidence(store, worker):
    assert "a number was typed" in tools.run("thermo_props", {"artifactId": "", "streamId": "", "preset": "", "recordId": 7}).error
    r = _tool(artifactId=RUN_ID, streamId="beer")
    assert r.error is None and r.summary["artifactId"] and r.summary["library"] == STANDIN
    assert [p["evidenceId"] for p in r.summary["properties"]] == [e.id for e in r.evidence]
    refused = _tool(preset="beer-at-titre-of", recordId=YIELD["id"])
    assert refused.error.startswith("thermo_props refused:") and refused.evidence == []


def test_a_claim_may_cite_the_answer_like_any_computed_value(store, worker):
    r = _tool(preset="beer-at-titre-of", recordId=TITRE["id"])
    seen = SeenSet()
    seen.add(r)
    density = r.evidence[0].id
    raw = [{"id": "c1", "text": "The beer at that titre is a little lighter than water.", "recordIds": [],
            "evidenceIds": [density], "passages": [], "moduleRefs": [], "support": "direct"},
           {"id": "c2", "text": "Its heat capacity is known.", "recordIds": [], "evidenceIds": ["0000000000000000:Cp"],
            "passages": [], "moduleRefs": [], "support": "direct"}]
    out = validate_plan(raw, seen, SimpleNamespace(record=lambda _id: None))
    assert [c.id for c in out.claims] == ["c1"] and out.claims[0].provenance == "unverified"
    assert out.rejected == 1 and "cites what no tool returned" in out.reasons[0]


def test_the_tool_refuses_an_archived_programs_run_with_the_switch_off(store, worker):
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    pha = Artifact.model_validate(next(a for a in kept if a["tool"] == "proforma.run"))
    _keep(pha)
    raw = {"artifactId": pha.id, "streamId": "sugar", "preset": "", "recordId": ""}
    off = tools.run("thermo_props", raw, tools.ToolContext(include_archived=False))
    assert "archived (hidden)" in off.error and "PHA" in off.error and worker.calls == []
    on = tools.run("thermo_props", raw, tools.ToolContext(include_archived=True))
    assert on.error is None and on.evidence


# ── the endpoints ────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_post_answers_get_reads_and_neither_takes_a_number(store, worker, client):
    q = {"artifactId": RUN_ID, "streamId": "beer"}
    assert client.get("/api/thermo/props", params=q).json() == {"artifact": None} and worker.calls == []
    made = client.post("/api/thermo/props", json=q)
    assert made.status_code == 200 and made.json()["tool"] == "thermo_props"
    ThermoProps.model_validate(made.json()["output"])
    kept = client.get("/api/thermo/props", params=q).json()["artifact"]
    assert kept["id"] == made.json()["id"] and len(worker.calls) == 1


@pytest.mark.parametrize("body, status, words", [
    ({"artifactId": "cccccccccccccccc", "streamId": "beer"}, 404, "no artifact"),
    ({"preset": "brine"}, 422, "no preset"),
    ({}, 422, "name a run's stream"),
])
def test_the_endpoints_say_what_is_not_on_file_and_what_cannot_be_asked(store, worker, client, body, status, words):
    for r in (client.post("/api/thermo/props", json=body), client.get("/api/thermo/props", params=body)):
        assert r.status_code == status and words in r.json()["detail"]


def test_a_chemical_the_library_lacks_is_a_422_and_a_dead_worker_a_503(store, worker, client, monkeypatch):
    _keep(Artifact.model_validate({**_run("bbbbbbbbbbbbbbb6").model_dump(), "output": {
        "streams": [_stream("cells", {"PHB": 1.0}), _stream("odd", {"boom": 1.0})], "units": [], "tableUnits": {}}}))
    r = client.post("/api/thermo/props", json={"artifactId": "bbbbbbbbbbbbbbb6", "streamId": "cells"})
    assert r.status_code == 422 and "no chemical named PHB" in r.json()["detail"]
    r = client.post("/api/thermo/props", json={"artifactId": "bbbbbbbbbbbbbbb6", "streamId": "odd"})
    assert r.status_code == 503 and "where thermosteam runs" in r.json()["detail"]


# ── the double's answers ─────────────────────────────────────────────────


def test_the_doubles_answers_are_the_stand_in_runs_streams_and_say_what_they_are():
    entries = json.loads((PROTOTYPE / "thermo-props.json").read_text(encoding="utf-8"))["response"]["entries"]
    train = json.loads((PROTOTYPE / "pureos-train.json").read_text(encoding="utf-8"))["response"]
    by = {(e["request"].get("artifactId"), e["request"].get("streamId")): e for e in entries}
    for s in train["streams"]:
        assert (train["artifactId"], s["id"]) in by, f"the double cannot answer for stream {s['id']} of the train"
    assert by[(train["artifactId"], "broth")]["status"] == 422 and "PHB" in by[(train["artifactId"], "broth")]["body"]["detail"]
    answered = [e["body"] for e in entries if e["status"] == 200]
    assert answered and all("STAND-IN" in ThermoProps.model_validate(a["output"]).library for a in answered)


def test_the_service_never_imports_thermosteam():
    code = ("import sys; from openferment_core import thermo, api; from openferment_core.tools import thermo as t; "
            "assert 'thermosteam' not in sys.modules and 'biosteam' not in sys.modules")
    r = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]


# ── the real worker (`pnpm test:sim`) ────────────────────────────────────


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


@pytest.mark.sim
def test_thermosteams_water_is_its_own_997(warm):
    # 997 kg/m^3 is the library's own value for liquid water at 298.15 K and
    # 101325 Pa, read from thermosteam for this check: the test asserts that
    # thermosteam agrees with itself within 1 %, through the worker.
    out = warm.call("thermo_props", {"components": {"Water": 1.0}, "T": 298.15, "P": 101325.0})
    assert out["density"] == pytest.approx(997.0, rel=0.01)
    assert out["units"]["density"] == "kg/m^3" and out["library"].startswith("thermosteam ")
    assert out["TSource"] == "given" and out["notes"] == []


@pytest.mark.sim
def test_an_ethanol_water_stream_boils_between_its_two_pure_chemicals(warm):
    water = warm.call("thermo_props", {"components": {"Water": 1.0}})
    ethanol = warm.call("thermo_props", {"components": {"Ethanol": 1.0}})
    mix = warm.call("thermo_props", {"components": {"Water": 0.9, "Ethanol": 0.1}})
    assert ethanol["bubblePoint"] < mix["bubblePoint"] < water["bubblePoint"]
    assert mix["bubblePoint"] <= mix["dewPoint"] and mix["TSource"] == "thermosteam's Stream default"


@pytest.mark.sim
def test_a_chemical_the_library_lacks_is_an_error_in_words(warm):
    with pytest.raises(WorkerError, match="Refused: thermosteam's chemical library has no chemical named Unobtainium"):
        warm.call("thermo_props", {"components": {"Water": 1.0, "Unobtainium": 1.0}})


@pytest.mark.sim
def test_the_presets_through_the_service(warm, monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    az = thermo.output_of(thermo.props(ThermoPropsRequest(preset="ethanol-water-azeotrope")))
    # At an azeotrope the liquid boils to a vapour of its own composition.
    assert az.bubblePoint == pytest.approx(az.dewPoint, abs=0.01)
    assert az.vapourAtBubble["Ethanol"] == pytest.approx(az.solved["moleFraction"], abs=1e-6)
    beer = thermo.output_of(thermo.props(ThermoPropsRequest(preset="beer-at-titre-of", recordId=TITRE["id"]),
                                         pool=_titres(TITRE)))
    # The solved fraction holds the record's titre at the mixture's own density.
    assert beer.massFractions["Ethanol"] * beer.density == pytest.approx(80.0, rel=1e-9)
