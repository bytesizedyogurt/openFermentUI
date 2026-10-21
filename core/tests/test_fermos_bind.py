"""A simulation's parameters from a fit, the records, a kept simulation or a
named person, in that order, each named (OF-BLD-020 §3.2, D6).

Every record here is a STAND-IN written in the test, on thread Q paper ids;
every series is SYNTHETIC, made from parameters chosen here. None is a
measurement and no number here is a result. Proforma's run ids below were
measured on this file's stand-in pool at dc78045, before binding.py took the
aggregate gate and its statistic out of proforma.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, binding, demo, evidence_pool, fermos, intake, kinetics, proforma, units
from openferment_core.models import InputAssumption, Override, SimulationRequest

BY = "openFerment test fixture"
BATCH = "batch_v1"
SCOPE = f"fermos:family:{BATCH}"
CENPK = "s-cerevisiae-cenpk113-7d"
S288C = "s-cerevisiae-s288c"
YEAST = "Saccharomyces cerevisiae"


def rec(rid, field, value, unit="g L-1", *, paper="Q7", carbon="glucose", strain=None, organism=YEAST, **kw):
    return {"id": rid, "paperId": paper, "field": field, "value": value, "unit": unit, "carbonSource": carbon,
            "strainId": strain, "organismText": organism, "provenance": "unverified", "status": "unverified",
            "primary": True, **kw}


def pool_of(*records):
    rs = list(records)
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}, hidden={})


# A batch_v1 pool: μmax and Ks on glucose, the yields, the medium; no Pmax.
STANDIN = [
    rec("mu1", "growth_rate_mu", 0.30, "h-1"), rec("mu2", "growth_rate_mu", 0.40, "h-1"),
    rec("mu3", "growth_rate_mu", 0.50, "h-1"),
    rec("ks1", "monod_ks", 0.10), rec("ks2", "monod_ks", 0.30),
    rec("yx1", "biomass_yield_substrate", 0.12, "g g-1"),
    rec("yp1", "ethanol_yield_substrate", 0.44, "g g-1"), rec("yp2", "ethanol_yield_substrate", 0.46, "g g-1"),
    rec("s01", "medium_component_conc", 40.0), rec("s02", "medium_component_conc", 60.0),
]
# What a person types for what no record binds here.
TYPED = dict(alpha=2.0, p_max=90.0, x0=0.2, p0=0.0)


def typed(**values):
    return [Override(scope=SCOPE, key=k, value=v, by=BY, at="2026-10-21", note="a STAND-IN for a test")
            for k, v in values.items()]


def by_key(values):
    return {v.key: v for v in values}


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def bind(pool, *, strain=None, product="ethanol", sugar="glucose", overrides=(), fit=None, simulation=None,
         preset="until-sugar-runs-out"):
    values, waiting = fermos.bind_parameters(BATCH, strain, product, sugar, pool, list(overrides), fit, None,
                                             simulation=simulation, duration_preset=preset)
    return by_key(values), waiting


# ── the records ────────────────────────────────────────────────────────


def test_records_bind_mu_max_and_ks_and_pmax_waits_naming_its_field(store):
    v, waiting = bind(pool_of(*STANDIN))
    mu = v["mu_max"]
    assert mu.origin == "record" and mu.value == 0.40 and (mu.low, mu.high) == (0.30, 0.50)
    assert mu.recordIds == ["mu1", "mu2", "mu3"] and "3 records of growth_rate_mu on glucose" in mu.detail
    assert mu.detail.endswith("the median 0.4") and mu.identified is None
    ks = v["ks"]
    assert ks.origin == "record" and ks.value == pytest.approx(0.20) and (ks.low, ks.high) == (0.10, 0.30)
    # One record is held fixed, as Proforma holds it.
    assert v["yxs"].origin == "record" and v["yxs"].value == v["yxs"].low == v["yxs"].high == 0.12
    assert v["s0"].origin == "record" and v["s0"].value == 50.0
    assert v["p_max"].origin == "waiting" and "ethanol_max_conc" in v["p_max"].detail
    assert set(waiting) == {"alpha", "p_max", "x0", "p0"}
    # A run refuses naming every parameter that waits and the field that would bind it.
    with pytest.raises(fermos.SimulationRefused, match="batch_v1 cannot run yet") as e:
        fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                          overrides=typed(**{k: x for k, x in TYPED.items() if k != "p_max"})),
                        by_pool=pool_of(*STANDIN))
    assert "p_max (maximum product concentration)" in str(e.value) and "ethanol_max_conc" in str(e.value)
    assert "mu_max" not in str(e.value)


def test_the_proforma_gate_and_statistic_are_the_ones_records_bind_through(store):
    assert proforma._exclusion is binding.exclusion and proforma._in_program is binding.in_program
    v, _ = bind(pool_of(*STANDIN, rec("mu-est", "growth_rate_mu", 9.0, "h-1", provenance="industry-estimate"),
                        rec("mu-cites", "growth_rate_mu", 9.0, "h-1", primary=False),
                        rec("mu-rej", "growth_rate_mu", 9.0, "h-1", status="rejected"),
                        rec("mu-pha", "growth_rate_mu", 9.0, "h-1", paper="P6")))
    assert v["mu_max"].recordIds == ["mu1", "mu2", "mu3"], "the aggregate gate and the program's papers hold"
    assert "3 kept out by the aggregate gate" in v["mu_max"].detail
    for vals, want in (([1.0], (1.0, 1.0, 1.0, "fixed")), ([1.0, 3.0], (2.0, 1.0, 3.0, "uniform")),
                       ([2.0, 2.0, 2.0], (2.0, 2.0, 2.0, "fixed")), ([3.0, 1.0, 1.5], (1.5, 1.0, 3.0, "triangular"))):
        st = binding.statistic(vals)
        assert (st.value, st.low, st.high, st.sampling) == want
    assert binding.statistic([1.0]).flag == proforma.SINGLE and binding.statistic([1.0, 3.0]).flag is None


def _would_be(pool, typed_, sid="sc-yeast-1"):
    """sc-yeast-1's run id as proforma.run computes it, up to the simulator."""
    flowsheet = proforma.flowsheet_of(sid, None)
    inputs = proforma.bind_inputs(flowsheet, pool.records, None, typed_)
    fitted = proforma.apply_fits(inputs, proforma.fits_beside(None, typed_), flowsheet)
    b = proforma.basis_inputs(inputs, None, flowsheet, proforma.SAMPLES, scenario_id=sid, fitted=fitted)
    return artifacts.artifact_id(proforma.RUN, artifacts.registered(proforma.RUN).version_for(b), b, 0)


def test_proformas_artifact_ids_for_sc_yeast_1_are_unchanged_by_the_move(monkeypatch):
    # Measured before the move (scratchpad runid.py at dc78045) and after it,
    # on the stand-in pool demo.py's fixtures bind, and on one that takes
    # every branch of the statistic. The diagram input names whether dot is
    # on this host's path, so it is pinned as the fixtures pin it.
    monkeypatch.setattr(proforma, "drawn_here", lambda: False)

    def a(key, value, low=None, high=None):
        return InputAssumption(key=key, value=value, low=value if low is None else low,
                               high=value if high is None else high, by=BY, at="2026-10-20", note="a STAND-IN for a test")

    economics = [a("plant_scale", 100000.0), a("glucose_price", 0.4, 0.3, 0.5)]
    rs = demo._standin_yeast_records()
    assert _would_be(pool_of(*rs), economics) == "f78dc92272889efd"
    branches = [dict(r, value=1.5) if r["field"] == "ethanol_productivity" else r for r in rs
                if not (r["field"] == "ethanol_titre" and not r["id"].endswith("-0"))
                and not (r["field"] == "ethanol_yield_substrate" and r["id"].endswith("-2"))]
    assert _would_be(pool_of(*branches), economics) == "a4b9bc93bd0c8310"


# ── the strain, the organism and the sugar ─────────────────────────────


def test_the_strain_filter_and_every_strain_each_bind_what_they_should(store):
    pool = pool_of(
        rec("mu-cenpk", "growth_rate_mu", 0.30, "h-1", strain=CENPK),
        rec("mu-alias", "growth_rate_mu", 0.32, "h-1", organism="CEN.PK113-7D"),
        rec("mu-s288c", "growth_rate_mu", 0.40, "h-1", strain=S288C),
        rec("mu-none", "growth_rate_mu", 0.50, "h-1"),
        rec("mu-zymo", "growth_rate_mu", 0.90, "h-1", organism="Zymomonas mobilis ZM4"),
        rec("s0-s288c", "medium_component_conc", 20.0, strain=S288C),
    )
    one, _ = bind(pool, strain=CENPK)
    assert one["mu_max"].recordIds == ["mu-cenpk", "mu-alias"], "the strain and its aliases"
    assert "3 of another strain or of none" in one["mu_max"].detail
    assert "for Saccharomyces cerevisiae CEN.PK113-7D" in one["mu_max"].detail
    # The medium is the experimenter's: it binds whatever strain is chosen.
    assert one["s0"].recordIds == ["s0-s288c"]
    every, _ = bind(pool)
    assert every["mu_max"].recordIds == ["mu-cenpk", "mu-alias", "mu-s288c", "mu-none"]
    assert "1 of another organism" in every["mu_max"].detail
    # The basis says which choice bound the records.
    sim = fermos.simulate(SimulationRequest(family=BATCH, strain=CENPK, product="ethanol", sugar="glucose",
                                            overrides=typed(ks=0.2, yxs=0.12, yps=0.45, **TYPED)), by_pool=pool)
    named = {i.name: i for i in artifacts.get(sim.artifactId).inputs}
    assert named["records of"].value.startswith(f"{CENPK} by its aliases")
    every_sim = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                                  overrides=typed(ks=0.2, yxs=0.12, yps=0.45, **TYPED)),
                                by_pool=pool)
    named = {i.name: i for i in artifacts.get(every_sim.artifactId).inputs}
    assert named["records of"].value == "every strain of the Yeast ethanol program's organism, Saccharomyces cerevisiae"
    with pytest.raises(fermos.SimulationRefused, match="there is no catalogued strain"):
        bind(pool, strain="s-cerevisiae-nowhere")


def test_the_carbon_source_filter(store):
    pool = pool_of(
        rec("mu-glc", "growth_rate_mu", 0.30, "h-1"), rec("mu-none", "growth_rate_mu", 0.40, "h-1", carbon=None),
        rec("mu-xyl", "growth_rate_mu", 0.10, "h-1", carbon="xylose"),
        rec("pmax-xyl", "ethanol_max_conc", 80.0, carbon="xylose"),
        rec("ki-none", "substrate_inhibition_ki", 150.0, carbon=None),
        rec("ki-xyl", "substrate_inhibition_ki", 50.0, carbon="xylose"),
    )
    v, _ = bind(pool)
    assert v["mu_max"].recordIds == ["mu-glc"]
    assert "1 naming no carbon source" in v["mu_max"].detail and "1 naming another carbon source" in v["mu_max"].detail
    # Pmax is the product's, so any carbon source binds; Ki is a substrate's, so none or the sugar.
    assert v["p_max"].recordIds == ["pmax-xyl"]
    assert v["ki_substrate"].recordIds == ["ki-none"] and "1 naming another carbon source" in v["ki_substrate"].detail
    xylose, _ = bind(pool, sugar="xylose")
    assert xylose["mu_max"].recordIds == ["mu-xyl"] and xylose["ki_substrate"].recordIds == ["ki-none", "ki-xyl"]
    nosugar, waiting = bind(pool, sugar=None)
    assert nosugar["mu_max"].origin == "waiting" and "no sugar is named" in nosugar["mu_max"].detail
    assert nosugar["p_max"].recordIds == ["pmax-xyl"] and "mu_max" in waiting
    with pytest.raises(fermos.SimulationRefused, match="a sugar is named by its carbon-source id"):
        bind(pool, sugar="treacle")


def test_a_field_one_product_owns_binds_for_it_alone(store):
    pool = pool_of(rec("yp", "ethanol_yield_substrate", 0.45, "g g-1"), rec("pha", "pha_yield_substrate", 0.3, "g g-1"))
    assert bind(pool)[0]["yps"].recordIds == ["yp"]
    none, _ = bind(pool, product=None)
    assert none["yps"].origin == "waiting" and "ethanol's own field, and no product is named" in none["yps"].detail
    # phb binds its own field in ethanol's place; the record is on a yeast paper, so the program decides.
    phb, _ = bind(pool, product="phb")
    assert phb["yps"].origin == "waiting" and "pha_yield_substrate" in phb["yps"].detail
    assert phb["alpha"].origin == "waiting" and "the product is phb" in phb["alpha"].detail


def test_a_record_in_another_unit_is_converted_and_one_units_cannot_convert_is_counted_out(store):
    pool = pool_of(rec("mu-h", "growth_rate_mu", 0.30, "h-1"), rec("mu-d", "growth_rate_mu", 12.0, "d-1"),
                   rec("mu-min", "growth_rate_mu", 0.006, "min⁻¹"), rec("mu-bad", "growth_rate_mu", 0.3, "g/L"),
                   rec("ks-mg", "monod_ks", 200.0, "mg/L"))
    v, _ = bind(pool)
    mu = v["mu_max"]
    assert mu.recordIds == ["mu-h", "mu-d", "mu-min"] and (mu.low, mu.high) == pytest.approx((0.30, 0.50))
    assert mu.value == pytest.approx(0.36)
    assert "1 in a unit units.py does not convert (mu-bad: g/L" in mu.detail
    assert v["ks"].value == pytest.approx(0.2) and v["ks"].recordIds == ["ks-mg"]


def test_the_new_kinetics_fields_are_exported_with_their_units():
    for field, unit in (("maintenance_coefficient", "g g⁻¹ h⁻¹"), ("biomass_yield_oxygen", "g g⁻¹"),
                        ("specific_oxygen_uptake", "mmol g⁻¹ h⁻¹"), ("kla_measured", "h⁻¹")):
        f = units.field(field)
        assert f["family"] == "kinetics" and f["canonicalUnit"] == unit and f["range"][0] < f["range"][1], field
    assert units.convert(1.0, "s⁻¹", "h⁻¹") == pytest.approx(3600.0)
    assert units.convert(2.0, "mmol/g/h", "mmol g⁻¹ h⁻¹") == 2.0
    with pytest.raises(units.UnitError):
        units.convert(1.0, "mmol g⁻¹ h⁻¹", "g g⁻¹ h⁻¹")
    assert "molar mass" in (units.explain_refusal("mmol g⁻¹ h⁻¹", "g g⁻¹ h⁻¹") or "")


def test_a_record_of_a_new_field_binds_maintenance_and_makes_the_culture_aerobic(store):
    pool = pool_of(*STANDIN, rec("m1", "maintenance_coefficient", 0.02, "g g-1 h-1"),
                   rec("yo1", "biomass_yield_oxygen", 1.1, "g g-1"))
    v, _ = bind(pool)
    assert v["maintenance"].origin == "record" and v["maintenance"].value == 0.02
    assert v["yxo"].origin == "record" and v["yxo"].value == 1.1
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", overrides=typed(**TYPED)),
                        by_pool=pool)
    assert r.aerobic and r.our.peak > 0


# ── a person, and what the basis says ──────────────────────────────────


def test_an_override_replaces_a_record_and_the_basis_names_the_person(store):
    pool = pool_of(*STANDIN)
    v, _ = bind(pool, overrides=typed(mu_max=0.25))
    assert v["mu_max"].origin == "assumption" and v["mu_max"].overriddenBy == BY and not v["mu_max"].recordIds
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                          overrides=typed(mu_max=0.25, **TYPED)), by_pool=pool)
    art = artifacts.get(r.artifactId)
    named = {i.name: i for i in art.inputs}
    assert named["mu_max"].source.kind == "assumption" and named["mu_max"].source.by == BY
    assert not any(i.name == "mu_max record" for i in art.inputs), "the person's value stands in the records' place"
    assert {i.value for i in art.inputs if i.name == "ks record"} == {"ks1", "ks2"}
    assert all(i.source.kind == "record" for i in art.inputs if i.name.endswith(" record"))
    assert r.provenance == "demo", "a named person's value makes the simulation demo (D1)"
    p = by_key(r.parameters)
    assert p["mu_max"].origin == "assumption" and p["ks"].origin == "record" and p["ks"].recordIds == ["ks1", "ks2"]
    assert p["ks"].low == 0.10 and p["ks"].high == 0.30
    assert artifacts.replay(r.artifactId).identical


# ── a fit, and a kept simulation ───────────────────────────────────────

STANDIN_BATCH = dict(mu_max=0.40, ks=0.20, kd=0.0, yxs=0.15, alpha=2.0, beta=0.05, yps=0.45, maintenance=0.0,
                     p_max=None, n_inhibition=1.0, ki_substrate=None, yxo=None, mo=0.0)
TIMES = np.linspace(0.0, 12.0, 13)


def _series(role, t, v):
    from openferment_core.models import FermosPoint, FermosSeries

    return FermosSeries(measureId=f"m-{role}", label=role, unit="g L-1", role=role,
                        points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                for i, (a, b) in enumerate(zip(t, v))])


def _batch_fit(monkeypatch, roles=("biomass", "substrate", "product")) -> str:
    with monkeypatch.context() as m:
        m.setattr(kinetics, "RTOL", 1e-12)
        m.setattr(kinetics, "ATOL", 1e-14)
        tr = kinetics.FAMILIES[BATCH].simulate(STANDIN_BATCH, {"X": 0.2, "S": 50.0, "P": 0.0}, float(TIMES[-1]))
    Y = tr.sample(TIMES)
    state = {"biomass": "X", "substrate": "S", "product": "P"}
    out = fermos.fit("dep-bind", [_series(r, TIMES, Y[kinetics.IX[state[r]]]) for r in roles], family=BATCH)
    return out.kineticArtifactId


def test_yps_binds_from_a_fit_with_its_interval_and_identified_and_the_fit_comes_first(store, monkeypatch):
    fit_id = _batch_fit(monkeypatch)
    pool = pool_of(*STANDIN, rec("pmax1", "ethanol_max_conc", 90.0))
    v, waiting = bind(pool, fit=fit_id)
    yps = v["yps"]
    assert yps.origin == "fit" and yps.value == pytest.approx(0.45, rel=0.01) and yps.identified is True
    assert yps.low < yps.value < yps.high and yps.source.kind == "artifact" and yps.source.id == fit_id
    # The fit comes before the records it stands in place of.
    assert v["mu_max"].origin == "fit" and not v["mu_max"].recordIds
    assert v["x0"].origin == "fit" and v["p0"].origin == "fit" and v["s0"].origin == "fit"
    # What one batch's readings cannot pin binds as its spec says: Pmax from its record.
    assert v["p_max"].origin == "record" and waiting == []
    # With nothing typed the simulation rests on the fit and the records: unverified, not demo (D1).
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", fitArtifact=fit_id),
                        by_pool=pool)
    assert r.provenance == "unverified"
    named = {i.name: i for i in artifacts.get(r.artifactId).inputs}
    assert named["yps origin"].value == "fit" and named["yps"].source.id == fit_id
    p = by_key(r.parameters)
    assert p["yps"].origin == "fit" and p["yps"].identified is True and p["p_max"].origin == "record"
    # The fit-length preset runs as long as the fit's run.
    v, _ = bind(pool, fit=fit_id, preset="fit-length")
    assert v["t_end"].origin == "fit" and v["t_end"].value == TIMES[-1]
    # A fit of another family is refused in words.
    with pytest.raises(fermos.SimulationRefused, match="takes a fit of its own family or a logistic_v0 fit"):
        fermos.bind_parameters("fedbatch_v1", None, "ethanol", "glucose", pool, [], fit_id)


def test_an_unidentified_fitted_parameter_binds_flagged(store, monkeypatch):
    monkeypatch.setattr(kinetics, "FIT_MAX_NFEV", 20)
    fit_id = _batch_fit(monkeypatch, ("substrate", "product"))
    pool = pool_of(*STANDIN, rec("pmax1", "ethanol_max_conc", 90.0))
    v, _ = bind(pool, fit=fit_id)
    assert v["mu_max"].origin == "fit" and v["mu_max"].identified is False
    assert "did not identify it" in v["mu_max"].detail
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", fitArtifact=fit_id,
                                          overrides=typed(x0=0.2)), by_pool=pool)
    assert by_key(r.parameters)["mu_max"].identified is False
    assert any(f.startswith("mu_max is bound to fit") for f in r.flags)


def test_a_logistic_fit_gives_mu_its_coefficients_and_yps_through_its_forecast(store):
    t = np.linspace(0, 30, 16)
    x0, mu, xmax, alpha, beta, s0, gamma, delta = 0.1, 0.35, 8.0, 0.4, 0.02, 60.0, 4.5, 0.05
    x, i = fermos.logistic(t, x0, mu, xmax)
    out = fermos.fit("dep-log", [_series("biomass", t, x), _series("product", t, 0.05 + alpha * (x - x0) + beta * i),
                                 _series("substrate", t, s0 - gamma * (x - x0) - delta * i)])
    v, _ = bind(pool_of(), fit=out.kineticArtifactId)
    assert v["mu_max"].origin == "fit" and v["mu_max"].value == pytest.approx(mu, rel=1e-3) and v["mu_max"].identified
    assert v["alpha"].value == pytest.approx(alpha, rel=1e-3) and v["s0"].value == pytest.approx(s0, rel=1e-3)
    assert v["yps"].origin == "fit" and 0 < v["yps"].value < 1 and "Yp/s" in v["yps"].detail


def test_a_kept_simulation_binds_where_no_fit_or_record_does(store):
    first = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                              overrides=typed(ks=0.2, yxs=0.12, yps=0.45, mu_max=0.3, s0=50.0,
                                                              **TYPED)),
                            by_pool=pool_of())
    pool = pool_of(rec("mu1", "growth_rate_mu", 0.40, "h-1"))
    v, waiting = bind(pool, simulation=first.artifactId)
    assert v["mu_max"].origin == "record", "the records come before a kept simulation (D6)"
    assert v["ks"].origin == "simulation" and v["ks"].value == 0.2 and v["ks"].source.id == first.artifactId
    assert v["kd"].origin == "convention", "a convention binds as its spec says, not as the simulation's"
    assert waiting == []
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                          startFrom=f"simulation:{first.artifactId}"), by_pool=pool)
    named = {i.name: i for i in artifacts.get(r.artifactId).inputs}
    assert named["ks origin"].value == "simulation" and named["ks"].source.kind == "artifact"
    assert by_key(r.parameters)["ks"].origin == "simulation"
    assert r.provenance == "demo", "the kept simulation rested on a named person's values"


# ── the endpoints ──────────────────────────────────────────────────────


@pytest.fixture()
def client(monkeypatch, store):
    from openferment_core import api

    pool = pool_of(*STANDIN)
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: pool)
    return TestClient(api.app, base_url="http://127.0.0.1")


def test_the_bind_endpoint_and_the_family_scope_bind_alike(client):
    q = {"family": BATCH, "product": "ethanol", "sugar": "glucose"}
    r = client.get("/api/fermos/bind", params=q)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"values", "waiting", "notes"} and set(body["waiting"]) == {"alpha", "p_max", "x0", "p0"}
    got = {x["key"]: x for x in body["values"]}
    assert got["mu_max"]["origin"] == "record" and got["mu_max"]["recordIds"] == ["mu1", "mu2", "mu3"]
    assert any("Records bind from the Yeast ethanol program's papers" in n for n in body["notes"])
    scope = client.get(f"/api/params/{SCOPE}", params={k: v for k, v in q.items() if k != "family"}).json()
    assert {x["key"]: x["value"] for x in scope["values"]} == {k: x["value"] for k, x in got.items()}
    resolved = client.post(f"/api/params/{SCOPE}/resolve", json={
        "product": "ethanol", "sugar": "glucose", "overrides": [o.model_dump() for o in typed(mu_max=0.25)]}).json()
    assert {x["key"]: x for x in resolved["values"]}["mu_max"]["overriddenBy"] == BY
    for params_, status, words in (
        ({"family": "nowhere_v1"}, 404, "there is no model family"),
        ({**q, "sugar": "treacle"}, 422, "carbon-source id"),
        ({**q, "startFrom": "fit"}, 422, "names the fit"),
        ({**q, "durationPreset": "fit-length"}, 422, "no fit is named"),
        ({**q, "durationPreset": "forever"}, 422, "run-length preset"),
        ({**q, "fit": "0123456789abcdef"}, 422, "there is no kept fit"),
    ):
        r = client.get("/api/fermos/bind", params=params_)
        assert r.status_code == status and words in r.json()["detail"], (params_, r.json())
    bad = client.get(f"/api/params/{SCOPE}", params={"fit": "0123456789abcdef"})
    assert bad.status_code == 422 and "there is no kept fit" in bad.json()["detail"]
    # A binding keeps nothing.
    kept = intake.DATA_DIR / "artifacts"
    assert not kept.exists() or not list(kept.glob("*.json"))


# ── records named for a parameter (OF-BLD-020 §3.4, D13) ───────────────


def test_a_parameter_named_records_binds_exactly_them_and_the_rest_bind_by_the_rule(store):
    pool = pool_of(*STANDIN, rec("mu-s288c", "growth_rate_mu", 0.9, "h-1", strain=S288C, carbon="xylose"))
    v, waiting = fermos.bind_parameters(BATCH, CENPK, "ethanol", "glucose", pool, [], None,
                                        records_by_param={"mu_max": ["mu1", "mu-s288c"]})
    mu = by_key(v)["mu_max"]
    # Named by id: no strain or sugar filter chose them, and the detail says they were named.
    assert mu.origin == "record" and mu.recordIds == ["mu1", "mu-s288c"] and (mu.low, mu.high) == (0.30, 0.9)
    assert mu.detail.startswith("2 records of growth_rate_mu, named for it: ") and mu.source.kind == "record"
    # Every other parameter binds as before: CEN.PK113-7D's own records, none here.
    assert by_key(v)["ks"].origin == "waiting" and "ks" in waiting
    same, _ = fermos.bind_parameters(BATCH, None, "ethanol", "glucose", pool_of(*STANDIN), [], None)
    named, _ = fermos.bind_parameters(BATCH, None, "ethanol", "glucose", pool_of(*STANDIN), [], None,
                                      records_by_param={"yps": ["yp2"]})
    assert by_key(named)["yps"].recordIds == ["yp2"] and by_key(named)["yps"].value == 0.46
    assert {k: x for k, x in by_key(named).items() if k != "yps"} == {k: x for k, x in by_key(same).items() if k != "yps"}


def test_named_records_bind_ahead_of_a_fit_and_a_persons_override_still_wins(store, monkeypatch):
    fit_id = _batch_fit(monkeypatch)
    pool = pool_of(*STANDIN, rec("pmax1", "ethanol_max_conc", 90.0))
    got = fermos.bind(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", fitArtifact=fit_id,
                                        recordsByParam={"yps": ["yp1"]}), pool=pool)
    v = by_key(got.values)
    assert v["yps"].origin == "record" and v["yps"].recordIds == ["yp1"] and v["mu_max"].origin == "fit"
    assert any(n.startswith("yps is bound to the records named for it (yp1); the fit would have bound it, and is set "
                            "aside for it") for n in got.notes), got.notes
    over, _ = fermos.bind_parameters(BATCH, None, "ethanol", "glucose", pool, typed(yps=0.4), fit_id,
                                     records_by_param={"yps": ["yp1"]})
    assert by_key(over)["yps"].origin == "assumption" and by_key(over)["yps"].overriddenBy == BY


def test_a_simulation_on_named_records_names_them_in_its_basis_and_says_they_were_named(store):
    pool = pool_of(*STANDIN)
    rest = {k: x for k, x in dict(ks=0.2, yxs=0.12, yps=0.45, s0=50.0, **TYPED).items()}
    r = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", overrides=typed(**rest),
                                          recordsByParam={"mu_max": ["mu1", "mu2"]}), by_pool=pool)
    art = artifacts.get(r.artifactId)
    named = {i.name: i for i in art.inputs}
    assert [i.value for i in art.inputs if i.name == "mu_max record"] == ["mu1", "mu2"]
    assert all(i.source.kind == "record" for i in art.inputs if i.name == "mu_max record")
    assert named["mu_max origin"].value == fermos.NAMED and "named for it by id" in named["mu_max origin"].source.note
    # Only named records bound, so `records of` (whose records the rule found) is not said.
    assert "records of" not in named
    p = by_key(r.parameters)
    assert p["mu_max"].origin == "record" and p["mu_max"].recordIds == ["mu1", "mu2"] and p["mu_max"].identified is None
    assert artifacts.replay(r.artifactId).identical
    # A request naming no records keeps the id it had before §3.4: nothing is added to its basis.
    plain = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                              overrides=typed(mu_max=0.3, **rest)), by_pool=pool)
    assert not [i for i in artifacts.get(plain.artifactId).inputs if i.name.endswith(" origin")]


@pytest.mark.parametrize("named, words", [
    ({"mu_max": ["nowhere"]}, "record nowhere, named for mu_max, is not in the evidence pool the program switch shows"),
    ({"mu_max": ["ks1"]}, "record ks1 is a record of monod_ks"),
    ({"mu_max": ["mu-rej"]}, "is kept out by the aggregate gate: rejected"),
    ({"mu_max": ["mu-est"]}, "is kept out by the aggregate gate: industry-estimate"),
    ({"mu_max": ["mu-bad"]}, "record mu-bad, named for mu_max, is in 'g/L', which units.py does not convert into h⁻¹"),
    ({"yps": ["yp1"]}, "yps (product yield on substrate) binds from no record field here"),
    ({"p0": ["s01"]}, "p0 (product at the start) binds from no record field here"),
    ({"nope": ["mu1"]}, "recordsByParam names nope, which is no parameter of batch_v1"),
])
def test_a_named_record_that_cannot_bind_refuses_the_request_naming_it(store, named, words):
    pool = pool_of(*STANDIN, rec("mu-rej", "growth_rate_mu", 0.9, "h-1", status="rejected"),
                   rec("mu-est", "growth_rate_mu", 0.9, "h-1", provenance="industry-estimate"),
                   rec("mu-bad", "growth_rate_mu", 0.3, "g/L"))
    product = None if "yps" in named else "ethanol"
    with pytest.raises(fermos.SimulationRefused) as e:
        fermos.bind_parameters(BATCH, None, product, "glucose", pool, [], None, records_by_param=named)
    assert words in str(e.value), str(e.value)


def test_the_simulate_endpoint_takes_named_records_and_refuses_one_that_cannot_bind(client):
    body = {"family": BATCH, "product": "ethanol", "sugar": "glucose", "recordsByParam": {"mu_max": ["mu2"]},
            "overrides": [o.model_dump() for o in typed(**TYPED)]}
    ok = client.post("/api/fermos/simulate", json=body)
    assert ok.status_code == 200, ok.json()
    mu = {x["key"]: x for x in ok.json()["parameters"]}["mu_max"]
    assert mu["recordIds"] == ["mu2"] and mu["origin"] == "record"
    bad = client.post("/api/fermos/simulate", json={**body, "recordsByParam": {"mu_max": ["ks1"]}})
    assert bad.status_code == 422 and "record ks1 is a record of monod_ks" in bad.json()["detail"]
