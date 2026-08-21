"""proforma_mcp — Proforma, over MCP stdio.

The server-side half of ``EconomicsAdapter`` in ``src/adapters/types.ts``: the
cost model, and the plant behind the price. Two tools answer for real; three
are declared and refuse, and here the refusals are most of the surface — which
is the honest state of this subsystem rather than an oversight.

── WHAT IS REAL, AND WHERE IT COMES FROM ─────────────────────────────────────

``CostModelSummary`` is ``CostModel`` minus its ``evaluate``: ``{ modelId,
dims, referencePoint }``. Every one of those three is already in
``data/corpus/scenarios.json`` — ``modelId`` verbatim, ``dims`` as the sweep
axes, and ``referencePoint`` as the scenario's ``point`` — so this server
DERIVES the summaries from the corpus rather than carrying a copy of them.
``scripts/check-servers.mjs`` replays that derivation against the TypeScript
``COST_MODELS`` and fails if the two ever stop agreeing; without that gate this
would be a hand-maintained twin, which is the failure the repo rails name.

``ScenarioDim`` carries two fields a ``CostModel`` dim does not — ``paperId``
and ``sourceRecordId`` — and they are dropped here rather than passed along.
They are the provenance of the AXIS (which paper the range came from), which
belongs to the scenario a reader is looking at, not to the cost model a solver
is stepping through.

── WHAT REFUSES, AND WHY ALL THREE ───────────────────────────────────────────

``solve_plant`` refuses and names BioSTEAM. CLAUDE.md routes cost-model
authoring to BioSTEAM in Python; this repository has a TypeScript port of the
bioSTEAM costing primitives and the TEA, and that port is exactly the second
implementation the migration exists to retire. Answering here from a Python
reimplementation would make three.

``evaluate_point`` refuses because the interpolation it would do is over a grid
built by SOLVING the plant at every node — the interpolation is the cheap half
and the solve is the half that does not exist here. CLAUDE.md keeps grid
interpolation in TypeScript deliberately: it is a UI convenience over a grid
the client already holds, and moving it server-side without the solve would
move the convenience and leave the substance behind.

``get_sensitivity`` refuses because it is two plant solves per parameter.

── DELIBERATE ABSENCE ────────────────────────────────────────────────────────

No tool authors, edits or adds a cost model. A cost model's dims and reference
point are the frame every MSP in the system is quoted in; an agent that could
widen an axis could move a headline number without touching a single datum,
and the change would look like arithmetic rather than like an edit. Cost model
authoring is BioSTEAM's and it is a human's commit.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from openferment_core.corpus import CorpusReader
from openferment_core.schema import Scenario
from openferment_core.serving import as_json, envelope, health_payload

SERVER_NAME = "proforma_mcp"
SERVER_VERSION = "proforma-mcp/0.1.0"

_CORPUS = CorpusReader()
_SCENARIOS: tuple[Scenario, ...] = _CORPUS.load("scenarios", Scenario)

mcp = MCPServer(
    SERVER_NAME,
    version="0.1.0",
    instructions=(
        "Proforma cost-model server. Cost model summaries are derived from "
        "data/corpus/scenarios.json, validated through the canonical "
        "openferment_core Scenario model. Every solve — point evaluation, plant, "
        "sensitivity — is declared and refuses: BioSTEAM is not wired up."
    ),
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _envelope(data: object, notice: str | None = None) -> str:
    """This server's envelope.

    No modelVersion on anything here, and that absence is load-bearing: it
    means NO MODEL RAN. Every tool below is a corpus read or a refusal. The
    first tool that actually solves a plant must stamp what solved it.
    """
    return as_json(
        envelope(
            data,
            server_version=SERVER_VERSION,
            corpus_snapshot_id=_CORPUS.snapshot_id,
            notice=notice,
        )
    )


def _summarise(scenario: Scenario) -> dict:
    """Derive one CostModelSummary from the scenario that states its axes.

    `field` is kept — it is what binds an axis to an ontology parameter, and a
    solver that has it can find the records behind the range. `paperId` and
    `sourceRecordId` are dropped: they are provenance of the axis, which is the
    scenario's business and not the cost model's.
    """
    return {
        "modelId": scenario.model_id,
        "dims": [
            {
                "key": dim.key,
                "label": dim.label,
                "unit": dim.unit,
                "values": list(dim.values),
                **({"field": dim.field} if dim.field is not None else {}),
            }
            for dim in scenario.dims
        ],
        "referencePoint": dict(scenario.point),
    }


#: Stated on every summary response. The numbers are real corpus values; what
#: is absent is anything that turns them into a price.
DERIVED_FROM_SCENARIOS = (
    "Cost model summaries are derived from the scenario definitions in the corpus — the axes and "
    "the reference point, nothing that evaluates them. No minimum selling price is available from "
    "this server: solving the plant is BioSTEAM's work and it is not wired up."
)


@mcp.tool(name="health", title="Server health and corpus identity", annotations=_READ_ONLY)
def health() -> str:
    """Liveness plus identity: { ok, serverVersion, corpusSnapshotId, corpusFiles }."""
    return as_json(
        health_payload(
            server_version=SERVER_VERSION,
            corpus_snapshot_id=_CORPUS.snapshot_id,
            corpus_files=_CORPUS.files,
        )
    )


@mcp.tool(name="list_cost_models", title="List cost model summaries", annotations=_READ_ONLY)
def list_cost_models() -> str:
    """Every cost model, as { modelId, dims, referencePoint }.

    Mirrors EconomicsAdapter.listCostModels. The `evaluate` member and the
    ResultGrid never appear and never can: one is a function and the other
    holds Float64Arrays, and src/data/types.ts records both as unable to
    round-trip through JSON Schema — which makes them exactly the two things
    that must not cross a wire.
    """
    return _envelope([_summarise(s) for s in _SCENARIOS], DERIVED_FROM_SCENARIOS)


@mcp.tool(name="get_cost_model", title="Get one cost model summary", annotations=_READ_ONLY)
def get_cost_model(
    model_id: Annotated[str, Field(description="Cost model id, e.g. 'S1'.")],
) -> str:
    """One cost model summary by id, or null with a notice naming the miss."""
    for scenario in _SCENARIOS:
        if scenario.model_id == model_id:
            return _envelope(_summarise(scenario), DERIVED_FROM_SCENARIOS)
    known = ", ".join(s.model_id for s in _SCENARIOS)
    return _envelope(
        None,
        notice=(
            f"No cost model '{model_id}' in corpus snapshot {_CORPUS.snapshot_id}. "
            f"Ids present: {known}."
        ),
    )


@mcp.tool(
    name="evaluate_point",
    title="Interpolate one point off the sweep (DECLARED — refuses)",
    annotations=_READ_ONLY,
)
def evaluate_point(
    model_id: Annotated[str, Field(description="Cost model id, e.g. 'S1'.")],
    point: Annotated[dict[str, float], Field(description="Axis key to value.")],
) -> str:
    """DECLARED, REFUSES. The grid it would read off does not exist here.

    Interpolation is the cheap half; the grid is built by solving the plant at
    every node, and that solve is BioSTEAM's. When it exists, this returns an
    EvaluatedPoint whose `clamped` flag says the request fell outside the
    modelled envelope and was pulled to its edge — a fact about the answer that
    a caller must be able to see rather than infer.
    """
    raise NotImplementedError(
        "EconomicsAdapter.evaluatePoint: no cost grid exists on this server. "
        f"The request (model '{model_id}', {len(point)} axis/axes) parsed cleanly "
        "and was discarded. A grid is built by solving the plant at every node; "
        "the solve is BioSTEAM's and is not wired up."
    )


@mcp.tool(
    name="solve_plant",
    title="Size, cost and price the flowsheet (DECLARED — refuses)",
    annotations=_READ_ONLY,
)
def solve_plant(
    model_id: Annotated[str, Field(description="Cost model id, e.g. 'S1'.")],
    point: Annotated[dict[str, float], Field(description="Axis key to value.")],
) -> str:
    """DECLARED, REFUSES. BioSTEAM is not wired up.

    This is the tool the whole subsystem is for: equipment sized, costed
    against published correlations, and priced by a discounted cash flow solved
    at NPV = 0. Producing a minimum selling price here from anything less would
    put a number with a currency sign on it into a trace, which is the single
    most quotable thing this system emits.
    """
    raise NotImplementedError(
        "EconomicsAdapter.solvePlant: BioSTEAM is not wired up. The request "
        f"(model '{model_id}', {len(point)} axis/axes) parsed cleanly and was "
        "discarded. No minimum selling price is available from this server."
    )


@mcp.tool(
    name="get_sensitivity",
    title="Local sensitivity bars (DECLARED — refuses)",
    annotations=_READ_ONLY,
)
def get_sensitivity(
    model_id: Annotated[str, Field(description="Cost model id, e.g. 'S1'.")],
    point: Annotated[dict[str, float], Field(description="Axis key to value.")],
) -> str:
    """DECLARED, REFUSES. Two plant solves per parameter, and there are no solves.

    Local when it exists, and the word is not decoration: it takes one
    parameter to each bound with everything else held fixed, so it cannot see
    interactions between them.
    """
    raise NotImplementedError(
        "EconomicsAdapter.getSensitivity: a sensitivity bar is two plant solves "
        f"per parameter, and solve_plant refuses. The request (model '{model_id}', "
        f"{len(point)} axis/axes) parsed cleanly and was discarded."
    )


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
