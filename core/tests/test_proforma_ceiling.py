"""A scenario's yield read against the geneOS ceiling (OF-BLD-019 §5.2, D11),
with no simulator and no flux balance analysis.

Every ceiling here is a STAND-IN artifact written by standins.standin_ceiling
into a scratch store, at a value chosen in the test beside the stand-in
records' yields; every record and assumption is a FIXTURE. None is a
measurement and no number here is a result. The binding, the fits and the
runs go through the real code over the closed-form STAND-IN evaluator
(standins.py). The strain catalogue left with the seed (alpha 2.0, ADR-010),
so the two strains the stand-in records and geneOS's yeast models name are
catalogued here (`catalogue`).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, fermos, geneos_models, intake, proforma
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.models import FermosPoint, FermosSeries, InputAssumption, ProformaRunRequest

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
HELD = "sc-held-1"  # a scenario the service holds by its id, as the `held` fixture holds it
# standins._standin_yeast_records' ethanol yields, in g g-1: 0.4, 0.45, 0.48.
LOWEST, MEDIAN, HIGHEST = 0.4, 0.45, 0.48
# Stand-in ceilings, chosen here around those yields.
OVER_ALL, BETWEEN, UNDER_ALL = 0.5, 0.46, 0.3


def assume(key, value, low=None, high=None):
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=BY, at="2026-10-20", note="a STAND-IN for a test")


ASSUMED = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]


@pytest.fixture(autouse=True)
def catalogue(monkeypatch):
    """The strains these tests name, by their labels, as the strain catalogue
    would give them."""
    labels = {"s-cerevisiae-cenpk113-7d": "Saccharomyces cerevisiae CEN.PK113-7D",
              "s-cerevisiae-s288c": "Saccharomyces cerevisiae S288C"}
    monkeypatch.setattr(proforma, "_strain_labels", lambda: (labels, {}))
    return labels


@pytest.fixture()
def held(monkeypatch):
    """One scenario the service holds by its id, on the ethanol flowsheet."""
    row = {"id": HELD, "name": "A held test scenario", "kind": "biosteam", "modelId": ETHANOL}
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [row])
    return row


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def pool(monkeypatch, store):
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, pool):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)
    return TestClient(api.app, base_url="http://127.0.0.1")


def ceiling(g, model="Yeast9", product="ethanol", substrate="glucose", at=standins.AT, version="STAND-IN ceiling 1"):
    return standins.standin_ceiling(model, product, substrate, g, at=at, version=version)


def check(pool, scenario=MADE_HERE, flowsheet=ETHANOL, **kw):
    return proforma.ceiling_check(scenario, flowsheet, pool=pool, **kw)


def row(c, model="Yeast9"):
    return next(r for r in c.rows if r.modelId == model)


# ── the yield beside the ceiling ────────────────────────────────────────


def test_a_yield_under_the_ceiling_is_within_and_not_flagged(pool):
    art = ceiling(OVER_ALL)
    c = check(pool)
    assert c.product == "ethanol" and c.substrate == "glucose" and c.flowsheet == ETHANOL
    assert c.yieldBinding == "records" and c.yieldRecords == 3
    assert (c.yieldLow, c.yieldValue, c.yieldHigh) == pytest.approx((LOWEST, MEDIAN, HIGHEST))
    r = row(c)
    assert r.artifactId == art.id and r.ceilingGPerG == pytest.approx(OVER_ALL)
    assert r.flag == "within" and not c.flagged and r.recordsAbove == []
    assert (r.yieldLowGPerG, r.yieldGPerG, r.yieldHighGPerG) == pytest.approx((LOWEST, MEDIAN, HIGHEST))
    # Mol per mol at the ceiling's own conventions: its molPerMol over its gPerG.
    assert r.yieldMolPerMol == pytest.approx(MEDIAN * r.ceilingMolPerMol / r.ceilingGPerG)
    assert r.ceilingMolPerMol == pytest.approx(OVER_ALL * geneos_models.SUBSTRATES["glucose"]["molarMass"]
                                               / geneos_models.PRODUCTS["ethanol"]["molarMass"])
    assert any("180.156 g mol-1" in w for w in r.conventions)
    assert c.empty is None and proforma.CEILING_KEPT in c.notes


def test_a_yield_above_the_ceiling_is_flagged_and_never_clamped(pool):
    before = proforma.bind_flowsheet(ETHANOL, pool=pool)
    run_before = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED), pool=pool)
    ceiling(UNDER_ALL)
    c = check(pool)
    r = row(c)
    assert r.flag == "above" and c.flagged
    # Never clamped: the yield is the binding's own median and range.
    assert (r.yieldLowGPerG, r.yieldGPerG, r.yieldHighGPerG) == pytest.approx((LOWEST, MEDIAN, HIGHEST))
    assert sorted(r.recordsAbove) == sorted(next(i for i in before.inputs if i.key == "yield").recordIds)
    assert "above this ceiling" in r.words and "reviewer should check the basis of each record" in r.words
    assert "not clamped" in r.words
    # The binding and the run are unchanged by a ceiling on file.
    after = proforma.bind_flowsheet(ETHANOL, pool=pool)
    assert after.model_dump() == before.model_dump()
    run_after = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED), pool=pool)
    assert run_after.artifactId == run_before.artifactId
    assert not any(i.name == "yield cap" for i in artifacts.get(run_after.artifactId).inputs)
    # And the check kept nothing: the store holds the ceiling and the run alone.
    assert sorted(a.tool for a in artifacts.all_artifacts()) == ["geneos.ceiling", "proforma.run"]


def test_a_high_end_above_the_ceiling_flags_the_records_above_it_alone(pool):
    ceiling(BETWEEN)
    r = row(check(pool))
    assert r.flag == "above" and r.recordsAbove == ["standin-ethanol_yield_substrate-2"]
    assert "under this ceiling, but its high end is above it" in r.words


def test_no_ceiling_on_file_says_so_and_names_where_one_is_computed(pool):
    c = check(pool)
    assert c.rows == [] and not c.flagged
    assert c.models == ["iMM904", "Yeast9"]
    assert "No geneOS ceiling for ethanol on glucose is on file for iMM904, Yeast9" in c.empty
    assert "geneOS → Model" in c.empty and "One is computed in geneOS → Model: choose ethanol, glucose" in c.empty
    assert c.computeAt == "/geneos/model?product=ethanol&substrate=glucose&model=iMM904"


def test_a_ceiling_on_another_sugar_is_left_aside(pool):
    ceiling(UNDER_ALL, substrate="xylose")
    c = check(pool)
    assert c.rows == [] and c.otherSugars == ["xylose"] and c.empty
    ceiling(OVER_ALL)
    c = check(pool)
    assert [x.substrate for x in c.rows] == ["glucose"] and row(c).flag == "within"


def test_the_newest_of_two_ceilings_is_used(pool):
    old = ceiling(UNDER_ALL, at="2026-10-01T09:00:00Z", version="STAND-IN ceiling 1")
    new = ceiling(OVER_ALL, at="2026-10-02T09:00:00Z", version="STAND-IN ceiling 2")
    r = row(check(pool))
    assert r.artifactId == new.id != old.id and r.older == 1
    assert r.ceilingGPerG == pytest.approx(OVER_ALL) and r.flag == "within"


def test_each_model_of_the_organism_has_its_own_row(pool):
    ceiling(UNDER_ALL, model="iMM904")
    ceiling(OVER_ALL, model="Yeast9")
    c = check(pool)
    assert {r.modelId: r.flag for r in c.rows} == {"iMM904": "above", "Yeast9": "within"}
    assert c.flagged


# ── how the organism maps to a model ───────────────────────────────────


def test_records_of_another_strain_map_to_the_species_models_and_say_so(pool):
    ceiling(OVER_ALL)
    c = check(pool)
    assert c.strains == ["s-cerevisiae-cenpk113-7d"] and c.species == ["saccharomyces cerevisiae"]
    r = row(c)
    assert r.match == "species" and r.host == "s-cerevisiae-s288c"
    assert "another strain's network bounds it" in r.matchWords


def test_the_organism_line_counts_the_records_that_name_a_strain_and_those_that_name_none(pool):
    """OF-BLD-019 §5.R, finding 4: a few yield records that name a strain
    once spoke for every record the yield binds. The line counts both kinds,
    and the species rows say how many records they cover."""
    ceiling(OVER_ALL)
    unnamed = dict(pool.records_by_id["standin-ethanol_yield_substrate-1"], id="standin-ethanol_yield_substrate-3",
                   value=0.44, strainId=None, organismText="ST9681, a STAND-IN clone name")
    rs = [*pool.records, unnamed]
    c = check(SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}))
    assert c.yieldRecords == 4 and c.strains == ["s-cerevisiae-cenpk113-7d"] and c.species == ["saccharomyces cerevisiae"]
    w = c.organismWords
    assert "3 of the 4 records its yield binds name Saccharomyces cerevisiae CEN.PK113-7D" in w, w
    assert "1 names no catalogued strain and names no organism the tree can read" in w, w
    assert not w.startswith("the strain of the records its yield binds"), w
    r = row(c)
    assert r.match == "species" and "3 of the 4 records the yield binds are read as of it" in r.matchWords, r.matchWords
    # Every record of the strain: said as all of them.
    assert "all 3 records its yield binds name Saccharomyces cerevisiae CEN.PK113-7D" in check(pool).organismWords


def test_a_host_filter_on_the_models_strain_maps_by_strain(pool):
    ceiling(OVER_ALL)
    c = check(pool, host="s-cerevisiae-s288c")
    assert c.strains == ["s-cerevisiae-s288c"] and row(c).match == "strain"
    # No stand-in record is of S288C, so the yield waits and nothing is read against the ceiling.
    assert c.yieldBinding == "waiting" and row(c).flag == "no-yield" and not c.flagged


def test_a_yield_a_person_assumed_is_read_against_the_ceiling_with_its_range(pool):
    ceiling(BETWEEN)
    c = check(pool, host="s-cerevisiae-s288c", assumptions=[assume("yield", 0.42, 0.4, 0.47)])
    r = row(c)
    assert c.yieldBinding == "assumption" and c.yieldSource.by == BY
    assert r.flag == "above" and r.yieldHighGPerG == pytest.approx(0.47) and r.recordsAbove == []
    assert "what the assumption rests on" in r.words


def test_a_fermos_fit_feeds_the_yield_the_check_reads(pool):
    import numpy as np

    t = np.linspace(0, 30, 16)
    x, i = fermos.logistic(np.asarray(t, float), 0.1, 0.35, 8.0)
    rng = np.random.default_rng(3)

    def series(role, label, v):
        return FermosSeries(measureId=f"m-{label.lower()}", label=label, unit="g L-1", role=role,
                            points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{n}", confirmed=True)
                                    for n, (a, b) in enumerate(zip(t, v))])

    fit = fermos.fit("dep-ethanol", [series("biomass", "Dry cell weight", x + rng.normal(0, 0.12, len(t))),
                                     series("product", "Ethanol", 0.05 + 0.4 * (x - 0.1) + 0.02 * i + rng.normal(0, 0.08, len(t))),
                                     series("substrate", "Glucose", 60 - 4.5 * (x - 0.1) - 0.05 * i + rng.normal(0, 0.6, len(t)))])
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=200.0)
    ceiling(OVER_ALL)
    # A yield a fit feeds binds no record, so the host names the organism.
    c = check(pool, fits={"yield": fc.artifactId}, host="s-cerevisiae-s288c")
    assert c.yieldBinding == "artifact" and c.yieldSource.id == fc.artifactId and c.yieldRecords == 0
    # The yield the fit feeds: its Yp/s at the hour its median sugar runs out (§5.R).
    fed = next(f for f in proforma.fit_info(artifacts.get(fc.artifactId), ETHANOL).feeds if f.key == "yield")
    assert row(c).yieldGPerG == pytest.approx(fed.value)


def test_it_is_refused_in_words_as_the_binding_is(pool, held):
    with pytest.raises(proforma.ScenarioRefused, match="reference biorefinery"):
        check(pool, scenario=MADE_HERE, flowsheet="corn_drygrind")
    with pytest.raises(proforma.ScenarioRefused, match="no held scenario"):
        check(pool, scenario=MADE_HERE, flowsheet=None)
    with pytest.raises(proforma.ScenarioRefused, match="runs ethanol_glucose_v0, not custom_train_v1"):
        check(pool, scenario=HELD, flowsheet="custom_train_v1")


# ── the endpoint ───────────────────────────────────────────────────────


def test_the_endpoint_answers_a_held_and_a_made_scenario_and_refuses_in_words(client, held):
    ceiling(BETWEEN)
    got = client.get("/api/proforma/ceiling-check", params={"scenarioId": HELD})
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["scenarioId"] == HELD and body["flagged"] is True
    assert body["rows"][0]["recordsAbove"] == ["standin-ethanol_yield_substrate-2"]
    made = client.get("/api/proforma/ceiling-check", params={"scenarioId": MADE_HERE, "flowsheet": ETHANOL})
    assert made.status_code == 200 and made.json()["scenarioId"] == MADE_HERE
    host = client.get("/api/proforma/ceiling-check", params={
        "scenarioId": HELD, "host": "s-cerevisiae-s288c",
        "assumptions": f"[{assume('yield', 0.42, 0.4, 0.47).model_dump_json()}]"})
    assert host.status_code == 200, host.text
    assert host.json()["yieldBinding"] == "assumption" and host.json()["rows"][0]["match"] == "strain"
    for params, said in (({"scenarioId": HELD, "fits": "[1]"}, "fits is a JSON object"),
                         ({"scenarioId": HELD, "assumptions": "{}"}, "assumptions is a JSON list"),
                         ({"scenarioId": MADE_HERE, "flowsheet": "cornstover_benchmark"}, "reference biorefinery"),
                         ({"scenarioId": HELD, "fits": '{"yield": "0000000000000000"}'}, "no kept artifact")):
        r = client.get("/api/proforma/ceiling-check", params=params)
        assert r.status_code == 422 and said in r.json()["detail"], (params, r.text)
