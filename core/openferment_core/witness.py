"""Witness — scoring the run that actually ran (OF-BLD-012 §6.2).

`match_run` builds one RunOutput for 'haiku-1' by holding every seed record
on an extracted paper against the candidates the extractor produced for that
paper and field. The outcome vocabulary is the browser's, from
`computeRunMetrics` in src/engine/metrics.ts, so Witness scores a real run
with the same code it was written to score seeded ones:

  match           some candidate agrees with the seed value within 2 %, after
                  unit conversion — `quantity_equals`, the mirror of the
                  browser's `quantityEquals`, same tolerance
  span_error      no candidate agrees, but one that anchoring REFUSED for its
                  quote did. It never reached BioRepo; it still counts here,
                  because Witness measures the extractor and the extractor
                  produced it
  value_mismatch  a candidate in the field's unit family exists and none agrees
  unit_error      candidates exist and none is in the seed record's unit family
  miss            no candidate for the field at all

Only papers that have been extracted are scored. A fetched paper the
extractor has not seen is not a paper it missed everything on.

Candidates on an extracted paper for a field the seed has no record of are
NEW records — the corpus growing — and they are not scored: there is nothing
to score them against until a reviewer decides. They go to the overlay for
Guild (§7). `RunOutput.falsePositives` lists one only after a reviewer
rejects it; until then the screen says they are unscored.

Nothing here writes. The run is recomputed from candidates/*.json against the
seed on every request, so a re-extraction or a review decision moves the
numbers without a cache to invalidate.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from collections.abc import Iterable
from typing import Any

from . import biorepo, extract
from .corpus import load_corpus
from .models import (
    Candidate,
    DroppedCandidate,
    ExtractRun,
    ExtractRunFalsePositive,
    ExtractRunResult,
    Quantity,
    ReviewDecision,
)
from .units import quantity_equals, same_family

log = logging.getLogger("openferment.witness")

RUN = extract.RUN
TOLERANCE_PCT = 2  # the browser's quantityEquals default, and §6.2's number


def _is_categorical(value: Any) -> bool:
    return isinstance(value, str)


def _agrees(cv: Any, cu: str, rv: Any, ru: str) -> bool:
    """Candidate against seed: strings case-insensitively, numbers within
    tolerance after conversion. A candidate with no value agrees with nothing."""
    if cv is None:
        return False
    if _is_categorical(cv) or _is_categorical(rv):
        return str(cv).strip().lower() == str(rv).strip().lower()
    try:
        return quantity_equals((float(cv), cu), (float(rv), ru), TOLERANCE_PCT)
    except (TypeError, ValueError):
        return False


def _same_family(cu: str, ru: str) -> bool:
    """Categorical records carry no unit on either side; that is the same family."""
    if not cu and not ru:
        return True
    return same_family(cu, ru)


def _quantity(value: Any, unit: str) -> Quantity | None:
    if value is None:
        return None
    return Quantity(value=value, unit=unit)


def match_run(
    candidates: list[Candidate],
    seed_records: list[dict[str, Any]],
    *,
    papers: Iterable[str],
    dropped: list[DroppedCandidate] | None = None,
    run: str = RUN,
) -> ExtractRun:
    """One RunOutput over the seed records of `papers` (§6.2).

    `papers` is the set of paper ids the extractor has actually run over;
    seed records on any other paper are left out rather than counted as
    misses. `dropped` supplies the span_error cases.
    """
    scored = set(papers)
    by_key: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_key[(c.paperId, c.field)].append(c)
    dropped_by_key: dict[tuple[str, str], list[DroppedCandidate]] = defaultdict(list)
    for d in dropped or []:
        if d.rule == "quote":
            dropped_by_key[(d.paperId, d.field)].append(d)

    results: list[ExtractRunResult] = []
    for rec in seed_records:
        if rec["paperId"] not in scored:
            continue
        key = (rec["paperId"], rec["field"])
        rv, ru = rec["value"], rec["unit"]
        cands = by_key.get(key, [])

        hit = next((c for c in cands if _agrees(c.value, c.unit, rv, ru)), None)
        if hit is not None:
            results.append(
                ExtractRunResult(goldRecordId=rec["id"], outcome="match", extracted=_quantity(hit.value, hit.unit))
            )
            continue

        span = next(
            (d for d in dropped_by_key.get(key, []) if _agrees(d.value, d.unit, rv, ru)),
            None,
        )
        if span is not None:
            results.append(
                ExtractRunResult(
                    goldRecordId=rec["id"], outcome="span_error", extracted=_quantity(span.value, span.unit)
                )
            )
            continue

        if not cands:
            results.append(ExtractRunResult(goldRecordId=rec["id"], outcome="miss"))
            continue

        same = next((c for c in cands if _same_family(c.unit, ru)), None)
        if same is not None:
            results.append(
                ExtractRunResult(
                    goldRecordId=rec["id"], outcome="value_mismatch", extracted=_quantity(same.value, same.unit)
                )
            )
        else:
            first = cands[0]
            results.append(
                ExtractRunResult(
                    goldRecordId=rec["id"], outcome="unit_error", extracted=_quantity(first.value, first.unit)
                )
            )

    # falsePositives stays empty here on purpose: a candidate the seed does
    # not cover is unscored until a reviewer rejects it (§6.2, §7.3) —
    # `false_positives` below reads those rejections from biorepo.json.
    return ExtractRun(run=run, results=results, falsePositives=[])


def false_positives(
    candidates: list[Candidate], decisions: dict[str, ReviewDecision]
) -> list[ExtractRunFalsePositive]:
    """The candidates a reviewer rejected, with the reason (§6.2, §7.3).
    The only way onto this list: no candidate is a false positive because a
    score said so, only because a person did."""
    out: list[ExtractRunFalsePositive] = []
    for c in candidates:
        d = decisions.get(c.id)
        if d is None or d.status != "rejected":
            continue
        out.append(
            ExtractRunFalsePositive(
                id=c.id,
                paperId=c.paperId,
                field=c.field,
                extracted=Quantity(value=c.value, unit=c.unit),
                note=d.rejectReason or "rejected without a stated reason",
            )
        )
    return out


def new_records(
    candidates: list[Candidate],
    seed_records: list[dict[str, Any]],
    *,
    papers: Iterable[str],
) -> list[Candidate]:
    """Candidates on an extracted paper for a field the seed has no record of.
    These are the corpus growing; they go to Guild, not to the score."""
    scored = set(papers)
    covered = {(r["paperId"], r["field"]) for r in seed_records}
    return [c for c in candidates if c.paperId in scored and (c.paperId, c.field) not in covered]


# ── from the cache ─────────────────────────────────────────────────────


def seed_records() -> list[dict[str, Any]]:
    """The curated records, and only those. `pnpm export:corpus` appends
    accepted candidates to corpus.json (§7.4) with `source: 'biorepo'`; a run
    scored against them would match the extractor against itself, and a
    field they cover would stop looking new. The seed is what is scored."""
    return [r for r in load_corpus().records if r.get("source", "seed") == "seed"]


_CONTENT = ("sectionId", "field", "value", "unit", "quote")


def _same_content(a: Candidate, b: Candidate) -> bool:
    return all(getattr(a, k) == getattr(b, k) for k in _CONTENT)


@dataclass
class Gathered:
    """Everything the cache and biorepo.json say about candidates, read once."""

    candidates: list[Candidate] = field(default_factory=list)
    dropped: list[DroppedCandidate] = field(default_factory=list)
    papers: set[str] = field(default_factory=set)
    decisions: dict[str, ReviewDecision] = field(default_factory=dict)
    # Candidate ids whose biorepo.json copy no longer matches what the cache
    # holds under that id: the paper was re-extracted and the numbering moved.
    stale: set[str] = field(default_factory=set)


def _gather() -> Gathered:
    """Every candidate the extractor produced, plus the copies biorepo.json
    keeps of the ones a reviewer decided — the same candidate when both exist,
    and the only copy on a fresh clone where candidates/ is empty. The scored
    papers are the extracted ones alone: a decided candidate does not make
    its paper a paper the extractor ran over in this checkout.

    Ids are positional (§6.2: hk1-<paperId>-<n>), so a re-extraction can put
    different content under an id a reviewer already decided. When the copy
    and the cache disagree on content, the cache wins — it is what the
    extractor says now — and the decision is STALE: not applied, not a false
    positive, logged with the ids so someone re-decides. A decision about a
    sentence must not follow the id to a different sentence."""
    repo = biorepo.read()
    responses = extract.all_cached()
    copies = {c.id: c for c in repo.records}
    out = Gathered(decisions=dict(repo.decisions), papers={r.paperId for r in responses})
    seen: set[str] = set()
    for r in responses:
        for c in r.candidates:
            seen.add(c.id)
            copy = copies.get(c.id)
            if copy is not None and not _same_content(copy, c):
                out.stale.add(c.id)
                out.candidates.append(c)
            else:
                out.candidates.append(copy or c)
        out.dropped.extend(r.dropped)
    out.candidates += [c for cid, c in copies.items() if cid not in seen]
    for cid in out.stale:
        out.decisions.pop(cid, None)
    if out.stale:
        log.warning(
            "witness: %d decision(s) are stale — the paper was re-extracted and the candidate under "
            "the same id changed: %s. Not applied; decide again in Guild.",
            len(out.stale),
            ", ".join(sorted(out.stale)),
        )
    return out


def _run(g: Gathered, seed: list[dict[str, Any]]) -> ExtractRun:
    run = match_run(g.candidates, seed, papers=g.papers, dropped=g.dropped)
    run.falsePositives = false_positives([c for c in g.candidates if c.paperId in g.papers], g.decisions)
    outcomes: dict[str, int] = defaultdict(int)
    for r in run.results:
        outcomes[r.outcome] += 1
    log.info(
        "witness: %s over %d papers → %d scored (%s), %d new, %d rejected",
        RUN,
        len(g.papers),
        len(run.results),
        ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())) or "nothing",
        len(new_records(g.candidates, seed, papers=g.papers)),
        len(run.falsePositives),
    )
    return run


def runs() -> list[ExtractRun]:
    """GET /api/witness/runs — recomputed from every candidates/*.json against
    the seed, with the reviewers' rejections from biorepo.json as the false
    positives. Empty when nothing has been extracted: no run, no number."""
    g = _gather()
    if not g.papers:
        return []
    return [_run(g, seed_records())]


def new_candidates() -> list[Candidate]:
    """The candidates the seed has no record for (§6.2): the undecided ones
    from the cache, and every one a reviewer has decided, from biorepo.json,
    so an accepted record is still a record on a checkout that never ran the
    extractor."""
    g = _gather()
    decided = {c.id for c in biorepo.records()} - g.stale
    fresh = new_records(g.candidates, seed_records(), papers=g.papers) if g.papers else []
    out = [c for c in fresh if c.id not in decided]
    return out + [c for c in biorepo.records() if c.id not in g.stale]


def overlay_candidates() -> list[Candidate]:
    """`overlay.candidates` (§2.1, §7.3): EVERY candidate, not only the new
    ones. A candidate that matches a seed record's field is not a record —
    the seed has one — but it is what the review card shows beside that
    record: the extractor's reading of the same paper, and the span a
    promotion carries when the curated quote is not in the fetched text. The
    browser sorts new from matching with the seed in hand; the decisions
    travel in `overlay.records`."""
    return _gather().candidates


def overlay_bundle() -> tuple[list[ExtractRun], list[Candidate], dict[str, ReviewDecision]]:
    """Runs, candidates and decisions for the overlay, from ONE read of the
    cache and biorepo.json — the store asks on every page load and after
    every extraction. A missing corpus.json costs the run, not the rest."""
    g = _gather()
    try:
        runs_ = [_run(g, seed_records())] if g.papers else []
    except FileNotFoundError as e:
        log.warning("overlay without runs — %s", e)
        runs_ = []
    return runs_, g.candidates, g.decisions
