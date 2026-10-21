"""fermOS's model families (OF-BLD-020 §3.1, D5). Every process number here
is a STAND-IN chosen for a synthetic case, never a result and never a record;
none of them is in kinetics.py, which an AST test below holds to its named
solver settings."""
from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import numpy as np
import pytest

from openferment_core import kinetics as K
from openferment_core.kinetics import FAMILIES, IX, FamilyRefused

# ── stand-ins ──────────────────────────────────────────────────────────
STANDIN_KINETICS = dict(mu_max=0.40, ks=0.20, kd=0.01, yxs=0.15, alpha=2.0, beta=0.05, yps=0.45, maintenance=0.02,
                        p_max=90.0, n_inhibition=1.0, ki_substrate=150.0, yxo=None, mo=0.0)
STANDIN_START = {"X": 0.2, "S": 50.0, "P": 0.0}
STANDIN_RUN_H = 40.0
STANDIN_AEROBIC = dict(yxo=1.2, mo=0.01)
STANDIN_FED_START = {"X": 1.0, "S": 5.0, "P": 0.0, "V": 1.0}
STANDIN_FED = {
    "constant": dict(STANDIN_KINETICS, feed_profile="constant", feed_rate=0.01, mu_set=None, feed_conc=400.0,
                     feed_start_h=4.0, feed_end_h=30.0),
    "exponential": dict(STANDIN_KINETICS, feed_profile="exponential", feed_rate=None, mu_set=0.15, feed_conc=400.0,
                        feed_start_h=4.0, feed_end_h=24.0),
    # a feed too weak to cover maintenance: the culture starves with the feed on
    "weak": dict(STANDIN_KINETICS, feed_profile="constant", feed_rate=0.0002, mu_set=None, feed_conc=400.0,
                 feed_start_h=0.0, feed_end_h=None, maintenance=0.05),
}
STANDIN_FED_RUN_H = {"constant": 40.0, "exponential": 30.0, "weak": 60.0}
STANDIN_CHEMOSTAT = dict(STANDIN_KINETICS, feed_conc=20.0, dilution_rate=0.1)
STANDIN_CHEMOSTAT_START = {"X": 0.5, "S": 10.0, "P": 0.0}
STANDIN_CHEMOSTAT_RUN_H = 400.0
STANDIN_WASHOUT_MARGIN = 0.05
STANDIN_STORAGE = dict(mu_max=0.30, ks=0.5, kd=0.0, yxs=0.45, yps=0.35, maintenance=0.01, ki_substrate=None,
                       k_n=0.01, yxn=8.0, q_storage_max=0.15, q_max=0.8, yxo=None, mo=0.0)
STANDIN_STORAGE_START = {"X": 0.5, "S": 30.0, "N": 0.5}
STANDIN_STORAGE_RICH = {"X": 0.5, "S": 200.0, "N": 0.5}
STANDIN_PMAX = dict(mu_max=0.40, ks=0.20, kd=0.0, yxs=0.15, alpha=2.0, beta=0.5, yps=0.45, maintenance=0.0,
                    p_max=20.0, n_inhibition=1.0, ki_substrate=None, yxo=None, mo=0.0)
STANDIN_PMAX_START = {"X": 0.2, "S": 150.0, "P": 0.0}
# §3.R (finding 1): a Haldane μ that peaks at low sugar and falls far by the
# feed's sugar, so μ(Sf) − kd is under D while μ's peak is above it. Two
# starts: one near the culture, one near washout. STAND-INs, the reviewer's.
STANDIN_HALDANE = dict(mu_max=0.5, ks=0.5, kd=0.0, yxs=0.5, alpha=0.1, beta=0.0, yps=0.45, maintenance=0.0,
                       n_inhibition=1.0, p_max=90.0, ki_substrate=2.0, yxo=None, mo=0.0, dilution_rate=0.15,
                       feed_conc=50.0)
STANDIN_HALDANE_NEAR_CULTURE = {"X": 20.0, "S": 1.0, "P": 0.0}
STANDIN_HALDANE_NEAR_WASHOUT = {"X": 0.1, "S": 50.0, "P": 0.0}
STANDIN_HALDANE_RUN_H = 400.0
STANDIN_FIT_TIMES = np.linspace(0.0, 12.0, 12)
STANDIN_FIT_KEYS = ("mu_max", "ks", "yxs", "yps", "alpha", "beta")
# Where the fit starts: each rate off its stand-in by a factor, as a start
# estimate would be.
STANDIN_FIT_START = dict(mu_max=0.3, ks=0.6, yxs=0.3, yps=0.3, alpha=3.0, beta=0.1)
STANDIN_FEW_EVALUATIONS = 30
# The reference tolerance a synthetic series is made at, so the fit (at
# K.RTOL) is not judged against its own discretisation.
REF_RTOL, REF_ATOL = 1e-12, 1e-14
BALANCE = 1e-3  # §3.1's test: 0.1 %


def dense(traj):
    times = traj.times(steps=True)
    return times, traj.sample(times)


def batch():
    return FAMILIES["batch_v1"]


def reference(fam, p, y0, t_end, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(K, "RTOL", REF_RTOL)
        m.setattr(K, "ATOL", REF_ATOL)
        return fam.simulate(p, y0, t_end)


# ── the registry is what D5 and Appendix 2 §A say ──────────────────────

# D5's words, as the document writes them.
D5 = {
    "batch_v1": ["dX/dt = μ·X − kd·X", "μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ", "dP/dt = (α·μ + β)·X",
                 "dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dP/dt − m·X",
                 "states X, S, P; optional kd, Ki, m (zero when absent, said so)"],
    "fedbatch_v1": ["adds V with dV/dt = F(t), feed concentration Sf, profile `constant` | `exponential` (set μ_set, "
                    "F = μ_set·X·V/(Yxs·(Sf − S))) | `steps` (a table), dilution terms on every state"],
    "chemostat_v1": ["dilution D on every state, feed Sf, steady state solved and the dynamic path integrated; washout "
                     "reported when D ≥ μmax·Sf/(Ks + Sf)"],
    "storage_v1": ["a second substrate N with its own Monod term limiting growth, a storage product Q accumulating "
                   "when N is exhausted at rate qQ,max·S/(Ks+S)·(1 − Q/Qmax)"],
    "light_v1": ["declared with its parameters (incident irradiance, path length, attenuation coefficient, "
                 "photoinhibition constant) and no `rhs`: a socket that refuses to run in words"],
    "oxygen": ["qO2 = μ/Yxo + mo", "OUR(t) = qO2·X"],
}
BATCH_KEYS = {"mu_max", "ks", "kd", "yxs", "alpha", "beta", "yps", "maintenance", "p_max", "n_inhibition",
              "ki_substrate", "yxo", "mo", "x0", "s0", "p0", "v0", "t_end"}
APPENDIX_KEYS = {
    "batch_v1": BATCH_KEYS,
    "fedbatch_v1": BATCH_KEYS | {"feed_profile", "feed_rate", "mu_set", "feed_conc", "feed_start_h", "feed_end_h"},
    "chemostat_v1": BATCH_KEYS | {"dilution_rate", "feed_conc"},
    # As built (8): the store is the product, so α, β, Pmax, n and P0 are not
    # this family's.
    "storage_v1": (BATCH_KEYS - {"alpha", "beta", "p_max", "n_inhibition", "p0"})
    | {"n_initial", "k_n", "yxn", "q_storage_max", "q_max"},
    "light_v1": {"irradiance", "path_length", "attenuation", "k_photoinhibition"},
}


def words(text: str) -> str:
    return " ".join(text.split())


def test_the_module_docstring_writes_every_family_as_d5_does():
    doc = words(K.__doc__)
    for fid, lines in D5.items():
        for line in lines:
            assert words(line) in doc, (fid, line)
    for fid, fam in FAMILIES.items():
        assert fam.equations.startswith(fid), fid
    for line in D5["batch_v1"] + D5["oxygen"]:
        assert line in FAMILIES["batch_v1"].equations


def test_every_family_with_a_product_shows_the_pmax_gate_on_beta():
    """§3.R finding 5: the rate law gates β·X by (1 − P/Pmax)ⁿ in every
    family with a product (_rates), and fed-batch's and chemostat's
    equations, which fermOS → Simulate shows, wrote β bare."""
    for fid, fam in FAMILIES.items():
        if not fam.has_P or fam.socket:
            continue
        eq = fam.equations
        assert "fP = (1 − P/Pmax)ⁿ" in eq and "β·fP" in eq, fid
        assert "(α·μ + β)·X" not in eq.split("As built")[0] or fid == "batch_v1", (fid, "β is bare in the rate law")


def test_every_family_declares_the_appendix_parameters_with_bounds_and_groups():
    from openferment_core import units

    allowed = set(K.GROUPS)
    for fid, fam in FAMILIES.items():
        specs = fam.specs()
        keys = {s.key for s in specs}
        assert len(keys) == len(specs), fid
        assert keys == APPENDIX_KEYS[fid], (fid, keys ^ APPENDIX_KEYS[fid])
        for s in specs:
            assert s.boundsReason.strip() and s.group in allowed and s.sourceRule, (fid, s.key)
            for e in s.sourceRule:
                if e.startswith("record:"):
                    assert units.field(e.split(":", 1)[1]) is not None, (fid, s.key, e)
        assert fam.groups() == [g for g in K.GROUPS if g in {s.group for s in specs}]
    b = {s.key: s for s in batch().specs()}
    assert b["kd"].convention == 0 and b["beta"].convention == 0 and b["maintenance"].convention == 0
    assert b["ki_substrate"].convention == "off" and b["n_inhibition"].convention == 1
    assert b["yxo"].convention == "anaerobic" and b["t_end"].convention == "until the sugar runs out"
    # D6's order: a fit, the records, a kept simulation, a person, a convention.
    assert b["mu_max"].sourceRule == ["fit", "record:growth_rate_mu", "simulation", "assumption"]
    assert b["s0"].sourceRule == ["fit", "record:medium_component_conc", "simulation", "assumption"]
    assert "convention" not in b["p_max"].sourceRule and "convention" not in b["alpha"].sourceRule
    # The fields the appendix calls new, which §3.2 added to the ontology.
    assert b["maintenance"].sourceRule == ["fit", "record:maintenance_coefficient", "simulation", "assumption",
                                           "convention"]
    assert b["yxo"].sourceRule == ["fit", "record:biomass_yield_oxygen", "simulation", "assumption", "convention"]
    # The run length is a fit's only under the fit-length preset, and never a kept simulation's.
    assert b["t_end"].sourceRule == ["fit", "convention", "assumption"]
    assert all("simulation" not in s.sourceRule for s in FAMILIES["light_v1"].specs())


def test_the_light_socket_refuses_in_words():
    fam = FAMILIES["light_v1"]
    assert fam.socket and [s.key for s in fam.specs()] == ["irradiance", "path_length", "attenuation",
                                                           "k_photoinhibition"]
    for call in (lambda: fam.simulate({}, {}, None), lambda: fam.fit({"X": ([0, 1], [1, 2])}, {}, {})):
        with pytest.raises(FamilyRefused, match="light_v1 is declared and not built.*What would build it"):
            call()


def test_a_parameter_with_no_value_refuses_naming_it():
    with pytest.raises(FamilyRefused, match="no value for ks"):
        batch().simulate({**STANDIN_KINETICS, "ks": None}, STANDIN_START, None)
    with pytest.raises(FamilyRefused, match="no start value for X"):
        batch().simulate(STANDIN_KINETICS, {"S": 1.0, "P": 0.0}, None)
    with pytest.raises(FamilyRefused, match="yps must be above zero"):
        batch().simulate({**STANDIN_KINETICS, "yps": 0.0}, STANDIN_START, None)


# ── every family mass-balanced; the sugar never negative ───────────────


def runs():
    out = {
        "batch_v1": batch().simulate(STANDIN_KINETICS, STANDIN_START, STANDIN_RUN_H),
        "batch_v1 aerobic": batch().simulate({**STANDIN_KINETICS, **STANDIN_AEROBIC}, STANDIN_START, None),
        "chemostat_v1": FAMILIES["chemostat_v1"].simulate(STANDIN_CHEMOSTAT, STANDIN_CHEMOSTAT_START,
                                                          STANDIN_CHEMOSTAT_RUN_H),
        "storage_v1": FAMILIES["storage_v1"].simulate(STANDIN_STORAGE, STANDIN_STORAGE_START, None),
    }
    for name, p in STANDIN_FED.items():
        out[f"fedbatch_v1 {name}"] = FAMILIES["fedbatch_v1"].simulate(p, STANDIN_FED_START, STANDIN_FED_RUN_H[name])
    return out


def test_every_family_integrates_mass_balanced_within_a_tenth_of_a_percent():
    for name, tr in runs().items():
        mb = K.mass_balance(tr)
        assert mb["consumed"] > 0, name
        assert mb["relAux"] < BALANCE and mb["relCross"] < BALANCE, (name, mb)
        assert tr.balance["closure"] == mb["closure"]


def test_the_sugar_never_goes_negative():
    for name, tr in runs().items():
        _, Y = dense(tr)
        # Rounding on the zero the starved culture holds, never grams below it.
        assert Y[IX["S"]].min() >= -1e-12, (name, Y[IX["S"]].min())
    weak = FAMILIES["fedbatch_v1"].simulate(STANDIN_FED["weak"], STANDIN_FED_START, STANDIN_FED_RUN_H["weak"])
    assert any(s.mode.starved for s in weak.segments), "the weak feed starves the culture"


def test_the_balance_catches_a_wrong_rate_law(monkeypatch):
    """Sabotage: the sugar equation forgets 1/Yps on the product, in the
    sugar and in the consumption state alike. The cross-check through the
    yields reads it; the check of the consumption states, which carry the
    same wrong term, cannot."""
    right = K._rhs

    def wrong(fam, v, mode, t_regime, counter):
        f = right(fam, v, mode, t_regime, counter)

        def g(t, y):
            d = f(t, y)
            d_p = d[IX["Cp"]] / y[IX["V"]]
            d[IX["S"]] += d_p * (1 - v["yps"])
            d[IX["Cp"]] *= v["yps"]
            return d
        return g

    monkeypatch.setattr(K, "_rhs", wrong)
    tr = batch().simulate(STANDIN_KINETICS, STANDIN_START, STANDIN_RUN_H)
    assert tr.balance["relCross"] > K.BALANCE_TOL and tr.balance["relAux"] < BALANCE


def test_the_integration_holds_against_a_tight_reference(monkeypatch):
    fam = batch()
    ref = reference(fam, STANDIN_KINETICS, STANDIN_START, STANDIN_RUN_H, monkeypatch)
    tr = fam.simulate(STANDIN_KINETICS, STANDIN_START, STANDIN_RUN_H)
    ts = np.linspace(0.0, STANDIN_RUN_H, 401)
    a, b = tr.sample(ts), ref.sample(ts)
    for state in ("X", "S", "P"):
        assert np.abs(a[IX[state]] - b[IX[state]]).max() < 1e-3 * STANDIN_START["S"], state
    assert abs(tr.runout_h - ref.runout_h) < 1e-4


def test_the_sugar_runs_out_at_its_share_of_the_start_and_a_stalled_run_is_refused():
    fam = batch()
    tr = fam.simulate(STANDIN_KINETICS, STANDIN_START, None)
    assert tr.t_final == tr.runout_h
    assert tr.y_final[IX["S"]] == pytest.approx(K.RUN_OUT_SHARE * STANDIN_START["S"], rel=1e-6)
    with pytest.raises(FamilyRefused, match="the sugar does not run out.*name a run length"):
        fam.simulate(STANDIN_PMAX, STANDIN_PMAX_START, None)
    with pytest.raises(FamilyRefused, match="needs a run length"):
        FAMILIES["fedbatch_v1"].simulate(STANDIN_FED["constant"], STANDIN_FED_START, None)


# ── Pmax ───────────────────────────────────────────────────────────────


def test_no_product_forms_above_pmax():
    fam = batch()
    for n in (0.5, 1.0, 2.0):
        tr = fam.simulate({**STANDIN_PMAX, "n_inhibition": n}, STANDIN_PMAX_START, 200.0)
        _, Y = dense(tr)
        # LSODA overshoots by a few millionths before the factor freezes.
        assert Y[IX["P"]].max() <= STANDIN_PMAX["p_max"] * (1 + 1e-5), (n, Y[IX["P"]].max())
    above = {**STANDIN_PMAX_START, "P": STANDIN_PMAX["p_max"] * 1.25}
    tr = fam.simulate({**STANDIN_PMAX, "n_inhibition": 0.5}, above, 50.0)
    _, Y = dense(tr)
    assert Y[IX["P"]].max() == above["P"] and tr.y_final[IX["X"]] == pytest.approx(above["X"], abs=1e-12)
    assert K._f_product({"p_max": 1.0, "n_inhibition": 0.5}, 1.5) == 0.0


# ── oxygen ─────────────────────────────────────────────────────────────


def test_our_is_qo2_times_x_and_zero_when_anaerobic():
    p = {**STANDIN_KINETICS, **STANDIN_AEROBIC}
    tr = batch().simulate(p, STANDIN_START, None)
    times = tr.times()
    our = K.oxygen(p, tr, times)
    Y = tr.sample(times)
    for t, o, col in zip(times, our, Y.T):
        S, P = max(col[1], 0.0), max(col[2], 0.0)
        mu = (p["mu_max"] * S / (p["ks"] + S) / (1 + S / p["ki_substrate"])
              * max(0.0, 1 - P / p["p_max"]) ** p["n_inhibition"])
        assert o == pytest.approx((mu / p["yxo"] + p["mo"]) * col[0], rel=1e-9, abs=1e-12), t
    peak, peak_h = K.oxygen_peak(p, tr)
    assert peak >= max(our) and 0 < peak_h <= tr.t_final
    anaerobic = batch().simulate(STANDIN_KINETICS, STANDIN_START, None)
    assert not any(K.oxygen(STANDIN_KINETICS, anaerobic)) and K.oxygen_peak(STANDIN_KINETICS, anaerobic) == (0.0, None)


# ── fed-batch, chemostat, storage ──────────────────────────────────────


def test_a_feed_brings_what_it_names_between_its_start_and_end():
    p = STANDIN_FED["constant"]
    tr = FAMILIES["fedbatch_v1"].simulate(p, STANDIN_FED_START, STANDIN_FED_RUN_H["constant"])
    fed = p["feed_rate"] * (p["feed_end_h"] - p["feed_start_h"]) * p["feed_conc"]
    assert tr.y_final[IX["Min"]] == pytest.approx(fed, rel=1e-9)
    assert tr.y_final[IX["V"]] == pytest.approx(STANDIN_FED_START["V"] + p["feed_rate"] * (p["feed_end_h"] - p["feed_start_h"]))


def test_the_exponential_feed_holds_its_set_growth_rate():
    fam = FAMILIES["fedbatch_v1"]
    p = STANDIN_FED["exponential"]
    tr = fam.simulate(p, STANDIN_FED_START, STANDIN_FED_RUN_H["exponential"])
    ts = np.linspace(10.0, 20.0, 11)
    Y = tr.sample(ts)
    mus = [K._terms(fam, tr.p, col, tr.segment_at(t).mode, tr.segment_at(t).t_regime)["mu"] for t, col in zip(ts, Y.T)]
    assert np.mean(mus) == pytest.approx(p["mu_set"], rel=0.02)
    with pytest.raises(FamilyRefused, match="μset is above μmax"):
        fam.simulate({**p, "mu_set": p["mu_max"] * 2}, STANDIN_FED_START, STANDIN_FED_RUN_H["exponential"])


def test_the_chemostat_reaches_its_steady_state_and_washes_out_at_the_predicted_rate():
    ch = FAMILIES["chemostat_v1"]
    tr = ch.simulate(STANDIN_CHEMOSTAT, STANDIN_CHEMOSTAT_START, STANDIN_CHEMOSTAT_RUN_H)
    ss = ch.steady_state(STANDIN_CHEMOSTAT)
    for state in ("X", "S", "P"):
        assert tr.y_final[IX[state]] == pytest.approx(ss[state], rel=1e-6, abs=1e-9), state
    off = {**STANDIN_CHEMOSTAT, "kd": 0.0, "ki_substrate": None}
    w = ch.washout(off)
    assert w["dWashout"] == pytest.approx(w["dWashoutD5"], rel=1e-12)
    for factor, washes in ((1 - STANDIN_WASHOUT_MARGIN, False), (1 + STANDIN_WASHOUT_MARGIN, True)):
        p = {**off, "dilution_rate": factor * w["dWashoutD5"]}
        end = ch.simulate(p, STANDIN_CHEMOSTAT_START, 3000.0).y_final
        held = ch.steady_state(p)
        assert held["washout"] is washes
        if washes:
            assert abs(end[IX["X"]]) < 1e-9 and end[IX["S"]] == pytest.approx(p["feed_conc"], rel=1e-6)
        else:
            assert end[IX["X"]] == pytest.approx(held["X"], rel=1e-6) and end[IX["X"]] > 0.1
    # With kd and Ki set, D5's expression overstates the washout rate; between
    # the two the culture washes out.
    general = ch.washout(STANDIN_CHEMOSTAT)
    assert general["dWashout"] < general["dWashoutD5"]
    between = {**STANDIN_CHEMOSTAT, "dilution_rate": (general["dWashout"] + general["dWashoutD5"]) / 2}
    assert abs(ch.simulate(between, STANDIN_CHEMOSTAT_START, 4000.0).y_final[IX["X"]]) < 1e-6


def test_a_haldane_chemostat_finds_its_culture_where_mu_at_the_feed_is_under_d():
    """§3.R finding 1: washout was decided on μ(Sf) − kd alone. A Haldane μ
    can rise above D + kd at low sugar while μ(Sf) − kd is under D: then a
    steady culture exists at the low-S root, and washout is a second stable
    state. The steady state is the culture, said bistable; which one a run
    reaches depends on where it starts, and `reached` says which."""
    ch = FAMILIES["chemostat_v1"]
    p = STANDIN_HALDANE
    ss = ch.steady_state(p)
    assert ss["dWashout"] < p["dilution_rate"] < ss["dWashoutMax"], ss
    assert ss["washout"] is False and ss["bistable"] is True, ss
    culture = ch.simulate(p, STANDIN_HALDANE_NEAR_CULTURE, STANDIN_HALDANE_RUN_H)
    for state in ("X", "S", "P"):
        assert culture.y_final[IX[state]] == pytest.approx(ss[state], rel=1e-6), state
    assert ch.reached(ss, culture) == "culture"
    washed = ch.simulate(p, STANDIN_HALDANE_NEAR_WASHOUT, STANDIN_HALDANE_RUN_H)
    assert washed.y_final[IX["X"]] < 1e-6 and ch.reached(ss, washed) == "washout"
    # Above μ's peak no culture holds, whatever the start.
    over = {**p, "dilution_rate": ss["dWashoutMax"] * (1 + STANDIN_WASHOUT_MARGIN)}
    gone = ch.steady_state(over)
    assert gone["washout"] is True and gone["bistable"] is False and gone["X"] == 0.0
    assert ch.reached(gone, ch.simulate(over, STANDIN_HALDANE_NEAR_CULTURE, STANDIN_HALDANE_RUN_H)) == "washout"
    # Monod alone rises all the way to Sf: its peak is μ(Sf), and one state.
    plain = ch.steady_state({**STANDIN_CHEMOSTAT, "ki_substrate": None})
    assert plain["dWashoutMax"] == pytest.approx(plain["dWashout"], rel=1e-9) and plain["bistable"] is False


def test_a_chemostat_with_no_dilution_is_refused_in_words():
    """§3.R finding 2: D = 0 sits inside the spec's bounds, and the steady
    state divided nothing by nothing (NaN into brentq, a 500). With nothing
    flowing it is a batch: refused in words before anything integrates."""
    ch = FAMILIES["chemostat_v1"]
    still = {**STANDIN_CHEMOSTAT, "kd": 0.0, "beta": 0.0, "maintenance": 0.0, "dilution_rate": 0.0}
    for call in (lambda: ch.simulate(still, STANDIN_CHEMOSTAT_START, STANDIN_CHEMOSTAT_RUN_H),
                 lambda: ch.steady_state(still), lambda: ch.washout(still)):
        with pytest.raises(FamilyRefused, match="dilution rate above zero.*a batch"):
            call()
    spec = next(s for s in ch.specs() if s.key == "dilution_rate")
    assert "above zero" in spec.boundsReason


def test_the_store_forms_only_after_the_second_nutrient_is_exhausted():
    st = FAMILIES["storage_v1"]
    tr = st.simulate(STANDIN_STORAGE, STANDIN_STORAGE_START, None)
    times, Y = dense(tr)
    assert tr.n_exhausted_h is not None and tr.n_exhausted_h < tr.runout_h
    before = times < tr.n_exhausted_h
    assert Y[IX["Q"]][before].max() == 0.0 and Y[IX["Q"]][~before].max() > 0.0
    rich = st.simulate(STANDIN_STORAGE, STANDIN_STORAGE_RICH, 300.0)
    _, Y = dense(rich)
    share = Y[IX["Q"]] / (Y[IX["X"]] + Y[IX["Q"]])
    assert share.max() <= STANDIN_STORAGE["q_max"] * (1 + 1e-6)


def test_harvest_reads_the_hour_the_sugar_runs_out_or_an_hour_named():
    tr = batch().simulate(STANDIN_KINETICS, STANDIN_START, STANDIN_RUN_H)
    h = K.harvest(tr)
    assert h["hour"] == tr.runout_h and h["state"]["S"] == pytest.approx(K.RUN_OUT_SHARE * STANDIN_START["S"])
    at = K.harvest(tr, 6.0)
    assert at["state"]["P"] == pytest.approx(float(tr.at(6.0)[IX["P"]])) and at["how"] == "an hour a person set"
    for bad in (-1.0, STANDIN_RUN_H + 1):
        with pytest.raises(FamilyRefused, match="outside the simulation"):
            K.harvest(tr, bad)
    # A fed culture is harvested at its run's end: its sugar is fed again.
    chemo = FAMILIES["chemostat_v1"].simulate(STANDIN_CHEMOSTAT, STANDIN_CHEMOSTAT_START, STANDIN_CHEMOSTAT_RUN_H)
    assert K.harvest(chemo)["hour"] == chemo.t_final
    short = batch().simulate(STANDIN_KINETICS, STANDIN_START, 2.0)
    with pytest.raises(FamilyRefused, match="does not run out"):
        K.harvest(short)


# ── fits ───────────────────────────────────────────────────────────────


def synthetic(monkeypatch, states=("X", "S", "P")):
    p = {k: v for k, v in STANDIN_KINETICS.items()}
    tr = reference(batch(), p, STANDIN_START, float(STANDIN_FIT_TIMES[-1]), monkeypatch)
    Y = tr.sample(STANDIN_FIT_TIMES)
    return {s: (STANDIN_FIT_TIMES.copy(), Y[IX[s]].copy()) for s in states}


def fixed_for(keys):
    held = {k: v for k, v in STANDIN_KINETICS.items() if k not in keys}
    held.update({"x0": STANDIN_START["X"], "s0": STANDIN_START["S"], "p0": STANDIN_START["P"], "v0": None})
    return {k: v for k, v in held.items() if k not in keys}


def test_a_fit_of_a_synthetic_batch_recovers_its_parameters_within_one_percent(monkeypatch):
    series = synthetic(monkeypatch)
    r = batch().fit(series, {k: STANDIN_FIT_START[k] for k in STANDIN_FIT_KEYS}, fixed_for(STANDIN_FIT_KEYS))
    for k in STANDIN_FIT_KEYS:
        assert r.values[k] == pytest.approx(STANDIN_KINETICS[k], rel=0.01), (k, r.values[k])
        assert r.identified[k] and r.low[k] < r.values[k] < r.high[k], k
    assert r.rank == len(STANDIN_FIT_KEYS) and set(r.quality) == {"X", "S", "P"}
    assert all(q["r2"] > 0.999999 for q in r.quality.values())


def test_a_product_and_substrate_only_fit_reports_mu_unidentified(monkeypatch):
    monkeypatch.setattr(K, "FIT_MAX_NFEV", STANDIN_FEW_EVALUATIONS)
    series = synthetic(monkeypatch, ("S", "P"))
    keys = (*STANDIN_FIT_KEYS, "x0")
    start = {**{k: STANDIN_FIT_START[k] for k in STANDIN_FIT_KEYS}, "x0": STANDIN_START["X"] * 2}
    r = batch().fit(series, start, fixed_for(keys))
    assert r.identified["mu_max"] is False
    assert any("No biomass series: μmax is reported unidentified by rule" in n for n in r.notes)
    assert set(r.quality) == {"S", "P"}


def test_a_fit_keeps_why_each_parameter_is_unidentified(monkeypatch):
    """§3.R finding 3: a parameter was unidentified for one of several
    reasons (its interval, the Jacobian's null space, the optimizer's budget,
    the no-biomass rule), and every reader said "the interval reaches zero".
    The fit now keeps the reasons by key, and a reason the interval beside it
    contradicts is never one of them."""
    keys = (*STANDIN_FIT_KEYS, "x0")
    start = {**{k: STANDIN_FIT_START[k] for k in STANDIN_FIT_KEYS}, "x0": STANDIN_START["X"] * 2}
    with monkeypatch.context() as m:
        m.setattr(K, "FIT_MAX_NFEV", 1)  # stopped at once, at its budget
        stopped = batch().fit(synthetic(monkeypatch, ("S", "P")), start, fixed_for(keys))
    assert all("budget" in stopped.why[k] for k in keys), stopped.why
    assert "rule" in stopped.why["mu_max"]
    full = batch().fit(synthetic(monkeypatch), {k: STANDIN_FIT_START[k] for k in STANDIN_FIT_KEYS},
                       fixed_for(STANDIN_FIT_KEYS))
    assert full.why == {}
    for r in (stopped, full):
        for k in r.keys:
            assert bool(r.why.get(k)) is (not r.identified[k]), (k, r.why.get(k))
            assert ("interval" in r.why.get(k, [])) is (r.low[k] <= 0), (k, r.low[k])
            assert set(r.why.get(k, [])) <= set(K.UNIDENTIFIED), k


def test_a_fit_needs_more_readings_than_parameters():
    few = {"S": ([0.0, 1.0], [5.0, 4.0]), "P": ([0.0, 1.0], [0.0, 0.5])}
    with pytest.raises(FamilyRefused, match="cannot pin down"):
        batch().fit(few, {k: STANDIN_FIT_START[k] for k in STANDIN_FIT_KEYS}, fixed_for(STANDIN_FIT_KEYS))


# ── no number but the solver's own ─────────────────────────────────────


def test_kinetics_holds_no_number_but_its_named_settings():
    """A process number would be Rule 1 broken: every parameter value arrives
    in `p`. The only numbers are 0, 1 and 2 and the solver's settings, each a
    module-level name with its reason in SETTINGS."""
    tree = ast.parse(Path(inspect.getsourcefile(K)).read_text(encoding="utf-8"))
    named: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)) \
                    and not isinstance(node.value.value, bool):
                assert name in K.SETTINGS, f"{name} = {node.value.value} has no reason in SETTINGS"
                named.add(id(node.value))
    stray = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if id(node) in named or node.value in (0, 1, 2):
                continue
            stray.append((node.lineno, node.value))
    assert stray == [], f"numbers in kinetics.py outside its named settings: {stray}"
    assert set(K.SETTINGS) == {n.targets[0].id for n in tree.body if isinstance(n, ast.Assign)
                               and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                               and isinstance(n.value, ast.Constant) and isinstance(n.value.value, (int, float))
                               and not isinstance(n.value.value, bool)}
    assert all(r.strip() for r in K.SETTINGS.values())
    assert math.isclose(K.RTOL, 1e-6), "D5 and §3.1 set the integrator's relative tolerance"
