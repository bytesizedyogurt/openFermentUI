"""One parameter panel (OF-BLD-020 §2.1, D2–D4), with no simulator.

Every spec, candidate, record and override here is a FIXTURE written in the
test: none is a measurement, a published value or a result. The Proforma
provider runs through the real binding code over demo.py's yeast STAND-IN
records, the pool the ethanol tests already use.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openferment_core import basis, demo, intake, params, proforma
from openferment_core.flowsheets import shelf
from openferment_core.models import (
    BasisSource,
    ComputedBasis,
    Override,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    ScenarioInput,
)

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
RULE = ["fit", "record:growth_rate_mu", "artifact", "simulation", "assumption", "convention", "library-default"]


def spec(key="mu_max", rule=None, **kw) -> ParameterSpec:
    base = dict(key=key, label=f"{key} (a STAND-IN)", symbol="μmax", gloss="a STAND-IN parameter for a test",
                dimension="rate", unit="h-1", min=0.0, max=2.0, group="Growth", sourceRule=rule or RULE,
                boundsReason="a STAND-IN range written for this test", convention=None)
    base.update(kw)
    return ParameterSpec(**base)


def cand(value, origin="record", **kw) -> ParameterValue:
    source = kw.pop("source", BasisSource(kind="artifact", id=f"standin-{origin}"))
    return ParameterValue(key="ignored", value=value, source=source, origin=origin, **kw)


def override(key="mu_max", value=0.3, scope="fermos:family:batch_v1", **kw) -> Override:
    base = dict(scope=scope, key=key, value=value, low=None, high=None, by=BY, at="2026-10-21", note="a STAND-IN")
    base.update(kw)
    return Override(**base)


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def standin(monkeypatch, store):
    """The yeast STAND-IN records as the pool, and every road to a simulator
    or a kept artifact closed: the params endpoints bind and run nothing."""
    from openferment_core import artifacts, evidence_pool

    def no_worker(*_a, **_k):
        raise AssertionError("a parameter scope started the simulator")

    def no_compute(*_a, **_k):
        raise AssertionError("a parameter scope kept an artifact")

    monkeypatch.setattr(proforma, "call", no_worker)
    monkeypatch.setattr(artifacts, "compute", no_compute)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records() + demo._standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: pool)
    return pool


@pytest.fixture()
def client(standin):
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


# ── scopes ─────────────────────────────────────────────────────────────


def test_a_scope_names_one_of_four_kinds_and_anything_else_is_refused_in_words():
    assert params.parse_scope("fermos:family:batch_v1") == ("fermos-family", ("batch_v1",))
    assert params.parse_scope("fermos:vessel:0123456789abcdef") == ("fermos-vessel", ("0123456789abcdef",))
    assert params.parse_scope("pureos:unit:train-1:u2") == ("pureos-unit", ("train-1", "u2"))
    assert params.parse_scope("proforma:sc-yeast-1") == ("proforma", ("sc-yeast-1",))
    assert params.scope_name("pureos-unit", "train-1", "u2") == "pureos:unit:train-1:u2"
    for bad in ("", "proforma:", "proforma", "proforma:sc 1", "proforma:sc/1", "fermos:vessel:a:b", "fermos:family",
                "pureos:unit:t", "geneos:model:x", "PROFORMA:sc-yeast-1", "proforma:-x"):
        with pytest.raises(params.ParamRefused, match="a parameter scope is fermos:family:<family id>"):
            params.parse_scope(bad)


# ── resolution ─────────────────────────────────────────────────────────


def test_the_first_source_in_the_rule_wins_in_order():
    order = ["fit", "record", "artifact", "simulation", "assumption", "convention", "library-default"]
    entries = dict(zip(order, RULE))
    for n, want in enumerate(order):
        sources = {"mu_max": {entries[o]: cand(0.1 * (i + 1), o, identified=True) for i, o in enumerate(order) if i >= n}}
        (v,) = params.resolve([spec()], sources, [])
        assert v.origin == want and v.value == pytest.approx(0.1 * (n + 1)) and v.key == "mu_max"
        # A fit alone says whether it identified the parameter; nothing else may.
        assert v.identified is (True if want == "fit" else None)
        assert v.overriddenBy is None
    (v,) = params.resolve([spec(rule=["record:growth_rate_mu", "fit"])], {"mu_max": {
        "fit": cand(0.5, "fit"), "record:growth_rate_mu": cand(0.2, "record", recordIds=["r1"])}}, [])
    assert v.origin == "record" and v.value == 0.2, "the rule's order decides, not the candidates'"


def test_an_override_wins_over_every_source_and_is_named_in_the_value_and_the_basis():
    sources = {"mu_max": {"fit": cand(0.5, "fit", identified=True), "library-default": cand(0.9, "library-default")}}
    o = override(value=0.3, low=0.2, high=0.4, note="read from a lab notebook")
    (v,) = params.resolve([spec()], sources, [o])
    assert (v.value, v.low, v.high, v.origin, v.overriddenBy) == (0.3, 0.2, 0.4, "assumption", BY)
    assert v.source.kind == "assumption" and v.source.by == BY
    assert v.source.note == "typed on 2026-10-21: read from a lab notebook"
    assert v.identified is None and v.libraryDefault == 0.9, "the library's default still shows beside a person's value"
    inputs = params.basis_inputs([spec()], [v])
    assert [i.name for i in inputs] == ["mu_max", "mu_max low", "mu_max high"]
    assert all(i.source.kind == "assumption" and i.source.by == BY and "lab notebook" in i.source.note for i in inputs)
    b = ComputedBasis(tool="t", toolVersion="1", inputs=inputs, artifactId="x", at="2026-10-21")
    assert basis.basis_provenance(b, {}, {}) == "demo"
    # The same source Proforma's assumptions carry, so a run's basis reads alike.
    assert v.source == basis.assumption_source(BY, "2026-10-21", "read from a lab notebook")


def test_an_override_needs_a_person_a_number_or_a_choice_and_its_own_range():
    s = spec()
    for bad, words in (
        (override(by="me"), "placeholder"),
        (override(by="  "), "needs a person's name"),
        (override(key="nothing"), "there is no parameter nothing here"),
        (override(value="fast"), "takes a number, not words"),
        (override(value=math.inf), "finite"),
        (override(value=0.3, low=0.4), "within its own low and high"),
        (override(value=0.3, high=0.2), "within its own low and high"),
        (override(at=""), "says when it was typed"),
    ):
        with pytest.raises(params.ParamRefused, match=words):
            params.resolve([s], {}, [bad])
    with pytest.raises(params.ParamRefused, match="two overrides of mu_max"):
        params.resolve([s], {}, [override(), override(value=0.4)])
    # A name the request gives stands in for an override that names nobody.
    (v,) = params.resolve([s], {}, [override(by="")], by=BY)
    assert v.overriddenBy == BY and v.source.by == BY
    choice = spec(key="method", rule=["library-default"], unit="", min=None, max=None, choices=["Riet", "Dewes"],
                  boundsReason="a choice of words: the library's own list")
    (v,) = params.resolve([choice], {"method": {"library-default": cand("Riet", "library-default")}},
                          [override(key="method", value="Dewes")])
    assert (v.value, v.origin, v.libraryDefault) == ("Dewes", "assumption", "Riet")
    for bad, words in ((override(key="method", value="Labik"), "one of Riet, Dewes"),
                       (override(key="method", value=1.0), "one of Riet, Dewes"),
                       (override(key="method", value="Riet", low=1.0), "takes no low or high")):
        with pytest.raises(params.ParamRefused, match=words):
            params.resolve([choice], {}, [bad])


def test_a_value_outside_its_bounds_is_kept_and_flagged_in_words():
    s = spec()
    assert params.bounds_check(s, 1.0) is None and params.bounds_check(s, "words") is None
    assert params.bounds_check(spec(min=None, max=None), 1e9) is None
    (v,) = params.resolve([s], {}, [override(value=3.0, low=1.0, high=3.5)])
    assert v.value == 3.0 and v.high == 3.5, "kept as given, never clamped"
    assert "the value, 3 h-1 and its high end, 3.5 h-1" in v.outOfBounds and s.boundsReason in v.outOfBounds
    assert "0 to 2 h-1" in v.outOfBounds and "kept as given" in v.outOfBounds
    (v,) = params.resolve([s], {"mu_max": {"record:growth_rate_mu": cand(-1.0, "record", recordIds=["r1"])}}, [])
    assert v.value == -1.0 and "the value, -1 h-1" in v.outOfBounds, "a bound source is flagged the same way"
    assert "at least 0" in params.bounds_check(spec(max=None), -1.0)


def test_a_waiting_parameter_names_the_field_that_would_bind_it():
    s = spec(rule=["fit", "record:ethanol_productivity", "record:volumetric_productivity", "assumption"])
    (v,) = params.resolve([s], {"mu_max": {"waiting": cand(None, "waiting", source=None, detail="14 records name no carbon source")}}, [])
    assert (v.value, v.source, v.origin) == (None, None, "waiting")
    assert "a record of ethanol_productivity or volumetric_productivity through the aggregate gate" in v.detail
    assert "a fit a person chooses" in v.detail and "a named person's assumption" in v.detail
    assert v.detail.endswith("14 records name no carbon source")
    assert params.basis_inputs([s], [v]) == [], "a waiting value adds nothing to a basis"


def test_a_convention_takes_the_stated_value_with_its_reason():
    s = spec(key="n_inhibition", rule=["fit", "assumption", "convention"], unit="", convention=1.0,
             note="a STAND-IN convention: its reason in words")
    (v,) = params.resolve([s], {}, [])
    assert (v.value, v.origin, v.source.kind, v.source.note) == (1.0, "convention", "convention", s.note)
    (v,) = params.resolve([spec(rule=["convention"])], {}, [])
    assert v.origin == "waiting", "a convention rule with nothing stated waits, it does not invent"


def test_records_enter_a_basis_one_by_one_so_their_provenance_counts():
    (v,) = params.resolve([spec()], {"mu_max": {"record:growth_rate_mu": cand(
        0.2, "record", low=0.1, high=0.3, recordIds=["r1", "r2"], source=BasisSource(kind="record", note="2 records"),
        detail="2 records of growth_rate_mu")}}, [])
    inputs = params.basis_inputs([spec()], [v])
    assert [i.name for i in inputs] == ["mu_max", "mu_max low", "mu_max high", "mu_max record", "mu_max record"]
    assert [i.source.id for i in inputs if i.source.kind == "record"] == ["r1", "r2"]
    assert inputs[0].source.kind == "convention" and "2 records of growth_rate_mu" in inputs[0].source.note
    b = ComputedBasis(tool="t", toolVersion="1", inputs=inputs, artifactId="x", at="2026-10-21")
    assert basis.basis_provenance(b, {"r1": {"provenance": "verified"}, "r2": {"provenance": "unverified"}}, {}) == "unverified"


# ── D4: every spec carries the reason for its bounds ──────────────────


def test_a_spec_without_a_bounds_reason_or_with_an_unknown_source_is_refused():
    for blank in ("", "   "):
        with pytest.raises(ValidationError, match="written reason"):
            spec(boundsReason=blank)
    with pytest.raises(ValidationError, match="is not a source"):
        spec(rule=["fit", "a paper I remember"])
    with pytest.raises(ValidationError, match="is not a source"):
        spec(rule=["record:"])
    with pytest.raises(ValidationError, match="names where its value comes from"):
        spec(sourceRule=[])


def test_the_check_reads_every_declared_spec_and_names_one_with_no_reason(monkeypatch, capsys):
    n, problems = params.check()
    assert problems == []
    from openferment_core import kinetics, vessel

    # The shelf's inputs, fermOS's family specs (OF-BLD-020 §3.1) and its
    # vessel declarations (§4.1).
    assert n == (sum(len(info.inputs) for info in shelf.SHELF.values())
                 + sum(len(f.specs()) for f in kinetics.FAMILIES.values())
                 + sum(len(s) for _, s in vessel._static()))
    assert params.main(["--check"]) == 0 and "every one has a written bounds reason" in capsys.readouterr().out
    unreasoned = ParameterSpec.model_construct(**{**spec().model_dump(), "boundsReason": " "})
    monkeypatch.setitem(params._STATIC, "fermos-family", lambda: [("a STAND-IN family", [spec(), unreasoned])])
    n, problems = params.check()
    assert any("a STAND-IN family: mu_max has no boundsReason" in p for p in problems)
    assert any("two parameters named mu_max" in p for p in problems)
    assert params.main(["--check"]) == 1 and "✗" in capsys.readouterr().out

    def broken():
        yield "a STAND-IN family", [spec(boundsReason="")]

    monkeypatch.setitem(params._STATIC, "fermos-family", broken)
    assert any("the specs could not be read" in p and "written reason" in p for p in params.check()[1])


# ── Proforma's scenarios (`proforma:<scenario id>`) ────────────────────


def test_a_flowsheets_inputs_are_its_specs_with_bounds_and_their_reasons():
    specs = {s.key: s for s in params.flowsheet_specs(shelf.info(ETHANOL))}
    assert list(specs) == [i.key for i in shelf.info(ETHANOL).inputs]
    feed, titre, scale, purity = specs["feed_glucose_conc"], specs["titre"], specs["plant_scale"], specs["ethanol_purity"]
    assert feed.sourceRule == ["record:medium_component_conc", "assumption"]
    assert titre.sourceRule == ["fit", "record:ethanol_titre", "assumption"], "a chosen fit replaces the records"
    from openferment_core import units

    lo, hi = units.field("ethanol_titre")["range"]
    assert (titre.min, titre.max) == (lo, hi) and "ontology's plausibility range for ethanol_titre" in titre.boundsReason
    assert (scale.min, scale.max, scale.sourceRule) == (0.0, None, ["assumption"])
    assert scale.boundsReason == "a physical limit: no negative ethanol fermented in a year"
    assert purity.sourceRule == ["convention"] and purity.convention == "fuel grade" and purity.min is None
    assert purity.note == shelf.info(ETHANOL).inputs[-1].note
    pha = {s.key: s for s in params.flowsheet_specs(shelf.info("pha_sugar_v0"))}
    assert (pha["content"].min, pha["content"].max) == (0.0, 1.0) and "does not convert into g g-1" in pha["content"].boundsReason
    assert (pha["recovery"].min, pha["recovery"].max) == (0.0, 1.0)
    corn = params.flowsheet_specs(shelf.info("corn_drygrind"))
    assert all(s.sourceRule == ["library-default"] and "package's own default" in s.boundsReason for s in corn)


def test_the_provider_binds_what_bind_inputs_binds(standin):
    bound = {i.key: i for i in proforma.bind_inputs(ETHANOL, standin.records)}
    for got in (params.scope("proforma:sc-yeast-1"),
                params.scope(f"proforma:{MADE_HERE}", ParamResolveRequest(flowsheet=ETHANOL))):
        assert got.kind == "proforma" and [s.key for s in got.specs] == [i.key for i in shelf.info(ETHANOL).inputs]
        values = {v.key: v for v in got.values}
        assert set(bound) < set(values) and values["ethanol_purity"].value == "fuel grade"
        for key, inp in bound.items():
            v = values[key]
            if inp.binding == "records":
                assert (v.origin, v.value, v.low, v.high, v.recordIds) == ("record", inp.value, inp.low, inp.high, inp.recordIds)
                assert v.source == inp.source
            else:
                assert inp.binding == "waiting" and v.origin == "waiting" and v.value is None
        assert got.waiting == [k for k, i in bound.items() if i.binding == "waiting"] == ["plant_scale", "glucose_price"]
        assert values["feed_glucose_conc"].detail.startswith("3 records of medium_component_conc, 20 to 100 g L-1, median 60")
    assert params.scope("proforma:sc-yeast-1").title.endswith(f"({shelf.info(ETHANOL).title})")
    narrowed = params.scope("proforma:sc-yeast-1", ParamResolveRequest(host="nobody"))
    assert "titre" in narrowed.waiting


def test_a_fit_a_person_chose_is_the_first_source_of_titre():
    fitted = ScenarioInput(key="titre", label="titre", unit="g L-1", binding="artifact", value=80.0, low=70.0, high=90.0,
                           source=BasisSource(kind="artifact", id="0123456789abcdef", note="the forecast's median titre"),
                           flags=["chosen in place of the 9 records it bound"])
    cands = params._input_sources(fitted, SimpleNamespace(records_by_id={}), "glucose")
    titre = next(s for s in params.flowsheet_specs(shelf.info(ETHANOL)) if s.key == "titre")
    (v,) = params.resolve([titre], {"titre": cands}, [])
    assert (v.origin, v.identified, v.value, v.source.id) == ("fit", True, 80.0, "0123456789abcdef")
    assert "the forecast's median titre" in v.detail and "chosen in place of the 9 records" in v.detail


def test_an_override_of_a_proforma_input_is_an_assumption_in_the_basis(standin):
    o = override(key="glucose_price", value=0.4, low=0.3, high=0.5, scope="proforma:sc-yeast-1")
    r = params.resolve_scope("proforma:sc-yeast-1", ParamResolveRequest(overrides=[o]))
    values = {v.key: v for v in r.values}
    assert values["glucose_price"].origin == "assumption" and values["glucose_price"].overriddenBy == BY
    assert r.waiting == ["plant_scale"] and r.warnings == []
    assert [i.name for i in r.basisInputs] == ["glucose_price", "glucose_price low", "glucose_price high"]
    assert all(i.unit == "USD kg-1" and i.source.kind == "assumption" and i.source.by == BY for i in r.basisInputs)
    # D4: a person may type outside the bounds; it is kept and said.
    far = params.resolve_scope("proforma:sc-yeast-1", ParamResolveRequest(overrides=[
        override(key="titre", value=400.0, scope="proforma:sc-yeast-1")]))
    titre = next(v for v in far.values if v.key == "titre")
    assert titre.value == 400.0 and titre.origin == "assumption" and far.warnings == [titre.outOfBounds]
    assert "ontology's plausibility range for ethanol_titre" in titre.outOfBounds
    with pytest.raises(params.ParamRefused, match="sent to proforma:sc-yeast-1: proforma:sc-pha-1"):
        params.resolve_scope("proforma:sc-yeast-1", ParamResolveRequest(overrides=[override(scope="proforma:sc-pha-1")]))


# ── the endpoints ──────────────────────────────────────────────────────


def test_get_serves_a_scope_and_refuses_in_words(client):
    r = client.get("/api/params/proforma:sc-yeast-1")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"scope", "kind", "title", "specs", "values", "waiting", "notes"}
    assert body["scope"] == "proforma:sc-yeast-1" and body["kind"] == "proforma"
    assert all(s["boundsReason"].strip() for s in body["specs"]) and len(body["specs"]) == len(body["values"])
    assert set(body["values"][0]) == set(ParameterValue.model_fields)
    made = client.get(f"/api/params/proforma:{MADE_HERE}?flowsheet={ETHANOL}")
    assert made.status_code == 200 and made.json()["waiting"] == body["waiting"]
    for path, status, words in (
        ("/api/params/proforma:nowhere", 404, "there is no scenario nowhere"),
        ("/api/params/fermos:family:nowhere", 404, "there is no model family nowhere"),
        ("/api/params/fermos:vessel:0123456789abcdef", 404, "no artifact '0123456789abcdef' is on file here"),
        ("/api/params/pureos:unit:t1:u1", 404, "pureOS's train units"),
        ("/api/params/nothing-at-all", 422, "a parameter scope is"),
        ("/api/params/proforma:sc-yeast-1/resolve", 422, "a parameter scope is"),
        ("/api/params/proforma:sc-s1", 422, "authored scenario"),
        (f"/api/params/proforma:{MADE_HERE}?flowsheet=cornstover_benchmark", 422, "reference biorefinery"),
        ("/api/params/proforma:sc-yeast-1?flowsheet=pha_sugar_v0", 422, "sc-yeast-1 runs ethanol_glucose_v0"),
        ("/api/params/proforma:sc-yeast-1?fits=[1]", 422, "fits is a JSON object"),
        ("/api/params/proforma:sc-yeast-1?fits={\"recovery\":\"0123456789abcdef\"}", 422, "a fermOS fit feeds"),
    ):
        r = client.get(path)
        assert r.status_code == status and words in r.json()["detail"], (path, r.status_code, r.json())


def test_post_resolves_overrides_and_runs_nothing(client, store):
    o = override(key="plant_scale", value=100000.0, scope="proforma:sc-yeast-1").model_dump()
    r = client.post("/api/params/proforma:sc-yeast-1/resolve", json={"overrides": [o]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"scope", "values", "waiting", "basisInputs", "warnings", "notes"}
    assert body["waiting"] == ["glucose_price"] and body["warnings"] == []
    assert [i["name"] for i in body["basisInputs"]] == ["plant_scale"]
    assert body["basisInputs"][0]["source"] == {"kind": "assumption", "id": None, "note": "typed on 2026-10-21: a STAND-IN", "by": BY}
    assert not any(store.rglob("*.json")), "the service keeps no override and no artifact"
    for payload, status, words in (
        ({"overrides": [{**o, "by": "me"}]}, 422, "placeholder"),
        ({"overrides": [{**o, "key": "sugarFeed"}]}, 422, "there is no parameter sugarFeed here"),
        ({"overrides": [{**o, "scope": "proforma:sc-pha-1"}]}, 422, "names the scope it changes"),
        ({"overrides": [{**o, "value": "a lot"}]}, 422, "takes a number, not words"),
    ):
        r = client.post("/api/params/proforma:sc-yeast-1/resolve", json=payload)
        assert r.status_code == status and words in r.json()["detail"], (payload, r.json())
    assert client.post("/api/params/proforma:nowhere/resolve", json={}).status_code == 404
    assert client.post("/api/params/bogus/resolve", json={}).status_code == 422


def test_the_post_is_guarded_like_every_changing_request(client):
    r = client.post("/api/params/proforma:sc-yeast-1/resolve", json={},
                    headers={"host": "127.0.0.1:8000", "origin": "https://evil.example.com"})
    assert r.status_code == 403 and "evil.example.com" in r.json()["detail"]
    assert client.get("/api/params/proforma:sc-yeast-1", headers={"origin": "https://evil.example.com"}).status_code == 200
