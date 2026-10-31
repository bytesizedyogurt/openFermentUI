"""thermosteam answers property questions (OF-BLD-019 §4.2, D9).

Offline, the Proforma worker is replaced by a STAND-IN that records what it
was asked and answers in the worker's shape with invented numbers, so these
tests check what the service sends and keeps, never what thermosteam says.
Marked `sim` (`pnpm test:sim`), the real worker answers: thermosteam's water,
an ethanol-water stream and a chemical it lacks. Nothing here reads a key or
the network.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma, thermo, tools
from openferment_core.models import Artifact, BasisInput, BasisSource, ThermoProps, ThermoPropsRequest, Volatility
from openferment_core.validate import SeenSet, validate_plan
from openferment_core.workers import WorkerError

CORE = Path(__file__).resolve().parent.parent
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
    from standins import plant_artifact

    plant_artifact(art)


class StandIn:
    """The worker's `thermo_props` op, in its shape, with invented numbers;
    `refuse` names chemicals to refuse as the worker refuses them."""

    def __init__(self, refuse=(), library=STANDIN):
        self.calls: list[dict] = []
        self.refuse, self.library = set(refuse), library

    def __call__(self, op, args):
        assert op == "thermo_props"
        self.calls.append(args)
        names = set(args.get("components") or {}) | ({"Water", "Ethanol"} if args.get("solve") else set())
        lacking = sorted(names & self.refuse)
        if lacking:
            raise WorkerError(f"Refused: thermosteam's chemical library has no chemical named {', '.join(lacking)}")
        if "boom" in names:
            raise WorkerError("RuntimeError: something else went wrong")
        return {"library": self.library, "T": args.get("T") or 298.15, "P": args.get("P") or 101325.0,
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
    w = StandIn(refuse={"Unobtainium"})
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


def test_a_run_resting_on_an_assumption_makes_its_streams_answers_assumed(store, worker):
    _keep(_run("bbbbbbbbbbbbbbb2", provenance="assumed"))
    art = thermo.props(ThermoPropsRequest(artifactId="bbbbbbbbbbbbbbb2", streamId="beer"))
    assert art.provenance == "assumed"


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


def test_a_stream_chemical_the_library_lacks_is_refused_in_words_and_nothing_is_kept(store, worker):
    _keep(Artifact.model_validate({**_run("bbbbbbbbbbbbbbb4").model_dump(), "output": {
        "streams": [_stream("cells", {"Water": 1.0, "Unobtainium": 1.0})], "units": [], "tableUnits": {}}}))
    with pytest.raises(thermo.ThermoRefused, match="no chemical named Unobtainium"):
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
    return tools.run("thermo_props", raw, tools.ToolContext(pool_factory=lambda: _titres(TITRE)))


def test_the_tool_is_a_loose_read_in_the_closed_registry():
    # The registry's count is test_tools.NAMES' (OF-BLD-019 §6.1); thermo_props
    # is the first name after the module pairs.
    assert tools.WHITELIST[tools.WHITELIST.index("home_write") + 1] == "thermo_props"
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
        "streams": [_stream("cells", {"Unobtainium": 1.0}), _stream("odd", {"boom": 1.0})], "units": [], "tableUnits": {}}}))
    r = client.post("/api/thermo/props", json={"artifactId": "bbbbbbbbbbbbbbb6", "streamId": "cells"})
    assert r.status_code == 422 and "no chemical named Unobtainium" in r.json()["detail"]
    r = client.post("/api/thermo/props", json={"artifactId": "bbbbbbbbbbbbbbb6", "streamId": "odd"})
    assert r.status_code == 503 and "where thermosteam runs" in r.json()["detail"]


def test_a_damaged_file_is_a_409_in_words_never_a_500(store, worker, client):
    """OF-BLD-019 §4.R: a run's file, or the answer's, that does not parse is
    said in words, as GET /api/biorepo/artifacts/{id} says it, and the card
    shows them; it was an unhandled 500 ('check its log')."""
    from standins import plant_damaged

    plant_damaged("bbbbbbbbbbbbbbb2")
    q = {"artifactId": "bbbbbbbbbbbbbbb2", "streamId": "beer"}
    for r in (client.get("/api/thermo/props", params=q), client.post("/api/thermo/props", json=q)):
        assert r.status_code == 409 and "bbbbbbbbbbbbbbb2 is damaged on disk" in r.json()["detail"], r.text
    # The run parses and the answer kept for its stream does not.
    asked = {"artifactId": RUN_ID, "streamId": "beer"}
    inputs, _ = thermo.basis_inputs(ThermoPropsRequest(**asked), None)
    reg = artifacts.registered(thermo.TOOL)
    answer = artifacts.artifact_id(reg.tool, reg.version, inputs)
    plant_damaged(answer)
    for r in (client.get("/api/thermo/props", params=asked), client.post("/api/thermo/props", json=asked)):
        assert r.status_code == 409 and f"{answer} is damaged on disk" in r.json()["detail"], r.text
    assert worker.calls == [], "nothing is asked of thermosteam over a damaged answer"



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


# ── a product's volatility (OF-BLD-020 §7.1, D12) ────────────────────────


class VolatilityStandIn:
    """The worker's `volatility` op, in its shape, with invented numbers;
    `refuse` names chemicals to refuse as the worker refuses them, and
    `none` the chemicals it answers with no azeotrope."""

    def __init__(self, refuse=(), none=(), library=STANDIN):
        self.calls: list[dict] = []
        self.refuse, self.none, self.library = set(refuse), set(none), library

    def __call__(self, op, args):
        assert op == "volatility"
        self.calls.append(args)
        if args["chemical"] in self.refuse:
            raise WorkerError(f"Refused: thermosteam's chemical library has no chemical named {args['chemical']}")
        if args["chemical"] == "boom":
            raise WorkerError("RuntimeError: something else went wrong")
        found = args["chemical"] not in self.none
        return {"library": self.library, "chemical": args["chemical"], "partner": args["partner"], "P": 101325.0,
                "PSource": thermo.LIBRARY_DEFAULT, "boilingPoint": 350.0, "partnerBoilingPoint": 370.0,
                "lighter": args["chemical"], "azeotrope": found, "azeotropeMoleFraction": 0.9 if found else None,
                "azeotropeMassFraction": 0.95 if found else None, "azeotropeT": 349.0 if found else None,
                "searched": {"of": args["chemical"], "from": 0.1, "to": 0.9, "points": 9, "halvings": 3},
                "units": {"boilingPoint": "K", "partnerBoilingPoint": "K", "azeotropeT": "K", "P": "Pa",
                          "azeotropeMoleFraction": "mol/mol", "azeotropeMassFraction": "kg/kg"},
                "how": STANDIN, "notes": [] if found else ["azeotrope: none found (a test's words)"]}


@pytest.fixture()
def vworker(monkeypatch):
    w = VolatilityStandIn(refuse={"Unobtainium"}, none={"Methanol"})
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(thermo, "CHEMICALS", {**thermo.CHEMICALS, "unobtainium-product": "Unobtainium",
                                              "methanol-product": "Methanol", "odd-product": "boom"})
    return w


def test_ethanols_volatility_asks_the_worker_by_the_librarys_name_and_is_kept(store, vworker):
    art = thermo.volatility("ethanol")
    [sent] = vworker.calls
    # The library's own names and nothing of ours: the pressure is the library's default.
    assert sent == {"chemical": "Ethanol", "partner": "Water", "P": None}
    assert art.tool == "volatility" and art.toolVersion.startswith("thermo volatility 1 · thermosteam ")
    named = {i.name: i for i in art.inputs}
    assert named["product"].value == "ethanol" and named["chemical"].value == "Ethanol"
    assert named["partner"].value == "Water" and named["P"].value == thermo.LIBRARY_DEFAULT
    assert named["azeotrope search"].value == thermo.AZEOTROPE_SEARCH and named["azeotrope search"].source.kind == "convention"
    assert named["library"].source.kind == "model" and named["library"].source.id.startswith("thermosteam@")
    assert {i.source.kind for i in art.inputs} == {"convention", "model"} and art.provenance == "computed"
    o = thermo.volatility_of(art)
    assert o.product == "ethanol" and o.azeotrope is True and o.library == STANDIN
    assert o.subject == "Ethanol (product ethanol) beside Water"
    # Asked again, the stored answer comes back and the worker is not asked.
    assert thermo.volatility("ethanol").id == art.id and len(vworker.calls) == 1
    assert thermo.stored_volatility("ethanol").id == art.id and len(vworker.calls) == 1


def test_stored_volatility_reads_without_asking_the_worker(store, vworker):
    assert thermo.stored_volatility("ethanol") is None and vworker.calls == []


@pytest.mark.parametrize("product, err, words", [
    ("phb", thermo.VolatilityMissing, "product 'phb' names no chemical of thermosteam's library here"),
    ("taq-dna-polymerase", thermo.VolatilityMissing, "ethanol → Ethanol"),
    ("", thermo.ThermoRefused, "names a product by its id"),
])
def test_a_product_with_no_library_name_is_missing_before_the_worker(store, vworker, product, err, words):
    with pytest.raises(err, match=words):
        thermo.volatility(product)
    with pytest.raises(err, match=words):
        thermo.stored_volatility(product)
    assert vworker.calls == [] and [a.tool for a in artifacts.all_artifacts()].count("volatility") == 0


def test_a_missing_volatility_is_a_not_found_and_a_refusal_is_not():
    assert issubclass(thermo.VolatilityMissing, thermo.ThermoNotFound)
    assert not issubclass(thermo.VolatilityMissing, thermo.ThermoRefused)


def test_a_product_chemical_the_library_lacks_is_refused_in_words_and_nothing_is_kept(store, vworker):
    with pytest.raises(thermo.ThermoRefused, match="no chemical named Unobtainium"):
        thermo.volatility("unobtainium-product")
    assert [a.tool for a in artifacts.all_artifacts()].count("volatility") == 0


def test_none_found_is_an_answer_and_says_the_grid_it_searched(store, vworker):
    o = thermo.volatility_of(thermo.volatility("methanol-product"))
    assert o.azeotrope is False and o.azeotropeMoleFraction is None and o.searched["of"] == "Methanol"
    assert any("none found" in n for n in o.notes)


def test_a_worker_failure_that_is_no_refusal_stays_a_worker_error_for_volatility(store, vworker):
    with pytest.raises(WorkerError, match="something else"):
        thermo.volatility("odd-product")


def test_each_volatility_property_is_its_own_evidence(store, vworker):
    found = thermo.volatility("ethanol")
    ev = {e.id.split(":")[1]: e for e in thermo.volatility_evidence(found)}
    assert list(ev) == [k for k, _ in thermo.VOLATILITY_PROPERTIES]
    assert ev["azeotrope"].value == "found" and ev["boilingPoint"].unit == "K" and ev["boilingPoint"].value == 350.0
    assert all(e.basis.artifactId == found.id and e.provenance == "computed" for e in ev.values())
    none = thermo.volatility_evidence(thermo.volatility("methanol-product"))
    assert [e.id.split(":")[1] for e in none] == ["boilingPoint", "azeotrope"] and none[1].value == "none found"
    # A label is words: the only digits are the library's version.
    assert all(not any(c.isdigit() for c in e.label.replace(STANDIN, "")) for e in ev.values())


def test_a_property_label_names_thermosteam_and_never_its_version(store, monkeypatch):
    """OF-BLD-020 §7.R, finding 33: the worker answers with the library's
    name and version (`thermosteam <v>`, as the real one does), and a label a
    claim may copy word for word holds no number: the version is the basis's
    `library` input, which every evidence carries."""
    from importlib.metadata import version

    from openferment_core.validate import find_number

    words = f"thermosteam {version('thermosteam')}"
    vol, props = VolatilityStandIn(none={"Methanol"}, library=words), StandIn(library=words)
    monkeypatch.setattr(proforma, "call", lambda op, args: (vol if op == "volatility" else props)(op, args))
    monkeypatch.setattr(thermo, "CHEMICALS", {**thermo.CHEMICALS, "methanol-product": "Methanol"})
    found, none = thermo.volatility("ethanol"), thermo.volatility("methanol-product")
    for e in thermo.volatility_evidence(found) + thermo.volatility_evidence(none):
        assert not any(ch.isdigit() for ch in e.label), e.label
        assert find_number(e.label) is None and e.label.endswith(", as thermosteam computes it"), e.label
        assert {i.name: i.value for i in e.basis.inputs}["library"] == words
    # thermo_props' evidence names the library the same way. (A run's stream
    # names its run by id, which this run's id holds as an identifier.)
    for req in (ThermoPropsRequest(preset="ethanol-water-azeotrope"), ThermoPropsRequest(artifactId=RUN_ID, streamId="beer")):
        for e in thermo.evidence_of(thermo.props(req)):
            assert find_number(e.label) is None and e.label.endswith(", as thermosteam computes it"), e.label
            assert version("thermosteam") not in e.label


def test_volatility_of_refuses_an_artifact_of_another_tool(store, worker):
    with pytest.raises(thermo.ThermoRefused, match="not a volatility answer"):
        thermo.volatility_of(thermo.props(ThermoPropsRequest(preset="ethanol-water-azeotrope")))


def test_the_volatility_endpoints_answer_read_and_say_what_is_missing(store, vworker, client, monkeypatch):
    assert client.get("/api/thermo/volatility", params={"product": "ethanol"}).json() == {"artifact": None}
    made = client.post("/api/thermo/volatility", json={"product": "ethanol"})
    assert made.status_code == 200 and made.json()["tool"] == "volatility"
    Volatility.model_validate(made.json()["output"])
    assert client.get("/api/thermo/volatility", params={"product": "ethanol"}).json()["artifact"]["id"] == made.json()["id"]
    for r in (client.post("/api/thermo/volatility", json={"product": "phb"}),
              client.get("/api/thermo/volatility", params={"product": "phb"})):
        assert r.status_code == 404 and "names no chemical" in r.json()["detail"]
    r = client.post("/api/thermo/volatility", json={"product": "unobtainium-product"})
    assert r.status_code == 422 and "no chemical named Unobtainium" in r.json()["detail"]
    r = client.post("/api/thermo/volatility", json={"product": "odd-product"})
    assert r.status_code == 503 and "where thermosteam runs" in r.json()["detail"]
    # A product by id, and nothing else: a number or a chemical name is refused.
    assert client.post("/api/thermo/volatility", json={"product": "ethanol", "P": 5}).status_code == 422
    assert client.post("/api/thermo/volatility", json={"product": "ethanol", "chemical": "Ethanol"}).status_code == 422
    assert len(vworker.calls) == 3


def test_a_damaged_volatility_is_a_409_in_words(store, vworker, client):
    from standins import plant_damaged

    art = thermo.volatility("ethanol")
    plant_damaged(art.id)
    for r in (client.get("/api/thermo/volatility", params={"product": "ethanol"}),
              client.post("/api/thermo/volatility", json={"product": "ethanol"})):
        assert r.status_code == 409 and f"{art.id} is damaged on disk" in r.json()["detail"], r.text


@pytest.mark.sim
def test_ethanols_volatility_finds_the_azeotrope_and_names_the_librarys_tb(warm, monkeypatch, tmp_path):
    import thermosteam as tmo  # read here only to hold the worker's answer to the library's own

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    art = thermo.volatility("ethanol")
    o = thermo.volatility_of(art)
    assert o.boilingPoint == tmo.Chemical("Ethanol").Tb and o.partnerBoilingPoint == tmo.Chemical("Water").Tb
    assert o.lighter == "Ethanol" and o.azeotrope is True and o.library == f"thermosteam {tmo.__version__}"
    # Minimum-boiling: the azeotrope boils below both pure chemicals.
    assert o.azeotropeT < o.boilingPoint and o.azeotropeT < o.partnerBoilingPoint
    # The same search the preset runs, on the same pair, finds the same liquid.
    az = thermo.output_of(thermo.props(ThermoPropsRequest(preset="ethanol-water-azeotrope")))
    assert o.azeotropeMoleFraction == az.solved["moleFraction"]
    assert o.azeotropeMassFraction == pytest.approx(az.massFractions["Ethanol"], rel=1e-12)
    assert art.provenance == "computed" and o.searched["of"] == "Ethanol" and o.notes == []
    # A label a claim may copy holds no number: the library is named, its version is in the basis (§7.R).
    from openferment_core.validate import find_number

    assert all(find_number(e.label) is None for e in thermo.volatility_evidence(art))


@pytest.mark.sim
def test_a_pair_with_no_azeotrope_says_so_with_the_grid_searched(warm):
    # Methanol and water: the library's own equilibrium finds none, and says
    # on which grid it looked.
    out = warm.call("volatility", {"chemical": "Methanol", "partner": "Water"})
    assert out["azeotrope"] is False and out["azeotropeMoleFraction"] is None and out["lighter"] == "Methanol"
    assert out["searched"]["of"] == "Methanol" and out["searched"]["points"] > 0
    assert any("none found" in n for n in out["notes"])


@pytest.mark.sim
def test_a_products_chemical_the_library_lacks_is_refused_in_words(warm, monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(thermo, "CHEMICALS", {**thermo.CHEMICALS, "made-up": "Unobtainium"})
    with pytest.raises(thermo.ThermoRefused, match="no chemical named Unobtainium"):
        thermo.volatility("made-up")
    with pytest.raises(thermo.VolatilityMissing, match="names no chemical"):
        thermo.volatility("phb")
