"""The organism a measurement was made in.

Ported from `src/data/types.ts`. A `Strain` is the host an `ExtractionRecord`
was measured in — the thing a titre or a PTM occupancy is only meaningful
relative to — and it is what geneOS reasons over when it compares hosts. It
carries no measured quantities of its own; those live on the records that point
at it.
"""

from __future__ import annotations

from typing import Literal

from ._base import OFModel
from .records import CuratorNote

__all__ = ["Strain"]


class Strain(OFModel):
    id: str
    binomial: str
    designation: str
    taxonomy: list[str]
    description: str
    badges: list[str]
    # Biosafety level is a two-valued classification here, not a measurement.
    bsl: Literal[1, 2]
    notes: list[CuratorNote]
