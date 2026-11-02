"""SFF flowsheet records (ADR-003; execution prompt §8.3).

A flowsheet travels in and out of openFerment as an SFF file (the PISCES
Standard Flowsheet Format). A record holds the file as it came, what the
vendored toolkit said of it (its validation against the schema the toolkit
ships, its completeness report, the tags it earns), the graph the UI draws
(units as nodes, streams as edges, the feeds and products at the boundary)
and its origin, computed from where the file came from:

    run       exported by openFerment from a run of the project (`export`)
    library   one of the toolkit's reference flowsheets at the pinned commit,
              known by its sha256 whichever door it came through
    imported  any other file a person brought (`import_sff`)

The toolkit imports BioSTEAM, so validating, scoring and exporting are the
Proforma worker's ops (workers/sff_toolkit.py), reached through
engine/simulator.py; the graph is plain JSON and is read here.

The reference flowsheets are never committed. `sff_library.json` names each
file at the commit, with its sha256 and size; `fetch` brings one from GitHub
into core/data/sff-library/<commit>/ (OPENFERMENT_SFF_LIBRARY moves it) and
refuses a file that does not hash as pinned; the toolkit's verdict on a
fetched file is kept beside it, keyed by its hash and the toolkit's schema.

A record is a row of the project's `flowsheets` table: the record in
`body`, the file whole in `document`. The same file kept twice is one
record (its id is its hash); a run exported twice is one record (its id is
the run's).

    GET  /api/flowsheets                 the project's records, newest first, without their graphs
    GET  /api/flowsheets/{id}            one record, its graph included
    GET  /api/flowsheets/{id}/file       the file as it is held
    POST /api/flowsheets/import          an uploaded SFF file, checked and kept
    GET  /api/flowsheets/library         the reference flowsheets at the pinned commit
    POST /api/flowsheets/library/{id}    one fetched, checked and kept in the project
    POST /api/flowsheets/export          a run's base case exported, checked and kept

`python -m openferment_core.engine.sff fetch` brings every reference
flowsheet; `manifest <clone>` rewrites the manifest from a clone of the
toolkit at its pinned commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .. import db
from ..db import models as t
from ..db import rows
from ..models import (
    SFFBoundary,
    SFFCompleteness,
    SFFEdge,
    SFFFlowsheet,
    SFFGraph,
    SFFLibraryEntry,
    SFFNode,
    SFFTag,
    SFFValidation,
)
from . import simulator

CORE = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("sff_library.json")
REPOSITORY = "https://github.com/sustainability-software-lab/pisces-standard-flowsheet-format"
# The toolkit's sentinel for the plant's boundary in a stream's source or sink
# (validate/sff_checks.md, C-01): a feed comes from "None", a product goes to it.
BOUNDARY = "None"
# The largest file an import takes. Settings, not measurements: the toolkit's
# largest reference flowsheet is 1.1 MB.
MAX_FILE = 16 * 1024 * 1024
DOWNLOAD_TIMEOUT_S = 120.0
# The spellings of the units a graph reports flows and prices in. A file in
# the inline style (SFF 0.0.6 and before) writes each value's unit beside it;
# a later file writes one unit per quantity in `quantity_units_global`. A
# value in any other unit is left out of the graph, never converted here.
MASS_FLOW_UNITS = frozenset({"kg/hr", "kg/h"})
PRICE_UNITS = frozenset({"USD/kg", "$/kg"})


class SFFRefused(ValueError):
    """The file or the request cannot be taken, in words."""


class FlowsheetNotFound(KeyError):
    pass


class LibraryUnavailable(RuntimeError):
    """A reference flowsheet could not be fetched, or did not hash as pinned."""


# ── the reference flowsheets ───────────────────────────────────────────


@dataclass(frozen=True)
class LibraryFile:
    """One file of the toolkit's repository at the pinned commit."""

    id: str
    path: str
    sha256: str
    bytes: int
    title: str = ""
    sffVersion: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class Manifest:
    repository: str
    revision: str
    schema: str
    licence: str
    registry: LibraryFile
    flowsheets: tuple[LibraryFile, ...]

    def url(self, path: str) -> str:
        owner_repo = self.repository.removeprefix("https://github.com/").rstrip("/")
        return f"https://raw.githubusercontent.com/{owner_repo}/{self.revision}/{path}"

    def file(self, file_id: str) -> LibraryFile:
        for f in (*self.flowsheets, self.registry):
            if f.id == file_id:
                return f
        raise FlowsheetNotFound(f"the toolkit's reference corpus has no {file_id}; it has "
                                f"{', '.join(f.id for f in self.flowsheets)}")


@cache
def manifest() -> Manifest:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return Manifest(
        repository=raw["repository"], revision=raw["revision"], schema=raw["schema"], licence=raw["licence"],
        registry=LibraryFile(**raw["registry"]),
        flowsheets=tuple(LibraryFile(**f) for f in raw["flowsheets"]),
    )


def _library_by_sha() -> dict[str, LibraryFile]:
    return {f.sha256: f for f in manifest().flowsheets}


def _from_root(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (CORE.parent / path).resolve()


def library_root() -> Path:
    """Where fetched reference files are kept, read at call time:
    OPENFERMENT_SFF_LIBRARY, else sff-library/ in the data directory."""
    raw = os.environ.get("OPENFERMENT_SFF_LIBRARY", "").strip()
    if raw:
        return _from_root(raw)
    data = os.environ.get("OPENFERMENT_DATA_DIR", "").strip()
    return (_from_root(data) if data else CORE / "data") / "sff-library"


def local(f: LibraryFile) -> Path:
    return library_root() / manifest().revision / f.path


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _held(f: LibraryFile) -> bool:
    p = local(f)
    return p.is_file() and sha256_of(p.read_bytes()) == f.sha256


def download(url: str) -> bytes:
    """The bytes GitHub serves at `url`; a failure is said in words."""
    import httpx

    try:
        response = httpx.get(url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_S)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise LibraryUnavailable(f"{url} could not be fetched: {type(e).__name__}: {e}") from e
    return response.content


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def fetch(file_id: str, *, get: Callable[[str], bytes] = download) -> Path:
    """Bring one file of the reference corpus from the pinned commit and check
    its hash. A file already here that hashes as pinned is not fetched again;
    one that does not is set aside as `<name>.mismatch` and refused."""
    m = manifest()
    f = m.file(file_id)
    path = local(f)
    if _held(f):
        return path
    data = get(m.url(f.path))
    got = sha256_of(data)
    if got != f.sha256:
        aside = path.with_name(path.name + ".mismatch")
        _write(aside, data)
        raise LibraryUnavailable(
            f"{f.id}: the file at {m.revision[:12]} hashes to {got}, not the pinned {f.sha256}. It was set aside as "
            f"{aside.name} and is not used."
        )
    _write(path, data)
    return path


def library() -> list[SFFLibraryEntry]:
    """The reference flowsheets as the manifest names them, and which this
    machine holds. Nothing is fetched."""
    m = manifest()
    return [SFFLibraryEntry(id=f.id, title=f.title, sffVersion=f.sffVersion, sha256=f.sha256, bytes=f.bytes,
                            url=m.url(f.path), model=f.model, fetched=_held(f))
            for f in m.flowsheets]


def _library_source(f: LibraryFile) -> str:
    m = manifest()
    return f"the PISCES SFF reference flowsheet {f.id} ({m.repository} at {m.revision[:12]}, {m.licence})"


# ── the graph (read here: plain JSON) ───────────────────────────────────


def _global_unit(doc: dict[str, Any], quantity: str) -> str | None:
    entry = (doc.get("quantity_units_global") or {}).get(quantity)
    return entry.get("quantity_units") if isinstance(entry, dict) else None


def _value(raw: Any, allowed: frozenset[str], global_unit: str | None) -> float | None:
    """A number in one of the allowed units, from either style: an inline
    {value, units}, or a bare number in the file's global unit."""
    if isinstance(raw, dict):
        value, unit = raw.get("value"), raw.get("units")
    else:
        value, unit = raw, global_unit
    if isinstance(value, bool) or not isinstance(value, (int, float)) or unit not in allowed:
        return None
    value = float(value)
    return value if value == value and abs(value) != float("inf") else None


def _method(unit: dict[str, Any]) -> str | None:
    """The simulator's class for the unit, the first words of the toolkit's
    `design_simulation_method` ("FeedStockHandling on https://…")."""
    said = unit.get("design_simulation_method")
    if not isinstance(said, str):
        return None
    return said.split(" on ", 1)[0].strip() or None


def _ranks(order: list[str], edges: list[SFFEdge], starts: list[str]) -> dict[str, int]:
    """Each unit's column, left to right: a depth-first walk from the units
    the feeds enter (then from any unit not yet reached, in the file's
    order) sets aside the streams that close a recycle, and each unit then
    stands one column right of the furthest unit feeding it."""
    succ: dict[str, list[str]] = {n: [] for n in order}
    for e in edges:
        succ[e.source].append(e.sink)
    state: dict[str, int] = {}
    back: set[tuple[str, str]] = set()
    post: list[str] = []
    for root in [*starts, *order]:
        if root in state:
            continue
        state[root] = 1
        stack = [(root, iter(succ[root]))]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                state[node] = 2
                post.append(node)
                stack.pop()
            elif nxt not in state:
                state[nxt] = 1
                stack.append((nxt, iter(succ[nxt])))
            elif state[nxt] == 1:
                back.add((node, nxt))
    rank = dict.fromkeys(order, 0)
    for node in reversed(post):
        for nxt in succ[node]:
            if (node, nxt) not in back:
                rank[nxt] = max(rank[nxt], rank[node] + 1)
    return rank


def graph(doc: dict[str, Any]) -> SFFGraph:
    """The flowsheet as the UI draws it: every unit a node, every stream
    between two units an edge, every stream crossing the boundary a feed or
    a product. A stream that names a unit the file does not list is counted
    in `dangling` and not drawn."""
    units = [u for u in doc.get("units") or [] if isinstance(u, dict) and isinstance(u.get("id"), str)]
    known = {u["id"] for u in units}
    meta = doc.get("metadata") or {}
    names = {}
    for key in ("feedstocks", "products"):
        for item in meta.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("stream_id"), str):
                names[item["stream_id"]] = item.get("display_name")
    flow_unit, price_unit = _global_unit(doc, "mass_flow"), _global_unit(doc, "price")
    edges: list[SFFEdge] = []
    feeds: list[SFFBoundary] = []
    products: list[SFFBoundary] = []
    dangling: list[str] = []
    for s in doc.get("streams") or []:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str):
            continue
        src, sink = str(s.get("source_unit_id")), str(s.get("sink_unit_id"))
        flow = _value((s.get("stream_properties") or {}).get("total_mass_flow"), MASS_FLOW_UNITS, flow_unit)
        if src == BOUNDARY and sink == BOUNDARY:
            continue  # neither enters nor leaves a unit: the toolkit holds its flows at zero (C-02)
        if (src != BOUNDARY and src not in known) or (sink != BOUNDARY and sink not in known):
            dangling.append(s["id"])
        elif src == BOUNDARY:
            feeds.append(SFFBoundary(id=s["id"], unit=sink, name=names.get(s["id"]), massFlow=flow,
                                     price=_value(s.get("price"), PRICE_UNITS, price_unit)))
        elif sink == BOUNDARY:
            products.append(SFFBoundary(id=s["id"], unit=src, name=names.get(s["id"]), massFlow=flow,
                                        price=_value(s.get("price"), PRICE_UNITS, price_unit)))
        else:
            edges.append(SFFEdge(id=s["id"], source=src, sink=sink, massFlow=flow))
    order = [u["id"] for u in units]
    rank = _ranks(order, edges, list(dict.fromkeys(f.unit for f in feeds)))
    nodes = [SFFNode(id=u["id"], type=str(u.get("unit_type") or ""), method=_method(u), rank=rank[u["id"]])
             for u in units]
    return SFFGraph(nodes=nodes, edges=edges, feeds=feeds, products=products, dangling=dangling)


def title_of(doc: dict[str, Any], fallback: str) -> str:
    """The file's own title, else its named feedstocks and products, else
    `fallback`."""
    meta = doc.get("metadata") or {}
    said = meta.get("process_title")
    if isinstance(said, str) and said.strip():
        return said.strip()

    def named(key: str) -> list[str]:
        return [str(i.get("display_name") or i.get("stream_id")) for i in meta.get(key) or []
                if isinstance(i, dict) and (i.get("display_name") or i.get("stream_id"))]

    ins, outs = named("feedstocks"), named("products")
    if ins or outs:
        return f"{' + '.join(ins) or '?'} → {' + '.join(outs) or '?'}"
    return fallback


def parsed(data: bytes, name: str) -> tuple[str, dict[str, Any]]:
    """The file as text and as JSON, refused in words when it is not a file
    the graph can be read from: UTF-8 JSON, an object with `units` and
    `streams` lists."""
    if len(data) > MAX_FILE:
        raise SFFRefused(f"{name} is larger than {MAX_FILE // (1024 * 1024)} MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SFFRefused(f"{name} is not UTF-8 text; an SFF file is JSON") from None
    try:
        doc = json.loads(text)
    except ValueError as e:
        raise SFFRefused(f"{name} is not JSON: {e}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("units"), list) or not isinstance(doc.get("streams"), list):
        raise SFFRefused(f"{name} is not an SFF flowsheet: an SFF file is a JSON object with a list of units and a "
                         "list of streams")
    return text, doc


# ── what the toolkit says (in the worker) ───────────────────────────────


def _checked(path: Path) -> dict[str, Any]:
    v = simulator.call("sff_validate", {"path": str(path)})
    s = simulator.call("sff_score", {"path": str(path)})
    return {"validation": {k: v[k] for k in ("valid", "schemaVersion", "summary", "findings")},
            "completeness": s["completeness"], "tags": s["tags"], "toolkit": f"pisces_sff {v['schemaVersion']}"}


def _checked_library(f: LibraryFile, path: Path) -> dict[str, Any]:
    """The toolkit's verdict on a fetched reference file, kept beside it and
    keyed by the file's hash and the toolkit's schema: a file is checked once
    per toolkit."""
    kept = path.with_name(path.name + ".checked.json")
    if kept.is_file():
        try:
            said = json.loads(kept.read_text(encoding="utf-8"))
        except ValueError:
            said = {}
        if said.get("sha256") == f.sha256 and said.get("schema") == manifest().schema:
            return said["checked"]
    checked = _checked(path)
    _write(kept, json.dumps({"sha256": f.sha256, "schema": manifest().schema, "checked": checked}).encode("utf-8"))
    return checked


# ── records ────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _record(doc: dict[str, Any], data: bytes, checked: dict[str, Any], *, record_id: str, origin: str, source: str,
            fallback_title: str, by: str, run_artifact_id: str | None = None, library_id: str | None = None,
            simulator_said: str | None = None) -> SFFFlowsheet:
    meta = doc.get("metadata") or {}
    sim = meta.get("process_simulator")
    if simulator_said is None and isinstance(sim, dict) and sim.get("name"):
        simulator_said = f"{sim['name']} {sim.get('version') or ''}".strip()
    version = meta.get("sff_version")
    return SFFFlowsheet(
        id=record_id, title=title_of(doc, fallback_title), origin=origin, source=source,
        sffVersion=version if isinstance(version, str) else None, sha256=sha256_of(data), bytes=len(data),
        simulator=simulator_said, runArtifactId=run_artifact_id, libraryId=library_id,
        units=len(doc.get("units") or []), streams=len(doc.get("streams") or []),
        validation=SFFValidation.model_validate(checked["validation"]),
        completeness=SFFCompleteness.model_validate(checked["completeness"]),
        tags={k: SFFTag.model_validate(v) for k, v in checked["tags"].items()},
        graph=graph(doc), toolkit=checked["toolkit"], createdBy=by, createdAt=_now(),
    )


async def _get(project_id: str, record_id: str) -> SFFFlowsheet | None:
    async with db.session() as s:
        body = await rows.body(s, t.flowsheets, project_id, record_id)
    return SFFFlowsheet.model_validate(body) if body is not None else None


async def _put(project_id: str, record: SFFFlowsheet, text: str) -> SFFFlowsheet:
    async with db.session() as s:
        await rows.put(s, t.flowsheets, project_id, record.id, record.model_dump(mode="json"), by=record.createdBy,
                       schema_version=record.sffVersion or "unstated", recipe=None, origin=record.origin,
                       sha256=record.sha256, document=text)
    return record


async def _listed(project_id: str) -> list[SFFFlowsheet]:
    async with db.session() as s:
        bodies = await rows.bodies(s, t.flowsheets, project_id, order=(t.flowsheets.c.created_at.desc(),
                                                                       t.flowsheets.c.id))
    return [SFFFlowsheet.model_validate({**b, "graph": None}) for b in bodies]


async def _document(project_id: str, record_id: str) -> str | None:
    async with db.session() as s:
        q = select(t.flowsheets.c.document).where(t.flowsheets.c.project_id == project_id,
                                                  t.flowsheets.c.id == record_id)
        return (await s.execute(q)).scalar_one_or_none()


def get(record_id: str, *, project_id: str) -> SFFFlowsheet:
    found = db.run(_get(project_id, record_id))
    if found is None:
        raise FlowsheetNotFound(f"the project holds no flowsheet {record_id}")
    return found


def listed(*, project_id: str) -> list[SFFFlowsheet]:
    """The project's records, newest first, without their graphs."""
    return db.run(_listed(project_id))


def document(record_id: str, *, project_id: str) -> str:
    """The file as it is held, byte for byte as it came."""
    found = db.run(_document(project_id, record_id))
    if found is None:
        raise FlowsheetNotFound(f"the project holds no flowsheet {record_id}")
    return found


def import_sff(data: bytes, filename: str, *, project_id: str, by: str) -> SFFFlowsheet:
    """An SFF file kept in the project: read, checked by the toolkit in the
    worker (validated and scored; a file that fails validation is kept with
    its findings), drawn, and stored. Its origin is `library` when its hash
    is one of the reference flowsheets', else `imported`. The same file kept
    again is the record already held."""
    name = filename or "the file"
    text, doc = parsed(data, name)
    sha = sha256_of(data)
    record_id = f"sff-{sha[:16]}"
    held = db.run(_get(project_id, record_id))
    if held is not None:
        return held
    lib = _library_by_sha().get(sha)
    with tempfile.TemporaryDirectory(prefix="openferment-sff-") as tmp:
        path = Path(tmp) / "flowsheet.json"
        path.write_bytes(data)
        if lib is not None:
            checked = _checked_library(lib, local(lib)) if _held(lib) else _checked(path)
        else:
            checked = _checked(path)
    if lib is not None:
        record = _record(doc, data, checked, record_id=record_id, origin="library", source=_library_source(lib),
                         fallback_title=lib.id, by=by, library_id=lib.id)
    else:
        record = _record(doc, data, checked, record_id=record_id, origin="imported",
                         source=f"the file {name}, imported", fallback_title=Path(name).stem or record_id, by=by)
    return db.run(_put(project_id, record, text))


def import_library(file_id: str, *, project_id: str, by: str, get: Callable[[str], bytes] = download) -> SFFFlowsheet:
    """A reference flowsheet fetched (or found here), checked and kept in the
    project, with origin `library`."""
    f = manifest().file(file_id)
    if f is manifest().registry:
        raise SFFRefused(f"{file_id} is the toolkit's model registry, not a flowsheet")
    path = fetch(file_id, get=get)
    return import_sff(path.read_bytes(), Path(f.path).name, project_id=project_id, by=by)


def library_flowsheet(file_id: str, *, get: Callable[[str], bytes] = download) -> SFFFlowsheet:
    """One reference flowsheet loaded as a record with origin `library`,
    kept in no project: fetched and checked here, its verdict kept beside it."""
    m = manifest()
    f = m.file(file_id)
    if f is m.registry:
        raise SFFRefused(f"{file_id} is the toolkit's model registry, not a flowsheet")
    path = fetch(file_id, get=get)
    data = path.read_bytes()
    _, doc = parsed(data, f.id)
    return _record(doc, data, _checked_library(f, path), record_id=f"sff-{f.sha256[:16]}", origin="library",
                   source=_library_source(f), fallback_title=f.id, by=f"the toolkit at {m.revision[:12]}",
                   library_id=f.id)


def library_flowsheets(ids: list[str] | None = None, *, get: Callable[[str], bytes] = download) -> list[SFFFlowsheet]:
    """The reference flowsheets loaded as records with origin `library`: every
    one the manifest names, or those asked for."""
    return [library_flowsheet(i, get=get) for i in (ids or [f.id for f in manifest().flowsheets])]


def export(plant: dict[str, Any], *, project_id: str, run_artifact_id: str, by: str,
           title: str | None = None) -> SFFFlowsheet:
    """A run's base case written as an SFF file by the toolkit in the worker,
    checked there, drawn and kept with origin `run`. `plant` is what the
    worker builds the base case from: the shelf flowsheet's id and, for a
    flowsheet run case by case, its base values (and a structured
    flowsheet's structure). The file's metadata carries openFerment's block
    (docs/api/sff.md): the project, the run's artifact and the origin."""
    flowsheet = str(plant.get("flowsheet") or "")
    if not flowsheet:
        raise SFFRefused("an export names the flowsheet whose base case it writes")
    meta = {"project_id": project_id, "run_artifact_id": run_artifact_id, "origin": "run", "flowsheet": flowsheet}
    with tempfile.TemporaryDirectory(prefix="openferment-sff-") as tmp:
        path = Path(tmp) / f"{run_artifact_id}.sff.json"
        out = simulator.call("sff_export", {**plant, "path": str(path), "metadata": meta, "title": title})
        data = path.read_bytes()
    text, doc = parsed(data, f"the export of run {run_artifact_id}")
    checked = {"validation": out["validation"], "completeness": out["completeness"], "tags": out["tags"],
               "toolkit": out["toolkit"]}
    record = _record(doc, data, checked, record_id=f"run-{run_artifact_id}", origin="run",
                     source=f"exported from run {run_artifact_id} of {flowsheet}", fallback_title=flowsheet, by=by,
                     run_artifact_id=run_artifact_id, simulator_said=out.get("simulator"))
    return db.run(_put(project_id, record, text))


# ── the command line ────────────────────────────────────────────────────


def write_manifest(clone: Path, *, repository: str, revision: str, licence: str = "MIT") -> dict[str, Any]:
    """The manifest of the reference corpus, read from a clone of the toolkit
    at `revision`: each exported flowsheet's path, hash, size, title and SFF
    version, the model registry's hash, and the model each flowsheet is
    paired with in it."""
    import yaml

    pkg = clone / "pisces_sff"
    schema = json.loads((pkg / "schema" / "sff_schema.json").read_text(encoding="utf-8"))["version"]
    registry_path = pkg / "export" / "models" / "all_models.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    paired = {entry.get("flowsheet"): model for model, entry in (registry.get("models") or {}).items()}

    def rel(p: Path) -> str:
        return p.relative_to(clone).as_posix()

    flowsheets = []
    for p in sorted((pkg / "export" / "exported_flowsheets").rglob("SF_*.json")):
        data = p.read_bytes()
        doc = json.loads(data)
        version = (doc.get("metadata") or {}).get("sff_version")
        flowsheets.append({"id": p.stem, "path": rel(p), "sha256": sha256_of(data), "bytes": len(data),
                           "title": title_of(doc, p.stem), "sffVersion": version, "model": paired.get(p.stem)})
    reg = registry_path.read_bytes()
    out = {
        "repository": repository, "revision": revision, "schema": schema, "licence": licence,
        "registry": {"id": "all_models", "path": rel(registry_path), "sha256": sha256_of(reg), "bytes": len(reg)},
        "flowsheets": flowsheets,
    }
    MANIFEST.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest.cache_clear()
    return out


def main(argv: list[str]) -> int:
    if argv[:1] == ["fetch"] and len(argv) == 1:
        status = 0
        for f in (*manifest().flowsheets, manifest().registry):
            try:
                path = fetch(f.id)
            except LibraryUnavailable as e:
                print(f"✗ {e}", file=sys.stderr)
                status = 1
                continue
            print(f"✓ {f.id}: {path}, sha256 {f.sha256}")
        return status
    if argv[:1] == ["manifest"] and len(argv) == 2:
        import subprocess

        clone = Path(argv[1])
        revision = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], check=True, capture_output=True,
                                  text=True).stdout.strip()
        out = write_manifest(clone, repository=REPOSITORY, revision=revision)
        print(f"{MANIFEST.name}: {len(out['flowsheets'])} flowsheets at {out['revision'][:12]}, schema {out['schema']}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
