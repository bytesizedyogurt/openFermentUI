"""`draft_runbook`: Postdoc drafts a runbook, and the service writes every
number (OF-BLD-014 §9.2).

Ids and words in: a title, a product id, a strain id, items that each point
at one computed evidence item or at records of one field, and measures that
each name the item they test at one of four timepoints. `runbook_draft.build`
writes the predictions' values and intervals from the artifacts and records,
and the draft comes back on `ToolResult.draft` for the plan to carry. A person
adopts it and locks it.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from .. import runbook_draft
from ..models import DraftItem, DraftMeasure, ToolResult
from . import Tool, ToolContext, register

NAME = "draft_runbook"


class DraftRunbookInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="What the runbook tests, in words with no number.")
    productId: str = Field(description="A product id.")
    strainId: str = Field(description="A strain id.")
    items: list[DraftItem] = Field(description="Each prediction: one evidence id, or a field with record ids this run returned.")
    measures: list[DraftMeasure] = Field(description="What the bench records, each naming the item label it tests.")


@lru_cache(maxsize=1)
def _ids() -> tuple[frozenset[str], frozenset[str]]:
    """The product and strain ids a draft may name: those the corpus holds
    (none until a project's records carry them, alpha 2.0 stage 2)."""
    from ..corpus import load_corpus

    c = load_corpus()
    return frozenset(p["id"] for p in c.products), frozenset(s["id"] for s in c.strains)


def _run(inp: DraftRunbookInput, ctx: ToolContext) -> ToolResult:
    try:
        products, strains = _ids()
        draft, left_out = runbook_draft.build(inp.title, inp.productId, inp.strainId, inp.items, inp.measures,
                                              ctx.seen, ctx.pool, set(products), set(strains))
    except (runbook_draft.DraftRefused, FileNotFoundError) as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    return ToolResult(
        summary={
            "title": draft.title,
            "predictions": [{"label": p.label, "kind": p.kind, "basis": p.basis} for p in draft.predictions],
            "measures": [m.label for m in draft.measures],
            "leftOut": left_out,
            "meaning": "a draft a person reads, adopts and locks; its numbers were written by the service",
        },
        draft=draft,
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "Draft a runbook from what this run found: a title, a product id and a strain id, items that each name one "
            "evidence id or a field with record ids returned earlier in this run, and measures (label, unit, one of "
            "start, mid-run, harvest, after recovery, and the item label they test). Send no numbers: the service writes "
            "each prediction's value and interval from the evidence and the records. A person adopts and locks it."
        ),
        input_model=DraftRunbookInput,
        run=_run,
    )
)
