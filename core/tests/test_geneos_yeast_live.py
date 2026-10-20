"""The two yeast reconstructions, reproduced: an ethanol ceiling on glucose
from Yeast9 and from iMM904. Needs the files `pnpm geneos:fetch` brings; no
key.

    cd core && uv run --all-extras pytest tests/test_geneos_yeast_live.py -m live

The values are regression constants, measured on 2026-10-20 with cobra
0.32.1 and GLPK through the geneOS worker, at the shelf's conventions (sugar
uptake opened at 10 mmol gDW-1 h-1, every other bound as the file publishes
it). Tolerance 0.1 % relative. Glucose to ethanol at two per glucose is the
redox balance of the sugar, so both genome-scale networks reach it.
"""
from __future__ import annotations

import pytest

from openferment_core import geneos, geneos_models as shelf

pytestmark = pytest.mark.live

REL = 1e-3
YEAST9, IMM904 = shelf.SHELF["Yeast9"], shelf.SHELF["iMM904"]


def needs(model):
    return pytest.mark.skipif(not model.fetched.local.is_file(),
                              reason=f"run pnpm geneos:fetch first: the {model.id} file is not here")


@pytest.mark.parametrize("model", [YEAST9, IMM904], ids=lambda m: m.id)
def test_the_file_is_the_pinned_one(model):
    if not model.fetched.local.is_file():
        pytest.skip(f"run pnpm geneos:fetch first: the {model.id} file is not here")
    assert geneos.sha256_of(model.fetched.local) == model.fetched.sha256


@pytest.mark.parametrize("model_id, flux, mol, gg", [
    ("Yeast9", 20.0000, 2.0000, 0.5114),
    ("iMM904", 20.0000, 2.0000, 0.5114),
])
def test_an_ethanol_ceiling_on_glucose(model_id, flux, mol, gg):
    if not shelf.SHELF[model_id].fetched.local.is_file():
        pytest.skip(f"run pnpm geneos:fetch first: the {model_id} file is not here")
    r = geneos.ceiling(model_id, "ethanol", "glucose", keep=False)
    assert r.finding is None
    assert r.output["status"] == "optimal" and r.output["solver"] == "glpk_interface"
    assert r.output["exchange"] == shelf.exchange_id(model_id, "glucose")
    assert r.output["flux"] == pytest.approx(flux, rel=REL)
    assert r.output["molPerMol"] == pytest.approx(mol, rel=REL)
    assert r.evidence.value == pytest.approx(gg, rel=REL)
    assert r.evidence.provenance == "computed" and r.evidence.label.startswith("most ethanol from glucose")


@pytest.mark.parametrize("model_id, flux, mol, gg", [
    # Yeast9's xylose reductase takes NADPH and its xylitol dehydrogenase
    # gives NADH: the imbalance holds it below xylose's redox limit.
    ("Yeast9", 15.0000, 1.5000, 0.4603),
    ("iMM904", 16.6667, 1.6667, 0.5114),
])
def test_an_ethanol_ceiling_on_xylose(model_id, flux, mol, gg):
    if not shelf.SHELF[model_id].fetched.local.is_file():
        pytest.skip(f"run pnpm geneos:fetch first: the {model_id} file is not here")
    r = geneos.ceiling(model_id, "ethanol", "xylose", keep=False)
    assert r.output["flux"] == pytest.approx(flux, rel=REL)
    assert r.output["molPerMol"] == pytest.approx(mol, rel=REL)
    assert r.evidence.value == pytest.approx(gg, rel=REL)


@needs(YEAST9)
def test_yeast9_shape_and_its_mapped_exchanges():
    d = geneos.describe("Yeast9")
    assert (d["reactions"], d["metabolites"], d["genes"]) == (4105, 2748, 1143), "the counts the file publishes"
    assert d["added"] == [], "ethanol leaves through the file's own exchange; nothing is added"
    assert d["growthReaction"] == "r_2111"
    assert d["substrates"] == {"glucose": True, "fructose": True, "xylose": True}
    assert d["products"] == {"phb": False, "ethanol": True}
    assert geneos.ceiling("Yeast9", "phb", "glucose", keep=False).finding == "this reconstruction has no route to poly(3-hydroxybutyrate)"


@needs(IMM904)
def test_imm904_shape():
    d = geneos.describe("iMM904")
    assert (d["reactions"], d["metabolites"], d["genes"]) == (1577, 1226, 905), "the counts BiGG publishes"
    assert d["added"] == [] and d["growthReaction"] == "BIOMASS_SC5_notrace"
    assert d["substrates"] == {"glucose": True, "fructose": True, "xylose": True}
    assert d["products"] == {"phb": False, "ethanol": True}


@needs(YEAST9)
@needs(IMM904)
def test_what_the_shelf_says_of_each_file_is_what_the_file_holds():
    # The route, the notes' published bounds and the mapped names, read from
    # the files themselves, so the shelf's words cannot drift from them.
    from openferment_core.workers import geneos_worker as gw

    y = gw.read_sbml_model(str(YEAST9.fetched.local))
    gw.check_exchange_names(y, YEAST9)
    assert y.reactions.get_by_id("r_0959").name == "pyruvate decarboxylase"
    assert y.reactions.get_by_id("r_2115").name == "alcohol dehydrogenase, (acetaldehyde to ethanol)"
    assert y.reactions.get_by_id("r_1992").name == "oxygen exchange" and y.reactions.get_by_id("r_1992").lower_bound == -1000
    assert y.reactions.get_by_id("r_4046").bounds == pytest.approx((0.7, 0.7))
    m = gw.read_sbml_model(str(IMM904.fetched.local))
    assert {"PYRDC", "ALCD2ir", "EX_etoh_e"} <= {r.id for r in m.reactions}
    assert m.reactions.get_by_id("EX_o2_e").lower_bound == -2 and m.reactions.get_by_id("ATPM").bounds == (1, 1)


@pytest.mark.parametrize("model_id, rxn, growth_max, flux_at_max", [
    ("Yeast9", "r_2111", 0.8386, 0.0),
    # Oxygen at the file's 2 binds: the fastest-growing cell still ferments.
    ("iMM904", "BIOMASS_SC5_notrace", 0.2879, 15.8155),
])
def test_the_ethanol_frontier_on_glucose(model_id, rxn, growth_max, flux_at_max):
    if not shelf.SHELF[model_id].fetched.local.is_file():
        pytest.skip(f"run pnpm geneos:fetch first: the {model_id} file is not here")
    r = geneos.frontier(model_id, "ethanol", "glucose", keep=False)
    pts = r.output["points"]
    assert len(pts) == shelf.FRONTIER_POINTS and r.output["growthReaction"] == rxn
    assert pts[0]["growth"] == pytest.approx(0, abs=1e-9) and pts[0]["flux"] == pytest.approx(20.0, rel=REL)
    assert pts[-1]["growth"] == pytest.approx(growth_max, rel=REL)
    assert pts[-1]["flux"] == pytest.approx(flux_at_max, rel=REL, abs=1e-6)


@pytest.mark.parametrize("model_id, mid_flux, mid_gg, end_flux, end_gg", [
    ("Yeast9", 19.0000, 0.4859, 18.0000, 0.4603),
    ("iMM904", 20.0000, 0.5114, 20.0000, 0.5114),
])
def test_the_glucose_xylose_mix(model_id, mid_flux, mid_gg, end_flux, end_gg):
    if not shelf.SHELF[model_id].fetched.local.is_file():
        pytest.skip(f"run pnpm geneos:fetch first: the {model_id} file is not here")
    r = geneos.mix(model_id, "ethanol", "glucose", "xylose", keep=False)
    pts = r.output["points"]
    assert (pts[5]["uptakeA"], pts[5]["uptakeB"]) == pytest.approx((5, 6))
    assert pts[5]["flux"] == pytest.approx(mid_flux, rel=REL) and pts[5]["gPerG"] == pytest.approx(mid_gg, rel=REL)
    assert pts[-1]["flux"] == pytest.approx(end_flux, rel=REL) and pts[-1]["gPerG"] == pytest.approx(end_gg, rel=REL)
