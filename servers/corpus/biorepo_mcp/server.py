"""biorepo_mcp — BioRepo, over MCP stdio.

The server-side half of ``CorpusAdapter`` in ``src/adapters/types.ts``: papers,
extraction records, patent scope, and the gold-set plan. Two collections are
served for real; the rest of the declared surface refuses, each for a stated
reason, because a corpus server is the one place in this system where a
plausible answer is more dangerous than no answer.

── WHAT REFUSES, AND WHY IT IS NOT LAZINESS ──────────────────────────────────

``search_papers`` refuses and names PaperQA2. It would be four lines to write a
substring filter here, and those four lines would be the exact failure this
repository's one rule exists to prevent: the UI ALREADY has a substring filter
(``BUNDLED_SEARCH_METHOD`` in ``src/data/source.ts``), it already says on the
face of the trace that it is not a retrieval system, and a second one on the
server would be a second implementation that has to agree with the first
forever, wearing a server's authority while doing a browser's work. CLAUDE.md
routes corpus retrieval to PaperQA2 and says do not reimplement. So this tool
holds the shape and declines to fill it.

``get_scope`` and ``get_whitespace`` refuse because the claims they would read
are not machine-readable yet: every ``Patent`` in the corpus carries
``parseUncertain: true`` and ``bounds: []``. A scope answer computed from empty
bounds would come back "no claim covers this configuration", which reads as
"unencumbered" and is a sentence nobody here is entitled to say.

── DELIBERATE ABSENCE — read before adding a tool ────────────────────────────

There is NO ``write_record`` tool, and there must not be one. ``CorpusAdapter``
declares ``writeRecord`` and the browser fixture implements it, because there a
human is looking at the screen that submitted it. An MCP tool is called by an
agent, unattended, and what it would write is a claim about a REAL PUBLICATION
into the store that the Ledger, the gold set and every aggregate read from.
CLAUDE.md's second invariant — no fabricated data — is not a coding standard
here, it is the one unrecoverable error in the project, and the way to keep an
agent from committing it is to not hand it the pen. The same reasoning kept a
publishing tool off the Guild server.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from openferment_core.corpus import CorpusReader
from openferment_core.schema import ExtractionRecord, Paper
from openferment_core.serving import as_json, envelope, health_payload

SERVER_NAME = "biorepo_mcp"

# The ``biorepo-mcp/`` prefix is the load-bearing part, exactly as ``fixture-``
# is for the in-browser backend: a trace must show at a glance WHICH backend
# answered it. A deployment substitutes a git describe or an image tag.
SERVER_VERSION = "biorepo-mcp/0.1.0"

# Read once at import. The process serves one corpus snapshot for its lifetime,
# which is what makes its snapshot id meaningful; failing to import on a corpus
# the schema rejects is intended.
_CORPUS = CorpusReader()
_PAPERS: tuple[Paper, ...] = _CORPUS.load("papers", Paper)
_RECORDS: tuple[ExtractionRecord, ...] = _CORPUS.load("records", ExtractionRecord)

mcp = MCPServer(
    SERVER_NAME,
    version="0.1.0",
    instructions=(
        "BioRepo corpus server. Papers and extraction records come from "
        "data/corpus/, validated through the canonical openferment_core models. "
        "Retrieval, patent scope and whitespace are declared and refuse — see "
        "each tool's description. There is deliberately no tool that writes a "
        "record."
    ),
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _envelope(data: object, notice: str | None = None) -> str:
    """This server's envelope. No modelVersion anywhere: nothing here computes."""
    return as_json(
        envelope(
            data,
            server_version=SERVER_VERSION,
            corpus_snapshot_id=_CORPUS.snapshot_id,
            notice=notice,
        )
    )


def _dump(entity: Paper | ExtractionRecord) -> dict:
    """Wire form: camelCase aliases, so it matches the generated TypeScript."""
    return entity.model_dump(by_alias=True, exclude_none=True, mode="json")


# ── Health ────────────────────────────────────────────────────────────────


@mcp.tool(name="health", title="Server health and corpus identity", annotations=_READ_ONLY)
def health() -> str:
    """Liveness plus identity: { ok, serverVersion, corpusSnapshotId, corpusFiles }.

    corpusSnapshotId is a digest of the raw bytes of the corpus files this
    process read at startup, so it moves when the corpus does. corpusFiles
    names them, so a reader holding the repo can recompute the id instead of
    trusting it.
    """
    return as_json(
        health_payload(
            server_version=SERVER_VERSION,
            corpus_snapshot_id=_CORPUS.snapshot_id,
            corpus_files=_CORPUS.files,
        )
    )


# ── The real tools: corpus reads ──────────────────────────────────────────


@mcp.tool(name="get_paper", title="Get one paper by id", annotations=_READ_ONLY)
def get_paper(
    paper_id: Annotated[str, Field(description="Corpus paper id, e.g. 'M5' or 'H4'.")],
) -> str:
    """One paper by id, or null with a notice naming the miss.

    Mirrors CorpusAdapter.getPaper. Null carries a notice because an empty
    payload must say what it means — here 'no such id in this snapshot', never
    'the corpus is empty'.

    Papers come back whole, sentinels included: `year: 0` where the year is
    unknown and the VENUE_UNSTATED constant where the venue is. Those are
    first-class values in this schema and a consumer that treats them as
    missing data will be wrong about which papers are actually dated.
    """
    for paper in _PAPERS:
        if paper.id == paper_id:
            return _envelope(_dump(paper))
    return _envelope(
        None,
        notice=(
            f"No paper '{paper_id}' in corpus snapshot {_CORPUS.snapshot_id}. "
            f"The snapshot holds {len(_PAPERS)} papers."
        ),
    )


@mcp.tool(name="list_papers", title="List paper ids and titles", annotations=_READ_ONLY)
def list_papers() -> str:
    """Every paper in the snapshot, as { id, title, year, venue }.

    A deliberately thin projection: the full corpus is large, and the caller
    that wants a whole paper asks for one by id. This is the index, not the
    library.
    """
    return _envelope(
        [
            {"id": p.id, "title": p.title, "year": p.year, "venue": p.venue}
            for p in _PAPERS
        ]
    )


@mcp.tool(name="list_records", title="Extraction records, filtered", annotations=_READ_ONLY)
def list_records(
    paper_id: Annotated[
        str | None, Field(default=None, description="Restrict to one paper's records.")
    ] = None,
    field: Annotated[
        str | None,
        Field(default=None, description="Ontology field id, e.g. 'final_biomass_density'."),
    ] = None,
    organism: Annotated[
        str | None,
        Field(default=None, description="Strain id, matched against ExtractionRecord.organism."),
    ] = None,
    ids: Annotated[
        list[str] | None,
        Field(default=None, description="Fetch these record ids directly."),
    ] = None,
) -> str:
    """Records, filtered. No filter returns the whole set.

    Mirrors CorpusAdapter.getRecords and its RecordQuery: every filter is
    optional and absent means 'any'. Filtering is exact equality on each field,
    which is a lookup and not an algorithm — the distinction that lets this
    tool be real while search_papers refuses.

    Records come back with their `provenance` and `evidenceClass` intact and
    UNFILTERED. Deciding what may enter an aggregate is isAggregatable()'s job
    and it is the single gate; a server that pre-filtered here would be a
    second, invisible gate disagreeing with it.
    """
    wanted = set(ids) if ids else None
    hits = [
        r
        for r in _RECORDS
        if (paper_id is None or r.paper_id == paper_id)
        and (field is None or r.field == field)
        and (organism is None or r.organism == organism)
        and (wanted is None or r.id in wanted)
    ]

    notice = None
    if wanted is not None:
        missing = sorted(wanted - {r.id for r in hits})
        if missing:
            notice = (
                f"{len(missing)} requested id(s) are not in corpus snapshot "
                f"{_CORPUS.snapshot_id}: {', '.join(missing)}."
            )
    elif not hits:
        notice = (
            "No record matches those filters in this snapshot. That is an empty "
            "result, not an empty corpus — the snapshot holds "
            f"{len(_RECORDS)} records."
        )
    return _envelope([_dump(r) for r in hits], notice)


# ── The declared refusals ─────────────────────────────────────────────────


@mcp.tool(
    name="search_papers",
    title="Retrieval over the corpus (DECLARED — refuses, see description)",
    annotations=_READ_ONLY,
)
def search_papers(
    query: Annotated[str, Field(description="Natural-language question.")],
    k: Annotated[int, Field(default=5, description="Passages to return.")] = 5,
) -> str:
    """DECLARED, REFUSES. Retrieval is PaperQA2's and is not implemented here.

    Not a gap to fill in with a substring filter. The browser already has one
    and says so in every trace it produces; a second one here would have to
    agree with it forever while carrying a server's authority. When PaperQA2 is
    wired up, this tool returns CorpusSearchResult whole — hits plus the
    `method` sentence stating what actually ran — and no caller changes.
    """
    raise NotImplementedError(
        "CorpusAdapter.searchPapers: retrieval is not implemented by this server. "
        f"The query ({len(query)} chars, k={k}) parsed cleanly and was discarded. "
        "Corpus retrieval belongs to PaperQA2 and is deliberately not "
        "reimplemented; use list_papers and get_paper for id-addressed reads."
    )


@mcp.tool(
    name="get_scope",
    title="Which patent claims cover a configuration (DECLARED — refuses)",
    annotations=_READ_ONLY,
)
def get_scope(
    config: Annotated[
        dict[str, float | str],
        Field(description="The configuration to test, keyed by ontology field."),
    ],
) -> str:
    """DECLARED, REFUSES. The claims are not machine-readable yet.

    Every Patent in this corpus carries parseUncertain: true and bounds: [], so
    the only answer available would be an empty hit list — which reads as
    'unencumbered'. DesignRecord.scope makes the same point about the word
    'clear'. Refusing is the difference between 'no claim was checked' and 'no
    claim applies', and only one of those is true.
    """
    raise NotImplementedError(
        "CorpusAdapter.getScope: patent claim bounds are unparsed "
        "(every Patent carries parseUncertain: true, bounds: []). A scope test "
        f"over {len(config)} axis/axes would return an empty hit list that reads "
        "as 'unencumbered', which this server is not entitled to say."
    )


@mcp.tool(
    name="get_whitespace",
    title="Unclaimed regions of the parameter space (DECLARED — refuses)",
    annotations=_READ_ONLY,
)
def get_whitespace() -> str:
    """DECLARED, REFUSES. Whitespace is the complement of parsed claims.

    With no parsed claims the complement is the whole space, and returning that
    would be advice, not data.
    """
    raise NotImplementedError(
        "CorpusAdapter.getWhitespace: whitespace is the complement of parsed "
        "claim bounds, and no claim in this corpus is parsed. The complement of "
        "nothing is everything, which is not a finding."
    )


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
