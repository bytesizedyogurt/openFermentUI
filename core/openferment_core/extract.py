"""Extract — one forced tool call per paper (OF-BLD-012 §6.1).

The whole paper goes in, as sections; candidate records come out, through a
single tool, `emit_candidates`, with `tool_choice` pinned to it so the model
has exactly one way to respond and the API checks the shape before we see it.
The same pattern `postdoc.py` uses with `emit_answer_plan`, for the same
reason: structured output by construction, not by asking nicely for JSON.

NOTHING THE MODEL EMITS ENTERS BIOREPO ON ITS SAY-SO. Every candidate goes
through `validate.anchor_candidate` — §2.4's six rules — and only a candidate
whose quote is verbatim in the section it names, whose value is inside that
quote, whose unit is one the field is denominated in, and whose converted
value is in range survives. The rest are dropped and counted per rule. The
model's `status` and `provenance`, if it offered any, are ignored: both are
'unverified' by construction.

What this module does NOT do. It does not score the run against the seed —
`match_run` (§6.2) does that. It does not decide which candidates are new
records — that is the same function's job. It does not loop: one call per
paper, no retries on content, no follow-ups. And it does not fetch: a paper
with no cached full text is refused, because there is nothing to anchor to.

Fixture mode (`OPENFERMENT_FIXTURES=1`) reads a saved response from
`tests/fixtures/extract/{paperId}.json` and refuses the API — §8.1's offline
demo replays the loop that way, and the tests here stub the call directly.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import anthropic

from . import intake
from .models import Candidate, ExtractResponse, Usage
from .postdoc import MAX_TOKENS as POSTDOC_MAX_TOKENS, MODEL, cost_usd
from .units import tables
from .validate import anchor_all

log = logging.getLogger("openferment.extract")

CANDIDATES_DIR = intake.DATA_DIR / "candidates"
FIXTURE_DIR = intake.FIXTURE_ROOT / "extract"
RUN = "haiku-1"
# `--save-fixture`: after a real call, write {raw, usage} to FIXTURE_DIR so a
# fixture-mode service can replay it (§8.1). Off by default; never in
# fixture mode, where there is no call to save.
SAVE_RESPONSES = False

# A paper can yield dozens of candidates at roughly eighty tokens each, and
# Postdoc's 2000 would truncate the tool call mid-list — a truncated tool
# input is a malformed response, not a shorter one. Four times Postdoc's
# budget, and still one call.
# The response has to hold EVERY candidate for a paper, and a review with
# many tables carries more than a hundred. No longer derived from Postdoc's
# (OF-BLD-012.1 F8): the two calls answer different questions — one writes a
# handful of claims, this one lists every measurement in a paper — and tying
# them together meant a limit chosen for the first silently capped the
# second. 16 000 covers the corpus; the split below covers what it does not.
MAX_TOKENS = 16_000

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

Copy the quote verbatim from the section you cite. Never paraphrase, never \
tidy, never translate a unit. The value must appear inside the quote, as the \
paper wrote it. A candidate whose quote is not in the section, or whose value \
is not in the quote, is discarded whole — it is not corrected.

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
    """The model's response was cut off at the token limit, or carried no tool
    call at all. Nothing is kept and NOTHING IS CACHED: an empty extraction
    written to disk would be scored as every record missed and could never
    be re-run without --force. Raised as its own type so the batch can say
    which papers need a second look."""


class ExtractUnavailable(RuntimeError):
    """No key, no cached text, or the API could not be reached."""


# ── the tool ───────────────────────────────────────────────────────────


def build_tool(section_ids: list[str], field_ids: list[str]) -> dict[str, Any]:
    """`emit_candidates`, with this paper's section ids and the ontology's
    field ids as enums, so the model cannot cite a section that does not
    exist or a field the ontology does not have. §2.4 checks both anyway;
    the enum just stops the wasted output."""
    return {
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
                                "description": "The section the quote is copied from.",
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
                                    "Verbatim from the section, at most 300 characters, containing "
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
    """The user turn: the ontology, then every section as `[id · heading]`
    followed by its text. Returns the notes for any section that was cut."""
    notes: list[str] = []
    parts = [
        "Ontology (the only fields you may emit):",
        json.dumps(ontology_for_prompt(), ensure_ascii=False),
        "",
        "Paper, by section:",
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
    """One call. Returns the raw tool input and what it cost.

    In fixture mode the saved response for the paper is returned instead and
    the API is never touched.
    """
    if intake.fixtures_only():
        path = FIXTURE_DIR / f"{paper_id}.json"
        if not path.exists():
            raise ExtractUnavailable(f"OPENFERMENT_FIXTURES is set and there is no saved response at {path}")
        saved = json.loads(path.read_text(encoding="utf-8"))
        return saved["raw"], Usage.model_validate(saved.get("usage") or {})

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ExtractUnavailable(
            "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."
        )
    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": user_text}],
            tools=[tool],
            # Forced, not suggested — the same discipline as Postdoc.
            tool_choice={"type": "tool", "name": "emit_candidates"},
        )
    except anthropic.APIConnectionError as e:
        raise ExtractUnavailable(f"Could not reach the Anthropic API: {e}") from e
    except anthropic.AuthenticationError as e:
        raise ExtractUnavailable("The Anthropic API rejected the key in core/.env.") from e
    except anthropic.RateLimitError as e:
        raise ExtractUnavailable("Rate limited by the Anthropic API. Wait and try again.") from e
    except anthropic.APIStatusError as e:
        raise ExtractUnavailable(f"Anthropic API error {e.status_code}: {e.message}") from e

    usage = Usage(
        inputTokens=response.usage.input_tokens,
        outputTokens=response.usage.output_tokens,
        costUsd=cost_usd(response.usage.input_tokens, response.usage.output_tokens),
    )
    if response.stop_reason == "max_tokens":
        # A tool input cut off mid-list does not parse into candidates the
        # validator can trust; better no candidates and a loud log line.
        log.warning("%s: response hit max_tokens (%d); candidates dropped", paper_id, MAX_TOKENS)
        return {"candidates": [], "truncated": True, "usage": usage.model_dump()}, usage
    for block in response.content:
        if block.type == "tool_use" and block.name == "emit_candidates":
            raw = block.input if isinstance(block.input, dict) else json.loads(block.input)
            return raw, usage
    log.warning("%s: no tool_use block; stop_reason=%s", paper_id, response.stop_reason)
    return {"candidates": [], "truncated": True, "usage": usage.model_dump()}, usage


# ── persistence ────────────────────────────────────────────────────────


def _path(paper_id: str) -> Path:
    return CANDIDATES_DIR / f"{paper_id}.json"


def cached(paper_id: str) -> ExtractResponse | None:
    path = _path(paper_id)
    if not path.exists():
        return None
    return ExtractResponse.model_validate_json(path.read_text(encoding="utf-8"))


def all_cached() -> list[ExtractResponse]:
    if not CANDIDATES_DIR.exists():
        return []
    out = []
    for path in sorted(CANDIDATES_DIR.glob("*.json")):
        r = cached(path.stem)
        if r is not None:
            out.append(r)
    return out


def _persist(result: ExtractResponse) -> ExtractResponse:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    _path(result.paperId).write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


# ── one paper ──────────────────────────────────────────────────────────


@dataclass
class _Extracted:
    """What one extraction produced, across however many calls it took."""

    raws: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    truncatedSections: list[str] = field(default_factory=list)
    calls: int = 0


def _spent(a: Usage, b: Usage) -> Usage:
    """Every call is paid for, including one that produced nothing."""
    return Usage(
        inputTokens=a.inputTokens + b.inputTokens,
        outputTokens=a.outputTokens + b.outputTokens,
        costUsd=a.costUsd + b.costUsd,
    )


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

    A response cut off at the token limit is not an extraction — the tool
    call is incomplete and nothing in it can be trusted — but it is also not
    evidence that the paper holds no measurements, which is how Witness read
    it before F8. So the paper is halved and asked again, twice, and only the
    remainder that still will not fit is reported as truncated. Candidates
    are content-addressed, so a sentence that lands in both halves collapses
    to one.
    """
    user_text, _ = build_prompt(sections)
    tool = build_tool([s["id"] for s in sections], list(tables()["ontology"].keys()))
    raw, usage = call_model(paper_id, user_text, tool)
    if not raw.get("truncated"):
        raws = raw.get("candidates") or []
        return _Extracted(
            raws=[r for r in raws if isinstance(r, dict)] if isinstance(raws, list) else [],
            usage=usage,
            calls=1,
        )

    spent = Usage.model_validate(raw.get("usage") or usage.model_dump())
    ids = [str(s["id"]) for s in sections]
    if len(sections) < 2 or depth >= MAX_SPLIT_DEPTH:
        log.warning(
            "%s: sections %s still truncate at depth %d; reported, not discarded",
            paper_id, ", ".join(ids), depth,
        )
        return _Extracted(usage=spent, truncatedSections=ids, calls=1)

    log.info("%s: response hit max_tokens over %d sections; splitting", paper_id, len(sections))
    left, right = _halve(sections)
    out = _Extracted(usage=spent, calls=1)
    for half in (left, right):
        part = _extract_sections(paper_id, half, depth=depth + 1)
        out.raws.extend(part.raws)
        out.usage = _spent(out.usage, part.usage)
        out.truncatedSections.extend(part.truncatedSections)
        out.calls += part.calls
    return out


def extract_paper(paper_id: str, *, force: bool = False) -> ExtractResponse:
    """Fetch → prompt → one call → anchor → persist. Cached unless `force`."""
    if not force:
        hit = cached(paper_id)
        if hit is not None:
            return hit

    fetched = intake.cached(paper_id)
    if fetched is None or fetched.status != "complete" or not fetched.sections:
        raise ExtractUnavailable(
            f"{paper_id} has no cached full text. Fetch it first — there is nothing to anchor to."
        )
    sections = [s.model_dump() for s in fetched.sections]

    # What the prompt had to cut to fit a section in; the same for every call
    # below, because the sections are the same.
    _, notes = build_prompt(sections)
    got = _extract_sections(paper_id, sections)
    if got.truncatedSections and not got.raws:
        # Nothing was extracted at all, so nothing is cached (see
        # ExtractTruncated): an empty extraction on disk would be scored as
        # every record missed and could never be re-run without --force.
        raise ExtractTruncated(
            f"{paper_id}: the model's response hit the token limit over every section, "
            f"even split {MAX_SPLIT_DEPTH} deep, or carried no tool call; nothing kept, "
            f"nothing cached (${got.usage.costUsd:.4f} spent over {got.calls} calls)."
        )
    if got.truncatedSections:
        notes.append(
            "sections " + ", ".join(got.truncatedSections) + " still hit the token limit after "
            f"splitting and were not extracted; the rest of the paper was"
        )
    if SAVE_RESPONSES and not intake.fixtures_only():
        # The candidates from every call, as one response: a fixture replays
        # the RESULT, and a split is how it was obtained rather than what it
        # was. A run that produced nothing is not saved at all.
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        (FIXTURE_DIR / f"{paper_id}.json").write_text(
            json.dumps(
                {
                    "_note": f"Saved response of {MODEL} for {paper_id}, for OPENFERMENT_FIXTURES=1 replay.",
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


# ── batch ──────────────────────────────────────────────────────────────


def extract_all(*, force: bool = False) -> list[ExtractResponse]:
    """Every paper with cached full text, in id order. A paper whose call
    fails is reported and skipped; the batch does not stop for it."""
    out: list[ExtractResponse] = []
    for paper_id, status in intake.all_statuses().items():
        if status.ingest != "complete":
            continue
        try:
            out.append(extract_paper(paper_id, force=force))
        except ExtractTruncated as e:
            print(f"{paper_id:<6} NOT extracted — {e}")
        except ExtractUnavailable as e:
            print(f"{paper_id:<6} skipped — {e}")
    return out


def _print_table(results: list[ExtractResponse]) -> None:
    rules = ["field", "section", "quote", "value", "unit", "range", "method"]
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
        _print_table(extract_all(force=force))
        return 0
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
