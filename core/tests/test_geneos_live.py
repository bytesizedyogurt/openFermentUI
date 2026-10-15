"""The published C. necator model, reproduced (OF-BLD-014 §6.5, Appendix 2
cases 5 and 6). Needs the file `pnpm geneos:fetch` brings; no key.

    cd core && uv run --all-extras pytest tests/test_geneos_live.py -m live
"""
from __future__ import annotations

import pytest

from openferment_core import geneos, geneos_models as shelf

pytestmark = pytest.mark.live

MODEL = shelf.SHELF["RehMBEL1391"]
REL = 1e-3

needs_file = pytest.mark.skipif(
    not MODEL.fetched.local.is_file(), reason="run pnpm geneos:fetch first: the C. necator file is not here"
)


@needs_file
def test_the_file_is_the_pinned_one():
    assert geneos.sha256_of(MODEL.fetched.local) == MODEL.fetched.sha256


@needs_file
def test_case_5_fructose():
    r = geneos.ceiling("RehMBEL1391", "phb", "fructose", keep=False)
    assert r.output["flux"] == pytest.approx(12.4138, rel=REL)
    assert r.output["molPerMol"] == pytest.approx(1.2414, rel=REL)
    assert r.evidence.value == pytest.approx(0.5932, rel=REL)


@needs_file
def test_case_6_carbon_dioxide_and_hydrogen():
    # A regression check on the file alone: fructose closed, CO2 at 1000 and
    # hydrogen at 100 opened; oxygen at 18.5 binds (Appendix 2).
    from openferment_core.workers import geneos_worker as gw

    m = gw.read_sbml_model(str(MODEL.fetched.local))
    dm = gw.demand(m, "phb_c")
    flux, status = gw._optimum(m, {"EX_co2_e": 1000.0, "EX_h2_e": 100.0}, dm)
    assert status == "optimal" and flux == pytest.approx(4.6250, rel=REL)


@needs_file
def test_its_shape_and_its_missing_sugars():
    d = geneos.describe("RehMBEL1391")
    assert (d["reactions"], d["metabolites"], d["genes"]) == (1538, 1348, 1350)
    assert d["growthReaction"] == "Biomass"
    assert d["substrates"] == {"glucose": False, "fructose": True, "xylose": False}
    assert geneos.ceiling("RehMBEL1391", "phb", "glucose", keep=False).finding == "this reconstruction has no uptake reaction for glucose"


@needs_file
def test_its_frontier_ends_where_appendix_2_says():
    r = geneos.frontier("RehMBEL1391", "phb", "fructose", keep=False)
    assert r.output["points"][-1]["growth"] == pytest.approx(0.9304, rel=REL)
