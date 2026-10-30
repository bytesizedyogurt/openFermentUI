"""Extract — one structured response per document (OF-BLD-012 §6.1; ADR-002).

The whole document goes in, as the passages Sci RAG Kit holds for it
(`kit.passages`: one a chunk, `p0`, `p1`, …, each under the section it sits
in); candidate records come out as JSON that
matches the `emit_candidates` schema, through structured outputs (llm.py), so
the model has exactly one way to respond and the API checks the shape before
we see it. The same pattern `postdoc.py` uses with `emit_answer_plan`, for the
same reason: structured output by construction, not by asking nicely for JSON.
The model is Claude Opus 5.5, with Claude Sonnet 5.5 for a paper Opus declines
or cannot take; each response records which answered.

NOTHING THE MODEL EMITS ENTERS BIOREPO ON ITS SAY-SO. Every candidate goes
through `validate.anchor_candidate` — §2.4's six rules — and only a candidate
whose quote is verbatim in the passage it names, whose value is inside that
quote, whose unit is one the field is denominated in, and whose converted
value is in range survives. The rest are dropped and counted per rule. The
model's `status` and `provenance`, if it offered any, are ignored: both are
'unverified' by construction.

What this module does NOT do. It does not score the run against the seed —
`match_run` (§6.2) does that. It does not decide which candidates are new
records — that is the same function's job. It does not loop: one call per
document, no retries on content, no follow-ups. And it does not fetch: a
document the project does not hold is refused, because there is nothing to
anchor to; Intake collects it first.

Fixture mode (`OPENFERMENT_FIXTURES=1`) reads a saved response from
`tests/fixtures/extract/{paperId}.json` and refuses the API — §8.1's offline
demo replays the loop that way, and the tests here stub the call directly.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from . import db, llm, projects
from .db import models as t
from .literature import collectors, kit
from .models import AuditEvent, Candidate, ExtractResponse, Usage
from .units import tables
from .validate import ANCHOR_RULES, anchor_all, anchor_candidate

log = logging.getLogger("openferment.extract")

# A candidate a model wrote by hand (§7.3) is named apart from the extractor's,
# and kept apart from it, in its own row of the candidates table (source
# `hand`; the extractor's is `model`; OF-BLD-016 §1.R finding 3).
MODEL_PREFIX = "mw1"
MODEL, HAND = "model", "hand"
FIXTURE_DIR = collectors.FIXTURE_ROOT / "extract"
# The first extraction run that runs for real. Named for the pipeline and not
# for one model: Opus answers most papers and Sonnet the ones Opus declines,
# and each response's `usage.models` says which (OF-BLD-012 §6).
RUN = "claude-1"
# `--save-fixture`: after a real call, write {raw, usage} to FIXTURE_DIR so a
# fixture-mode service can replay it (§8.1). Off by default; never in
# fixture mode, where there is no call to save.
SAVE_RESPONSES = False

# The response has to hold EVERY candidate for a paper, at roughly eighty
# tokens each, and a review with many tables carries more than a hundred; a
# response cut off mid-list is malformed, not shorter. Not derived from
# Postdoc's (OF-BLD-012.1 F8): one call writes a handful of claims, this one
# lists every measurement in a paper. The model thinks before it answers and
# the thinking counts against this limit too, hence 32 000 (the call streams,
# so its length is no problem). The split below covers what still does not fit.
MAX_TOKENS = 32_000

# How many times a paper may be halved before the remainder is REPORTED as
# truncated rather than split again (F8). Two is a quarter of a paper per
# call; below that the ontology re-sent with every call costs more than the
# candidates left in the remainder are worth.
MAX_SPLIT_DEPTH = 2

# §6.1: any single section over this is cut at a sentence boundary and the
# response says so in `notes`. Methods sections in long papers exceed it;
# tables rarely do, and tables are where the numbers are.
SECTION_CHAR_LIMIT = 12_000

SYSTEM = """You are Intake, the extraction stage of openFerment. You read one \
paper and emit candidate records for a fixed ontology.

Copy the quote verbatim from the passage you cite. Never paraphrase, never \
tidy, never translate a unit. The value must appear inside the quote, as the \
paper wrote it. A candidate whose quote is not in the passage, or whose value \
is not in the quote, is discarded whole — it is not corrected. Neighbouring passages share a sentence or two; cite \
either.

Emit one candidate per measurement. When a sentence reports someone else's \
result — a citation, a comparison to prior work — set isPrimary to false.

Prefer table rows over prose when both report the same number: a row names \
the condition beside the value. Quote the whole row.

Use only the fields in the ontology you are given, by id. When the paper \
reports nothing for a field, emit nothing for it. Do not guess a field a \
measurement almost fits.

A field marked requiresMethod needs the analytical method the paper used. \
Name it as the paper does; if the paper reports the value without saying how \
it was measured, write "undetermined".

Give the unit as the paper wrote it. Give confidence as your own estimate \
that the quote really reports this field, from 0 to 1.

When the sentence states a RANGE rather than a point — "7-10 days", "0.6 to \
1 g/L", "$4-6/kg" — emit `range` with the low and high as the paper wrote \
them, and set `value` to the midpoint. Do not pick one end and present it as \
the measurement, and do not invent a point the paper did not state.

When the sentence reports an ABSENCE that was measured — "no detectable \
product", "not phosphorylated", "micelles did not form" — emit `value` 0 \
with `negativeResult` true. An absence somebody looked for is a result. A \
field the paper simply never mentions is not, and gets no candidate at all."""


class ExtractTruncated(RuntimeError):
    """The model's response was cut off at the token limit, or held no
    candidates in the expected form. Nothing is kept and NOTHING IS CACHED: an empty extraction
    written to disk would be scored as every record missed and could never
    be re-run without --force. Raised as its own type so the batch can say
    which papers need a second look."""


class ExtractUnavailable(RuntimeError):
    """No key, nothing to anchor to, or the API could not be reached."""


class NothingToAnchor(ExtractUnavailable):
    """The project holds no such document, or the document holds no text:
    nothing for a quote to anchor to."""


# ── the tool ───────────────────────────────────────────────────────────


def build_tool(section_ids: list[str], field_ids: list[str]) -> dict[str, Any]:
    """`emit_candidates`, with this document's passage ids and the ontology's
    field ids as enums, so the model cannot cite a passage that does not
    exist or a field the ontology does not have. §2.4 checks both anyway;
    the enum just stops the wasted output."""
    tool = {
        "name": "emit_candidates",
        "description": (
            "Return every measurement the paper reports for a field in the ontology, "
            "each with the verbatim quote it stands in. This is the only way to respond."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "description": "One entry per measurement. Empty when the paper reports none.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sectionId": {
                                "type": "string",
                                "enum": section_ids,
                                "description": "The passage the quote is copied from.",
                            },
                            "field": {
                                "type": "string",
                                "enum": field_ids,
                                "description": "The ontology field id.",
                            },
                            "value": {
                                "type": ["number", "string"],
                                "description": (
                                    "The number as the paper wrote it, or the category for a "
                                    "categorical field."
                                ),
                            },
                            "unit": {
                                "type": "string",
                                "description": "The unit as the paper wrote it; '' for a categorical field.",
                            },
                            "quote": {
                                "type": "string",
                                "description": (
                                    "Verbatim from the passage, at most 300 characters, containing "
                                    "the value."
                                ),
                            },
                            "method": {
                                "type": "string",
                                "description": (
                                    "The analytical method, when the field requires one. "
                                    "'undetermined' when the paper does not say."
                                ),
                            },
                            "organism": {
                                "type": "string",
                                "description": "The strain or organism the measurement is of, if named.",
                            },
                            # OF-BLD-014 §2.1. Anchoring keeps it only when
                            # the words stand in the cited section.
                            "carbonSource": {
                                "type": "string",
                                "description": (
                                    "The carbon source or feedstock the measurement was made on, in "
                                    "the words the paper uses for it. Omit it when the paper names none."
                                ),
                            },
                            "isPrimary": {
                                "type": "boolean",
                                "description": "False when the sentence reports another paper's measurement.",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            # What the curators can record, the model can say
                            # too (OF-BLD-012.1 F1.4). Without these it has to
                            # invent a point for "7-10 days" and something
                            # arbitrary for "not phosphorylated", and then
                            # disagrees with the seed on exactly the records
                            # the curators handled most carefully.
                            "range": {
                                "type": "object",
                                "description": (
                                    "Present only when the sentence states a range rather than "
                                    "a point. The endpoints as the paper wrote them, in `unit`."
                                ),
                                "properties": {
                                    "low": {"type": "number"},
                                    "high": {"type": "number"},
                                },
                                "required": ["low", "high"],
                            },
                            "negativeResult": {
                                "type": "boolean",
                                "description": (
                                    "True when the sentence reports an absence that was measured "
                                    "rather than a quantity. Emit value 0 with it."
                                ),
                            },
                        },
                        "required": ["sectionId", "field", "value", "unit", "quote", "isPrimary", "confidence"],
                    },
                }
            },
            "required": ["candidates"],
        },
    }
    return tool


# ── the prompt ─────────────────────────────────────────────────────────


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    """Cut at the last sentence end before `limit`. Says whether it cut."""
    if len(text) <= limit:
        return text, False
    head = text[:limit]
    cut = max(head.rfind(". "), head.rfind(".\n"), head.rfind("\n"))
    if cut < limit // 2:
        cut = limit
    return head[: cut + 1].rstrip(), True


def ontology_for_prompt() -> list[dict[str, Any]]:
    """The ontology as the model sees it (§6.1): id, name, definition,
    canonicalUnit, categorical, requiresMethod. Not the range — a range in
    front of an extractor is an invitation to find a number that fits it —
    and not the curator's notes, which carry example values."""
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "definition": f["definition"],
            "canonicalUnit": f["canonicalUnit"],
            "categorical": f["categorical"],
            "requiresMethod": f["requiresMethod"],
        }
        for f in tables()["ontology"].values()
    ]


def build_prompt(sections: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """The user turn: the ontology, then every passage as `[id · heading]`
    followed by its text. Returns the notes for any passage that was cut."""
    notes: list[str] = []
    parts = [
        "Ontology (the only fields you may emit):",
        json.dumps(ontology_for_prompt(), ensure_ascii=False),
        "",
        "Document, by passage:",
    ]
    for s in sections:
        text, cut = _truncate(str(s.get("text") or ""), SECTION_CHAR_LIMIT)
        if cut:
            notes.append(
                f"section {s['id']} was truncated at a sentence boundary to "
                f"{len(text)} of {len(str(s.get('text') or ''))} characters"
            )
        parts.append(f"[{s['id']} · {s.get('heading', '')}]\n{text}")
    return "\n\n".join(parts), notes


# ── the call ───────────────────────────────────────────────────────────


def call_model(paper_id: str, user_text: str, tool: dict[str, Any]) -> tuple[dict[str, Any], Usage]:
    """One call. Returns the raw candidates and what they cost.

    In fixture mode the saved response for the paper is returned instead and
    the API is never touched.
    """
    if collectors.fixtures_only():
        path = FIXTURE_DIR / f"{paper_id}.json"
        if not path.exists():
            raise ExtractUnavailable(f"OPENFERMENT_FIXTURES is set and there is no saved response at {path}")
        saved = json.loads(path.read_text(encoding="utf-8"))
        return saved["raw"], Usage.model_validate(saved.get("usage") or {})

    try:
        result = llm.call(
            system=SYSTEM,
            user=user_text,
            schema=tool["input_schema"],
            max_tokens=MAX_TOKENS,
            label=f"{paper_id}: ",
        )
    except llm.ModelRefused as e:
        # Not cached: a later model, or a later version of this one, may take
        # the paper, and the batch reports it as not extracted.
        raise ExtractUnavailable(f"{paper_id} {e}") from e
    except llm.ModelUnavailable as e:
        spent = f" (${e.usage.costUsd:.4f} spent first)" if e.usage.costUsd else ""
        raise ExtractUnavailable(f"{e}{spent}") from e

    if result.truncated:
        # A list cut off mid-way does not parse into candidates the validator
        # can trust; better no candidates and a loud log line.
        log.warning("%s: response hit max_tokens (%d); candidates dropped", paper_id, MAX_TOKENS)
        return {"candidates": [], "truncated": True, "usage": result.usage.model_dump()}, result.usage
    if result.data is None:
        log.warning("%s: no candidates in the response; stop_reason=%s", paper_id, result.stop_reason)
        return {"candidates": [], "truncated": True, "usage": result.usage.model_dump()}, result.usage
    return result.data, result.usage


# ── persistence ────────────────────────────────────────────────────────
#
# One row of the `candidates` table per paper and source: the extractor's
# run (`model`) and the candidates a model wrote by hand (`hand`), each the
# ExtractResponse as JSON, in the current project (ADR-001, ADR-005).


async def _row(s: AsyncSession, project_id: str, paper_id: str, source: str) -> dict[str, Any] | None:
    return (
        await s.execute(
            select(t.candidates.c.body).where(
                t.candidates.c.project_id == project_id,
                t.candidates.c.document_id == paper_id,
                t.candidates.c.source == source,
            )
        )
    ).scalar_one_or_none()


async def _rows(project_id: str, source: str) -> list[dict[str, Any]]:
    async with db.session() as s:
        q = select(t.candidates.c.body).where(t.candidates.c.project_id == project_id, t.candidates.c.source == source)
        return list((await s.execute(q.order_by(t.candidates.c.document_id))).scalars())


async def _put(s: AsyncSession, project_id: str, source: str, result: ExtractResponse, by: str) -> None:
    stmt = insert(t.candidates).values(
        project_id=project_id, document_id=result.paperId, source=source, body=result.model_dump(mode="json"), created_by=by
    )
    await s.execute(
        stmt.on_conflict_do_update(
            index_elements=[t.candidates.c.project_id, t.candidates.c.document_id, t.candidates.c.source],
            set_={"body": stmt.excluded.body, "updated_at": func.clock_timestamp()},
        )
    )


async def _one(project_id: str, paper_id: str, source: str) -> dict[str, Any] | None:
    async with db.session() as s:
        return await _row(s, project_id, paper_id, source)


def _this_run(paper_id: str, body: dict[str, Any] | None) -> ExtractResponse | None:
    """`body` when it is this run's extraction. One left by an earlier run
    (`haiku-1`, from before the move to Opus) is not this run's and is not
    read: the paper counts as unextracted and the next batch extracts it
    again, under the current run, rather than serving one model's output
    under another's name."""
    if body is None:
        return None
    run = body.get("run") if isinstance(body, dict) else None
    if run is not None and run != RUN:
        log.info("%s: cached extraction is from run %r, not %r; it will be extracted again", paper_id, run, RUN)
        return None
    return ExtractResponse.model_validate(body)


def cached(paper_id: str) -> ExtractResponse | None:
    """This run's extraction of a paper, or None."""
    return _this_run(paper_id, db.run(_one(projects.current(), paper_id, MODEL)))


def all_extracted() -> list[ExtractResponse]:
    """This run's extractions, one per paper, by paper id: what Witness scores."""
    out = []
    for body in db.run(_rows(projects.current(), MODEL)):
        r = _this_run(str(body.get("paperId")), body)
        if r is not None:
            out.append(r)
    return out


# ── candidates a model wrote by hand (OF-BLD-015 §7.3) ─────────────────
#
# Kept in a row of their own and never in the extractor's (OF-BLD-016 §1.R
# finding 3). A hand-written candidate is not an extraction: in the
# extractor's row it made `cached` answer for a paper the extractor never ran
# over, so the batch skipped the paper for good and Witness scored a run that
# never happened. The row has the extractor's shape and is read by `hand`
# alone, never by `cached`.


def by_hand(candidate_id: str) -> bool:
    """Whether this id names a candidate a model wrote by hand."""
    return candidate_id.startswith(f"{MODEL_PREFIX}-")


def hand(paper_id: str) -> ExtractResponse | None:
    """The candidates a model wrote by hand on a paper, or None."""
    body = db.run(_one(projects.current(), paper_id, HAND))
    return None if body is None else ExtractResponse.model_validate(body)


def all_hand() -> list[ExtractResponse]:
    return [ExtractResponse.model_validate(b) for b in db.run(_rows(projects.current(), HAND))]


def all_cached() -> list[ExtractResponse]:
    """Every paper's candidates: this run's extractions, then the candidates
    written by hand. The evidence pool reads all of them; Witness scores
    `all_extracted` alone."""
    return all_extracted() + all_hand()


async def _keep(project_id: str, result: ExtractResponse) -> None:
    async with db.session() as s:
        await _put(s, project_id, MODEL, result, by=RUN)


def _persist(result: ExtractResponse) -> ExtractResponse:
    db.run(_keep(projects.current(), result))
    return result


# ── one paper ──────────────────────────────────────────────────────────


@dataclass
class _Extracted:
    """What one extraction produced, across however many calls it took."""

    raws: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    truncatedSections: list[str] = field(default_factory=list)
    calls: int = 0
    # What the prompt had to cut to fit a section in. Per section, so the
    # same for every call over the same sections; taken from the first.
    notes: list[str] = field(default_factory=list)


def _spent(a: Usage, b: Usage) -> Usage:
    """Every call is paid for, including one that produced nothing."""
    return llm.add(a, b)


def _halve(sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split by cumulative CHARACTER count, not by section count, so the two
    halves cost about the same. A paper whose one table is most of its text
    is exactly the paper that truncates."""
    lengths = [len(str(s.get("text") or "")) for s in sections]
    total = sum(lengths)
    cut, seen = 1, 0
    for i, n in enumerate(lengths):
        seen += n
        if total == 0 or seen * 2 >= total:
            cut = i + 1
            break
    cut = min(max(cut, 1), len(sections) - 1)
    return sections[:cut], sections[cut:]


def _extract_sections(paper_id: str, sections: list[dict[str, Any]], *, depth: int = 0) -> _Extracted:
    """One call over these sections; on truncation, two calls over halves.

    A response cut off at the token limit is not an extraction — the JSON
    is incomplete and nothing in it can be trusted — but it is also not
    evidence that the paper holds no measurements, which is how Witness read
    it before F8. So the paper is halved and asked again, twice, and only the
    remainder that still will not fit is reported as truncated. Candidates
    are content-addressed, so a sentence that lands in both halves collapses
    to one.
    """
    user_text, notes = build_prompt(sections)
    tool = build_tool([s["id"] for s in sections], list(tables()["ontology"].keys()))
    raw, usage = call_model(paper_id, user_text, tool)
    if not raw.get("truncated"):
        raws = raw.get("candidates") or []
        return _Extracted(
            raws=[r for r in raws if isinstance(r, dict)] if isinstance(raws, list) else [],
            usage=usage,
            calls=1,
            notes=notes,
        )

    spent = Usage.model_validate(raw.get("usage") or usage.model_dump())
    ids = [str(s["id"]) for s in sections]
    if len(sections) < 2 or depth >= MAX_SPLIT_DEPTH:
        log.warning(
            "%s: sections %s still truncate at depth %d; reported, not discarded",
            paper_id, ", ".join(ids), depth,
        )
        return _Extracted(usage=spent, truncatedSections=ids, calls=1, notes=notes)

    log.info("%s: response hit max_tokens over %d sections; splitting", paper_id, len(sections))
    left, right = _halve(sections)
    out = _Extracted(usage=spent, calls=1, notes=notes)
    for half in (left, right):
        part = _extract_sections(paper_id, half, depth=depth + 1)
        out.raws.extend(part.raws)
        out.usage = _spent(out.usage, part.usage)
        out.truncatedSections.extend(part.truncatedSections)
        out.calls += part.calls
    return out


def passages(document_id: str) -> list[dict[str, Any]]:
    """The document's passages in the kit, which every quote anchors to.
    Refused when the project holds no such document, or it holds no text."""
    from sci_rag.server.errors import ApiError

    try:
        held = kit.passages(document_id, project_id=projects.current())
    except ApiError as e:
        raise NothingToAnchor(
            f"this project holds no document {document_id}. Collect it first — there is nothing to anchor to."
        ) from e
    if not held.sections:
        raise NothingToAnchor(f"{document_id} holds no text — there is nothing to anchor to.")
    return held.sections


def extract_paper(paper_id: str, *, force: bool = False) -> ExtractResponse:
    """Fetch → prompt → one call → anchor → persist. Cached unless `force`."""
    if not force:
        hit = cached(paper_id)
        if hit is not None:
            return hit

    sections = passages(paper_id)

    got = _extract_sections(paper_id, sections)
    # What the prompt had to cut to fit a section in — from the call that
    # built it, not from building it a second time.
    notes = list(got.notes)
    if got.truncatedSections and not got.raws:
        # Nothing was extracted at all, so nothing is cached (see
        # ExtractTruncated): an empty extraction on disk would be scored as
        # every record missed and could never be re-run without --force.
        raise ExtractTruncated(
            f"{paper_id}: the model's response hit the token limit over every section, "
            f"even split {MAX_SPLIT_DEPTH} deep, or held no candidates in the expected form; nothing kept, "
            f"nothing cached (${got.usage.costUsd:.4f} spent over {got.calls} calls)."
        )
    if got.truncatedSections:
        notes.append(
            "sections " + ", ".join(got.truncatedSections) + " still hit the token limit after "
            f"splitting and were not extracted; the rest of the paper was"
        )
    if SAVE_RESPONSES and not collectors.fixtures_only():
        # The candidates from every call, as one response: a fixture replays
        # the RESULT, and a split is how it was obtained rather than what it
        # was. A run that produced nothing is not saved at all.
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        (FIXTURE_DIR / f"{paper_id}.json").write_text(
            json.dumps(
                {
                    "_note": (
                        f"Saved response of {', '.join(got.usage.models) or 'the model'} for {paper_id}, "
                        "for OPENFERMENT_FIXTURES=1 replay."
                    ),
                    "raw": {"candidates": got.raws},
                    "usage": got.usage.model_dump(),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    usage = got.usage
    anchored = anchor_all(got.raws, sections, paper_id=paper_id)

    # §6.2 — the audit trail starts here. The Candidate model carries no audit
    # (§2.5); the persisted file does, and `ExtractResponse` keeps it beside
    # each candidate so promotion in §7 can carry it onto the record.
    now = datetime.now(timezone.utc).isoformat()
    result = ExtractResponse(
        paperId=paper_id,
        run=RUN,
        extractedAt=now,
        candidates=anchored.accepted,
        audit=[{"at": now, "who": RUN, "action": "extracted"}],
        rejected=anchored.rejected,
        rejectionReasons=anchored.reasons,
        rejectionDetails=anchored.details,
        dropped=anchored.dropped,
        usage=usage,
        notes=notes,
        calls=got.calls,
        truncatedSections=got.truncatedSections,
        fieldDrops=dict(anchored.field_drops),
    )
    if any(anchored.field_drops.values()):
        # §2.1 — a field dropped from a kept candidate is counted, never
        # repaired, and said here the way a rejection is.
        log.warning(
            "%s: anchoring dropped a field from %d kept candidates — %s",
            paper_id,
            sum(anchored.field_drops.values()),
            "; ".join(anchored.field_drop_details),
        )
    if anchored.rejected:
        # §2.4 — a rising rejection rate is the signal that the prompt has
        # drifted, and it is the only signal there is.
        log.warning(
            "%s: anchoring dropped %d/%d candidates — %s",
            paper_id,
            anchored.rejected,
            anchored.rejected + len(anchored.accepted),
            ", ".join(f"{k}={v}" for k, v in anchored.reasons.items() if v),
        )
    return _persist(result)


def add_candidate(paper_id: str, raw: dict[str, Any], *, who: str) -> tuple[Candidate | None, str | None, str | None]:
    """One candidate a model wrote by hand (OF-BLD-015 §7.3), held to §2.4
    like one the extractor emitted: anchored to a sentence of the fetched
    paper, refused with the rule it broke, and appended to the paper's
    hand-written candidates under the lock, with an audit line naming `who`.
    The extractor's file is never created, read or replaced here (§1.R
    finding 3): the paper stays as extracted, or as unextracted, as it was."""
    sections = passages(paper_id)
    return db.run(_add_candidate(projects.current(), paper_id, raw, sections, who))


async def _add_candidate(
    project_id: str, paper_id: str, raw: dict[str, Any], sections: list[dict[str, Any]], who: str
) -> tuple[Candidate | None, str | None, str | None]:
    async with db.session() as s:
        await db.lock(s, "candidates", project_id, paper_id)
        body = await _row(s, project_id, paper_id, HAND)
        current = None if body is None else ExtractResponse.model_validate(body)
        n = len(current.candidates) if current else 0
        made, rule, detail = anchor_candidate(raw, sections, paper_id=paper_id, candidate_id=f"{MODEL_PREFIX}-{paper_id}-{n:04d}")
        if made is None:
            return None, rule, detail
        now = datetime.now(timezone.utc).isoformat()
        if current is None:
            # No model call made this row: no usage, and no calls.
            current = ExtractResponse(paperId=paper_id, extractedAt=now, candidates=[], audit=[], usage=Usage(), calls=0)
        current.candidates.append(made)
        current.audit.append(AuditEvent(at=now, who=who, action=f"candidate {made.id} written by hand"))
        await _put(s, project_id, HAND, current, by=who)
    return made, None, None


# ── batch ──────────────────────────────────────────────────────────────


def extract_all(*, force: bool = False, failed: list[str] | None = None) -> list[ExtractResponse]:
    """Every document the project holds, newest first. A document whose call
    fails is reported and skipped; the batch does not stop for it, and its id
    goes into `failed` when one is given, so the caller can say the batch did
    not finish clean."""
    out: list[ExtractResponse] = []
    for document, _ in kit.documents(projects.current()):
        try:
            out.append(extract_paper(document.id, force=force))
        except ExtractTruncated as e:
            print(f"{document.id} NOT extracted — {e}")
            if failed is not None:
                failed.append(document.id)
        except ExtractUnavailable as e:
            print(f"{document.id} skipped — {e}")
            if failed is not None:
                failed.append(document.id)
    return out


def _print_table(results: list[ExtractResponse]) -> None:
    rules = list(ANCHOR_RULES)
    print(f"{'id':<6} {'kept':>5} {'rejected':>8}  " + "  ".join(f"{r:>7}" for r in rules) + f"  {'in':>7} {'out':>6} {'cost':>9}")
    total_cost = 0.0
    for r in results:
        counts = "  ".join(f"{r.rejectionReasons.get(k, 0):>7}" for k in rules)
        total_cost += r.usage.costUsd
        print(
            f"{r.paperId:<6} {len(r.candidates):>5} {r.rejected:>8}  {counts}  "
            f"{r.usage.inputTokens:>7} {r.usage.outputTokens:>6} ${r.usage.costUsd:>8.4f}"
        )
    kept = sum(len(r.candidates) for r in results)
    rejected = sum(r.rejected for r in results)
    print(f"\n{len(results)} papers · {kept} candidates anchored · {rejected} rejected · ${total_cost:.4f}")


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
    global SAVE_RESPONSES
    force = "--force" in argv
    SAVE_RESPONSES = "--save-fixture" in argv
    if "--all" in argv:
        # Exit 1 when any paper could not be extracted (no key, an outage, a
        # paper too long even split), so the nightly log shows a failed night
        # as one (OF-BLD-012 §B.8). A clean night with nothing new exits 0.
        failed: list[str] = []
        _print_table(extract_all(force=force, failed=failed))
        if failed:
            print(f"{len(failed)} not extracted: {', '.join(failed)}")
        return 1 if failed else 0
    ids = [a for a in argv if not a.startswith("--")]
    if not ids:
        print("usage: python -m openferment_core.extract --all [--force] [--save-fixture] | <paperId> [...]")
        return 2
    results = []
    for paper_id in ids:
        try:
            results.append(extract_paper(paper_id, force=force))
        except (ExtractTruncated, ExtractUnavailable) as e:
            print(f"{paper_id}: {e}")
            return 1
    _print_table(results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
