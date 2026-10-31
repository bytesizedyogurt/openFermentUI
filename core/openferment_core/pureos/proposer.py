"""pureOS proposes a train by rules that each name the property they read
(OF-BLD-020 §7.2, D12, D13, E.4‴).

`propose(product, host, inlet_ref=None, *)` reads a
product's class and the properties its class's rule splits on, and answers a
`TrainProposal`: a `TrainSpec` (pureos/train_spec.py) whose units are catalogue
types in order (pureos/catalogue.py), each with one reason naming the rule,
the property it read and the artifact that holds it; what is missing, by
property; and notes. It is re-exported as `pureos.propose`. (The module is
`proposer`, not `propose`: a submodule of that name would be shadowed by the
function the package re-exports, as `pureos.train` was in §5.2.)

A PROPOSAL TYPES NO VALUE (D12). Every unit's `params` and `records` are
empty: a parameter with a library default keeps it, and one with none waits
for a record or a person in pureOS's Builder, where a train runs only once a
person fills what waits. The one thing a rule writes besides the unit's type
is where an outlet goes (`onward`, `waste`), a word, where the catalogue's
default would send the product the wrong way (a harvest's cake carries an
intracellular product on). `validate(proposal.train)` passes for every
proposal; nothing here runs a train.

WHAT A RULE READS, AND WHERE IT IS HELD.

- The product's CLASS. A products catalogue entry (`_catalogue().products`,
  none until a store holds a catalogue) states it as its `category`, read as a word by
  `CLASS_OF_CATEGORY` (each protein category a protein; a human milk
  oligosaccharide, a terpene and a glycoside a small molecule; a biopolymer a
  polymer). A product the catalogue holds no entry for but thermosteam's
  library is asked about by name (`thermo.CHEMICALS`, ethanol tonight) is a
  small molecule when the library gives it a normal boiling point (`Tb`, the
  `volatility` artifact's `boilingPoint`): a chemical that boils as a pure
  compound. A class nobody states is missing, never guessed from a name. The
  host is a strain the catalogue holds (`_catalogue().strains`).
- SECRETED OR INTRACELLULAR (`location`), as a catalogue entry states it; an
  entry that states none leaves a protein or a polymer naming it missing.
- VOLATILITY: thermosteam's answer, one `volatility` artifact
  (`thermo.volatility`, §7.1): which of the product and water boils first
  (`lighter`, a word read from the two normal boiling points the same answer
  holds), and whether the library's own vapour-liquid equilibrium gives the
  pair a minimum-boiling azeotrope (`azeotrope`). What counts as volatile is
  that word, never a typed temperature. A product the library is not asked
  about here is missing (`VolatilityMissing`).
- MOLECULAR WEIGHT AND ISOELECTRIC POINT: Biopython's ProtParam on the
  sequence the product's entry carries, one `protparam` artifact
  (`protparam.of_product`, §7.1). No sequence: missing (`ProtParamMissing`).
- THE INLET'S pH, which decides with the isoelectric point which exchanger a
  protein binds. No inlet carries one here: a simulation's states are cells,
  sugar and product, a run's stream table keeps no pH, and a typed inlet takes
  concentrations, a temperature and a pressure. So a capture step's mode
  waits, and its reason says why.

THE RULES (`RULES`, each with its basis in words):

- small molecule, lighter than water → separate by boiling (`distillation`,
  the beer column); a flash drum (`flash`) is the single-stage step the rule
  also names, a person's choice in the Builder;
- and when thermosteam finds a minimum-boiling azeotrope with water → a
  dehydration step after it (`molecular-sieve`): the column's top cannot pass
  the azeotrope;
- small molecule, heavier than water → extraction into a solvent (`lle`), the
  rule's first; crystallisation (`crystallisation`) is its second, and no
  property read here (a solubility is not) says which, so the first is
  proposed and the reason names the other;
- secreted protein → clarify (`centrifugation`, the liquid on; a clarifier the
  settling alternative), concentrate (`uf-df`, beside the molecular weight),
  capture (`chromatography`, its mode keyed on the isoelectric point against
  the inlet's pH; with no pH it waits), polish (`chromatography` again, beside
  the molecular weight, its mode waiting), formulate (`spray-dry`);
- intracellular protein → harvest (`centrifugation`, the cake on), disrupt
  (`cell-disruption`), clarify (`centrifugation`, the liquid on), then as
  secreted from concentrate on;
- intracellular polymer → harvest (`centrifugation`, the cake on), digest
  (`cell-disruption`, the cells broken to free the granules; extraction, `lle`,
  is the other step the rule names), wash (`centrifugation`, the solids on),
  dry (`drying-drum`, a wet solid's dryer).

A product whose class is not stated, or whose class's deciding property is
missing, proposes nothing (`train` is null) and names each missing property.
A rule that would need a typed number is left out: no membrane cut-off is
chosen from the molecular weight (it would need a typed ratio), and no
polishing mode is chosen from it (a size threshold would be typed).

KEPT: nothing but the property artifacts §7.1's functions keep (`volatility`,
`protparam`), each computed once and read back after. Rule 1 holds: no number
in this file, and no number in a reason's words.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from ..models import ProposalMissing, ProposalReason, TrainInlet, TrainProposal, TrainSpec, TrainUnitSpec

PROTEIN, SMALL, POLYMER = "protein", "small molecule", "polymer"
SECRETED, INTRACELLULAR = "secreted", "intracellular"
LOCATIONS = (SECRETED, INTRACELLULAR)
SIMULATION = "fermos.simulation"
AID = re.compile(r"[0-9a-f]{16}")
ONWARD, WASTE = "onward", "waste"

# The products catalogue's categories, read as a class (a word a category names).
CLASS_OF_CATEGORY = {
    "molecular_biology_enzyme": PROTEIN,
    "diagnostic": PROTEIN,
    "research_protein": PROTEIN,
    "food_protein": PROTEIN,
    "sweet_protein": PROTEIN,
    "structural_protein": PROTEIN,
    "industrial_enzyme": PROTEIN,
    "therapeutic_protein": PROTEIN,
    "hmo": SMALL,
    "terpene": SMALL,
    "glycoside": SMALL,
    "biopolymer": POLYMER,
}
CLASS_WHY = ("the products catalogue's category, read as a word: an enzyme, an antigen and a food, sweet, structural, "
             "research or therapeutic protein is a protein; a human milk oligosaccharide, a terpene and a glycoside "
             "are small molecules; a biopolymer is a polymer")
LIBRARY_CLASS_WHY = ("no products catalogue entry; thermosteam's library is asked about it by name (thermo.CHEMICALS) and "
                     "gives it a normal boiling point, so it is a chemical that boils as a pure compound: a small molecule")

# A unit's id in a proposal: a letter-led prefix by catalogue type and a count
# (BioSTEAM's ids take letters, digits and underscores). Structural words.
PREFIX = {"centrifugation": "C", "clarifier": "C", "distillation": "D", "flash": "F", "molecular-sieve": "MS",
          "lle": "X", "crystallisation": "K", "uf-df": "UF", "chromatography": "CH", "spray-dry": "SD",
          "cell-disruption": "H", "drying-drum": "DD"}


class ProposeUnknown(LookupError):
    """No such product: a 404."""


class ProposeRefused(ValueError):
    """A proposal that cannot be asked as asked, in words: a 422."""


@dataclass(frozen=True)
class Rule:
    id: str
    unit: str
    # What the rule does and why, in words; the basis of every reason it gives.
    words: str


RULES: dict[str, Rule] = {r.id: r for r in (
    Rule("volatile-separate", "distillation",
         "a small molecule that boils before water is separated from the broth by boiling: a column, BioSTEAM's "
         "BinaryDistillation, the beer column (a flash drum is the single-stage step the rule also names, a person's "
         "choice in the Builder)"),
    Rule("azeotrope-dehydrate", "molecular-sieve",
         "thermosteam's own vapour-liquid equilibrium gives the product and water a minimum-boiling azeotrope, which the "
         "column's top cannot pass, so a dehydration step takes the water left: a molecular sieve"),
    Rule("nonvolatile-extract", "lle",
         "a small molecule that boils after water stays in the liquid when water boils off, so it is captured by "
         "extraction into a solvent (crystallisation is the other step the rule names; no property read here, a "
         "solubility least of all, says which, so the rule's first is proposed)"),
    Rule("secreted-clarify", "centrifugation",
         "a secreted product is in the liquid once the cells are spun out: a solids centrifuge, the liquid on (a "
         "clarifier is the settling alternative)"),
    Rule("intracellular-harvest", "centrifugation",
         "an intracellular product stays in the cells, so the cells are harvested by a solids centrifuge: the cake on, "
         "the spent liquid to waste"),
    Rule("intracellular-disrupt", "cell-disruption",
         "the harvested cells are broken, by homogeniser or bead mill, so the product they hold moves into the liquid"),
    Rule("disrupted-clarify", "centrifugation",
         "the broken cells' debris is spun out of the liquid that now carries the product: the liquid on"),
    Rule("protein-concentrate", "uf-df",
         "a protein is held back by a membrane that passes water and small solutes: ultrafiltration concentrates it "
         "and diafiltration washes it; the molecular weight ProtParam gives is read beside it, and the membrane's "
         "sieving coefficients wait for a record or a person (a cut-off chosen from the weight would need a typed "
         "ratio, so none is chosen)"),
    Rule("protein-capture", "chromatography",
         "a protein is captured on a column by its charge, and which exchanger binds it is its isoelectric point "
         "(ProtParam) against the inlet's pH: above the inlet's pH the protein carries a net positive charge and a "
         "cation exchanger binds it, below it a net negative charge and an anion exchanger"),
    Rule("protein-polish", "chromatography",
         "a second column polishes what capture left; the molecular weight ProtParam gives is read for a separation "
         "by size, and the mode waits for a person (a size threshold would be typed, so none is chosen)"),
    Rule("protein-formulate", "spray-dry",
         "a protein leaves as a dry powder: a spray dryer turns the polished liquid into one"),
    Rule("polymer-harvest", "centrifugation",
         "a polymer the cells store stays in them, so the cells are harvested by a solids centrifuge: the cake on, the "
         "spent liquid to waste"),
    Rule("polymer-digest", "cell-disruption",
         "the harvested cells are broken open to free the polymer's granules (digest; extraction into a solvent, lle, "
         "is the other step the rule names)"),
    Rule("polymer-wash", "centrifugation",
         "the freed granules are spun out of what the cells left and washed: the solids on, the liquid to waste"),
    Rule("polymer-dry", "drying-drum",
         "the washed granules are a wet solid, which a drum dryer dries (a spray dryer dries a liquid)"),
)}


# ── what is on file ─────────────────────────────────────────────────────


def _catalogue() -> Any:
    """The products and strains on file. No store holds either catalogue yet,
    so both are empty and every proposal is refused for want of a host on
    file; tests supply them here."""
    return SimpleNamespace(products=(), strains=())


def _molecules() -> dict[str, dict[str, Any]]:
    return {str(m["id"]): m for m in _catalogue().products}


def _hosts() -> dict[str, dict[str, Any]]:
    return {str(h["id"]): h for h in _catalogue().strains}


def _program(product: str, entry: dict[str, Any] | None, host: dict[str, Any]) -> tuple[str, str | None]:
    """The chemical set the train builds on (`train_spec.chemical_set`): the
    one the product's entry or the host names when pureOS holds it, else the
    one pureOS holds, with words saying so."""
    from .train_spec import TrainRefused, chemical_set

    named = (entry or {}).get("program") or host.get("program")
    try:
        program = chemical_set(named)
    except TrainRefused as e:
        raise ProposeRefused(str(e)) from None
    if named == program:
        return program, None
    return program, (f"Neither product {product} nor host {host['id']} names a chemical set pureOS holds, so the "
                     f"train is built on the one it holds, {program}.")


def _inlet(product: str, inlet_ref: str | None) -> tuple[TrainInlet, str]:
    """The inlet a proposal names, as `TrainInlet`, with words for the notes:
    none (typed by a person in the Builder), a kept simulation's harvest by
    its artifact id, or a kept run's stream as `<artifact id>/<stream id>`, the
    form pureos_build's `inletRef` takes (`build.STREAM_SEP`)."""
    from .. import artifacts, proforma
    from . import train_spec
    from .build import STREAM_SEP

    ref = (inlet_ref or "").strip()
    if not ref:
        return TrainInlet(kind="typed"), ("No inlet is named: the train's inlet is typed, and its broth flow and "
                                          "composition wait for a person in the Builder.")
    aid, sep, stream = ref.partition(STREAM_SEP)
    if not AID.fullmatch(aid):
        raise ProposeRefused(f"an inlet is a kept artifact's id (sixteen hex letters and digits), or a kept run's id "
                             f"and one of its streams as <artifact id>{STREAM_SEP}<stream id>; {ref!r} is neither")
    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise ProposeRefused(f"there is no kept artifact {aid} here to take as the train's inlet") from None
    try:
        if art.tool == SIMULATION:
            if sep:
                raise ProposeRefused(f"simulation {aid}'s harvest is the inlet whole: name it by its id alone")
            made = (art.output or {}).get("product") if isinstance(art.output, dict) else None
            if made and made != product:
                raise ProposeRefused(f"simulation {aid} makes {made}; the proposal is for {product}")
            return TrainInlet(kind="simulation", ref=aid), (f"The inlet is simulation {aid}'s broth at harvest; its broth "
                                                            "flow waits for a vessel design of it or a person.")
        if art.tool in train_spec.STREAM_TOOLS:
            if not stream:
                raise ProposeRefused(f"run {aid} has a stream table: name the stream as {aid}{STREAM_SEP}<stream id>")
            if not any(s.id == stream for s in proforma.tables_of(art).streams):
                raise ProposeRefused(f"run {aid}'s stream table holds no stream {stream}")
            return TrainInlet(kind="run-stream", ref=aid, streamId=stream), (
                f"The inlet is stream {stream} of run {aid}, as its stream table holds it.")
    except train_spec.TrainRefused as e:
        raise ProposeRefused(str(e)) from None
    raise ProposeRefused(f"artifact {aid} is a {art.tool} artifact: an inlet is a kept fermOS simulation's harvest "
                         f"({SIMULATION}) or a stream of a kept run ({', '.join(train_spec.STREAM_TOOLS)})")


# ── the properties (§7.1's functions keep their artifacts) ─────────────


def _volatility(product: str) -> tuple[Any | None, str | None]:
    """(the volatility artifact, None), or (None, why it is missing)."""
    from .. import thermo

    try:
        return thermo.volatility(product), None
    except thermo.VolatilityMissing as e:
        return None, str(e)
    except thermo.ThermoRefused as e:
        raise ProposeRefused(str(e)) from None


def _protparam(product: str) -> tuple[Any | None, str | None]:
    from .. import protparam

    try:
        return protparam.of_product(product), None
    except protparam.ProtParamMissing as e:
        return None, str(e)
    except protparam.ProtParamRefused as e:
        raise ProposeRefused(str(e)) from None


def capture_mode(isoelectric_point: float, ph: float | None) -> tuple[str | None, str]:
    """The capture rule on the isoelectric point against the inlet's pH: the
    mode word it would choose and its words, or (None, why it waits). Two read
    numbers compared; no threshold of the proposer's own."""
    if ph is None:
        return None, ("the inlet carries no pH (a simulation's states are cells, sugar and product, a run's stream "
                      "table keeps no pH, a typed inlet takes none), so which exchanger binds the protein is not "
                      "decided and the mode waits for a person")
    if isoelectric_point > ph:
        return "iex", ("its isoelectric point is above the inlet's pH, so it carries a net positive charge there: a "
                       "cation exchanger (iex) binds it")
    if isoelectric_point < ph:
        return "iex", ("its isoelectric point is below the inlet's pH, so it carries a net negative charge there: an "
                       "anion exchanger (iex) binds it")
    return None, "its isoelectric point is the inlet's pH, where it carries no net charge: no exchanger binds it by charge"


# ── the proposal ───────────────────────────────────────────────────────


class _Train:
    """Units and reasons as the rules add them."""

    def __init__(self) -> None:
        self.units: list[TrainUnitSpec] = []
        self.reasons: list[ProposalReason] = []
        # The units under each id prefix so far: the next one's count is how many.
        self._by_prefix: dict[str, list[str]] = {}

    def add(self, rule_id: str, prop: str, artifact_id: str | None, words: str,
            outlets: dict[str, str] | None = None) -> None:
        rule = RULES[rule_id]
        prefix = PREFIX[rule.unit]
        same = self._by_prefix.setdefault(prefix, [])
        same.append(rule.unit)
        uid = f"{prefix}{len(same)}"
        self.units.append(TrainUnitSpec(id=uid, type=rule.unit, outlets=dict(outlets or {})))
        self.reasons.append(ProposalReason(unitId=uid, rule=rule.id, property=prop, artifactId=artifact_id,
                                           words=f"{rule.words}. Read: {words}"))


def _small(t: _Train, vol: Any, missing: list[ProposalMissing], notes: list[str]) -> bool:
    """The small-molecule rules on a volatility answer; False when its
    deciding property is missing."""
    from .. import thermo

    o = thermo.volatility_of(vol)
    if o.lighter is None:
        missing.append(ProposalMissing(property="boilingPoint", why=(
            f"thermosteam's answer ({vol.id}) does not say which of {o.chemical} and {o.partner} boils first: the "
            "library holds no normal boiling point for one of them")))
        return False
    if o.lighter == o.chemical:
        t.add("volatile-separate", "boilingPoint", vol.id,
              f"thermosteam's normal boiling point of {o.chemical} is below {o.partner}'s, so {o.chemical} is the "
              "lighter of the two")
        if o.azeotrope is True:
            t.add("azeotrope-dehydrate", "azeotrope", vol.id,
                  f"thermosteam finds a minimum-boiling azeotrope of {o.chemical} and {o.partner}")
        elif o.azeotrope is False:
            notes.append(f"thermosteam finds no minimum-boiling azeotrope of {o.chemical} and {o.partner} on the grid it "
                         "searched, so no dehydration step follows the column.")
        else:
            missing.append(ProposalMissing(property="azeotrope", why=(
                f"thermosteam's answer ({vol.id}) does not say whether {o.chemical} and {o.partner} form an azeotrope, "
                "so whether a dehydration step follows the column is not decided")))
        return True
    t.add("nonvolatile-extract", "boilingPoint", vol.id,
          f"thermosteam's normal boiling point of {o.chemical} is above {o.partner}'s, so water is the lighter of the two")
    return True


def _protein(t: _Train, location: str, pp: Any) -> None:
    from .. import protparam

    o = protparam.output_of(pp)
    if location == INTRACELLULAR:
        t.add("intracellular-harvest", "location", None, "the products catalogue's entry says the product stays in the cells",
              outlets={"cake": ONWARD, "liquid": WASTE})
        t.add("intracellular-disrupt", "location", None, "the products catalogue's entry says the product stays in the cells")
        t.add("disrupted-clarify", "location", None, "the product is in the liquid once the cells are broken")
    else:
        t.add("secreted-clarify", "location", None, "the products catalogue's entry says the cells secrete the product")
    t.add("protein-concentrate", "molecularWeight", pp.id, "ProtParam's molecular weight of the product's chain")
    _, why = capture_mode(o.isoelectricPoint, None)
    t.add("protein-capture", "isoelectricPoint", pp.id, f"ProtParam's isoelectric point of the product's chain; {why}")
    t.add("protein-polish", "molecularWeight", pp.id, "ProtParam's molecular weight of the product's chain")
    t.add("protein-formulate", "class", None, "the products catalogue's category says the product is a protein")


def _polymer(t: _Train) -> None:
    said = "the products catalogue's entry says the polymer stays in the cells"
    t.add("polymer-harvest", "location", None, said, outlets={"cake": ONWARD, "liquid": WASTE})
    t.add("polymer-digest", "location", None, said)
    t.add("polymer-wash", "class", None, "the products catalogue's category says the product is a polymer, a solid",
          outlets={"cake": ONWARD, "liquid": WASTE})
    t.add("polymer-dry", "class", None, "the products catalogue's category says the product is a polymer, a solid")


def propose(product: str, host: str, inlet_ref: str | None = None) -> TrainProposal:
    """A train for `product` made in `host`, proposed by the written rules:
    every unit at its library defaults or waiting, each with its reason; or
    none, naming what is missing. `ProposeUnknown` for a product neither the
    products catalogue nor thermo.CHEMICALS holds; `ProposeRefused` in words
    otherwise (an unknown host, an inlet that is not one, a sequence ProtParam
    cannot read, a chemical the library lacks).
    A worker that cannot answer raises its own error (the endpoint's 503)."""
    from .. import thermo
    from . import train_spec

    pid, hid = (product or "").strip(), (host or "").strip()
    if not pid:
        raise ProposeRefused("a proposal names its product by its id")
    if not hid:
        raise ProposeRefused("a proposal names its host by its id: the cells the product is made in")
    entry = _molecules().get(pid)
    chemical = thermo.CHEMICALS.get(pid)
    if entry is None and chemical is None:
        named = ", ".join(sorted(thermo.CHEMICALS))
        raise ProposeUnknown(f"there is no product {pid!r} in the products catalogue or among the "
                             f"chemicals thermosteam's library is asked about here ({named})")
    hosts = _hosts()
    h = hosts.get(hid)
    if h is None:
        raise ProposeRefused(f"there is no host {hid!r} among the strains on file: name the strain the product is made in by "
                             "its id")
    program, program_words = _program(pid, entry, h)
    inlet, inlet_words = _inlet(pid, inlet_ref)
    missing: list[ProposalMissing] = []
    notes: list[str] = [program_words] if program_words else []
    read: list[str] = []
    t = _Train()
    product_class: str | None = None
    vol = None
    if entry is not None:
        product_class = CLASS_OF_CATEGORY.get(str(entry.get("category") or ""))
        if product_class is None:
            missing.append(ProposalMissing(property="class", why=(
                f"product {pid}'s category, {entry.get('category')!r}, names no class the rules read ({CLASS_WHY})")))
        else:
            notes.append(f"{pid} is a {product_class}: {CLASS_WHY}.")
    else:
        vol, why = _volatility(pid)
        if vol is None:  # unreachable while CHEMICALS names it, said all the same
            missing.append(ProposalMissing(property="volatility", why=str(why)))
        else:
            read.append(vol.id)
            if thermo.volatility_of(vol).boilingPoint is None:
                missing.append(ProposalMissing(property="class", why=(
                    f"product {pid} has no products catalogue entry, and thermosteam's answer ({vol.id}) holds no normal "
                    "boiling point for it, so nothing states its class")))
            else:
                product_class = SMALL
                notes.append(f"{pid} is a {SMALL}: {LIBRARY_CLASS_WHY}.")
    location = str(entry.get("location") or "") if entry else ""
    if product_class == SMALL:
        if vol is None:
            vol, why = _volatility(pid)
            if vol is None:
                missing.append(ProposalMissing(property="volatility", why=str(why)))
            else:
                read.append(vol.id)
        if vol is not None:
            _small(t, vol, missing, notes)
    elif product_class in (PROTEIN, POLYMER):
        if location not in LOCATIONS:
            missing.append(ProposalMissing(property="location", why=(
                f"product {pid}'s products catalogue entry does not say whether the product is secreted or stays in the "
                "cells (its `location`), and the rules split on it: it enters the entry from a named source, never "
                "guessed")))
        if product_class == PROTEIN:
            pp, why = _protparam(pid)
            if pp is None:
                missing.append(ProposalMissing(property="sequence", why=str(why)))
            else:
                read.append(pp.id)
                if location in LOCATIONS:
                    _protein(t, location, pp)
        elif location == SECRETED:
            missing.append(ProposalMissing(property="location", why=(
                f"product {pid} is a polymer the cells secrete, and the rules hold one for a polymer the cells store "
                "alone")))
        elif location == INTRACELLULAR:
            _polymer(t)
    train = None
    if t.units:
        name = (entry or {}).get("name") or pid
        train = TrainSpec(id=f"proposed-{pid}", name=f"Proposed train for {name}", program=program, product=pid,
                          inlet=inlet, units=t.units)
        said = train_spec.validate(train)
        if said:  # a defect in a rule, never a person's: said whole
            raise ProposeRefused("the proposed train does not validate: " + "; ".join(said))
        notes += [inlet_words,
                  "Every unit is at its library defaults: the proposal types no value, and each parameter with no "
                  "default waits for a record or a person in the Builder, where the train runs once nothing waits."]
    else:
        notes.append("Nothing is proposed: the rules need the properties named as missing.")
    return TrainProposal(product=pid, host=hid, program=program, productClass=product_class, train=train,
                    reasons=t.reasons if train is not None else [], missing=missing, artifacts=read, notes=notes)


def evidence(proposal: TrainProposal) -> list[Any]:
    """The properties a proposal read, each its own `Evidence`
    (`<artifact id>:<property>`), from the artifacts it names."""
    from .. import artifacts, protparam, thermo

    out = []
    for aid in proposal.artifacts:
        art = artifacts.get(aid)
        if art.tool == thermo.VOLATILITY:
            out += thermo.volatility_evidence(art)
        elif art.tool == protparam.TOOL:
            out += protparam.evidence_of(art)
    return out
