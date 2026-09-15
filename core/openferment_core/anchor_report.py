"""How many curated records the anchoring rules can promote (OF-BLD-012.1 F1).

    python -m openferment_core.anchor_report

Prints one JSON object on stdout: every numeric seed record run through the
REAL `anchor_candidate`, against a section that says exactly what the record's
quote says, carrying the structure the curators recorded. `scripts/check-
anchors.mjs` reads it and holds the count to a number committed in the guard.

This is the measurement F1 exists for. Before it, 34 of the 104 numeric
curated records could not be promoted to gold: their value is not literally
in their own quote, because the curator wrote the midpoint of a range, or a
zero for an absence, or converted the unit. Rule 3 now reads all three.

A record is run against a synthetic one-section paper rather than a real
fetch so that this measures ANCHORING and nothing else — no network, no
fixtures, and no dependence on which papers happen to have been fetched.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from .corpus import load_corpus
from .validate import anchor_candidate


def report() -> dict[str, Any]:
    corpus = load_corpus()
    rows: list[dict[str, Any]] = []
    for r in corpus.records:
        if r.get("source", "seed") != "seed":
            continue
        value = r["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        sections = [
            {"id": r["sectionId"], "heading": "Results", "text": f"In the run, {r['quote']}."}
        ]
        raw = {
            "sectionId": r["sectionId"],
            "field": r["field"],
            "value": value,
            "unit": r["unit"],
            "quote": r["quote"],
            "method": r.get("method"),
            "range": r.get("range"),
            "negativeResult": r.get("negativeResult"),
            "isPrimary": r.get("primary", True),
            "confidence": 1.0,
        }
        candidate, rule, detail = anchor_candidate(raw, sections, paper_id=r["paperId"])
        rows.append(
            {
                "id": r["id"],
                "field": r["field"],
                "anchors": rule is None,
                "basis": candidate.valueBasis if candidate is not None else None,
                "rule": rule,
                "why": detail,
            }
        )
    return {"records": rows}


def main() -> int:
    json.dump(report(), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
