"""pureOS's unit catalogue (OF-BLD-020 §5.1, D8, E.3‴, Appendix 2 §B).

Offline: the catalogue is data the service serves without BioSTEAM; every
entry names a class BioSTEAM's source (or the in-house module's) defines,
its id is a vocabulary step, every spec has a bounds reason, the listing
starts no worker, the specs endpoint serves the worker's reading and says
404 and 503 in words, the `pureos-unit` scope serves defaults and waits for
what a class requires, and templates expand per component and per effect.

Marked `sim` (`pnpm test:sim`, the real Proforma worker): each class is read
both ways (every constructor parameter is a spec's or named as not offered,
and every spec is a parameter the class takes), each default is the one the
class gives, and each unit type is built alone on a stand-in stream and
converges.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

import ast
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, params, proforma
from openferment_core.models import Override, ParameterSpec, ParamResolveRequest, UnitSpecs, UnitType
from openferment_core.pureos import catalogue
from openferment_core.validate import unit_operations
from test_pureos import _biosteam_unit_classes

CORE = Path(__file__).resolve().parent.parent
PKG = CORE / "openferment_core"
BY = "openFerment test fixture"
AT = "2026-10-21"
STANDIN = "STAND-IN for this test: an assumption typed to exercise the code, not a result"


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


class StandInWorker:
    """Answers `catalogue_specs` as the worker's JSON contract does, every
    default and choice a STAND-IN (the class's own name for each parameter
    as the entry declares it), and fails any other op."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, op, args):
        self.calls.append((op, args))
        if op != "catalogue_specs":
            raise AssertionError(f"the stand-in worker has no op {op}")
        e = catalogue.entry(args["type"])
        defaults = {p.key: {"value": (None if p.per or p.how or "library-default" not in p.rule else
                                      ("standin-word" if p.choices is not None else 0.5)), "from": STANDIN}
                    for p in e.params}
        choices = {p.key: ["standin-word", "another-standin-word"] for p in e.params if p.choices is not None}
        refuses = {"N": {"atOrBelow": 1.0, "from": STANDIN}} if any(p.key == "N" for p in e.params) else {}
        return {"type": e.id, "unitClass": e.cls, "module": "standin", "signature": {}, "constructor": {},
                "attributes": {}, "defaults": defaults, "choices": choices, "refuses": refuses,
                "chemicals": ["Water", "Ethanol", "Yeast"], "versions": {"biosteam": "0.0-standin"}}


@pytest.fixture()
def worker(monkeypatch):
    w = StandInWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    return w


@pytest.fixture()
def no_worker(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("the catalogue's listing started the simulator")

    monkeypatch.setattr(proforma, "call", refuse)
    monkeypatch.setattr(catalogue, "_SPECS", {})


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


# ── the catalogue is data (offline) ────────────────────────────────────


def _inhouse_classes() -> set[str]:
    """The in-house module's classes that subclass `bst.Unit`, read as text."""
    tree = ast.parse((PKG / "pureos" / "inhouse.py").read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)
            and any(isinstance(b, ast.Attribute) and b.attr == "Unit" and getattr(b.value, "id", "") == "bst"
                    for b in n.bases)}


def _biosteam_exported() -> set[str]:
    """Every name a module of BioSTEAM's units package exports (`__all__`),
    read as text: what `bst.<name>` reaches."""
    import importlib.util
    import warnings

    spec = importlib.util.find_spec("biosteam")
    if spec is None or not spec.submodule_search_locations:
        pytest.skip("BioSTEAM is not installed here (the sim extra)")
    names: set[str] = set()
    for path in (Path(list(spec.submodule_search_locations)[0]) / "units").rglob("*.py"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(path.read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets):
                try:
                    names |= set(ast.literal_eval(n.value))
                except ValueError:
                    continue
    return names


def test_every_entry_names_a_class_its_source_defines():
    """A BioSTEAM entry names a class BioSTEAM's units package defines and
    exports; an in-house one a `bst.Unit` subclass of pureos/inhouse.py;
    never both. Read as text: no BioSTEAM is imported."""
    defined, exported, inhouse = _biosteam_unit_classes(), _biosteam_exported(), _inhouse_classes()
    assert inhouse == {"Ultrafiltration", "CellDisruption", "Chromatography"}
    for e in catalogue.UNIT_TYPES:
        assert bool(e.biosteam) != bool(e.inhouse), e.id
        if e.biosteam:
            assert e.biosteam in defined and e.biosteam in exported, e.id
        else:
            assert e.inhouse in inhouse, e.id
    for cls in catalogue.LEFT_OUT:
        assert cls in defined and cls not in {e.biosteam for e in catalogue.UNIT_TYPES}


def test_ids_are_vocabulary_steps_and_every_spec_has_a_bounds_reason():
    steps = {o["id"]: o for o in unit_operations()}
    ids = [e.id for e in catalogue.UNIT_TYPES]
    assert len(ids) == len(set(ids)) == len(catalogue.BY_ID)
    for e in catalogue.UNIT_TYPES:
        assert e.id in steps, f"{e.id} is not a vocabulary step"
        if e.biosteam:
            assert e.biosteam in steps[e.id]["biosteamClasses"], e.id
        assert set(e.maps) <= set(steps), e.id
        assert e.stage in catalogue.STAGES, e.id
        specs = catalogue.static_specs(e)
        keys = [s.key for s in specs]
        assert len(keys) == len(set(keys)) == len(e.params), e.id
        for s in specs:
            assert s.boundsReason.strip(), (e.id, s.key)
            ParameterSpec.model_validate(s.model_dump())
        for alts, _ in e.needs:
            assert {k for alt in alts for k in alt} <= set(keys), e.id
        ports = catalogue.unit_type(e).insOuts
        assert ports[0].side == "in" and ports[0].index == 0 and ports[0].source == "upstream", e.id
        assert sum(p.onward for p in ports if p.side == "out") == 1, f"{e.id} names no one outlet the product goes on by"
        assert {p.via for p in e.params} <= {"argument", "attribute"}
    for _, (step, why) in catalogue.LEFT_OUT.items():
        assert step in steps and step not in catalogue.BY_ID and why.strip()


def test_the_in_house_entries_say_no_cost_model_and_the_column_says_cadet_replaces_it():
    for tid in ("uf-df", "cell-disruption", "chromatography"):
        e = catalogue.entry(tid)
        assert not e.cost_model and any("No cost model" in n for n in e.notes), tid
        assert all("library-default" not in p.rule or "None" in (p.note or "") for p in e.params), tid
    assert any("CADET replaces this" in n for n in catalogue.entry("chromatography").notes)
    modes = {p.key: p for p in catalogue.entry("chromatography").params}["mode"]
    assert modes.choices == catalogue.MODES == tuple(catalogue.MODE_VOCABULARY)
    assert set(catalogue.entry("chromatography").maps) == set(catalogue.MODE_VOCABULARY.values())
    assert set(catalogue.entry("cell-disruption").maps) == {"homogenisation", "bead-mill"}


def test_the_listing_is_served_from_data_and_starts_no_worker(no_worker, client):
    r = client.get("/api/pureos/catalogue")
    assert r.status_code == 200
    body = r.json()
    assert [u["id"] for u in body] == [u.id for u in catalogue.listing()]
    assert {u["id"] for u in body} == set(catalogue.BY_ID)
    order = [catalogue.STAGES.index(u["stage"]) for u in body]
    assert order == sorted(order)
    for u in body:
        assert set(u) == set(UnitType.model_fields)
        assert u["specCount"] == len(catalogue.entry(u["id"]).params)
    assert {u["id"]: u["costModel"] for u in body}["chromatography"] is False


def test_an_unknown_type_is_a_404_and_a_worker_that_cannot_answer_a_503(client, monkeypatch):
    from openferment_core.workers import WorkerError

    r = client.get("/api/pureos/catalogue/nonesuch/specs")
    assert r.status_code == 404 and "there is no unit type 'nonesuch' in pureOS's catalogue" in r.json()["detail"]

    def down(op, args):
        raise WorkerError("the Proforma simulator could not start: STAND-IN")

    monkeypatch.setattr(proforma, "call", down)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    r = client.get("/api/pureos/catalogue/tank/specs")
    assert r.status_code == 503 and "could not read tank's class" in r.json()["detail"]


def test_the_specs_endpoint_serves_the_workers_reading(worker, client):
    r = client.get("/api/pureos/catalogue/crystallisation/specs")
    assert r.status_code == 200
    got = UnitSpecs.model_validate(r.json())
    e = catalogue.entry("crystallisation")
    assert got.biosteamClass == "BatchCrystallizer" and got.inhouseClass is None
    assert [s.key for s in got.specs] == [p.key for p in e.params] == [d.key for d in got.defaults]
    by = {s.key: s for s in got.specs}
    # The class's own refusal raises the declared bound, with its words.
    assert by["N"].min == 2 and "refuses" in by["N"].boundsReason
    assert by["tau"].min == 0
    defaults = {d.key: d for d in got.defaults}
    assert defaults["T"].value == 0.5 and defaults["T"].readFrom == STANDIN and defaults["tau"].value is None
    assert {m.key: m.via for m in got.params}["tau_0"] == "attribute"
    assert {n.name for n in got.notOffered} == {"vessel_material"}
    assert got.chemicals == ["Water", "Ethanol", "Yeast"] and got.versions == {"biosteam": "0.0-standin"}
    # Read once a process: a second ask starts nothing.
    client.get("/api/pureos/catalogue/crystallisation/specs")
    assert [op for op, _ in worker.calls] == ["catalogue_specs"]
    tank = UnitSpecs.model_validate(client.get("/api/pureos/catalogue/tank/specs").json())
    assert {s.key: s.choices for s in tank.specs}["vessel_type"] == ["standin-word", "another-standin-word"]


def override(key, value, scope="pureos:unit:t1:u1"):
    return Override(scope=scope, key=key, value=value, by=BY, at=AT, note=STANDIN)


def test_the_unit_scope_serves_defaults_and_waits_for_what_the_class_requires(worker, client):
    base = "/api/params/pureos:unit:t1:u1"
    r = client.get(base)
    assert r.status_code == 404 and "pureOS's train units" in r.json()["detail"] and "unitType" in r.json()["detail"]
    r = client.get(base, params={"unitType": "nonesuch"})
    assert r.status_code == 422 and "no unit type 'nonesuch'" in r.json()["detail"]
    r = client.get(base, params={"unitType": "centrifugation"})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "pureos-unit" and body["title"].startswith("Unit u1 of train t1: Solids centrifuge")
    assert body["waiting"] == ["split"]
    values = {v["key"]: v for v in body["values"]}
    assert values["moisture_content"]["origin"] == "library-default" and values["moisture_content"]["value"] == 0.5
    assert values["moisture_content"]["libraryDefault"] == 0.5
    assert "a record of step_recovery" in values["split"]["detail"]
    assert any("Needs split" in n for n in body["notes"]) and any("Not offered: solids" in n for n in body["notes"])
    # A person's value is their assumption, named in what a run would add.
    r = client.post(f"{base}/resolve", json={"unitType": "centrifugation",
                                             "overrides": [override("moisture_content", 0.25).model_dump()]})
    assert r.status_code == 200
    got = {v["key"]: v for v in r.json()["values"]}
    assert got["moisture_content"]["origin"] == "assumption" and got["moisture_content"]["overriddenBy"] == BY
    assert [b["name"] for b in r.json()["basisInputs"]] == ["moisture_content"]
    assert r.json()["basisInputs"][0]["source"]["kind"] == "assumption"
    # A template is set per component on a train's unit, never as itself.
    r = client.post(f"{base}/resolve", json={"unitType": "centrifugation", "overrides": [override("split", 0.5).model_dump()]})
    assert r.status_code == 422 and "split.<component>" in r.json()["detail"]
    # An in-house unit's required parameters wait for a record or a person;
    # an optional one reads as the class's own reading of None.
    inh = {v["key"]: v for v in client.get(base, params={"unitType": "uf-df"}).json()["values"]}
    assert inh["concentration_factor"]["origin"] == "waiting" and inh["sieving_coefficient"]["origin"] == "waiting"
    assert inh["diavolumes"]["origin"] == "library-default"
    assert inh["diavolumes"]["source"]["id"] == "openferment.pureos.inhouse"


def test_templates_expand_per_component_and_per_effect():
    chems = ["Water", "Ethanol", "Yeast"]
    keys = [s.key for s in catalogue.expand("centrifugation", catalogue.static_specs(catalogue.entry("centrifugation")),
                                            chems)]
    assert keys == ["split.Water", "split.Ethanol", "split.Yeast", "moisture_content", "centrifuge_type"]
    uf = [s.key for s in catalogue.expand("uf-df", catalogue.static_specs(catalogue.entry("uf-df")), chems)]
    assert uf[:2] == ["sieving_coefficient.Ethanol", "sieving_coefficient.Yeast"], "water is the solvent"
    ev = catalogue.expand("evaporation", catalogue.static_specs(catalogue.entry("evaporation")), chems, effects=3)
    assert [s.key for s in ev] == ["effects", "P.1", "P.2", "P.3", "V", "V_definition", "flash"]
    assert {s.key: s.label for s in ev}["P.2"] == "Pressure of an effect, effect 2"
    assert all(s.boundsReason for s in ev)


def test_what_a_unit_needs_is_said_until_it_is_set():
    # Every number below is a STAND-IN, an assumption of this test.
    assert catalogue.unmet("flash", {"P": 1.0}) == [
        "Flash drum waits for Pressure and Temperature or Pressure and Vapour fraction or Pressure and Duty or "
        "Temperature and Vapour fraction or Temperature and Duty or Vapour fraction and Duty: BioSTEAM sets a flash by "
        "exactly two of pressure, temperature, vapour fraction and duty"]
    assert catalogue.unmet("flash", {"P": 1.0, "V": 0.5}) == []
    assert len(catalogue.unmet("evaporation", {"effects": 2, "P.1": 1.0})) == 2
    assert len(catalogue.unmet("evaporation", {"effects": 2, "P.1": 1.0, "P.2": 1.0})) == 1
    assert catalogue.unmet("splitter", {"split.Water": 0.5}) == []
    assert catalogue.unmet("crystallisation", {"tau": 1.0, "V": 2.0}) == []
    assert "Batch time" in catalogue.unmet("crystallisation", {"N": 3.0})[0]


def test_a_units_values_become_the_classs_own_arguments():
    # Every number below is a STAND-IN, an assumption of this test.
    kw, attrs = catalogue.kwargs_of("distillation", {"light_key": "Ethanol", "heavy_key": "Water", "k": 1.5,
                                                     "is_divided": "true", "P": None, "y_top": 0.5})
    assert kw == {"LHK": ["Ethanol", "Water"], "k": 1.5, "y_top": 0.5, "is_divided": True} and attrs == {}
    kw, _ = catalogue.kwargs_of("evaporation", {"effects": 2.0, "P.1": 3.0, "P.2": 2.0, "V": 0.5})
    assert kw == {"P": [3.0, 2.0], "V": 0.5}
    kw, attrs = catalogue.kwargs_of("crystallisation", {"tau": 4.0, "N": 3.0, "tau_0": 2.0})
    assert kw == {"tau": 4.0, "N": 3} and isinstance(kw["N"], int) and attrs == {"tau_0": 2.0}
    kw, _ = catalogue.kwargs_of("centrifugation", {"split.Yeast": 0.5, "split.Water": 0.25})
    assert kw == {"split": {"Yeast": 0.5, "Water": 0.25}}
    with pytest.raises(ValueError, match="only under the model 'partition coefficients'"):
        catalogue.kwargs_of("lle", {"partition_coefficient.Ethanol": 2.0})
    kw, _ = catalogue.kwargs_of("lle", {"model": "partition coefficients", "partition_coefficient.Ethanol": 2.0})
    assert kw["settler_data"] == {"partition_IDs": ["Ethanol"], "partition_coefficients": [2.0]}
    kw, _ = catalogue.kwargs_of("lle-multistage", {"N_stages": 2.0, "partition_coefficient.Ethanol": 2.0})
    assert kw == {"N_stages": 2, "partition_data": {"IDs": ["Ethanol"], "K": [2.0]}}
    kw, _ = catalogue.kwargs_of("chromatography", {"product_ID": "Ethanol", "mode": "iex"})
    assert kw == {"mode": "iex", "product_ID": "Ethanol"}


def test_the_catalogue_and_its_units_hold_no_number_but_structural_ones():
    """Rule 1: no process number in catalogue.py or inhouse.py; every literal
    is 0 or 1, the named structural PAIR, or an in-house unit's count of
    inlets and outlets."""
    for name, allowed_targets in (("catalogue.py", {"PAIR"}), ("inhouse.py", {"_N_ins", "_N_outs"})):
        tree = ast.parse((PKG / "pureos" / name).read_text(encoding="utf-8"))
        allowed = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in allowed_targets
                                                    for t in node.targets):
                allowed |= {id(n) for n in ast.walk(node)}
        odd = [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
               and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
               and n.value not in (0, 1) and id(n) not in allowed]
        assert odd == [], f"numbers in pureos/{name}: {odd}"


def test_the_guards_reading_names_every_entry_and_what_was_left_out(capsys):
    assert catalogue.main(["--ids"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in rows if not r.get("leftOut")] == list(catalogue.BY_ID)
    assert [r for r in rows if r.get("leftOut")] == [{"id": "adsorption", "leftOut": "SingleComponentAdsorptionColumn"}]
    assert catalogue.main(["--nonesuch"]) == 1


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


@pytest.fixture()
def real(monkeypatch, tmp_path, warm):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.mark.sim
@pytest.mark.parametrize("type_id", catalogue.ids())
def test_the_worker_reads_each_class_both_ways(real, type_id):
    """Every parameter the class's constructor takes is a spec of the entry
    or named as not offered, and nothing else is; every spec is a parameter
    the class takes or an attribute it reads; every choice is listed from
    BioSTEAM; and each default is the signature's, or the class attribute or
    literal its `_init` reads in place of an empty one, named."""
    e = catalogue.entry(type_id)
    ws = catalogue.worker_specs(type_id)
    named = {p.bst for p in e.params if p.via == "argument"}
    left = {n for n, _ in e.not_offered}
    assert set(ws["constructor"]) == named | left, (set(ws["constructor"]) ^ (named | left))
    attrs = {p.bst for p in e.params if p.via == "attribute"}
    assert attrs <= set(ws["attributes"]) and all(ws["attributes"][a]["value"] is not None for a in attrs)
    for p in e.params:
        if p.choices is not None:
            assert ws["choices"][p.key], (type_id, p.key)
        if p.per or p.how or p.via == "attribute":
            continue
        d = ws["defaults"][p.key]
        if "signature" in d["from"]:
            assert d["value"] == ws["signature"][p.bst], (type_id, p.key)
        else:
            assert d["value"] is not None and ("_default" in d["from"] or "in place of None" in d["from"]), (type_id, d)
    served = catalogue.specs_of(type_id)
    json.dumps(served.model_dump(mode="json"), allow_nan=False)
    assert [s.key for s in served.specs] == [p.key for p in e.params]


# The stand-in inlets (kg/hr by chemical, on the yeast program's chemicals)
# and the stand-in values for what each class requires: every one an
# assumption of this test, none a result.
BROTH = {"flows": {"Water": 900, "Ethanol": 50, "Glucose": 5, "Yeast": 10}, "T": 305}
SOLVENT = {"flows": {"Octane": 500}}
FILLED = {}  # an inlet the unit sizes itself
STAND_INS: dict[str, tuple[list[dict], dict]] = {
    "centrifugation": ([BROTH], {"split.Yeast": 0.9, "split.Ethanol": 0.05}),
    "pressure-filtration": ([BROTH], {}),
    "rotary-vacuum-filtration": ([BROTH], {"split.Yeast": 0.9, "split.Ethanol": 0.05}),
    "clarifier": ([BROTH], {"split.Water": 0.9, "split.Ethanol": 0.9, "split.Glucose": 0.9}),
    "flash": ([BROTH], {"P": 101325.0, "V": 0.1}),
    "distillation": ([BROTH], {"light_key": "Ethanol", "heavy_key": "Water", "k": 1.2, "y_top": 0.5, "x_bot": 0.001}),
    "distillation-shortcut": ([BROTH], {"light_key": "Ethanol", "heavy_key": "Water", "k": 1.2, "y_top": 0.5,
                                        "x_bot": 0.001}),
    "evaporation": ([BROTH], {"effects": 2.0, "P.1": 101325.0, "P.2": 50000.0, "V": 0.1}),
    "uf-df": ([BROTH, FILLED], {"sieving_coefficient.Ethanol": 1.0, "sieving_coefficient.Glucose": 0.9,
                                "sieving_coefficient.Yeast": 0.0, "concentration_factor": 5.0, "diavolumes": 2.0,
                                "flux": 50.0}),
    "cell-disruption": ([{"byPhase": {"l": {"Water": 900, "Ethanol": 40}, "s": {"Yeast": 10, "Ethanol": 10}},
                          "T": 305}], {"product_ID": "Ethanol", "release": 0.5, "passes": 2.0}),
    "lle": ([BROTH, SOLVENT], {}),
    "lle-multistage": ([BROTH, SOLVENT], {"N_stages": 2.0}),
    "chromatography": ([BROTH, FILLED], {"mode": "iex", "product_ID": "Ethanol", "recovery": 0.9, "purity": 0.8,
                                         "binding_capacity": 40.0, "elution_volumes": 5.0}),
    "molecular-sieve": ([BROTH], {"split.Ethanol": 0.9, "split.Water": 0.1}),
    "crystallisation": ([BROTH], {"tau": 10.0, "N": 3.0}),
    "spray-dry": ([BROTH], {}),
    "drying-drum": ([BROTH, FILLED, FILLED], {"split.Water": 0.5, "split.Ethanol": 1.0}),
    "heat-exchange": ([BROTH], {"T": 320.0}),
    "tank": ([BROTH], {}),
    "mix-tank": ([BROTH, BROTH], {}),
    "pump": ([BROTH], {}),
    "mixer": ([BROTH, BROTH], {}),
    "splitter": ([BROTH], {"split.Water": 0.5, "split.Ethanol": 0.5}),
}


def test_every_unit_type_has_its_stand_ins():
    assert set(STAND_INS) == set(catalogue.BY_ID)


def _as_assumptions(type_id: str, values: dict) -> dict:
    """The stand-ins laid on the unit's expanded specs as a person's values
    (`params.resolve`), each an assumption by the fixture's name: what goes
    to the worker is what the resolve kept."""
    got = catalogue.provided(type_id)
    chems = catalogue.worker_specs(type_id)["chemicals"]
    effects = values.get("effects")
    specs = catalogue.expand(type_id, got.specs, chems, effects=int(effects) if effects else None)
    scope = f"pureos:unit:standin:{type_id}"
    resolved = params.resolve(specs, got.sources, [Override(scope=scope, key=k, value=v, by=BY, at=AT, note=STANDIN)
                                                   for k, v in values.items()])
    typed = {v.key: v for v in resolved if v.overriddenBy}
    assert set(typed) == set(values) and all(v.origin == "assumption" and v.overriddenBy == BY for v in typed.values())
    return {k: v.value for k, v in typed.items()}


@pytest.mark.sim
@pytest.mark.parametrize("type_id", catalogue.ids())
def test_each_unit_type_builds_alone_on_a_stand_in_stream_and_converges(real, type_id):
    """Built alone in the worker on its own defaults plus the stand-ins for
    what it requires, each unit type simulates, keeps its mass balance, and
    holds the defaults the catalogue read from its class."""
    e = catalogue.entry(type_id)
    ins, stand_ins = STAND_INS[type_id]
    values = _as_assumptions(type_id, stand_ins)
    assert catalogue.unmet(type_id, values) == []
    hold = [p.bst for p in e.params if not p.per and not p.how]
    r = proforma.call("catalogue_unit_check", {"type": type_id, "ins": ins, "values": values, "hold": hold})
    assert r["unitClass"] == e.cls
    assert len(r["outs"]) == len([p for p in e.ports if p.side == "out"])
    flows = [m for s in r["ins"] + r["outs"] for m in s["massFlows"].values()]
    assert all(math.isfinite(m) and m >= 0 for m in flows)
    mass_in, mass_out = (sum(s["massFlow"] for s in r[k]) for k in ("ins", "outs"))
    if type_id == "drying-drum":
        # BioSTEAM's DrumDryer burns its fuel to CO2 and water without taking
        # the oxygen from its gas (read from its _run, measured here): its
        # outlets carry that oxygen's mass beyond its inlets, and no more.
        fuel, emissions = r["ins"][2]["massFlow"], r["outs"][2]["massFlow"]
        assert mass_out - mass_in == pytest.approx(emissions - fuel, rel=1e-6) and emissions > fuel > 0
    else:
        assert mass_out == pytest.approx(mass_in, rel=1e-9)
    if e.inhouse or e.biosteam in ("Mixer", "Splitter"):
        assert r["purchaseCost"] == 0 and r["installedCost"] == 0
    else:
        assert r["installedCost"] > 0
    ws = catalogue.worker_specs(type_id)
    for p in e.params:
        if p.per or p.how or "library-default" not in p.rule or p.key in stand_ins:
            continue
        read, held = ws["defaults"][p.key]["value"], r["held"][p.bst]
        if read is None or (isinstance(held, str) and held.startswith("unreadable")):
            continue  # the class decides at run time, or keeps it under no public name
        assert held == read, (type_id, p.key, read, held)


@pytest.mark.sim
def test_the_in_house_units_balance_as_their_equations_say(real):
    """Each in-house unit's balance, on its STAND-IN values, against its
    equation in pureos/inhouse.py."""
    def call(tid):
        ins, values = STAND_INS[tid]
        return proforma.call("catalogue_unit_check", {"type": tid, "ins": ins, "values": values, "hold": []}), values

    r, v = call("cell-disruption")
    share = 1 - (1 - v["release"]) ** v["passes"]
    assert r["design"]["Share released"] == pytest.approx(share)
    assert r["design"]["Product released"] == pytest.approx(share * 10, rel=1e-9)  # the stand-in's held ethanol
    r, v = call("uf-df")
    feed, buffer = r["ins"]
    retentate, permeate = r["outs"]
    cf, n = v["concentration_factor"], v["diavolumes"]
    for chem in ("Ethanol", "Glucose", "Yeast"):
        s = v[f"sieving_coefficient.{chem}"]
        kept = retentate["massFlows"].get(chem, 0.0)
        assert kept == pytest.approx(feed["massFlows"][chem] * cf ** (-s) * math.exp(-n * s), rel=1e-9, abs=1e-12)
    assert retentate["massFlows"]["Water"] == pytest.approx(feed["massFlows"]["Water"] / cf, rel=1e-9)
    assert buffer["massFlows"]["Water"] == pytest.approx(n * feed["massFlows"]["Water"] / cf, rel=1e-9)
    assert r["design"]["Membrane area"] > 0
    r, v = call("chromatography")
    load, buffer = r["ins"]
    eluate, _ = r["outs"]
    product = load["massFlows"]["Ethanol"]
    assert eluate["massFlows"]["Ethanol"] == pytest.approx(v["recovery"] * product, rel=1e-9)
    assert r["design"]["Eluate purity"] == pytest.approx(v["purity"], rel=1e-9)
    assert r["design"]["Bed volume per hour of loading"] == pytest.approx(product / v["binding_capacity"], rel=1e-9)
    assert r["design"]["Elution buffer"] == pytest.approx(v["elution_volumes"] * product / v["binding_capacity"],
                                                          rel=1e-6)
    assert eluate["massFlows"]["Water"] == pytest.approx(buffer["massFlows"]["Water"], rel=1e-9)


@pytest.mark.sim
def test_the_real_unit_scope_serves_biosteams_defaults(real):
    s = params.scope("pureos:unit:t1:u1", ParamResolveRequest(unitType="tank"))
    ws = catalogue.worker_specs("tank")
    values = {v.key: v for v in s.values}
    assert values["tau"].origin == "library-default" and values["tau"].value == ws["defaults"]["tau"]["value"]
    assert values["tau"].source.note.startswith("StorageTank's own default for tau")
    assert "Floating roof" in {sp.key: sp for sp in s.specs}["vessel_type"].choices and s.waiting == []


@pytest.mark.sim
def test_the_adsorption_column_still_does_not_build_on_the_yeast_chemicals():
    """LEFT_OUT, held: BioSTEAM's SingleComponentAdsorptionColumn on the yeast
    program's chemicals with its own defaults (the cycle time a STAND-IN)
    fails on its adsorbent. The day it builds, it enters the catalogue."""
    code = ("import warnings; warnings.simplefilter('ignore')\n"
            "import biosteam as bst\n"
            "from openferment_core.workers.proforma_worker import package_defaults, yeast_chemicals\n"
            "with package_defaults():\n"
            "    bst.settings.set_thermo(yeast_chemicals())\n"
            "    feed = bst.Stream('feed', Water=1, Ethanol=1, units='kg/hr')\n"
            "    try:\n"
            "        u = bst.SingleComponentAdsorptionColumn('A1', ins=feed, outs=('a', 'b', 'c'), cycle_time=1, "
            "adsorbate='Ethanol')\n"
            "        u.simulate()\n"
            "    except Exception as e:\n"
            "        print('REFUSED', type(e).__name__, e)\n"
            "    else:\n"
            "        print('CONVERGED')\n")
    env = {**os.environ, "PYTHONPATH": str(CORE), "PYTHONBREAKPOINT": "0"}
    r = subprocess.run([sys.executable, "-c", code], cwd=CORE, env=env, capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    assert "REFUSED" in r.stdout and "ActivatedCarbon" in r.stdout, (r.stdout, r.stderr[-2000:])
