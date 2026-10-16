"""`search_records`: the records Postdoc may cite, found by words (OF-BLD-014 §3.4)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..evidence_pool import MAX_LIMIT
from ..models import ToolResult
from ..postdoc import _evidence_payload
from . import Tool, ToolContext, register


class SearchRecordsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="Words to search the records for: what was measured, the organism, the product, the feed.")
    field: str | None = Field(description="An ontology field id to keep only records of that field, or null for any field.")
    organism: str | None = Field(description="A strain id to keep only records on that strain, or null for any organism.")
    limit: int = Field(description=f"How many records to return, at most {MAX_LIMIT}.")

    @field_validator("field", "organism")
    @classmethod
    def _unused_is_null(cls, v: str | None) -> str | None:
        # Told to send an empty string, a model sent the two characters ""
        # and every such search came back empty (live test, 2026-10-16). An
        # empty value, or quotes around nothing, means unused, as null does.
        if v is None or v.strip() in ("", '""', "''"):
            return None
        return v


def _run(inp: SearchRecordsInput, ctx: ToolContext) -> ToolResult:
    pool = ctx.pool
    hits = pool.search(inp.query, field=inp.field or "", organism=inp.organism or "", limit=inp.limit)
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
            "ontology field id and by a strain id, or pass null for no filter. Returns none when nothing "
            "matches."
        ),
        input_model=SearchRecordsInput,
        run=_run,
    )
)
