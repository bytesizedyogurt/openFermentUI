"""Extraction against the real model (OF-BLD-012 §6.1; ADR-002).

Marked `live` and `lit`: needs the network for the fetch, FastEmbed's model to
store the paper in the project's literature, a key for the call, and it
spends money — one model call (Opus, or Sonnet on fallback) over one paper. Excluded from `pnpm verify`;
run with `pnpm test:live`. Prints the per-paper usage so the cost of a real
extraction is a number somebody has seen rather than an estimate.
"""
from __future__ import annotations

import os

import pytest

from openferment_core import extract, intake, projects

pytestmark = [pytest.mark.live, pytest.mark.lit]

needs_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live tests need ANTHROPIC_API_KEY in core/.env",
)


@needs_key
def test_h1_extracts_at_least_one_anchored_candidate(kit_database):
    collected = intake.collect("PMC12292773", project_id=projects.current(), by="the live test")
    assert collected.documentId, collected.reason

    result = extract.extract_paper(collected.documentId, force=True)
    print(
        f"\nH1: {len(result.candidates)} anchored, {result.rejected} rejected "
        f"({', '.join(f'{k}={v}' for k, v in result.rejectionReasons.items() if v) or 'none'}), "
        f"{result.usage.inputTokens} in / {result.usage.outputTokens} out, ${result.usage.costUsd:.4f}"
    )
    assert result.candidates, "a real paper with real tables yielded nothing that anchors"
    for c in result.candidates:
        assert c.status == "unverified" and c.provenance == "unverified"
        assert c.extractorRun == "claude-1"
    assert result.usage.costUsd > 0
