"""`search_records`: the records Postdoc may cite, found by words (OF-BLD-014 §3.4)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..evidence_pool import MAX_LIMIT
from ..models import ToolResult
from ..postdoc import _evidence_payload
from . import Tool, ToolContext, register


class SearchRecordsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="Words to search the records for: what was measured, the organism, the product, the feed.")
    field: str = Field(description="An ontology field id to keep only records of that field, or an empty string for any field.")
    organism: str = Field(description="A strain id to keep only records on that strain, or an empty string for any organism.")
    limit: int = Field(description=f"How many records to return, at most {MAX_LIMIT}.")


def _run(inp: SearchRecordsInput, ctx: ToolContext) -> ToolResult:
    pool = ctx.pool
    hits = pool.search(inp.query, field=inp.field, organism=inp.organism, limit=inp.limit)
    payload = _evidence_payload(hits, pool)
    for item, hit in zip(payload, hits):
        item["carbonSource"] = hit.get("carbonSource")
    return ToolResult(
        summary={
            "query": inp.query,
            "field": inp.field or None,
            "organism": inp.organism or None,
            "count": len(payload),
            "records": payload,
        },
        recordIds=[h["id"] for h in hits],
    )


TOOL = register(
    Tool(
        name="search_records",
        description=(
            "Search the records Postdoc may cite: curated and verified records, and the extractor's anchored "
            "candidates nobody rejected, which are marked unverified. Returns at most ten, best match first, each "
            "with its record id, paper, what was measured, its value and unit as the paper wrote them, the quoted "
            "sentence, the strain, the carbon source when the paper states one, and its provenance. Filter by an "
            "ontology field id and by a strain id, or pass empty strings for no filter. Returns none when nothing "
            "matches."
        ),
        input_model=SearchRecordsInput,
        run=_run,
    )
)
