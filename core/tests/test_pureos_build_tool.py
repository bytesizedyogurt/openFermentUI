"""`pureos_build`, `pureos_write`'s train actions, the store of the trains a
model built, and `pureos_read`'s kinds `train` and `train-run` (OF-BLD-020
§5.4; D9, D13, E.4‴).

Offline, the Proforma worker is test_train's stand-in (`TrainWorker`: STAND-IN
tables, every unit sends all on but a share of the product); the evidence pool
is a STAND-IN of records written here on a thread Q paper id, none a paper's
value. A model's train takes its inlet from a stream of a train run a STAND-IN
person kept with typed values (test_train's `spec_of`), since a model types no
value. Marked `sim`: the same build runs through the real worker.

Every STAND-IN here is an assumption of this test; only what the code does with
it is asserted.
"""
from __future__ import annotations

import ast
import json
import sys
import threading
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, audit, intake, module_stores, proposals, pureos, tools
from openferment_core.models import TrainSpec
from openferment_core.pureos import build, kept, train_spec
from openferment_core.validate import SeenSet, validate_plan
from test_module_tools import ctx_for, read
from test_train import TrainWorker, spec_of, typed

PKG = Path(__file__).resolve().parent.parent / "openferment_core"
MODEL = "claude-haiku-5-5"


def _record(rid, field, value, unit, words, paper="Q1"):
    return {"id": rid, "field": field, "value": value, "unit": unit, "paperId": paper, "quote": words,
            "method": None, "conditions": None, "provenance": "unverified", "status": "unverified"}


# STAND-IN records: two of a centrifugation step's recovery on a thread Q paper,
# one naming another step, one on an archived program's paper.
RECORDS = [
    _record("r-st-1", "step_recovery", 90.0, "%", "after centrifugation the broth kept"),
    _record("r-st-2", "step_recovery", 80.0, "%", "after centrifugation the broth kept"),
    _record("r-st-3", "step_recovery", 50.0, "%", "after the chromatography column"),
    _record("r-st-4", "step_recovery", 70.0, "%", "after centrifugation", paper="A1"),
    _record("r-cm-1", "cake_moisture", 60.0, "%", "the centrifuge cake held"),
]


def stand_in_pool(records=RECORDS):
    return SimpleNamespace(records=list(records), records_by_id={r["id"]: r for r in records})


@pytest.fixture()
def worker(monkeypatch):
    w = TrainWorker()
    from openferment_core import proforma
    from openferment_core.pureos import catalogue

    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_UNITS", {})
    return w


@pytest.fixture()
def store(tmp_path, monkeypatch, worker):
    """A throwaway data directory with the audit log and the proposals in it,
    the stand-in pool as the run's, and the model the writes are marked with."""
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(audit, "PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", tmp_path / "proposals.json")
    monkeypatch.setattr(train_spec, "_pool", lambda: stand_in_pool())
    monkeypatch.setenv("OPENFERMENT_MODEL", MODEL)
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    return tmp_path


def ctx(archived=False, pool=None):
    c = tools.ToolContext(pool_factory=lambda: pool or stand_in_pool(), include_archived=archived)
    c.ask_id, c.model = "ask-54", MODEL
    return c


def b(**fields):
    return tools.run("pureos_build", fields, ctx())


@pytest.fixture()
def inlet(store):
    """A stream a STAND-IN person's train run kept: the liquid of its flash."""
    run = pureos.run_train(spec_of())
    return f"{run.artifactId}/F1_liquid"


def built(inlet_ref, *types):
    r = b(action="new", product="ethanol", inletRef=inlet_ref)
    assert r.error is None, r.error
    tid = r.summary["trainId"]
    for t in types:
        got = b(action="add_unit", trainId=tid, unitType=t)
        assert got.error is None, got.error
    return tid


# ── the tool's shape ───────────────────────────────────────────────────


def test_pureos_build_is_registered_loose_with_ids_and_words_only():
    t = tools.REGISTRY["pureos_build"]
    assert "pureos_build" in tools.WHITELIST and not t.strict
    schema = t.info().inputSchema
    assert set(schema["properties"]) == {"action", "trainId", "unitType", "afterUnitId", "unitId", "product", "inletRef",
                                         "recordsByParam"}
    text = json.dumps(schema)
    assert '"number"' not in text and '"integer"' not in text
    assert schema["properties"]["action"]["enum"] == ["new", "add_unit", "remove_unit", "set_from_record", "run",
                                                      "propose"]
    assert "never type a number" in t.description and "pureOS → Builder" in t.description


def test_a_number_or_a_field_the_action_does_not_take_is_refused_before_anything_runs(store):
    assert "a number was typed" in b(action="new", product="ethanol", inletRef=3).error
    assert "a number was typed" in b(action="set_from_record", trainId="tr-x", unitId="C1",
                                     recordsByParam={"split.Ethanol": [0.9]}).error
    assert "refused its input" in b(action="new", product="ethanol", value="nine").error
    extra = b(action="new", product="ethanol", inletRef="0123456789abcdef/F1_liquid", unitType="flash")
    assert extra.error == "pureos_build refused: new takes product, inletRef; unitType is not one of them"
    assert audit.read() == [] and kept.read().trains == []


# ── a train, built a step at a time ────────────────────────────────────


def test_new_keeps_a_train_for_the_product_from_a_runs_stream_marked_as_the_models(store, inlet):
    r = b(action="new", product="ethanol", inletRef=inlet)
    assert r.error is None, r.error
    s = r.summary
    aid = inlet.split("/")[0]
    assert s["state"] == "open" and s["trainId"].startswith(build.ID_PREFIX) and s["product"] == "ethanol"
    assert s["program"] == "yeast" and s["inlet"] == {"kind": "run-stream", "ref": aid, "streamId": "F1_liquid",
                                                      "vessel": None}
    assert s["units"] == [] and s["toRun"] == ["a train holds at least one unit"]
    assert any("the program is yeast: the program pureos.train_run" in w for w in s["read"])
    [k] = kept.read().trains
    assert (k.spec.id, k.agent, k.madeBy, k.effort, k.askId) == (s["trainId"], "model", MODEL, "medium", "ask-54")
    assert k.at == k.updatedAt
    [line] = audit.read()
    assert (line.agent, line.who, line.module, line.action, line.state, line.target, line.askId, line.effort) == (
        "model", MODEL, "pureos", "new_train", "open", s["trainId"], "ask-54", "medium")
    assert line.detail["tool"] == "pureos_build"
    # At no gate: nothing was proposed.
    assert proposals.read().proposals == []


def test_units_are_added_in_order_named_by_type_and_taken_out(store, inlet):
    tid = built(inlet, "centrifugation", "tank")
    after = b(action="add_unit", trainId=tid, unitType="tank", afterUnitId="C1")
    assert after.error is None and after.summary["added"] == "T2"
    first = b(action="add_unit", trainId=tid, unitType="pump", afterUnitId="inlet")
    assert [u["id"] for u in first.summary["units"]] == ["P1", "C1", "T2", "T1"]
    c1 = next(u for u in first.summary["units"] if u["id"] == "C1")
    assert c1 == {"id": "C1", "type": "centrifugation", "name": "Solids centrifuge", "stage": c1["stage"],
                  "class": "SolidsCentrifuge", "outlets": {"cake": "waste", "liquid": "onward"}, "recordsNamed": {}}
    gone = b(action="remove_unit", trainId=tid, unitId="T2")
    assert gone.error is None and [u["id"] for u in gone.summary["units"]] == ["P1", "C1", "T1"]
    assert [a.action for a in audit.read()] == ["new_train", "add_unit", "add_unit", "add_unit", "add_unit",
                                                "remove_unit"]
    k = kept.kept_train(tid)
    assert k is not None and k.updatedAt > k.at


@pytest.mark.parametrize("fields, words", [
    ({"action": "new", "product": "ethanol", "inletRef": ""}, "name the inlet by the artifact it is read from"),
    ({"action": "new", "product": "ethanol", "inletRef": "beer"}, "'beer' is not an artifact id"),
    ({"action": "new", "product": "ethanol", "inletRef": "0123456789abcdef"},
     "there is no kept artifact 0123456789abcdef here"),
    ({"action": "new", "product": "phb", "inletRef": "@run/F1_liquid"}, "phb is none of them"),
    ({"action": "new", "product": "", "inletRef": "@run/F1_liquid"}, "name the product the train recovers"),
    ({"action": "new", "product": "ethanol", "inletRef": "@run"}, "name its stream as"),
    ({"action": "new", "product": "ethanol", "inletRef": "@run/beer"}, "holds no stream 'beer'"),
    ({"action": "add_unit", "trainId": "tr-nowhere", "unitType": "tank"}, "there is no kept train tr-nowhere here"),
    ({"action": "add_unit", "trainId": "", "unitType": "tank"}, "name the train by its id"),
    ({"action": "add_unit", "trainId": "@train", "unitType": "centrifuge"}, "there is no unit type 'centrifuge'"),
    ({"action": "add_unit", "trainId": "@train", "unitType": "tank", "afterUnitId": "Z9"}, "has no unit 'Z9'"),
    ({"action": "remove_unit", "trainId": "@train", "unitId": "Z9"}, "has no unit 'Z9'"),
    ({"action": "run", "trainId": "@train"}, "a train holds at least one unit"),
])
def test_a_step_that_cannot_be_taken_is_refused_in_words_and_changes_nothing(store, inlet, fields, words):
    tid = built(inlet)
    fields = {k: (v.replace("@run", inlet.split("/")[0]).replace("@train", tid) if isinstance(v, str) else v)
              for k, v in fields.items()}
    before, lines = kept.read(), len(audit.read())
    r = b(**fields)
    assert r.error and r.error.startswith("pureos_build refused: ") and words in r.error, r.error
    assert kept.read() == before and len(audit.read()) == lines and r.evidence == []


def test_an_inlet_of_another_kind_or_an_archived_program_is_refused(store, inlet, monkeypatch):
    from test_train import real_simulation

    sim = real_simulation()
    from_sim = b(action="new", product="", inletRef=sim.artifactId)
    assert from_sim.error is None and from_sim.summary["product"] == "ethanol"
    assert from_sim.summary["inlet"]["kind"] == "simulation"
    assert any("the product is the simulation's own, ethanol" in w for w in from_sim.summary["read"])
    assert "makes ethanol; a train recovering" in b(action="new", product="phb", inletRef=sim.artifactId).error
    assert "names no stream" in b(action="new", product="ethanol", inletRef=f"{sim.artifactId}/beer").error
    # An artifact of another kind is not an inlet (a STAND-IN: the simulation's file read as a ceiling's).
    real_get = artifacts.get
    ceiling = real_get(sim.artifactId).model_copy(update={"id": "f" * 16, "tool": "geneos.ceiling"})
    monkeypatch.setattr(artifacts, "get", lambda aid: ceiling if aid == "f" * 16 else real_get(aid))
    other = b(action="new", product="ethanol", inletRef="f" * 16).error
    assert "is a geneos.ceiling artifact; a train's inlet is a kept simulation's harvest" in other
    # With the switch off, an inlet of an archived program is refused, naming the switch.
    monkeypatch.setattr(module_stores, "artifact_program", lambda a, *x, **k: "pha")
    off = b(action="new", product="ethanol", inletRef=inlet)
    assert "belongs to PHA, archived (hidden)" in off.error and "Settings → Programs" in off.error
    on = tools.run("pureos_build", {"action": "new", "product": "ethanol", "inletRef": inlet}, ctx(archived=True))
    assert "pureOS builds a train on" in on.error and "program pha has no chemical set here" in on.error


# ── records named for a parameter ──────────────────────────────────────


def test_set_from_record_binds_exactly_the_records_named_and_the_run_reads_them(store, inlet):
    tid = built(inlet, "centrifugation", "tank")
    r = b(action="set_from_record", trainId=tid, unitId="C1", recordsByParam={"split.Ethanol": ["r-st-1", "r-st-2"]})
    assert r.error is None, r.error
    assert r.summary["bound"] == {"split.Ethanol": {"field": "step_recovery", "records": 2}}
    c1 = next(u for u in r.summary["units"] if u["id"] == "C1")
    assert c1["recordsNamed"] == {"split.Ethanol": 2}
    assert kept.kept_train(tid).spec.units[0].records == {"split.Ethanol": ["r-st-1", "r-st-2"]}
    line = audit.read()[-1]
    assert (line.action, line.target, line.detail["unit"]) == ("set_from_record", tid, "C1")
    # Only the summary's counts; no value of the records reaches the model.
    assert "0.15" not in json.dumps(r.summary) and "90" not in json.dumps(r.summary["bound"])


@pytest.mark.parametrize("named, words", [
    ({"split.Ethanol": ["r-zz"]}, "record r-zz is not in the evidence pool here"),
    ({"split.Ethanol": ["r-cm-1"]}, "record r-cm-1 is of cake_moisture, not step_recovery"),
    ({"split.Ethanol": ["r-st-3"]}, "record r-st-3: naming another step or none"),
    ({"split.Ethanol": ["r-st-4"]}, "record r-st-4: not on the yeast program's papers"),
    ({"split.Water": ["r-st-1"]}, "binds the product's split alone (Ethanol)"),
    ({"split.Ethanol": []}, "recordsByParam names no record for split.Ethanol"),
    ({"split.Ethanol": ["r-st-1", "r-st-1"]}, "record r-st-1 is named twice for split.Ethanol"),
    ({"split.Ethanol": ["../corpus"]}, "a record is named by its id"),
    ({"split.Octane": ["r-st-1"]}, "not a parameter of unit C1 on this train's chemicals"),
    ({"order": ["r-st-1"]}, "order binds from no record field"),
    ({"growth": ["r-st-1"]}, "has no parameter 'growth'"),
    ({}, "name at least one parameter of unit C1"),
])
def test_set_from_record_refuses_a_record_that_cannot_bind_naming_it_and_why(store, inlet, named, words):
    tid = built(inlet, "centrifugation")
    before, lines = kept.read(), len(audit.read())
    r = b(action="set_from_record", trainId=tid, unitId="C1", recordsByParam=named)
    assert r.error and r.error.startswith("pureos_build refused: ") and words in r.error, r.error
    assert kept.read() == before and len(audit.read()) == lines


def test_with_the_switch_off_a_record_of_an_archived_program_is_not_in_the_pool(store, inlet):
    tid = built(inlet, "centrifugation")
    shown = stand_in_pool([r for r in RECORDS if r["paperId"] != "A1"])
    r = tools.run("pureos_build", {"action": "set_from_record", "trainId": tid, "unitId": "C1",
                                   "recordsByParam": {"split.Ethanol": ["r-st-4"]}}, ctx(pool=shown))
    assert "record r-st-4 is not in the evidence pool here" in r.error


# ── the run ────────────────────────────────────────────────────────────


def test_run_keeps_one_train_run_cited_by_its_artifact_id_with_the_whole_run_in_data(store, inlet, worker):
    tid = built(inlet, "centrifugation", "pressure-filtration", "spray-dry")
    assert b(action="set_from_record", trainId=tid, unitId="C1",
             recordsByParam={"split.Ethanol": ["r-st-1", "r-st-2"]}).error is None
    r = b(action="run", trainId=tid)
    assert r.error is None, r.error
    (ev,) = r.evidence
    s = r.summary
    art = artifacts.get(ev.id)
    assert art.tool == "pureos.train_run" and ev.basis.tool == "pureos.train_run" and ev.basis.artifactId == art.id
    assert ev.id == s["artifactId"] == s["evidenceId"] and s["trainId"] == tid
    assert ev.value == pytest.approx(art.output and pureos.train_of(art).overallRecovery) and ev.figure == "recovery"
    assert ev.provenance == s["provenance"] == art.provenance
    # Each unit, what bound its parameters by origin and count; never a value.
    units = {u["id"]: u for u in s["units"]}
    assert list(units) == ["C1", "P1", "S1"] and units["C1"]["recordsBinding"]["split.Ethanol"] == 2
    # split.Ethanol by the records named; the cake's moisture by the one the rule finds (r-cm-1).
    assert units["C1"]["boundBy"]["record"] == 2 and units["C1"]["recordsBinding"]["moisture_content"] == 1
    assert units["C1"]["recovery"] == pytest.approx(0.9)
    assert s["overallRecovery"] == pytest.approx(0.9 ** 3, rel=1e-3) and s["product"] == "Ethanol"
    assert len(json.dumps(s, ensure_ascii=False)) <= tools.MAX_SUMMARY_CHARS
    # The whole run rides in data, which no model reads.
    assert r.data["artifactId"] == art.id and r.data["spec"]["id"] == tid and r.data["train"]["streams"]
    # The run's basis names the records and the train the model built.
    by = {i.name: i for i in art.inputs}
    assert [i.value for i in art.inputs if i.name == "C1.split.Ethanol record"] == ["r-st-1", "r-st-2"]
    assert json.loads(by["train"].value)["id"] == tid and by["C1 class"].value == "SolidsCentrifuge"
    line = audit.read()[-1]
    assert (line.agent, line.who, line.module, line.action, line.target) == ("model", MODEL, "pureos", "run_train", tid)
    assert line.detail["artifactId"] == art.id and line.detail["tool"] == "pureos_build"
    assert proposals.read().proposals == []
    # pureos_write's run_train is the same run, marked with its own name.
    w = tools.run("pureos_write", {"action": "run_train", "target": tid, "fields": {}, "note": "again"}, ctx())
    assert w.error is None and w.evidence[0].id == ev.id
    assert audit.read()[-1].detail["tool"] == "pureos_write" and audit.read()[-1].detail["note"] == "again"
    mine = [c for c in worker.calls if c[0] == "train_run" and c[1]["system"] == f"pureos_{tid.replace('-', '_')}"]
    assert len(mine) == 1, "the same train is the same artifact, and the worker is not asked twice"


def test_a_run_with_a_value_waiting_returns_the_refusals_words_and_keeps_nothing(store, inlet, worker):
    tid = built(inlet, "pressure-filtration", "flash")
    lines = len(audit.read())
    r = b(action="run", trainId=tid)
    assert r.error and r.error.startswith("pureos_build refused: unit F1: Flash drum waits for")
    assert "a model never supplies one" in r.error and "pureOS → Builder" in r.error
    assert r.evidence == [] and len(audit.read()) == lines
    assert not [a for a in artifacts.all_artifacts() if a.tool == "pureos.train_run" and
                (a.output.get("train") or {}).get("id") == tid]
    assert not [c for c in worker.calls if c[0] == "train_run" and c[1]["system"] == f"pureos_{tid.replace('-', '_')}"]
    w = tools.run("pureos_write", {"action": "run_train", "target": tid, "fields": {}, "note": ""}, ctx())
    assert w.error == r.error.replace("pureos_build", "pureos_write", 1)


def test_a_worker_that_cannot_answer_is_said_in_words(store, inlet, monkeypatch):
    tid = built(inlet, "pressure-filtration")
    from openferment_core import proforma
    from openferment_core.workers import WorkerError

    def down(op, args):
        raise WorkerError("the simulator is starting")

    monkeypatch.setattr(proforma, "call", down)
    monkeypatch.setattr(train_spec, "_SPECS", {})
    r = b(action="run", trainId=tid)
    assert r.error == "pureos_build could not run the train: the simulator is starting"


# ── pureos_write's train actions ───────────────────────────────────────


def test_pureos_write_builds_the_same_train_through_the_same_functions(store, inlet):
    def w(action, target="", fields=None):
        return tools.run("pureos_write", {"action": action, "target": target, "fields": fields or {}, "note": "n"}, ctx())

    made = w("new_train", fields={"product": "ethanol", "inletRef": inlet})
    assert made.error is None, made.error
    tid = made.summary["trainId"]
    assert w("add_unit", tid, {"unitType": "centrifugation"}).error is None
    bound = w("set_from_record", tid, {"unitId": "C1", "records.split.Ethanol": "r-st-1, r-st-2"})
    assert bound.error is None and bound.summary["bound"]["split.Ethanol"]["records"] == 2
    assert w("remove_unit", tid, {"unitId": "C1"}).summary["units"] == []
    assert [(a.action, a.detail["tool"]) for a in audit.read()] == [
        ("new_train", "pureos_write"), ("add_unit", "pureos_write"), ("set_from_record", "pureos_write"),
        ("remove_unit", "pureos_write")]
    odd = w("add_unit", tid, {"unitType": "tank", "split": "0"})
    assert odd.error == "pureos_write refused add_unit: split is not a field of it; its fields are unitType, afterUnitId"
    nothing = w("publish")
    assert "'publish' is not an action" in nothing.error and "no write function" in nothing.error
    assert "new_train:" in tools.REGISTRY["pureos_write"].description


# ── propose (OF-BLD-020 §7.2's proposer) ───────────────────────────────


def test_propose_refuses_in_words_until_the_proposer_has_landed(store, monkeypatch):
    monkeypatch.setitem(sys.modules, "openferment_core.pureos.propose", None)
    r = b(action="propose", product="ethanol", inletRef="")
    assert r.error.startswith("pureos_build refused propose: the train proposer is OF-BLD-020 §7.2's")
    assert kept.read().trains == [] and audit.read() == []


def test_propose_keeps_the_proposers_train_under_an_id_of_its_own(store, inlet, monkeypatch):
    """A STAND-IN proposer (§7.2's shape: `propose(product, host, inlet_ref)`
    returns a train and its reasons); its train is kept as the model's."""
    asked = []

    def propose(product, host, inlet_ref):
        asked.append((product, host, inlet_ref))
        spec = spec_of(id="proposed", units=[{"id": "D1", "type": "distillation"}],
                       inlet={"kind": "run-stream", "ref": inlet.split("/")[0], "streamId": "F1_liquid"})
        return SimpleNamespace(train=spec, reasons=["STAND-IN reason: the product is volatile"])

    stand_in = ModuleType("openferment_core.pureos.propose")
    stand_in.propose = propose  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openferment_core.pureos.propose", stand_in)
    r = b(action="propose", product="ethanol", inletRef=inlet)
    assert r.error is None, r.error
    assert asked == [("ethanol", None, inlet)]
    assert r.summary["trainId"].startswith(build.ID_PREFIX) and r.summary["trainId"] != "proposed"
    assert r.summary["reasons"] == ["STAND-IN reason: the product is volatile"]
    [k] = kept.read().trains
    assert [u.type for u in k.spec.units] == ["distillation"] and k.madeBy == MODEL
    assert audit.read()[-1].action == "propose_train"


# ── the store ──────────────────────────────────────────────────────────


def test_the_store_is_written_by_one_function_under_its_locks_and_keeps_every_change(store, inlet):
    tid = built(inlet)
    # Twenty changes at once from eight threads: none is lost.
    errors = []

    def add(n):
        try:
            for _ in range(n):
                assert b(action="add_unit", trainId=tid, unitType="tank").error is None
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=add, args=(n,)) for n in (3, 3, 3, 3, 2, 2, 2, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    units = kept.kept_train(tid).spec.units
    assert len(units) == 20 and len({u.id for u in units}) == 20
    # A person's train is never kept here, and a change keeps its train's id.
    with pytest.raises(kept.KeptTrainRefused, match="a person's trains live in their browser"):
        kept.keep_train(tid, lambda cur: cur, "Stand-In Person", agent="person")
    with pytest.raises(kept.KeptTrainRefused, match="a change keeps the train's id"):
        kept.keep_train(tid, lambda cur: cur.model_copy(update={"id": "tr-other"}), MODEL)
    with pytest.raises(kept.KeptTrainRefused, match="names the model that made it"):
        kept.keep_train(None, lambda _: spec_of(), " ")
    # The file is the service's data directory's, and no file but its own is written.
    assert kept.path() == store / kept.FILE and kept.path().exists()
    assert sorted(p.name for p in store.iterdir() if p.name.startswith("pureos-trains")) == [
        "pureos-trains.json", "pureos-trains.json.lock"]


def test_kept_py_writes_only_through_atomic_and_holds_no_process_number():
    for rel in ("pureos/kept.py", "pureos/build.py"):
        src = (PKG / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        named = {"ID_HEX", "SUMMARY_DIGITS", "MAX_LINE_CHARS", "JSON_INDENT"}
        allowed = {id(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id in named for t in n.targets)}
        found = [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
                 and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
                 and n.value not in (0, 1) and id(n) not in allowed]
        assert found == [], (rel, found)
        assert ".write_text(" not in src.replace("atomic.write_text(", ""), rel
    assert "atomic.write_text(" in (PKG / "pureos/kept.py").read_text(encoding="utf-8")


def test_the_trains_kept_endpoint_lists_them_newest_first_and_honours_the_switch(store, inlet, monkeypatch):
    from openferment_core import api

    client = TestClient(api.app, base_url="http://127.0.0.1")
    assert client.get("/api/pureos/trains-kept").json() == []
    first, second = built(inlet), built(inlet, "tank")
    body = client.get("/api/pureos/trains-kept").json()
    assert [k["spec"]["id"] for k in body] == [second, first]
    assert body[0]["madeBy"] == MODEL and body[0]["agent"] == "model" and body[0]["at"]
    assert [u["type"] for u in body[0]["spec"]["units"]] == ["tank"]
    # A train of an archived program hides unless asked for.
    kept.keep_train(first, lambda cur: cur.model_copy(update={"program": "pha"}), MODEL)
    assert [k["spec"]["id"] for k in client.get("/api/pureos/trains-kept").json()] == [second]
    assert {k["spec"]["id"] for k in client.get("/api/pureos/trains-kept?includeArchived=true").json()} == {first, second}
    assert client.post("/api/pureos/trains-kept").status_code == 405


# ── pureos_read, SeenSet, the prompt ───────────────────────────────────


def test_pureos_read_lists_a_models_train_and_its_runs_with_no_number_in_their_detail(store, inlet):
    from test_module_tools import _numbers_in

    tid = built(inlet, "pressure-filtration")
    run = b(action="run", trainId=tid)
    aid = run.evidence[0].id
    pool = stand_in_pool()
    c = ctx_for(pool, artifacts=artifacts.all_artifacts, kept_trains=lambda: kept.read().trains)
    assert module_stores.KINDS["pureos"] == ("unit-operation", "train", "train-unit", "train-run")
    trains = read("pureos", c, ids=[tid]).rows
    assert [(r.kind, r.id) for r in trains] == [("train", tid), ("train-run", aid)]
    t, rr = trains
    assert t.ref == f"pureos/train/{tid}" and t.state == "open" and t.status == "built by a model" and t.provenance is None
    assert t.detail["madeBy"] == MODEL and t.detail["runs"] == [aid] and t.detail["unitTypes"] == ["pressure-filtration"]
    assert rr.ref == f"pureos/train-run/{aid}" and rr.state == "open" and rr.status == "computed"
    assert rr.label == "Run of train ethanol train, built by a model (ethanol)"
    assert rr.detail["trainId"] == tid and rr.detail["productStream"] and rr.detail["units"] == ["P1"]
    assert _numbers_in(t.detail) == [] and _numbers_in(rr.detail) == [], "a train run's numbers stay in its artifact"
    # The mark is worked out from the inputs as they stand, never copied from the file.
    doctored = artifacts.get(aid).model_copy(update={"provenance": "measured"})
    other = [a for a in artifacts.all_artifacts() if a.id != aid]
    c2 = ctx_for(pool, artifacts=lambda: [*other, doctored], kept_trains=lambda: kept.read().trains)
    [again] = read("pureos", c2, ids=[aid], kind="train-run").rows
    assert again.provenance == artifacts.get(aid).provenance != "measured"
    # The STAND-IN person's run the inlet is read from is a train run too.
    person = inlet.split("/")[0]
    assert {r.id for r in read("pureos", c, kind="train-run").rows} == {aid, person}
    assert "train-run" in tools.REGISTRY["pureos_read"].description


def test_a_claim_cites_a_run_by_its_evidence_id_or_its_rows_ref_and_never_states_its_recovery(store, inlet):
    tid = built(inlet, "pressure-filtration")
    run = b(action="run", trainId=tid)
    aid = run.evidence[0].id
    ref = f"pureos/train-run/{aid}"
    pool = stand_in_pool()
    from_tool = SeenSet()
    from_tool.add(run)
    assert from_tool.runs == {aid: ref}, "SeenSet learns the run from the evidence pureos_build returns"
    seen = SeenSet()
    seen.add(read("pureos", ctx_for(pool, artifacts=artifacts.all_artifacts), ids=[aid], kind="train-run"))
    assert seen.runs == {aid: ref}, "and from pureos_read's row"

    def claim(cid, text="The train recovers most of the ethanol it takes in.", evidence=(), refs=()):
        return {"id": cid, "text": text, "recordIds": [], "support": "direct", "passages": [],
                "evidenceIds": list(evidence), "moduleRefs": list(refs)}

    kept_by_id = validate_plan([claim("c1", evidence=[aid]),
                                claim("c2", text="The train recovers 73 percent of the ethanol.", evidence=[aid]),
                                claim("c3", evidence=["0123456789abcdef"])], from_tool, pool)
    assert [c.id for c in kept_by_id.claims] == ["c1"] and kept_by_id.claims[0].provenance == run.evidence[0].provenance
    assert kept_by_id.reasons[0].startswith("c2: claim text contains a number")
    assert kept_by_id.reasons[1].startswith("c3: cites what no tool returned in this run")
    by_row = validate_plan([claim("c4", refs=[ref]), claim("c5", evidence=[aid])], seen, pool)
    assert [c.id for c in by_row.claims] == ["c4"]
    assert by_row.reasons[0].startswith(f"c5: cites {aid} by evidence id, which a read returned only as a row: cite {ref}")
    # A refused run teaches the set nothing.
    nothing = SeenSet()
    nothing.add(b(action="run", trainId="tr-nowhere"))
    assert not nothing.evidence and not nothing.runs


def test_the_prompt_says_a_trains_numbers_are_read_from_its_runs_artifact():
    from openferment_core import postdoc_agent

    rule = postdoc_agent.AGENT_SYSTEM.split("17. ", 1)[1]
    assert rule.startswith("A train is built with pureos_build")
    assert "never" in rule and "stated by you" in rule and "its artifact id" in rule and "pureOS → Builder" in rule
    assert {"pureos_build", "pureos_write", "draft_runbook"} <= postdoc_agent.UNCACHED


def test_the_trace_names_each_step_of_a_build(store, inlet):
    from openferment_core import postdoc_agent

    made = b(action="new", product="ethanol", inletRef=inlet)
    tid = made.summary["trainId"]
    line = postdoc_agent._summary_line
    assert line("pureos_build", {"action": "new"}, made) == f"Built a train for ethanol · kept train {tid}"
    added = b(action="add_unit", trainId=tid, unitType="pressure-filtration")
    assert line("pureos_build", {"action": "add_unit", "unitType": "pressure-filtration"}, added) == (
        f"Added pressure-filtration to train {tid} as P1")
    ran = b(action="run", trainId=tid)
    assert line("pureos_build", {"action": "run"}, ran) == f"Ran train {tid} · kept run {ran.summary['artifactId']}"
    refused = b(action="run", trainId="tr-nowhere")
    assert line("pureos_build", {"action": "run"}, refused).count("pureos_build refused") == 1


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.fixture()
def real(monkeypatch, tmp_path):
    from openferment_core import proforma

    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(audit, "PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", tmp_path / "proposals.json")
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_pool", lambda: stand_in_pool())
    monkeypatch.setenv("OPENFERMENT_MODEL", MODEL)
    return tmp_path


@pytest.mark.sim
def test_a_model_builds_three_units_on_a_kept_stream_and_runs_them_through_the_real_worker(real):
    """new → three units → run, through BioSTEAM, on the liquid of a STAND-IN
    person's centrifuged broth: a kept run whose units are the three a model
    named, each at its class's own defaults; a centrifuge whose split the
    records named bind runs too; a flash waits for a person's two settings,
    and the run refuses in words, keeping nothing."""
    person = pureos.run_train(spec_of(inlet={"kind": "typed", "params": {
        "broth_flow": typed(1.0), "conc.Yeast": typed(10.0), "conc.Ethanol": typed(50.0),
        "conc.Glucose": typed(5.0)}}, units=[{"id": "C1", "type": "centrifugation",
                                               "params": {"split.Yeast": typed(0.9)}}]))
    stream = f"{person.artifactId}/C1_liquid"
    tid = built(stream, "tank", "pump", "mix-tank")
    r = b(action="run", trainId=tid)
    assert r.error is None, r.error
    (ev,) = r.evidence
    art = artifacts.get(ev.id)
    assert art.tool == "pureos.train_run" and [u["id"] for u in r.summary["units"]] == ["T1", "P1", "M1"]
    assert [i.value for i in art.inputs if i.name.endswith(" class")] == ["StorageTank", "Pump", "MixTank"]
    assert all(set(u["boundBy"]) == {"library-default"} for u in r.summary["units"]), "a model typed nothing"
    assert r.summary["overallRecovery"] == pytest.approx(1.0, rel=1e-6), "nothing leaves a tank, a pump or a mixer"
    assert audit.read()[-1].action == "run_train" and artifacts.replay(ev.id).identical
    # A centrifuge's split bound by the records named for it.
    spun = built(stream, "centrifugation", "pressure-filtration", "spray-dry")
    assert b(action="set_from_record", trainId=spun, unitId="C1",
             recordsByParam={"split.Ethanol": ["r-st-1", "r-st-2"]}).error is None
    got = b(action="run", trainId=spun)
    assert got.error is None, got.error
    c1 = got.summary["units"][0]
    assert c1["recordsBinding"]["split.Ethanol"] == 2 and 0 < c1["recovery"] < 1 and c1["lostTo"] == ["C1_cake"]
    assert 0 < got.summary["overallRecovery"] <= c1["recovery"]
    # A flash waits for a person's two settings.
    waits = built(stream, "flash")
    before = {a.id for a in artifacts.all_artifacts()}
    refused = b(action="run", trainId=waits)
    assert refused.error and refused.error.startswith("pureos_build refused: unit F1: Flash drum waits for")
    assert "pureOS → Builder" in refused.error and {a.id for a in artifacts.all_artifacts()} == before
