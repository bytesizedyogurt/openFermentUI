"""What was computed is kept and can be replayed (OF-BLD-014 §3.2, E.5).

Every calculation from §3.4 on goes through `compute`: a tool registers a pure
function from its inputs to a small output, and `compute` runs it once per
distinct (tool, version, inputs, seed), writes the result to
`core/data/artifacts/<id>.json` and returns it. The same call again returns
the stored artifact and computes nothing. `replay` runs the registered
function again on the stored inputs and says whether the output is the same.

The artifact's provenance is `basis.basis_provenance` over its inputs, read
when it is computed; no caller sets it.

    GET  /api/biorepo/artifacts
    GET  /api/biorepo/artifacts/{id}
    POST /api/biorepo/artifacts/{id}/replay

The folder is gitignored and travels on the data branch (E.10). One
exception: a calculation over a labelled sample is returned inline and kept
nowhere (§7.4), which is `compute(..., keep=False)`.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import atomic, intake
from .basis import basis_provenance
from .models import Artifact, BasisInput, ComputedBasis, ReplayDifference, ReplayResult

# The function a tool registers: its inputs and seed in, a JSON-ready dict out.
# It must be pure: the same inputs give the same output, or replay will say so.
ToolFn = Callable[[list[BasisInput], "int | None"], dict[str, Any]]

ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

# A difference list longer than this is cut, and the cut is said in the last
# entry: a page can show it, and the whole output is in the artifact anyway.
MAX_DIFFERENCES = 50


class ArtifactNotFound(KeyError):
    pass


class ToolNotRegistered(LookupError):
    pass


@dataclass(frozen=True)
class Registered:
    tool: str
    version: str
    fn: ToolFn


_REGISTRY: dict[str, Registered] = {}
_LOCK = threading.Lock()


def folder() -> Path:
    """Read at call time, so a test that points `intake.DATA_DIR` elsewhere
    moves the store with it."""
    return intake.DATA_DIR / "artifacts"


def register(tool: str, version: str, fn: ToolFn) -> None:
    """Make `tool` computable and replayable. Registering a name again replaces
    it: that is how a tool's code changes between versions."""
    _REGISTRY[tool] = Registered(tool, version, fn)


def registered(tool: str) -> Registered:
    try:
        return _REGISTRY[tool]
    except KeyError:
        raise ToolNotRegistered(
            f"no tool named {tool!r} is registered in this service, so it cannot compute or replay it"
        ) from None


# ── canonical forms ────────────────────────────────────────────────────


def canonical(value: Any) -> str:
    """JSON with sorted keys and no spaces: one text per value."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def artifact_id(tool: str, version: str, inputs: Sequence[BasisInput], seed: int | None = None) -> str:
    """First 16 hex of sha256 over tool, version and the canonical inputs.
    A seed joins the hash when there is one, so two samples drawn with
    different seeds are two artifacts."""
    payload: dict[str, Any] = {
        "tool": tool,
        "toolVersion": version,
        "inputs": [i.model_dump(mode="json") for i in inputs],
    }
    if seed is not None:
        payload["seed"] = seed
    return _sha(canonical(payload))[:16]


def output_hash(output: Mapping[str, Any]) -> str:
    return _sha(canonical(output))


# ── the store ──────────────────────────────────────────────────────────


def _path(aid: str) -> Path:
    if not ID_PATTERN.match(aid):
        # Ids are hex: anything else could name a path outside the folder.
        raise ArtifactNotFound(aid)
    return folder() / f"{aid}.json"


def get(aid: str) -> Artifact:
    path = _path(aid)
    try:
        return Artifact.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ArtifactNotFound(aid) from None


def all_artifacts() -> list[Artifact]:
    """Every stored artifact, newest first. A file that does not parse is
    skipped, so one bad file never hides the rest."""
    out: list[Artifact] = []
    root = folder()
    if not root.is_dir():
        return out
    for path in root.glob("*.json"):
        if not ID_PATTERN.match(path.stem):
            continue
        try:
            out.append(Artifact.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    out.sort(key=lambda a: (a.createdAt, a.id), reverse=True)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _run(reg: Registered, inputs: list[BasisInput], seed: int | None) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    output = reg.fn([i.model_copy(deep=True) for i in inputs], seed)
    if not isinstance(output, dict):
        raise TypeError(f"tool {reg.tool!r} returned {type(output).__name__}, expected a dict")
    canonical(output)  # raises on anything JSON cannot hold, before it is stored
    return output, int(round((time.perf_counter() - started) * 1000))


def compute(
    tool: str,
    inputs: Sequence[BasisInput],
    *,
    records_by_id: Mapping[str, Any] | None = None,
    seed: int | None = None,
    keep: bool = True,
) -> Artifact:
    """Run `tool` on `inputs`, or return what an identical call stored.

    `records_by_id` supplies the provenance of every `record` input; when it
    is None and a record input is present, the corpus is read. An artifact
    input's provenance is read from this store. `keep=False` computes and
    returns without writing, for a labelled sample (§7.4).
    """
    reg = registered(tool)
    inputs = list(inputs)
    aid = artifact_id(reg.tool, reg.version, inputs, seed)
    if keep:
        try:
            return get(aid)
        except ArtifactNotFound:
            pass

    output, ms = _run(reg, inputs, seed)
    basis = ComputedBasis(tool=reg.tool, toolVersion=reg.version, inputs=inputs, artifactId=aid, at=_now(), seed=seed)
    artifact = Artifact(
        id=aid,
        tool=reg.tool,
        toolVersion=reg.version,
        inputs=inputs,
        output=output,
        outputHash=output_hash(output),
        provenance=basis_provenance(basis, _records_for(inputs, records_by_id), _artifacts_for(inputs)),
        createdAt=basis.at,
        durationMs=ms,
        seed=seed,
    )
    if not keep:
        return artifact
    path = _path(aid)
    with _LOCK, atomic.held(path):
        # Two callers may have computed the same thing at once. The first to
        # write wins and both return its file, so there is one artifact.
        if path.exists():
            return get(aid)
        atomic.write_text(path, artifact.model_dump_json(indent=2) + "\n")
    return artifact


def basis_of(artifact: Artifact) -> ComputedBasis:
    """The basis a value computed by `artifact` carries."""
    return ComputedBasis(
        tool=artifact.tool,
        toolVersion=artifact.toolVersion,
        inputs=artifact.inputs,
        artifactId=artifact.id,
        at=artifact.createdAt,
        seed=artifact.seed,
    )


def _records_for(inputs: Sequence[BasisInput], given: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if given is not None or not any(i.source.kind == "record" for i in inputs):
        return given or {}
    from .corpus import load_corpus

    return load_corpus().records_by_id


def _artifacts_for(inputs: Sequence[BasisInput]) -> dict[str, Artifact]:
    found: dict[str, Artifact] = {}
    for i in inputs:
        if i.source.kind == "artifact" and i.source.id:
            try:
                found[i.source.id] = get(i.source.id)
            except ArtifactNotFound:
                pass  # missing → basis_provenance reads it as the weakest there is
    return found


# ── replay ─────────────────────────────────────────────────────────────


def _diff(stored: Any, replayed: Any, path: str, out: list[ReplayDifference]) -> None:
    if len(out) > MAX_DIFFERENCES:
        return
    if isinstance(stored, dict) and isinstance(replayed, dict):
        for k in sorted(set(stored) | set(replayed)):
            sub = f"{path}.{k}" if path else str(k)
            if k not in stored:
                out.append(ReplayDifference(path=sub, stored=None, replayed=replayed[k]))
            elif k not in replayed:
                out.append(ReplayDifference(path=sub, stored=stored[k], replayed=None))
            else:
                _diff(stored[k], replayed[k], sub, out)
        return
    if isinstance(stored, list) and isinstance(replayed, list) and len(stored) == len(replayed):
        for n, (a, b) in enumerate(zip(stored, replayed)):
            _diff(a, b, f"{path}[{n}]", out)
        return
    if canonical(stored) != canonical(replayed):
        out.append(ReplayDifference(path=path, stored=stored, replayed=replayed))


def replay(aid: str) -> ReplayResult:
    """Recompute a stored artifact with the tool registered now, and compare.
    The stored file is never changed by a replay."""
    artifact = get(aid)
    reg = registered(artifact.tool)
    output, ms = _run(reg, artifact.inputs, artifact.seed)
    replayed = output_hash(output)
    differences: list[ReplayDifference] = []
    if replayed != artifact.outputHash:
        _diff(artifact.output, output, "", differences)
        if len(differences) > MAX_DIFFERENCES:
            differences = differences[:MAX_DIFFERENCES]
            differences.append(ReplayDifference(path="…", stored="more differences not listed", replayed=None))
        if reg.version != artifact.toolVersion:
            differences.insert(
                0, ReplayDifference(path="toolVersion", stored=artifact.toolVersion, replayed=reg.version)
            )
    return ReplayResult(
        artifactId=aid,
        identical=replayed == artifact.outputHash,
        storedHash=artifact.outputHash,
        replayedHash=replayed,
        differences=differences,
        durationMs=ms,
    )
