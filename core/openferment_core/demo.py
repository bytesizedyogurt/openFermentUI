"""Regenerate the offline demo's fixtures as a set (OF-BLD-012 §8.1).

    pnpm demo:fixtures            # offline: the decisions, the export set and the smoke overlay
    pnpm demo:fixtures --real     # + fetch B5's real JATS and save one real model response

The three demo fixtures — the JATS, the saved model response, the decisions
— only make sense together: the response is anchored against that text, and
the decisions are keyed by the content ids the anchoring produced. Replacing
one by hand breaks the other two (test_demo says so), so this rebuilds them
in order, through the real code paths: fixture-mode fetch and extract into a
scratch directory, then `biorepo.write` for each decision.

`--real` first saves the real B5 JATS from Europe PMC and then, with
ANTHROPIC_API_KEY in core/.env, runs one extraction over it (one call, or
more when a response is cut off and the paper is split) and saves the
response with `extract --save-fixture`'s shape, beside what anchoring gave
for it then (`anchoredAtSave`), which test_demo holds every replay to. It
spends what one extraction of B5 costs, and prints it. Without `--real`,
whatever JATS and response are saved are used as they are.

The decisions follow the saved response (OF-BLD-014 §1.5). Over the
hand-written stand-in they demonstrate the review: the titre row promoted to
gold and corrected, the same row rejected as a colony time, and the curated
r-B5-3 accepted. Over a real response, a response whose usage names the
model that answered, they are the accept of r-B5-3 alone: the real
candidates stay undecided for a person in Guild, since two demonstration
decisions over them would record decisions nobody made.

Two fixtures are rebuilt from the structural document and the same two
hand-written raw candidates every time, regardless of `--real`: the smoke
overlay (tests/fixtures/overlay-smoke.json), which the browser tests serve as
the service's overlay, and the export set (tests/fixtures/export/), whose
decisions land all four ways a decision can and which `pnpm test:export`
exports.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

CORE = Path(__file__).parent.parent
FIXTURES = CORE / "tests" / "fixtures"
DEMO = FIXTURES / "demo"
EXPORT = FIXTURES / "export"
B5 = {"id": "B5", "pmcid": "PMC8471596"}
AT = "2026-09-15T09:00:00Z"
# The key, in a saved real response, of what anchoring gave when it was saved.
ANCHORED_AT_SAVE = "anchoredAtSave"

# The raw candidates the smoke overlay is built from — the same two the demo
# response carries: a titre the seed has no B5 record for, and the same row
# read as a colony time.
SMOKE_RAWS = [
    {
        "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
        "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
    },
    {
        "sectionId": "t1", "field": "time_to_colony", "value": 7, "unit": "d",
        "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.55,
    },
]


@contextmanager
def _scratch() -> Iterator[Path]:
    path = Path(tempfile.mkdtemp(prefix="of-demo-fixtures-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def response_is_real(fixtures: Path) -> bool:
    """Whether the saved response for B5 came from a model: a real one names
    the model that answered in its usage, and the hand-written stand-in names
    none (models.Usage)."""
    from .models import Usage

    saved = json.loads((fixtures / "extract" / "B5.json").read_text(encoding="utf-8"))
    return bool(Usage.model_validate(saved.get("usage") or {}).models)


@contextmanager
def _pointed_at(scratch: Path, fixtures: Path) -> Iterator[None]:
    """Redirect the service's directories for this process, the way the demo
    script does with the environment — but after import, so by attribute —
    and put every one back afterwards, OPENFERMENT_FIXTURES included."""
    from . import biorepo, extract, intake

    moved = {
        (intake, "DATA_DIR"): scratch,
        (intake, "FULLTEXT_DIR"): scratch / "fulltext",
        (intake, "FIXTURE_ROOT"): fixtures,
        (intake, "FIXTURE_DIR"): fixtures / "jats",
        (extract, "CANDIDATES_DIR"): scratch / "candidates",
        (extract, "FIXTURE_DIR"): fixtures / "extract",
        (biorepo, "PATH"): scratch / "biorepo.json",
    }
    before = {key: getattr(*key) for key in moved}
    env = os.environ.get("OPENFERMENT_FIXTURES")
    try:
        for (module, name), value in moved.items():
            setattr(module, name, value)
        yield
    finally:
        for (module, name), value in before.items():
            setattr(module, name, value)
        if env is None:
            os.environ.pop("OPENFERMENT_FIXTURES", None)
        else:
            os.environ["OPENFERMENT_FIXTURES"] = env


def record_anchoring(path: Path, result) -> None:
    """Write into a saved response what anchoring gave for it: the candidate
    ids it kept and how many it rejected. A replay is held to these, so a
    change to anchoring that moves the demo shows as a failing test."""
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved[ANCHORED_AT_SAVE] = {"candidates": [c.id for c in result.candidates], "rejected": result.rejected}
    path.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_real(scratch: Path) -> None:
    """The real JATS from Europe PMC, and one real model response over it."""
    from . import extract, intake

    os.environ.pop("OPENFERMENT_FIXTURES", None)
    xml = intake.fetch_fulltext(B5["pmcid"])
    note = (
        "<!--\n  pnpm demo:fixtures --real: Saved from Europe PMC, "
        f"{B5['pmcid']} (B5), for the offline demo (OF-BLD-012 §8.1).\n"
        "  The licence element inside says under what terms.\n-->\n"
    )
    head, rest = (xml.split("\n", 1) + [""])[:2] if xml.startswith("<?xml") else ("", xml)
    (DEMO / "jats").mkdir(parents=True, exist_ok=True)
    (DEMO / "jats" / f"{B5['pmcid']}.xml").write_text(
        (head + "\n" if head else "") + note + rest, encoding="utf-8"
    )
    print(f"saved {DEMO / 'jats' / (B5['pmcid'] + '.xml')}")

    # Fetch in fixture mode from what was just saved, then one real call.
    os.environ["OPENFERMENT_FIXTURES"] = "1"
    fetched = intake.fetch_paper(B5)
    assert fetched.status == "complete", fetched.reason
    os.environ.pop("OPENFERMENT_FIXTURES", None)
    extract.SAVE_RESPONSES = True
    result = extract.extract_paper("B5", force=True)
    record_anchoring(extract.FIXTURE_DIR / "B5.json", result)
    print(
        f"saved {extract.FIXTURE_DIR / 'B5.json'}: {len(result.candidates)} anchored, "
        f"{result.rejected} rejected, ${result.usage.costUsd:.4f}"
    )


def rebuild_decisions(fixtures: Path = DEMO, out: Path | None = None, note: str | None = None) -> list[str]:
    """biorepo.json for one fixture set, made through biorepo.write against
    its saved JATS and response, and written to `out` (the set's own
    biorepo.json unless told otherwise). Returns the decided ids."""
    from . import biorepo, extract, intake
    from .models import Quantity, ReviewDecision

    out = out or fixtures / "biorepo.json"
    real = response_is_real(fixtures)
    with _scratch() as scratch, _pointed_at(scratch, fixtures):
        os.environ["OPENFERMENT_FIXTURES"] = "1"
        fetched = intake.fetch_paper(B5, force=True)
        assert fetched.status == "complete", fetched.reason
        result = extract.extract_paper("B5", force=True)
        if real and not result.candidates:
            sys.exit(
                f"the saved real response anchors no candidate against the saved JATS ({result.rejected} rejected): "
                "a demo with nothing to decide shows nothing. Save another with pnpm demo:fixtures --real"
            )
        if real:
            # §1.5 — a real response is left for a person to decide. The one
            # decision is the accept of a curated record, which decides no
            # candidate and keeps Guild and Witness opening on something
            # reviewed.
            biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="sean",
                                         recordId="r-B5-3", at=AT))
        else:
            if len(result.candidates) < 2:
                sys.exit(
                    f"the saved response anchors {len(result.candidates)} candidate(s) against the saved JATS; "
                    "the three decisions below need two — nothing to decide on"
                )
            # One of each kind of decision, so `pnpm test:export` has all three merge
            # paths to check (OF-BLD-012.1 F4) and the demo opens on a corpus that has
            # actually been reviewed rather than only rejected:
            #
            #   1. the titre row promoted to gold AND corrected into canonical units —
            #      the paper wrote mg/L, the corpus records g/L, and both the gold
            #      value and the correction have to anchor in that same sentence
            #   2. the same row read as a colony time, rejected — Witness's false
            #      positive
            #   3. a curated B5 record accepted as it stands
            first, second = result.candidates[0], result.candidates[1]
            biorepo.write(ReviewDecision(
                status="verified", provenance="gold", reviewer="sean", recordId=first.id, at=AT,
                gold=Quantity(value=first.value, unit=first.unit),
                corrected=Quantity(value=float(first.value) / 1000.0, unit="g L\u207b\u00b9"),
            ))
            biorepo.write(ReviewDecision(
                status="rejected", provenance="unverified", reviewer="sean", recordId=second.id, at=AT,
                rejectReason="wrong span — a row of titres read as a colony time",
            ))
            biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="sean",
                                         recordId="r-B5-3", at=AT))
        raw = json.loads(biorepo.PATH.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"_note": note or (DEMO_NOTE_REAL if real else DEMO_NOTE), **raw}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ids = list(raw["decisions"])
    print(f"wrote {out}: {ids}")
    return ids


DEMO_NOTE = (
    "pnpm demo:offline (OF-BLD-012 §8.1): a biorepo.json with three decisions, copied "
    "into the demo's scratch data directory at start so Guild and Witness open with "
    "something decided. Written by `pnpm demo:fixtures` through biorepo.write against "
    "the demo fixtures — the titre row promoted to gold and corrected into canonical "
    "units, the same row rejected where it was read as a colony time (Witness's false "
    "positive), and one accept of a curated B5 record. Not the committed "
    "core/data/biorepo.json, which the demo never touches."
)
DEMO_NOTE_REAL = (
    "pnpm demo:offline (OF-BLD-012 §8.1, OF-BLD-014 §1.5): a biorepo.json with one decision, "
    "copied into the demo's scratch data directory at start. Written by `pnpm demo:fixtures` "
    "through biorepo.write against the demo fixtures, which hold B5's real text and a real "
    "model response: the accept of the curated r-B5-3. The real candidates are left "
    "undecided, for a person to decide in Guild. Not the committed core/data/biorepo.json, "
    "which the demo never touches."
)
EXPORT_NOTE = (
    "pnpm test:export (OF-BLD-012.1 F4, OF-BLD-014 §1.5): a biorepo.json whose decisions land "
    "all four ways a decision can — the titre row promoted to gold and corrected into "
    "canonical units, the same row rejected where it was read as a colony time, and one "
    "accept of a curated B5 record — over the structural stand-in document and two "
    "hand-written candidates, whatever the demo set holds. Written by `pnpm demo:fixtures` "
    "through biorepo.write. Not the committed core/data/biorepo.json, which the demo never "
    "touches."
)


def rebuild_export_set(out: Path | None = None) -> list[str]:
    """The decision set `pnpm test:export` exports (OF-BLD-014 §1.5): the
    hand-written stand-in, decided all four ways, rebuilt in a scratch
    fixture root from the structural document and SMOKE_RAWS."""
    with _scratch() as root:
        (root / "jats").mkdir()
        shutil.copy2(FIXTURES / "jats" / "structural.xml", root / "jats" / f"{B5['pmcid']}.xml")
        (root / "extract").mkdir()
        (root / "extract" / "B5.json").write_text(
            json.dumps({"_note": "hand-written stand-in (demo.SMOKE_RAWS)", "raw": {"candidates": SMOKE_RAWS},
                        "usage": {}}),
            encoding="utf-8",
        )
        return rebuild_decisions(root, out=out or EXPORT / "biorepo.json", note=EXPORT_NOTE)


def rebuild_smoke_overlay() -> None:
    """The overlay the browser tests are served: the structural document as
    B5's text, the two raw candidates through the real anchoring, the run
    from the real matcher."""
    from .corpus import load_corpus
    from .intake import split_jats
    from .validate import anchor_all
    from .witness import match_run

    path = FIXTURES / "overlay-smoke.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    structural = (FIXTURES / "jats" / "structural.xml").read_text(encoding="utf-8")
    fetched = split_jats(structural, paper_id="B5", pmcid="structural")
    assert fetched.status == "complete", fetched.reason
    sections = [s.model_dump() for s in fetched.sections]
    anchored = anchor_all(SMOKE_RAWS, sections, paper_id="B5")
    assert anchored.rejected == 0, anchored.details
    seed = [r for r in load_corpus().records if r["paperId"] == "B5"]
    run = match_run(anchored.accepted, seed, papers={"B5"}, dropped=anchored.dropped)
    out = {
        "_note": current["_note"],
        "papers": {
            "B5": {
                "ingest": "complete",
                "textSource": "full-text",
                "sections": sections,
                "license": fetched.license.href if fetched.license else None,
                # Fixed, so regenerating an unchanged set leaves the tree clean.
                "fetchedAt": AT,
                "reason": None,
            }
        },
        "records": {},
        "candidates": [c.model_dump(exclude_none=True) for c in anchored.accepted],
        "runs": [run.model_dump(exclude_none=True)],
    }
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}: {[c.id for c in anchored.accepted]}")


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(CORE / ".env", override=False)
    if "--real" in argv:
        with _scratch() as scratch, _pointed_at(scratch, DEMO):
            save_real(scratch)
    rebuild_decisions(DEMO)
    rebuild_export_set()
    rebuild_smoke_overlay()
    print("\nRun `pnpm test:core` — test_demo and test_api_intake check the sets still fit the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
