"""Proforma's slow runs (OF-BLD-014 §8.2, §8.3): `pnpm test:slow`, outside
verify. Each starts the real BioSTEAM worker and runs a whole flowsheet."""
from __future__ import annotations

import pytest

from openferment_core import artifacts, intake, proforma

pytestmark = [pytest.mark.slow, pytest.mark.sim]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_the_benchmark_reproduces_the_published_price(store):
    # B.3: 1.968 USD per gallon with the package's defaults, within 0.5 %.
    art = proforma.run_benchmark()
    assert art.output["mespUsdPerGal"] == pytest.approx(1.968, rel=0.005)
    assert art.output["package"] == "biorefineries.cornstover@2.35.1"
    assert art.provenance == "computed" and {i.source.kind for i in art.inputs} == {"model"}
    assert proforma.stored_benchmark().id == art.id
    assert artifacts.replay(art.id).identical
