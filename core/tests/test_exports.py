"""The export package of a project's studies (studies/exports.py; execution
prompt §9.1 step 5), offline.

The worker is test_runbooks.py's STAND-IN. A study (a run on the library's
own defaults, a scenario's run with a person's assumption and a model's
estimate, their comparison, and a locked runbook) exports as one zip that
the standard library opens alone, in `python -I -S`: every file has the
size and sha256 its manifest gives; study.json holds the runs with their
inputs' origins, the scenario, the comparison, the runbook and the
artifacts behind them; each run's SFF file is the project's, byte for byte;
versions.json names the tools; study.md names every run, scenario,
comparison and runbook. The same study exports the same files, the manifest
aside; a project with no study exports a package that says so. A contract
engine's run exports its outputs.values and the distributions it names, its
receipt the engine's words, and a comparison that holds one each empty cell
in words.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import projects
from openferment_core.api import app
from openferment_core.engine import library, runs, simulator
from openferment_core.engine.sample import SAMPLE
from openferment_core.models import ComparisonCreate, PredictedOutput, ProjectCreate, RunbookCreate
from openferment_core.studies import comparisons, exports, runbooks, scenarios
from openferment_core.workers import WorkerError

from test_engines import given
from test_runbooks import FlowsheetStandIn
from test_studies import asked

# What opens the package: the standard library alone (`-S` leaves every
# installed package off the path), in a directory of its own.
READER = '''\
import hashlib, json, sys, zipfile

with zipfile.ZipFile(sys.argv[1]) as z:
    manifest = json.loads(z.read("manifest.json"))
    listed = {f["path"]: f for f in manifest["files"]}
    assert sorted(z.namelist()) == sorted([*listed, "manifest.json"]), z.namelist()
    for path, f in listed.items():
        data = z.read(path)
        assert len(data) == f["bytes"] and hashlib.sha256(data).hexdigest() == f["sha256"], path
    study = json.loads(z.read("study.json"))
    versions = json.loads(z.read("versions.json"))
    words = z.read("study.md").decode("utf-8")
    sff = {p: hashlib.sha256(z.read(p)).hexdigest() for p in listed if p.startswith("sff/")}
    for p in sff:
        json.loads(z.read(p))
ids = [r["id"] for r in study["runs"]] + [s["id"] for s in study["scenarios"]] + \\
      [c["id"] for c in study["comparisons"]] + [b["id"] for b in study["runbooks"]]
print(json.dumps({
    "runs": [r["id"] for r in study["runs"]],
    "sff": sff,
    "versions": sorted(versions),
    "unnamed": [i for i in ids if i not in words],
    "loaded": sorted(m for m in sys.modules if m.split(".")[0] in ("openferment_core", "pydantic", "fastapi")),
    "sitePackages": [p for p in sys.path if "site-packages" in p],
}))
'''


@pytest.fixture
def worker(monkeypatch):
    stand_in = FlowsheetStandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def a_study():
    base = runs.run("sugarcane", by="Ada Moreno").run
    made = scenarios.make(asked())
    scen = scenarios.run(made.id, by="Ada Moreno").run
    compared = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.id, scen.id], by="Ada Moreno"))
    book = runbooks.make(RunbookCreate(title="Dearer cane at the bench", runId=scen.id, by="Ada Moreno", predict=[
        PredictedOutput(output="price.solvedPrice", label="Minimum selling price")]))
    runbooks.lock(book.id, by="Ada Moreno")
    return base, scen, made, compared.comparison, book


def opened(data: bytes, tmp_path: Path) -> dict:
    (tmp_path / "package").mkdir()
    (tmp_path / "reader").mkdir()
    (tmp_path / "empty").mkdir()
    package = tmp_path / "package" / "study.zip"
    package.write_bytes(data)
    reader = tmp_path / "reader" / "open_export.py"
    reader.write_text(READER, encoding="utf-8")
    done = subprocess.run([sys.executable, "-I", "-S", str(reader), str(package)], cwd=tmp_path / "empty",
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_a_study_exports_as_a_package_the_standard_library_opens_alone(worker, tmp_path):
    base, scen, made, compared, book = a_study()
    out = opened(exports.package(by="Ada Moreno"), tmp_path)
    assert out["loaded"] == [] and out["sitePackages"] == [], "nothing of openFerment's opened it"
    assert out["runs"] == [base.id, scen.id], "oldest first"
    assert out["sff"] == {f"sff/{r.id}.sff.json": runs.report(r.id).flowsheet.sha256 for r in (base, scen)}, \
        "each run's file byte for byte as the project holds it"
    assert out["versions"] == ["comparisons", "lockDigest", "openferment", "python", "runs", "sff"]
    assert out["unnamed"] == []


def test_the_study_json_holds_each_value_with_its_origin_and_the_artifacts_behind_it(worker):
    base, scen, made, compared, book = a_study()
    held = json.loads(exports.files()["study.json"])
    assert held["format"] == exports.FORMAT and held["project"]["id"] == projects.current()
    origins = {i["name"]: i["quantity"]["origin"]["kind"] for i in held["runs"][1]["inputs"]}
    assert origins["stream.sugarcane.price"] == "person-assumption" and origins["stream.sugarcane.F_mass"] == "model-estimate"
    assert held["runs"][1]["provenance"] == "assumed" and held["runs"][0]["provenance"] == "computed"
    assert [s["id"] for s in held["scenarios"]] == [made.id] and held["comparisons"][0]["id"] == compared.id
    assert {base.artifactId, scen.artifactId, compared.artifactId} == set(held["artifacts"])
    (kept,) = held["runbooks"]
    assert kept["id"] == book.id and kept["lockHash"] and "kind" not in kept["predictions"][0]
    versions = json.loads(exports.files()["versions.json"])
    assert versions["runs"][base.id]["biosteam"] == library._installed("biosteam")
    assert versions["sff"][scen.id]["record"] == f"run-{scen.id}"
    assert versions["comparisons"] == {compared.id: comparisons.VERSION}


def test_the_same_study_exports_the_same_files_the_manifest_aside(worker):
    a_study()
    first, again = exports.files(by="Ada Moreno"), exports.files(by="Grace")
    assert first.keys() == again.keys() and list(first)[-1] == "manifest.json"
    assert {p: d for p, d in first.items() if p != "manifest.json"} == {p: d for p, d in again.items() if p != "manifest.json"}
    assert json.loads(first["manifest.json"])["files"] == json.loads(again["manifest.json"])["files"]
    assert json.loads(again["manifest.json"])["exportedBy"] == "Grace"


def test_a_run_its_plant_refused_is_in_the_package_as_its_receipt(worker, monkeypatch):
    def refusing(op, args):
        if op == "library_run":
            raise WorkerError("Refused: infeasible here (BioSTEAM's InfeasibleRegion): M1")
        return worker(op, args)

    monkeypatch.setattr(simulator, "call", refusing)
    made = scenarios.make(asked())
    with pytest.raises(library.LibraryRefused):
        scenarios.run(made.id, by="Ada Moreno")
    files = exports.files()
    (receipt,) = json.loads(files["study.json"])["runs"]
    assert receipt["status"] == "refused" and receipt["artifactId"] is None
    assert not any(p.startswith("sff/") for p in files)
    assert "The plant refused it: infeasible here (BioSTEAM's InfeasibleRegion): M1" in files["study.md"].decode("utf-8")


def test_a_contract_engines_run_and_receipt_export_with_its_outputs_and_its_own_versions():
    """A run of any engine beside BioSTEAM's library (the contract's sample,
    whose worker computes nothing) exports its outputs.values, each with its
    unit and origin, and the distributions it names; its receipt is the
    engine's refusal in its words."""
    run = SAMPLE.run("placeholder", None, [given("a-parameter", 2.5, note="a placeholder")], "Ada Moreno")
    with pytest.raises(library.LibraryRefused):
        SAMPLE.run("refuses", None, [], "Ada Moreno")
    files = exports.files()
    words = files["study.md"].decode("utf-8")
    assert "Its outputs, each in the unit its artifact states:" in words
    assert f"| given a-parameter | 2.5 | placeholder-unit | artifact {run.artifactId} |" in words
    assert f"| count | 1 | 1 | artifact {run.artifactId} |" in words, "ten significant digits, as every number"
    assert "The engine refused it: the sample engine refuses every run of this thing, in these words" in words
    assert "The runs of every other engine, each on the distributions it names:" in words
    assert f"| `{run.id}` | {run.tool} ({run.toolVersion}) | openferment-core 0.1.0 |" in words
    assert "| BioSTEAM |" not in words, "no library run, so no table of BioSTEAM's distributions"
    versions = json.loads(files["versions.json"])
    assert versions["runs"][run.id] == {"tool": run.tool, "toolVersion": run.toolVersion, "openferment-core": "0.1.0"}


def test_a_comparison_that_holds_another_engines_run_exports_each_empty_cell_in_words(worker):
    base = runs.run("sugarcane", by="Ada Moreno").run
    sample = SAMPLE.run("placeholder", None, [given("a-parameter", 2.5, note="a placeholder")], "Ada Moreno")
    compared = comparisons.make(ComparisonCreate(title="A plant beside a placeholder", runIds=[base.id, sample.id]))
    assert compared.artifact.toolVersion == comparisons.VERSION_ENGINES
    words = exports.files()["study.md"].decode("utf-8")
    assert (f"| value a-parameter | {exports.NO_SUCH_VALUE} | 2.5 placeholder-unit (person-assumption, Ada Moreno) |"
            in words)
    versions = json.loads(exports.files()["versions.json"])
    assert versions["comparisons"] == {compared.comparison.id: comparisons.VERSION_ENGINES}


def test_a_project_with_no_study_exports_a_package_that_says_so():
    other = projects.create(ProjectCreate(name="Empty bench", by="Ada Moreno"))
    with projects.using(other.id):
        files = exports.files()
    assert sorted(files) == ["manifest.json", "study.json", "study.md", "versions.json"]
    words = files["study.md"].decode("utf-8")
    assert words.startswith("# Empty bench: studies") and "The project holds no engine run." in words
    assert "No study has made a runbook." in words


def test_the_route_and_the_command_line_hand_over_the_same_package(worker, tmp_path, monkeypatch):
    monkeypatch.setattr(exports, "ENV_FILE", tmp_path / "no.env")
    a_study()
    answer = TestClient(app).get("/api/studies/export")
    assert answer.status_code == 200 and answer.headers["content-type"] == "application/zip"
    assert answer.headers["content-disposition"] == f'attachment; filename="{projects.current()}-studies.zip"'
    with zipfile.ZipFile(io.BytesIO(answer.content)) as z:
        from_route = z.read("study.json")
    out = tmp_path / "studies.zip"
    assert exports.main([str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert z.read("study.json") == from_route
    assert exports.main([]) == 2
    with projects.using("no-such-project"):
        assert exports.main([str(out)]) == 2


def test_a_proforma_runs_scenario_is_named_in_the_package(monkeypatch, tmp_path):
    """A Proforma scenario's run is a run of BioSTEAM's (alpha 2.2 D6): the
    package names the scenario it belongs to by its name, as the project
    keeps it, in study.json and study.md."""
    from types import SimpleNamespace

    import standins
    from openferment_core import intake, proforma, project_state
    from openferment_core.models import ProformaRunRequest
    from standins import assumed_inputs
    from test_proforma_runs import ASSUMED, ETHANOL

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    sid = "sc-export-1"
    project_state.put("scenarios", sid, {"id": sid, "kind": "biosteam", "modelId": ETHANOL,
                                         "name": "A STAND-IN scenario", "description": "", "product": "",
                                         "pinned": False}, by="Ada Moreno")
    ran = proforma.run(ProformaRunRequest(scenarioId=sid, inputs=assumed_inputs(ASSUMED), samples=8, by="Ada Moreno"),
                       pool=pool)
    files = exports.files()
    held = json.loads(files["study.json"])
    assert [r["id"] for r in held["runs"]] == [ran.artifactId]
    assert held["proformaScenarios"] == [{"id": sid, "name": "A STAND-IN scenario"}]
    assert f"Asked for by scenario `{sid}` (A STAND-IN scenario)." in files["study.md"].decode("utf-8")
