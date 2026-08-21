"""fermos_mcp — the fermOS process server, over MCP stdio.

This is the server-side half of the seam ``src/adapters/types.ts`` declares as
``ProcessAdapter`` (fermOS). Two tools answer from the real corpus; two are
declared stubs that refuse, matching the handle-based ``submitEvaluation`` /
``getEvaluation`` pair the adapter fixes in shape now so the expensive tiers
(COBRApy, BioSTEAM) can fill them in later without touching any caller.

Every successful response is the adapter envelope —
``{ data, serverVersion, corpusSnapshotId, notice? }`` — for the reason
``ResponseMeta``'s docstring gives: a response without versioning is a fact
with no way back to what produced it. ``modelVersion`` is deliberately ABSENT
from everything here, and that absence carries meaning: absent means NO MODEL
RAN. These are corpus reads. The first tool that computes something must stamp
what computed it.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

# OFModel is the wire convention (camelCase aliases, extra='forbid') every
# entity already follows; the input models below reuse it so the tool schemas
# match the TypeScript transport shapes byte for byte instead of approximating
# them. Imported, not copied — one definition.
from openferment_core.schema._base import OFModel

from fermos_mcp.corpus import CorpusView, load_corpus

SERVER_NAME = "fermos_mcp"

# The build id of whatever answered. A deployment substitutes a git describe or
# an image tag; the ``fermos-mcp/`` prefix is the load-bearing part, exactly as
# ``fixture-`` is for the in-browser backend — a trace must show at a glance
# WHICH backend answered it.
SERVER_VERSION = "fermos-mcp/0.1.0"

# Read once at import; the process serves one corpus snapshot for its lifetime,
# which is what makes its snapshot id meaningful. Failing to import on a bad
# corpus is intended — see load_corpus's docstring.
_CORPUS: CorpusView = load_corpus()

mcp = MCPServer(
    SERVER_NAME,
    version="0.1.0",
    instructions=(
        "fermOS process server. Scenarios come from data/corpus/scenarios.json, "
        "validated through the canonical openferment_core Scenario model. The "
        "evaluation pair is declared but refuses: no evaluator is wired up yet."
    ),
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _envelope(data: Any, notice: str | None = None) -> str:
    """The adapter response envelope, serialised.

    One helper so no tool can forget a field or invent a fourth — the same
    rule ``src/adapters/fixture/meta.ts`` enforces with ``respond()``.
    """
    body: dict[str, Any] = {
        "data": data,
        "serverVersion": SERVER_VERSION,
        "corpusSnapshotId": _CORPUS.snapshot_id,
    }
    if notice is not None:
        body["notice"] = notice
    return json.dumps(body, ensure_ascii=False, indent=2)


# ── Health ────────────────────────────────────────────────────────────────


@mcp.tool(name="health", title="Server health and corpus identity", annotations=_READ_ONLY)
def health() -> str:
    """Liveness plus identity: { ok, serverVersion, corpusSnapshotId }.

    corpusSnapshotId is a digest of the raw bytes of the data/corpus files
    this process actually read at startup — it changes when the corpus does,
    which is the one job a snapshot id has.
    """
    return json.dumps(
        {
            "ok": True,
            "serverVersion": SERVER_VERSION,
            "corpusSnapshotId": _CORPUS.snapshot_id,
            "corpusFiles": list(_CORPUS.files),
        },
        ensure_ascii=False,
        indent=2,
    )


# ── The real tools: scenarios ─────────────────────────────────────────────


@mcp.tool(name="list_scenarios", title="List cost scenarios", annotations=_READ_ONLY)
def list_scenarios() -> str:
    """All cost scenarios from data/corpus/scenarios.json.

    Each entry was validated through the canonical openferment_core Scenario
    model at startup and is serialised back through it here (by_alias, so the
    wire shape is the same camelCase the generated TypeScript types read).
    Mirrors ProcessAdapter.listScenarios.
    """
    return _envelope(
        [s.model_dump(by_alias=True, mode="json") for s in _CORPUS.scenarios],
    )


@mcp.tool(name="get_scenario", title="Get one scenario by id", annotations=_READ_ONLY)
def get_scenario(
    scenario_id: Annotated[str, Field(description="Scenario id, e.g. 'sc-s1'.")],
) -> str:
    """One scenario by id, or null with a notice naming the miss.

    Mirrors ProcessAdapter.getScenario: data is the scenario or null. Null
    carries a notice because an empty payload must say what it means — here,
    'no such id in this snapshot', never 'the corpus is empty'.
    """
    for s in _CORPUS.scenarios:
        if s.id == scenario_id:
            return _envelope(s.model_dump(by_alias=True, mode="json"))
    known = ", ".join(s.id for s in _CORPUS.scenarios)
    return _envelope(
        None,
        notice=(
            f"No scenario '{scenario_id}' in corpus snapshot {_CORPUS.snapshot_id}. "
            f"Ids present: {known}."
        ),
    )


# ── The declared stubs: the evaluation pair ───────────────────────────────
#
# The handle-based shape is fixed NOW, before there is an evaluator, for the
# reason ProcessAdapter.submitEvaluation gives: T2 (reactor model) and T3
# (Monte Carlo cash flow) will exceed any request/response timeout, so the
# result must be collected by handle — and that has to be true from the first
# call site, because retrofitting it means touching all of them.


class SubmitEvaluationInput(OFModel):
    """Wire twin of EvaluationRequest (src/adapters/types.ts).

    Inherits OFModel's config unchanged: camelCase aliases on the wire,
    unknown fields are an error.
    """

    scenario_id: str = Field(description="Scenario the configuration belongs to.")
    config: dict[str, float] = Field(
        description="Axis key to configured value, e.g. {'density': 2.0}."
    )
    label: str | None = Field(
        default=None, description="Display label for the resulting design."
    )


@mcp.tool(name="submit_evaluation", title="Submit a configuration for tier evaluation (STUB — refuses)", annotations=_READ_ONLY)
def submit_evaluation(params: SubmitEvaluationInput) -> str:
    """STUB. Validates the request shape, then refuses: no evaluator is wired up.

    When fermOS wraps BioSTEAM/COBRApy this returns a JobId handle inside the
    envelope; get_evaluation collects it. Until then refusing is the only
    honest answer — issuing a handle here would promise a result no code can
    produce, and fabricating a DesignRecord is forbidden outright.
    """
    raise NotImplementedError(
        "ProcessAdapter.submitEvaluation: no evaluator is wired up. "
        "This is where T2 (reactor model) and T3 (BioSTEAM cash flow) go; "
        f"the request for scenario '{params.scenario_id}' parsed cleanly and "
        "was discarded. No handle was issued."
    )


@mcp.tool(name="get_evaluation", title="Collect an evaluation by handle (STUB — refuses)", annotations=_READ_ONLY)
def get_evaluation(
    job_id: Annotated[str, Field(description="Handle returned by submit_evaluation.")],
) -> str:
    """STUB. Refuses: no evaluator is wired up.

    The contract says a backend rejects any handle it never issued. This
    backend has never issued one, so every job_id is such a handle. When the
    evaluator exists this returns EvaluationStatus — { jobId, status,
    position, stages, result?, failReason? } — with position REPORTED by the
    runner, never derived by the caller.
    """
    raise NotImplementedError(
        "ProcessAdapter.getEvaluation: no evaluator is wired up. This backend "
        f"has never issued a handle, so '{job_id}' cannot be one of its own. "
        "Submit via submit_evaluation once an evaluator exists."
    )


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
