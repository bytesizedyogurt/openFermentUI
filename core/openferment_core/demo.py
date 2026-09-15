"""Regenerate the offline demo's fixtures as a set (OF-BLD-012 §8.1).

    pnpm demo:fixtures            # offline: biorepo.json + the smoke overlay fixture
    pnpm demo:fixtures --real     # + fetch B5's real JATS and save one real model response

The three demo fixtures — the JATS, the saved model response, the decisions
— only make sense together: the response is anchored against that text, and
the decisions are keyed by the content ids the anchoring produced. Replacing
one by hand breaks the other two (test_demo says so), so this rebuilds them
in order, through the real code paths: fixture-mode fetch and extract into a
scratch directory, then `biorepo.write` for each decision.

`--real` first saves the real B5 JATS from Europe PMC and then, with
ANTHROPIC_API_KEY in core/.env, makes ONE call over it and saves the
response with `extract --save-fixture`'s shape. It spends about a cent.
Without `--real`, whatever JATS and response are saved are used as they are.

The smoke overlay fixture (tests/fixtures/overlay-smoke.json), which the
browser tests serve as the service's overlay, is rebuilt from the structural
document and the same two hand-written raw candidates every time, so the
smoke test keeps a fixed, non-paper stand-in regardless of `--real`.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

CORE = Path(__file__).parent.parent
FIXTURES = CORE / "tests" / "fixtures"
DEMO = FIXTURES / "demo"
B5 = {"id": "B5", "pmcid": "PMC8471596"}
AT = "2026-09-15T09:00:00Z"

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


def _point_modules_at(scratch: Path, fixtures: Path) -> None:
    """Redirect the service's directories for this process, the way the demo
    script does with the environment — but after import, so by attribute."""
    from . import biorepo, extract, intake

    intake.DATA_DIR = scratch
    intake.FULLTEXT_DIR = scratch / "fulltext"
    intake.FIXTURE_ROOT = fixtures
    intake.FIXTURE_DIR = fixtures / "jats"
    extract.CANDIDATES_DIR = scratch / "candidates"
    extract.FIXTURE_DIR = fixtures / "extract"
    biorepo.PATH = scratch / "biorepo.json"


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
    print(
        f"saved {extract.FIXTURE_DIR / 'B5.json'}: {len(result.candidates)} anchored, "
        f"{result.rejected} rejected, ${result.usage.costUsd:.4f}"
    )


def rebuild_decisions(scratch: Path) -> list[str]:
    """biorepo.json with three decisions, made through biorepo.write against
    the saved JATS and response: reject the first two candidates, accept
    the curated r-B5-3."""
    from . import biorepo, extract, intake
    from .models import ReviewDecision

    os.environ["OPENFERMENT_FIXTURES"] = "1"
    fetched = intake.fetch_paper(B5, force=True)
    assert fetched.status == "complete", fetched.reason
    result = extract.extract_paper("B5", force=True)
    if len(result.candidates) < 1:
        sys.exit("the saved response anchors no candidate against the saved JATS; nothing to decide on")
    if biorepo.PATH.exists():
        biorepo.PATH.unlink()
    reasons = [
        "not this field — a placeholder table row, not a titre",
        "wrong span — a row of titres read as a colony time",
    ]
    for c, why in zip(result.candidates[:2], reasons):
        biorepo.write(ReviewDecision(status="rejected", provenance="unverified", reviewer="sean",
                                     recordId=c.id, at=AT, rejectReason=why))
    biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="sean",
                                 recordId="r-B5-3", at=AT))
    raw = json.loads(biorepo.PATH.read_text(encoding="utf-8"))
    out = {
        "_note": (
            "pnpm demo:offline (OF-BLD-012 §8.1): a biorepo.json with three decisions, copied "
            "into the demo's scratch data directory at start so Guild and Witness open with "
            "something decided. Written by `pnpm demo:fixtures` through biorepo.write against "
            "the demo fixtures — two rejections of the first two candidates (Witness's false "
            "positives) and one accept of a curated B5 record. Not the committed "
            "core/data/biorepo.json, which the demo never touches."
        ),
        **raw,
    }
    (DEMO / "biorepo.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ids = list(raw["decisions"])
    print(f"wrote {DEMO / 'biorepo.json'}: {ids}")
    return ids


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
    scratch = Path(tempfile.mkdtemp(prefix="of-demo-fixtures-"))
    try:
        _point_modules_at(scratch, DEMO)
        if "--real" in argv:
            save_real(scratch)
        rebuild_decisions(scratch)
        rebuild_smoke_overlay()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    print("\nRun `pnpm test:core` — test_demo and test_api_intake check the set still fits the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
