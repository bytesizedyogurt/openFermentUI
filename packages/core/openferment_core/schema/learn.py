"""Learn modules, lessons, checkpoints — and the reader's own paper collections.

Ported from `src/data/types.ts`. The Learn surface is the one place where the
platform explains its own rules (provenance, units, the review queue) rather
than merely enforcing them, so a lesson block is either prose or a live embed of
the real component being described — never a screenshot of one. `EmbedKind`
enumerates the nine components a lesson is allowed to mount; its values are the
strings the TypeScript renderer switches on, so they are reproduced exactly.

`Collection` sits here because it is the reader-facing grouping of papers used
by Learn and by chat scoping, not a corpus-side concept.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ._base import OFModel

__all__ = [
    "CheckpointQuestion",
    "Collection",
    "EmbedBlock",
    "EmbedKind",
    "LearnModule",
    "Lesson",
    "LessonBlock",
    "NumericAnswer",
    "ProseBlock",
]


class EmbedKind(StrEnum):
    """Which live component a lesson block mounts.

    A closed set: a lesson embeds the real interface element it is teaching, so
    every member here corresponds to a component the Learn renderer knows how to
    mount. Adding a value without adding the component leaves a lesson with a
    hole in it.
    """

    CHIP_DEMO = "chip-demo"
    RECORD_CARD = "record-card"
    UNIT_PLAYGROUND = "unit-playground"
    MINI_QUEUE = "mini-queue"
    METRICS_TILES = "metrics-tiles"
    STRIP_PLOT = "strip-plot"
    PROTOCOL_CARD = "protocol-card"
    ASK_PROMPT = "ask-prompt"
    SCENARIO_WIDGET = "scenario-widget"


class ProseBlock(OFModel):
    """The prose arm of `LessonBlock`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["prose"]
    md: str


class EmbedBlock(OFModel):
    """The embed arm of `LessonBlock`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["embed"]
    embed: EmbedKind
    arg: str | None = Field(
        default=None,
        description=(
            "Component-specific argument, e.g. the record or protocol id the embed "
            "should show. Absent where the embed needs no target."
        ),
    )


LessonBlock = Annotated[ProseBlock | EmbedBlock, Field(discriminator="kind")]
"""One block of a lesson: either prose or a live embed, discriminated on `kind`."""


class NumericAnswer(OFModel):
    """The expected answer to a `kind: 'numeric'` checkpoint question.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. The tolerance is carried with the answer rather than applied globally
    because a unit-conversion question and an order-of-magnitude question are not
    marked to the same precision.
    """

    value: float
    unit: str
    tolerance_pct: float


class CheckpointQuestion(OFModel):
    """One end-of-lesson check.

    Multiple-choice questions carry `options` and `answerIndex`; numeric ones
    carry `answer`. Both shapes live in one interface in the TypeScript, so both
    sets of fields are optional here and the `kind` says which apply.
    """

    id: str
    prompt: str
    kind: Literal["mc", "numeric"]
    options: list[str] | None = Field(
        default=None, description="Multiple-choice options. Present when `kind` is 'mc'."
    )
    answer_index: int | None = Field(
        default=None,
        # An index into `options`, so int rather than float.
        description="Index of the correct entry in `options`. Present when `kind` is 'mc'.",
    )
    answer: NumericAnswer | None = Field(
        default=None,
        description="Expected value, unit and tolerance. Present when `kind` is 'numeric'.",
    )
    explanation: str
    evidence_chip: str | None = Field(
        default=None,
        description=(
            "Evidence chip backing the answer, e.g. 'ex-0112' or 'SP-004' — the lesson "
            "cites the corpus for its own claims on the same terms it asks the reader to."
        ),
    )


class Lesson(OFModel):
    id: str
    title: str
    minutes: int = Field(
        # A whole number of minutes, so int rather than float.
        description="Estimated reading time in whole minutes."
    )
    blocks: list[LessonBlock]
    checkpoint: list[CheckpointQuestion]


class LearnModule(OFModel):
    id: str
    index: int = Field(
        # An ordering index, so int rather than float.
        description="Ordering index of the module within the Learn track."
    )
    title: str
    blurb: str
    lessons: list[Lesson]
    outline: list[str] | None = Field(
        default=None,
        description=(
            "Planned lesson headings for a module whose lessons are not written yet. "
            "An empty `lessons` list with an outline is a stated gap, not a defect."
        ),
    )


class Collection(OFModel):
    """A reader-assembled set of corpus papers."""

    id: str
    name: str
    paper_ids: list[str]
