"""`yield_ceiling`: the most product a published reaction network can make
from a feed (OF-BLD-014 §6.3).

Ids and words in: a model on geneOS's shelf, the product (PHB from the
E. coli and C. necator models, ethanol from the two yeast models), the
sugar. One `Evidence` out, figure hint `ceiling`, whose basis names the model
file, the add-on route and the uptake convention; the model reads a short
description of the model beside it. A sugar the model cannot take up, or a
product it has no route to, is a finding, said in words, and carries no
number.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import geneos, geneos_models as shelf
from ..models import ToolResult
from ..workers import WorkerCrashed, WorkerError, WorkerTimeout
from . import Tool, ToolContext, register

NAME = "yield_ceiling"


class YieldCeilingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modelId: str = Field(description="A model on geneOS's shelf, with the products it names a route to: " + "; ".join(
        f"{m.id} ({', '.join(m.products)})" for m in shelf.SHELF.values()) + ".")
    product: str = Field(description=f"The product: {', '.join(shelf.PRODUCTS)}.")
    substrate: str = Field(description=f"The sugar fed: {', '.join(shelf.SUBSTRATES)}.")


def _run(inp: YieldCeilingInput, ctx: ToolContext) -> ToolResult:
    try:
        result = geneos.ceiling(inp.modelId, inp.product, inp.substrate)
    except geneos.GeneosUnavailable as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{NAME} could not compute it: {e}")
    entry = shelf.SHELF.get(inp.modelId)
    model = {"id": inp.modelId, "name": entry.name, "scope": entry.scope, "route": entry.route} if entry else {"id": inp.modelId}
    if result.finding:
        return ToolResult(summary={"model": model, "product": inp.product, "substrate": inp.substrate, "finding": result.finding})
    ev = result.evidence
    assert ev is not None
    return ToolResult(
        summary={
            "evidenceId": ev.id,
            "model": model,
            "what": ev.label,
            "gPerG": ev.value,
            "molPerMol": result.output.get("molPerMol"),
            "provenance": ev.provenance,
            "artifactId": result.artifactId,
            "meaning": "a ceiling from flux balance analysis: the most product this network can make from this feed; no time axis, no vessel",
        },
        evidence=[ev],
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "The most product a published reaction network can make from one sugar, by flux balance analysis, kept as "
            "a computed value with its basis. Returns one evidence id to cite, the value in g per g and mol per mol, "
            "and the model it came from; the core model gives the central-carbon ceiling, a genome-scale model the "
            "full network's. A sugar the model cannot take up, or a product it has no route to, comes back as a "
            "finding with no number."
        ),
        input_model=YieldCeilingInput,
        run=_run,
    )
)
