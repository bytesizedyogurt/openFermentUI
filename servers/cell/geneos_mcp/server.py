"""geneos_mcp — geneOS, over MCP stdio.

The server-side half of ``CellAdapter`` in ``src/adapters/types.ts``: hosts, and
what is known or predicted about them. Three tools answer from the real corpus;
one is declared and refuses.

── THE ONE THAT REFUSES ──────────────────────────────────────────────────────

``predict_flux`` refuses, permanently under this backend, and the refusal is
the same fact every design in this build reports as an absent T1: there is no
genome-scale metabolic model here. Flux balance is COBRApy's, in Python, and
CLAUDE.md names it among the libraries a second implementation would have to
agree with forever. A prediction is ABSENT rather than estimated. `null` alone
would read as "no answer for this strain" when the truth is "no model, for any
strain", so the refusal says which.

── WHERE THE ATTRIBUTION RULE LIVES ──────────────────────────────────────────

``get_strain_records`` does not implement "which records count for a strain".
That rule is ``openferment_core.corpus.records_attributed_to`` and this server
calls it, because it is an attribution decision about the corpus rather than a
display choice — the fixture that also implements it says so itself and names
its own retirement. ``scripts/check-cell-parity.mjs`` replays every strain
through both and fails if they disagree.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from openferment_core.corpus import CorpusReader, records_attributed_to
from openferment_core.schema import ExtractionRecord, Paper, Strain
from openferment_core.serving import as_json, envelope, health_payload

SERVER_NAME = "geneos_mcp"
SERVER_VERSION = "geneos-mcp/0.1.0"

_CORPUS = CorpusReader()
_STRAINS: tuple[Strain, ...] = _CORPUS.load("strains", Strain)
_PAPERS: tuple[Paper, ...] = _CORPUS.load("papers", Paper)
_RECORDS: tuple[ExtractionRecord, ...] = _CORPUS.load("records", ExtractionRecord)

#: Word for word the reason every design in this build carries an absent T1.
#: One string, so the server, the adapter and the design engine cannot come to
#: say different things about the same missing model.
NO_FLUX_MODEL = (
    "No genome-scale metabolic model in this build. Flux balance is COBRApy's, in Python, and "
    "server-side; a prediction is absent here rather than estimated, which is what T1 reports on "
    "every design for the same reason."
)

mcp = MCPServer(
    SERVER_NAME,
    version="0.1.0",
    instructions=(
        "geneOS host server. Strains and their attributed records come from "
        "data/corpus/, validated through the canonical openferment_core models. "
        "Flux prediction is declared and refuses: no genome-scale model is wired up."
    ),
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _envelope(data: object, notice: str | None = None) -> str:
    """This server's envelope. No modelVersion: nothing here computes."""
    return as_json(
        envelope(
            data,
            server_version=SERVER_VERSION,
            corpus_snapshot_id=_CORPUS.snapshot_id,
            notice=notice,
        )
    )


def _dump(entity: Strain | ExtractionRecord) -> dict:
    return entity.model_dump(by_alias=True, exclude_none=True, mode="json")


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


@mcp.tool(name="list_strains", title="List hosts", annotations=_READ_ONLY)
def list_strains() -> str:
    """Every host in the snapshot. Mirrors CellAdapter.listStrains.

    `bsl` comes back on each one and is a constraint rather than a label:
    Protocol.bsl bounds which protocols a host can be run under, and a consumer
    that drops it can pair the two with no basis for it.
    """
    return _envelope([_dump(s) for s in _STRAINS])


@mcp.tool(name="get_strain", title="Get one host by id", annotations=_READ_ONLY)
def get_strain(
    strain_id: Annotated[str, Field(description="Strain id, e.g. 'cw15'.")],
) -> str:
    """One host by id, or null with a notice naming the miss."""
    for strain in _STRAINS:
        if strain.id == strain_id:
            return _envelope(_dump(strain))
    known = ", ".join(s.id for s in _STRAINS)
    return _envelope(
        None,
        notice=(
            f"No strain '{strain_id}' in corpus snapshot {_CORPUS.snapshot_id}. "
            f"Ids present: {known}."
        ),
    )


@mcp.tool(
    name="get_strain_records",
    title="Records attributable to a host",
    annotations=_READ_ONLY,
)
def get_strain_records(
    strain_id: Annotated[str, Field(description="Strain id, e.g. 'cw15'.")],
) -> str:
    """Every record attributable to a host. Mirrors CellAdapter.getStrainRecords.

    A record counts when it is tagged with the strain, or — absent a tag —
    when its paper's organism list names it; an explicit tag for a different
    strain always wins. The rule is openferment_core's, not this server's.

    An unknown strain id gets an empty list WITH a notice, because empty here
    is otherwise indistinguishable from a host nobody has published on.
    """
    hits = records_attributed_to(_RECORDS, _PAPERS, strain_id)
    notice = None
    if not any(s.id == strain_id for s in _STRAINS):
        notice = (
            f"'{strain_id}' is not a strain in corpus snapshot {_CORPUS.snapshot_id}, "
            "so this empty list means the host is unknown, not that no evidence exists."
        )
    elif not hits:
        notice = (
            f"No record in this snapshot is attributable to '{strain_id}' — neither "
            "tagged with it nor belonging to a paper whose organism list names it."
        )
    return _envelope([_dump(r) for r in hits], notice)


@mcp.tool(
    name="predict_flux",
    title="Flux balance analysis (DECLARED — refuses, see description)",
    annotations=_READ_ONLY,
)
def predict_flux(
    strain_id: Annotated[str, Field(description="Host to solve for.")],
    objective: Annotated[
        str, Field(description="Reaction or objective to maximise, in the model's own ids.")
    ],
) -> str:
    """DECLARED, REFUSES. There is no genome-scale metabolic model in this build.

    When COBRApy is wired up this returns a FluxPrediction whose `modelId`
    names the SBML that was solved — not optional, because a flux without the
    model that produced it is a number with no way to check it — and the
    envelope carries a modelVersion, because something will have computed it.
    """
    raise NotImplementedError(
        f"CellAdapter.predictFlux: {NO_FLUX_MODEL} The request "
        f"(strain '{strain_id}', objective '{objective}') parsed cleanly and was discarded."
    )


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
