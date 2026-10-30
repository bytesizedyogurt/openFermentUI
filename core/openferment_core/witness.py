"""Witness — scoring the run that actually ran (OF-BLD-012 §6.2).

`match_run` builds one RunOutput for 'claude-1' by holding every reference
record on an extracted paper against the candidates the extractor produced
for that paper and field. A reference record is a value a reviewer typed, a
gold value or a correction (`reviewed_records`), or a corpus file's curated
record where one is held; alpha 2.0 ships no corpus (ADR-010), so in a
project the references are what its reviewers typed. The outcome vocabulary
is the browser's, from
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
from .units import UnitError, quantity_equals, same_family, to_si
from .validate import recorded_range

log = logging.getLogger("openferment.witness")

RUN = extract.RUN
TOLERANCE_PCT = 2  # the browser's quantityEquals default, and §6.2's number


def _number(value: Any) -> float | None:
    """The number a value is, when it is one. The tool asks for 'the number
    as the paper wrote it', so a dropped candidate can carry '4,200' as a
    string; that is 4200, not a category."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace(" ", ""))
        except ValueError:
            return None
    return None


def _is_categorical(value: Any) -> bool:
    return isinstance(value, str) and _number(value) is None


def _ranges_agree(cr: tuple[float, float], rr: tuple[float, float], cu: str, ru: str) -> bool:
    """Two ranges are the same interval, endpoint for endpoint, after
    conversion (OF-BLD-012.1 F1.4)."""
    try:
        return quantity_equals((cr[0], cu), (rr[0], ru), TOLERANCE_PCT) and quantity_equals(
            (cr[1], cu), (rr[1], ru), TOLERANCE_PCT
        )
    except (TypeError, ValueError):
        return False


def _agrees(
    cv: Any,
    cu: str,
    rv: Any,
    ru: str,
    *,
    c_range: tuple[float, float] | None = None,
    r_range: tuple[float, float] | None = None,
) -> bool:
    """Candidate against seed: strings case-insensitively, numbers within
    tolerance after conversion. A candidate with no value agrees with nothing.

    When both sides record the same range, they are reporting the same
    measurement even if one wrote an endpoint where the other wrote the
    midpoint — so the range is asked first."""
    if c_range is not None and r_range is not None and _ranges_agree(c_range, r_range, cu, ru):
        return True
    if cv is None:
        return False
    if _is_categorical(cv) or _is_categorical(rv):
        return str(cv).strip().lower() == str(rv).strip().lower()
    cn, rn = _number(cv), _number(rv)
    if cn is None or rn is None:
        return False
    try:
        return quantity_equals((cn, cu), (rn, ru), TOLERANCE_PCT)
    except (TypeError, ValueError):
        return False


def _distance(
    cv: Any,
    cu: str,
    rv: Any,
    ru: str,
    *,
    c_range: tuple[float, float] | None = None,
    r_range: tuple[float, float] | None = None,
) -> float | None:
    """How far a candidate is from a seed record, or None when they do not
    agree at all (OF-BLD-012.1 F6).

    Agreement is `_agrees`, which already converts and applies the tolerance;
    this only ORDERS the pairs that agree, so a crude magnitude comparison
    through SI is enough. A categorical match and a matching range are both
    distance zero: there is nothing to be closer or further about."""
    if not _agrees(cv, cu, rv, ru, c_range=c_range, r_range=r_range):
        return None
    if _is_categorical(cv) or _is_categorical(rv) or (c_range and r_range):
        return 0.0
    try:
        cs, _ = to_si(_number(cv) or 0.0, cu)
        rs, _ = to_si(_number(rv) or 0.0, ru)
    except (TypeError, ValueError, UnitError):
        return 0.0
    return abs(cs - rs) / abs(rs) if rs else abs(cs)


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

    THE ALGORITHM (OF-BLD-012.1 F6). One candidate scores one record, and the
    pairing is by distance, not by arrival:

      1. Every (record, candidate) pair of the same paper and field that
         AGREES — `_agrees`, which converts units, honours a recorded range,
         and applies TOLERANCE_PCT — is scored with `_distance`.
      2. The pairs are sorted by distance, ties broken on record order then
         candidate order, and consumed greedily: each record takes its
         closest unclaimed candidate, each candidate scores at most once.
      3. The dropped candidates whose quote failed anchoring are paired the
         same way against whatever records are still unmatched: those are the
         span_errors.
      4. What is left over is judged record by record — a candidate of the
         right family is a value_mismatch, of the wrong family a unit_error,
         nothing at all a miss.

    Greedy-by-distance is not globally optimal, but it is stable, it is
    explainable to a reviewer looking at one row, and it cannot do what
    first-fit did: hand a record the candidate its sibling was closer to and
    then score the sibling a mismatch the extractor never earned.
    """
    scored = set(papers)
    by_key: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_key[(c.paperId, c.field)].append(c)
    dropped_by_key: dict[tuple[str, str], list[DroppedCandidate]] = defaultdict(list)
    for d in dropped or []:
        if d.rule == "quote":
            dropped_by_key[(d.paperId, d.field)].append(d)

    # One candidate scores one record. Several curated records can share a
    # (paper, field) — three expression figures from one paper, or one
    # sentence curated per strain — and scoring each against every candidate
    # would let one extraction match twice, or count the siblings it never
    # addressed as value mismatches. Matches are taken first, consuming the
    # candidate; what remains is judged against what remains.
    scored_records = [rec for rec in seed_records if rec["paperId"] in scored]
    consumed: set[int] = set()
    consumed_dropped: set[int] = set()
    outcome_for: dict[str, ExtractRunResult] = {}

    # F6 — the CLOSEST pair is the match. Every agreeing (record, candidate)
    # pair is scored, sorted by distance, and consumed greedily. Taken in
    # record order instead, the first record could consume the candidate the
    # second one is closer to and leave it a value mismatch the extractor did
    # not earn. Ties break on record order then candidate order, so the result
    # does not depend on what order the candidates arrived in.
    pairs: list[tuple[float, int, int, dict[str, Any], Candidate]] = []
    for ri, rec in enumerate(scored_records):
        key = (rec["paperId"], rec["field"])
        for ci, c in enumerate(by_key.get(key, [])):
            d = _distance(
                c.value, c.unit, rec["value"], rec["unit"],
                c_range=recorded_range(c), r_range=recorded_range(rec),
            )
            if d is not None:
                pairs.append((d, ri, ci, rec, c))
    for _, _, _, rec, hit in sorted(pairs, key=lambda t: (t[0], t[1], t[2])):
        if rec["id"] in outcome_for or id(hit) in consumed:
            continue
        consumed.add(id(hit))
        outcome_for[rec["id"]] = ExtractRunResult(
            goldRecordId=rec["id"], outcome="match", extracted=_quantity(hit.value, hit.unit)
        )

    # The dropped-span pass, paired the same way: a candidate whose value
    # agreed and whose quote failed anchoring is a span_error against the
    # record it is closest to, not against whichever came first.
    span_pairs: list[tuple[float, int, int, dict[str, Any], DroppedCandidate]] = []
    for ri, rec in enumerate(scored_records):
        if rec["id"] in outcome_for:
            continue
        key = (rec["paperId"], rec["field"])
        for di, d in enumerate(dropped_by_key.get(key, [])):
            distance = _distance(d.value, d.unit, rec["value"], rec["unit"])
            if distance is not None:
                span_pairs.append((distance, ri, di, rec, d))
    for _, _, _, rec, span in sorted(span_pairs, key=lambda t: (t[0], t[1], t[2])):
        if rec["id"] in outcome_for or id(span) in consumed_dropped:
            continue
        consumed_dropped.add(id(span))
        outcome_for[rec["id"]] = ExtractRunResult(
            goldRecordId=rec["id"], outcome="span_error", extracted=_quantity(span.value, span.unit)
        )

    for rec in scored_records:
        if rec["id"] in outcome_for:
            continue
        key = (rec["paperId"], rec["field"])
        rv, ru = rec["value"], rec["unit"]
        cands = [c for c in by_key.get(key, []) if id(c) not in consumed]
        if not cands:
            outcome_for[rec["id"]] = ExtractRunResult(goldRecordId=rec["id"], outcome="miss")
            continue
        same = next((c for c in cands if _same_family(c.unit, ru)), None)
        chosen = same if same is not None else cands[0]
        consumed.add(id(chosen))
        outcome_for[rec["id"]] = ExtractRunResult(
            goldRecordId=rec["id"],
            outcome="value_mismatch" if same is not None else "unit_error",
            extracted=_quantity(chosen.value, chosen.unit),
        )

    results = [outcome_for[rec["id"]] for rec in scored_records]

    # falsePositives stays empty here on purpose: a candidate the seed does
    # not cover is unscored until a reviewer rejects it (§6.2, §7.3) —
    # `false_positives` below reads those rejections from the decisions.
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
    """The curated records of a corpus file, and only those (the tests'; alpha
    2.0 ships none, ADR-010). Accepted candidates join the corpus (§7.4) with
    `source: 'biorepo'`; a run scored against them would match the extractor
    against itself, and a field they cover would stop looking new."""
    return [r for r in load_corpus().records if r.get("source", "seed") == "seed"]


def reviewed_records(repo: Any | None = None) -> list[dict[str, Any]]:
    """Every record a reviewer gave a value of their own, a gold value or a
    correction, in the project's decisions: the reviewer's value on the
    candidate's paper and field. What a person typed is independent of the
    extractor, so a run is scored against it; a record accepted as the
    extractor wrote it is not, since it would score the extractor against
    itself."""
    repo = repo if repo is not None else biorepo.read()
    copies = {c.id: c for c in repo.records}
    out: list[dict[str, Any]] = []
    for record_id, decision in repo.decisions.items():
        typed = decision.gold or decision.corrected
        candidate = copies.get(record_id)
        if typed is None or candidate is None:
            continue
        out.append({
            "id": record_id, "paperId": candidate.paperId, "field": candidate.field,
            "value": typed.value, "unit": typed.unit, "source": "biorepo",
        })
    return out


def reference_records(repo: Any | None = None) -> list[dict[str, Any]]:
    """What a run is scored against: the records reviewers typed a value for
    (`reviewed_records`), and a corpus file's curated records where one is
    held, a reviewed record first where both name one id."""
    reviewed = reviewed_records(repo)
    named = {r["id"] for r in reviewed}
    return reviewed + [r for r in seed_records() if r["id"] not in named]


@dataclass
class Gathered:
    """Everything the candidates and the decisions say about candidates, read once."""

    candidates: list[Candidate] = field(default_factory=list)
    # The candidates the extractor produces NOW — what the run is scored on.
    # A copy a decision keeps of a candidate a re-extraction no longer
    # produces is still a record (if accepted) and still a false positive (if
    # rejected), but it is not something the current run got right.
    current: list[Candidate] = field(default_factory=list)
    dropped: list[DroppedCandidate] = field(default_factory=list)
    papers: set[str] = field(default_factory=set)
    # The models that answered, in first-seen order, from each paper's
    # usage.models: what Witness names, never a model typed into the screen.
    models: list[str] = field(default_factory=list)
    decisions: dict[str, ReviewDecision] = field(default_factory=dict)


def _gather() -> Gathered:
    """Every candidate the extractor produced, plus the copies the decisions
    keep of the ones a reviewer decided — the same candidate when both exist
    (ids are content-addressed, so the same id IS the same content), and the
    only copy where the extraction is gone. The scored papers are the
    extracted ones alone: a decided candidate does not make its paper a paper
    the extractor ran over in this project.

    A candidate a model wrote by hand is gathered for the overlay, so Guild
    shows it, and never scored: it makes no paper extracted and is never the
    extractor's match (OF-BLD-016 §1.R finding 3)."""
    repo = biorepo.read()
    responses = extract.all_extracted()
    copies = {c.id: c for c in repo.records}
    out = Gathered(decisions=dict(repo.decisions), papers={r.paperId for r in responses})
    seen: set[str] = set()
    for r in responses:
        for c in r.candidates:
            seen.add(c.id)
            out.candidates.append(copies.get(c.id, c))
            out.current.append(copies.get(c.id, c))
        out.dropped.extend(r.dropped)
        for m in r.usage.models:
            if m not in out.models:
                out.models.append(m)
    for r in extract.all_hand():
        for c in r.candidates:
            if c.id not in seen:
                seen.add(c.id)
                out.candidates.append(copies.get(c.id, c))
    out.candidates += [c for cid, c in copies.items() if cid not in seen]
    return out


def _run(g: Gathered, seed: list[dict[str, Any]]) -> ExtractRun:
    run = match_run(g.current, seed, papers=g.papers, dropped=g.dropped)
    # A rejected hand-written candidate is the model's mistake, not the extractor's.
    run.falsePositives = false_positives(
        [c for c in g.candidates if c.paperId in g.papers and not extract.by_hand(c.id)], g.decisions
    )
    run.models = list(g.models)
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
    """GET /api/witness/runs — recomputed from every paper's candidates against
    the seed, with the reviewers' rejections from the decisions as the false
    positives. Empty when nothing has been extracted: no run, no number."""
    g = _gather()
    if not g.papers:
        return []
    return [_run(g, reference_records())]


def new_candidates() -> list[Candidate]:
    """The candidates the seed has no record for (§6.2): the undecided ones
    from the candidates, and every one a reviewer has decided, from the
    decisions, so an accepted record is still a record where the extraction
    is gone."""
    g = _gather()
    decided = {c.id for c in biorepo.records()}
    fresh = new_records(g.candidates, reference_records(), papers=g.papers) if g.papers else []
    return [c for c in fresh if c.id not in decided] + biorepo.records()


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
    candidates and the decisions — the store asks on every page load and after
    every extraction. A missing corpus.json costs the run, not the rest."""
    g = _gather()
    try:
        runs_ = [_run(g, reference_records())] if g.papers else []
    except FileNotFoundError as e:
        log.warning("overlay without runs — %s", e)
        runs_ = []
    return runs_, g.candidates, g.decisions
