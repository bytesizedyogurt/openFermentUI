"""pureOS's unit catalogue (OF-BLD-020 §5.1, D8, E.3‴, Appendix 2 §B).

A train is built from unit types, and each unit type is one entry here: a
BioSTEAM class, or one of three in-house `bst.Unit` subclasses BioSTEAM lacks
(pureos/inhouse.py: ultrafiltration and diafiltration, cell disruption, a
chromatography step), with every parameter its constructor takes either
declared as a `ParameterSpec` or named in `notOffered` with why. An entry's
id is the vocabulary's (schema/vocabulary.yaml `unitOperations`, read by
`validate.unit_operations`); its stage
is one of `STAGES`; `insOuts` says what each inlet and outlet is, in words,
and which outlet goes on with the product by default.

THIS MODULE IS DATA, AND IMPORTS NO BIOSTEAM AT ITS TOP (E.3‴). The service
lists the catalogue from it (`listing`, GET /api/pureos/catalogue) and reads
every declaration statically (`static_specs`, which `params --check` holds to
a written bounds reason). What only BioSTEAM knows — each class's defaults,
the choices its cost tables list, what its setters refuse — is read by the
functions under "the worker side", which import BioSTEAM inside themselves
and run in the Proforma worker alone (`catalogue_specs` and
`catalogue_unit_check` in workers/proforma_worker.py, which hands them the
class and the chemicals). The service asks the worker through the JSON
contract (`worker_specs`, cached for the process's life, as
`vessel.worker_specs` is) and serves the answer as `UnitSpecs`.

THE CATALOGUE COPIES BIOSTEAM (D8). A parameter's key is BioSTEAM's own name
for it, and where it is not (`light_key` and `heavy_key` are BioSTEAM's
`LHK`; `effects` is how many pressures BioSTEAM's `P` holds;
`partition_coefficient` reaches a mixer-settler through its `settler_data`),
its note and its `UnitParamMap` say which. Its default is read from the
class's code at import: the signature, then a `_default_<name>` or
`<name>_default` the class reads where the signature leaves the name empty
or falsy, then a literal its `_init` puts in place of None. None is never
retyped as a number. A parameter the class takes per component (a split, a
sieving coefficient, a partition coefficient) is declared once as a template
whose key a train expands per chemical as `<key>.<chemical>` (`expand`); the
multi-effect evaporator's pressures are expanded per effect as `P.<n>`.

WHERE A VALUE COMES FROM. A parameter with a BioSTEAM default takes it
(`library-default`) unless a person types another (`assumption`, under their
name, D3); one that BioSTEAM requires and gives no default for (a split, the
keys and the reflux of a column, the evaporator's pressures, the number of
extraction stages) waits for a record of its ontology field where Appendix 2
§B names one, or a person. The ontology fields this step adds for that are
`step_recovery`, `product_purity`, `partition_coefficient`,
`sieving_coefficient` and `cake_moisture` (schema/fields.yaml). Binding a
record to a unit of a train, by the train's product and chemicals, is §5.2's
(`kwargs_of` and `expand` are what its builder calls); here the specs say
where a value would come from.

WHAT DID NOT ENTER (Part A: "a unit that does not converge on its own
defaults does not enter the catalogue"). `LEFT_OUT` names each class the
document lists that does not, with BioSTEAM's own words: a sim test holds
that it still fails, so it is let in the day it runs.

Rule 1 holds here: no number in this file but structural ones (zero, one, and
the bounds that are physical limits, each with its reason in words). A
default is BioSTEAM's, read; a value is a record's, a person's, or the
class's own.
"""
from __future__ import annotations

import json
import re
import sys
import threading
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable, Literal

from .. import params
from ..models import (
    BasisSource,
    NotOffered,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    UnitDefault,
    UnitNeed,
    UnitParamMap,
    UnitPort,
    UnitSpecs,
    UnitType,
)

# Where a unit sits in a train, fermenter to product (the document's list).
STAGES = ("harvest", "disruption", "clarification", "concentration", "capture", "polish", "formulation", "drying",
          "utility")
# The chromatography placeholder's modes, as words, and the vocabulary id each
# stands for (schema/vocabulary.yaml): `mode` maps them.
MODES = ("iex", "hic", "imac", "affinity", "sec", "mixed-mode")
MODE_VOCABULARY = {"iex": "iex", "hic": "hic", "imac": "imac", "affinity": "affinity-custom", "sec": "sec",
                   "mixed-mode": "mixed-mode"}
# The solvent a broth's units move: the chemical a per-component template
# leaves out where the class reads it from another parameter (ultrafiltration
# sets the retentate's water by its concentration factor).
SOLVENT = "Water"
# How a template key is expanded.
SEP = "."
# The mixer-settler's model that reads partition coefficients, as its _init
# compares it (lowercased).
PARTITION_MODEL = "partition coefficients"
# A flash is set by a pair of its four conditions (Flash's docstring: "You may
# only specify two of the following parameters"): structural, not a quantity.
PAIR = 2


class CatalogueUnknown(LookupError):
    """An id the catalogue does not hold: a 404."""


# ── the declarations ───────────────────────────────────────────────────

# The words of a bound (D4). Every one is a physical limit or says there is
# none.
_SPLIT = "a physical limit: a share of a component's flow, between none and the whole"
_SHARE = "a physical limit: a share lies between none and the whole"
_WORDS = "a choice of words: it has no bounds"
_ABS_T = "a physical limit: a temperature in kelvin is above none"
_ABS_P = "a physical limit: an absolute pressure is above none"
_COUNT = "a physical limit: a whole number of them, at least one"


def _none(what: str) -> str:
    return f"a physical limit: no negative {what}"


def _above(what: str) -> str:
    return f"a physical limit: {what} is above none"


@dataclass(frozen=True)
class Param:
    """One parameter as the catalogue declares it. `choices` is a fixed list
    of words, or where the worker reads them: "bool", "chemicals",
    "table:<module>:<attribute path>" (the keys of a cost table), "setter"
    (the words the class's setter compares against) or "init:<name>" (the
    words its `_init` compares `name` against)."""

    key: str
    label: str
    gloss: str
    dimension: str
    unit: str
    group: str
    rule: tuple[str, ...]
    bounds: tuple[float | None, float | None, str]
    symbol: str = ""
    name: str | None = None
    via: Literal["argument", "attribute"] = "argument"
    how: str | None = None
    per: Literal["component", "effect"] | None = None
    choices: tuple[str, ...] | str | None = None
    note: str | None = None
    step: float | None = None
    convention: float | str | None = None

    @property
    def bst(self) -> str:
        """The class's own name for it."""
        return self.name or self.key


@dataclass(frozen=True)
class Port:
    """An inlet or outlet; its index is its place among its side's ports, in
    the order the entry lists them."""

    side: Literal["in", "out"]
    name: str
    what: str
    onward: bool = False
    source: Literal["upstream", "side", "unit"] | None = None
    many: bool = False


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    line: str
    stage: str
    params: tuple[Param, ...]
    ports: tuple[Port, ...]
    cost_model: bool
    biosteam: str | None = None
    inhouse: str | None = None
    not_offered: tuple[tuple[str, str], ...] = ()
    needs: tuple[tuple[tuple[tuple[str, ...], ...], str], ...] = ()
    notes: tuple[str, ...] = ()
    maps: tuple[str, ...] = ()
    # OF-BLD-020 §5.R (part a): the outlet a per-component split sends its
    # share to, as the class's own `_run` sends it (None: the first outlet,
    # BioSTEAM's reading for its splitters and solids separators; the drum
    # dryer's `split_to(hot_air, dry_solids, split)` sends it to its hot gas).
    split_to: str | None = None
    # The chemical whose split the class never reads while a moisture content
    # is set: it moves that chemical between its outlets to meet the moisture
    # (SolidsSeparator._run zeroes its split; DrumDryer._run adjusts it after
    # the split), so a split of it is not read (finding 6).
    moisture_sets: str | None = None

    @property
    def cls(self) -> str:
        return self.biosteam or self.inhouse or ""


ASSUME = ("assumption",)
DEFAULT = ("assumption", "library-default")
BOOL = "bool"
CHEMS = "chemicals"
PV_MATERIALS = "table:biosteam.units.design_tools.specification_factors:pressure_vessel_material_factors"
VACUUM = "table:biosteam.units.design_tools.vacuum:_default_vacuum_systems"


def _in(name: str = "feed", what: str = "the stream from the unit before", *, many: bool = False) -> Port:
    return Port("in", name, what, source="upstream", many=many)


def _side(name: str, what: str, source: Literal["side", "unit"]) -> Port:
    return Port("in", name, what, source=source)


def _out(name: str, what: str, *, onward: bool = False) -> Port:
    return Port("out", name, what, onward=onward)


def _split(gloss: str, *, rule: tuple[str, ...] = ("record:step_recovery", "assumption"), note: str) -> Param:
    return Param("split", "Split", gloss, "fraction", "", "Separation", rule, (0, 1, _SPLIT), per="component",
                 note=note)


_SPLIT_NOTE = ("Per component: a key split.<chemical> for each chemical of the train. BioSTEAM's split, which the class "
               "requires and gives no default for. A record of step_recovery binds the product's split when a train "
               "is built (§5.2); every other component's waits for a person.")
_ORDER = ("order", "the order a split's shares are listed in: the per-component keys name each chemical instead")
_MOISTURE_ID = ("moisture_ID", "the chemical the moisture content is of: BioSTEAM's water when unset, and a broth's "
                               "moisture is water")
_STRICT = ("strict_moisture_content", "a check switch: whether BioSTEAM refuses a cake that cannot hold the moisture "
                                      "asked; left to the class")
_MOISTURE_SETS = ("The moisture content sets the water: BioSTEAM moves water between the outlets to meet it and "
                  "never reads a split of water, so split.Water is not read while a moisture content is set (§5.R).")


def _moisture(rule: tuple[str, ...] = ("record:cake_moisture", "assumption", "library-default"),
              gloss: str = "the share of the cake's mass that is water: BioSTEAM moves water between the outlets to "
                           "meet it", label: str = "Cake moisture", note: str | None = None) -> Param:
    return Param("moisture_content", label, gloss, "fraction", "", "Separation", rule, (0, 1, _SHARE), note=note)


def _column(name: str, line: str, *, cls: str, notes: tuple[str, ...]) -> Entry:
    """BinaryDistillation and ShortcutColumn: one constructor (Distillation's)."""
    frac = (0, 1, _SHARE)
    return Entry(
        id=name, name=cls, line=line, stage="concentration", biosteam=cls, cost_model=True,
        params=(
            Param("light_key", "Light key", "the more volatile of the two chemicals the column separates, sent to the "
                  "distillate", "choice", "", "Separation", ASSUME, (None, None, _WORDS), name="LHK",
                  how="LHK=(light_key, heavy_key)", choices=CHEMS,
                  note="BioSTEAM's LHK holds the light key and the heavy key as one pair; it requires both."),
            Param("heavy_key", "Heavy key", "the less volatile of the two chemicals the column separates, sent to the "
                  "bottoms", "choice", "", "Separation", ASSUME, (None, None, _WORDS), name="LHK",
                  how="LHK=(light_key, heavy_key)", choices=CHEMS, note="The second of BioSTEAM's LHK pair."),
            Param("k", "Reflux over minimum", "the reflux ratio as a multiple of the minimum reflux ratio", "ratio", "",
                  "Separation", ASSUME, (1, None, "a physical limit: the reflux is at least the minimum it is a "
                                                  "multiple of"), symbol="k",
                  note="BioSTEAM requires it and gives no default."),
            Param("P", "Pressure", "the column's operating pressure", "pressure", "Pa", "Conditions", DEFAULT,
                  (0, None, _ABS_P), symbol="P"),
            Param("Rmin", "Least minimum reflux", "a minimum reflux ratio the column holds to when the one it computes "
                  "is lower", "ratio", "", "Separation", DEFAULT, (0, None, _none("reflux")), symbol="Rmin"),
            Param("product_specification_format", "Product specification", "whether the products are set by the "
                  "light key's share at the top and bottom (Composition) or by each key's recovery (Recovery)",
                  "choice", "", "Separation", DEFAULT, (None, None, _WORDS), choices="setter",
                  note="None: BioSTEAM reads it from which pair is given, y_top and x_bot or Lr and Hr."),
            Param("y_top", "Light key at the top", "the light key's molar share of the two keys in the distillate",
                  "fraction", "", "Separation", DEFAULT, frac, symbol="y_top"),
            Param("x_bot", "Light key at the bottom", "the light key's molar share of the two keys in the bottoms",
                  "fraction", "", "Separation", DEFAULT, frac, symbol="x_bot"),
            Param("Lr", "Light key recovery", "the share of the light key recovered in the distillate", "fraction", "",
                  "Separation", DEFAULT, frac, symbol="Lr"),
            Param("Hr", "Heavy key recovery", "the share of the heavy key recovered in the bottoms", "fraction", "",
                  "Separation", DEFAULT, frac, symbol="Hr"),
            Param("vessel_material", "Column material", "what the column shell is made of, which sets its cost factor",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.distillation:distillation_column_material_factors"),
            Param("tray_material", "Tray material", "what the trays are made of, which sets their cost factor",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.distillation:tray_material_factor_functions"),
            Param("tray_type", "Tray type", "the kind of tray, which sets its cost factor", "choice", "", "Equipment",
                  DEFAULT, (None, None, _WORDS), choices="table:biosteam.units.distillation:distillation_tray_type_factor"),
            Param("tray_spacing", "Tray spacing", "the height between trays", "length", "mm", "Equipment", DEFAULT,
                  (0, None, _above("a spacing"))),
            Param("stage_efficiency", "Stage efficiency", "the share of an ideal stage each tray achieves", "fraction",
                  "", "Equipment", DEFAULT, frac,
                  note="None: BioSTEAM computes it by the O'Connell correlation."),
            Param("velocity_fraction", "Velocity over flooding", "the vapour's velocity as a share of the most it may "
                  "reach before the column floods", "fraction", "", "Equipment", DEFAULT, frac),
            Param("foaming_factor", "Foaming factor", "the share of the flooding velocity left once foaming is "
                  "allowed for", "fraction", "", "Equipment", DEFAULT,
                  (0, 1, "the class's own range: its setter refuses a foaming factor outside none to the whole")),
            Param("open_tray_area", "Open tray area", "the open area of a tray over its active area", "fraction", "",
                  "Equipment", DEFAULT, frac),
            Param("downcomer_area_fraction", "Downcomer area", "the downcomer's share of a tray's area", "fraction", "",
                  "Equipment", DEFAULT, frac, note="None: BioSTEAM estimates it by Oliver's rule."),
            Param("is_divided", "Divided column", "whether the rectifier and the stripper are two columns",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("vacuum_system_preference", "Vacuum system", "the vacuum system BioSTEAM sizes when the column runs "
                  "below atmospheric pressure", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=VACUUM),
            Param("partial_condenser", "Partial condenser", "whether the condenser condenses part of the vapour (the "
                  "distillate leaves as vapour) or all of it", "choice", "", "Equipment", DEFAULT,
                  (None, None, _WORDS), choices=BOOL),
            Param("weir_height", "Weir height", "the weir's height as a share of the tray spacing", "fraction", "",
                  "Equipment", DEFAULT,
                  (0, 1, "the class's own range: its setter refuses a weir height that is not a share of the spacing")),
        ),
        not_offered=(
            ("condenser_thermo", "a thermo object, the condenser's property package: the column's own"),
            ("reboiler_thermo", "a thermo object, the reboiler's property package: the column's own"),
            ("vlle", "an equilibrium-model switch for a second liquid phase, held off as BioSTEAM holds it: a broth's "
                     "column is vapour and liquid"),
            ("check_LHK", "a check switch: BioSTEAM checks the keys' volatilities, held on"),
        ),
        needs=((( ("light_key", "heavy_key"),), "a column separates two keys, and BioSTEAM requires both"),
               ((("k",),), "BioSTEAM requires the reflux as a multiple of the minimum"),
               ((("y_top", "x_bot"), ("Lr", "Hr")), "the products are set by the light key's share at the top and the "
                                                    "bottom, or by both keys' recoveries")),
        ports=(_in(many=True), _out("distillate", "the light key and what boils with it", onward=True),
               _out("bottoms", "the heavy key and what stays with it")),
        notes=notes,
    )


UNIT_TYPES: tuple[Entry, ...] = (
    # ── harvest ──────────────────────────────────────────────────────────
    Entry(
        id="centrifugation", name="Solids centrifuge", stage="harvest", biosteam="SolidsCentrifuge", cost_model=True,
        line="spins the solids, cells first, out of the broth: each component splits between a solids-rich cake and "
             "the liquid",
        params=(
            _split("the share of each component's flow that leaves with the solids-rich cake (outlet 0)",
                   note=_SPLIT_NOTE),
            _moisture(rule=("record:cake_moisture", "assumption", "library-default")),
            Param("centrifuge_type", "Centrifuge type", "the kind of centrifuge, each with the solids loading its cost "
                  "correlation holds for", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.solids_separation:SolidsCentrifuge.solids_loading_range"),
        ),
        not_offered=(_ORDER, ("solids", "which chemicals count as solids, a list of names, which a parameter of one "
                                       "number or one word cannot hold: BioSTEAM takes every chemical locked as a "
                                       "solid, and sizes the centrifuges by their load"), _MOISTURE_ID, _STRICT),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(many=True), _out("cake", "the solids-rich cake: each component's split"),
               _out("liquid", "the liquid: the rest", onward=True)),
        notes=("The liquid goes on by default, as it does for a product in solution; a train routes the cake on for a "
               "product held in the cells.", _MOISTURE_SETS),
        moisture_sets=SOLVENT,
    ),
    # ── clarification ────────────────────────────────────────────────────
    Entry(
        id="pressure-filtration", name="Pressure filter", stage="clarification", biosteam="PressureFilter",
        cost_model=True,
        line="presses the broth through a filter cloth: solids stay as a cake, the filtrate passes",
        params=(
            _moisture(rule=("record:cake_moisture", "assumption", "library-default")),
            _split("the share of each component's flow that stays in the retentate, the cake (outlet 0)",
                   rule=("record:step_recovery", "assumption", "library-default"),
                   note=("Per component: a key split.<chemical> for each chemical of the train. Unset, each "
                         "component's split is the class's own table share (PressureFilter._init's, of the NREL corn "
                         "stover design), read in the worker from a filter built with its split unset on the program's "
                         "chemicals. BioSTEAM drops its whole table once any share is given, so a run that sets one "
                         "share passes every other at the table's own (§5.R).")),
        ),
        needs=(),
        ports=(_in(many=True), _out("retentate", "the cake"), _out("filtrate", "what passes the cloth", onward=True)),
        notes=("BioSTEAM costs the filter as the NREL corn stover design's filter press and its tanks and pumps.",
               _MOISTURE_SETS),
        moisture_sets=SOLVENT,
    ),
    Entry(
        id="rotary-vacuum-filtration", name="Rotary vacuum filter", stage="clarification",
        biosteam="RotaryVacuumFilter", cost_model=True,
        line="draws the liquid through a turning drum's filter under vacuum: solids stay as a cake on the drum",
        params=(
            _split("the share of each component's flow that stays in the retentate, the cake (outlet 0)",
                   note=_SPLIT_NOTE),
            _moisture(note="None: the split alone, with no water moved to meet a moisture."),
        ),
        not_offered=(_ORDER, _MOISTURE_ID, _STRICT),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(many=True), _out("retentate", "the cake"), _out("permeate", "the filtrate", onward=True)),
        notes=(_MOISTURE_SETS,),
        moisture_sets=SOLVENT,
    ),
    Entry(
        id="clarifier", name="Clarifier", stage="clarification", biosteam="Clarifier", cost_model=True,
        line="lets the solids settle in a tank: the clear liquid overflows, the solids leave as underflow",
        params=(
            _split("the share of each component's flow that leaves with the clear overflow (outlet 0); the rest "
                   "settles to the underflow", note=_SPLIT_NOTE),
        ),
        not_offered=(_ORDER,),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(), _out("overflow", "the clarified liquid: each component's split", onward=True),
               _out("underflow", "the settled solids: the rest")),
        notes=("BioSTEAM sizes the settling area from the overflow's volume.",),
    ),
    # ── concentration ────────────────────────────────────────────────────
    Entry(
        id="flash", name="Flash drum", stage="concentration", biosteam="Flash", cost_model=True,
        line="heats or lowers the pressure of the broth so part of it boils: vapour and liquid leave at equilibrium",
        params=(
            Param("P", "Pressure", "the drum's operating pressure", "pressure", "Pa", "Conditions", DEFAULT,
                  (0, None, _ABS_P), symbol="P"),
            Param("T", "Temperature", "the drum's operating temperature", "temperature", "K", "Conditions", DEFAULT,
                  (0, None, _ABS_T), symbol="T"),
            Param("V", "Vapour fraction", "the molar share of the feed that leaves as vapour", "fraction", "",
                  "Conditions", DEFAULT, (0, 1, _SHARE), symbol="V"),
            Param("Q", "Duty", "the heat the drum takes in (negative, gives out)", "power", "kJ h⁻¹", "Conditions",
                  DEFAULT, (None, None, "no bound: a duty may be taken in or given out"), symbol="Q"),
            Param("vessel_material", "Vessel material", "what the drum is made of, which sets its cost factor",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=PV_MATERIALS),
            Param("vacuum_system_preference", "Vacuum system", "the vacuum system BioSTEAM sizes when the drum runs "
                  "below atmospheric pressure", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices=VACUUM),
            Param("has_glycol_groups", "Glycol groups", "whether the mixture holds glycol groups, which change how "
                  "the drum is sized", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("has_amine_groups", "Amine groups", "whether the mixture holds amine groups, which change how the "
                  "drum is sized", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("vessel_type", "Vessel orientation", "whether the drum stands vertical or lies horizontal",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.design_tools.pressure_vessel:allowed_vessel_types",
                  note="None: BioSTEAM chooses by its heuristic, from the vapour and liquid flows."),
            Param("holdup_time", "Holdup time", "the time to raise the liquid to half full", "time", "min",
                  "Equipment", DEFAULT, (0, None, _none("time"))),
            Param("surge_time", "Surge time", "the time from the normal to the highest liquid level", "time", "min",
                  "Equipment", DEFAULT, (0, None, _none("time"))),
            Param("has_mist_eliminator", "Mist eliminator", "whether the drum has a mist eliminator pad", "choice",
                  "", "Equipment", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("flash_inlet", "Flash the inlet", "whether BioSTEAM flashes the inlet when it sizes the heater "
                  "(off saves time when the inlet is already flashed)", "choice", "", "Equipment", DEFAULT,
                  (None, None, _WORDS), choices=BOOL),
            Param("has_vapor_condenser", "Vapour condenser", "whether the vapour leaving is condensed, which lets a "
                  "vacuum system run more efficiently", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices=BOOL, note="None: no condenser."),
        ),
        not_offered=(("x", "a binary mixture's liquid composition: a broth holds more than two chemicals, so the drum "
                           "is set by two of P, T, V and Q"),
                     ("y", "a binary mixture's vapour composition: a broth holds more than two chemicals, so the drum "
                           "is set by two of P, T, V and Q")),
        needs=((tuple(combinations(("P", "T", "V", "Q"), PAIR)), "BioSTEAM sets a flash by exactly two of pressure, "
                                                              "temperature, vapour fraction and duty"),),
        ports=(_in(), _out("vapour", "what boils off", onward=True), _out("liquid", "what stays liquid")),
        notes=("The vapour goes on by default, as it does for a volatile product; a train routes the liquid on for a "
               "product that stays.", "Give two of P, T, V and Q, no more."),
    ),
    _column(
        "distillation",
        "separates two keys by repeated boiling and condensing on trays: the lighter leaves at the top, the heavier at "
        "the bottom, each to the purity or recovery set", cls="BinaryDistillation",
        notes=("The column is sized and costed by BioSTEAM (McCabe–Thiele stages, tray efficiency, flooding).",
               "thermosteam's own vapour–liquid equilibrium decides how far the keys can be split; an azeotrope "
               "between them limits the top (a train's run warns of it, §5.2).")),
    _column(
        "distillation-shortcut",
        "as the binary column, with the stages found by the Fenske–Underwood–Gilliland shortcut over every "
        "chemical, not the two keys alone", cls="ShortcutColumn",
        notes=("The Fenske–Underwood–Gilliland shortcut, sized and costed by BioSTEAM.",)),
    Entry(
        id="evaporation", name="Multi-effect evaporator", stage="concentration", biosteam="MultiEffectEvaporator",
        cost_model=True,
        line="boils water off the broth in a series of effects at falling pressures, each heated by the vapour of the "
             "one before",
        params=(
            Param("effects", "Effects", "how many evaporators run in series, one pressure each", "count", "",
                  "Conditions", ASSUME, (1, None, _COUNT), name="P", how="the number of pressures in P", step=1,
                  note="BioSTEAM's P is one pressure per effect; this is how many it holds."),
            Param("P", "Pressure of an effect", "the operating pressure of one effect, the first effect first",
                  "pressure", "Pa", "Conditions", ASSUME, (0, None, _ABS_P), symbol="P", per="effect",
                  how="P=(P.1, …, P.<effects>)",
                  note="Per effect: a key P.<n> for each of the effects. BioSTEAM requires them."),
            Param("V", "Fraction evaporated", "the molar share of the feed evaporated, as V_definition reads it",
                  "fraction", "", "Conditions", ASSUME, (0, 1, _SHARE), symbol="V",
                  note="BioSTEAM requires it and gives no default."),
            Param("V_definition", "What V is of", "whether V is evaporated over all the effects or in the first",
                  "choice", "", "Conditions", DEFAULT, (None, None, _WORDS), choices="setter"),
            Param("flash", "Flash the first effect", "whether the first effect is a flash, which lets volatile "
                  "chemicals leave with the water", "choice", "", "Conditions", DEFAULT, (None, None, _WORDS),
                  choices=BOOL),
        ),
        not_offered=(("chemical", "the chemical the later effects evaporate, BioSTEAM's water by its CAS number: a "
                                  "broth's evaporator evaporates water"),),
        needs=(((("effects", "P"),), "BioSTEAM requires a pressure for each effect"),
               ((("V",),), "BioSTEAM requires the fraction evaporated")),
        ports=(_in(), _out("concentrate", "the concentrated liquid", onward=True),
               _out("condensate", "the water boiled off, condensed")),
    ),
    Entry(
        id="uf-df", name="Ultrafiltration and diafiltration", stage="concentration", inhouse="Ultrafiltration",
        cost_model=False,
        line="concentrates the broth across a membrane, then washes the retentate with buffer: each component passes "
             "by its sieving coefficient",
        params=(
            Param("sieving_coefficient", "Sieving coefficient", "the share of a component's concentration that "
                  "passes the membrane: none is fully retained, the whole passes freely", "fraction", "",
                  "Separation", ("record:sieving_coefficient", "assumption"), (0, 1, _SHARE), symbol="S",
                  per="component",
                  note=("Per component: a key sieving_coefficient.<chemical> for each chemical of the train but water, "
                        "the solvent, whose retentate share is the concentration factor's. The class requires one for "
                        "every chemical the feed carries.")),
            Param("concentration_factor", "Concentration factor", "the feed's water over the retentate's: how many "
                  "times the volume is reduced", "ratio", "", "Separation", ASSUME,
                  (1, None, "a physical limit: concentrating leaves at most the volume fed"), symbol="CF"),
            Param("diavolumes", "Diafiltration volumes", "how many retentate volumes of buffer wash through after "
                  "concentrating", "count", "", "Separation", DEFAULT, (0, None, _none("buffer")), symbol="N",
                  note="None: no diafiltration, a concentration step alone (the class's own reading)."),
            Param("flux", "Flux", "the permeate's flow per area of membrane, which sizes the membrane", "flux",
                  "L m⁻² h⁻¹", "Equipment", DEFAULT, (0, None, _above("a flux")), symbol="J",
                  note="None: no membrane area is sized."),
        ),
        needs=(((("sieving_coefficient",),), "the class requires each component's sieving coefficient"),
               ((("concentration_factor",),), "the class requires the concentration factor")),
        ports=(_in(), _side("buffer", "the diafiltration buffer, water the unit sizes itself: the diavolumes times "
                                      "the retentate's water", "unit"),
               _out("retentate", "what the membrane holds back", onward=True),
               _out("permeate", "what passes, with the buffer")),
        notes=("No cost model: a membrane's correlation with a source is not added yet, so BioSTEAM's Unit costs it at "
               "nothing.",
               "Each component's retentate share is CF^(−S)·e^(−N·S): concentration by the factor CF, then N "
               "diavolumes at constant volume, with S its sieving coefficient."),
    ),
    # ── disruption ───────────────────────────────────────────────────────
    Entry(
        id="cell-disruption", name="Cell disruption", stage="disruption", inhouse="CellDisruption", cost_model=False,
        line="breaks the cells, by homogeniser or bead mill, so the product they hold moves into the liquid",
        params=(
            Param("product_ID", "Product", "the chemical the cells hold, which disruption releases", "choice", "",
                  "Separation", ASSUME, (None, None, _WORDS), choices=CHEMS,
                  note="The cells hold it as the inlet's solid phase; the class requires it."),
            Param("release", "Release per pass", "the share of the product still in the cells that one pass "
                  "releases", "fraction", "", "Separation", ("record:disruption_protein_yield", "assumption"),
                  (0, 1, _SHARE), symbol="k",
                  note=("A record of disruption_protein_yield states the share released by its method as run, which "
                        "binds the release of one pass where the record's method names one (§5.2).")),
            Param("passes", "Passes", "how many times the broth goes through", "count", "", "Separation", ASSUME,
                  (1, None, _COUNT), symbol="N", step=1),
        ),
        needs=(((("product_ID",),), "the class requires the product the cells hold"),
               ((("release",),), "the class requires the release per pass"),
               ((("passes",),), "the class requires the passes")),
        ports=(_in(), _out("lysate", "the disrupted broth: the product released into the liquid", onward=True)),
        notes=("No cost model: a homogeniser's or bead mill's correlation with a source is not added yet.",
               "First-order release: after N passes the share released is 1 − (1 − k)^N, moved from the inlet's solid "
               "phase (the cells) to its liquid."),
        maps=("homogenisation", "bead-mill"),
    ),
    # ── capture ──────────────────────────────────────────────────────────
    Entry(
        id="lle", name="Mixer-settler extraction", stage="capture", biosteam="MixerSettler", cost_model=True,
        line="mixes the broth with an immiscible solvent and lets the two liquids settle: the product moves into the "
             "solvent by its partition",
        params=(
            Param("top_chemical", "Extract's main chemical", "the chemical that makes up the extract phase", "choice",
                  "", "Separation", DEFAULT, (None, None, _WORDS), choices=CHEMS,
                  note="None: the solvent's main chemical."),
            Param("model", "Settler model", "how the settler splits the two liquids: thermosteam's liquid–liquid "
                  "equilibrium, given splits, or given partition coefficients", "choice", "", "Separation", DEFAULT,
                  (None, None, _WORDS), choices="init:model"),
            Param("partition_coefficient", "Partition coefficient", "a component's concentration in the extract over "
                  "its concentration in the raffinate", "ratio", "", "Separation",
                  ("record:partition_coefficient", "assumption", "library-default"),
                  (0, None, _none("partition coefficient")), symbol="K", name="settler_data", per="component",
                  how="settler_data={'partition_IDs': (…), 'partition_coefficients': (…)}, read when model is "
                      "'partition coefficients'",
                  note=("Per component: a key partition_coefficient.<chemical>. None: the settler computes the split "
                        "by the model; a value is read only under the model 'partition coefficients'.")),
        ),
        not_offered=(("mixer_data", "a dict of another unit's settings: the LiquidsMixingTank BioSTEAM builds inside, on "
                                    "its own defaults"),
                     ("settler_data", "a dict of another unit's settings, the settler's: its partition coefficients "
                                      "are partition_coefficient, the rest are the settler's own defaults")),
        ports=(_in(), _side("solvent", "the fresh solvent, a stream the train supplies beside the line", "side"),
               _out("extract", "the solvent phase, carrying what partitions into it", onward=True),
               _out("raffinate", "the broth phase left")),
        notes=("The solvent is the second inlet: a train names its chemical and flow (§5.2).",),
    ),
    Entry(
        id="lle-multistage", name="Counter-current mixer-settlers", stage="capture",
        biosteam="MultiStageMixerSettlers", cost_model=True,
        line="extracts in a series of mixer-settlers with the solvent running against the broth",
        params=(
            Param("N_stages", "Stages", "how many mixer-settlers run in series", "count", "", "Separation", ASSUME,
                  (1, None, _COUNT), step=1, note="BioSTEAM requires it and gives no default."),
            Param("partition_coefficient", "Partition coefficient", "a component's composition in the extract over "
                  "its composition in the raffinate, by mole", "ratio", "", "Separation",
                  ("record:partition_coefficient", "assumption", "library-default"),
                  (0, None, _none("partition coefficient")), symbol="K", name="partition_data", per="component",
                  how="partition_data={'IDs': (…), 'K': (…)}",
                  note=("Per component: a key partition_coefficient.<chemical>. None: thermosteam computes the "
                        "partition from temperature and composition.")),
            Param("top_chemical", "Extract's main chemical", "the chemical that makes up the extract phase", "choice",
                  "", "Separation", DEFAULT, (None, None, _WORDS), choices=CHEMS),
        ),
        not_offered=(("feed_stages", "which stage each inlet enters, a pair of stage numbers: BioSTEAM's counter-current "
                                     "default, the feed at the first and the solvent at the last"),
                     ("extract_side_draws", "draws between stages, a train's routing and not one number"),
                     ("raffinate_side_draws", "draws between stages, a train's routing and not one number"),
                     ("mixer_data", "a dict of another unit's settings: the mixing tanks' own defaults"),
                     ("settler_data", "a dict of another unit's settings: the settlers' own defaults"),
                     ("use_cache", "a cache switch: whether BioSTEAM starts from its last solution")),
        needs=(((("N_stages",),), "BioSTEAM requires the number of stages"),),
        ports=(_in(), _side("solvent", "the fresh solvent, a stream the train supplies beside the line", "side"),
               _out("extract", "the solvent phase, carrying what partitions into it", onward=True),
               _out("raffinate", "the broth phase left")),
        notes=("The solvent is the second inlet: a train names its chemical and flow (§5.2).",),
    ),
    Entry(
        id="chromatography", name="Chromatography step", stage="capture", inhouse="Chromatography", cost_model=False,
        line="binds the product on a column and elutes it, leaving most impurities in the flow-through: declared "
             "recovery and purity until a column model arrives",
        params=(
            Param("mode", "Mode", "the chromatography's mode of separation", "choice", "", "Separation", ASSUME,
                  (None, None, _WORDS), choices=MODES,
                  note="Each mode is a vocabulary step (iex, hic, imac, affinity-custom, sec, mixed-mode); the "
                       "placeholder's balance is the same for all."),
            Param("product_ID", "Product", "the chemical the column binds and elutes", "choice", "", "Separation",
                  ASSUME, (None, None, _WORDS), choices=CHEMS),
            Param("recovery", "Recovery", "the share of the product loaded that leaves in the eluate", "fraction", "",
                  "Separation", ("record:step_recovery", "assumption"), (0, 1, _SHARE), symbol="R"),
            Param("purity", "Purity", "the product's share of what the eluate carries besides water: the host "
                  "impurities follow it in proportion", "fraction", "", "Separation",
                  ("record:product_purity", "assumption"), (0, 1, _SHARE), symbol="P"),
            Param("binding_capacity", "Binding capacity", "the product a litre of bed holds, which sizes the bed per "
                  "hour of loading", "massConc", "g L⁻¹", "Equipment", ASSUME, (0, None, _above("a capacity"))),
            Param("elution_volumes", "Elution volumes", "how many bed volumes of buffer elute the product", "count",
                  "", "Equipment", ASSUME, (0, None, _none("buffer"))),
        ),
        needs=(((("mode",),), "the class requires the mode"), ((("product_ID",),), "the class requires the product"),
               ((("recovery",),), "the class requires the recovery"), ((("purity",),), "the class requires the purity"),
               ((("binding_capacity",),), "the class sizes the bed and the buffer by the binding capacity"),
               ((("elution_volumes",),), "the class sizes the buffer by the elution volumes")),
        ports=(_in(name="load", what="the stream loaded"),
               _side("buffer", "the elution buffer, water the unit sizes itself: the elution volumes times the bed "
                               "per hour of loading", "unit"),
               _out("eluate", "the product pool", onward=True),
               _out("flow-through", "what the column does not hold")),
        notes=("No cost model: no column correlation with a source is added.",
               "CADET replaces this: a column model will compute what recovery and purity declare here.",
               "Recovery splits the product; purity, on the dry basis, sets the share of every other chemical but "
               "water that follows it, alike for all."),
        maps=tuple(MODE_VOCABULARY.values()),
    ),
    # ── polish ───────────────────────────────────────────────────────────
    Entry(
        id="molecular-sieve", name="Molecular sieve", stage="polish", biosteam="MolecularSieve", cost_model=True,
        line="adsorbs the water distillation cannot take past the azeotrope: each component splits between the "
             "regenerate the sieves release and the dehydrated product",
        params=(
            _split("the share of each component's flow the sieves hold and release in the regenerate (outlet 0): the "
                   "water they adsorb, and what goes with it; the rest leaves as the dehydrated product (outlet 1)",
                   rule=("assumption",), note=("Per component: a key split.<chemical> for each chemical of the train. "
                                               "BioSTEAM's split, to outlet 0, which the class requires and gives no "
                                               "default for.")),
            Param("approx_duty", "Approximate duty", "whether BioSTEAM adds the regeneration's heating and cooling "
                  "duties by its own per-flow rule", "choice", "", "Conditions", DEFAULT, (None, None, _WORDS),
                  choices=BOOL),
        ),
        not_offered=(_ORDER, ("P", "MolecularSieve._init sets P to None whatever it is passed (read from its code), so "
                                   "the outlets leave at the feed's pressure")),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(), _out("regenerate", "the water the sieves adsorb and release, with what goes with it: each "
                                         "component's split"),
               _out("product", "the dehydrated product: the rest", onward=True)),
        notes=("BioSTEAM's MolecularSieve sends its split to outlet 0, and biorefineries' ethanol plant uses it for the "
               "water-rich regenerate it recycles to the rectifier; the dehydrated ethanol leaves by outlet 1 (§5.R).",),
    ),
    Entry(
        id="crystallisation", name="Batch crystalliser", stage="polish", biosteam="BatchCrystallizer", cost_model=True,
        line="holds the liquor in batch vessels at a set temperature while crystals form",
        params=(
            Param("tau", "Batch time", "the hours each batch is held", "time", "h", "Schedule", ASSUME,
                  (0, None, _above("a batch's time")), symbol="τ",
                  note="None in its signature, and the class cannot size the vessels without it."),
            Param("N", "Number of vessels", "how many crystallisers share the liquor", "count", "", "Schedule", DEFAULT,
                  (1, None, _COUNT), step=1, note="None by default. Give N or V, not both."),
            Param("V", "Vessel volume", "the volume of each crystalliser", "volume", "m³", "Schedule", DEFAULT,
                  (0, None, _above("a volume")), note="None by default. Give N or V, not both."),
            Param("T", "Temperature", "the crystallisers' operating temperature", "temperature", "K", "Conditions",
                  DEFAULT, (0, None, _ABS_T), symbol="T"),
            Param("Nmin", "Fewest vessels", "the fewest crystallisers BioSTEAM may choose when V is given", "count", "",
                  "Schedule", DEFAULT, (1, None, _COUNT), step=1),
            Param("Nmax", "Most vessels", "the most crystallisers BioSTEAM may choose when V is given", "count", "",
                  "Schedule", DEFAULT, (1, None, _COUNT), step=1),
            Param("kW", "Power per volume", "the electricity the suspension takes per volume", "powerPerVolume",
                  "kW gal⁻¹", "Conditions", DEFAULT, (0, None, _none("power"))),
            Param("tau_0", "Cleaning and unloading time", "the hours between batches", "time", "h", "Schedule",
                  DEFAULT, (0, None, _none("time")), via="attribute", symbol="τ₀"),
            Param("V_wf", "Working volume fraction", "the share of each vessel the liquor fills", "fraction", "",
                  "Schedule", DEFAULT, (0, 1, _SHARE), via="attribute"),
        ),
        not_offered=(("vessel_material", "BatchCrystallizer._init takes it and keeps it nowhere (read from its code), "
                                         "so it would change nothing"),),
        needs=(((("tau",),), "the class cannot size the vessels without the batch time"),
               ((("N",), ("V",)), "BioSTEAM sizes by the number of vessels or by their volume")),
        ports=(_in(), _out("slurry", "the liquor as fed, held and cooled", onward=True)),
        notes=("BioSTEAM's BatchCrystallizer is a vessel: its run copies the inlet to the outlet (its docstring calls it "
               "abstract; a subclass implements the crystallisation), so it sizes and costs the crystallisers and "
               "separates nothing. A crystal yield or a solubility is not its parameter.",),
    ),
    # ── drying ───────────────────────────────────────────────────────────
    Entry(
        id="spray-dry", name="Spray dryer", stage="drying", biosteam="SprayDryer", cost_model=True,
        line="sprays the liquid into hot gas: the water leaves as vapour and the solids as powder",
        params=(
            _moisture(rule=DEFAULT, gloss="the share of the dried product's mass that is water",
                      label="Product moisture"),
        ),
        ports=(_in(), _out("vapour", "the water evaporated"), _out("powder", "the dried solids", onward=True)),
    ),
    Entry(
        id="drying-drum", name="Drum dryer", stage="drying", biosteam="DrumDryer", cost_model=True,
        line="dries wet solids with hot gas in a turning drum, the gas heated by burning natural gas",
        params=(
            _split("the share of each component's flow that leaves with the hot gas (outlet 1)",
                   rule=("assumption",), note=("Per component: a key split.<chemical> for each chemical of the train. "
                                               "BioSTEAM's split, to the hot gas, which the class requires.")),
            Param("RH", "Relative humidity", "the hot gas's relative humidity as it leaves", "fraction", "",
                  "Conditions", DEFAULT, (0, 1, _SHARE), symbol="RH"),
            Param("H", "Specific evaporation rate", "the water evaporated per hour per volume of drum", "rate",
                  "kg h⁻¹ m⁻³", "Equipment", DEFAULT, (0, None, _above("a rate")), symbol="H"),
            Param("length_to_diameter", "Length to diameter", "the drum's length over its width (it lies "
                  "horizontal)", "ratio", "", "Equipment", DEFAULT, (0, None, _above("an aspect ratio"))),
            Param("T", "Temperature", "the drum's operating temperature", "temperature", "K", "Conditions", DEFAULT,
                  (0, None, _ABS_T), symbol="T"),
            Param("P", "Pressure", "the drying gas's pressure", "pressure", "Pa", "Conditions", DEFAULT,
                  (0, None, _ABS_P), symbol="P"),
            Param("moisture_content", "Product moisture", "the share of the dried solids' mass that is water",
                  "fraction", "", "Separation", DEFAULT, (0, 1, _SHARE),
                  note="A dried product's moisture, not a cake's: no record field holds it."),
            Param("utility_agent", "Heat source", "what heats the gas: burning natural gas, or steam", "choice", "",
                  "Conditions", DEFAULT, (None, None, _WORDS), choices="setter"),
        ),
        not_offered=(("gas_composition", "the drying gas's composition, a list of chemical and share pairs: BioSTEAM's "
                                         "air when unset"), _MOISTURE_ID),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(name="wet", what="the wet solids from the unit before"),
               _side("gas", "the dry gas, which the unit sizes to meet the relative humidity", "unit"),
               _side("fuel", "the natural gas, which the unit sizes to meet the heat", "unit"),
               _out("dried", "the dried solids", onward=True), _out("hot-gas", "the gas, with the water"),
               _out("emissions", "the burnt fuel's gas")),
        notes=("DrumDryer._run sends its split to the hot gas (outlet 1): a component the split does not name stays in "
               "the dried solids (§5.R).", _MOISTURE_SETS),
        split_to="hot-gas",
        moisture_sets=SOLVENT,
    ),
    # ── utility ──────────────────────────────────────────────────────────
    Entry(
        id="heat-exchange", name="Heat exchanger", stage="utility", biosteam="HXutility", cost_model=True,
        line="heats or cools the stream with a utility to a set outlet temperature or vapour fraction",
        params=(
            Param("T", "Outlet temperature", "the temperature the stream leaves at", "temperature", "K", "Conditions",
                  DEFAULT, (0, None, _ABS_T), symbol="T"),
            Param("V", "Outlet vapour fraction", "the molar share of the stream leaving as vapour", "fraction", "",
                  "Conditions", DEFAULT, (0, 1, _SHARE), symbol="V"),
            Param("rigorous", "Rigorous equilibrium", "whether BioSTEAM computes the vapour–liquid equilibrium of the "
                  "outlet", "choice", "", "Conditions", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("U", "Heat transfer coefficient", "the overall heat transfer coefficient", "heatTransfer",
                  "kW m⁻² K⁻¹", "Equipment", DEFAULT, (0, None, _above("a coefficient")), symbol="U",
                  note="None: BioSTEAM's heuristic for the fluids."),
            Param("heat_exchanger_type", "Exchanger type", "the kind of exchanger, which sets its cost correlation",
                  "choice", "", "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.heat_exchange:Cb_dict"),
            Param("material", "Material", "the shell and tube materials, which set the cost factor", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.heat_exchange:shell_and_tube_material_factor_coefficients"),
            Param("N_shells", "Shells", "the number of shells the temperature correction is computed for", "count", "",
                  "Equipment", DEFAULT, (1, None, _COUNT), step=1),
            Param("ft", "Correction factor", "a log-mean temperature difference correction factor in place of "
                  "BioSTEAM's", "fraction", "", "Equipment", DEFAULT, (0, 1, _SHARE), symbol="ft",
                  note="None: BioSTEAM computes it from the shells."),
            Param("heat_only", "Heat only", "whether the exchanger may only heat", "choice", "", "Conditions", DEFAULT,
                  (None, None, _WORDS), choices=BOOL),
            Param("cool_only", "Cool only", "whether the exchanger may only cool", "choice", "", "Conditions",
                  DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("heat_transfer_efficiency", "Heat transfer efficiency", "the share of the utility's heat the stream "
                  "receives; the rest is lost", "fraction", "", "Conditions", DEFAULT, (0, 1, _SHARE),
                  note="None: the utility agent's own."),
            Param("dP", "Pressure drop", "the pressure the stream loses across the exchanger", "pressure", "Pa",
                  "Conditions", DEFAULT, (0, None, _none("pressure drop")), symbol="ΔP"),
            Param("estimate_pressure_drop", "Estimate pressure drop", "whether BioSTEAM estimates the pressure drop "
                  "when none is given", "choice", "", "Conditions", DEFAULT, (None, None, _WORDS), choices=BOOL),
        ),
        not_offered=(("H", "an outlet enthalpy in kJ/hr: the outlet is set here by its temperature or vapour fraction"),
                     ("furnace_pressure", "the combustion gas's pressure, read only for a furnace; its _init puts a "
                                          "value in place of None whose unit its own comments name both as pascals "
                                          "and as psig, so it is left to the class")),
        needs=(((("T",), ("V",)), "BioSTEAM sets the outlet by its temperature or its vapour fraction"),),
        ports=(_in(), _out("outlet", "the stream heated or cooled", onward=True)),
    ),
    Entry(
        id="tank", name="Storage tank", stage="utility", biosteam="StorageTank", cost_model=True,
        line="holds the stream for a residence time: sized and costed by volume, the stream unchanged",
        params=(
            Param("vessel_type", "Tank type", "the kind of storage tank, which sets its cost correlation", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.tank:StorageTank.purchase_cost_algorithms"),
            Param("tau", "Residence time", "the hours the stream is held", "time", "h", "Schedule", DEFAULT,
                  (0, None, _above("a residence time")), symbol="τ"),
            Param("V_wf", "Working volume fraction", "the share of the tank the stream fills", "fraction", "",
                  "Equipment", DEFAULT, (0, 1, _SHARE)),
            Param("vessel_material", "Material", "what the tank is made of, which sets its cost factor", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS), choices="table:biosteam.units.tank:vessel_material_factors"),
            Param("kW_per_m3", "Power per volume", "the electricity the tank takes per volume", "powerPerVolume",
                  "kW m⁻³", "Equipment", DEFAULT, (0, None, _none("power"))),
        ),
        ports=(_in(), _out("outlet", "the stream as held", onward=True)),
    ),
    Entry(
        id="mix-tank", name="Mix tank", stage="utility", biosteam="MixTank", cost_model=True,
        line="mixes its inlets in a stirred tank for a residence time",
        params=(
            Param("vessel_type", "Tank type", "the kind of mixing tank, which sets its cost correlation", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS),
                  choices="table:biosteam.units.tank:MixTank.purchase_cost_algorithms"),
            Param("tau", "Residence time", "the hours the stream is held", "time", "h", "Schedule", DEFAULT,
                  (0, None, _above("a residence time")), symbol="τ"),
            Param("V_wf", "Working volume fraction", "the share of the tank the stream fills", "fraction", "",
                  "Equipment", DEFAULT, (0, 1, _SHARE)),
            Param("vessel_material", "Material", "what the tank is made of, which sets its cost factor", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS), choices="table:biosteam.units.tank:vessel_material_factors"),
            Param("kW_per_m3", "Power per volume", "the agitator's electricity per volume", "powerPerVolume",
                  "kW m⁻³", "Equipment", DEFAULT, (0, None, _none("power"))),
        ),
        ports=(_in(what="the streams to mix, the first from the unit before", many=True),
               _out("outlet", "the mixed stream", onward=True)),
    ),
    Entry(
        id="pump", name="Pump", stage="utility", biosteam="Pump", cost_model=True,
        line="raises the stream's pressure",
        params=(
            Param("P", "Outlet pressure", "the pressure the stream leaves at", "pressure", "Pa", "Conditions", DEFAULT,
                  (0, None, _ABS_P), symbol="P",
                  note="None: the outlet keeps the inlet's pressure and the pump is designed for dP_design."),
            Param("pump_type", "Pump type", "the kind of pump; Default chooses by BioSTEAM's heuristic", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS), choices="table:biosteam.units._pump:pump_types"),
            Param("material", "Material", "what the pump is made of, which sets its cost factor", "choice", "",
                  "Equipment", DEFAULT, (None, None, _WORDS), choices="table:biosteam.units._pump:pump_material_factors"),
            Param("dP_design", "Design pressure rise", "the pressure rise the pump is designed for when the outlet "
                  "keeps the inlet's pressure", "pressure", "Pa", "Equipment", DEFAULT,
                  (0, None, _none("pressure rise")), symbol="ΔP"),
            Param("ignore_NPSH", "Ignore NPSH", "whether the net positive suction head is left out of choosing the pump "
                  "type", "choice", "", "Equipment", DEFAULT, (None, None, _WORDS), choices=BOOL),
        ),
        ports=(_in(), _out("outlet", "the stream at its new pressure", onward=True)),
    ),
    Entry(
        id="mixer", name="Mixer", stage="utility", biosteam="Mixer", cost_model=True,
        line="joins its inlets into one stream",
        params=(
            Param("rigorous", "Rigorous equilibrium", "whether BioSTEAM computes the vapour–liquid equilibrium of the "
                  "mixture", "choice", "", "Conditions", DEFAULT, (None, None, _WORDS), choices=BOOL),
            Param("conserve_phases", "Keep phases", "whether each inlet's phases are kept as they are", "choice", "",
                  "Conditions", DEFAULT, (None, None, _WORDS), choices=BOOL),
        ),
        ports=(_in(what="the streams to join, the first from the unit before", many=True),
               _out("outlet", "the joined stream", onward=True)),
        notes=("BioSTEAM costs a mixer at nothing: it is a junction.",),
    ),
    Entry(
        id="splitter", name="Splitter", stage="utility", biosteam="Splitter", cost_model=True,
        line="divides the stream in two by each component's split",
        params=(
            _split("the share of each component's flow that leaves by outlet 0", rule=("assumption",),
                   note=("Per component: a key split.<chemical> for each chemical of the train; a splitter's split is "
                         "the one parameter a person sets. BioSTEAM's split, which the class requires.")),
        ),
        not_offered=(_ORDER,),
        needs=(((("split",),), "BioSTEAM requires the split"),),
        ports=(_in(), _out("split", "each component's split", onward=True), _out("rest", "the remainder")),
        notes=("BioSTEAM costs a splitter at nothing: it is a junction.",),
    ),
)

BY_ID: dict[str, Entry] = {e.id: e for e in UNIT_TYPES}
# What the document's Appendix 2 §B lists and did not enter, with BioSTEAM's
# own words when it was built on the yeast program's chemicals with its own
# defaults (measured 2026-10-21, BioSTEAM 2.54.0; a sim test holds it).
LEFT_OUT = {
    "SingleComponentAdsorptionColumn": (
        "adsorption",
        "does not build on the yeast program's chemicals with its own defaults: its adsorbent, ActivatedCarbon, is not "
        "a chemical of the set (thermosteam: UndefinedChemicalAlias 'ActivatedCarbon'), and no chemical of the set is "
        "an adsorbent"),
}


def entry(type_id: str) -> Entry:
    try:
        return BY_ID[type_id]
    except KeyError:
        raise CatalogueUnknown(f"there is no unit type {type_id!r} in pureOS's catalogue; it holds "
                               f"{', '.join(BY_ID)}") from None


def ids() -> list[str]:
    return list(BY_ID)


def split_outlets(e: Entry) -> tuple[str, str | None]:
    """The outlet a unit's per-component split sends its share to, and the
    one a component the split does not name leaves by: the class's own
    reading (`Entry.split_to`, else its first outlet; the rest to its first
    other outlet, None for a unit of one outlet)."""
    outs = [p.name for p in e.ports if p.side == "out"]
    to = e.split_to or outs[0]
    return to, next((n for n in outs if n != to), None)


# ── what the service serves without BioSTEAM ──────────────────────────


def _ports(e: Entry) -> list[UnitPort]:
    out, seen = [], {"in": 0, "out": 0}
    for p in e.ports:
        out.append(UnitPort(side=p.side, index=seen[p.side], name=p.name, what=p.what, onward=p.onward,
                            source=p.source, many=p.many))
        seen[p.side] += 1
    return out


def _needs(e: Entry) -> list[UnitNeed]:
    return [UnitNeed(alternatives=[list(a) for a in alts], why=why) for alts, why in e.needs]


def _not_offered(e: Entry) -> list[NotOffered]:
    return [NotOffered(name=n, why=w) for n, w in e.not_offered]


def _spec(e: Entry, p: Param, choices: list[str] | None = None,
          bounds: tuple[float | None, str] | None = None) -> ParameterSpec:
    declared_low, high, declared_reason = p.bounds
    low, reason = bounds if bounds is not None else (declared_low, declared_reason)
    if p.choices is None:
        offered = None
    elif choices is not None:
        offered = choices
    else:
        offered = list(p.choices) if isinstance(p.choices, tuple) else []
    names = (f"{e.cls}'s {p.bst}" + (f" ({p.how})" if p.how else "") if p.bst != p.key or p.how else None)
    note = " ".join(x for x in (p.note, f"The class's own name for it: {names}." if names else None) if x) or None
    return ParameterSpec(
        key=p.key, label=p.label, symbol=p.symbol, gloss=p.gloss, dimension=p.dimension, unit=p.unit, min=low,
        max=high, step=p.step, group=p.group, sourceRule=list(p.rule), note=note, boundsReason=reason,
        choices=offered, convention=p.convention)


def static_specs(e: Entry) -> list[ParameterSpec]:
    """An entry's specs as declared, read with no worker: a choice the worker
    reads from BioSTEAM is offered once it is read (`[]` here); templates are
    one spec each."""
    return [_spec(e, p) for p in e.params]


def param_maps(e: Entry) -> list[UnitParamMap]:
    return [UnitParamMap(key=p.key, name=p.bst, via=p.via, per=p.per, how=p.how) for p in e.params]


def unit_type(e: Entry) -> UnitType:
    return UnitType(id=e.id, name=e.name, line=e.line, stage=e.stage, biosteamClass=e.biosteam,  # type: ignore[arg-type]
                    inhouseClass=e.inhouse, insOuts=_ports(e), costModel=e.cost_model,
                    notes=list(e.notes), notOffered=_not_offered(e), needs=_needs(e), maps=list(e.maps),
                    specCount=len(e.params))


def listing() -> list[UnitType]:
    """GET /api/pureos/catalogue: every entry, in stage order, from the data
    alone (no worker, no BioSTEAM)."""
    order = {s: n for n, s in enumerate(STAGES)}
    return [unit_type(e) for e in sorted(UNIT_TYPES, key=lambda x: order[x.stage])]


def _static() -> Iterable[tuple[str, list[ParameterSpec]]]:
    for e in UNIT_TYPES:
        yield f"pureos unit {e.id}", static_specs(e)
    # OF-BLD-020 §5.2: what a train adds, its inlet and its side inlets.
    from . import train_spec

    yield from train_spec.static_specs()


def template_keys(e: Entry) -> dict[str, str]:
    """The template keys of an entry, by what they are expanded per."""
    return {p.key: p.per for p in e.params if p.per}


def expand(type_id: str, specs: list[ParameterSpec], chemicals: Iterable[str], effects: int | None = None
           ) -> list[ParameterSpec]:
    """An entry's specs with each template replaced by one spec a chemical
    (`<key>.<chemical>`) or an effect (`P.<n>`, for `effects` effects): what
    a train's unit is resolved over (§5.2). The ultrafiltration's sieving
    coefficient leaves out the solvent, whose retentate share its
    concentration factor sets."""
    e = entry(type_id)
    per = template_keys(e)
    chems = list(chemicals)
    out: list[ParameterSpec] = []
    for s in specs:
        kind = per.get(s.key)
        if kind is None:
            out.append(s)
            continue
        if kind == "component":
            items = [c for c in chems if not (s.key == "sieving_coefficient" and c == SOLVENT)]
            labels = {c: c for c in items}
        else:
            items = [str(n) for n in range(1, (effects or 0) + 1)]
            labels = {n: f"effect {n}" for n in items}
        for item in items:
            out.append(s.model_copy(update={"key": f"{s.key}{SEP}{item}", "label": f"{s.label}, {labels[item]}"}))
    return out


def _given(v: Any) -> bool:
    return v is not None and not (isinstance(v, str) and not v.strip())


def unmet(type_id: str, values: dict[str, Any]) -> list[str]:
    """What a unit of this type still needs, in words, given its values by
    key (a template counts as set when any of its expanded keys is, and the
    evaporator's pressures when each of its effects has one); empty when it
    can run. §5.2 refuses a train in these words."""
    e = entry(type_id)
    per = template_keys(e)
    labels = {p.key: p.label for p in e.params}

    def has(key: str) -> bool:
        if per.get(key) == "effect":
            n = values.get("effects")
            return isinstance(n, (int, float)) and not isinstance(n, bool) and n >= 1 and all(
                _given(values.get(f"{key}{SEP}{i}")) for i in range(1, int(n) + 1))
        if per.get(key) == "component":
            return any(k.startswith(f"{key}{SEP}") and _given(v) for k, v in values.items())
        return _given(values.get(key))

    said = []
    for alts, why in e.needs:
        if any(all(has(k) for k in alt) for alt in alts):
            continue
        options = " or ".join(" and ".join(labels.get(k, k) for k in alt) for alt in alts)
        said.append(f"{e.name} waits for {options}: {why}")
    return said


def _word(v: Any) -> Any:
    return {"true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def kwargs_of(type_id: str, values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """The class's constructor arguments and the attributes to set after it,
    from a unit's values by catalogue key (templates expanded, words for
    booleans): what a train's builder passes (§5.2). A value left None is
    left to the class. Plain JSON: the worker turns a partition table into
    the arrays BioSTEAM takes."""
    e = entry(type_id)
    kwargs: dict[str, Any] = {}
    attrs: dict[str, Any] = {}
    for p in e.params:
        target = attrs if p.via == "attribute" else kwargs
        if p.per == "component":
            got = {k.partition(SEP)[-1]: float(v) for k, v in values.items()
                   if k.startswith(f"{p.key}{SEP}") and _given(v)}
            if not got:
                continue
            if p.bst == "settler_data":
                target["settler_data"] = {"partition_IDs": list(got), "partition_coefficients": list(got.values())}
            elif p.bst == "partition_data":
                target["partition_data"] = {"IDs": list(got), "K": list(got.values())}
            else:
                target[p.bst] = got
        elif p.per == "effect":
            n = values.get("effects")
            if isinstance(n, (int, float)) and not isinstance(n, bool) and n >= 1:
                pressures = [values.get(f"{p.key}{SEP}{i}") for i in range(1, int(n) + 1)]
                if all(_given(x) for x in pressures):
                    target[p.bst] = [float(x) for x in pressures]
        elif p.key in ("light_key", "heavy_key"):
            light, heavy = values.get("light_key"), values.get("heavy_key")
            if _given(light) and _given(heavy):
                target["LHK"] = [light, heavy]
        elif p.key == "effects":
            continue
        elif _given(values.get(p.key)):
            v = _word(values[p.key])
            if p.choices is None and isinstance(v, float) and p.step == 1 and v.is_integer():
                v = int(v)
            target[p.bst] = v
    if "settler_data" in kwargs and str(kwargs.get("model") or "").lower() != PARTITION_MODEL:
        # The mixer-settler reads partition coefficients under one model only,
        # and its other settlers take no such argument: said, never switched.
        raise ValueError(f"{e.name} reads partition coefficients only under the model '{PARTITION_MODEL}'; set model "
                         "to it, or leave the partition coefficients to the settler")
    return kwargs, attrs


# ── what the worker reads, cached ──────────────────────────────────────

_SPECS: dict[str, dict[str, Any]] = {}
_SPECS_LOCK = threading.Lock()


def worker_specs(type_id: str) -> dict[str, Any]:
    """The class's parameters, defaults, choices and refusals as BioSTEAM
    gives them, from the worker's `catalogue_specs`, kept for this process's
    life (the installed library's, which does not change under it)."""
    from .. import proforma

    entry(type_id)
    with _SPECS_LOCK:
        if type_id not in _SPECS:
            _SPECS[type_id] = proforma.call("catalogue_specs", {"type": type_id})
        return _SPECS[type_id]


def component_defaults(type_id: str) -> dict[str, tuple[dict[str, float], str]]:
    """The per-component defaults a class fills itself when none is given
    (PressureFilter's split table), by template key: each chemical's share
    and where it was read, as the worker read them (`read_class`), or none
    (OF-BLD-020 §5.R part a)."""
    out: dict[str, tuple[dict[str, float], str]] = {}
    for key, d in (worker_specs(type_id).get("defaults") or {}).items():
        table = (d or {}).get("byComponent")
        if isinstance(table, dict) and table:
            out[key] = ({str(c): float(x) for c, x in table.items()}, str(d.get("from") or "its code"))
    return out


def _bounds(p: Param, ws: dict[str, Any]) -> tuple[float | None, str] | None:
    """A lower bound the class sets itself (what its setter refuses at or
    below, read from its code), with its reason; None keeps the declared."""
    got = (ws.get("refuses") or {}).get(p.key)
    if got is None:
        return None
    x = float(got["atOrBelow"])
    if p.step == 1:
        return float(int(x)) + 1, (f"a whole number above what BioSTEAM's {ws['unitClass']} refuses: its setter raises "
                                   f"at or below {x:g} ({got['from']})")
    return x, f"BioSTEAM's {ws['unitClass']} refuses {p.key} at or below {x:g} ({got['from']}): a value above it"


def served_specs(e: Entry, ws: dict[str, Any]) -> list[ParameterSpec]:
    """The entry's specs with the choices and class bounds the worker read."""
    return [_spec(e, p, (ws.get("choices") or {}).get(p.key), _bounds(p, ws)) for p in e.params]


def _defaults(e: Entry, ws: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(ws.get("defaults") or {})


def specs_of(type_id: str) -> UnitSpecs:
    """GET /api/pureos/catalogue/{id}/specs."""
    e = entry(type_id)
    ws = worker_specs(type_id)
    got = _defaults(e, ws)
    return UnitSpecs(
        id=e.id, biosteamClass=e.biosteam, inhouseClass=e.inhouse, specs=served_specs(e, ws),
        defaults=[UnitDefault(key=p.key, value=(got.get(p.key) or {}).get("value"),
                              readFrom=(got.get(p.key) or {}).get("from") or "not read")
                  for p in e.params],
        params=param_maps(e), notOffered=_not_offered(e), needs=_needs(e), chemicals=list(ws.get("chemicals") or []),
        versions=dict(ws.get("versions") or {}), notes=list(e.notes))


# ── the panel's scope (`pureos:unit:<train id>:<unit id>`) ─────────────


def _model_source(e: Entry, ws: dict[str, Any], key: str, where: str) -> BasisSource:
    if e.inhouse:
        return BasisSource(kind="model", id="openferment.pureos.inhouse", note=f"{e.inhouse}'s own reading of {key}, "
                                                                              f"from {where}")
    return BasisSource(kind="model", id=f"biosteam@{(ws.get('versions') or {}).get('biosteam', '')}",
                       note=f"{e.biosteam}'s own default for {key}, read from {where}")


def provided(type_id: str) -> params.Provided:
    """The scope's specs and each one's candidates: the class's own default
    where its rule takes one (a None the class decides at run time); a
    required parameter waits, saying what would bind it."""
    e = entry(type_id)
    ws = worker_specs(type_id)
    got = _defaults(e, ws)
    sources: dict[str, dict[str, ParameterValue | None]] = {}
    for p in e.params:
        cands: dict[str, ParameterValue | None] = {}
        if "library-default" in p.rule and p.per is None:
            d = got.get(p.key) or {}
            v, where = d.get("value"), d.get("from") or "its code"
            cands["library-default"] = ParameterValue(
                key=p.key, value=v, origin="library-default", libraryDefault=v, source=_model_source(e, ws, p.key, where),
                detail=(f"{e.cls}'s default, from {where}" if v is not None else
                        f"{e.cls}'s default is None ({where}): " + (p.note or "the class decides at run time")))
        elif "library-default" in p.rule:
            cands["library-default"] = ParameterValue(
                key=p.key, value=None, origin="library-default", source=_model_source(e, ws, p.key, "its code"),
                detail=p.note or f"{e.cls} decides it per component")
        sources[p.key] = cands
    words = [e.line[0].upper() + e.line[1:] + "."]
    words += [f"Needs {' or '.join(' and '.join(a) for a in alts)}: {why}." for alts, why in e.needs]
    words += [f"Not offered: {n}, {w}." for n, w in e.not_offered]
    words += list(e.notes)
    per = template_keys(e)
    if per:
        words.append(f"{', '.join(per)} {'is' if len(per) == 1 else 'are'} one key here, expanded per "
                     f"{' and per '.join(sorted(set(per.values())))} as <key>{SEP}<item> when a train's unit is resolved "
                     "(§5.2); records bind by the train's product then.")
    return params.Provided(title=f"{e.name} (" + (f"BioSTEAM's {e.biosteam}" if e.biosteam else
                                                  f"in-house {e.inhouse}") + ")",
                           specs=served_specs(e, ws), sources=sources, notes=words)


def _provider(ids: tuple[str, ...], req: ParamResolveRequest) -> params.Provided:
    train, unit = ids
    if req.train is not None:
        # OF-BLD-020 §5.2: the train sent with the request decides the unit's
        # type, its chemicals and its records (pureos/train_spec.py).
        from . import train_spec as _train

        return _train.provided(ids, req)
    if unit == "inlet":
        raise params.ScopeUnknown(f"the inlet of train {train} is resolved with its train: send the train as ?train= "
                                  "(JSON) or as the resolve's `train`")
    if not req.unitType:
        raise params.ScopeUnknown(
            f"pureOS's train units are served with their train (?train=, OF-BLD-020 §5.2), or by their unit type: "
            f"name the type of unit {unit} of train {train} with ?unitType=<catalogue id>")
    try:
        e = entry(req.unitType)
    except CatalogueUnknown as e:
        raise params.ParamRefused(str(e)) from None
    per = template_keys(e)
    bare = sorted({o.key for o in req.overrides if o.key in per})
    if bare:
        raise params.ParamRefused(
            f"{', '.join(bare)} is set per {' and per '.join(sorted({per[k] for k in bare}))}, as "
            f"{', '.join(f'{k}{SEP}<{per[k]}>' for k in bare)}, on a train's unit (§5.2); this scope holds the template")
    got = provided(e.id)
    return got._replace(title=f"Unit {unit} of train {train}: {got.title}")


params.register("pureos-unit", _provider, _static)


# ── the worker side (BioSTEAM imported inside, in the worker alone) ────


def _plain(v: Any) -> Any:
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return float(v)
    return str(v)


def _source_of(fn: Any) -> str:
    import inspect

    try:
        return inspect.getsource(fn)
    except (OSError, TypeError):
        return ""


def _constructor(cls: Any) -> dict[str, Any]:
    """The constructor's parameters (its `_init`'s, as `Unit.__init__` passes
    them on) and their signature defaults; ID, ins, outs and thermo are
    `Unit.__init__`'s own and not in it."""
    import inspect

    out = {}
    for name, p in inspect.signature(cls._init).parameters.items():
        if name == "self" or p.kind in (p.VAR_KEYWORD, p.VAR_POSITIONAL):
            continue
        out[name] = None if p.default is p.empty else p.default
    return out


def _class_default(cls: Any, name: str, sig: Any, source: str) -> tuple[Any, str]:
    """A constructor parameter's default as the class gives it: its
    signature's, unless the class reads a `_default_<name>` or
    `<name>_default` in place of a falsy one, or its `_init` puts a literal
    in place of None."""
    import ast

    owner = cls._init.__qualname__.split(".")[0]
    for attr in (f"_default_{name}", f"{name}_default"):
        if re.search(rf"\b{name}\s+or\s+self\.{attr}\b", source) and not sig and getattr(cls, attr, None) is not None:
            return getattr(cls, attr), f"{cls.__name__}.{attr} ({owner}._init reads {name} or it)"
    if sig is None:
        m = re.search(rf"self\.{name}\s*=\s*(.+?)\s+if\s+{name}\s+is\s+None\s+else\s+{name}\b", source)
        if m:
            try:
                return ast.literal_eval(m.group(1)), f"{owner}._init, in place of None"
            except (ValueError, SyntaxError):
                return None, f"{owner}._init: computed in place of None, decided at run time"
        for attr in (f"{name}_default", f"_default_{name}"):
            if getattr(cls, attr, None) is not None and re.search(rf"\b{attr}\b", source):
                return getattr(cls, attr), f"{cls.__name__}.{attr}"
        return None, f"{owner}._init's signature: None, which the class reads at run time"
    return sig, f"{owner}._init's signature"


def _choices_of(cls: Any, p: Param, chemicals: list[str], source: str) -> list[str] | None:
    from importlib import import_module

    c = p.choices
    if c is None:
        return None
    if isinstance(c, tuple):
        return list(c)
    if c == BOOL:
        return ["true", "false"]
    if c == CHEMS:
        return list(chemicals)
    if c.startswith("table:"):
        _, module, path = c.split(":")
        obj: Any = import_module(module)
        for part in path.split("."):
            obj = getattr(obj, part)
        items = list(obj.keys()) if hasattr(obj, "keys") else list(obj)
        return [str(i) for i in items if i]
    if c == "setter":
        import inspect

        for k in cls.__mro__:
            prop = k.__dict__.get(p.bst)
            if isinstance(prop, property) and prop.fset is not None:
                text = _source_of(prop.fset)
                found = re.findall(r"in\s*\(([^)]*)\)", text)
                words = re.findall(r"'([^']+)'", found[0]) if found else re.findall(r"==\s*'([^']+)'", text)
                return list(dict.fromkeys(words))
        raise LookupError(f"{cls.__name__} has no setter for {p.bst} to read its choices from")
    if c.startswith("init:"):
        # The words `_init` compares the argument against, in the spelling of
        # its signature's default where the class lowercases (MixerSettler's
        # model is 'LLE', compared as 'lle').
        name = c.partition(":")[-1]
        default = _constructor(cls).get(name)
        words = list(dict.fromkeys(re.findall(rf"\b{name}\s*==\s*'([^']+)'", source)))
        return [default if isinstance(default, str) and w == default.lower() else w for w in words]
    raise LookupError(f"there is no choice source {c!r}")


def _refuses(cls: Any, name: str) -> dict[str, Any] | None:
    """The value a property's setter raises at or below, read from its code."""
    import inspect

    attr = inspect.getattr_static(cls, name, None)
    if not isinstance(attr, property) or attr.fset is None:
        return None
    m = re.search(rf"if\s+{name}\s*<=\s*([0-9.eE+-]+)\s*:\s*raise\s+ValueError", _source_of(attr.fset))
    if not m:
        return None
    return {"atOrBelow": float(m.group(1)),
            "from": f"{cls.__name__}.{name}'s setter raises ValueError at or below it (read from its code)"}


def _own_split(cls: Any, name: str, chemicals: list[str]) -> dict[str, float]:
    """In the worker: the split a class fills itself when built with it
    unset, by chemical, read from a unit built so on a flowsheet of its own
    (the thermo set is the worker's)."""
    import biosteam as bst

    with bst.Flowsheet("pureos_catalogue_own_split"):
        unit = cls(None, **{name: None})
        got = dict(zip(unit.chemicals.IDs, (float(x) for x in getattr(unit, name))))
    return {c: got[c] for c in chemicals if c in got}


def read_class(type_id: str, cls: Any, chemicals: list[str]) -> dict[str, Any]:
    """In the worker: what the class takes and gives, read from its code at
    import — its constructor's parameters and their defaults, the class
    attributes the entry names, the choices its tables and setters list, what
    its setters refuse — beside the entry's keys. `cls` and `chemicals` are
    the worker's to hand in (the in-house class, or BioSTEAM's; the yeast
    program's chemical IDs). Never retyped: every value is the class's."""
    from importlib.metadata import version

    import biosteam  # noqa: F401  (the worker's; read for its version and its classes' modules)

    e = entry(type_id)
    source = _source_of(cls._init)
    ctor = _constructor(cls)
    signature = {name: _plain(sig) for name, sig in ctor.items()}
    constructor = {}
    for name, sig in ctor.items():
        value, where = _class_default(cls, name, sig, source)
        constructor[name] = {"value": _plain(value), "from": where}
    attributes = {}
    for p in e.params:
        if p.via == "attribute":
            attributes[p.bst] = {"value": _plain(getattr(cls, p.bst, None)), "from": f"{cls.__name__}.{p.bst}"}
    defaults = {}
    for p in e.params:
        if p.per or p.how:
            defaults[p.key] = {"value": None, "from": (f"{cls.__name__}'s {p.bst}, " + (p.how or "per " + str(p.per)))}
            if p.per == "component" and p.bst == "split" and "library-default" in p.rule:
                # §5.R (part a): a class that fills its split itself when none
                # is given (PressureFilter's table) is read by component.
                defaults[p.key] = {"value": None, "byComponent": _own_split(cls, p.bst, chemicals), "from": (
                    f"{cls.__name__}._init's own table in place of None, read from a {cls.__name__} built with its "
                    f"{p.bst} unset on the program's chemicals")}
            continue
        got = attributes.get(p.bst) if p.via == "attribute" else constructor.get(p.bst)
        defaults[p.key] = got or {"value": None, "from": f"{cls.__name__} names no {p.bst}"}
    choices = {}
    for p in e.params:
        found = _choices_of(cls, p, chemicals, source)
        if found is not None:
            choices[p.key] = found
    refuses = {}
    for p in e.params:
        if p.via == "argument" and p.per is None and not p.how:
            r = _refuses(cls, p.bst)
            if r is not None:
                refuses[p.key] = r
    return {
        "type": e.id, "unitClass": cls.__name__, "module": cls.__module__, "signature": signature,
        "constructor": constructor,
        "attributes": attributes, "defaults": defaults, "choices": choices, "refuses": refuses,
        "chemicals": list(chemicals),
        "versions": {"biosteam": version("biosteam"), "thermosteam": version("thermosteam")},
    }


def build_unit(type_id: str, cls: Any, ID: str, ins: Any, outs: Any, values: dict[str, Any]) -> Any:
    """In the worker: one unit of this type, built on the thermo set, from its
    values by catalogue key (`kwargs_of`); a partition table becomes the
    arrays BioSTEAM takes. §5.2's builder builds each unit of a train so."""
    import numpy as np

    kwargs, attrs = kwargs_of(type_id, values)
    for key, table in (("settler_data", "partition_coefficients"), ("partition_data", "K")):
        if key in kwargs:
            kwargs[key] = {**kwargs[key], table: np.array(kwargs[key][table], dtype=float)}
            if key == "settler_data":
                kwargs[key]["partition_IDs"] = tuple(kwargs[key]["partition_IDs"])
            else:
                kwargs[key]["IDs"] = tuple(kwargs[key]["IDs"])
    for key in ("LHK", "P"):
        if isinstance(kwargs.get(key), list):
            kwargs[key] = tuple(kwargs[key])
    unit = cls(ID, ins=ins, outs=outs, **kwargs)
    for k, v in attrs.items():
        setattr(unit, k, v)
    return unit


def unit_report(unit: Any, keys: Iterable[str]) -> dict[str, Any]:
    """In the worker: what a simulated unit holds, plain: its streams in and
    out (kg/hr by chemical), its design results, costs and utilities, and
    the value of each named attribute as the built unit holds it."""
    def flows(s: Any) -> dict[str, Any]:
        return {"id": s.ID or "", "massFlow": float(s.F_mass), "phase": str(s.phase),
                "massFlows": {i: float(m) for i, m in zip(s.chemicals.IDs, s.mass) if m}}

    held = {}
    for k in keys:
        try:
            held[k] = _plain(getattr(unit, k))
        except Exception as e:  # noqa: BLE001 (a property that cannot be read now is said so)
            held[k] = f"unreadable: {type(e).__name__}"
    return {
        "unitClass": type(unit).__name__, "ins": [flows(s) for s in unit.ins], "outs": [flows(s) for s in unit.outs],
        "design": {k: _plain(v) for k, v in unit.design_results.items()},
        "purchaseCost": float(unit.purchase_cost), "installedCost": float(unit.installed_cost),
        "utilityCost": float(unit.utility_cost or 0.0), "power": float(unit.power_utility.rate),
        "heatDuties": [float(h.duty) for h in unit.heat_utilities], "held": held,
    }


# ── the guard's reading (check:seed) ───────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--ids"]:
        print("usage: python -m openferment_core.pureos.catalogue --ids", file=sys.stderr)
        return 1
    print(json.dumps([{"id": e.id, "biosteamClass": e.biosteam, "inhouseClass": e.inhouse, "maps": list(e.maps)}
                      for e in UNIT_TYPES] + [{"id": vid, "leftOut": cls} for cls, (vid, _) in LEFT_OUT.items()]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
