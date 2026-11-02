"""SFF flowsheets, for Postdoc (alpha 2.1 stage B; ADR-003): the toolkit's
reference files, a reference file imported into the project, and a kept
record read back.

`flowsheet_library` lists the toolkit's reference flowsheets at the pinned
commit and which this machine holds. `flowsheet_import` brings one into the
project (`engine.sff.import_library`: fetched, its hash checked, checked by
the toolkit in the worker, drawn and kept with origin `library`) through
`writes.import_flowsheet`, which keeps it audited as its caller's.
`flowsheet_read` reads a record the project holds, or lists them by words.

A RECORD'S EVIDENCE. What the file's graph counts (its units, the streams
between them, its feeds and its products) and each feed's and product's mass
flow as the file states it is one Evidence whose id is `sff:<record id>:<key>`,
its basis the record: computed for a reference file or a run's export, which a
simulation wrote; unverified for any other file.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from ..models import ComputedBasis, Evidence, SFFFlowsheet, ToolResult
from . import Tool, ToolContext, register

MAX_ROWS = 20
MAX_TYPES = 12


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def record_evidence(record: SFFFlowsheet) -> list[Evidence]:
    """What a record's graph counts, and its boundary's mass flows as the file states them."""
    graph = record.graph
    basis = ComputedBasis(tool="engine.sff", toolVersion=record.toolkit, artifactId=record.id, at=record.createdAt,
                          inputs=[])
    provenance = "computed" if record.origin in ("library", "run") else "unverified"
    out: list[Evidence] = []

    def add(key: str, label: str, value: float, unit: str) -> None:
        out.append(Evidence(id=f"sff:{record.id}:{key}", label=f"{record.title}: {label}", value=value, unit=unit,
                            provenance=provenance, basis=basis))

    add("units", "the units the file lists", record.units, "")
    add("streams", "the streams the file lists", record.streams, "")
    if graph is not None:
        add("feeds", "the feeds at the plant's boundary", len(graph.feeds), "")
        add("products", "the products at the plant's boundary", len(graph.products), "")
        for side, ends in (("feed", graph.feeds), ("product", graph.products)):
            for end in ends:
                if _number(end.massFlow):
                    add(f"{side}.{end.id}.massFlow", f"the {side} {end.name or end.id}'s mass flow, as the file states it",
                        end.massFlow, graph.massFlowUnit)
    return out


def record_result(record: SFFFlowsheet, *, state: str = "open") -> ToolResult:
    """A record in a tool's words: what the file is, whether it is valid, and what its graph holds."""
    graph = record.graph
    evidence = record_evidence(record)
    summary: dict[str, Any] = {
        "state": state,
        "recordId": record.id,
        "title": record.title,
        "origin": record.origin,
        "source": record.source,
        "libraryId": record.libraryId,
        "runArtifactId": record.runArtifactId,
        "sffVersion": record.sffVersion,
        "simulator": record.simulator,
        "valid": record.validation.valid,
        "schemaVersion": record.validation.schemaVersion,
        "findings": [f"{x.severity}: {x.message}"[:200] for x in record.validation.findings[:6]],
        "evidence": [{"id": e.id, "label": e.label.split(": ", 1)[-1], "value": e.value, "unit": e.unit}
                     for e in evidence[:MAX_ROWS]],
    }
    if graph is not None:
        kinds = Counter(n.type for n in graph.nodes)
        summary["unitTypes"] = [{"type": t, "units": n} for t, n in kinds.most_common(MAX_TYPES)]
        summary["feeds"] = [e.name or e.id for e in graph.feeds][:MAX_ROWS]
        summary["products"] = [e.name or e.id for e in graph.products][:MAX_ROWS]
        summary["dangling"] = len(graph.dangling)
    return ToolResult(summary=summary, evidence=evidence)


# ── flowsheet_library ───────────────────────────────────────────────────


class FlowsheetLibraryInput(BaseModel):
    words: str = Field(default="", max_length=200,
                       description="Words to narrow the reference files by: a plant, a product, a file's id; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _library(inp: FlowsheetLibraryInput, ctx: ToolContext) -> ToolResult:
    from ..engine import sff

    words = [w for w in inp.words.lower().split() if w]
    rows = []
    for f in sff.library():
        said = f"{f.id} {f.title} {f.model or ''}".lower()
        if words and not all(w in said for w in words):
            continue
        rows.append({"id": f.id, "title": f.title, "sffVersion": f.sffVersion, "model": f.model, "fetched": f.fetched})
    return ToolResult(summary={"matched": len(rows), "files": rows[: inp.limit],
                               "note": "flowsheet_import brings one into the project by its id."})


# ── flowsheet_import ────────────────────────────────────────────────────


class FlowsheetImportInput(BaseModel):
    file: str = Field(max_length=80, description="A reference file's id, as flowsheet_library gives it (e.g. SF_BST_15).")
    note: str = Field(default="", max_length=600, description="Why it is imported, in words.")


def _import(inp: FlowsheetImportInput, ctx: ToolContext) -> ToolResult:
    from .writes import import_flowsheet

    return import_flowsheet("flowsheet_import", inp.file, inp.note, ctx)


# ── flowsheet_read ──────────────────────────────────────────────────────


class FlowsheetReadInput(BaseModel):
    record: str = Field(default="", max_length=80,
                        description="A kept record's id (flowsheet_import or engine_run gives it); empty to list them.")
    words: str = Field(default="", max_length=200, description="Words to narrow the list by, when no record is named.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _read(inp: FlowsheetReadInput, ctx: ToolContext) -> ToolResult:
    from .. import projects
    from ..engine import sff

    project = ctx.project or projects.current()
    if inp.record.strip():
        try:
            return record_result(sff.get(inp.record.strip(), project_id=project))
        except sff.FlowsheetNotFound as e:
            return ToolResult(error=f"flowsheet_read refused: {str(e).strip(chr(39))} (flowsheet_read with no record lists them)")
    words = [w for w in inp.words.lower().split() if w]
    rows = []
    for r in sff.listed(project_id=project):
        said = f"{r.id} {r.title} {r.origin} {r.libraryId or ''}".lower()
        if words and not all(w in said for w in words):
            continue
        rows.append({"recordId": r.id, "title": r.title, "origin": r.origin, "libraryId": r.libraryId,
                     "valid": r.validation.valid})
    return ToolResult(summary={"matched": len(rows), "records": rows[: inp.limit]})


LIBRARY_TOOL = register(Tool(
    name="flowsheet_library",
    description=(
        "List the SFF toolkit's reference flowsheet files at the pinned commit (their ids, titles, the schema version "
        "each declares, the simulator model each comes from) and which this machine holds. Narrow by words. Returns "
        "ids and words; flowsheet_import brings one into the project."
    ),
    input_model=FlowsheetLibraryInput, run=_library, strict=False,
))

IMPORT_TOOL = register(Tool(
    name="flowsheet_import",
    description=(
        "Import one of the toolkit's reference SFF files into the project by its id: fetched at the pinned commit, its "
        "hash checked, checked by the toolkit against the schema it ships, drawn, and kept as a record marked as yours. "
        "Returns the record's id, whether the file is valid and what the checks found, the unit types its graph holds, "
        "its feeds and its products by name, and what the graph counts as evidence ids to cite. A file already kept "
        "answers from its record."
    ),
    input_model=FlowsheetImportInput, run=_import, strict=False, writes=True,
))

READ_TOOL = register(Tool(
    name="flowsheet_read",
    description=(
        "Read an SFF flowsheet record the project holds by its id (an imported file, or the one an engine run writes): "
        "what the file is, whether it is valid, the unit types its graph holds, its feeds and its products, and what "
        "the graph counts as evidence ids to cite. With no id, list the project's records, narrowed by words."
    ),
    input_model=FlowsheetReadInput, run=_read, strict=False,
))
