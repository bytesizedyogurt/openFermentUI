"""pureOS's train, built and run in the Proforma worker (OF-BLD-020 §5.2, D9,
D10, E.3‴).

Not a flowsheet on the shelf (it is not in KNOWN): the worker's `train_run`
op hands this module a train as plain JSON, every value already resolved
and named by the service (pureos/train_spec.py), with the unit classes and the
chemicals, and this module builds the BioSTEAM objects:

    the inlet      a Stream on the program's chemicals: kg/hr by chemical as
                   given (a run's stream, its temperature, pressure and
                   phase), or concentrations in g L⁻¹ over a broth flow in
                   m³/hr (a simulation's harvest, or typed), the water the
                   balance: the water that brings the mixture's volume, as
                   thermosteam computes it at the stream's temperature and
                   pressure, to the broth flow (a bracketing root search)
    the units      in order, each its catalogue class built by
                   `catalogue.build_unit` from its values; its first inlet the
                   unit before's onward outlet (the inlet for the first); a
                   recycle into it joins that inlet; a side inlet a train
                   supplies (a solvent) is the stream of kg/hr the train
                   names, one the unit sizes itself (a buffer, air, fuel) an
                   empty stream; every outlet a stream named
                   `<unit id>_<outlet>`
    the system     `bst.System.from_units`, which finds every recycle loop in
                   the units' connections; simulated whole

A unit that cannot run refuses the train in words naming the unit and
BioSTEAM's own error. BIOSTEAM IS IMPORTED AT THE TOP OF THIS FILE, so it runs
in the worker alone (test_workers holds flowsheets/ to that). The in-house
classes reach it from the worker (`unit_class`), never by import here.

Rule 1: no number in this file but zero and one. Every value is the
service's, named in the run's basis; the water is a balance; the rest is
BioSTEAM's own.
"""
from __future__ import annotations

import re
from importlib.metadata import version
from typing import Any, Callable

import biosteam as bst

from ..pureos import catalogue

ONWARD, WASTE, RECYCLE = "onward", "waste", "recycle:"
INLET_ID = "inlet"
# BioSTEAM stamps an error with the object that raised it, as
# `<Class: ID>`, coloured for a terminal.
_STAMP = re.compile(r"<(?P<cls>\w+): (?P<id>[A-Za-z][A-Za-z0-9_]*)>")
_COLOUR = re.compile(r"\x1b\[[0-9;]*m")


class Refused(ValueError):
    """The train cannot be built or run here, in words (the worker's error
    names the class, so the service reads it as the worker's refusal)."""


def stream_id(unit_id: str, port: str) -> str:
    """A stream's id, from its unit and its port's name: BioSTEAM's ids take
    no dash."""
    return f"{unit_id}_{port.replace('-', '_')}"


def _said(e: BaseException) -> str:
    return _COLOUR.sub("", f"{type(e).__name__}: {e}").strip()


def inlet_stream(chems: Any, inlet: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """The train's inlet as a Stream, and what was built: its flows and, for
    concentrations over a broth flow, the water the balance gave and how."""
    T, P, phase = inlet.get("T"), inlet.get("P"), str(inlet.get("phase") or "l")
    kw = {k: float(v) for k, v in (("T", T), ("P", P)) if v is not None}
    s = bst.Stream(INLET_ID, thermo=chems, phase=phase, units="kg/hr", **kw)
    built: dict[str, Any] = {"water": None, "waterNote": None}
    flows = inlet.get("flows")
    if flows is not None:
        for chem, kg in flows.items():
            s.imass[chem] = float(kg)
    else:
        q = float(inlet["brothFlow"])
        balance = str(inlet.get("balance") or catalogue.SOLVENT)
        for chem, c in (inlet.get("concentrations") or {}).items():
            s.imass[chem] = float(c) * q  # g L⁻¹ is kg m⁻³
        water = _balance(s, balance, q)
        built.update(water=water, waterNote=(
            f"{balance} is the balance: {water:.6g} kg/hr, the {balance} that brings the mixture's volume, as "
            f"thermosteam {version('thermosteam')} computes it at {s.T:.6g} K and {s.P:.6g} Pa, to the broth flow"))
    built.update(flows={i: float(m) for i, m in zip(s.chemicals.IDs, s.mass) if m}, T=float(s.T), P=float(s.P),
                 phase=str(s.phase), volume=float(s.F_vol))
    return s, built


def _balance(s: Any, chem: str, q: float) -> float:
    """The mass of `chem` that brings the stream's volume to q m³/hr."""
    from scipy.optimize import brentq

    def gap(m: float) -> float:
        s.imass[chem] = m
        return float(s.F_vol) - q

    if gap(0) >= 0:
        raise Refused(f"the inlet's components other than {chem} take {s.F_vol:.6g} m³/hr by thermosteam's own "
                      f"volumes, at or above the broth flow, {q:.6g} m³/hr: no {chem} balances it")
    # The chemical alone at the whole broth flow: more than enough, since the
    # other components take room of their own.
    high = q * float(s.chemicals[chem].rho(s.phase, s.T, s.P))
    if gap(high) <= 0:
        raise Refused(f"{chem} at the whole broth flow does not fill it by thermosteam's volumes: the inlet cannot "
                      "be balanced")
    m = float(brentq(gap, 0, high))
    s.imass[chem] = m
    return m


class Built:
    """The train's BioSTEAM objects: the inlet, the units in order, every
    outlet stream by unit and port, and the system."""

    def __init__(self, spec: dict[str, Any], unit_class: Callable[[str], tuple[Any, Any]], chems: Any,
                 upstream: Any = None) -> None:
        self.spec = spec
        # OF-BLD-020 §6.1: `custom_train_v1` hands its fermenter's beer in as
        # the train's inlet (`upstream`) and makes the system itself, of the
        # fermenter and these units together; else the train builds its own
        # inlet from the spec and its own system.
        if upstream is None:
            self.inlet, self.inlet_built = inlet_stream(chems, spec["inlet"])
        else:
            self.inlet, self.inlet_built = upstream, None
        units = list(spec["units"])
        self.outlets: dict[str, dict[str, Any]] = {}
        self.entries: dict[str, Any] = {}
        # Every outlet first, so a recycle can join a unit built before the
        # unit it leaves.
        for u in units:
            e, _ = unit_class(u["type"])
            self.entries[u["id"]] = e
            self.outlets[u["id"]] = {p.name: bst.Stream(stream_id(u["id"], p.name)) for p in e.ports if p.side == "out"}
        recycles: dict[str, list[Any]] = {}
        for u in units:
            for port, route in (u.get("outlets") or {}).items():
                if route.startswith(RECYCLE):
                    recycles.setdefault(route[len(RECYCLE):], []).append(self.outlets[u["id"]][port])
        self.units: list[Any] = []
        upstream = self.inlet
        for u in units:
            e, cls = unit_class(u["type"])
            ins: list[Any] = []
            for p in (p for p in e.ports if p.side == "in"):
                if p.source == "upstream":
                    ins.append(upstream)
                    ins.extend(recycles.get(u["id"], []))
                elif p.source == "side":
                    side = bst.Stream(stream_id(u["id"], p.name), units="kg/hr")
                    for chem, kg in ((u.get("sides") or {}).get(p.name) or {}).items():
                        side.imass[chem] = float(kg)
                    ins.append(side)
                else:  # the unit sizes it
                    ins.append(bst.Stream(stream_id(u["id"], p.name)))
            outs = [self.outlets[u["id"]][p.name] for p in e.ports if p.side == "out"]
            try:
                unit = catalogue.build_unit(u["type"], cls, u["id"], ins, outs, dict(u.get("values") or {}))
            except Exception as ex:
                raise Refused(f"unit {u['id']} ({u['type']}, {cls.__name__}) could not be built: BioSTEAM said: "
                              f"{_said(ex)}") from None
            self.units.append(unit)
            onward = [name for name, route in (u.get("outlets") or {}).items() if route == ONWARD]
            upstream = self.outlets[u["id"]][onward[0]]
        self.product = upstream
        self.system = bst.System.from_units(spec["system"], units=self.units) if self.inlet_built is not None else None

    def simulate(self) -> None:
        """The whole train, recycles converged by BioSTEAM; a failure names
        the unit BioSTEAM stamped on its error, and BioSTEAM's words."""
        try:
            self.system.simulate()
        except Exception as ex:
            said = _said(ex)
            ids = {u.ID: u for u in self.units}
            hit = next((m for m in _STAMP.finditer(said) if m.group("id") in ids), None)
            if hit is not None:
                u = ids[hit.group("id")]
                kind = next((x["type"] for x in self.spec["units"] if x["id"] == u.ID), "")
                raise Refused(f"unit {u.ID} ({kind}, {type(u).__name__}) did not converge: BioSTEAM said: "
                              f"{_STAMP.sub('', said).strip(' :')}") from None
            raise Refused(f"the train did not converge as a whole (its recycles, or a unit BioSTEAM did not name): "
                          f"BioSTEAM said: {said}") from None

    def costs(self) -> list[dict[str, Any]]:
        """Each unit's purchase and installed cost as BioSTEAM gives them, its
        purchase cost by item, and its utility cost."""
        return [{"unit": u.ID, "unitClass": type(u).__name__, "purchaseCost": float(u.purchase_cost),
                 "installedCost": float(u.installed_cost),
                 "items": {str(k): float(v) for k, v in dict(u.purchase_costs).items()},
                 "utilityCost": float(u.utility_cost or 0)} for u in self.units]

    def outlet_ids(self) -> dict[str, dict[str, str]]:
        return {uid: {name: s.ID for name, s in ports.items()} for uid, ports in self.outlets.items()}


def read_unit(type_id: str, unit: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """A built unit's values by catalogue key, as the unit holds them (a
    shelf flowsheet's unit a train reads, §5.2): the class's own attribute for
    each, its private one where the class keeps it under a leading
    underscore; a split per chemical of the unit's set; the light and heavy
    keys from LHK; an evaporator's pressures per effect. A value the unit
    holds as None, or that cannot be read as a number or a word, is named in
    `unread` with why, and the class's own default stands for it."""
    e = catalogue.entry(type_id)
    values: dict[str, Any] = {}
    unread: dict[str, str] = {}

    def held(name: str) -> Any:
        for attr in (name, f"_{name}"):
            try:
                return getattr(unit, attr)
            except Exception:  # noqa: BLE001 (a property that cannot be read now is said so)
                continue
        raise AttributeError(name)

    for p in e.params:
        try:
            if p.key in ("light_key", "heavy_key"):
                lhk = held("LHK")
                values[p.key] = str(lhk[0] if p.key == "light_key" else lhk[1])
                continue
            if p.per == "component":
                got = held(p.bst)
                for chem, share in zip(unit.chemicals.IDs, list(got)):
                    values[f"{p.key}{catalogue.SEP}{chem}"] = float(share)
                continue
            if p.per == "effect":
                pressures = list(held(p.bst))
                for n, x in enumerate(pressures, 1):
                    values[f"{p.key}{catalogue.SEP}{n}"] = float(x)
                values["effects"] = float(len(pressures))
                continue
            if p.key == "effects":
                continue
            v = held(p.bst)
        except Exception as ex:  # noqa: BLE001
            unread[p.key] = f"{type(unit).__name__} {unit.ID} holds no readable {p.bst} ({type(ex).__name__})"
            continue
        if v is None:
            unread[p.key] = f"{type(unit).__name__} {unit.ID} holds {p.bst} as None: the class decides it"
        elif isinstance(v, bool):
            values[p.key] = "true" if v else "false"
        elif isinstance(v, (int, float)):
            values[p.key] = float(v)
        elif isinstance(v, str):
            values[p.key] = v
        else:
            unread[p.key] = f"{type(unit).__name__} {unit.ID} holds {p.bst} as a {type(v).__name__}, not a number or a word"
    return values, unread
