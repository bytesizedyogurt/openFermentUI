"""Reading `data/corpus/*.json` — which model parses which file, and what a
server may say about what it read.

Three things live here, each because more than one caller needs them to agree.

WHICH MODEL PARSES WHICH FILE (``COLLECTION_MODELS``). The exporter writes the
seven collections by validating each through a Pydantic model; every server
that reads one back must validate it through the SAME model. A second copy of
the map would be a second opinion about what ``strains.json`` is, so the
exporter imports this one rather than declaring its own, and ``load`` rejects a
call that names a model the exporter did not use — before opening the file, so
the error says "this server asked for the wrong model" rather than surfacing
later as a validation failure that reads like bad data.

WHAT A SERVER READ (``CorpusReader``). A server's answer is only as good as the
snapshot it was computed against, so the object that reads the files is the
object that mints the id: a reader cannot report an id for bytes it did not
open, and cannot open bytes without them entering the id. Keeping those two
apart is how a `corpusSnapshotId` drifts from the thing it names.

WHICH RECORDS BELONG TO A HOST (``records_attributed_to``). An attribution
decision about the corpus rather than a display choice — see its own docstring
for why it is Python and what holds its TypeScript copies to it.

VALIDATION HAPPENS ON READ, and that is the point. A corpus file the canonical
schema cannot parse is a bug in one of the two that must surface at startup,
not a shrug — and per the repo's rule, where a real corpus instance fails the
MODEL is wrong and the model gets fixed, never the data.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from openferment_core.schema import (
    ExtractionRecord,
    LearnModule,
    Paper,
    ParameterDef,
    Protocol,
    Scenario,
    Strain,
)
from openferment_core.schema._base import OFModel
from openferment_core.snapshot import corpus_snapshot_id

__all__ = [
    "COLLECTION_MODELS",
    "CorpusReader",
    "default_corpus_dir",
    "records_attributed_to",
]

M = TypeVar("M", bound=OFModel)

#: Collection key -> the canonical model for one of its entries.
#:
#: The key is the basename of the file the exporter writes
#: (``data/corpus/<key>.json``). Seven, matching the seven collections
#: `src/data/source.ts` serves; adding an eighth means the exporter and this
#: map change together, which is why they read the same one.
COLLECTION_MODELS: Mapping[str, type[OFModel]] = {
    "papers": Paper,
    "records": ExtractionRecord,
    "ontology": ParameterDef,
    "strains": Strain,
    "protocols": Protocol,
    "scenarios": Scenario,
    "learn": LearnModule,
}


def default_corpus_dir() -> Path:
    """Where the corpus lives, overridable by ``OF_CORPUS_DIR``.

    The environment variable exists for the container images: a Dockerfile
    copies the corpus to a path that is not three levels up from this file, and
    pointing the server at it must not require patching code.
    """
    override = os.environ.get("OF_CORPUS_DIR")
    if override:
        return Path(override)
    # openferment_core/corpus.py -> openferment_core -> core -> packages -> root
    return Path(__file__).resolve().parents[3] / "data" / "corpus"


class CorpusReader:
    """Reads corpus collections and reports the identity of what it read.

    Construct one per process and read everything the server serves through it,
    then hand ``snapshot_id`` to every response. Reading more files later moves
    the id, which is correct and is also why servers read what they need up
    front: an id that changes between two answers in the same session would
    make the two look like they came from different corpora.
    """

    def __init__(self, corpus_dir: Path | None = None) -> None:
        self.dir = corpus_dir if corpus_dir is not None else default_corpus_dir()
        self._bytes: dict[str, bytes] = {}

    def load(self, key: str, model: type[M]) -> tuple[M, ...]:
        """Read one collection, validated through ``model``.

        ``model`` is passed rather than looked up so the call site states, in
        the server's own source, what it believes it is reading — and so a type
        checker holds the server to it. It is checked against
        ``COLLECTION_MODELS`` regardless: agreeing with the exporter is not
        optional, and a mismatch here is a bug in the server, not a preference.

        Raises on a missing file, malformed JSON, a top-level shape that is not
        a list, or an entry the schema rejects. Failing to start is the correct
        behaviour for all four: a server that started anyway would be attesting
        to a corpus it does not hold.
        """
        expected = COLLECTION_MODELS.get(key)
        if expected is None:
            raise KeyError(
                f"'{key}' is not a corpus collection. Known: {', '.join(sorted(COLLECTION_MODELS))}."
            )
        if expected is not model:
            raise TypeError(
                f"collection '{key}' is written by the exporter as {expected.__name__}, "
                f"but this server asked to read it as {model.__name__}. The exporter's "
                f"map is canonical (openferment_core.corpus.COLLECTION_MODELS)."
            )

        path = self.dir / f"{key}.json"
        raw = path.read_bytes()
        entries: Any = json.loads(raw)
        if not isinstance(entries, list):
            raise TypeError(
                f"{path} holds {type(entries).__name__}, not a list. Every corpus "
                f"collection is a JSON array of entries."
            )
        parsed = tuple(model.model_validate(entry) for entry in entries)

        # Recorded only after every entry validated, so a reader never reports
        # a snapshot that includes a file it could not actually serve.
        self._bytes[f"data/corpus/{key}.json"] = raw
        return parsed

    @property
    def files(self) -> tuple[str, ...]:
        """Repo-relative paths the reader has read, sorted.

        Returned so a response can name them and a reader of a trace can
        recompute the id rather than take it on faith.
        """
        return tuple(sorted(self._bytes))

    @property
    def snapshot_id(self) -> str:
        """``sha256:<16 hex>`` over exactly the files in ``files``."""
        return corpus_snapshot_id(self._bytes)


def records_attributed_to(
    records: Iterable[Any],
    papers: Iterable[Any],
    strain_id: str,
) -> list[Any]:
    """Which extraction records count as evidence about one strain.

    A record counts when it is TAGGED with the strain, or — absent a tag — when
    its paper's organism list names it. An explicit tag for a different strain
    always wins, so a two-organism paper never double-counts a record that
    already knows which organism it belongs to.

    WHY THIS IS PYTHON. It is an attribution decision about the corpus, not a
    display choice: it decides what evidence exists for a host, which is the
    kind of statement the Ledger and any aggregate over a strain inherit. The
    TypeScript copy in ``src/adapters/fixture/cell.ts`` says so itself — "this
    is server-side work" — and names its own retirement. Until the fixture
    retires, ``scripts/check-servers.mjs`` replays every strain through both
    and fails if they disagree; that gate is what makes two copies tolerable
    rather than a slow divergence.

    Duck-typed on purpose (``organism``, ``paper_id``, ``id``, ``organisms``)
    so it works on the Pydantic models without this module importing them in a
    cycle. Order is preserved from ``records``, because a caller comparing two
    runs compares sequences.
    """
    organisms_by_paper = {p.id: set(p.organisms) for p in papers}
    out = []
    for record in records:
        tag = getattr(record, "organism", None)
        if tag:
            if tag == strain_id:
                out.append(record)
            continue
        if strain_id in organisms_by_paper.get(record.paper_id, ()):
            out.append(record)
    return out
