"""The proof (execution prompt §9.1): an end-to-end path with nothing seeded.

    pnpm prove                    every step this build holds: 1, 2, 4, 5, 7, 8
    pnpm prove --steps 5,8        the steps named, after the steps they stand on
    pnpm prove --keep             leave the service running at the end, and say where

The service runs on loopback as a host serves it (uvicorn, `openferment_core.api`), on a
database of the proof's own, made on the tests' server (OPENFERMENT_TEST_DATABASE_URL) and
dropped at the end, with a data directory of its own: a proof touches no core/data/ and no
other database. It runs without the model key and makes no model call; steps 3 and 6, which
read the literature and ask Postdoc with a stand-in model, arrive with stages 6 and 8. Every
check prints ✓ or ✗ with what it saw; the proof exits 1 when a check fails, 2 when it cannot
start.

    1  a fresh database, migrated to its head; `ready --offline` green
    2  a project made through the API
    4  the library's plants listed; the cellulosic ethanol reference plant (the package's
       cornstover) run and held to the package's own test within its tolerance, the two values
       the package's own test fails on this installation each held to what the package's code
       measures here (ADR-013); the run's tables, its parameters read back, its versions, and
       an SFF file that validates and scores
    5  openFerment's cellulosic ethanol flowsheet run on the library's own defaults, every
       value `library-default`; A→B→A, the flowsheet replayed identical after another plant
       ran; a scenario with one person's assumption and one model's estimate, run and
       `assumed`; a comparison; a runbook made and locked under the browser's digest; the
       export package (JSON, Markdown, SFF files, versions) opened by the standard library
       alone, with every installed package off the path
    7  one of the toolkit's reference SFF files imported as a flowsheet record; it draws
    8  the service stopped and started again: everything from 2 to 7 reloads from PostgreSQL,
       and the flowsheet's artifact replays within its tolerance
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

import httpx

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
HOST = "127.0.0.1"
SERVER = os.environ.get("OPENFERMENT_TEST_DATABASE_URL", "").strip() or \
    "postgresql://openferment:openferment@127.0.0.1:5432/openferment_test"
PROJECT_HEADER = "X-OpenFerment-Project"
# Who the proof acts as: the person who asks, and the person whose assumption a scenario carries.
BY = "openFerment proof"
PERSON = "Proof Reviewer"
REFERENCE_PLANT = "cornstover"
FLOWSHEET = "cellulosic_ethanol_v0"
# B in A→B→A: another plant, built in the same worker between the two runs of A.
OTHER_PLANT = "sugarcane"
# One of the toolkit's reference SFF files (engine/sff_library.json): Sugarcane → Ethanol.
REFERENCE_FILE = "SF_BST_15"
# The values the package's own test fails on this installation, each with what the package's
# own code measures here (ADR-013), held to the run's ten significant digits.
DEPARTURES = {
    (REFERENCE_PLANT, "tea.installed_equipment_cost"): 192647846.3483623,
    (REFERENCE_PLANT, "units.get_electricity_consumption()"): 20.91491944732716,
}
DIGITS = 10
# A step, and the steps it stands on.
STEPS: dict[int, tuple[int, ...]] = {1: (), 2: (1,), 4: (2,), 5: (2,), 7: (2,), 8: (2,)}
TITLES = {
    1: "a fresh database, migrated; ready green",
    2: "a project made through the API",
    4: "the library's plants; the cellulosic ethanol reference plant held to its package's test",
    5: "the flowsheet on the library's defaults; A→B→A; a scenario, a comparison, a runbook, the export",
    7: "a reference SFF file imported; it draws",
    8: "the service restarted: everything reloads; an artifact replays within its tolerance",
}
RUN_TIMEOUT_S = 1800.0

# Opens the export package with the standard library alone (run with -I -S, from a directory of its own).
READER = '''\
import hashlib, json, sys, zipfile

with zipfile.ZipFile(sys.argv[1]) as z:
    manifest = json.loads(z.read("manifest.json"))
    listed = {f["path"]: f for f in manifest["files"]}
    names = sorted(z.namelist())
    assert names == sorted([*listed, "manifest.json"]), names
    for path, f in listed.items():
        data = z.read(path)
        assert len(data) == f["bytes"] and hashlib.sha256(data).hexdigest() == f["sha256"], path
    study = json.loads(z.read("study.json"))
    versions = json.loads(z.read("versions.json"))
    words = z.read("study.md").decode("utf-8")
    sff = {}
    for p in listed:
        if p.startswith("sff/"):
            json.loads(z.read(p))
            sff[p] = hashlib.sha256(z.read(p)).hexdigest()
ids = [r["id"] for r in study["runs"]] + [s["id"] for s in study["scenarios"]] + \\
      [c["id"] for c in study["comparisons"]] + [b["id"] for b in study["runbooks"]]
print(json.dumps({
    "files": names,
    "runs": [r["id"] for r in study["runs"]],
    "sff": sff,
    "versions": sorted(versions),
    "unnamed": [i for i in ids if i not in words],
    "loaded": sorted(m for m in sys.modules if m.split(".")[0] in ("openferment_core", "pydantic", "httpx")),
    "sitePackages": [p for p in sys.path if "site-packages" in p],
}))
'''


# ── what a proof keeps ─────────────────────────────────────────────────


@dataclass
class Proof:
    origin: str = ""
    database: str = ""
    data_dir: Path = Path()
    project: str = ""
    failed: int = 0
    passed: int = 0
    # What the steps made, for step 8 to reload.
    made: dict[str, Any] = field(default_factory=dict)
    service: subprocess.Popen | None = None
    log: Path = Path()

    def check(self, ok: bool, words: str) -> bool:
        print(f"  {'✓' if ok else '✗'} {words}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        return ok


class Stop(Exception):
    """A step that cannot go on: its words are its last check."""


# ── the database, the service and the API ──────────────────────────────


def on_server(address: str, name: str) -> str:
    parts = urlsplit(address)
    return urlunsplit(parts._replace(path=f"/{name}"))


def migrations(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "openferment_core.migrations", *args], cwd=CORE, text=True,
                          capture_output=True, env={**os.environ, "OPENFERMENT_DATABASE_URL": SERVER})


def free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def environment(proof: Proof, port: int) -> dict[str, str]:
    """The service's environment: the proof's database and data directory, the toolkit's
    reference files fetched into it, and no model key."""
    env = {k: v for k, v in os.environ.items() if k not in ("OPENFERMENT_API_KEY", "ANTHROPIC_API_KEY")}
    return {**env, "OPENFERMENT_DATABASE_URL": on_server(SERVER, proof.database), "OPENFERMENT_DATA_DIR": str(proof.data_dir),
            "OPENFERMENT_SFF_LIBRARY": str(proof.data_dir / "sff-library"), "OPENFERMENT_DIST_DIR": str(ROOT / "dist"),
            "OPENFERMENT_POLL_HOST": HOST, "OPENFERMENT_PORT": str(port)}


def start(proof: Proof) -> None:
    port = free_port()
    proof.origin = f"http://{HOST}:{port}"
    log = proof.log.open("a", encoding="utf-8")
    proof.service = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "openferment_core.api:app", "--host", HOST, "--port", str(port), "--log-level", "warning"],
        cwd=CORE, env=environment(proof, port), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if proof.service.poll() is not None:
            raise Stop(f"the service exited with code {proof.service.returncode}; its log is {proof.log}")
        try:
            if httpx.get(f"{proof.origin}/api/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise Stop(f"the service did not answer /api/health within 120 s; its log is {proof.log}")


def stop(proof: Proof) -> None:
    """The service and every worker it started, stopped."""
    if proof.service is None or proof.service.poll() is not None:
        return
    os.killpg(proof.service.pid, signal.SIGTERM)
    try:
        proof.service.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proof.service.pid, signal.SIGKILL)
        proof.service.wait()


def api(proof: Proof, method: str, path: str, body: Any = None, *, expect: int = 200, project: bool = True,
        timeout: float = 60.0) -> Any:
    headers = {PROJECT_HEADER: proof.project} if project and proof.project else {}
    r = httpx.request(method, f"{proof.origin}{path}", json=body, headers=headers, timeout=timeout)
    if r.status_code != expect:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text[:300]
        raise Stop(f"{method} {path} answered {r.status_code}, not {expect}: {detail}")
    return r.content if r.headers.get("content-type", "").startswith("application/zip") else (r.json() if r.content else None)


def within_digits(a: float, b: float, digits: int = DIGITS) -> bool:
    return abs(a - b) <= 10.0 ** (1 - digits) * max(abs(a), abs(b))


# ── the steps ──────────────────────────────────────────────────────────


def step_1(proof: Proof) -> None:
    made = migrations("reset", proof.database)
    said = (made.stdout + made.stderr).strip().splitlines()
    if not proof.check(made.returncode == 0, f"database {proof.database} made on the tests' server: {said[-1] if said else ''}"):
        raise Stop("no database to prove on")
    from openferment_core.migrations import at_head

    revisions = at_head(on_server(SERVER, proof.database))
    proof.check(all(at == head for at, head in revisions.values()),
                "migrated to the head of each schema: " + ", ".join(f"{schema} at {at} of {head}" for schema, (at, head) in revisions.items()))
    start(proof)
    proof.check(True, f"the service answers at {proof.origin}, on its own database and data directory")
    ready = subprocess.run([sys.executable, "-m", "openferment_core.ready", "--offline"], cwd=CORE, text=True,
                           capture_output=True, env=environment(proof, int(proof.origin.rsplit(":", 1)[1])), timeout=600)
    lines = ready.stdout.strip().splitlines()
    failed = [line for line in lines if line.startswith("✗")]
    proof.check(ready.returncode == 0, "ready green (--offline: no network, no key): " + (
        "every row passes or warns" if ready.returncode == 0 else "; ".join(failed) or ready.stderr.strip()[-300:]))


def step_2(proof: Proof) -> None:
    made = api(proof, "POST", "/api/projects", {"name": "Proof", "description": "made by scripts/prove.py", "by": BY},
               expect=201, project=False)
    proof.project = made["id"]
    proof.made["project"] = made["id"]
    listed = api(proof, "GET", "/api/projects", project=False)
    proof.check(any(p["id"] == proof.project for p in listed), f"project {proof.project} made through the API and listed")


def step_4(proof: Proof) -> None:
    shelf = api(proof, "GET", "/api/library")
    plants = {p["id"]: p for p in shelf["plants"]}
    proof.check(REFERENCE_PLANT in plants and FLOWSHEET in plants,
                f"the library lists {len(plants)} plants under {shelf['package']} and {shelf['simulator']}, "
                f"{REFERENCE_PLANT} and {FLOWSHEET} among them")
    rep = api(proof, "POST", f"/api/library/{REFERENCE_PLANT}/run", {"by": BY}, timeout=RUN_TIMEOUT_S)
    run, art = rep["run"], rep["artifact"]
    proof.made["reference"] = run["id"]
    if not proof.check(run["status"] == "done" and art is not None,
                       f"{REFERENCE_PLANT} run {run['id']}: {run['status']}, {run['provenance']}"):
        raise Stop("the reference plant did not run")
    checks = art["output"].get("checks") or []
    within = [c for c in checks if c["within"]]
    outside = [c for c in checks if not c["within"]]
    held = [c for c in outside if (REFERENCE_PLANT, c["expression"]) in DEPARTURES
            and c["measured"] is not None and within_digits(c["measured"], DEPARTURES[(REFERENCE_PLANT, c["expression"])])]
    stray = [c for c in outside if c not in held]
    proof.check(bool(checks) and not stray,
                f"held to the package's own test: {len(within)} of {len(checks)} within its tolerance"
                + (f"; {len(held)} outside it as the package's own test is on this installation (ADR-013): "
                   + ", ".join(f"{c['expression']} {c['measured']:.10g} against {c['package']:.10g}" for c in held) if held else "")
                + (f"; outside and not the package's own measurement: "
                   + ", ".join(f"{c['expression']} {c['measured']} against {c['package']}" for c in stray) if stray else ""))
    o = art["output"]
    proof.check(bool(o.get("streams")) and bool(o.get("units")) and o.get("tea") is not None,
                f"its tables: {len(o.get('streams') or [])} streams, {len(o.get('units') or [])} units, the TEA's breakdown")
    proof.check(bool(o.get("parameters")) and bool(rep.get("parameters")),
                f"its {len(o.get('parameters') or [])} parameters read back from the plant, each with its origin")
    v = run["versions"]
    proof.check(all(k in v for k in ("biosteam", "thermosteam", "biorefineries")),
                "its versions: " + ", ".join(f"{k} {v[k]}" for k in sorted(v)))
    s = run.get("sff") or {}
    proof.check(bool(s.get("valid")) and isinstance(s.get("score"), (int, float)) and 0 < s["score"] <= 1,
                f"its SFF file {s.get('recordId')}: {'valid' if s.get('valid') else 'not valid'}, scored {s.get('score')}"
                + (f"; refused: {run.get('sffRefused')}" if run.get("sffRefused") else ""))


def step_5(proof: Proof) -> None:
    from openferment_core import llm
    from openferment_core.runbook_lock import lock_hash

    a = api(proof, "POST", f"/api/library/{FLOWSHEET}/run", {"by": BY}, timeout=RUN_TIMEOUT_S)
    run_a = a["run"]
    proof.made["flowsheet"] = run_a["id"]
    values = (a.get("parameters") or {}).get("values") or []
    kinds = sorted({i["quantity"]["origin"]["kind"] for i in run_a["inputs"]})
    proof.check(run_a["status"] == "done" and run_a["provenance"] == "computed" and bool(values)
                and all(v["origin"] == "library-default" for v in values) and set(kinds) <= {"library-default", "convention"},
                f"{FLOWSHEET} run {run_a['id']} on the library's own defaults: {run_a['provenance']}, each of its "
                f"{len(values)} parameters library-default, its inputs {' and '.join(kinds)}")
    b = api(proof, "POST", f"/api/library/{OTHER_PLANT}/run", {"by": BY}, timeout=RUN_TIMEOUT_S)
    proof.made["other"] = b["run"]["id"]
    again = api(proof, "POST", f"/api/biorepo/artifacts/{run_a['artifactId']}/replay", timeout=RUN_TIMEOUT_S)
    proof.check(again["identical"], f"A→B→A: {FLOWSHEET}, then {OTHER_PLANT}, then {FLOWSHEET} replayed: "
                + ("identical" if again["identical"] else
                   f"not identical ({len(again['differences'])} differences, within its tolerance: {again['withinTolerance']})"))

    estimate = llm.DEFAULT_PRIMARY
    scenario = api(proof, "POST", "/api/studies/scenarios", {
        "title": "Dearer stover, two-day co-fermentation", "plant": FLOWSHEET, "by": PERSON,
        "note": "one person's assumption and one model's estimate, as the proof plants them",
        "values": [
            {"key": "stream.cornstover.price", "quantity": {"value": 0.08, "unit": "USD/kg", "origin": {
                "kind": "person-assumption", "by": PERSON, "at": "2026-10-30", "note": "a delivered price quoted to us"}}},
            {"key": "unit.R303.tau_cofermentation", "quantity": {"value": 48.0, "unit": "hr", "origin": {
                "kind": "model-estimate", "by": estimate, "at": "2026-10-30T12:00:00Z",
                "note": "two days, as such plants are often run"}}},
        ]})
    proof.made["scenario"] = scenario["id"]
    s = api(proof, "POST", f"/api/studies/scenarios/{scenario['id']}/run", {"by": PERSON}, timeout=RUN_TIMEOUT_S)
    run_s = s["run"]
    proof.made["scenarioRun"] = run_s["id"]
    origins = {i["name"]: i["quantity"]["origin"] for i in run_s["inputs"]}
    proof.check(run_s["status"] == "done" and run_s["provenance"] == "assumed" and run_s["scenarioId"] == scenario["id"]
                and origins.get("stream.cornstover.price", {}).get("kind") == "person-assumption"
                and origins.get("unit.R303.tau_cofermentation", {}).get("kind") == "model-estimate",
                f"scenario {scenario['id']} run {run_s['id']}: {run_s['provenance']}, its price a person's assumption "
                f"by {PERSON}, its residence time a model's estimate by {estimate}")

    compared = api(proof, "POST", "/api/studies/comparisons", {
        "title": "The scenario against the flowsheet as built", "runIds": [run_a["id"], run_s["id"]], "by": PERSON})
    c = compared["comparison"]
    proof.made["comparison"] = c["id"]
    rows = {r["key"]: r for r in compared["artifact"]["output"]["rows"]}
    mesp = rows.get("outputs.mespUsdPerKg")
    proof.check(c["provenance"] == "assumed" and mesp is not None and mesp["unit"] == "USD/kg",
                f"comparison {c['id']}: {c['provenance']}, the selling price "
                + (f"{mesp['values'][0]:.4g} to {mesp['values'][1]:.4g} {mesp['unit']} ({mesp['change'][1]:+.1%})" if mesp else "missing"))

    book = api(proof, "POST", "/api/studies/runbooks", {
        "title": "Dearer stover at the bench", "runId": run_s["id"], "by": PERSON,
        "predict": [{"output": "outputs.mespUsdPerKg", "label": "Minimum ethanol selling price"}]})
    locked = api(proof, "POST", f"/api/studies/runbooks/{book['id']}/lock", {"by": PERSON})
    proof.made["runbook"] = (locked["id"], locked.get("lockedAt"), locked.get("lockHash"))
    digest = lock_hash(locked["predictions"], locked["measurementSchema"])
    proof.check(bool(locked.get("lockedAt")) and locked.get("lockHash") == digest
                and locked["predictions"][0]["value"] == mesp["values"][1] and locked["predictions"][0]["unit"] == "USD/kg",
                f"runbook {locked['id']} predicting the scenario's selling price, locked under {locked.get('lockHash')}, "
                "the digest the browser's lock.ts writes")
    refused = httpx.post(f"{proof.origin}/api/studies/runbooks/{book['id']}/lock", json={"by": PERSON},
                         headers={PROJECT_HEADER: proof.project}, timeout=60)
    proof.check(refused.status_code == 422, f"a second lock refused: {refused.status_code}, {refused.json().get('detail', '')[:90]}")

    package = api(proof, "GET", f"/api/studies/export?by={PERSON}")
    where = proof.data_dir / "export"
    for d in ("package", "reader", "empty"):
        (where / d).mkdir(parents=True, exist_ok=True)
    (where / "package" / "studies.zip").write_bytes(package)
    (where / "reader" / "open_export.py").write_text(READER, encoding="utf-8")
    opened = subprocess.run([sys.executable, "-I", "-S", str(where / "reader" / "open_export.py"),
                             str(where / "package" / "studies.zip")], cwd=where / "empty", capture_output=True, text=True, timeout=120)
    if not proof.check(opened.returncode == 0, f"the export package ({len(package)} bytes) opened by the standard library alone"
                       + ("" if opened.returncode == 0 else f": {opened.stderr.strip()[-300:]}")):
        return
    seen = json.loads(opened.stdout)
    proof.check(seen["loaded"] == [] and seen["sitePackages"] == [],
                "with every installed package off the path, and nothing of openFerment's loaded")
    files = sorted(set(seen["files"]) - {p for p in seen["files"] if p.startswith("sff/")})
    proof.check(files == ["manifest.json", "study.json", "study.md", "versions.json"] and seen["unnamed"] == [],
                f"it holds {', '.join(files)} and {len(seen['sff'])} SFF files; study.md names every run, scenario, "
                "comparison and runbook, and each file has the size and sha256 its manifest gives")
    held = {}
    for run_id in seen["runs"]:
        rec = api(proof, "GET", f"/api/runs/{run_id}")
        if rec.get("flowsheet"):
            held[f"sff/{run_id}.sff.json"] = rec["flowsheet"]["sha256"]
    proof.check(seen["sff"] == held, f"each run's SFF file in it is the project's, byte for byte ({len(held)} files)")


def step_7(proof: Proof) -> None:
    listed = api(proof, "GET", "/api/flowsheets/library")
    entry = next((f for f in listed if f["id"] == REFERENCE_FILE), None)
    if not proof.check(entry is not None, f"the toolkit's reference files listed: {len(listed)}, {REFERENCE_FILE} among them"):
        raise Stop("no reference file to import")
    record = api(proof, "POST", f"/api/flowsheets/library/{REFERENCE_FILE}", {"by": BY}, timeout=300)
    proof.made["flowsheetRecord"] = record["id"]
    proof.check(record["origin"] == "library" and record["sha256"] == entry["sha256"],
                f"{REFERENCE_FILE} ({entry['title']}) imported as record {record['id']}, origin {record['origin']}, "
                f"its sha256 the manifest's")
    drawn = api(proof, "GET", f"/api/flowsheets/{record['id']}")
    g = drawn.get("graph") or {}
    proof.check(bool(g.get("nodes")) and bool(g.get("edges")),
                f"it draws: {len(g.get('nodes') or [])} units, {len(g.get('edges') or [])} streams between them, "
                f"{len(g.get('feeds') or [])} feeds and {len(g.get('products') or [])} products; "
                f"{'valid' if drawn['validation']['valid'] else 'not valid'} against SFF {drawn['validation']['schemaVersion']}")


def step_8(proof: Proof) -> None:
    stop(proof)
    proof.check(proof.service is not None and proof.service.poll() is not None, "the service stopped, its workers with it")
    start(proof)
    proof.check(True, f"the service started again at {proof.origin} on the same database")
    m = proof.made
    projects = api(proof, "GET", "/api/projects", project=False)
    proof.check(any(p["id"] == m.get("project") for p in projects), f"project {m.get('project')} reloads")
    runs = {r["id"]: r for r in api(proof, "GET", "/api/runs")}
    want = [m[k] for k in ("reference", "flowsheet", "other", "scenarioRun") if k in m]
    proof.check(all(r in runs for r in want), f"its {len(runs)} engine runs reload: {', '.join(want)}")
    if "scenario" in m:
        held = {s["id"]: s for s in api(proof, "GET", "/api/studies/scenarios")}
        proof.check(m["scenario"] in held and held[m["scenario"]]["runIds"] == [m["scenarioRun"]],
                    f"scenario {m['scenario']} reloads with its run")
    if "comparison" in m:
        c = api(proof, "GET", f"/api/studies/comparisons/{m['comparison']}")
        proof.check(c["comparison"]["provenance"] == "assumed" and c["artifact"]["id"] == m["comparison"],
                    f"comparison {m['comparison']} reloads with its artifact")
    if "runbook" in m:
        rid, at, digest = m["runbook"]
        b = api(proof, "GET", f"/api/studies/runbooks/{rid}")
        locks = api(proof, "GET", "/api/state")["runbookLocks"]
        proof.check(b.get("lockedAt") == at and b.get("lockHash") == digest and locks.get(rid, {}).get("lockHash") == digest,
                    f"runbook {rid} reloads locked under {digest}")
    records = {f["id"] for f in api(proof, "GET", "/api/flowsheets")}
    want = [m["flowsheetRecord"]] if "flowsheetRecord" in m else []
    want += [f"run-{m[k]}" for k in ("reference", "flowsheet") if k in m]
    proof.check(all(r in records for r in want), f"its {len(records)} flowsheet records reload: {', '.join(want)}")
    target = m.get("flowsheet") or m.get("reference")
    if target:
        again = api(proof, "POST", f"/api/biorepo/artifacts/{target}/replay", timeout=RUN_TIMEOUT_S)
        proof.check(again["withinTolerance"], f"artifact {target} replays after the restart: "
                    + ("identical" if again["identical"] else
                       f"within its tolerance: {again['withinTolerance']} ({len(again['differences'])} differences)"))


RUNNERS: dict[int, Callable[[Proof], None]] = {1: step_1, 2: step_2, 4: step_4, 5: step_5, 7: step_7, 8: step_8}


def order(asked: list[int]) -> list[int]:
    out: list[int] = []

    def add(n: int) -> None:
        for d in STEPS[n]:
            add(d)
        if n not in out:
            out.append(n)

    for n in sorted(asked):
        add(n)
    # Step 8 reloads what the others made, so it runs last.
    return sorted(out, key=lambda n: (n == 8, n))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="pnpm prove", description=__doc__.split("\n\n")[0])
    parser.add_argument("--steps", default=",".join(str(n) for n in STEPS), help="the steps to prove, e.g. 5,8")
    parser.add_argument("--keep", action="store_true", help="leave the service and its database at the end")
    args = parser.parse_args(argv)
    try:
        asked = [int(x) for x in args.steps.split(",") if x.strip()]
    except ValueError:
        parser.error("--steps names steps by number, e.g. 5,8")
    unknown = [n for n in asked if n not in STEPS]
    if unknown:
        parser.error(f"this build proves steps {', '.join(map(str, STEPS))}; not {', '.join(map(str, unknown))}")
    proof = Proof(database=f"openferment_proof_{os.urandom(4).hex()}", data_dir=Path(tempfile.mkdtemp(prefix="openferment-proof-")))
    proof.log = proof.data_dir / "service.log"
    print(f"openFerment proof: steps {', '.join(map(str, order(asked)))} on database {proof.database}\n")
    started = time.monotonic()
    try:
        for n in order(asked):
            print(f"── {n}  {TITLES[n]}")
            t0 = time.monotonic()
            try:
                RUNNERS[n](proof)
            except Stop as e:
                proof.check(False, str(e))
                if n in (1, 2):
                    break
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as e:
                proof.check(False, f"step {n} stopped: {type(e).__name__}: {e}")
            print(f"  ({time.monotonic() - t0:.0f} s)\n")
    finally:
        if args.keep and proof.service is not None and proof.service.poll() is None:
            print(f"kept: the service at {proof.origin} (project {proof.project}), database {proof.database}, "
                  f"data {proof.data_dir}; stop it with kill -TERM -{proof.service.pid}")
        else:
            stop(proof)
            dropped = migrations("drop", proof.database)
            if dropped.returncode != 0:
                print(f"(database {proof.database} was left behind: {(dropped.stderr or dropped.stdout).strip()[-200:]})")
    print(f"{proof.passed + proof.failed} checks in {time.monotonic() - started:.0f} s: "
          + (f"{proof.failed} failed. The service's log: {proof.log}" if proof.failed else "every one holds."))
    return 1 if proof.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
