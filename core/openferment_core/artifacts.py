"""What was computed is kept and can be replayed (OF-BLD-014 §3.2, E.5).

Every calculation from §3.4 on goes through `compute`: a tool registers a pure
function from its inputs to a small output, and `compute` runs it once per
distinct (tool, version, inputs, seed) in a project, keeps the result as a row
of the `artifacts` table under the current project (ADR-001) and returns it.
The same call again returns the stored artifact and computes nothing.
`replay` runs the registered function again on the stored inputs and says
whether the output is the same.

The artifact's provenance is `basis.basis_provenance` over its inputs, read
when it is computed; no caller sets it.

    GET  /api/biorepo/artifacts
    GET  /api/biorepo/artifacts/{id}
    POST /api/biorepo/artifacts/{id}/replay

A row's key is the project and the artifact's id; its columns name the
tool, the version and the output's hash, and its body is the artifact whole.
The tool's function runs outside any transaction; keeping its result is one
short transaction under the store's advisory lock. One exception: a
calculation over a labelled sample is returned inline and kept nowhere (§7.4),
which is `compute(..., keep=False)`.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from sqlalchemy import func, select

from . import db, events, projects
from .basis import basis_provenance
from .db import models as t
from .db import rows
from .models import Artifact, BasisInput, ComputedBasis, ReplayDifference, ReplayResult, ReplayTolerance

# The function a tool registers: its inputs and seed in, a JSON-ready dict out.
# It must be pure: the same inputs give the same output, or replay will say so.
ToolFn = Callable[[list[BasisInput], "int | None"], dict[str, Any]]

ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

# A difference list longer than this is cut, and the cut is said in the last
# entry: a page can show it, and the whole output is in the artifact anyway.
MAX_DIFFERENCES = 50


class ArtifactNotFound(KeyError):
    pass


class ArtifactDamaged(ValueError):
    """A stored row whose body does not read as an artifact."""


class ToolNotRegistered(LookupError):
    pass


@dataclass(frozen=True)
class Registered:
    tool: str
    version: str
    fn: ToolFn
    # A tool whose version depends on what it computes (fermOS's simulation
    # names its family, OF-BLD-020 §3.1) reads it from the inputs.
    version_of: Callable[[Sequence[BasisInput]], str] | None = None
    # A tool whose basis states the precision its numbers keep (a library
    # run's significant digits) reads the tolerance a replay holds them to.
    tolerance_of: Callable[[Sequence[BasisInput]], ReplayTolerance] | None = None

    def version_for(self, inputs: Sequence[BasisInput]) -> str:
        return self.version_of(inputs) if self.version_of is not None else self.version


_REGISTRY: dict[str, Registered] = {}
# A tool whose version cannot be known at import (it reads a file that may not
# exist yet) registers a function that registers it, run on first use.
_LAZY: dict[str, Callable[[], None]] = {}


def register(tool: str, version: str, fn: ToolFn,
             version_of: Callable[[Sequence[BasisInput]], str] | None = None,
             tolerance_of: Callable[[Sequence[BasisInput]], ReplayTolerance] | None = None) -> None:
    """Make `tool` computable and replayable. Registering a name again replaces
    it: that is how a tool's code changes between versions. `version_of`,
    when given, reads the version from the inputs, so one tool name can
    carry what it computes in its version (`version` is then its stem).
    `tolerance_of` reads the precision the basis states, which a replay
    holds each number to."""
    _REGISTRY[tool] = Registered(tool, version, fn, version_of, tolerance_of)


def register_lazy(tool: str, registrar: Callable[[], None]) -> None:
    """`registrar()` calls `register(tool, ...)` the first time `tool` is
    computed or replayed."""
    _LAZY[tool] = registrar


def registered(tool: str) -> Registered:
    if tool not in _REGISTRY and tool in _LAZY:
        _LAZY[tool]()
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


def _checked(aid: str) -> str:
    if not ID_PATTERN.match(aid):
        # Ids are hex: anything else names no artifact.
        raise ArtifactNotFound(aid)
    return aid


def _valid(aid: str, raw: Any) -> Artifact:
    """A stored body as an artifact, or ArtifactDamaged in words naming it."""
    try:
        return Artifact.model_validate(raw)
    except ValueError as e:
        raise ArtifactDamaged(
            f"artifact {aid} is damaged on disk (its row in the artifact store): {e}".splitlines()[0]
        ) from None


async def _get(project_id: str, aid: str) -> Artifact:
    async with db.session() as s:
        raw = await rows.body(s, t.artifacts, project_id, aid)
    if raw is None:
        raise ArtifactNotFound(aid)
    return _valid(aid, raw)


def get(aid: str) -> Artifact:
    """One artifact of the current project."""
    return db.run(_get(projects.current(), _checked(aid)))


async def _all(project_id: str) -> list[Artifact]:
    async with db.session() as s:
        found = (await s.execute(select(t.artifacts.c.body).where(t.artifacts.c.project_id == project_id))).scalars()
        bodies = list(found)
    out: list[Artifact] = []
    for raw in bodies:
        try:
            out.append(Artifact.model_validate(raw))
        except ValueError:
            continue
    out.sort(key=lambda a: (a.createdAt, a.id), reverse=True)
    return out


def all_artifacts() -> list[Artifact]:
    """Every artifact of the current project, newest first. A row that does
    not read as an artifact is skipped, so one damaged row never hides the
    rest."""
    return db.run(_all(projects.current()))


async def _count() -> int:
    async with db.session() as s:
        return int((await s.execute(select(func.count()).select_from(t.artifacts))).scalar_one())


def count() -> int:
    """How many artifacts the database keeps, every project's together: the
    machine's figure `pnpm ready` reports."""
    return db.run(_count())


async def _keep(project_id: str, artifact: Artifact, *, replace: bool) -> Artifact:
    """Keep `artifact` under the store's lock. Two callers that computed the
    same thing at once both return the row the first one wrote, so there is
    one artifact; `replace` writes over the row (a provenance brought up to
    date)."""
    async with db.session() as s:
        await db.lock(s, "artifacts", project_id)
        if not replace:
            raw = await rows.body(s, t.artifacts, project_id, artifact.id)
            if raw is not None:
                return _valid(artifact.id, raw)
        await rows.put(
            s, t.artifacts, project_id, artifact.id, artifact.model_dump(mode="json"), by="system",
            tool=artifact.tool, version=artifact.toolVersion, output_hash=artifact.outputHash,
        )
    return artifact


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
    version = reg.version_for(inputs)
    aid = artifact_id(reg.tool, version, inputs, seed)
    records = _records_for(inputs, records_by_id)
    if keep:
        try:
            stored = get(aid)
        except ArtifactNotFound:
            stored = None
        if stored is not None:
            # The output is the same; the provenance is what the inputs are
            # worth now. A record demoted since the first computation demotes
            # the value, and the stored row is brought up to date (§3.R).
            now = basis_provenance(basis_of(stored), records, _artifacts_for(inputs))
            if now == stored.provenance:
                return stored
            updated = stored.model_copy(update={"provenance": now})
            return db.run(_keep(projects.current(), updated, replace=True))

    output, ms = _run(reg, inputs, seed)
    basis = ComputedBasis(tool=reg.tool, toolVersion=version, inputs=inputs, artifactId=aid, at=_now(), seed=seed)
    artifact = Artifact(
        id=aid,
        tool=reg.tool,
        toolVersion=version,
        inputs=inputs,
        output=output,
        outputHash=output_hash(output),
        provenance=basis_provenance(basis, records, _artifacts_for(inputs)),
        createdAt=basis.at,
        durationMs=ms,
        seed=seed,
    )
    if not keep:
        return artifact
    kept = db.run(_keep(projects.current(), artifact, replace=False))
    events.publish("artifact.kept", {"id": kept.id, "tool": kept.tool, "toolVersion": kept.toolVersion,
                                     "provenance": kept.provenance, "durationMs": kept.durationMs})
    return kept


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


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _within(stored: Any, replayed: Any, tol: ReplayTolerance) -> bool:
    """Whether a replayed output is the stored one with every number within
    the tolerance (|replayed − stored| ≤ atol + rtol·|stored|) and all else
    the same."""
    if isinstance(stored, dict) and isinstance(replayed, dict):
        return stored.keys() == replayed.keys() and all(_within(stored[k], replayed[k], tol) for k in stored)
    if isinstance(stored, list) and isinstance(replayed, list):
        return len(stored) == len(replayed) and all(_within(a, b, tol) for a, b in zip(stored, replayed))
    if _number(stored) and _number(replayed):
        return abs(replayed - stored) <= tol.atol + tol.rtol * abs(stored)
    return canonical(stored) == canonical(replayed)


def replay(aid: str) -> ReplayResult:
    """Recompute a stored artifact with the tool registered now, and compare:
    identical, or within the precision its basis states when the tool reads
    one (`tolerance_of`). A replay changes nothing stored."""
    artifact = get(aid)
    reg = registered(artifact.tool)
    try:
        output, ms = _run(reg, artifact.inputs, artifact.seed)
    except Exception as e:
        # The tool now refuses what it once computed (a unit table changed,
        # say). That is a difference to show, not a crash (§3.R).
        said = f"the tool refused: {type(e).__name__}: {e}"
        return ReplayResult(
            artifactId=aid,
            identical=False,
            storedHash=artifact.outputHash,
            replayedHash="",
            differences=[ReplayDifference(path="", stored=artifact.output, replayed=said)],
            durationMs=0,
        )
    replayed = output_hash(output)
    tolerance = reg.tolerance_of(artifact.inputs) if reg.tolerance_of is not None else None
    differences: list[ReplayDifference] = []
    if replayed != artifact.outputHash:
        _diff(artifact.output, output, "", differences)
        if len(differences) > MAX_DIFFERENCES:
            differences = differences[:MAX_DIFFERENCES]
            differences.append(ReplayDifference(path="…", stored="more differences not listed", replayed=None))
        now = reg.version_for(artifact.inputs)
        if now != artifact.toolVersion:
            differences.insert(
                0, ReplayDifference(path="toolVersion", stored=artifact.toolVersion, replayed=now)
            )
    identical = replayed == artifact.outputHash
    return ReplayResult(
        artifactId=aid,
        identical=identical,
        storedHash=artifact.outputHash,
        replayedHash=replayed,
        differences=differences,
        durationMs=ms,
        tolerance=tolerance,
        withinTolerance=identical or (tolerance is not None and _within(artifact.output, output, tolerance)),
    )
