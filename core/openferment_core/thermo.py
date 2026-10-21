"""thermosteam answers property questions (OF-BLD-019 §4.2, D9).

thermosteam is BioSTEAM's property engine: a database of chemicals with
their models for density, heat capacity, viscosity and vapour-liquid
equilibrium. It lives in the Proforma worker, which has it loaded already
(`workers/proforma_worker.py`, op `thermo_props`); this module never imports
it, and talks to it only through the worker's JSON contract.

A QUESTION NAMES A MIXTURE ON FILE, NEVER A NUMBER. Two kinds:

- a stream of a Proforma run: the run's artifact id and the stream's id. Its
  composition, temperature, pressure and phase are the stream table's row
  (`proforma.tables_of`), and the run is the answer's source, so the run's
  provenance enters the answer's.
- a preset the service fills:
  `ethanol-water-azeotrope` — the composition at which the library's own
  vapour-liquid equilibrium gives a vapour of the liquid's composition, at the
  library's default pressure, found in the worker;
  `beer-at-titre-of` an ethanol titre record — the record's own value through
  units.py into kg m⁻³, and in the worker the water–ethanol mass fraction at
  which that much ethanol stands in a cubic metre of the mixture at the
  mixture's own density. The record is a source, so its provenance enters.
  The beer's cells, residual sugar and dissolved CO2 are not in it, and the
  answer says so.

A temperature or pressure the question does not carry is the library's own
Stream default, said so in the basis and the answer. Every number the answer
holds is the library's, in the library's units; a chemical the library lacks
refuses the whole question in words naming it (`ThermoRefused`).

The answer is one `thermo_props` artifact (`artifacts.compute`): its basis
names the library and its version, every input with its source, and its
provenance is `basis_provenance`'s: `computed` for a preset of conventions,
the weakest of that and the record or the run otherwise.

    POST /api/thermo/props   computes (or returns the stored answer)
    GET  /api/thermo/props   the stored answer for the same question, or none;
                             it starts no simulator

A PRODUCT'S VOLATILITY (OF-BLD-020 §7.1, D12) is its own question and its
own artifact tool, `volatility`, beside `thermo_props`, so the contract above
is unchanged. `volatility(product)` names a product by id; `CHEMICALS` maps
it to the library's own name for it (ethanol → Ethanol), and a product with no
name there is missing, never guessed (`VolatilityMissing`, a 404). The worker
(op `volatility`) reads the library's normal boiling point (`Tb`) of the
chemical and of water, and searches the pair for a minimum-boiling azeotrope
at the library's default pressure with the search the
`ethanol-water-azeotrope` preset runs, generalised to the named chemical and
water: one found is the composition and temperature the library gives; none
found is said with the grid searched (`AZEOTROPE_SEARCH`, a convention named
in the basis). A chemical the library lacks is refused in words naming it
(`ThermoRefused`, a 422). pureOS's proposer (§7.2) reads it.

    POST /api/thermo/volatility   {product}: computes (or returns the stored answer)
    GET  /api/thermo/volatility   ?product=: the stored answer, or none; it
                                  starts no simulator
"""
from __future__ import annotations

from typing import Any

from .models import Artifact, BasisInput, BasisSource, Evidence, ThermoProps, ThermoPropsRequest, Volatility

TOOL = "thermo_props"
RUN = "proforma.run"
VERSION_WORDS = "thermo props 1"
STREAM = "stream"
AZEOTROPE = "ethanol-water-azeotrope"
BEER = "beer-at-titre-of"
PRESETS = (AZEOTROPE, BEER)
TITRE_FIELD = "ethanol_titre"
KG_M3 = "kg m⁻³"
# The library's own names for the two chemicals the presets ask about.
ETHANOL, WATER = "Ethanol", "Water"
LIBRARY_DEFAULT = "thermosteam's Stream default"
# What the evidence of an answer names, in the order a page shows them.
PROPERTIES = (
    ("density", "Density"),
    ("Cp", "Heat capacity"),
    ("viscosity", "Viscosity"),
    ("bubblePoint", "Bubble point"),
    ("dewPoint", "Dew point"),
)
BEER_LEAVES_OUT = ("the beer here is water and ethanol at the record's titre: its cells, residual sugar and dissolved "
                   "CO2 are not in it")


class ThermoRefused(ValueError):
    """The question cannot be answered as asked, in words."""


class ThermoNotFound(LookupError):
    """The run, the stream or the record the question names is not on file."""


def _installed(dist: str) -> str:
    from .proforma import _installed as installed

    return installed(dist)


def version() -> str:
    return f"{VERSION_WORDS} · thermosteam {_installed('thermosteam')}"


def _library_input() -> BasisInput:
    v = _installed("thermosteam")
    return BasisInput(name="library", value=f"thermosteam {v}", unit="", source=BasisSource(
        kind="model", id=f"thermosteam@{v}",
        note="BioSTEAM's property engine: its chemical database and its mixture and activity models, as shipped"))


# ── the question ─────────────────────────────────────────────────────────


def question(req: ThermoPropsRequest) -> tuple[str, dict[str, str]]:
    """(kind, its ids), or `ThermoRefused` saying what a question names.
    `beer-at-titre-of <record id>` in the preset alone is read as the two."""
    aid, sid = (req.artifactId or "").strip(), (req.streamId or "").strip()
    preset, rid = (req.preset or "").strip(), (req.recordId or "").strip()
    if preset.startswith(BEER + " ") and not rid:
        preset, rid = BEER, preset[len(BEER):].strip()
    if aid or sid:
        if preset or rid:
            raise ThermoRefused("name a run's stream (artifactId and streamId) or a preset (preset, and recordId for "
                                f"{BEER}), not both")
        if not (aid and sid):
            raise ThermoRefused("a stream is named by its run's artifact id and the stream's id, both")
        return STREAM, {"artifactId": aid, "streamId": sid}
    if preset == AZEOTROPE:
        if rid:
            raise ThermoRefused(f"{AZEOTROPE} names no record: its composition is the library's own")
        return AZEOTROPE, {}
    if preset == BEER:
        if not rid:
            raise ThermoRefused(f"{BEER} names an ethanol titre record (field {TITRE_FIELD}): give its id")
        return BEER, {"recordId": rid}
    if preset:
        raise ThermoRefused(f"there is no preset {preset!r}; the presets are {AZEOTROPE}, and {BEER} with an ethanol "
                            "titre record's id")
    raise ThermoRefused(f"name a run's stream (artifactId and streamId), or a preset: {AZEOTROPE}, or {BEER} with a "
                        "record id")


def _run_of(aid: str) -> Artifact:
    from . import artifacts

    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise ThermoNotFound(f"no artifact {aid!r} is on file here: a stream is read from a Proforma run's stream "
                             "table, so run the scenario in Proforma first") from None
    if art.tool != RUN:
        raise ThermoRefused(f"artifact {aid} is a {art.tool} artifact, not a Proforma run; a stream is read from a "
                            "run's stream table")
    return art


def _row(art: Artifact, sid: str):
    from . import proforma

    t = proforma.tables_of(art)
    row = next((s for s in t.streams if s.id == sid), None)
    if row is None:
        have = ", ".join(s.id for s in t.streams[:12]) + (" and more" if len(t.streams) > 12 else "")
        raise ThermoNotFound(f"run {art.id} has no stream {sid!r}" + (f"; its streams are {have}" if have else
                                                                       "; it kept no stream table"))
    if not any(v > 0 for v in row.massFlows.values()):
        raise ThermoRefused(f"stream {sid} of run {art.id} carries nothing in the run's base case")
    if row.phase not in ("l", "g", "s"):
        raise ThermoRefused(f"stream {sid} of run {art.id} is in phases {row.phase!r}, and the stream table keeps no "
                            "split by phase; thermosteam is asked about one phase and not asked to guess the split")
    return row, t.tableUnits


def _record(rid: str, pool: Any) -> dict[str, Any]:
    from . import units

    r = pool.record(rid) if pool is not None else None
    if r is None:
        raise ThermoNotFound(f"no record {rid!r} is in the evidence pool this reads: an ethanol titre extracted from a "
                             "thread Q paper and anchored to its sentence fills this")
    if r.get("field") != TITRE_FIELD:
        raise ThermoRefused(f"record {rid} is a {r.get('field')}, not an ethanol titre ({TITRE_FIELD}); "
                            f"{BEER} reads a titre")
    if not isinstance(r.get("value"), (int, float)) or isinstance(r.get("value"), bool):
        raise ThermoRefused(f"record {rid} holds no number to read")
    unit = r.get("unit") or units.field(TITRE_FIELD)["canonicalUnit"]
    try:
        units.convert(float(r["value"]), unit, KG_M3)
    except units.UnitError as e:
        raise ThermoRefused(f"record {rid}'s titre in {unit} does not convert to {KG_M3}: "
                            f"{units.explain_refusal(unit, KG_M3) or e}") from None
    return r


def basis_inputs(req: ThermoPropsRequest, pool: Any = None) -> tuple[list[BasisInput], dict[str, Any]]:
    """The answer's basis, and the records it names by id (for their
    provenance). Every number in it is read from what is on file."""
    kind, ids = question(req)
    lib = _library_input()
    default = BasisSource(kind="model", id=lib.source.id, note="the library's own default for a Stream nobody set it on")
    if kind == STREAM:
        art = _run_of(ids["artifactId"])
        row, tu = _row(art, ids["streamId"])
        src = BasisSource(kind="artifact", id=art.id, note="a stream of the run's stream table")
        flow_unit = tu.get("massFlow", "kg/hr")
        return [
            BasisInput(name="question", value=STREAM, unit="", source=BasisSource(
                kind="convention", note="a stream of a Proforma run, at its own temperature, pressure and phase")),
            BasisInput(name="stream", value=row.id, unit="", source=src),
            BasisInput(name="T", value=row.T, unit=tu.get("T", "K"), source=src),
            BasisInput(name="P", value=row.P, unit=tu.get("P", "Pa"), source=src),
            BasisInput(name="phase", value=row.phase, unit="", source=src),
            *(BasisInput(name=f"flow {c}", value=v, unit=flow_unit, source=src)
              for c, v in sorted(row.massFlows.items()) if v > 0),
            lib,
        ], {}
    if kind == AZEOTROPE:
        return [
            BasisInput(name="question", value=AZEOTROPE, unit="", source=BasisSource(
                kind="convention", note="the composition at which the library's own vapour-liquid equilibrium gives a "
                                        "vapour of the liquid's composition, at the library's default pressure: found in "
                                        "the worker by scanning the library's bubble point for the change of sign, then "
                                        "halving")),
            BasisInput(name="T", value=LIBRARY_DEFAULT, unit="K", source=default),
            BasisInput(name="P", value=LIBRARY_DEFAULT, unit="Pa", source=default),
            lib,
        ], {}
    r = _record(ids["recordId"], pool)
    return [
        BasisInput(name="question", value=BEER, unit="", source=BasisSource(
            kind="convention", note="water and ethanol at the record's titre: the record's value through units.py into "
                                    f"{KG_M3}, and the ethanol mass fraction at which that much ethanol stands in a cubic "
                                    "metre of the mixture at the mixture's own density as the library computes it; "
                                    + BEER_LEAVES_OUT)),
        BasisInput(name="titre", value=float(r["value"]), unit=r.get("unit") or "", source=BasisSource(kind="record", id=r["id"])),
        BasisInput(name="T", value=LIBRARY_DEFAULT, unit="K", source=default),
        BasisInput(name="P", value=LIBRARY_DEFAULT, unit="Pa", source=default),
        lib,
    ], {r["id"]: r}


# ── the computation (registered with artifacts) ─────────────────────────


def _named(inputs: list[BasisInput], name: str) -> Any:
    return next((i for i in inputs if i.name == name), None)


def _number(i: BasisInput | None) -> float | None:
    return float(i.value) if i is not None and not isinstance(i.value, str) else None


def _compute(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """The answer, from the basis alone: the worker's `thermo_props` on the
    mixture the basis names. Pure, so a replay recomputes it."""
    from . import proforma, units
    from .workers import WorkerError

    kind = str(_named(inputs, "question").value)
    T, P = _number(_named(inputs, "T")), _number(_named(inputs, "P"))
    head: dict[str, Any] = {"kind": kind}
    args: dict[str, Any] = {"T": T, "P": P}
    notes: list[str] = []
    if kind == STREAM:
        stream = _named(inputs, "stream")
        aid = stream.source.id
        args.update(components={i.name.removeprefix("flow "): float(i.value) for i in inputs if i.name.startswith("flow ")},
                    phase=str(_named(inputs, "phase").value))
        head.update(subject=f"stream {stream.value} of run {aid}", runArtifactId=aid, streamId=str(stream.value))
    elif kind == AZEOTROPE:
        args.update(components={}, solve={"kind": "azeotrope", "light": ETHANOL, "heavy": WATER})
        head.update(subject="the ethanol–water azeotrope", preset=AZEOTROPE)
    elif kind == BEER:
        titre = _named(inputs, "titre")
        c = units.convert(float(titre.value), titre.unit or units.field(TITRE_FIELD)["canonicalUnit"], KG_M3)
        args.update(components={}, solve={"kind": "titre", "solute": ETHANOL, "solvent": WATER, "kgPerM3": c})
        head.update(subject=f"water and ethanol at the titre of record {titre.source.id}", preset=BEER,
                    recordId=titre.source.id)
        notes.append(BEER_LEAVES_OUT)
    else:
        raise ThermoRefused(f"there is no question {kind!r}")
    try:
        said = proforma.call("thermo_props", args)
    except WorkerError as e:
        text = str(e)
        if text.startswith("Refused: "):  # the worker's refusal, in its words
            raise ThermoRefused(text.removeprefix("Refused: ")) from None
        raise
    out = {**said, **head, "notes": [*said.get("notes", []), *notes]}
    return ThermoProps.model_validate(out).model_dump(mode="json")


def _register() -> None:
    from . import artifacts

    artifacts.register(TOOL, version(), _compute)


def _register_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(TOOL, _register)


_register_lazy()


# ── what callers use ─────────────────────────────────────────────────────


def props(req: ThermoPropsRequest, pool: Any = None) -> Artifact:
    """Answer the question, or return the answer stored for it. The pool
    resolves a record id (the endpoint's reads archived programs too, since a
    person names the record; a tool passes its own)."""
    from . import artifacts

    inputs, records = basis_inputs(req, pool)
    return artifacts.compute(TOOL, inputs, records_by_id=records)


def stored(req: ThermoPropsRequest, pool: Any = None) -> Artifact | None:
    """The answer stored for this question, or None: a read, which starts no
    simulator. Its provenance is worked out from its inputs as they stand
    now, as an artifact row's is."""
    from . import artifacts
    from .basis import basis_provenance

    inputs, records = basis_inputs(req, pool)
    reg = artifacts.registered(TOOL)
    try:
        art = artifacts.get(artifacts.artifact_id(reg.tool, reg.version, inputs))
    except artifacts.ArtifactNotFound:
        return None
    now = basis_provenance(artifacts.basis_of(art), records, artifacts._artifacts_for(inputs))
    return art if now == art.provenance else art.model_copy(update={"provenance": now})


def output_of(art: Artifact) -> ThermoProps:
    if art.tool != TOOL:
        raise ThermoRefused(f"artifact {art.id} is a {art.tool} artifact, not a {TOOL} answer")
    return ThermoProps.model_validate(art.output)


def evidence_of(art: Artifact) -> list[Evidence]:
    """One Evidence a property the library answered, each citable by its own
    id (`<artifact id>:<property>`) and each carrying the artifact's basis, so
    a claim cites the one value it rests on."""
    from . import artifacts

    o = output_of(art)
    where = {"bubblePoint": "at its pressure", "dewPoint": "at its pressure"}
    out = []
    for key, what in PROPERTIES:
        v = getattr(o, key)
        if v is None:
            continue
        out.append(Evidence(
            id=f"{art.id}:{key}",
            label=f"{what} of {o.subject}, {where.get(key, 'at its temperature and pressure')}, as {o.library} computes it",
            value=v, unit=o.units.get(key, ""), provenance=art.provenance, basis=artifacts.basis_of(art), figure=None))
    return out


# ── a product's volatility (OF-BLD-020 §7.1, D12) ───────────────────────

VOLATILITY = "volatility"
VOLATILITY_WORDS = "thermo volatility 1"
# The library's own name for each product thermosteam is asked about, by the
# product id fermOS, geneOS and Proforma use (the shelf's products). A product
# not named here is missing: its volatility is not computed, and nothing is
# guessed from its name. The products seed carries no small molecule with a
# library name yet, and no ethanol entry.
CHEMICALS: dict[str, str] = {"ethanol": ETHANOL}
# An azeotrope is asked with water, the solvent a broth mostly is.
PARTNER = WATER
VOLATILITY_QUESTION = ("the chemical's normal boiling point as the library holds it (Tb), and whether the library's own "
                       "vapour-liquid equilibrium gives it and water a minimum-boiling azeotrope at the library's "
                       "default pressure")
AZEOTROPE_SEARCH = ("the lower-boiling chemical's mole fraction in the liquid, scanned on the worker's grid between "
                    "the two pure chemicals (both pure ends left out) for where its vapour's mole fraction turns from "
                    "above the liquid's to not, then halved: the ethanol-water-azeotrope preset's search. None found "
                    "means none on that grid at that pressure, and the answer names the grid (`searched`)")
# What the evidence of a volatility names, in the order a page shows them.
VOLATILITY_PROPERTIES = (
    ("boilingPoint", "Normal boiling point"),
    ("azeotrope", "Minimum-boiling azeotrope"),
    ("azeotropeMoleFraction", "The product's mole fraction at the minimum-boiling azeotrope"),
    ("azeotropeMassFraction", "The product's mass fraction at the minimum-boiling azeotrope"),
    ("azeotropeT", "Boiling temperature of the minimum-boiling azeotrope"),
)


class VolatilityMissing(ThermoNotFound):
    """The product names no chemical of the library here: the property is
    missing, not refused (§7.2's proposer says which property it lacks)."""


def volatility_version() -> str:
    return f"{VOLATILITY_WORDS} · thermosteam {_installed('thermosteam')}"


def chemical_of(product: str) -> str:
    """The library's own name for `product`, or `VolatilityMissing` in words."""
    pid = (product or "").strip()
    if not pid:
        raise ThermoRefused("a volatility names a product by its id")
    name = CHEMICALS.get(pid)
    if name is None:
        named = ", ".join(f"{p} → {c}" for p, c in sorted(CHEMICALS.items()))
        raise VolatilityMissing(f"product {pid!r} names no chemical of thermosteam's library here ({named} are named), "
                                "so its volatility is not computed: a product enters by the library's own name for it, "
                                "never by a guess from its name")
    return name


def volatility_inputs(product: str) -> list[BasisInput]:
    """A volatility's basis: the product, the library's name for it, the
    partner, the search and the library, every one named; no number of ours."""
    pid = (product or "").strip()
    chemical = chemical_of(pid)
    lib = _library_input()
    return [
        BasisInput(name="question", value=VOLATILITY, unit="", source=BasisSource(
            kind="convention", note=VOLATILITY_QUESTION)),
        BasisInput(name="product", value=pid, unit="", source=BasisSource(kind="convention", note="the product, by its id")),
        BasisInput(name="chemical", value=chemical, unit="", source=BasisSource(
            kind="convention", note="the library's own name for the product, from thermo.CHEMICALS")),
        BasisInput(name="partner", value=PARTNER, unit="", source=BasisSource(
            kind="convention", note="an azeotrope is asked with water, the solvent a broth mostly is")),
        BasisInput(name="azeotrope search", value=AZEOTROPE_SEARCH, unit="", source=BasisSource(kind="convention")),
        BasisInput(name="P", value=LIBRARY_DEFAULT, unit="Pa", source=BasisSource(
            kind="model", id=lib.source.id, note="the library's own default for a Stream nobody set it on")),
        lib,
    ]


def _compute_volatility(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """The answer, from the basis alone: the worker's `volatility` on the
    chemical and the partner the basis names. Pure, so a replay recomputes it."""
    from . import proforma
    from .workers import WorkerError

    product = str(_named(inputs, "product").value)
    chemical, partner = str(_named(inputs, "chemical").value), str(_named(inputs, "partner").value)
    try:
        said = proforma.call(VOLATILITY, {"chemical": chemical, "partner": partner, "P": _number(_named(inputs, "P"))})
    except WorkerError as e:
        text = str(e)
        if text.startswith("Refused: "):  # the worker's refusal, in its words
            raise ThermoRefused(text.removeprefix("Refused: ")) from None
        raise
    out = {**said, "product": product, "subject": f"{chemical} (product {product}) beside {partner}"}
    return Volatility.model_validate(out).model_dump(mode="json")


def _register_volatility() -> None:
    from . import artifacts

    artifacts.register(VOLATILITY, volatility_version(), _compute_volatility)


def _register_volatility_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(VOLATILITY, _register_volatility)


_register_volatility_lazy()


def volatility(product: str) -> Artifact:
    """The product's volatility, computed in the Proforma worker or returned
    as stored: one `volatility` artifact, `computed` (its inputs are the
    library and conventions). `VolatilityMissing` when the product names no
    chemical of the library here; `ThermoRefused` when the library lacks or
    cannot build the one it names; a `WorkerError` when the worker cannot
    answer."""
    from . import artifacts

    return artifacts.compute(VOLATILITY, volatility_inputs(product))


def stored_volatility(product: str) -> Artifact | None:
    """The volatility stored for the product, or None: a read, which starts
    no simulator."""
    from . import artifacts

    inputs = volatility_inputs(product)
    reg = artifacts.registered(VOLATILITY)
    try:
        return artifacts.get(artifacts.artifact_id(reg.tool, reg.version_for(inputs), inputs))
    except artifacts.ArtifactNotFound:
        return None


def volatility_of(art: Artifact) -> Volatility:
    if art.tool != VOLATILITY:
        raise ThermoRefused(f"artifact {art.id} is a {art.tool} artifact, not a {VOLATILITY} answer")
    return Volatility.model_validate(art.output)


def volatility_evidence(art: Artifact) -> list[Evidence]:
    """One Evidence a property the library answered (`<artifact id>:<key>`),
    each carrying the artifact's basis. Whether an azeotrope was found is its
    own evidence, its value the words `found` or `none found`; a property the
    library could not give is no evidence."""
    from . import artifacts

    o = volatility_of(art)
    out = []
    for key, what in VOLATILITY_PROPERTIES:
        v = getattr(o, key)
        if v is None:
            continue
        if key == "azeotrope":
            v = "found" if v else "none found"
        if key == "boilingPoint":
            of = f"{o.chemical} (product {o.product})"
        else:
            of = f"{o.chemical} (product {o.product}) and {o.partner}, " + (
                "at its pressure" if o.PSource == "given" else "at the library's default pressure")
        out.append(Evidence(
            id=f"{art.id}:{key}", label=f"{what} of {of}, as {o.library} computes it", value=v,
            unit=o.units.get(key, ""), provenance=art.provenance, basis=artifacts.basis_of(art), figure=None))
    return out
