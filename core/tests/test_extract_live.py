"""Extraction against the real model (OF-BLD-012 §6.1).

Marked `live`: needs the network for the fetch, a key for the call, and it
spends money — one Haiku call over one paper. Excluded from `pnpm verify`;
run with `pnpm test:live`. Prints the per-paper usage so the cost of a real
extraction is a number somebody has seen rather than an estimate.
"""
from __future__ import annotations

import os

import pytest

from openferment_core import extract, intake

pytestmark = pytest.mark.live

needs_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live tests need ANTHROPIC_API_KEY in core/.env",
)


@needs_key
def test_h1_extracts_at_least_one_anchored_candidate():
    fetched = intake.fetch_paper({"id": "H1", "pmcid": "PMC12292773"})
    assert fetched.status == "complete", fetched.reason

    result = extract.extract_paper("H1", force=True)
    print(
        f"\nH1: {len(result.candidates)} anchored, {result.rejected} rejected "
        f"({', '.join(f'{k}={v}' for k, v in result.rejectionReasons.items() if v) or 'none'}), "
        f"{result.usage.inputTokens} in / {result.usage.outputTokens} out, ${result.usage.costUsd:.4f}"
    )
    assert result.candidates, "a real paper with real tables yielded nothing that anchors"
    for c in result.candidates:
        assert c.status == "unverified" and c.provenance == "unverified"
        assert c.extractorRun == "haiku-1"
    assert result.usage.costUsd > 0
