"""The proof (execution prompt §9.1): an end-to-end path with nothing seeded.

    pnpm prove                    every step: 1 to 10
    pnpm prove --steps 5,8        the steps named, after the steps they stand on
    pnpm prove --keep             leave the service running at the end, and say where
    pnpm prove --live             with the key in core/.env and the network: step 3 collects the
                                  ethanol sources (docs/corpus/ethanol-sources.txt) and the routed
                                  model extracts a paper; step 6 asks the routed models; every step
                                  but the walk, unless --steps names it. It spends, under the cap

The service runs on loopback as a host serves it (uvicorn, `openferment_core.api`), on a
database of the proof's own, made on the tests' server (OPENFERMENT_TEST_DATABASE_URL) and
dropped at the end, with a data directory of its own, removed at the end when every check
holds and kept with the service's log when one fails: a proof touches no core/data/ and no
other database. It runs without the model key and makes no model call, and in fixture mode,
so its collectors refuse the network: step 3's extraction reads a stand-in's written response
where it would call a model, and step 6 asks Postdoc through its evaluation's offline stand-in.
Its last check reads the proof's own spend table: offline it holds no call. Every check prints ✓
or ✗ with what it saw; the proof exits 1 when a check fails, 2 when it cannot start.

Before its service starts, the proof installs every package directory under examples/engines/
(one holding a pyproject.toml) into core's environment with `uv pip install -e`, each said with the
engines its pyproject.toml registers, and every package core/uv.lock pins held at its locked
version (the lock's versions are the install's constraints, so a package that would move one is
refused in uv's words). A package that leads outside examples/engines/, one whose pyproject.toml
cannot be read and one that fails to install each fail the proof in words; with none there one
line says so. Step 9 runs the first thing of each of their engines on its own defaults from the
Runs screen and step 10 checks each, as it checks every engine the service lists, with no value
set: the proof names no example engine, so a builder's package is picked up with no change under
scripts/. At its end, however it ends (a failure, Ctrl-C, SIGTERM), the proof leaves core's
environment as it found it: each package it installed whose distribution was installed nowhere
before is uninstalled, one installed before from the same directory stays, and one installed
before from another directory is installed from there again, one line a package. With --keep the
packages stay installed while the kept service runs, each said with the command that takes it out.

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
       graph, a scenario begun from that run, the plants Studies offers to run, the project's
       SFF flowsheets, the catalogues screen keeping a placeholder strain in the proof's person's
       name (added, edited, taken in again from a file through the screen, and read back as the
       person's; the service then holds it as the strain catalogue's one entry, the person's keep
       from that file), the conversation of step 6 with its estimate marked, the runbook of step 5;
       then a reading deposited at the bench on that locked runbook, the readings alone, by the
       proof's person, in the unit of the scenario parameter step 5 sets, the placeholder the
       person types; a scenario made from step 5's flowsheet run through NewScenarioDialog with
       that reading chosen and nothing typed, and run; its run's page read: provenance measured,
       the reading's origin linked to its deposition. The service then holds each as the walk
       left it: the deposition, the reading with its depositor and time, the scenario resting
       on the reading alone, and its run `measured` with the measurement among its inputs; then,
       for each engine a package under examples/engines/ registers, its first thing run on its own
       defaults from the Runs screen (Studies' run card, the engine chosen), the run's page opened,
       and its provenance, its outputs and its diagnostics read there as the service keeps them;
       with no such package, one line says so and the walk checks nothing more
   10  every engine of the entry-point group `openferment.engines` listed by the service with its
       version and its worker's state, none with an error, every engine core/pyproject.toml registers
       among them (biosteam, kinetics and train), and every engine the step sets values or a project
       for; the eight conformance checks of docs/api/engines.md
       made on each (`python -m openferment_core.engine.conform <name>`, on a scratch database of
       its own; the kinetics engine's with `--inputs`, the placeholders its builder writes as the
       proof's person's assumptions, each dated the proof's day; the train engine's with
       `--project`, naming the proof's own project, which the checks read and copy into a database
       of their own and check there, on a train made in the project first as a person makes one in
       pureOS's Builder: step 4's cornstover run read into a train (`POST
       /api/pureos/train/from-run`), its first units taken out while a check refuses its inlet as one
       the chemical set cannot build, then the units whose values wait taken out with every unit
       before them, the inlet the run's stream entering the first unit kept, checked and saved as the
       project's row, read back as the proof's person's), each within its time (CONFORM_TIMEOUT_S),
       the words of checks 3, 5 and 7 printed under each engine's line; the proof's project as it was
       after every engine's checks (its runs, its trains and its artifacts); and each verdict kept in
       the proof's database and listed, every core engine's among them
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlsplit, urlunsplit

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
# The reading the walk deposits at the bench (step 9) on step 5's locked runbook: a placeholder the proof's person
# types, in the unit of the scenario parameter step 5 sets, the unit the runbook's measure is in; and the parameter a
# scenario then sets to that reading alone. The pairing is a placeholder chosen by unit: the service holds a reading's
# unit to the parameter's, and which measure stands for which parameter is the scenario maker's choice (ADR-006's
# note of 2026-11-03). The value measures nothing.
READING_PARAMETER = "stream.cornstover.price"
READING_UNIT = "USD/kg"
READING_VALUE = 1.0
# The placeholder strain the walk keeps on the catalogues screen (step 9): an id whose entry stands for no strain.
WALK_STRAIN = "walk-placeholder-strain"
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
STEPS: dict[int, tuple[int, ...]] = {1: (), 2: (1,), 3: (2,), 4: (2,), 5: (2,), 6: (2,), 7: (2,), 8: (2,), 9: (5, 6),
                                     10: (2, 4)}
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
    9: "the UI walk: Home, the project, ingest, search, a run report and its SFF graph, a scenario begun from it, the plants Studies offers, the SFF flowsheets, a placeholder strain kept on the catalogues screen, a conversation, a runbook; a reading at the bench, a scenario on it, its run measured; each example engine's first thing run from the Runs screen",
    10: "the engines: each registered one listed, the core's three among them, the eight conformance checks made on "
        "it, its verdict kept, the proof's project as it was; a train made on step 4's run for the train engine's",
}
# How long the conformance checks of one engine may take, and how long a run past it is given to end once asked
# to (SIGTERM), dropping its own database as it ends, before it is killed. BioSTEAM's are the longest: a cold
# import, then the parameters of every thing it runs (1840 of 10 things at C.7: the library's eight plants,
# openFerment's flowsheet and the shelf's scenario flowsheet) and its runs. Measured here at C.7: biosteam
# 51 to 63 s, kinetics 9 to 11 s, train 30 to 36 s.
CONFORM_TIMEOUT_S = 1800.0
CONFORM_END_S = 60.0
# The states a listed engine's worker may be in (engine/registry.py `status_of`): `none` for an engine with no
# worker, and for one with a worker any state but `failed`.
WORKER_STATES = ("ready", "cold", "starting")
# The checks whose words step 10 prints under each engine's line, from conform's own table: check 3 names the
# thing that ran and where, check 5 the branch it took (a file or sffRefused's words), check 7 the refusal held.
SAID_CHECKS = (3, 5, 7)
# The engines whose things wait for values no default gives, each with the module and the function that
# write the file `conform --inputs` reads (docs/api/engines.md, Conformance): the core's kinetics engine. The
# function is called with the file's path, the person whose assumptions the placeholders are (PERSON), and the
# proof's day, which dates each.
PLACEHOLDERS = {"kinetics": ("openferment_core.fermos_engine", "write_placeholder_inputs")}
# The engines whose things are a project's own (each declares `things_are`), checked in a copy of the proof's own
# project (`conform --project`), on what the proof made there for each: the core's train engine, on the train
# `make_train` makes on step 4's reference run.
IN_PROJECT = ("train",)
WRITE_PLACEHOLDERS = ("import importlib, sys; getattr(importlib.import_module(sys.argv[1]), sys.argv[2])"
                      "(sys.argv[3], by=sys.argv[4], at=sys.argv[5])")
RUN_TIMEOUT_S = 1800.0

# The engine packages a builder keeps in the repository (stage D's), each a directory holding a pyproject.toml,
# installed into core's environment before the service starts; and the group each registers its engines under.
EXAMPLES = ROOT / "examples" / "engines"
ENGINE_GROUP = "openferment.engines"

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
    # The day the proof began (UTC, YYYY-MM-DD): the day step 10's placeholders are dated. Step 5's person's
    # assumption and model's estimate carry days of their own, written in the step.
    day: str = ""
    failed: int = 0
    passed: int = 0
    # What the steps made, for step 8 to reload.
    made: dict[str, Any] = field(default_factory=dict)
    service: subprocess.Popen | None = None
    log: Path = Path()
    # The packages installed from examples/engines/, each with how core's environment held it before (D0.8a).
    installed: list[Any] = field(default_factory=list)

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


def conformed(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    """`conform` run to its end, as `subprocess.run` runs it; a run past CONFORM_TIMEOUT_S is asked to end
    (SIGTERM), which drops the checks' own database as it ends (engine/conform.py `_scratch`), and is killed
    CONFORM_END_S later if it has not. A run that outlived its time ends with words saying so."""
    with subprocess.Popen(command, cwd=CORE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env) as p:
        try:
            out, err = p.communicate(timeout=CONFORM_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                out, err = p.communicate(timeout=CONFORM_END_S)
            except subprocess.TimeoutExpired:
                p.kill()
                out, err = p.communicate()
            err = f"{err or ''}\nthe checks ran past {CONFORM_TIMEOUT_S:.0f} s and were asked to end"
        except BaseException:
            # The proof itself ends (Ctrl-C, SIGTERM): the checks are asked to end with it, dropping their database.
            p.terminate()
            try:
                p.wait(timeout=CONFORM_END_S)
            except subprocess.TimeoutExpired:
                p.kill()
            raise
    return subprocess.CompletedProcess(command, p.returncode, out, err)


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


# ── the example engines (alpha 2.2 D0.8, D0.8a) ─────────────────────────

# Where core's environment holds a distribution from, read by its own interpreter: null when it holds none, else its
# version and its direct_url.json (the directory an install named, and whether it was editable).
HELD_FROM = """\
import json, sys
from importlib import metadata
try:
    d = metadata.distribution(sys.argv[1])
except metadata.PackageNotFoundError:
    print("null")
else:
    print(json.dumps({"version": d.version, "from": json.loads(d.read_text("direct_url.json") or "null")}))
"""


@dataclass
class Installed:
    """A package the proof installed from examples/engines/, its distribution, the engines it registers, and how
    core's environment held that distribution before the proof began: None when it held none."""
    package: Path
    distribution: str
    engines: list[str]
    before: dict[str, Any] | None


def shown(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def example_packages(root: Path = EXAMPLES) -> list[Path]:
    """Each package directory under examples/engines/, one holding a pyproject.toml, in name order, each as it is
    named there (install_examples refuses one that leads outside the directory)."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "pyproject.toml").is_file())


def example_project(package: Path) -> tuple[str, list[str]]:
    """A package's distribution and the engines its pyproject.toml registers in the group `openferment.engines`, in
    name order; ValueError in words for a pyproject.toml that names no distribution, and the parser's own error for
    one that is no TOML."""
    import tomllib

    project = tomllib.loads((package / "pyproject.toml").read_text(encoding="utf-8")).get("project") or {}
    name = str(project.get("name") or "").strip()
    if not name:
        raise ValueError("its pyproject.toml names no distribution ([project] name)")
    return name, sorted((project.get("entry-points") or {}).get(ENGINE_GROUP) or {})


def held_from(distribution: str, run: Callable[..., Any] = subprocess.run) -> dict[str, Any] | None:
    """How core's environment holds `distribution` (HELD_FROM): None when it holds none."""
    done = run([sys.executable, "-c", HELD_FROM, distribution], cwd=CORE, text=True, capture_output=True, timeout=60)
    if done.returncode != 0:
        raise OSError(f"core's interpreter could not say whether it holds {distribution}: "
                      f"{(done.stderr or done.stdout or '').strip()[-200:] or 'no words'}")
    return json.loads(done.stdout.strip() or "null")


def lock_constraints(path: Path, run: Callable[..., Any] = subprocess.run) -> None:
    """core/uv.lock's versions written to `path` as an install's constraints (`uv export --frozen`), so an install
    moves no package the lock pins: one whose dependencies would is refused in uv's words. OSError in words when
    the lock cannot be read so."""
    done = run(["uv", "export", "--frozen", "--all-extras", "--no-hashes", "--no-emit-project", "--quiet"], cwd=CORE,
               text=True, capture_output=True, timeout=120)
    if done.returncode != 0:
        said = (done.stderr or done.stdout or "").strip().splitlines()
        raise OSError(f"core/uv.lock could not be read as the installs' constraints (uv export --frozen exited "
                      f"{done.returncode}): {said[-1] if said else 'no words'}")
    path.write_text(done.stdout, encoding="utf-8")


def install_examples(proof: Proof, root: Path = EXAMPLES, run: Callable[..., Any] = subprocess.run,
                     constraints: Path | None = None) -> list[str]:
    """Each package under examples/engines/ installed into core's environment (`uv pip install -e`, the
    interpreter the proof runs on, every package core/uv.lock pins held at its locked version), before the service
    starts: one check a package, naming the engines it registers. A package that leads outside examples/engines/
    (a symbolic link elsewhere), a pyproject.toml that cannot be read, an install uv refuses and one that outlives
    its time each fail in words, and the rest are installed; with none, one line saying so. Each package installed
    is kept in `proof.installed` with how core's environment held its distribution before (leave_as_found). The
    engines the installed packages register, for the walk (step 9)."""
    packages = example_packages(root)
    if not packages:
        print(f"  no package under {shown(root)}, so none is installed and no example engine is walked")
        return []
    held = constraints or proof.data_dir / "constraints.txt"
    try:
        lock_constraints(held, run)
    except (OSError, subprocess.TimeoutExpired) as e:
        proof.check(False, f"no package under {shown(root)} was installed: {e}")
        return []
    names: list[str] = []
    inside = root.resolve()
    for package in packages:
        where = shown(package)
        if not package.resolve().is_relative_to(inside):
            proof.check(False, f"{where} leads to {package.resolve()}, outside {shown(root)}; the proof installs "
                               f"from {shown(root)} alone, so this one was not installed")
            continue
        try:
            distribution, engines = example_project(package)
            before = held_from(distribution, run)
        except (OSError, UnicodeDecodeError, ValueError, subprocess.TimeoutExpired) as e:
            # tomllib's TOMLDecodeError is a ValueError.
            proof.check(False, f"{where} was not installed: {type(e).__name__}: {e}")
            continue
        try:
            done = run(["uv", "pip", "install", "--python", sys.executable, "-c", str(held), "-e", str(package)],
                       cwd=CORE, text=True, capture_output=True, timeout=RUN_TIMEOUT_S)
        except (OSError, subprocess.TimeoutExpired) as e:
            proof.check(False, f"{where} did not install (uv pip install -e): {type(e).__name__}: {e}")
            continue
        said = (done.stderr or done.stdout or "").strip().splitlines()
        if proof.check(done.returncode == 0,
                       f"{where} installed into core's environment (uv pip install -e, each package core/uv.lock "
                       "pins held at its locked version), registering "
                       + (", ".join(engines) or "no engine in the group openferment.engines")
                       if done.returncode == 0 else
                       f"{where} did not install (uv pip install -e exited {done.returncode}, each package "
                       f"core/uv.lock pins held at its locked version): " + (said[-1] if said else "no words")):
            proof.installed.append(Installed(package, distribution, engines, before))
            names += engines
    return sorted(set(names))


def _source_of(before: dict[str, Any]) -> tuple[Path | None, bool]:
    """The directory an earlier install of a distribution named, and whether it was editable; None for one
    installed from anywhere else (an index, a URL)."""
    url = ((before.get("from") or {}).get("url") or "")
    if not url.startswith("file://"):
        return None, False
    from urllib.parse import unquote

    editable = bool(((before.get("from") or {}).get("dir_info") or {}).get("editable"))
    return Path(unquote(urlsplit(url).path)), editable


def leave_as_found(proof: Proof, run: Callable[..., Any] = subprocess.run, *, kept: bool = False) -> None:
    """Core's environment as the proof found it (D0.8a), one line a package: each package the proof installed
    whose distribution the environment held none of before is uninstalled; one it held from that same directory
    stays; one it held from another directory is installed from there again, as it was. With the service kept
    (--keep), each stays installed while the service runs, with the command that takes it out."""
    for done in proof.installed:
        where = shown(done.package)
        if kept:
            print(f"  {done.distribution} stays installed from {where} while the kept service runs; "
                  f"cd core && uv pip uninstall {done.distribution} takes it out")
            continue
        if done.before is None:
            out = run(["uv", "pip", "uninstall", "--python", sys.executable, done.distribution], cwd=CORE, text=True,
                      capture_output=True, timeout=300)
            said = (out.stderr or out.stdout or "").strip().splitlines()
            print(f"  {done.distribution} uninstalled, as the proof found core's environment without it"
                  if out.returncode == 0 else
                  f"  ✗ {done.distribution} could not be uninstalled (uv pip uninstall exited {out.returncode}): "
                  f"{said[-1] if said else 'no words'}; cd core && uv pip uninstall {done.distribution} takes it out")
            continue
        source, editable = _source_of(done.before)
        if source is not None and source.resolve() == done.package.resolve():
            print(f"  {done.distribution} stays installed from {where}, as it was before the proof")
            continue
        if source is None or not source.is_dir():
            print(f"  {done.distribution} stays installed from {where}; before the proof it was installed from "
                  f"{source or (done.before.get('from') or {}).get('url') or 'an index'}, which the proof cannot "
                  "install it from again")
            continue
        constraints = proof.data_dir / "constraints.txt"
        out = run(["uv", "pip", "install", "--python", sys.executable, "-c", str(constraints),
                   *(["-e"] if editable else []), str(source)], cwd=CORE, text=True, capture_output=True,
                  timeout=RUN_TIMEOUT_S)
        said = (out.stderr or out.stdout or "").strip().splitlines()
        print(f"  {done.distribution} installed again from {source}, as it was before the proof"
              if out.returncode == 0 else
              f"  ✗ {done.distribution} could not be installed again from {source}: {said[-1] if said else 'no words'}; "
              f"it stays installed from {where}")


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
    if runbook:
        # The bench files a reading in its measure's unit, which the scenario parameter must be denominated in.
        units = {m["unit"] for m in api(proof, "GET", f"/api/studies/runbooks/{runbook[0]}")["measurementSchema"]}
        if READING_UNIT not in units:
            raise Stop(f"runbook {runbook[0]} measures in {', '.join(sorted(units))}, and the walk's reading is for "
                       f"{READING_PARAMETER}, in {READING_UNIT}")
    examples = proof.made.get("examples") or []
    if not examples:
        print("  no engine installed from examples/engines/, so the walk runs none of theirs")
    env = {**os.environ, "WALK_ORIGIN": proof.origin, "WALK_PROJECT": proof.project, "WALK_RUN": proof.made["flowsheet"],
           "WALK_CONVERSATION": proof.made["conversation"], "WALK_RUNBOOK": runbook[0] if runbook else "",
           "WALK_PERSON": PERSON, "WALK_READING": f"{READING_VALUE:g}", "WALK_READING_UNIT": READING_UNIT,
           "WALK_READING_PARAMETER": READING_PARAMETER, "WALK_STRAIN": WALK_STRAIN, "WALK_ENGINES": ",".join(examples)}
    walked = subprocess.run(["npx", "tsx", "scripts/walk.ts"], cwd=ROOT, text=True, capture_output=True, env=env,
                            timeout=1500)
    lines = [line.strip() for line in walked.stdout.splitlines() if line.strip().startswith(("✓", "✗"))]
    for line in lines:
        proof.check(line.startswith("✓"), line[1:].strip())
    proof.check(walked.returncode == 0 and bool(lines), "the walk ended clean" if walked.returncode == 0 else
                f"the walk exited {walked.returncode}: {(walked.stderr or '').strip()[-300:]}")
    catalogued_by_the_walk(proof)
    if runbook:
        measured_by_the_walk(proof, runbook[0])


def catalogued_by_the_walk(proof: Proof) -> None:
    """The strain the walk kept on the catalogues screen, read back through the API (alpha 2.2 E.8): the strain
    catalogue's one entry, under WALK_STRAIN, a person's keep in the proof's person's name (no model's door), with
    its other names and a file as its source, as the screen's file intake kept it last."""
    held = api(proof, "GET", "/api/catalogues/strain")
    e = held[0] if len(held) == 1 else {}
    proof.check(e.get("id") == WALK_STRAIN and e.get("by") == PERSON and e.get("agent") == "person" and e.get("via") is None
                and bool(e.get("aliases")) and str(e.get("source") or "").startswith("the file ") and bool(e.get("at")),
                f"the walk's strain {e.get('id')}: kept by {e.get('by')} as a {e.get('agent')}'s keep at {e.get('at')}, its "
                f"other names {', '.join(e.get('aliases') or [])}, from {e.get('source')}, the strain catalogue's one entry"
                if e else f"the strain catalogue holds {len(held)} entries, and the walk kept one")


def measured_by_the_walk(proof: Proof, runbook: str) -> None:
    """What the walk left on the service, read back through the API (alpha 2.2 C.5): the deposition it made at
    the bench on `runbook` with no protocol's steps, closed, holding the one reading the proof's person typed and
    read back; that reading listed as one a run takes in the parameter's unit, deposited by the person; the
    scenario on step 5's flowsheet setting the parameter to that reading alone; and its run, `measured`, the
    reading among its inputs as a measurement and every other input the library's default or a convention."""
    deposited = [d for d in api(proof, "GET", "/api/state")["depositions"] if d.get("runbookId") == runbook]
    readings = [r for r in api(proof, "GET", f"/api/depositions/readings?unit={quote(READING_UNIT)}")
                if r["runbookId"] == runbook]
    d = deposited[0] if len(deposited) == 1 else {}
    r = readings[0] if len(readings) == 1 else {}
    entries = d.get("entries") or []
    if not proof.check(bool(d) and d.get("protocolId") is None and d.get("state") == "closed" and len(entries) == 1
                       and entries[0].get("confirmed") is True and bool(r) and r["ref"] == f"{d['id']}/{entries[0]['id']}"
                       and (r["value"], r["unit"], r["by"]) == (READING_VALUE, READING_UNIT, PERSON),
                       f"the walk's deposition on runbook {runbook}: "
                       + (f"{d['id']}, the readings alone, {d['state']}, holding reading {r['ref']}, {r['value']:g} "
                          f"{r['unit']} confirmed at the bench, deposited by {r['by']} and taken {r['at']}"
                          if d and r else f"{len(deposited)} depositions and {len(readings)} readings")):
        return
    made = [s for s in api(proof, "GET", "/api/studies/scenarios")
            if any((v["quantity"].get("origin") or {}).get("kind") == "measurement" for v in s["values"])]
    scenario = made[0] if len(made) == 1 else {}
    values = scenario.get("values") or []
    origin = (values[0]["quantity"].get("origin") or {}) if len(values) == 1 else {}
    if not proof.check(bool(scenario) and len(values) == 1 and values[0]["key"] == READING_PARAMETER
                       and scenario.get("plant") == FLOWSHEET and scenario.get("by") == PERSON
                       and (origin.get("ref"), origin.get("by"), origin.get("at")) == (r["ref"], PERSON, r["at"])
                       and len(scenario.get("runIds") or []) == 1,
                       f"the walk's scenario {scenario.get('id')} on {scenario.get('plant')}, made by {scenario.get('by')}: "
                       + (f"{READING_PARAMETER} set to reading {origin.get('ref')} alone (a placeholder pairing chosen by "
                          "unit), kept with its depositor and time, nothing assumed, run once" if scenario
                          else f"{len(made)} scenarios rest on a reading")):
        return
    run = api(proof, "GET", f"/api/runs/{scenario['runIds'][0]}")["run"]
    inputs = {i["name"]: i["quantity"] for i in run["inputs"]}
    kinds = {q["origin"]["kind"] for q in inputs.values()}
    set_to = inputs.get(READING_PARAMETER) or {}
    came = set_to.get("origin") or {}
    proof.check(run["status"] == "done" and run["provenance"] == "measured" and run["scenarioId"] == scenario["id"]
                and kinds <= {"library-default", "convention", "measurement"}
                and (set_to.get("value"), set_to.get("unit")) == (READING_VALUE, READING_UNIT)
                and (came.get("kind"), came.get("ref"), came.get("by"), came.get("at")) == ("measurement", r["ref"], PERSON,
                                                                                           r["at"]),
                f"its run {run['id']}: {run['provenance']}, {READING_PARAMETER} {set_to.get('value')} {set_to.get('unit')} "
                f"a {came.get('kind')} (reading {came.get('ref')}, deposited by {came.get('by')}, taken {came.get('at')}); "
                f"its inputs {', '.join(sorted(kinds))}")
    proof.made["measuredRun"] = run["id"]
    proof.made["deposition"] = d["id"]


def make_train(proof: Proof) -> str:
    """A train on step 4's cornstover run in the proof's project, made through the routes a person uses in
    pureOS's Builder: the run's units read into a train (`POST /api/pureos/train/from-run`, every unit the
    product passes through whose class is a catalogue type, at its class's own defaults, from the unit the
    stream carrying the most product into it enters); its first units taken out while a check of it (`POST
    /api/pureos/train/check`) refuses its inlet as one whose chemicals the set cannot build
    (`train_spec.CANNOT_BUILD`), the inlet each time the run's own stream entering the new first unit, read from
    the run's unit table, as the Builder offers it once the first units go (`builder-inlet-away`); then the units
    whose values wait (the check's places, every refusal of each a value that waits,
    `openferment_core.pureos.engine.WAITING`) taken out with every unit before them, as a person with no value
    for them removes them, and the inlet the run's stream entering the first unit kept; any other refusal stops
    the proof; checked again, nothing refused; and saved as the project's row, as Save keeps it (`PUT
    /api/state/trains/<id>`). Its id."""
    from openferment_core.pureos.engine import WAITING
    from openferment_core.pureos.train_spec import CANNOT_BUILD

    reference = proof.made["reference"]
    read = api(proof, "POST", "/api/pureos/train/from-run", {"artifactId": reference}, timeout=RUN_TIMEOUT_S)
    train = read["train"]
    ins = {u["id"]: u["ins"] for u in api(proof, "GET", f"/api/biorepo/artifacts/{reference}")["output"]["units"]}

    def from_unit(n: int) -> dict[str, Any]:
        """The train from its unit n on, its inlet the run's stream entering that unit."""
        if n == 0:
            return train
        first = train["units"][n]
        return {**train, "name": f"{train['name']}, from {first['id']} on", "units": train["units"][n:],
                "inlet": {**train["inlet"], "streamId": ins[first["id"]][0]}}

    def check(tail: dict[str, Any]) -> dict[str, Any]:
        return api(proof, "POST", "/api/pureos/train/check", {"train": tail, "by": PERSON}, timeout=RUN_TIMEOUT_S)

    head = 0
    checked = check(train)
    while (not checked["ok"] and any(CANNOT_BUILD in w for w in checked["places"].get("inlet") or [])
           and head + 1 < len(train["units"])):
        head += 1
        checked = check(from_unit(head))
    tail = from_unit(head)
    waiting = [n for n, u in enumerate(tail["units"]) if checked["places"].get(u["id"])]
    other = [w for place, said in checked["places"].items() for w in said
             if not (place != "inlet" and WAITING.search(w))]
    if other:
        proof.check(False, f"{REFERENCE_PLANT} run {reference} read into train {train['id']}: from "
                           f"{tail['units'][0]['id']} on stream {tail['inlet']['streamId']}, refused for more than a "
                           "value that waits: " + "; ".join(other)[:600])
        raise Stop("the train is refused for more than an inlet it cannot build or a value that waits")
    kept = tail["units"][max(waiting) + 1:] if waiting else tail["units"]
    if not proof.check(bool(kept), f"{REFERENCE_PLANT} run {reference} read into train {train['id']}: "
                                   f"{len(train['units'])} units ({', '.join(u['id'] for u in train['units'])}) from "
                                   f"stream {train['inlet']['streamId']}; {head} taken out from the head ("
                                   f"{', '.join(u['id'] for u in train['units'][:head]) or 'none'}), each check refusing "
                                   "an inlet the chemical set cannot build; then "
                                   f"{len(waiting)} of the rest ({', '.join(tail['units'][n]['id'] for n in waiting) or 'none'}) "
                                   "waiting for values its class requires, every refusal of each a value that waits; "
                                   + (f"kept from {kept[0]['id']} on" if kept else "no unit runs on its own values")):
        raise Stop("no train to check the train engine on")
    made = from_unit(len(train["units"]) - len(kept))
    again = check(made)
    if not proof.check(again["ok"], f"train {made['id']} ({', '.join(u['id'] for u in kept)}) on stream "
                                    f"{made['inlet']['streamId']} of run {reference}: "
                                    + ("nothing a run would refuse" if again["ok"] else "; ".join(again["refusals"])[:300])):
        raise Stop("the train would be refused")
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    api(proof, "PUT", f"/api/state/trains/{made['id']}", {"by": PERSON, "value": {"train": made, "savedAt": at,
                                                                                   "by": PERSON}})
    proof.made["train"] = made["id"]
    return made["id"]


def registered_engines() -> list[str]:
    """The engines core/pyproject.toml registers in the group `openferment.engines`: the core's own, each of
    which step 10 requires listed with no error, conformed and held. An engine another package registers (stage
    D's) is checked beside them once the service lists it."""
    import tomllib

    project = tomllib.loads((CORE / "pyproject.toml").read_text(encoding="utf-8"))
    return sorted(project["project"]["entry-points"]["openferment.engines"])


def said_lines(stdout: str) -> dict[int, str]:
    """Each check's words from `conform`'s table (engine/conform.py `table`): the indented line under its
    `✓ <n>` or `✗ <n>` line, by its number."""
    lines = stdout.splitlines()
    out: dict[int, str] = {}
    for i, line in enumerate(lines):
        head = line[1:].split() if line.startswith(("✓", "✗")) else []
        if head and head[0].isdigit() and i + 1 < len(lines) and lines[i + 1].startswith("     "):
            out[int(head[0])] = lines[i + 1].strip()
    return out


def project_rows(proof: Proof) -> dict[str, Any]:
    """What a conformance run could write into the proof's project: its runs and its artifacts by id, and its
    trains as GET /api/state holds them."""
    return {"runs": sorted(r["id"] for r in api(proof, "GET", "/api/runs")),
            "trains": api(proof, "GET", "/api/state")["trains"],
            "artifacts": sorted(a["id"] for a in api(proof, "GET", "/api/biorepo/artifacts", timeout=RUN_TIMEOUT_S))}


def step_10(proof: Proof) -> None:
    core = registered_engines()
    if "reference" in proof.made:
        made = make_train(proof)
        row = api(proof, "GET", "/api/state")["trains"].get(made) or {}
        listed = {e["name"]: e for e in api(proof, "GET", "/api/engines")}
        proof.check(row.get("by") == PERSON and (row.get("train") or {}).get("id") == made
                    and any(t["id"] == made for t in (listed.get("train") or {}).get("things") or []),
                    f"train {made} saved as the project's row, read back as {row.get('by') or 'nobody'}'s, and "
                    "listed by the train engine")
    listed = api(proof, "GET", "/api/engines")
    usable = [e for e in listed if not e["error"]]
    broken = [e for e in listed if e["error"]]
    names = {e["name"] for e in usable}
    missing = [n for n in core if n not in names]
    # The engines step 10 sets values or a project for are among those it checks.
    unchecked = sorted(n for n in {*PLACEHOLDERS, *IN_PROJECT} if n not in names)
    # A listed engine's worker: none and `none`, or a module and a state that has not failed (registry.status_of).
    off = [e for e in usable if (e["workerStatus"] != "none" if e["worker"] is None
                                 else e["workerStatus"] not in WORKER_STATES)]
    proof.check(not missing and not broken and not unchecked and not off,
                f"the service lists {len(listed)} engine{'s' if len(listed) != 1 else ''} of the group "
                f"openferment.engines, core/pyproject.toml's {len(core)} ({', '.join(core)}) "
                + ("among them" if not missing else f"short of {', '.join(missing)}") + ": " + "; ".join(
                    f"{e['name']} from {e['entryPoint']} ("
                    + ", ".join(f"{k} {v}" for k, v in sorted(e["version"].items()))
                    + f"), worker {e['worker'] or 'none'}, {e['workerStatus']}" for e in usable)
                + ("; with errors: " + "; ".join(f"{e['name']}: {e['error']}" for e in broken) if broken else "")
                + (f"; {', '.join(unchecked)}, which step 10 sets values or a project for, not listed" if unchecked
                   else "")
                + ("; a worker in a state it should not be in: " + ", ".join(
                    f"{e['name']} ({e['worker'] or 'none'}, {e['workerStatus']})" for e in off) if off else ""))
    env = environment(proof, int(proof.origin.rsplit(":", 1)[1]))
    before = project_rows(proof)
    for e in usable:
        command = [sys.executable, "-m", "openferment_core.engine.conform", e["name"]]
        if e["name"] in PLACEHOLDERS:
            module, writer = PLACEHOLDERS[e["name"]]
            path = proof.data_dir / f"{e['name']}-inputs.json"
            wrote = subprocess.run([sys.executable, "-c", WRITE_PLACEHOLDERS, module, writer, str(path), PERSON,
                                    proof.day], cwd=CORE, text=True, capture_output=True, env=env, timeout=RUN_TIMEOUT_S)
            values = json.loads(path.read_text(encoding="utf-8")) if wrote.returncode == 0 and path.exists() else []
            origins = {tuple((((v.get("quantity") or {}).get("origin") or {}).get(k)) for k in ("kind", "by", "at"))
                       for v in values}
            planted = origins == {("person-assumption", PERSON, proof.day)}
            proof.check(wrote.returncode == 0 and planted,
                        f"the {e['name']} engine's placeholders written by {module}.{writer}: {len(values)} values, "
                        + (f"each {PERSON}'s assumption, dated {proof.day}, the proof's day" if planted else
                           "with the origins " + "; ".join(f"{k} by {b}, dated {a}" for k, b, a in sorted(
                               origins, key=str)))
                        if values else
                        f"the {e['name']} engine's placeholders could not be written: {wrote.stderr.strip()[-300:]}")
            command += ["--inputs", str(path)]
        if e["name"] in IN_PROJECT:
            command += ["--project", proof.project]
        t0 = time.monotonic()
        done = conformed(command, env)
        took = time.monotonic() - t0
        rows = [line for line in done.stdout.splitlines() if line.startswith(("✓", "✗"))]
        failed = [line for line in rows if line.startswith("✗")]
        said = (done.stdout.strip().splitlines() or [done.stderr.strip()[-300:]])[0]
        proof.check(done.returncode == 0 and len(rows) == 8 and not failed and took < CONFORM_TIMEOUT_S,
                    f"conform {e['name']}: {len(rows) - len(failed)} of {len(rows)} checks hold in {took:.0f} s of "
                    f"its {CONFORM_TIMEOUT_S:.0f}"
                    + (f" ({said})" if not failed and rows else "")
                    + (": " + "; ".join(failed) if failed else "")
                    + ("" if rows else f": {done.stderr.strip()[-300:] or said}"))
        # What ran, and the branch each run check and the refusal check took, in the checks' own words.
        words = said_lines(done.stdout)
        for n in SAID_CHECKS:
            if n in words:
                print(f"      check {n}: {words[n]}")
    after = project_rows(proof)
    proof.check(after == before,
                f"the proof's project as it was before the checks: its {len(before['runs'])} runs, "
                f"{len(before['trains'])} train{'s' if len(before['trains']) != 1 else ''} and "
                f"{len(before['artifacts'])} artifacts, the checks having written their verdicts alone"
                if after == before else
                "the checks wrote into the proof's project: " + "; ".join(
                    f"{k} {sorted(set(after[k]) - set(before[k]))[:5]} new, {sorted(set(before[k]) - set(after[k]))[:5]} gone"
                    if k != "trains" else "its trains changed" for k in before if after[k] != before[k]))
    again = {e["name"]: e for e in api(proof, "GET", "/api/engines")}
    kept = {n: (again[n].get("conformance") or {}) for n in (e["name"] for e in usable)}
    proof.check(bool(kept) and all(v.get("ok") for v in kept.values()) and all(n in kept for n in core),
                "each verdict kept and listed by GET /api/engines: " + "; ".join(
                    f"{n} {'holds' if v.get('ok') else 'fails' if v else 'never checked'}"
                    + (f" at {v['version']}" if v.get("version") else "") for n, v in kept.items())
                + "".join(f"; {n} not checked" for n in core if n not in kept))


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
    if "measuredRun" in m:
        held = {d["id"] for d in api(proof, "GET", "/api/state")["depositions"]}
        run = api(proof, "GET", f"/api/runs/{m['measuredRun']}")["run"]
        kinds = {i["quantity"]["origin"]["kind"] for i in run["inputs"]}
        proof.check(m["deposition"] in held and run["provenance"] == "measured" and "measurement" in kinds,
                    f"deposition {m['deposition']} reloads, and run {m['measuredRun']} with it, measured, its reading a "
                    "measurement")
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
                                               7: step_7, 8: step_8, 9: step_9, 10: step_10}


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
                  live=args.live, day=time.strftime("%Y-%m-%d", time.gmtime()))
    proof.log = proof.data_dir / "service.log"
    print(f"openFerment proof{' (live)' if proof.live else ''}: steps {', '.join(map(str, order(asked)))} "
          f"on database {proof.database}\n")
    started = time.monotonic()

    def ended(signum: int, _frame: Any) -> None:
        # SIGTERM ends the proof as Ctrl-C does: the finally below stops the service, drops the database and leaves
        # core's environment as the proof found it.
        raise SystemExit(128 + signum)

    previous = signal.signal(signal.SIGTERM, ended)
    try:
        print("── the engines under examples/engines/, installed before the service starts")
        proof.made["examples"] = install_examples(proof)
        print()
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
        kept = args.keep and proof.service is not None and proof.service.poll() is None
        if kept:
            print(f"kept: the service at {proof.origin} (project {proof.project}), database {proof.database}, "
                  f"data {proof.data_dir}; stop it with kill -TERM -{proof.service.pid}")
        else:
            stop(proof)
            dropped = migrations("drop", proof.database)
            if dropped.returncode != 0:
                print(f"(database {proof.database} was left behind: {(dropped.stderr or dropped.stdout).strip()[-200:]})")
        if proof.installed:
            print("── core's environment as the proof found it")
            leave_as_found(proof, kept=kept)
        if not kept and not proof.failed:
            shutil.rmtree(proof.data_dir, ignore_errors=True)
        signal.signal(signal.SIGTERM, previous)
    print(f"{proof.passed + proof.failed} checks in {time.monotonic() - started:.0f} s: "
          + (f"{proof.failed} failed. The service's log: {proof.log}" if proof.failed else "every one holds."))
    return 1 if proof.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
