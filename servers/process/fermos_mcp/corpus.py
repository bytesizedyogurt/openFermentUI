"""What this server serves, and how a response names it.

One collection: ``data/corpus/scenarios.json``, read and validated through
``openferment_core.corpus.CorpusReader`` — which is where the reading, the
model map and the snapshot id all live, shared with every other Python server
here. This module holds only what is specific to fermOS: which collection, and
the fact that a failure to load is a failure to start.

An earlier version of this file grew its own digest and its own framing, and
disagreed with the Guild server's. See ``openferment_core/snapshot.py`` for
what that cost and why the framing is now in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from openferment_core.corpus import CorpusReader
from openferment_core.schema import Scenario

__all__ = ["CorpusView", "load_corpus"]


@dataclass(frozen=True)
class CorpusView:
    """The slice of the corpus this server has read, plus its identity."""

    scenarios: tuple[Scenario, ...]
    #: ``sha256:<16 hex>`` over the raw bytes of every corpus file this process
    #: read. Derived, never constant — see openferment_core/snapshot.py.
    snapshot_id: str
    #: The files the digest covers, relative to the repo root, so a reader of a
    #: trace can recompute the id and check it.
    files: tuple[str, ...]


def load_corpus() -> CorpusView:
    """Read and validate the corpus this server answers from.

    Raises on a missing file or a scenario the canonical schema rejects.
    Failing to start is correct in both cases: a server that started anyway
    would be attesting to a corpus it does not hold.
    """
    reader = CorpusReader()
    scenarios = reader.load("scenarios", Scenario)
    return CorpusView(
        scenarios=scenarios,
        snapshot_id=reader.snapshot_id,
        files=reader.files,
    )
