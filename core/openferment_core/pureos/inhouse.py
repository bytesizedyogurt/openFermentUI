"""The three unit types pureOS's catalogue needs and BioSTEAM lacks
(OF-BLD-020 §5.1, D8).

    Ultrafiltration   a membrane concentrates the feed by a factor and washes
                      the retentate with diafiltration buffer; each component
                      passes by its sieving coefficient
    CellDisruption    a homogeniser or bead mill breaks the cells over a
                      number of passes; the product they hold (the inlet's
                      solid phase) moves into the liquid by first-order release
    Chromatography    a placeholder column: declared recovery and purity, the
                      bed and the elution buffer sized by the binding capacity
                      and the elution volumes; CADET replaces it

Each is a `bst.Unit` whose `_run` is a split; `_cost` is BioSTEAM's `Unit`
default, so each costs nothing until a correlation with a source is added
(the catalogue says *no cost model*), and `_design` records only what its
parameters size (the membrane's area, the column's bed). Every parameter is
the constructor's, with None as its default: a person or a record sets it
(catalogue.py says which, and its specs carry no library default but what
None reads as here). A required one left None is refused in words when the
unit runs.

BIOSTEAM IS IMPORTED AT THE TOP OF THIS FILE, so it runs in the Proforma
worker alone (E.3‴): the worker imports it to build a unit, and no service
module imports it (test_workers holds both).

No number here but zero and one: each equation is written with its
parameters, and its words are in the catalogue's notes.
"""
from __future__ import annotations

import math
from typing import Any

import biosteam as bst
import numpy as np
import thermosteam as tmo

from .catalogue import MODES, SOLVENT

__all__ = ("Ultrafiltration", "CellDisruption", "Chromatography")


def _required(unit: Any, **given: Any) -> None:
    missing = [k for k, v in given.items() if v is None]
    if missing:
        raise ValueError(f"{type(unit).__name__} {unit.ID} needs {', '.join(missing)}, which no record or person set")


def _phases_of(*streams: Any) -> tuple[str, ...]:
    """Every phase the streams carry, with liquid and solid, in order."""
    found = {"l", "s"}
    for s in streams:
        found |= set(getattr(s, "phases", None) or (s.phase,))
    return tuple(sorted(found))


def _split_from(unit: Any, streams: list[Any], split: np.ndarray) -> None:
    """Mix `streams` and split the mixture between the unit's two outlets by
    `split` (each chemical's share to outlet 0), phases kept."""
    mixed = tmo.MultiStream(None, thermo=unit.thermo, phases=_phases_of(*streams))
    mixed.mix_from(streams)
    mixed.split_to(*unit.outs, split)


class Ultrafiltration(bst.Unit):
    """Ultrafiltration, then diafiltration at constant volume.

    ins:  [0] feed, [1] diafiltration buffer (water, sized here)
    outs: [0] retentate, [1] permeate

    sieving_coefficient  {chemical: S}, the share of a component's
                         concentration that passes the membrane; one for
                         every chemical the feed carries but water
    concentration_factor CF, the feed's water over the retentate's (at least one)
    diavolumes           N, retentate volumes of buffer washed through after
                         concentrating; None reads as none
    flux                 J, permeate litres per square metre per hour, which
                         sizes the membrane; None sizes none

    A component's share kept in the retentate is CF^(−S)·e^(−N·S): batch
    concentration by CF (the retentate keeps CF^(−S) of it), then N
    diavolumes (e^(−N·S)). The retentate keeps the feed's water over CF; the
    buffer, N times that water, leaves in the permeate with everything else.
    """

    line = "Ultrafiltration"
    _N_ins = 2
    _N_outs = 2
    _units = {"Membrane area": "m2"}

    def _init(self, sieving_coefficient=None, concentration_factor=None, diavolumes=None, flux=None):
        self.sieving_coefficient = sieving_coefficient
        self.concentration_factor = concentration_factor
        self.diavolumes = diavolumes
        self.flux = flux

    def _run(self):
        feed, buffer = self.ins
        _required(self, sieving_coefficient=self.sieving_coefficient, concentration_factor=self.concentration_factor)
        CF = float(self.concentration_factor)
        if not CF >= 1:
            raise ValueError(f"Ultrafiltration {self.ID}: a concentration factor is at least one, the volume fed; "
                             f"{CF:g} is not")
        N = float(self.diavolumes or 0)
        S = dict(self.sieving_coefficient)
        kept_water = feed.imass[SOLVENT] / CF
        buffer.empty()
        buffer.phase = "l"
        buffer.T, buffer.P = feed.T, feed.P
        buffer.imass[SOLVENT] = N * kept_water
        water_in = feed.imass[SOLVENT] + buffer.imass[SOLVENT]
        split = np.zeros(self.chemicals.size)
        for n, ID in enumerate(self.chemicals.IDs):
            if not feed.mol[n] and ID != SOLVENT:
                continue
            if ID == SOLVENT:
                split[n] = kept_water / water_in if water_in else 0
                continue
            if ID not in S:
                raise ValueError(f"Ultrafiltration {self.ID} needs the sieving coefficient of {ID}, which the feed "
                                 "carries")
            s = float(S[ID])
            split[n] = CF ** (-s) * math.exp(-N * s)
        _split_from(self, [feed, buffer], split)

    def _design(self):
        if self.flux is not None:
            self.design_results["Membrane area"] = self.outs[1].get_total_flow("L/hr") / float(self.flux)


class CellDisruption(bst.Unit):
    """Cell disruption by homogeniser or bead mill.

    ins:  [0] the broth with the cells
    outs: [0] the lysate

    product_ID  the chemical the cells hold, as the inlet's solid phase (BioSTEAM's
                Unit keeps `product` for its outlet)
    release   k, the share of the product still in the cells one pass releases
    passes    N, how many times the broth goes through

    First-order release: after N passes the share released is 1 − (1 − k)^N,
    moved from the outlet's solid phase (the cells) to its liquid. A product
    the inlet carries in no solid phase is already in the liquid: nothing is
    released, and the design says so.
    """

    line = "Cell disruption"
    _N_ins = 1
    _N_outs = 1
    _units = {"Product released": "kg/hr"}

    def _init(self, product_ID=None, release=None, passes=None):
        self.product_ID = product_ID
        self.release = release
        self.passes = passes

    def _run(self):
        feed, = self.ins
        out, = self.outs
        _required(self, product_ID=self.product_ID, release=self.release, passes=self.passes)
        k, N = float(self.release), float(self.passes)
        if not 0 <= k <= 1:
            raise ValueError(f"CellDisruption {self.ID}: a release per pass is a share, between none and the whole")
        out.phases = _phases_of(feed)
        out.mix_from([feed])
        held = float(out.imol["s", self.product_ID])
        released = held * (1 - (1 - k) ** N)
        out.imol["s", self.product_ID] = held - released
        out.imol["l", self.product_ID] += released
        self._released = (1 - (1 - k) ** N, released, held)

    def _design(self):
        share, released, held = getattr(self, "_released", (None, 0, 0))
        self.design_results["Share released"] = share if held else 0
        self.design_results["Product released"] = released * self.chemicals[self.product_ID].MW


class Chromatography(bst.Unit):
    """A chromatography step, declared until a column model replaces it.

    ins:  [0] the load, [1] the elution buffer (water, sized here)
    outs: [0] the eluate, [1] the flow-through

    mode              one of MODES; the balance is the same for each
    product_ID        the chemical the column binds and elutes
    recovery          R, the share of the product loaded that leaves in the eluate
    purity            P, the product's share of the eluate but its water
    binding_capacity  the product a litre of bed holds (g L⁻¹, which is kg m⁻³)
    elution_volumes   bed volumes of buffer that elute it

    The bed per hour of loading is the product loaded over the binding
    capacity; the buffer is the elution volumes times that bed, and all of it
    leaves in the eluate. Every chemical but the product and water follows the
    product by one share, the one that makes the eluate's purity P (all of
    them when the load is purer than P already, said in the design).
    """

    line = "Chromatography"
    _N_ins = 2
    _N_outs = 2
    _units = {"Bed volume per hour of loading": "m3/hr", "Elution buffer": "m3/hr"}

    def _init(self, mode=None, product_ID=None, recovery=None, purity=None, binding_capacity=None,
              elution_volumes=None):
        self.mode = mode
        self.product_ID = product_ID
        self.recovery = recovery
        self.purity = purity
        self.binding_capacity = binding_capacity
        self.elution_volumes = elution_volumes

    def _run(self):
        load, buffer = self.ins
        _required(self, mode=self.mode, product_ID=self.product_ID, recovery=self.recovery, purity=self.purity,
                  binding_capacity=self.binding_capacity, elution_volumes=self.elution_volumes)
        if self.mode not in MODES:
            raise ValueError(f"Chromatography {self.ID}: a mode is one of {', '.join(MODES)}; {self.mode!r} is not")
        R, P = float(self.recovery), float(self.purity)
        if not (0 <= R <= 1 and 0 < P <= 1):
            raise ValueError(f"Chromatography {self.ID}: recovery is a share, and purity a share above none")
        loaded = float(load.imass[self.product_ID])
        bed = loaded / float(self.binding_capacity)
        buffer.empty()
        buffer.phase = "l"
        buffer.T, buffer.P = load.T, load.P
        buffer.ivol[SOLVENT] = float(self.elution_volumes) * bed
        others = float(load.F_mass) - loaded - float(load.imass[SOLVENT])
        wanted = R * loaded * (1 - P) / P
        follow = min(1, wanted / others) if others > 0 else 0
        water_in = float(load.imass[SOLVENT] + buffer.imass[SOLVENT])
        split = np.full(self.chemicals.size, follow)
        split[self.chemicals.index(self.product_ID)] = R
        split[self.chemicals.index(SOLVENT)] = buffer.imass[SOLVENT] / water_in if water_in else 0
        _split_from(self, [load, buffer], split)
        self._bed = (bed, float(buffer.F_vol), wanted > others)

    def _design(self):
        bed, buffer, short = getattr(self, "_bed", (0, 0, False))
        eluate = self.outs[0]
        dry = float(eluate.F_mass) - float(eluate.imass[SOLVENT])
        d = self.design_results
        d["Bed volume per hour of loading"] = bed
        d["Elution buffer"] = buffer
        d["Eluate purity"] = float(eluate.imass[self.product_ID]) / dry if dry else 0
        d["Purity asked for is below the load's"] = "yes" if short else "no"
