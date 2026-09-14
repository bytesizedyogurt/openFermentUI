"""Intake against the real Europe PMC (OF-BLD-012 §5.5).

Marked `live`: needs the network and is excluded from `pnpm verify`. Run with
`pnpm test:live`. No key is needed for this one — Europe PMC's open-access
subset is public — but it is still a request to somebody else's server, so it
fetches one paper and stops.
"""
from __future__ import annotations

import pytest

from openferment_core.intake import fetch_fulltext, split_jats

pytestmark = pytest.mark.live


def test_h1_fetches_and_splits_into_at_least_ten_sections():
    xml = fetch_fulltext("PMC12292773")  # H1
    result = split_jats(xml, paper_id="H1", pmcid="PMC12292773")
    assert result.status == "complete", result.reason
    assert len(result.sections) >= 10
    assert result.license is not None
