"""geneOS's worker and shelf (OF-BLD-014 §6.2). The toy network is built in the
worker and worked by hand here; the published models' values are §6.3's."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from openferment_core import geneos, geneos_models as shelf, intake
from openferment_core.workers import SimWorker, WorkerError
from openferment_core.workers import geneos_worker as gw

PACKAGE = Path(__file__).resolve().parents[1] / "openferment_core"


def test_the_toy_ceiling_is_the_one_worked_by_hand():
    # Glucose at 10 splits into 20 of the intermediate, each of which can
    # become one PHB unit: 20, so 2 mol per mol and 2 × 86.09 / 180.156 g per g.
    out = gw.ceiling(gw.build_toy(), "toy", "phb", "glucose")
    assert out["status"] == "optimal"
    assert out["flux"] == pytest.approx(20.0)
    assert out["molPerMol"] == pytest.approx(2.0)
    assert out["gPerG"] == pytest.approx(2 * 86.09 / 180.156)


def test_the_toy_frontier_trades_growth_for_product_on_a_straight_line():
    out = gw.frontier(gw.build_toy(), "toy", "phb", "glucose")
    pts = out["points"]
    assert len(pts) == shelf.FRONTIER_POINTS and out["growthReaction"] == "GROWTH"
    assert pts[0]["growth"] == pytest.approx(0) and pts[0]["flux"] == pytest.approx(20)
    assert pts[-1]["growth"] == pytest.approx(20) and pts[-1]["flux"] == pytest.approx(0)
    for p in pts:
        assert p["growth"] + p["flux"] == pytest.approx(20), "every unit of intermediate goes one way or the other"


def test_a_sugar_the_network_cannot_take_up_is_a_finding_with_no_number():
    out = gw.ceiling(gw.build_toy(), "toy", "phb", "xylose")
    assert out == {"finding": "this reconstruction has no uptake reaction for xylose", "modelId": "toy", "substrate": "xylose"}


def test_an_unbalanced_add_on_is_refused_whole():
    m = gw.build_toy()
    for mid in ("accoa_c", "coa_c", "nadph_c", "nadp_c", "h_c"):
        m.add_metabolites([gw.Metabolite(mid, formula="H", compartment="c")])
    bad = {
        "id": "broken",
        "metabolites": [{"id": "aacoa_c", "formula": "C25H36N7O18P3S", "charge": -4, "name": "Acetoacetyl-CoA"}],
        "reactions": [{"id": "BROKEN", "equation": "accoa_c --> aacoa_c", "lowerBound": 0.0}],
    }
    before = len(m.reactions)
    with pytest.raises(gw.Refused, match="does not balance"):
        gw.apply_addon(m, bad)
    assert len(m.reactions) == before


def test_the_phacab_add_on_balances_on_the_core_model():
    m = gw.load_model("textbook")
    added = gw.apply_addon(m, shelf.PHACAB)
    assert added == ["ACACT1r", "PHAB", "PHAC"], "the core model lacks the thiolase and gains it"


def test_a_round_trip_through_the_worker():
    w = SimWorker("openferment_core.workers.geneos_worker", timeout_s=120)
    try:
        assert w.ping()
        d = w.call("describe", {"modelId": "toy"})
        assert (d["reactions"], d["metabolites"], d["growthReaction"]) == (4, 3, "GROWTH")
        assert d["substrates"] == {"glucose": True, "fructose": False, "xylose": False}
        c = w.call("ceiling", {"modelId": "toy", "product": "phb", "substrate": "glucose"})
        assert c["flux"] == pytest.approx(20.0)
        with pytest.raises(WorkerError, match="no model nothing"):
            w.call("describe", {"modelId": "nothing"})
    finally:
        w.close()


def test_cobra_is_imported_in_the_geneos_worker_alone():
    importers = sorted(
        str(p.relative_to(PACKAGE))
        for p in PACKAGE.rglob("*.py")
        if re.search(r"^\s*(import cobra|from cobra)", p.read_text(encoding="utf-8"), re.M)
    )
    assert importers == ["workers/geneos_worker.py"]


def test_a_fetched_model_that_is_not_here_says_how_to_fetch_it(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    with pytest.raises(geneos.GeneosUnavailable, match="pnpm geneos:fetch"):
        geneos.model_args("RehMBEL1391")
    assert geneos.model_args("iJO1366") == {"modelId": "iJO1366"}


def test_a_file_whose_hash_does_not_match_is_set_aside(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    model = shelf.SHELF["RehMBEL1391"]
    calls = []

    def fake_git(cmd, check):
        calls.append(cmd[:3])
        if "checkout" in cmd:
            model.fetched.local.parent.mkdir(parents=True, exist_ok=True)
            model.fetched.local.write_text("not the published file", encoding="utf-8")
        else:
            (Path(cmd[-1]) / ".git").mkdir(parents=True)

    with pytest.raises(geneos.GeneosUnavailable, match="stop condition"):
        geneos.fetch(model, run=fake_git)
    assert not model.fetched.local.exists()
    assert model.fetched.local.with_suffix(".xml.mismatch").exists()
    assert calls[0][:2] == ["git", "clone"]


# ── §6.3: the ceiling, the frontier and the sugar mix ──────────────────
#
# Appendix 2's regression constants, belonging in test files alone. Tolerance
# 0.1 % relative.

REL = 1e-3


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "model, substrate, flux, mol, gg",
    [
        ("e_coli_core", "glucose", 10.0000, 1.0000, 0.4779),
        ("iJO1366", "glucose", 12.4122, 1.2412, 0.5931),
        ("iJO1366", "xylose", 10.2383, 1.0238, 0.5871),
    ],
)
def test_appendix_2_ceilings(model, substrate, flux, mol, gg):
    r = geneos.ceiling(model, "phb", substrate, keep=False)
    assert r.finding is None
    assert r.output["flux"] == pytest.approx(flux, rel=REL)
    assert r.output["molPerMol"] == pytest.approx(mol, rel=REL)
    assert r.evidence.value == pytest.approx(gg, rel=REL)
    assert r.output["status"] == "optimal" and r.output["solver"] == "glpk_interface"
    assert r.evidence.provenance == "computed" and r.evidence.figure == "ceiling"


def test_appendix_2_mix_midpoint_and_xylose_end():
    r = geneos.mix("iJO1366", "phb", "glucose", "xylose", keep=False)
    pts = r.output["points"]
    assert len(pts) == shelf.MIX_POINTS
    mid = pts[5]
    assert (mid["uptakeA"], mid["uptakeB"]) == pytest.approx((5, 6))
    assert mid["flux"] == pytest.approx(12.3600, rel=REL) and mid["gPerG"] == pytest.approx(0.5906, rel=REL)
    assert pts[-1]["uptakeB"] == pytest.approx(12) and pts[-1]["flux"] == pytest.approx(12.3078, rel=REL)
    assert pts[-1]["gPerG"] == pytest.approx(0.5881, rel=REL)


@pytest.mark.parametrize("model, growth_max, growth_rxn", [
    ("e_coli_core", 0.8739, "Biomass_Ecoli_core"),
    ("iJO1366", 0.9824, "BIOMASS_Ec_iJO1366_core_53p95M"),
])
def test_appendix_2_frontier_ends(model, growth_max, growth_rxn):
    r = geneos.frontier(model, "phb", "glucose", keep=False)
    pts = r.output["points"]
    assert len(pts) == shelf.FRONTIER_POINTS and r.output["growthReaction"] == growth_rxn
    assert pts[-1]["growth"] == pytest.approx(growth_max, rel=REL) and pts[-1]["flux"] == pytest.approx(0, abs=1e-6)
    ceiling = geneos.ceiling(model, "phb", "glucose", keep=False).output["flux"]
    assert pts[0]["growth"] == pytest.approx(0, abs=1e-9) and pts[0]["flux"] == pytest.approx(ceiling, rel=REL)
    assert r.evidence.figure == "frontier"


def test_a_sugar_a_model_cannot_take_up_stores_no_number(store):
    r = geneos.ceiling("e_coli_core", "phb", "xylose")
    assert r.finding == "this reconstruction has no uptake reaction for xylose"
    assert r.evidence is None and r.artifactId is None and r.output == {}
    assert not (store / "artifacts").exists() or not list((store / "artifacts").glob("*.json"))


def test_a_ceiling_is_kept_with_its_basis_and_replays(store):
    from openferment_core import artifacts

    r = geneos.ceiling("e_coli_core", "phb", "glucose")
    art = artifacts.get(r.artifactId)
    kinds = {i.name: (i.source.kind, i.source.id) for i in art.inputs}
    assert kinds["model"] == ("model", "e_coli_core")
    assert kinds["add-on"] == ("model", "RehMBEL1391")
    assert kinds["uptake"][0] == "convention" and kinds["substrate"][0] == "convention"
    assert next(i for i in art.inputs if i.name == "uptake").value == shelf.UPTAKE
    assert art.provenance == "computed"
    again = geneos.ceiling("e_coli_core", "phb", "glucose")
    assert again.artifactId == r.artifactId
    assert artifacts.replay(r.artifactId).identical


def test_the_endpoints(store):
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    shelf_ids = [m["id"] for m in c.get("/api/geneos/models").json()]
    assert shelf_ids == ["e_coli_core", "iJO1366", "RehMBEL1391"]
    unfetched = next(m for m in c.get("/api/geneos/models").json() if m["id"] == "RehMBEL1391")
    assert "pnpm geneos:fetch" in unfetched["unavailable"]
    ok = c.post("/api/geneos/ceiling", json={"modelId": "e_coli_core", "substrate": "glucose"}).json()
    assert ok["evidence"]["value"] == pytest.approx(0.4779, rel=REL)
    finding = c.post("/api/geneos/ceiling", json={"modelId": "e_coli_core", "substrate": "xylose"}).json()
    assert finding["finding"] and finding["evidence"] is None
    assert c.post("/api/geneos/ceiling", json={"modelId": "RehMBEL1391", "substrate": "fructose"}).status_code == 409
    assert c.post("/api/geneos/ceiling", json={"modelId": "nothing", "substrate": "glucose"}).status_code == 409
    guarded = c.post("/api/geneos/mix", json={"modelId": "iJO1366", "a": "glucose", "b": "xylose"},
                     headers={"Origin": "https://evil.example"})
    assert guarded.status_code == 403


def test_yield_ceiling_takes_ids_and_words_and_returns_one_evidence(store):
    from openferment_core import tools

    r = tools.run("yield_ceiling", {"modelId": "e_coli_core", "product": "phb", "substrate": "glucose"})
    assert r.error is None and len(r.evidence) == 1 and r.evidence[0].figure == "ceiling"
    assert r.summary["evidenceId"] == r.evidence[0].id and r.summary["model"]["scope"] == "central carbon"
    finding = tools.run("yield_ceiling", {"modelId": "e_coli_core", "product": "phb", "substrate": "xylose"})
    assert finding.evidence == [] and "no uptake reaction" in finding.summary["finding"]
    assert "a number was typed" in (tools.run("yield_ceiling", {"modelId": "e_coli_core", "product": "phb", "substrate": 10}).error or "")
