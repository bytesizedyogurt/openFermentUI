"""The worker runner (OF-BLD-014 §3.4, E.6): start, timeout, crash, restart."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from openferment_core.workers import SimWorker, WorkerCrashed, WorkerError, WorkerTimeout, serve

ECHO = "openferment_core.workers.echo_worker"


@pytest.fixture()
def worker():
    w = SimWorker(ECHO, timeout_s=10)
    yield w
    w.close()


def test_it_starts_on_first_use_and_stays_warm(worker):
    assert worker.starts == 0 and not worker.alive
    first = worker.ping()
    assert first["worker"] == "echo" and worker.alive
    assert worker.call("echo", {"a": "b"}) == {"a": "b"}
    assert worker.ping()["pid"] == first["pid"] and worker.starts == 1


def test_a_timeout_kills_it_and_the_next_call_starts_another(worker):
    pid = worker.ping()["pid"]
    with pytest.raises(WorkerTimeout):
        worker.call("sleep", {"seconds": 5}, timeout_s=0.3)
    assert not worker.alive
    assert worker.ping()["pid"] != pid and worker.starts == 2


def test_a_crash_reports_the_stderr_tail_and_the_next_call_restarts(worker):
    worker.ping()
    with pytest.raises(WorkerCrashed) as e:
        worker.call("exit", {"code": 3, "say": "the last words of the worker"})
    assert "the last words of the worker" in e.value.stderr_tail
    assert worker.call("echo", {"back": "again"}) == {"back": "again"} and worker.starts == 2


def test_an_error_answer_leaves_the_worker_running(worker):
    pid = worker.ping()["pid"]
    with pytest.raises(WorkerError, match="asked to fail"):
        worker.call("fail")
    with pytest.raises(WorkerError, match="no op"):
        worker.call("nonesuch")
    assert worker.ping()["pid"] == pid


def test_a_library_printing_to_stdout_does_not_corrupt_the_stream(worker):
    assert worker.call("chatter") == {"quiet": True}
    assert worker.call("echo", {"x": "y"}) == {"x": "y"}


def test_a_module_that_does_not_exist_crashes_with_its_reason():
    w = SimWorker("openferment_core.workers.nonesuch", timeout_s=10)
    try:
        with pytest.raises(WorkerCrashed) as e:
            w.ping()
        assert "No module named" in e.value.stderr_tail
    finally:
        w.close()


def test_serve_answers_ping_and_times_each_response():
    out = io.StringIO()
    serve({"echo": lambda a: a}, name="t", stdin=io.StringIO('{"id": 1, "op": "ping"}\n{"id": 2, "op": "echo", "args": {"k": "v"}}\nnot json\n'), stdout=out)
    lines = [json.loads(x) for x in out.getvalue().splitlines()]
    assert lines[0]["ok"] and lines[0]["result"]["worker"] == "t"
    assert lines[1] == {"id": 2, "ok": True, "result": {"k": "v"}, "ms": lines[1]["ms"]}
    assert lines[2]["ok"] is False and "ms" in lines[2]


def test_no_worker_starts_able_to_stop_in_a_debugger(monkeypatch):
    """OF-BLD-020 §4.1: BioSTEAM 2.54.0's AeratedBioreactor answers a failure
    of its bubble-column correlation with a bare `breakpoint()`, which would
    open pdb on a worker's JSON channel and hang it. Every worker, the
    Proforma worker first, starts with PYTHONBREAKPOINT=0."""
    import subprocess

    from openferment_core import workers

    seen = {}

    class Stop(Exception):
        pass

    def popen(args, **kwargs):
        seen.update(args=args, env=kwargs.get("env") or {})
        raise Stop

    monkeypatch.setenv("PYTHONBREAKPOINT", "pdb.set_trace")
    monkeypatch.setattr(subprocess, "Popen", popen)
    w = SimWorker("openferment_core.workers.proforma_worker", timeout_s=1)
    with pytest.raises(Stop):
        w.ping()
    assert seen["args"][-1] == "openferment_core.workers.proforma_worker"
    assert seen["env"]["PYTHONBREAKPOINT"] == "0"
    assert workers.SimWorker is SimWorker


# Part G, rule 8: cobra in the geneOS worker alone; biosteam in the Proforma
# worker and flowsheets/ alone. Neither exists yet; this holds the line from
# the first import on.
PKG = Path(__file__).resolve().parent.parent / "openferment_core"
ALLOWED = {
    "cobra": {"workers/geneos_worker.py"},
    # OF-BLD-020 E.3‴, §5.1: pureOS's unit catalogue reads a class's defaults
    # in functions that import BioSTEAM inside themselves and run in the worker
    # (its module imports none at the top: held below), and the in-house units
    # subclass `bst.Unit`, so the worker alone imports them (held below).
    "biosteam": {"workers/proforma_worker.py", "pureos/catalogue.py", "pureos/inhouse.py"},
    # OF-BLD-019 §4.2: BioSTEAM's property engine, which the service reaches
    # through the Proforma worker's `thermo_props` op and nowhere else.
    "thermosteam": {"workers/proforma_worker.py", "pureos/inhouse.py"},
    # OF-BLD-020 E.3‴: scipy in fermOS's kinetics and fits alone among the
    # service's modules. The workers and the flowsheets they run may use it
    # (worker side).
    "scipy": {"kinetics.py", "fermos.py"},
    # alpha 2.0 (ADR-003): the vendored SFF toolkit imports BioSTEAM when it is
    # imported, so it is imported in its worker module alone.
    "pisces_sff": {"workers/sff_toolkit.py"},
}
# What runs in a worker's process, not the service's.
WORKER_SIDE = ("workers/", "flowsheets/")


@pytest.mark.parametrize("lib", sorted(ALLOWED))
def test_heavy_libraries_are_imported_in_their_worker_alone(lib):
    pattern = re.compile(rf"^\s*(import\s+{lib}\b|from\s+{lib}(\.|\s))", re.M)
    offenders = []
    for path in PKG.rglob("*.py"):
        rel = path.relative_to(PKG).as_posix()
        if lib in ("biosteam", "thermosteam") and rel.startswith("flowsheets/"):
            continue
        if lib == "scipy" and rel.startswith(WORKER_SIDE):
            continue
        if rel in ALLOWED[lib]:
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert offenders == [], f"{lib} is imported outside its worker: {offenders}"


# ── pureOS's unit catalogue (OF-BLD-020 §5.1, E.3‴) ────────────────────

CORE = PKG.parent


def test_the_catalogue_imports_no_biosteam_at_its_top():
    """Its BioSTEAM side imports inside the functions the worker calls; the
    module's own body imports neither library, so the service imports it."""
    import ast

    tree = ast.parse((PKG / "pureos" / "catalogue.py").read_text(encoding="utf-8"))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    named = {a.name.split(".")[0] for n in top for a in n.names} | {
        (n.module or "").split(".")[0] for n in top if isinstance(n, ast.ImportFrom)}
    assert not named & {"biosteam", "thermosteam", "biorefineries"}, named


def test_the_service_lists_the_catalogue_and_its_specs_with_no_biosteam_loaded():
    """Importing pureOS, its catalogue and the service, listing the catalogue
    and reading every provider's static specs loads neither BioSTEAM nor
    thermosteam, nor the in-house units, which subclass `bst.Unit`."""
    import subprocess
    import sys

    code = ("import sys\n"
            "from openferment_core import api, params, pureos\n"
            "from openferment_core.pureos import catalogue\n"
            "catalogue.listing(); params.check()\n"
            "from fastapi.testclient import TestClient\n"
            "assert TestClient(api.app, base_url='http://127.0.0.1').get('/api/pureos/catalogue').status_code == 200\n"
            "steam = sorted(m for m in sys.modules if m.split('.')[0] in ('biosteam', 'thermosteam', 'biorefineries'))\n"
            "assert not steam, steam\n"
            "assert 'openferment_core.pureos.inhouse' not in sys.modules\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]


def test_no_service_module_but_the_worker_imports_the_in_house_units():
    pattern = re.compile(r"(from\s+[.\w]*pureos\s+import\s+[^\n]*\binhouse\b|from\s+[.\w]*pureos\.inhouse\s+import|"
                         r"from\s+\.inhouse\s+import|import\s+[.\w]*pureos\.inhouse\b|import_module\(\s*[\"'][^\"']*inhouse)")
    offenders = []
    for path in PKG.rglob("*.py"):
        rel = path.relative_to(PKG).as_posix()
        if rel in ("workers/proforma_worker.py", "pureos/inhouse.py"):
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert offenders == [], f"the in-house units are imported outside the worker: {offenders}"
