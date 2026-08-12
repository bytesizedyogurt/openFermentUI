"""Provenance, evidence class, and the corpus entries themselves.

Ported from `src/data/types.ts`. The two provenance axes are the load-bearing
idea in this package and their docstrings port with them verbatim.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from ._base import OFModel

__all__ = [
    "CorpusThread",
    "CoverageDispute",
    "EvidenceClass",
    "IngestStage",
    "IngestStatus",
    "Paper",
    "PaperSection",
    "Provenance",
    "SourceType",
    "TextSource",
]


class Provenance(StrEnum):
    """Provenance classes (OF-DES-001 §7.4, revised by OF-COR-001 §20).

    With a real corpus, 'demo' no longer means "this whole platform is fake" —
    it is reserved for the three surfaces that remain modeled rather than
    measured: simulation response grids, scripted agent answer text, and
    anything derived from them.

    'curated' is new and load-bearing. It marks a value transcribed from the
    curation document (OF-COR-001) rather than read off the source PDF. The
    claim is real and attributable, but it has not yet been checked against the
    paper itself, so it is weaker than 'verified' and must never silently pass
    as a source-span extraction.

    'industry-estimate' marks market and vendor figures (OF-COR-001 §16 O8).
    They are useful for framing and useless as evidence: excluded from the gold
    set and from aggregate statistics by default.

    'unsourced' is a defect class, not a value class. It marks a quantity that
    reached the interface with no provenance record behind it — the interface
    expression of Rule 1 of the agent contract, that no quantity may come from
    model weights. It is unreachable in the seeded build, `check:seed` enforces
    that no record carries it, and `Tick` shouts in the console when one renders.
    It is kept reachable on one Settings route so a reviewer can see what the
    system does when the rule is broken rather than be asked to believe it cannot
    be.
    """

    GOLD = "gold"
    VERIFIED = "verified"
    CURATED = "curated"
    UNVERIFIED = "unverified"
    USER = "user"
    INDUSTRY_ESTIMATE = "industry-estimate"
    DEMO = "demo"
    UNSOURCED = "unsourced"


class EvidenceClass(StrEnum):
    """Where a value came from, orthogonal to how far it has been verified.
    `Provenance` answers "how much has this been checked?";
    `EvidenceClass` answers "what kind of thing produced it?".

    Both are needed once the system holds predictions and bench results
    alongside literature: a `curated` prediction and a `curated` measurement
    are the same verification state and completely different claims.

    Encoded as tick *geometry*, never as a second hue — the ambient-texture
    property of the provenance palette depends on hue meaning one thing only.
    """

    LITERATURE = "literature"
    """a paper, thesis, report — today, every record"""
    PATENT = "patent"
    """Parchment"""
    COMPUTED = "computed"
    """geneOS / fermOS prediction"""
    EXPERIMENT = "experiment"
    """openLab deposit"""
    CORRECTION = "correction"
    """supersedes an earlier entry"""


class IngestStage(StrEnum):
    FETCH = "fetch"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    EXTRACT = "extract"


class IngestStatus(StrEnum):
    """Where a corpus entry is in the ingest pipeline.

    The TypeScript writes the five in-progress members as a template literal,
    `` `stage:${IngestStage}` ``, which is a genuinely nicer way to say it and a
    thing JSON Schema cannot express — a schema can enumerate strings but cannot
    describe a string built from another enum. They are therefore written out
    here. If `IngestStage` ever grows a member, this enum has to grow the
    matching `stage:` member by hand, and there is a test that fails if it does
    not.
    """

    COMPLETE = "complete"
    """Full text parsed into sections; spans anchor to the paper's own words."""
    CATALOGUED = "catalogued"
    """Bibliographically real, full text NOT yet ingested (OF-COR-001 §22.6).

    The reader shows the curation entry from OF-COR-001, clearly labelled as
    the curator's words rather than the paper's, with a DOI link out.
    """
    STAGE_FETCH = "stage:fetch"
    STAGE_PARSE = "stage:parse"
    STAGE_CHUNK = "stage:chunk"
    STAGE_EMBED = "stage:embed"
    STAGE_EXTRACT = "stage:extract"
    FAILED_FETCH = "failed:fetch"
    """The source document could not be retrieved at all."""
    FAILED_PARSE = "failed:parse"
    SHELF = "shelf"


class CorpusThread(StrEnum):
    """Which corpus thread an entry belongs to (OF-COR-001 §1)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"  # noqa: E741 — the thread is named I; renaming it would break every id.
    J = "J"
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    O = "O"  # noqa: E741 — likewise.


class SourceType(StrEnum):
    JOURNAL_ARTICLE = "journal-article"
    REVIEW = "review"
    THESIS = "thesis"
    PATENT = "patent"
    BOOK = "book"
    INDUSTRY_REPORT = "industry-report"
    PREPRINT = "preprint"


TextSource = Literal["full-text", "curation-note"]
"""Whether `Paper.sections` hold the paper's own text or the curator's notes."""


class PaperSection(OFModel):
    id: str
    heading: str
    text: str


class CoverageDispute(OFModel):
    """A reader filed "something's missing" against a source (OF-FE-003 §8.4).

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    note: str
    at: str


class Paper(OFModel):
    id: str = Field(
        description="Corpus entry id, e.g. 'H1' — thread letter plus index (OF-COR-001 §1)."
    )
    title: str
    authors: list[str]
    year: int = Field(
        description=(
            "0 where the year is genuinely unknown. A sentinel rather than a guess: "
            "see invariant 4 in CLAUDE.md."
        )
    )
    venue: str
    organisms: list[str]
    topics: list[str]
    abstract: str = Field(
        description=(
            "For 'catalogued' papers this is the curator's summary from OF-COR-001, "
            "NOT the publisher's abstract. `textSource` says which."
        )
    )
    sections: list[PaperSection]
    ingest: IngestStatus

    # ── real-corpus identity (OF-COR-001) ──────────────────────────────
    thread: CorpusThread
    source_type: SourceType
    doi: str | None = Field(
        default=None,
        description="The authoritative record key — never the author string (OF-COR-001 header).",
    )
    pmcid: str | None = None
    pmid: str | None = None
    text_source: TextSource = Field(
        description="Whether `sections` hold the paper's own text or the curator's notes."
    )
    open_access: bool = Field(
        description="Openly retrievable vs. needs institutional access (OF-COR-001 §19)."
    )
    tranche: Literal[1, 2, 3] = Field(
        description="Ingestion tranche: 1 = open-access core, 2 = remainder, 3 = v1.1."
    )
    verify_needed: bool | None = Field(
        default=None,
        description="Author string not fully resolved — must be checked at ingest ([verify]).",
    )
    corpus_role: str | None = Field(
        default=None, description="Why this entry earns its place, from the corpus document."
    )
    coverage_disputed: CoverageDispute | None = Field(
        default=None,
        description=(
            'A reader filed "something\'s missing" against this source (OF-FE-003 §8.4). '
            "Recall failure is the failure that hides: a wrong value gets clicked and "
            "corrected, a missed one is invisible forever. This flag is the only thing "
            "in the system that surfaces it, so it returns the source to the review "
            "queue rather than sitting as a passive annotation."
        ),
    )
