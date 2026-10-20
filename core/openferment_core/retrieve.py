"""Searching the papers' own words, five ways (OF-BLD-014 §4.2).

| lane            | what it adds                                        | needs            |
| bm25            | keyword match over passages                         | the index        |
| bm25+expand     | up to three other phrasings, every ranking fused    | the key          |
| hybrid          | a meaning match on vectors, fused with keywords     | the vectors      |
| bm25+rerank     | a reader grades the top thirty and copies a sentence| the key          |
| hybrid+rerank   | both                                                | key and vectors  |

FUSION is reciprocal rank fusion: a passage's score is the sum over the
rankings it appears in of `1 / (60 + rank)`, rank 1 first.

`search(question, k=8, lane=None)` uses the lane `core/data/index/config.json`
names when none is given, and `bm25` when that file is absent. A lane that
cannot run here raises `LaneUnavailable` with the reason in words.

THE PROGRAM SWITCH (OF-BLD-016 §2.3, E.2′). A passage of a paper in an
archived program is left out of every ranking before fusion, and so before a
reader grades anything, unless the caller passes `include_archived=True`.
Off is the default. Each ranking is then read past `DEPTH` until it holds
`DEPTH` passages that show.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from . import llm, passages, programs
from .models import PassageHit, RagLane, Usage

LANES = ("bm25", "bm25+expand", "hybrid", "bm25+rerank", "hybrid+rerank")
PAID = frozenset({"bm25+expand", "bm25+rerank", "hybrid+rerank"})
# The constant in reciprocal rank fusion, and how deep each ranking is read
# before fusing. Conventions (E.1).
RRF_K = 60
DEPTH = 50


class LaneUnavailable(RuntimeError):
    pass


def rrf(rankings: dict[str, list[str]], k0: int = RRF_K) -> list[tuple[str, float, dict[str, int]]]:
    """Fuse named rankings: (id, score, {ranking name: rank}) best first; a
    tie keeps the order the ids first appeared in."""
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    first_seen: dict[str, int] = {}
    for name, ids in rankings.items():
        for r, pid in enumerate(ids, start=1):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k0 + r)
            ranks.setdefault(pid, {})[name] = r
            first_seen.setdefault(pid, len(first_seen))
    order = sorted(scores, key=lambda p: (-scores[p], first_seen[p]))
    return [(p, round(scores[p], 8), ranks[p]) for p in order]


# ── availability ───────────────────────────────────────────────────────


def _have_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def why_unavailable(lane: str, *, embedder=None) -> str | None:
    if lane not in LANES:
        return f"there is no lane {lane!r}; the lanes are {', '.join(LANES)}"
    index = passages.bm25_index()
    if not index.cuts:
        return "no index yet: run pnpm index:build"
    if lane in PAID and not _have_key():
        return "needs the key in core/.env for its helper model calls"
    if lane.startswith("hybrid"):
        dense, why = _dense(index)
        if dense is None:
            return why
        if embedder is None:
            try:
                _query_embedder(dense.model)
            except Exception as e:
                return str(e)
    return None


def lanes(*, embedder=None) -> list[RagLane]:
    out = []
    for lane in LANES:
        why = why_unavailable(lane, embedder=embedder)
        out.append(RagLane(name=lane, available=why is None, why=why))
    return out


# ── the lanes ──────────────────────────────────────────────────────────

_EMBEDDERS: dict[str, object] = {}


def _query_embedder(model: str):
    """The embedder the vectors were made with, loaded once per process. A
    load that failed is remembered too, so a status read never retries a
    download; restart the service after fixing it."""
    from .embed import EmbedderUnavailable, FastEmbedder, HashEmbedder

    if model not in _EMBEDDERS:
        try:
            _EMBEDDERS[model] = HashEmbedder(int(model.split("-")[1])) if model.startswith("hash-") else FastEmbedder(model)
        except EmbedderUnavailable as e:
            _EMBEDDERS[model] = e
    found = _EMBEDDERS[model]
    if isinstance(found, Exception):
        raise found
    return found


def _dense(index: passages.Bm25Index):
    from .embed import load_dense

    return load_dense([c.passage.id for c in index.cuts], [f"{c.context}\n{c.passage.text}" for c in index.cuts])


@dataclass
class Detail:
    hits: list[PassageHit]
    lane: str
    usage: Usage = field(default_factory=Usage)
    phrasings: list[str] = field(default_factory=list)
    # Sentences the grading reader returned that are not in their passage.
    unverifiedSentences: int = 0
    # Why another lane ran in place of the chosen one, when it did.
    note: str | None = None
    # Passages of archived programs the rankings left out (OF-BLD-016 §2.3).
    hidden: int = 0


def _visible(include_archived: bool) -> Callable[[str], bool]:
    """Whether a passage id shows: its paper is general or in an active
    program, or archived programs were asked for."""
    if include_archived:
        return lambda pid: True
    archived = programs.archived_ids()
    cache: dict[str, bool] = {}

    def shows(pid: str) -> bool:
        paper = pid.split(":", 1)[0]
        if paper not in cache:
            cache[paper] = programs.program_of_paper(paper) not in archived
        return cache[paper]

    return shows


def search_detail(
    question: str,
    k: int = 8,
    lane: str | None = None,
    *,
    ask: Callable[..., llm.Result] | None = None,
    embedder=None,
    include_archived: bool = False,
) -> Detail:
    note = None
    if lane is None:
        # The chosen lane travels on the data branch; what it needs (vectors,
        # a key) may not be on this machine. A default search then runs on
        # bm25 and says why, where a named lane is refused (§4.R).
        lane = passages.chosen_lane()
        why = why_unavailable(lane, embedder=embedder)
        if why and lane != "bm25":
            note = f"the chosen lane, {lane}, cannot run here ({why}); searched with bm25"
            lane = "bm25"
    why = why_unavailable(lane, embedder=embedder)
    if why:
        raise LaneUnavailable(f"{lane}: {why}")
    index = passages.bm25_index()
    usage = Usage()
    shows = _visible(include_archived)
    # With archived programs hidden, a ranking is read in full and cut to
    # DEPTH after the archived passages leave it.
    depth = DEPTH if include_archived else max(DEPTH, len(index.cuts))
    left_out: set[str] = set()

    def ranked(ids: list[str]) -> list[str]:
        kept = []
        for pid in ids:
            if shows(pid):
                kept.append(pid)
            else:
                left_out.add(pid)
        return kept[:DEPTH]

    rankings: dict[str, list[str]] = {"bm25": ranked([h.passage.id for h in index.search(question, depth)])}
    phrased: list[str] = []

    if lane == "bm25+expand":
        from . import expand

        phrased, spent = expand.phrasings(question, ask=ask)
        usage = llm.add(usage, spent)
        for n, p in enumerate(phrased, start=1):
            rankings[f"phrasing-{n}"] = ranked([h.passage.id for h in index.search(p, depth)])

    if lane.startswith("hybrid"):
        dense, _ = _dense(index)
        assert dense is not None
        emb = embedder or _query_embedder(dense.model)
        qv = emb.embed([question])[0]
        rankings["dense"] = ranked([pid for pid, _ in dense.search(qv, depth)])

    fused = rrf(rankings)
    unverified = 0
    grades: dict[str, int] = {}
    sentences: dict[str, str] = {}
    if lane.endswith("+rerank"):
        from . import rerank

        top = [index.by_id[pid].passage for pid, _, _ in fused[: rerank.TOP]]
        graded = rerank.grade(question, top, ask=ask)
        usage = llm.add(usage, graded.usage)
        unverified = graded.unverified
        grades, sentences = graded.grades, graded.sentences
        position = {pid: n for n, (pid, _, _) in enumerate(fused)}
        fused = sorted(fused, key=lambda f: (-grades.get(f[0], -1), position[f[0]]))

    hits = [
        PassageHit(
            passage=index.by_id[pid].passage,
            score=score,
            lanes=ranks,
            grade=grades.get(pid) if lane.endswith("+rerank") and pid in grades else None,
            sentence=sentences.get(pid),
        )
        for pid, score, ranks in fused[: max(k, 0)]
    ]
    return Detail(hits=hits, lane=lane, usage=usage, phrasings=phrased, unverifiedSentences=unverified, note=note,
                  hidden=len(left_out))


def search(question: str, k: int = 8, lane: str | None = None, **kw) -> list[PassageHit]:
    return search_detail(question, k, lane, **kw).hits
