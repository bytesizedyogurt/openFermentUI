"""geneOS's worker and shelf (OF-BLD-014 §6.2). The toy network is built in the
worker and worked by hand here. The published models on the shelf need their
fetched files, so a test that reaches the service runs on the toy (allowed
where the test asks for it) or on a STAND-IN network of its own."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from openferment_core import geneos, geneos_models as shelf, intake
from openferment_core.workers import SimWorker, WorkerError
from openferment_core.workers import geneos_worker as gw

PACKAGE = Path(__file__).resolve().parents[1] / "openferment_core"


# A product kept in the cell, defined by its metabolite: a STAND-IN on the
# toy's intermediate, with a placeholder molar mass. The shelf holds no such
# product since alpha 2.0 removed PHB (ADR-010); the demand rule stands.
STORED = {"name": "the stored intermediate (STAND-IN)", "label": "stored intermediate", "metabolite": "a_c",
          "formula": "C3H6O3", "molarMass": 100.0, "note": "a placeholder product kept in the cell, for the tests"}


@pytest.fixture()
def stored(monkeypatch):
    monkeypatch.setitem(shelf.PRODUCTS, "stored", STORED)
    return "stored"


def test_a_product_kept_in_the_cell_is_the_flux_through_a_demand_worked_by_hand(stored):
    # Glucose at 10 splits into 20 of the intermediate, each of which the
    # demand can take: 20, so 2 mol per mol and 2 × 100 / 180.156 g per g at
    # the stand-in's placeholder molar mass.
    m = gw.build_toy()
    out = gw.ceiling(m, "toy", stored, "glucose")
    assert out["status"] == "optimal"
    assert out["flux"] == pytest.approx(20.0)
    assert out["molPerMol"] == pytest.approx(2.0)
    assert out["gPerG"] == pytest.approx(2 * 100.0 / 180.156)
    assert "DM_a_c" in m.reactions, "the demand is added where the file lacks one"


def test_the_toy_frontier_trades_growth_for_product_on_a_straight_line():
    out = gw.frontier(gw.build_toy(), "toy", "ethanol", "glucose")
    pts = out["points"]
    assert len(pts) == shelf.FRONTIER_POINTS and out["growthReaction"] == "GROWTH"
    assert pts[0]["growth"] == pytest.approx(0) and pts[0]["flux"] == pytest.approx(20)
    assert pts[-1]["growth"] == pytest.approx(20) and pts[-1]["flux"] == pytest.approx(0)
    for p in pts:
        assert p["growth"] + p["flux"] == pytest.approx(20), "every unit of intermediate goes one way or the other"


def test_a_sugar_the_network_cannot_take_up_is_a_finding_with_no_number():
    out = gw.ceiling(gw.build_toy(), "toy", "ethanol", "xylose")
    assert out == {"finding": "this reconstruction has no uptake reaction for xylose", "modelId": "toy", "substrate": "xylose"}


def test_a_secreted_product_is_the_flux_out_through_its_exchange():
    # The same 20 of the intermediate can each leave as one ethanol through
    # EX_etoh_e: 2 mol per mol, and 2 × 46.069 / 180.156 g per g. No demand
    # is added for a product defined by its exchange.
    m = gw.build_toy()
    out = gw.ceiling(m, "toy", "ethanol", "glucose")
    assert out["status"] == "optimal" and out["exchange"] == "EX_glc__D_e"
    assert out["flux"] == pytest.approx(20.0) and out["molPerMol"] == pytest.approx(2.0)
    assert out["gPerG"] == pytest.approx(2 * 46.069 / 180.156)
    assert not [r.id for r in m.reactions if r.id.startswith("DM_")], "an exchange-defined product needs no demand"
    f = gw.frontier(gw.build_toy(), "toy", "ethanol", "glucose")["points"]
    assert f[0]["flux"] == pytest.approx(20) and f[-1]["flux"] == pytest.approx(0)


def test_a_product_the_network_has_no_route_to_is_a_finding_with_no_number(stored):
    m = gw.build_toy()
    m.remove_reactions([m.reactions.get_by_id("EX_etoh_e")])
    assert not gw.has_route(m, "toy", "ethanol") and gw.has_route(m, "toy", stored)
    want = {"finding": "this reconstruction has no route to ethanol", "modelId": "toy", "product": "ethanol"}
    assert gw.ceiling(m, "toy", "ethanol", "glucose") == want
    assert gw.frontier(m, "toy", "ethanol", "glucose") == want
    with pytest.raises(gw.Refused, match="no product nothing"):
        gw.ceiling(m, "toy", "nothing", "glucose")


# A model whose exchanges are numbered, as Yeast9's are: the toy with its
# glucose and ethanol exchanges renamed, mapped by a stand-in shelf entry.
MAPPED = shelf.ShelfModel(
    id="mapped", name="Toy network, numbered (STAND-IN)", host=None, scope="central carbon", bundled="toy",
    products=("ethanol",), exchanges={"glucose": "r_0001", "ethanol": "r_0002"},
    exchange_names={"glucose": "D-glucose exchange", "ethanol": "ethanol exchange"},
)


def numbered_toy() -> gw.Model:
    m = gw.build_toy()
    for old, new, name in (("EX_glc__D_e", "r_0001", "D-glucose exchange"), ("EX_etoh_e", "r_0002", "ethanol exchange")):
        r = m.reactions.get_by_id(old)
        r.id, r.name = new, name
    m.repair()
    return m


def test_an_exchange_the_shelf_maps_is_used_in_place_of_the_bigg_id(monkeypatch):
    assert shelf.exchange_id("Yeast9", "glucose") == "r_1714" and shelf.exchange_id("Yeast9", "ethanol") == "r_1761"
    assert shelf.exchange_id("iMM904", "glucose") == "EX_glc__D_e" and shelf.exchange_id("iMM904", "ethanol") == "EX_etoh_e"
    assert shelf.exchange_id("toy", "xylose") == "EX_xyl__D_e", "a model off the shelf reads BiGG's ids"
    for m in shelf.SHELF.values():
        assert set(m.exchange_names) <= set(m.exchanges), f"{m.id} checks a name for an exchange it does not map"
        assert set(m.exchanges) <= set(shelf.SUBSTRATES) | set(shelf.PRODUCTS)
        assert m.product in shelf.PRODUCTS and set(m.products) <= set(shelf.PRODUCTS)
    monkeypatch.setitem(shelf.SHELF, "mapped", MAPPED)
    m = numbered_toy()
    gw.check_exchange_names(m, MAPPED)
    out = gw.ceiling(m, "mapped", "ethanol", "glucose")
    assert out["exchange"] == "r_0001" and out["flux"] == pytest.approx(20.0)
    assert gw.describe(m, "mapped")["substrates"]["glucose"] and gw.describe(m, "mapped")["products"]["ethanol"]
    # Under BiGG's ids the same network has neither the feed nor the route.
    assert gw.ceiling(numbered_toy(), "toy", "ethanol", "glucose")["finding"] == "this reconstruction has no uptake reaction for glucose"


def test_a_file_whose_mapped_exchange_changed_its_name_is_refused():
    m = numbered_toy()
    m.reactions.get_by_id("r_0002").name = "ethanolamine exchange"
    with pytest.raises(gw.Refused, match="names r_0002 'ethanolamine exchange', not 'ethanol exchange'"):
        gw.check_exchange_names(m, MAPPED)
    m.remove_reactions([m.reactions.get_by_id("r_0001")])
    with pytest.raises(gw.Refused, match="has no reaction r_0001"):
        gw.check_exchange_names(m, MAPPED)


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


def test_a_round_trip_through_the_worker():
    w = SimWorker("openferment_core.workers.geneos_worker", timeout_s=120)
    try:
        assert w.ping()
        d = w.call("describe", {"modelId": "toy"})
        assert (d["reactions"], d["metabolites"], d["growthReaction"]) == (5, 3, "GROWTH")
        assert d["substrates"] == {"glucose": True, "fructose": False, "xylose": False}
        assert d["products"] == {"ethanol": True} and d["added"] == []
        e = w.call("ceiling", {"modelId": "toy", "product": "ethanol", "substrate": "glucose"})
        assert e["flux"] == pytest.approx(20.0) and e["gPerG"] == pytest.approx(2 * 46.069 / 180.156)
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
        geneos.model_args("Yeast9")
    # A model bundled with cobra is named by its id alone (the stand-in entry above).
    monkeypatch.setitem(shelf.SHELF, "mapped", MAPPED)
    assert geneos.model_args("mapped") == {"modelId": "mapped"}


def test_a_file_whose_hash_does_not_match_is_set_aside(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    model = shelf.SHELF["Yeast9"]
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


def url_model(body: bytes) -> shelf.ShelfModel:
    import hashlib

    f = shelf.UrlFile(url="https://models.example/m.xml", revision="test", path="example/m.xml",
                      sha256=hashlib.sha256(body).hexdigest(), licence="test")
    return shelf.ShelfModel(id="m", name="a file at an address (STAND-IN)", host=None, scope="central carbon", fetched=f)


def test_a_file_at_an_address_is_downloaded_whole_and_checked(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    model = url_model(b"<sbml>the published file</sbml>")
    asked = []

    def get(url):
        asked.append(url)
        return b"<sbml>the published file</sbml>"

    def no_git(cmd, check):
        raise AssertionError("a file at an address is not fetched by git")

    assert geneos.fetch(model, run=no_git, get=get) == tmp_path / "models" / "example" / "m.xml"
    assert asked == ["https://models.example/m.xml"] and shelf.available(model) is None
    geneos.fetch(model, run=no_git, get=lambda url: pytest.fail("a present file that matches is not fetched again"))


def test_a_file_at_an_address_whose_hash_does_not_match_is_set_aside(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    model = url_model(b"<sbml>the published file</sbml>")
    with pytest.raises(geneos.GeneosUnavailable, match="m: the file at https://models.example/m.xml hashes to .* stop condition"):
        geneos.fetch(model, get=lambda url: b"<sbml>something else</sbml>")
    assert not model.fetched.local.exists() and model.fetched.local.with_suffix(".xml.mismatch").exists()
    assert "pnpm geneos:fetch" in shelf.available(model)

    def down(url):
        raise geneos.GeneosUnavailable(f"{url} could not be fetched: ConnectError")

    with pytest.raises(geneos.GeneosUnavailable, match="^m: https://models.example/m.xml could not be fetched"):
        geneos.fetch(model, get=down)


def test_fetch_reports_every_fetched_model_and_fails_when_one_does(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    tried = []

    def fake(model, **kw):
        tried.append(model.id)
        if model.id == "iMM904":
            raise geneos.GeneosUnavailable("iMM904: https://bigg.ucsd.edu/static/models/iMM904.xml could not be fetched")
        return model.fetched.local

    monkeypatch.setattr(geneos, "fetch", fake)
    assert geneos.main(["fetch"]) == 1
    assert tried == ["iMM904", "Yeast9"], "every fetched model is tried, one failing or not"
    out = capsys.readouterr()
    assert "✓ Yeast9 at 2d594ae1c4a2d550ccef120d96a58c7bbf586255" in out.out
    assert "✗ iMM904: https://bigg.ucsd.edu" in out.err


# ── §6.3: the ceiling, the frontier and the sugar mix ──────────────────
#
# Through the service, on the toy (allowed here) or on a STAND-IN network the
# test builds and runs in this process. The published models' values need
# their fetched files.


class InProcessWorker:
    """The worker's ops in this process, on a network the test builds: a
    STAND-IN for geneos.worker() where a test needs a network the worker
    process does not hold."""

    def __init__(self, build):
        self.build = build

    def call(self, op, args):
        m, mid = self.build(), str(args["modelId"])
        if op == "describe":
            return gw.describe(m, mid)
        if op == "ceiling":
            return gw.ceiling(m, mid, str(args["product"]), str(args["substrate"]))
        if op == "frontier":
            return gw.frontier(m, mid, str(args["product"]), str(args["substrate"]))
        return gw.mix(m, mid, str(args["product"]), str(args["a"]), str(args["b"]))


def two_sugar_toy() -> gw.Model:
    """The toy with a xylose feed beside its glucose: XSPLIT turns one xylose
    into one of the intermediate. A STAND-IN of the tests' own, so a sugar mix
    has two sugars the network takes up."""
    m = gw.build_toy()
    xyl = gw.Metabolite("xyl__D_e", formula="C5H10O5", compartment="e", name="xylose")
    ex = gw.Reaction("EX_xyl__D_e", lower_bound=0.0, upper_bound=1000.0)
    ex.add_metabolites({xyl: -1})
    split = gw.Reaction("XSPLIT", lower_bound=0.0, upper_bound=1000.0)
    split.add_metabolites({xyl: -1, m.metabolites.get_by_id("a_c"): 1})
    m.add_reactions([ex, split])
    return m


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_a_sugar_a_model_cannot_take_up_stores_no_number(store):
    r = geneos.ceiling("toy", "ethanol", "xylose", allow_toy=True)
    assert r.finding == "this reconstruction has no uptake reaction for xylose"
    assert r.evidence is None and r.artifactId is None and r.output == {}
    from openferment_core import artifacts

    assert artifacts.all_artifacts() == []


def test_a_ceiling_is_kept_with_its_basis_and_replays(store):
    from openferment_core import artifacts

    r = geneos.ceiling("toy", "ethanol", "glucose", allow_toy=True)
    art = artifacts.get(r.artifactId)
    kinds = {i.name: (i.source.kind, i.source.id) for i in art.inputs}
    # The toy is a stand-in: its model input is an assumption, so what is
    # computed on it is assumed, never computed evidence (§6.R).
    assert kinds["model"] == ("assumption", "toy") and art.provenance == "assumed"
    assert "add-on" not in kinds, "the toy carries its own route"
    assert kinds["uptake"][0] == "convention" and kinds["substrate"][0] == "convention"
    assert next(i for i in art.inputs if i.name == "uptake").value == shelf.UPTAKE
    again = geneos.ceiling("toy", "ethanol", "glucose", allow_toy=True)
    assert again.artifactId == r.artifactId
    assert artifacts.replay(r.artifactId).identical


def test_an_add_on_route_is_named_in_the_basis(monkeypatch):
    # A route the worker adds to a model that lacks one (ADDONS) is named in
    # the basis as the model it comes from. The shelf holds none since alpha
    # 2.0 removed the phaCAB route (ADR-010): a STAND-IN entry carries one.
    addon = {"id": "test-route", "source": "model: a published model (STAND-IN)", "metabolites": [],
             "reactions": [{"id": "TESTR", "equation": "a_c --> etoh_e", "lowerBound": 0.0}]}
    monkeypatch.setitem(shelf.ADDONS, "test-route", addon)
    monkeypatch.setitem(shelf.SHELF, "carrier", shelf.ShelfModel(
        id="carrier", name="A model carrying an add-on (STAND-IN)", host=None, scope="central carbon",
        bundled="toy", addon="test-route", products=("ethanol",)))
    route = {i.name: i for i in geneos._inputs("carrier", "ethanol", ["glucose"])}["add-on"]
    assert (route.value, route.source.kind, route.source.id) == ("test-route", "model", "a published model (STAND-IN)")
    assert route.source.note.startswith("TESTR; the route a published model (STAND-IN) carries")


def test_the_endpoints(store):
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    listed = c.get("/api/geneos/models").json()
    assert [m["id"] for m in listed] == ["iMM904", "Yeast9"]
    assert {m["id"]: (m["product"], m["products"]) for m in listed} == {
        "iMM904": ("ethanol", ["ethanol"]), "Yeast9": ("ethanol", ["ethanol"]),
    }
    # The store fixture's data folder holds no model file.
    assert all("pnpm geneos:fetch" in m["unavailable"] for m in listed)
    # Both are reconstructions of S288C, so they sit on its strain page.
    yeast = {m["id"]: m for m in listed if m["host"] == "s-cerevisiae-s288c"}
    assert set(yeast) == {"iMM904", "Yeast9"} and yeast["iMM904"]["source"].startswith("https://bigg.ucsd.edu/")
    assert yeast["Yeast9"]["source"] == "https://github.com/SysBioChalmers/yeast-GEM at v9.1.1 (2d594ae1c4a2d550ccef120d96a58c7bbf586255)"
    assert c.post("/api/geneos/ceiling", json={"modelId": "Yeast9", "product": "ethanol", "substrate": "glucose"}).status_code == 409
    # The toy is a stand-in for the tests: refused here like any model off the shelf (§6.R).
    assert c.post("/api/geneos/ceiling", json={"modelId": "toy", "substrate": "glucose"}).status_code == 409
    assert c.post("/api/geneos/ceiling", json={"modelId": "nothing", "substrate": "glucose"}).status_code == 409
    guarded = c.post("/api/geneos/mix", json={"modelId": "Yeast9", "a": "glucose", "b": "xylose"},
                     headers={"Origin": "https://evil.example"})
    assert guarded.status_code == 403


def test_yield_ceiling_takes_ids_and_words_and_returns_one_evidence(store, monkeypatch):
    from openferment_core import tools

    # The tool refuses the toy like any model off the shelf; here it is let
    # through, so the tool's answer is read without a fetched file.
    real = geneos.ceiling
    monkeypatch.setattr(geneos, "ceiling", lambda m, p, s, **k: real(m, p, s, **{**k, "allow_toy": True}))
    r = tools.run("yield_ceiling", {"modelId": "toy", "product": "ethanol", "substrate": "glucose"})
    assert r.error is None and len(r.evidence) == 1 and r.evidence[0].figure == "ceiling"
    assert r.summary["evidenceId"] == r.evidence[0].id and r.summary["model"] == {"id": "toy"}
    assert r.summary["what"].startswith("most ethanol from glucose") and r.summary["molPerMol"] == pytest.approx(2.0)
    assert r.summary["provenance"] == "assumed", "a stand-in network's value is modeled"
    product = next(i for i in r.evidence[0].basis.inputs if i.name == "product")
    assert product.value == "ethanol" and product.source.note.startswith("secreted through EX_etoh_e; ethanol C2H6O")
    finding = tools.run("yield_ceiling", {"modelId": "toy", "product": "ethanol", "substrate": "xylose"})
    assert finding.evidence == [] and "no uptake reaction" in finding.summary["finding"]
    assert "a number was typed" in (tools.run("yield_ceiling", {"modelId": "toy", "product": "ethanol", "substrate": 10}).error or "")


def test_yield_ceiling_names_each_models_products_and_refuses_in_words(store):
    from openferment_core import tools

    schema = tools.REGISTRY["yield_ceiling"].info().inputSchema["properties"]
    assert "Yeast9 (ethanol)" in schema["modelId"]["description"] and "iMM904 (ethanol)" in schema["modelId"]["description"]
    assert schema["product"]["description"] == "The product: ethanol."
    # The store fixture's data folder holds no model files.
    refused = tools.run("yield_ceiling", {"modelId": "Yeast9", "product": "ethanol", "substrate": "glucose"})
    assert "Yeast9's file is not on this machine: run pnpm geneos:fetch" in (refused.error or "")
    nothing = tools.run("yield_ceiling", {"modelId": "Yeast9", "product": "nothing", "substrate": "glucose"})
    assert "no product nothing" in (nothing.error or "")


def test_each_request_solves_a_fresh_copy_of_the_model_read_once():
    # OF-BLD-014 §10.2: the nightly replay found a warm model's answer drifting
    # in the last digits with the solve before it, so a kept ceiling did not
    # replay identically. Each request now solves a fresh copy of the model
    # the worker read once.
    first, mid = gw._model({"modelId": "toy"})
    second, _ = gw._model({"modelId": "toy"})
    loaded = gw.load("toy")
    assert mid == "toy" and first is not second and first is not loaded and second is not loaded
    ask = {"modelId": "toy", "product": "ethanol", "substrate": "glucose"}
    before = gw._op_ceiling(ask)
    gw._op_frontier(ask)
    assert gw._op_ceiling(ask) == before
