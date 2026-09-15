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
MAX_TOKENS = POSTDOC_MAX_TOKENS * 4

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
that the quote really reports this field, from 0 to 1."""


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

    user_text, notes = build_prompt(sections)
    tool = build_tool([s["id"] for s in sections], list(tables()["ontology"].keys()))
    raw, usage = call_model(paper_id, user_text, tool)
    if SAVE_RESPONSES and not intake.fixtures_only() and not raw.get("truncated"):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        (FIXTURE_DIR / f"{paper_id}.json").write_text(
            json.dumps(
                {
                    "_note": f"Saved response of {MODEL} for {paper_id}, for OPENFERMENT_FIXTURES=1 replay.",
                    "raw": raw,
                    "usage": usage.model_dump(),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    if raw.get("truncated"):
        # Not an extraction, and not cached as one (see ExtractTruncated).
        spent = Usage.model_validate(raw.get("usage") or usage.model_dump())
        raise ExtractTruncated(
            f"{paper_id}: the model's response hit the token limit or carried no tool call; "
            f"nothing kept, nothing cached (${spent.costUsd:.4f} spent). Split the paper or raise MAX_TOKENS."
        )

    raws = raw.get("candidates") or []
    if not isinstance(raws, list):
        raws = []
    anchored = anchor_all([r for r in raws if isinstance(r, dict)], sections, paper_id=paper_id)

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
