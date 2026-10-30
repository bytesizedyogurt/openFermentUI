"""The proof (execution prompt §9.1): an end-to-end path with nothing seeded.

    pnpm prove                    every step: 1 to 9
    pnpm prove --steps 5,8        the steps named, after the steps they stand on
    pnpm prove --keep             leave the service running at the end, and say where
    pnpm prove --live             with the key in core/.env and the network: step 3 collects the
                                  ethanol sources (docs/corpus/ethanol-sources.txt) and the routed
                                  model extracts a paper; step 6 asks the routed models; every step
                                  but the walk, unless --steps names it. It spends, under the cap

The service runs on loopback as a host serves it (uvicorn, `openferment_core.api`), on a
database of the proof's own, made on the tests' server (OPENFERMENT_TEST_DATABASE_URL) and
dropped at the end, with a data directory of its own: a proof touches no core/data/ and no
other database. It runs without the model key and makes no model call, and in fixture mode,
so its collectors refuse the network: step 3's extraction reads a stand-in's written response
where it would call a model, and step 6 asks Postdoc through its evaluation's offline stand-in.
Its last check reads the proof's own spend table: offline it holds no call. Every check prints ✓
or ✗ with what it saw; the proof exits 1 when a check fails, 2 when it cannot start.

    1  a fresh database, migrated to its head; `ready --offline` green
    2  a project made through the API
    3  Sci RAG Kit's demo corpus (five fictional documents, CC0) taken in through Intake's upload:
       its documents, chunks and embeddings held by the project; a search in words for each of the
       kit's seed questions answered by the passage that holds it, with its citation; a stand-in's
       candidate extracted through the service and anchored to the stored text, its second,
       quoting words the document does not hold, refused; a decision carrying a model's estimate
       refused at the record store; a person's decision accepting the candidate, and the record in
       BioRepo with its status, provenance and reviewer
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
    6  Postdoc on the project, its evaluation set asked offline through the service's answer
       path with the evaluation's stand-in model: a run's selling price cited by evidence id; a
       scenario of a labelled estimate proposed, run and explained by the run's artifact id; a
       claim with a bare number dropped and counted; the follow-up asked in the same
       conversation, reading its history from the service; each turn and its tool calls on the
       service, and each question scored and kept
    7  one of the toolkit's reference SFF files imported as a flowsheet record; it draws
    8  the service stopped and started again: everything from 2 to 7 reloads from PostgreSQL,
       and the flowsheet's artifact replays within its tolerance
    9  the UI walk (scripts/walk.ts, Chromium): Home, the project at its own address with its
       live trace, a document pasted in and searched, the flowsheet run's report and its SFF
       graph, the conversation of step 6 with its estimate marked, the runbook of step 5
"""
from __future__ import annotations

import argparse
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
# Sci RAG Kit's demo corpus (five fictional documents, CC0), and the one the extraction reads.
DEMO = CORE / "tests" / "fixtures" / "kit-demo"
DEMO_LICENCE = "CC0, as the manifest of Sci RAG Kit's demo corpus states (core/tests/fixtures/kit-demo/manifest.jsonl)"
POLICY = "Demo Region Policy Landscape for Agricultural Residue Utilization"
# Live: the ethanol sources (docs/corpus/ethanol-sources.txt), a question in words over them, and the paper
# the routed model extracts.
SOURCES = ROOT / "docs" / "corpus" / "ethanol-sources.txt"
LIVE_QUESTION = "ethanol yield of Saccharomyces cerevisiae on glucose"
LIVE_PAPER = "PMC4842200"
# How long a live proof waits before asking a source again that asked it to slow down.
RETRY_AFTER_S = 120.0
KEY_FILE = CORE / ".env"
# The values the package's own test fails on this installation, each with what the package's
# own code measures here (ADR-013), held to the run's ten significant digits.
DEPARTURES = {
    (REFERENCE_PLANT, "tea.installed_equipment_cost"): 192647846.3483623,
    (REFERENCE_PLANT, "units.get_electricity_consumption()"): 20.91491944732716,
}
DIGITS = 10
# A step, and the steps it stands on.
STEPS: dict[int, tuple[int, ...]] = {1: (), 2: (1,), 3: (2,), 4: (2,), 5: (2,), 6: (2,), 7: (2,), 8: (2,), 9: (5, 6)}
TITLES = {
    1: "a fresh database, migrated; ready green",
    2: "a project made through the API",
    3: "documents taken in, embedded and searched; a candidate extracted, anchored and accepted; the record in "
       "BioRepo",
    4: "the library's plants; the cellulosic ethanol reference plant held to its package's test",
    5: "the flowsheet on the library's defaults; A→B→A; a scenario, a comparison, a runbook, the export",
    6: "Postdoc: its evaluation set asked through the service's answer path and scored by code; a follow-up reads "
       "its history",
    7: "a reference SFF file imported; it draws",
    8: "the service restarted: everything reloads; an artifact replays within its tolerance",
    9: "the UI walk: Home, the project, ingest, search, a run report and its SFF graph, a conversation, a runbook",
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
    # Live: the key in core/.env, the network, the routed models (--live).
    live: bool = False
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
    # Live, the service reads the key from core/.env as a host's does. Offline, an empty key stands over
    # core/.env's (which the service loads without overriding what is set), the collectors refuse the
    # network, and the extract route reads a written response from the proof's own fixtures (step 3)
    # where it would call a model.
    mode = {} if proof.live else {"ANTHROPIC_API_KEY": "", "OPENFERMENT_FIXTURES": "1",
                                  "OPENFERMENT_FIXTURE_DIR": str(proof.data_dir / "fixtures")}
    return {**env, **mode,
            "OPENFERMENT_DATABASE_URL": on_server(SERVER, proof.database), "OPENFERMENT_DATA_DIR": str(proof.data_dir),
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
    ready = subprocess.run([sys.executable, "-m", "openferment_core.ready", *([] if proof.live else ["--offline"])],
                           cwd=CORE, text=True, capture_output=True,
                           env=environment(proof, int(proof.origin.rsplit(":", 1)[1])), timeout=600)
    lines = ready.stdout.strip().splitlines()
    failed = [line for line in lines if line.startswith("✗")]
    proof.check(ready.returncode == 0, ("ready green, the key and the model routes among its rows: " if proof.live else
                                        "ready green (--offline: no network, no key): ") + (
        "every row passes or warns" if ready.returncode == 0 else "; ".join(failed) or ready.stderr.strip()[-300:]))


def step_2(proof: Proof) -> None:
    made = api(proof, "POST", "/api/projects", {"name": "Proof", "description": "made by scripts/prove.py", "by": BY},
               expect=201, project=False)
    proof.project = made["id"]
    proof.made["project"] = made["id"]
    listed = api(proof, "GET", "/api/projects", project=False)
    proof.check(any(p["id"] == proof.project for p in listed), f"project {proof.project} made through the API and listed")


def upload(proof: Proof, path: Path, row: dict[str, Any]) -> dict[str, Any]:
    """One file through Intake's upload, as a person uploads it."""
    r = httpx.post(f"{proof.origin}/api/intake/upload", headers={PROJECT_HEADER: proof.project}, timeout=600,
                   files={"file": (path.name, path.read_bytes(), "text/markdown")},
                   data={"by": PERSON, "title": row["title"], "licenceClass": row["license_class"],
                         "licence": DEMO_LICENCE, "reason": "Sci RAG Kit's demo corpus, for the proof"})
    if r.status_code != 200:
        raise Stop(f"POST /api/intake/upload answered {r.status_code} for {path.name}: {r.text[:300]}")
    return r.json()


def demo_rows(name: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (DEMO / name).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def documents_held(proof: Proof, want: int) -> dict[str, dict[str, Any]]:
    """The project's documents by title, checked with their chunks and embeddings."""
    docs = {d["title"]: d for d in api(proof, "GET", "/api/literature/documents")}
    stats = api(proof, "GET", "/api/literature/stats")
    embedded = sum((stats.get("embedding_versions") or {}).values())
    proof.check(len(docs) == want and all(d["chunks"] > 0 for d in docs.values()) and stats["documents"] == want
                and stats["chunks"] > 0 and embedded == stats["chunks"],
                f"the project holds {stats['documents']} documents in {stats['chunks']} chunks, every chunk embedded: "
                + ", ".join(f"{v} by {k}" for k, v in (stats.get("embedding_versions") or {}).items()))
    return docs


def accept(proof: Proof, record_id: str, quote: str) -> None:
    """A person's decision accepting a candidate, and the record as BioRepo holds it."""
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    decided = api(proof, "POST", "/api/biorepo/decisions", {"status": "verified", "provenance": "curated",
                                                            "reviewer": PERSON, "recordId": record_id, "at": at})
    held = api(proof, "GET", "/api/biorepo/overlay")
    record = held["records"].get(record_id) or {}
    candidate = next((c for c in held["candidates"] if c["id"] == record_id), {})
    proof.check(decided["status"] == "verified" and record.get("status") == "verified"
                and record.get("reviewer") == PERSON and candidate.get("quote") == quote,
                f"{PERSON} accepted it: record {record_id} in BioRepo, {record.get('status')}, "
                f"{record.get('provenance')}, decided by {record.get('reviewer')}, on \"{candidate.get('quote')}\"")
    proof.made["record"] = (record_id, record.get("status"), record.get("provenance"))


def step_3_live(proof: Proof) -> None:
    """Live: the ethanol sources collected over the network, a paper extracted by the routed model."""
    sources = [line.split("#", 1)[0].strip() for line in SOURCES.read_text(encoding="utf-8").splitlines()]
    sources = [s for s in sources if s]
    def collect(identifier: str) -> dict[str, Any]:
        return api(proof, "POST", "/api/intake/collect", {"identifier": identifier, "by": PERSON,
                                                          "reason": "the ethanol sources, for the live proof"},
                   timeout=600)

    outcomes = [collect(s) for s in sources]
    # A failure that was the network's condition (a source asking to slow down) is asked again once, later.
    again = [n for n, o in enumerate(outcomes) if o["status"] == "failed" and o.get("transient")]
    if again:
        time.sleep(RETRY_AFTER_S)
        for n in again:
            outcomes[n] = collect(sources[n])
    failed = [f"{o['identifier']} ({o.get('reason')})" for o in outcomes if o["status"] == "failed"]
    proof.check(not failed, f"the ethanol sources collected through Intake: {len(sources) - len(failed)} of "
                f"{len(sources)} ({SOURCES.relative_to(ROOT)})" + (f", {len(again)} asked again after the network's "
                                                                   "condition" if again else "")
                + (f"; not collected: {', '.join(failed)}" if failed else ""))
    docs = documents_held(proof, len(sources) - len(failed))
    hits = httpx.get(f"{proof.origin}/api/literature/search", params={"q": LIVE_QUESTION, "topK": 5},
                     headers={PROJECT_HEADER: proof.project}, timeout=120).json()["hits"]
    held = {d["documentId"] for d in docs.values()}
    proof.check(bool(hits) and all(h["citation"] and h["passageId"] and h["documentId"] in held for h in hits),
                f"a search in words (\"{LIVE_QUESTION}\"): {len(hits)} passages of the project's documents, each with "
                "its passage id and citation")
    paper = next((o for o in outcomes if o["identifier"].upper() == LIVE_PAPER and o.get("documentId")), None)
    if not proof.check(paper is not None, f"{LIVE_PAPER} held to extract"):
        raise Stop("no paper to extract")
    got = api(proof, "POST", f"/api/intake/{paper['documentId']}/extract?force=true", timeout=900)
    sections = {s["id"]: s["text"] for s in api(proof, "GET", "/api/biorepo/overlay")["papers"][paper["documentId"]]["sections"]}
    kept = got["candidates"]
    anchored = [c for c in kept if c["quote"] in sections.get(c["sectionId"] or "", "")]
    proof.check(bool(kept) and len(anchored) == len(kept) and got["usage"]["models"] and got["usage"]["costUsd"] > 0,
                f"{LIVE_PAPER} extracted by {', '.join(got['usage']['models'])} through the service for "
                f"${got['usage']['costUsd']:.4f}: {len(kept)} candidates kept, each quote verbatim in the passage it "
                f"names; {got['rejected']} refused by the anchoring rules")
    if not kept:
        raise Stop("no candidate to decide on")
    accept(proof, kept[0]["id"], kept[0]["quote"])
    proof.made["documents"] = sorted(held)


def step_3(proof: Proof) -> None:
    from openferment_core.postdoc.evaluate import STANDIN

    if proof.live:
        return step_3_live(proof)
    rows = demo_rows("manifest.jsonl")
    stored = [upload(proof, DEMO / row["path"], row) for row in rows]
    proof.check(len(stored) == len(rows) and all(s["status"] == "ingested" and s.get("documentId") for s in stored),
                f"the kit's demo corpus taken in through Intake's upload: {len(rows)} documents, each "
                + ", ".join(sorted({s['status'] for s in stored})))
    docs = documents_held(proof, len(rows))
    proof.check(set(docs) == {r["title"] for r in rows}, "each by the title its manifest row gives")
    asked = [q for q in demo_rows("eval_seed_questions.jsonl") if "unanswerable" not in q.get("tags", [])]
    found, cited = 0, True
    for q in asked:
        hits = httpx.get(f"{proof.origin}/api/literature/search", params={"q": q["question"], "topK": 5},
                         headers={PROJECT_HEADER: proof.project}, timeout=120).json()["hits"]
        cited &= bool(hits) and all(h["citation"] and h["passageId"] for h in hits)
        phrases = [p.lower() for p in q["evidence_phrases"]]
        found += any(h["title"] in q["reference_titles"] and any(p in h["text"].lower() for p in phrases) for h in hits)
    proof.check(cited and found >= 0.8 * len(asked),
                f"a search in words for each of the kit's {len(asked)} seed questions: {found} answered by a passage "
                "of the document that holds the answer in the top five, every hit with its passage id and citation")

    # The extraction, offline: the service is in fixture mode, so the extract route reads the response the
    # stand-in wrote for the document in place of a model's, and anchors it by its own rules. The demo corpus
    # is about agricultural residues and holds no fermentation value: the field is chosen for the mechanics
    # alone, and the record is the proof's, dropped with its database.
    title, words = POLICY, "a target decision time of 120 days"
    document_id = docs[title]["documentId"]
    papers = api(proof, "GET", "/api/biorepo/overlay")["papers"]
    where = next((s["id"] for s in papers[document_id]["sections"] if words in s["text"]), None)
    if not proof.check(where is not None, f"{title}: the words the stand-in quotes stand in its passage {where}"):
        raise Stop("no passage to anchor to")
    named = {"sectionId": where, "field": "time_to_colony", "value": 120, "unit": "d", "isPrimary": True,
             "confidence": 0.9}
    response = {"_note": f"The proof's stand-in extractor ({STANDIN}), written by scripts/prove.py: no model "
                         "answered.",
                "raw": {"candidates": [{**named, "quote": words},
                                       {**named, "value": 90, "quote": "a target decision time of 90 days"}]},
                "usage": {"models": [STANDIN]}}
    (proof.data_dir / "fixtures" / "extract").mkdir(parents=True, exist_ok=True)
    (proof.data_dir / "fixtures" / "extract" / f"{document_id}.json").write_text(json.dumps(response), encoding="utf-8")
    got = api(proof, "POST", f"/api/intake/{document_id}/extract?force=true", timeout=300)
    kept = got["candidates"]
    proof.check(len(kept) == 1 and (kept[0]["paperId"], kept[0]["sectionId"], kept[0]["quote"]) == (document_id, where, words)
                and got["usage"]["models"] == [STANDIN],
                f"extracted through the service: candidate {kept[0]['id'] if kept else None} anchored to passage {where} "
                f"of the stored text, in its words \"{words}\"")
    proof.check(got["rejected"] == 1 and got["rejectionReasons"].get("quote") == 1,
                f"the stand-in's second candidate, quoting words the document does not hold, refused: "
                f"{got['rejected']} refused, by rule {', '.join(k for k, v in got['rejectionReasons'].items() if v)}")
    if not kept:
        raise Stop("no candidate to decide on")
    record_id = kept[0]["id"]
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    estimate = {"value": 120, "unit": "d", "origin": {"kind": "model-estimate", "by": STANDIN, "at": at}}
    asked_with = api(proof, "POST", "/api/biorepo/check", {"status": "verified", "provenance": "curated",
                                                           "reviewer": PERSON, "recordId": record_id, "at": at,
                                                           "gold": estimate})
    proof.check(asked_with["ok"] is False and asked_with["rule"] == "estimate",
                f"a decision carrying a model's estimate as its value refused at the record store: rule "
                f"{asked_with['rule']}")
    accept(proof, record_id, words)
    proof.made["documents"] = sorted(d["documentId"] for d in docs.values())


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
                + ("; outside and not the package's own measurement: "
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


def evaluation(proof: Proof, *args: str) -> dict[str, Any]:
    """`python -m openferment_core.evaluation` in the proof's project and database, its JSON."""
    env = {**environment(proof, int(proof.origin.rsplit(":", 1)[1])), "OPENFERMENT_PROJECT": proof.project}
    done = subprocess.run([sys.executable, "-m", "openferment_core.evaluation", *args], cwd=CORE, text=True,
                          capture_output=True, env=env, timeout=RUN_TIMEOUT_S)
    if done.returncode != 0:
        raise Stop(f"evaluation {' '.join(args)} exited {done.returncode}: {(done.stderr or done.stdout).strip()[-400:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def step_6_live(proof: Proof) -> None:
    """Live: the evaluation set asked of the routed models, each answer scored by code."""
    from openferment_core.postdoc import evaluate

    report = evaluation(proof, "run", "--live")
    runs = {r["questionId"]: r for r in report["runs"]}
    price, dearer = runs.get("eq-price"), runs.get("eq-dearer")
    if price is None or dearer is None:
        raise Stop(f"the evaluation answered {', '.join(runs) or 'nothing'}, not both questions")
    models = sorted({m for r in runs.values() for m in r["models"]})
    proof.check(all(r["mode"] == "live" for r in runs.values()) and bool(models) and evaluate.STANDIN not in models,
                f"asked live, through the service's answer path, of {', '.join(models)}")
    turns = api(proof, "GET", f"/api/conversations/{price['conversationId']}")["turns"]
    declined = [str((t.get("plan") or {}).get("declined"))[:200] for t in turns if (t.get("plan") or {}).get("declined")]
    proof.check(dearer["conversationId"] == price["conversationId"] and len(turns) == 2
                and all(t["status"] == "answered" for t in turns) and not declined,
                f"both questions answered in conversation {price['conversationId']}, the follow-up reading its history "
                f"from the service" + (f"; declined: {' | '.join(declined)}" if declined else ""))
    proof.check(all(set(r["scores"]) == {"tools", "citations", "estimates", "bareNumbers"} for r in runs.values()),
                "each answer scored by code and kept: " + "; ".join(
                    f"{q} {r['scores']}, {r['claims']} claims kept, {r['droppedForNumbers']} dropped for a number"
                    for q, r in runs.items()))
    proof.made["conversation"] = dearer["conversationId"]


def step_6(proof: Proof) -> None:
    from openferment_core.postdoc import evaluate

    seeded = evaluation(proof, "seed")["seeded"]
    proof.check(seeded == ["eq-price", "eq-dearer"], f"the evaluation set kept in the project as rows: {', '.join(seeded)}")
    if proof.live:
        return step_6_live(proof)
    report = evaluation(proof, "run")
    runs = {r["questionId"]: r for r in report["runs"]}
    price, dearer = runs.get("eq-price"), runs.get("eq-dearer")
    if price is None or dearer is None:
        raise Stop(f"the evaluation answered {', '.join(runs) or 'nothing'}, not both questions")
    proof.check(all(r["mode"] == "offline" and r["models"] == [evaluate.STANDIN] for r in runs.values()),
                f"asked offline, through the service's answer path, of the stand-in {evaluate.STANDIN}; no model key")
    proof.check(price["scores"] == {"tools": 1.0, "citations": 1.0, "estimates": 1.0, "bareNumbers": 1.0}
                and price["claims"] == 1,
                f"{OTHER_PLANT}'s selling price: a claim kept, citing the run by evidence id; scored {price['scores']}")
    turns = api(proof, "GET", f"/api/conversations/{price['conversationId']}")["turns"]
    proof.check(dearer["conversationId"] == price["conversationId"] and [t["status"] for t in turns] == ["answered"] * 2
                and report["followUps"].get("eq-dearer") is True,
                f"the follow-up asked in conversation {price['conversationId']}: both turns kept on the service, and the "
                "stand-in handed the question it follows, read from the service")
    (kept,) = turns[1]["plan"]["claims"]
    values = {v["quantity"]["origin"]["kind"]: v for v in kept["values"]}
    estimate, read = values.get("model-estimate"), values.get("artifact")
    proof.check(estimate is not None and estimate["quantity"]["origin"]["by"] == evaluate.STANDIN
                and kept["provenance"] == "assumed",
                f"the dearer cane's claim states the stand-in's estimate as a labelled value, marked {evaluate.STANDIN}'s, "
                f"and is {kept['provenance']}")
    run_id = read["quantity"]["origin"]["ref"] if read else None
    run = api(proof, "GET", f"/api/runs/{run_id}")["run"] if run_id else {}
    proof.check(bool(run) and read["source"].startswith(f"{run_id}:") and run.get("scenarioId") is not None
                and run.get("provenance") == "assumed",
                f"the scenario run {run_id} ({run.get('scenarioId')}, {run.get('provenance')}), and the claim's selling "
                f"price read from it by evidence id {read['source'] if read else None}")
    proof.check(dearer["droppedForNumbers"] == 1 and dearer["rejected"] == 1 and dearer["scores"]["bareNumbers"] == 0.0,
                "a claim with a bare number dropped and counted: one dropped, the turn's bare-number score 0")
    calls = api(proof, "GET", f"/api/conversations/{dearer['conversationId']}/turns/{dearer['turnId']}/calls")
    proof.check([c["tool"] for c in calls] == ["engine_parameters", "study_scenario", "engine_run"],
                f"the follow-up's tool calls kept with its turn: {', '.join(c['tool'] for c in calls)}")
    proof.check(report["mean"] == {"tools": 1.0, "citations": 1.0, "estimates": 1.0, "bareNumbers": 0.5},
                f"each question scored and kept: {report['mean']}")
    proof.made["conversation"] = dearer["conversationId"]


def step_9(proof: Proof) -> None:
    if not (ROOT / "dist" / "index.html").exists():
        raise Stop("dist/ holds no built app: run `pnpm build` before the proof, since the service mounts the app "
                   "it finds when it starts")
    runbook = proof.made.get("runbook")
    env = {**os.environ, "WALK_ORIGIN": proof.origin, "WALK_PROJECT": proof.project, "WALK_RUN": proof.made["flowsheet"],
           "WALK_CONVERSATION": proof.made["conversation"], "WALK_RUNBOOK": runbook[0] if runbook else ""}
    walked = subprocess.run(["npx", "tsx", "scripts/walk.ts"], cwd=ROOT, text=True, capture_output=True, env=env,
                            timeout=900)
    lines = [line.strip() for line in walked.stdout.splitlines() if line.strip().startswith(("✓", "✗"))]
    for line in lines:
        proof.check(line.startswith("✓"), line[1:].strip())
    proof.check(walked.returncode == 0 and bool(lines), "the walk ended clean" if walked.returncode == 0 else
                f"the walk exited {walked.returncode}: {(walked.stderr or '').strip()[-300:]}")


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
    if "record" in m:
        held = {d["documentId"] for d in api(proof, "GET", "/api/literature/documents")}
        record_id, status, provenance = m["record"]
        record = api(proof, "GET", "/api/biorepo/overlay")["records"].get(record_id) or {}
        proof.check(set(m["documents"]) <= held and (record.get("status"), record.get("provenance")) == (status, provenance),
                    f"its {len(held)} documents reload, and record {record_id}, {status} and {provenance}")
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


RUNNERS: dict[int, Callable[[Proof], None]] = {1: step_1, 2: step_2, 3: step_3, 4: step_4, 5: step_5, 6: step_6,
                                               7: step_7, 8: step_8, 9: step_9}


def spent(proof: Proof) -> None:
    """What the proof spent, from its database's spend table: offline, no call at all."""
    read = "import json; from openferment_core import spend; print(json.dumps(spend.state()))"
    done = subprocess.run([sys.executable, "-c", read], cwd=CORE, text=True, capture_output=True,
                          env=environment(proof, 0), timeout=120)
    if done.returncode != 0:
        proof.check(False, f"the spend table could not be read: {(done.stderr or done.stdout).strip()[-300:]}")
        return
    day = json.loads(done.stdout.strip().splitlines()[-1])
    words = ", ".join(f"{role} ${usd:.4f}" for role, usd in day["byRole"].items())
    if proof.live:
        proof.check(True, f"spent, from the proof's spend table: {day['calls']} calls, ${day['totalUsd']:.4f} ({words})")
    else:
        proof.check(day["calls"] == 0 and day["totalUsd"] == 0, f"no model call: the proof's spend table holds "
                    f"{day['calls']} calls, ${day['totalUsd']:.4f}")


def has_key() -> bool:
    """Whether core/.env names a key (read, never printed)."""
    if not KEY_FILE.exists():
        return False
    return any(line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip().strip("'\"")
               for line in KEY_FILE.read_text(encoding="utf-8").splitlines())


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
    parser.add_argument("--steps", default=None, help="the steps to prove, e.g. 5,8 (live: every step but 9)")
    parser.add_argument("--keep", action="store_true", help="leave the service and its database at the end")
    parser.add_argument("--live", action="store_true",
                        help="the key in core/.env, the network and the routed models: step 3 collects the ethanol "
                             "sources and a model extracts a paper, step 6 asks the routed models; it spends")
    args = parser.parse_args(argv)
    if args.live and not has_key():
        parser.error("--live reads the key from core/.env, which names none: with OPENFERMENT_API_KEY set, "
                     "`bash scripts/session-start.sh` writes it")
    # The walk (9) reads the offline conversation's labelled estimate, so a live proof leaves it out unless asked.
    steps = args.steps or ",".join(str(n) for n in STEPS if not (args.live and n == 9))
    try:
        asked = [int(x) for x in steps.split(",") if x.strip()]
    except ValueError:
        parser.error("--steps names steps by number, e.g. 5,8")
    unknown = [n for n in asked if n not in STEPS]
    if unknown:
        parser.error(f"this build proves steps {', '.join(map(str, STEPS))}; not {', '.join(map(str, unknown))}")
    proof = Proof(database=f"openferment_proof_{os.urandom(4).hex()}", data_dir=Path(tempfile.mkdtemp(prefix="openferment-proof-")),
                  live=args.live)
    proof.log = proof.data_dir / "service.log"
    print(f"openFerment proof{' (live)' if proof.live else ''}: steps {', '.join(map(str, order(asked)))} "
          f"on database {proof.database}\n")
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
        if proof.origin:
            print("── the spend")
            spent(proof)
            print()
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
