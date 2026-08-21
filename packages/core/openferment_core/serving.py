"""The response envelope every openFerment server answers in.

``AdapterResponse<T>`` in ``src/adapters/types.ts`` is the contract:
``{ data, serverVersion, corpusSnapshotId, notice? }``. It is a WIRE SHAPE, not
an entity, which is why it lives beside the schema rather than in it — but it
is shared for the same reason the entities are. Four Python servers answering
in four slightly different envelopes is the same failure as four copies of a
model: the caller cannot write one reader.

THE FOURTH FIELD THAT IS USUALLY ABSENT. ``modelVersion`` is stamped only when
something COMPUTED the payload. Its absence is meaningful and is not "version
unknown" — it means no model ran, so a corpus read leaves it off and a flux
prediction or a plant solve must not. ``envelope()`` takes it as an explicit
argument so that omitting it is a decision at the call site rather than a
default nobody looked at.

WHY ONE HELPER. So no tool can forget a field or invent a fifth. Every tool in
every server returns ``envelope(...)`` and nothing hand-builds the dict.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["as_json", "envelope", "health_payload"]


def envelope(
    data: Any,
    *,
    server_version: str,
    corpus_snapshot_id: str,
    notice: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Build one ``AdapterResponse``.

    ``notice`` follows the rule ``AdapterResponse.notice`` sets: one sentence,
    written for a reader rather than a developer, present only when the payload
    alone would mislead. It is how an empty payload says whether it means
    "nothing matched" or "nothing computed this" — and a caller that renders a
    payload carrying one must render it.
    """
    body: dict[str, Any] = {
        "data": data,
        "serverVersion": server_version,
        "corpusSnapshotId": corpus_snapshot_id,
    }
    if model_version is not None:
        body["modelVersion"] = model_version
    if notice is not None:
        body["notice"] = notice
    return body


def health_payload(
    *,
    server_version: str,
    corpus_snapshot_id: str,
    corpus_files: tuple[str, ...],
) -> dict[str, Any]:
    """The health-check payload every server returns.

    ``{ ok, serverVersion, corpusSnapshotId }`` plus the files the snapshot id
    covers. ``corpusFiles`` is there so the id can be CHECKED rather than
    trusted: a reader holding the repo can recompute it from exactly these
    paths. ``ok`` is true because reaching this line means the corpus loaded —
    a server whose corpus failed to validate does not start, so there is no
    state in which this returns false and still answers.
    """
    return {
        "ok": True,
        "serverVersion": server_version,
        "corpusSnapshotId": corpus_snapshot_id,
        "corpusFiles": list(corpus_files),
    }


def as_json(payload: Any) -> str:
    """Serialise a tool result. One spelling, so transcripts are comparable."""
    return json.dumps(payload, ensure_ascii=False, indent=2)
