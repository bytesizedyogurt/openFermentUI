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
