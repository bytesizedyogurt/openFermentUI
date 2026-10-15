"""The geneOS worker: flux balance analysis, in a process of its own
(OF-BLD-014 §6.2, Appendix 2).

The only module in openferment_core that imports `cobra` (test_workers holds
it to that). It loads the shelf's models on first use and keeps them warm,
applies the add-on route where a model lacks one, and answers five ops:

    ping       answered by `serve`
    describe   counts of reactions, metabolites and genes; the growth
               reaction; which of the shelf's sugars the model can take up
    ceiling    the most product from one feed (Appendix 2's procedure)
    frontier   the production envelope over twelve growth rates
    mix        the ceiling across eleven mixtures of two sugars at equal carbon

A substrate the model has no uptake reaction for is a finding, said in words,
with no number. Every number returned is cobra's, on the model as its file
publishes it, with the substrate's uptake opened at the convention rate.
"""
from __future__ import annotations

from typing import Any

import cobra
from cobra import Metabolite, Model, Reaction
from cobra.flux_analysis import production_envelope
from cobra.io import load_model, read_sbml_model

from .. import geneos_models as shelf
from . import serve

_LOADED: dict[str, Model] = {}
# Each model's counts as its file publishes them, and what this worker adds
# to it (an add-on route, a demand on the product), read at load.
_PUBLISHED: dict[str, dict[str, int]] = {}
_ADDED: dict[str, list[str]] = {}


class Refused(ValueError):
    """The request cannot be computed, in words."""


# ── models ─────────────────────────────────────────────────────────────


def build_toy() -> Model:
    """The toy network the offline tests and fixtures run on. STAND-IN, not a
    published model: three metabolites and four reactions, worked by hand.

        EX_glc__D_e   glc__D_e <=>               (the feed)
        SPLIT         glc__D_e --> 2 a_c
        GROWTH        a_c -->                    (the objective)
        PHAC          a_c --> phb_c

    The worker adds the demand on phb_c. From glucose at 10, the most product
    is 20: 2 mol per mol, and 2 × 86.09 / 180.156 g per g."""
    m = Model("toy")
    glc = Metabolite("glc__D_e", formula="C6H12O6", compartment="e", name="glucose")
    a = Metabolite("a_c", formula="C3H6O3", compartment="c", name="toy intermediate")
    phb = Metabolite("phb_c", formula="C4H6O2", compartment="c", name="PHB repeat unit")
    ex = Reaction("EX_glc__D_e", lower_bound=-10.0, upper_bound=1000.0)
    ex.add_metabolites({glc: -1})
    split = Reaction("SPLIT", lower_bound=0.0, upper_bound=1000.0)
    split.add_metabolites({glc: -1, a: 2})
    growth = Reaction("GROWTH", lower_bound=0.0, upper_bound=1000.0)
    growth.add_metabolites({a: -1})
    phac = Reaction("PHAC", lower_bound=0.0, upper_bound=1000.0)
    phac.add_metabolites({a: -1, phb: 1})
    m.add_reactions([ex, split, growth, phac])
    m.objective = "GROWTH"
    return m


def apply_addon(model: Model, addon: dict[str, Any]) -> list[str]:
    """Add the route's metabolites and reactions; refuse it whole when an
    added reaction does not balance. Returns the ids of the reactions added."""
    for spec in addon["metabolites"]:
        if spec["id"] not in model.metabolites:
            model.add_metabolites([Metabolite(spec["id"], formula=spec["formula"], charge=spec["charge"],
                                              name=spec["name"], compartment="c")])
    added: list[Reaction] = []
    for spec in addon["reactions"]:
        if spec.get("ifMissing") and spec["id"] in model.reactions:
            continue
        r = Reaction(spec["id"], lower_bound=spec["lowerBound"], upper_bound=1000.0)
        model.add_reactions([r])
        r.reaction = spec["equation"]
        added.append(r)
    for r in added:
        unbalanced = r.check_mass_balance()
        if unbalanced:
            model.remove_reactions(added)
            raise Refused(f"the add-on {addon['id']} does not balance: {r.id} leaves {unbalanced}")
    return [r.id for r in added]


def demand(model: Model, metabolite: str) -> Reaction:
    rid = f"DM_{metabolite}"
    if rid in model.reactions:
        return model.reactions.get_by_id(rid)
    if metabolite not in model.metabolites:
        raise Refused(f"the model has no metabolite {metabolite}")
    return model.add_boundary(model.metabolites.get_by_id(metabolite), type="demand")


def load(model_id: str, path: str | None = None) -> Model:
    if model_id in _LOADED:
        return _LOADED[model_id]
    added: list[str] = []
    if model_id == "toy":
        m = build_toy()
        _PUBLISHED[model_id] = _counts(m)
    else:
        entry = shelf.SHELF.get(model_id)
        if entry is None:
            raise Refused(f"there is no model {model_id} on the shelf")
        if entry.bundled:
            m = load_model(entry.bundled)
        else:
            if not path:
                raise Refused(f"{model_id} is read from a fetched file, and no path was given")
            m = read_sbml_model(path)
        _PUBLISHED[model_id] = _counts(m)
        if entry.addon:
            added += apply_addon(m, shelf.ADDONS[entry.addon])
    # The demand on each product is added here, once, where the file lacks
    # it. RehMBEL1391 exports PHB through PHBt and carries no DM_phb_c.
    for prod in shelf.PRODUCTS.values():
        rid = f"DM_{prod['metabolite']}"
        if prod["metabolite"] in m.metabolites and rid not in m.reactions:
            demand(m, prod["metabolite"])
            added.append(rid)
    _ADDED[model_id] = added
    _LOADED[model_id] = m
    return m


def _counts(model: Model) -> dict[str, int]:
    return {"reactions": len(model.reactions), "metabolites": len(model.metabolites), "genes": len(model.genes)}


def growth_reaction(model: Model) -> str:
    """The reaction the model file sets as its objective."""
    ids = [r.id for r in model.reactions if r.objective_coefficient != 0]
    if len(ids) != 1:
        raise Refused(f"the model's objective is not one reaction ({', '.join(ids) or 'none'})")
    return ids[0]


# ── the procedure (Appendix 2) ─────────────────────────────────────────


def close_carbon(model: Model) -> None:
    """Close every uptake whose metabolite carries carbon or no formula."""
    for ex in model.exchanges:
        m = next(iter(ex.metabolites))
        if ex.lower_bound < 0 and (not m.formula or "C" in m.elements):
            ex.lower_bound = 0.0


def exchange_for(model: Model, substrate: str) -> str | None:
    sub = shelf.SUBSTRATES.get(substrate)
    if sub is None:
        raise Refused(f"there is no substrate {substrate}; the shelf knows {', '.join(shelf.SUBSTRATES)}")
    return sub["exchange"] if sub["exchange"] in model.reactions else None


def no_uptake(model_id: str, substrate: str) -> dict[str, Any]:
    return {"finding": f"this reconstruction has no uptake reaction for {substrate}", "modelId": model_id, "substrate": substrate}


def _optimum(model: Model, opens: dict[str, float], dm: Reaction) -> tuple[float, str]:
    with model:
        close_carbon(model)
        for ex_id, rate in opens.items():
            model.reactions.get_by_id(ex_id).lower_bound = -rate
        model.objective = dm
        sol = model.optimize()
        if sol.status != "optimal":
            raise Refused(f"the solver answered {sol.status}, not optimal")
        return float(sol.objective_value), str(sol.status)


def ceiling(model: Model, model_id: str, product: str, substrate: str, uptake: float = shelf.UPTAKE) -> dict[str, Any]:
    prod = shelf.PRODUCTS.get(product)
    if prod is None:
        raise Refused(f"there is no product {product}; the shelf knows {', '.join(shelf.PRODUCTS)}")
    ex = exchange_for(model, substrate)
    if ex is None:
        return no_uptake(model_id, substrate)
    dm = demand(model, prod["metabolite"])
    flux, status = _optimum(model, {ex: uptake}, dm)
    sub = shelf.SUBSTRATES[substrate]
    return {
        "modelId": model_id, "product": product, "substrate": substrate, "exchange": ex,
        "uptake": uptake, "flux": flux, "molPerMol": flux / uptake,
        "gPerG": flux * prod["molarMass"] / (uptake * sub["molarMass"]),
        "solver": model.solver.interface.__name__.split(".")[-1], "status": status,
    }


def frontier(model: Model, model_id: str, product: str, substrate: str, uptake: float = shelf.UPTAKE,
             points: int = shelf.FRONTIER_POINTS) -> dict[str, Any]:
    prod = shelf.PRODUCTS.get(product)
    if prod is None:
        raise Refused(f"there is no product {product}")
    ex = exchange_for(model, substrate)
    if ex is None:
        return no_uptake(model_id, substrate)
    dm = demand(model, prod["metabolite"])
    growth = growth_reaction(model)
    sub = shelf.SUBSTRATES[substrate]
    with model:
        close_carbon(model)
        model.reactions.get_by_id(ex).lower_bound = -uptake
        table = production_envelope(model, reactions=[model.reactions.get_by_id(growth)], objective=dm, points=points)
    rows = []
    for _, row in table.iterrows():
        top = float(row["flux_maximum"])
        rows.append({
            "growth": float(row[growth]),
            "flux": top,
            "gPerG": top * prod["molarMass"] / (uptake * sub["molarMass"]),
        })
    return {"modelId": model_id, "product": product, "substrate": substrate, "exchange": ex, "uptake": uptake,
            "growthReaction": growth, "points": sorted(rows, key=lambda r: r["growth"])}


def mix(model: Model, model_id: str, product: str, a: str, b: str, uptake: float = shelf.UPTAKE,
        points: int = shelf.MIX_POINTS) -> dict[str, Any]:
    """The ceiling at `points` proportions of two sugars, from all of `a` at
    the convention uptake to all of `b` at the same total carbon."""
    prod = shelf.PRODUCTS.get(product)
    if prod is None:
        raise Refused(f"there is no product {product}")
    ex_a, ex_b = exchange_for(model, a), exchange_for(model, b)
    for sub, ex in ((a, ex_a), (b, ex_b)):
        if ex is None:
            return no_uptake(model_id, sub)
    sa, sb = shelf.SUBSTRATES[a], shelf.SUBSTRATES[b]
    carbon = uptake * sa["carbons"]
    dm = demand(model, prod["metabolite"])
    rows = []
    for i in range(points):
        share = 1 - i / (points - 1)  # the share of the carbon fed as `a`
        rate_a = carbon * share / sa["carbons"]
        rate_b = carbon * (1 - share) / sb["carbons"]
        opens = {k: v for k, v in ((ex_a, rate_a), (ex_b, rate_b)) if v > 0}
        flux, _ = _optimum(model, opens, dm)
        grams = rate_a * sa["molarMass"] + rate_b * sb["molarMass"]
        rows.append({"shareA": share, "uptakeA": rate_a, "uptakeB": rate_b, "flux": flux,
                     "gPerG": flux * prod["molarMass"] / grams})
    return {"modelId": model_id, "product": product, "a": a, "b": b, "carbon": carbon, "points": rows}


def describe(model: Model, model_id: str) -> dict[str, Any]:
    published = _PUBLISHED.get(model_id) or _counts(model)
    return {
        "modelId": model_id,
        # As the file publishes them; `added` names what this worker adds.
        **published,
        "added": _ADDED.get(model_id, []),
        "growthReaction": growth_reaction(model),
        "substrates": {s: exchange_for(model, s) is not None for s in shelf.SUBSTRATES},
        "products": {p: v["metabolite"] in model.metabolites for p, v in shelf.PRODUCTS.items()},
        "cobra": cobra.__version__,
    }


# ── the ops ────────────────────────────────────────────────────────────


def _model(args: dict[str, Any]) -> tuple[Model, str]:
    model_id = str(args.get("modelId", ""))
    return load(model_id, args.get("path")), model_id


def _op_describe(args):
    m, mid = _model(args)
    return describe(m, mid)


def _op_ceiling(args):
    m, mid = _model(args)
    return ceiling(m, mid, str(args["product"]), str(args["substrate"]))


def _op_frontier(args):
    m, mid = _model(args)
    return frontier(m, mid, str(args["product"]), str(args["substrate"]))


def _op_mix(args):
    m, mid = _model(args)
    return mix(m, mid, str(args["product"]), str(args["a"]), str(args["b"]))


HANDLERS = {"describe": _op_describe, "ceiling": _op_ceiling, "frontier": _op_frontier, "mix": _op_mix}

if __name__ == "__main__":
    serve(HANDLERS, name="geneos")
