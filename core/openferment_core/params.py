"""One parameter panel, declared in Python (OF-BLD-020 Phase 2, D2–D4).

Every model family, vessel design, catalogue unit and shelf flowsheet
declares its parameters once, as `ParameterSpec`s (models.py, mirrored in
src/data/types.ts through PAIRS). This module resolves them to
`ParameterValue`s, each naming where its value came from, and turns a
person's change into a named assumption. The browser renders what it is
served; no screen writes a form for a parameter of its own.

    parse_scope(scope)        what a scope names, or the refusal in words:
                                fermos:family:<family id>
                                fermos:vessel:<simulation artifact id>
                                fermos:forecast:<kinetic fit artifact id>
                                pureos:unit:<train id>:<unit id>
                                proforma:<scenario id>
    resolve(specs, sources, overrides, by=None)
                              each spec's value: an Override for its key wins
                              over everything (an `assumption` by the person)
                              where the spec's rule takes a person's value
                              (`checked`; §2.R), its interval's empty end the
                              value itself when one end is typed (`held`);
                              else the first entry of its `sourceRule` with a
                              candidate (fit, record:<field>, artifact,
                              simulation, assumption, convention,
                              library-default); else it waits, and its detail
                              names what would bind it
    bounds_check(spec, value) the warning in words when a value lies outside
                              the spec's bounds; the value is kept, never
                              clamped (D4)
    basis_inputs(specs, values)
                              one BasisInput per value with its source; an
                              override is an `assumption` naming the person
                              and what it rests on, so `basis_provenance`
                              makes the artifact `demo` (E.2‴)
    register(kind, provider, static=None)
                              a scope kind's provider: given the scope's ids
                              and the resolve request it returns
                              (title, specs, sources, notes); `static` yields
                              every spec it can name without a request, for
                              `check()`
    scope(name, req) / resolve_scope(name, req)
                              GET /api/params/{scope} and
                              POST /api/params/{scope}/resolve: they integrate
                              nothing and keep nothing. A `proforma:` scope
                              binds only and starts no worker; a
                              `fermos:vessel:` scope reads BioSTEAM's defaults
                              through the Proforma worker, once per process,
                              and so starts the worker when it is cold (below)
    check()                   every statically named spec has a written
                              boundsReason (D4); `pnpm check:seed` runs
                              `python -m openferment_core.params --check`

This module registers the `proforma` provider; vessel.py registers
`fermos-vessel` (OF-BLD-020 §4.1), imported on first need
(`PROVIDER_MODULES`). The vessel scope's values are BioSTEAM's own defaults,
read in the Proforma worker, so a read of it starts the worker when it is
cold (and keeps its answer for the process's life). Its scope is
`proforma:<scenario id>`: a seed BioSTEAM scenario, whose flowsheet
`proforma.seed_scenarios` names, or a scenario made in a browser, which names
its shelf flowsheet in the request. Its specs are the flowsheet's
`FlowsheetInput`s; its values are what `proforma.bound` binds (records
through the aggregate gate, the fermOS fits a person chose), called, never
copied. OF-BLD-020 §3.1 registers `fermos-family`
(`fermos:family:<family id>`): a kinetics family's specs, bound from a
person's overrides and the family's stated conventions (fermos.py). §4.1
registers `fermos-vessel`. §3.3 registers `fermos-forecast`
(`fermos:forecast:<kinetic fit artifact id>`): a logistic_v0 fit's start
values and run length, which a forecast takes from the fitted run unless a
person names others. §5.1 registers `pureos-unit` in pureos/catalogue.py
(`pureos:unit:<train id>:<unit id>`, the unit's type named by the request's
`unitType` until trains are kept): a catalogue entry's specs, each value the
class's own default read in the Proforma worker (so a read may start it, once
per process and type), or waiting for a record or a named person.

Rule 1 holds here: no value in this file. A bound is a convention with its
reason written beside it (an ontology plausibility range read from
corpus.json, or a physical limit: nothing negative, a share between none and
the whole); a value comes from a record, a fit, a kept artifact, a stated
convention, a library's own default read from its code, or a named person.
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Callable, Iterable, Mapping, NamedTuple

from .models import (
    BasisInput,
    BasisSource,
    FlowsheetInfo,
    FlowsheetInput,
    Override,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    ParamResolveResult,
    ParamScope,
)


class ParamRefused(ValueError):
    """A malformed scope, or an override or request that cannot stand, in
    words: a 422."""


class ScopeUnknown(LookupError):
    """A well-formed scope no provider here knows: a 404."""


# ── scopes ─────────────────────────────────────────────────────────────

# An id inside a scope: letters, digits, dots, dashes and underscores, so a
# colon always separates and a scope never carries a path or a space.
_ID = r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
_FORMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fermos-family", re.compile(rf"fermos:family:({_ID})")),
    ("fermos-vessel", re.compile(rf"fermos:vessel:({_ID})")),
    ("fermos-forecast", re.compile(rf"fermos:forecast:({_ID})")),
    ("pureos-unit", re.compile(rf"pureos:unit:({_ID}):({_ID})")),
    ("proforma", re.compile(rf"proforma:({_ID})")),
)
SCOPE_WORDS = ("fermos:family:<family id>, fermos:vessel:<simulation artifact id>, "
               "fermos:forecast:<kinetic fit artifact id>, pureos:unit:<train id>:<unit id> or proforma:<scenario id>")
KIND_WORDS = {
    "fermos-family": "fermOS's model families",
    "fermos-vessel": "fermOS's vessel designs",
    "fermos-forecast": "fermOS's forecasts",
    "pureos-unit": "pureOS's train units",
    "proforma": "Proforma's scenarios",
}


def parse_scope(scope: str) -> tuple[str, tuple[str, ...]]:
    """The kind a scope names and its ids, or the refusal in words."""
    text = scope if isinstance(scope, str) else ""
    for kind, form in _FORMS:
        m = form.fullmatch(text)
        if m:
            return kind, m.groups()
    shown = text if len(text) <= 80 else text[:80] + "…"
    raise ParamRefused(f"a parameter scope is {SCOPE_WORDS}, each id letters, digits, dots, dashes and underscores; "
                       f"{shown!r} is none of them")


def scope_name(kind: str, *ids: str) -> str:
    """The scope string for a kind and its ids (parse_scope's inverse)."""
    prefix = {"fermos-family": "fermos:family", "fermos-vessel": "fermos:vessel", "fermos-forecast": "fermos:forecast",
              "pureos-unit": "pureos:unit", "proforma": "proforma"}[kind]
    name = ":".join((prefix, *ids))
    parse_scope(name)
    return name


# ── providers ──────────────────────────────────────────────────────────


class Provided(NamedTuple):
    """What a provider gives for one scope. `sources` maps each parameter
    key to a dict from a sourceRule entry to the candidate value that entry
    found (or None); a provider may add a `"waiting"` candidate whose detail
    says why nothing bound. `basis`, when a provider gives it, is what a run
    of the scope adds to its basis for the request's overrides, built by the
    function the run builds them with (OF-BLD-020 §2.R: Proforma's run writes
    every override's low and high and the line saying it read overrides);
    without it the resolve takes `basis_inputs` over the overridden values,
    which is how the vessel builds its own."""

    title: str
    specs: list[ParameterSpec]
    sources: dict[str, dict[str, ParameterValue | None]]
    notes: list[str]
    basis: list[BasisInput] | None = None
    # The keys the resolved values leave unread, each with why in words (a
    # fed-batch's mu_set under a constant feed): such a key waits for
    # nothing, and is served `not-read` (OF-BLD-020 §3.R, finding 16).
    unread: Callable[[list[ParameterValue]], dict[str, str]] | None = None
    # What a run of these resolved values would be refused for though nothing
    # waits, in the run's own words, or None: the resolve refuses with it
    # (a 422), by the function the run refuses with (OF-BLD-020 §8.R,
    # finding 14).
    refuses: Callable[[list[ParameterValue]], str | None] | None = None


Provider = Callable[[tuple[str, ...], ParamResolveRequest], Provided]
Static = Callable[[], Iterable[tuple[str, list[ParameterSpec]]]]

_PROVIDERS: dict[str, Provider] = {}
_STATIC: dict[str, Static] = {}


def register(kind: str, provider: Provider, static: Static | None = None) -> None:
    """Serve a scope kind. `static` yields (label, specs) for every scope the
    kind can name without a request, which `check()` reads."""
    if kind not in KIND_WORDS:
        raise ValueError(f"{kind!r} is not a scope kind: {', '.join(KIND_WORDS)}")
    _PROVIDERS[kind] = provider
    if static is not None:
        _STATIC[kind] = static


# The modules that register a provider beside this one (they import this
# module, so they are imported here on first need, never at the top):
# fermOS's vessel (OF-BLD-020 §4.1) and pureOS's unit catalogue (§5.1), whose
# module imports no BioSTEAM at its top.
PROVIDER_MODULES = ("vessel", "pureos.catalogue")


def _load_providers() -> None:
    from importlib import import_module

    for name in PROVIDER_MODULES:
        import_module(f"{__package__}.{name}")


def providers() -> list[str]:
    _load_providers()
    return list(_PROVIDERS)


def _provided(scope: str, req: ParamResolveRequest) -> tuple[str, Provided]:
    _load_providers()
    kind, ids = parse_scope(scope)
    provider = _PROVIDERS.get(kind)
    if provider is None:
        raise ScopeUnknown(f"this service serves no parameters for {KIND_WORDS[kind]} yet")
    return kind, Provided(*provider(ids, req))


def _not_read(got: Provided, values: list[ParameterValue]) -> list[ParameterValue]:
    """The values with each waiting one the others leave unread served as
    `not-read`, saying why, so a panel never marks it waiting while a run
    would not refuse for it (OF-BLD-020 §3.R, finding 16)."""
    if got.unread is None:
        return values
    unread = got.unread(values)
    return [v.model_copy(update={"origin": "not-read", "detail": unread[v.key]})
            if v.origin == "waiting" and v.key in unread else v for v in values]


def scope(name: str, req: ParamResolveRequest | None = None) -> ParamScope:
    """GET /api/params/{scope}: the scope's specs and their values as the
    service binds them now, with no override (the service keeps none)."""
    req = (req or ParamResolveRequest()).model_copy(update={"overrides": []})
    kind, got = _provided(name, req)
    values = _not_read(got, resolve(got.specs, got.sources, []))
    return ParamScope(scope=name, kind=kind, title=got.title, specs=got.specs, values=values,
                      waiting=[v.key for v in values if v.origin == "waiting"], notes=got.notes)


def resolve_scope(name: str, req: ParamResolveRequest) -> ParamResolveResult:
    """POST /api/params/{scope}/resolve: the values with a person's overrides
    laid on, what those overrides would add to a run's basis, and every
    value outside its bounds, in words. Runs nothing and keeps nothing."""
    stray = sorted({o.scope for o in req.overrides if o.scope != name})
    if stray:
        raise ParamRefused(f"an override names the scope it changes, and these were sent to {name}: {', '.join(stray)}")
    _, got = _provided(name, req)
    values = _not_read(got, resolve(got.specs, got.sources, req.overrides))
    why = got.refuses(values) if got.refuses is not None else None
    if why:
        raise ParamRefused(why)
    added = got.basis if got.basis is not None else basis_inputs(got.specs, [v for v in values if v.overriddenBy])
    return ParamResolveResult(
        scope=name, values=values, waiting=[v.key for v in values if v.origin == "waiting"],
        basisInputs=added, warnings=[v.outOfBounds for v in values if v.outOfBounds], notes=got.notes)


# ── resolution ─────────────────────────────────────────────────────────


def _num(x: float) -> str:
    return f"{x:g}"


def _origin_of(entry: str) -> str:
    return "record" if entry.startswith("record:") else entry


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def bounds_check(spec: ParameterSpec, value: Any, low: float | None = None, high: float | None = None) -> str | None:
    """Words when a value, or the low or high end of its interval, lies
    outside the spec's bounds; None inside them, for a word, and for a spec
    with no bounds. The value is kept as given (D4)."""
    if spec.min is None and spec.max is None:
        return None
    unit = f" {spec.unit}" if spec.unit else ""
    span = (f"{_num(spec.min)} to {_num(spec.max)}{unit}" if spec.min is not None and spec.max is not None
            else f"at least {_num(spec.min)}{unit}" if spec.min is not None else f"at most {_num(spec.max)}{unit}")
    outside = []
    for what, x in (("the value", value), ("its low end", low), ("its high end", high)):
        if not _is_number(x) or not math.isfinite(x):
            continue
        if (spec.min is not None and x < spec.min) or (spec.max is not None and x > spec.max):
            outside.append(f"{what}, {_num(x)}{unit}")
    if not outside:
        return None
    return (f"{spec.label}: {' and '.join(outside)}, lies outside its bounds, {span} ({spec.boundsReason}); "
            "it is kept as given and the basis records it")


def _waiting_words(spec: ParameterSpec) -> str:
    parts = []
    fields = [e.split(":", 1)[1] for e in spec.sourceRule if e.startswith("record:")]
    if "fit" in spec.sourceRule:
        parts.append("a fit a person chooses")
    if fields:
        parts.append("a record of " + " or ".join(fields) + " through the aggregate gate")
    if "artifact" in spec.sourceRule:
        parts.append("a kept artifact")
    if "simulation" in spec.sourceRule:
        parts.append("a kept simulation")
    if "assumption" in spec.sourceRule:
        parts.append("a named person's assumption")
    if "convention" in spec.sourceRule:
        parts.append("a stated convention")
    if "library-default" in spec.sourceRule:
        parts.append("the library's own default")
    return "waits for a source: " + (", ".join(parts) if parts else "none is declared")


def unstamped(o: Override) -> str | None:
    """Why an override cannot stand for want of when it was typed, or None:
    the panel's resolve and a run refuse it in these words alike (§2.R,
    finding 5: the run kept one, and its basis named no day)."""
    return None if (o.at or "").strip() else f"the override of {o.key} says when it was typed"


def held(value: Any, low: float | None, high: float | None) -> tuple[float | None, float | None]:
    """An override's interval as every reader takes it (OF-BLD-020 §2.R,
    findings 1 and 14): one end typed and the other left empty, the empty
    end is the value itself, so the range runs from the end typed to the
    value; with neither end typed the value is held at itself and both stay
    empty (a run then holds it fixed, both ends the value). The resolve, the
    panel's row and a run (`proforma.named_values`) all read it so."""
    if low is None and high is None:
        return None, None
    return (value if low is None else low), (value if high is None else high)


def _takes_no_person(spec: ParameterSpec) -> str:
    """The refusal of an override of a parameter whose rule takes no named
    person's value, naming what the rule takes (§2.R, findings 2 and 18)."""
    if "convention" in spec.sourceRule:
        stated = f", {spec.convention}," if spec.convention is not None else ""
        return (f"{spec.key} is a convention{stated} that every run states in its basis, and takes no person's value: "
                "its source rule takes no assumption")
    if "library-default" in spec.sourceRule:
        return f"{spec.key} is the library's own default, read from its code, and takes no person's value"
    return (f"{spec.key} takes no person's value: its value comes from "
            + ", ".join(_origin_of(e) for e in spec.sourceRule))


def _checked(spec: ParameterSpec, o: Override, by: str | None) -> Override:
    """An override that can stand, with the person named and its interval
    as `held` reads it, or the refusal."""
    from .threadp import reviewer_refusal

    if "assumption" not in spec.sourceRule:
        raise ParamRefused(_takes_no_person(spec))
    name = (o.by or "").strip() or (by or "").strip()
    why = reviewer_refusal(name)
    if why:
        raise ParamRefused(f"the override of {spec.key} needs a person's name: {why}")
    when = unstamped(o)
    if when:
        raise ParamRefused(when)
    if spec.choices is not None:
        if not isinstance(o.value, str) or o.value not in spec.choices:
            raise ParamRefused(f"{spec.key} is one of {', '.join(spec.choices)}; {o.value!r} is not")
        if o.low is not None or o.high is not None:
            raise ParamRefused(f"{spec.key} is a choice of words and takes no low or high")
        return o.model_copy(update={"by": name})
    if not _is_number(o.value):
        raise ParamRefused(f"{spec.key} takes a number, not words")
    ends = [x for x in (o.value, o.low, o.high) if x is not None]
    if not all(math.isfinite(x) for x in ends):
        raise ParamRefused(f"the override of {spec.key} must be a finite number, with a finite low and high")
    if (o.low is not None and o.low > o.value) or (o.high is not None and o.value > o.high):
        raise ParamRefused(f"the override of {spec.key} must lie within its own low and high")
    low, high = held(o.value, o.low, o.high)
    return o.model_copy(update={"by": name, "low": low, "high": high})


def _from_override(spec: ParameterSpec, o: Override) -> ParameterValue:
    from .basis import assumption_source

    return ParameterValue(
        key=spec.key, value=o.value, low=o.low, high=o.high, source=assumption_source(o.by, o.at, o.note),
        origin="assumption", overriddenBy=o.by.strip(),
        detail=f"typed by {o.by.strip()} on {o.at}" + (f": {o.note}" if o.note else ""))


def _first(spec: ParameterSpec, cands: Mapping[str, ParameterValue | None]) -> ParameterValue:
    for entry in spec.sourceRule:
        found = cands.get(entry)
        if found is None and entry == "convention" and spec.convention is not None:
            found = ParameterValue(key=spec.key, value=spec.convention, source=BasisSource(kind="convention", note=spec.note),
                                   origin="convention", detail=spec.note)
        if found is None:
            continue
        origin = _origin_of(entry)
        return found.model_copy(update={"key": spec.key, "origin": origin, "overriddenBy": None,
                                        "identified": found.identified if origin == "fit" else None})
    why = cands.get("waiting")
    detail = _waiting_words(spec) + (f". {why.detail}" if why is not None and why.detail else "")
    return ParameterValue(key=spec.key, value=None, source=None, origin="waiting", detail=detail)


def checked(specs: list[ParameterSpec], overrides: Iterable[Override] | None, by: str | None = None) -> dict[str, Override]:
    """A scope's overrides that can stand, by key, each with its person named
    and its interval as `held` reads it; or the refusal in words: a key the
    scope does not have, a key twice, a parameter whose rule takes no named
    person's value, no person, no time, words where a number is needed, a
    choice not offered, a value outside its own low and high. `resolve` reads
    them through this, and a provider that binds with them (Proforma's) reads
    them through this first, so both refuse alike."""
    by_key: dict[str, ParameterSpec] = {}
    for spec in specs:
        if spec.key in by_key:
            raise ValueError(f"two parameters named {spec.key} in one scope")
        by_key[spec.key] = spec
    given: dict[str, Override] = {}
    for o in overrides or []:
        if o.key not in by_key:
            raise ParamRefused(f"there is no parameter {o.key} here; the parameters are {', '.join(by_key) or 'none'}")
        if o.key in given:
            raise ParamRefused(f"two overrides of {o.key}: one person's value a parameter")
        given[o.key] = _checked(by_key[o.key], o, by)
    return given


def resolve(specs: list[ParameterSpec], sources: Mapping[str, Mapping[str, ParameterValue | None]],
            overrides: Iterable[Override] | None, by: str | None = None) -> list[ParameterValue]:
    """Each spec's value. An Override for its key wins over every source and
    becomes an `assumption` by the person it names (or by `by`, when it names
    nobody; with neither it is refused), where the spec's rule takes a named
    person's value (`checked`). Otherwise the first entry of the spec's
    `sourceRule` with a candidate in `sources` wins, its origin the entry's;
    "convention" falls back on the spec's stated convention, with its note as
    the reason. With none, the value waits and says what would bind it.
    Every value outside the bounds is kept and flagged."""
    given = checked(specs, overrides, by)
    out = []
    for spec in specs:
        cands = sources.get(spec.key) or {}
        v = _from_override(spec, given[spec.key]) if spec.key in given else _first(spec, cands)
        lib = cands.get("library-default")
        if lib is not None:
            v.libraryDefault = lib.value
        v.outOfBounds = bounds_check(spec, v.value, v.low, v.high)
        out.append(v)
    return out


def basis_inputs(specs: list[ParameterSpec], values: Iterable[ParameterValue]) -> list[BasisInput]:
    """What a run's basis takes from these values (E.2‴): one input a value,
    named by its key, in its spec's unit, with its source; `<key> low` and
    `<key> high` beside it when it has an interval. An override's source is
    an `assumption` naming the person and what it rests on, so
    `basis_provenance` makes the artifact `demo`. A value bound to records
    is the statistic of those records (a `convention`), with one
    `<key> record` input per record naming it as its `record` source, so the
    records' own provenance enters. A waiting value adds nothing."""
    unit = {s.key: s.unit for s in specs}
    out: list[BasisInput] = []
    for v in values:
        if v.origin == "waiting" or v.value is None or v.source is None:
            continue
        u = unit.get(v.key, "")
        source = v.source
        if v.origin == "record" and v.recordIds:
            source = BasisSource(kind="convention", note=(f"the value of the records named '{v.key} record'"
                                                          + (f": {v.detail}" if v.detail else "")))
        out.append(BasisInput(name=v.key, value=v.value, unit=u, source=source))
        for part, x in (("low", v.low), ("high", v.high)):
            if x is not None:
                out.append(BasisInput(name=f"{v.key} {part}", value=x, unit=u, source=source))
        if v.origin == "record":
            out += [BasisInput(name=f"{v.key} record", value=rid, unit="", source=BasisSource(kind="record", id=rid))
                    for rid in v.recordIds]
    return out


# ── Proforma's scenarios (`proforma:<scenario id>`) ────────────────────

# The groups a flowsheet input falls into on the panel, by its kind.
_GROUPS = {"process": "Process", "economic": "Economics", "convention": "Conventions"}


def _ontology(field_id: str) -> dict[str, Any] | None:
    from . import units

    try:
        return units.field(field_id)
    except (FileNotFoundError, ValueError):  # no corpus exported here: no range is known
        return None


def _bounds(info: FlowsheetInfo, fi: FlowsheetInput, convention: Any) -> tuple[float | None, float | None, str]:
    """A flowsheet input's bounds and their reason (D4): the ontology's
    plausibility range of its first record field, converted into its unit,
    where it has one; else a physical limit."""
    from . import units

    if info.reference:
        return None, None, ("the package's own default, read back after the run: a reference biorefinery runs whole on "
                            "its package's defaults and takes no value here, so no range is offered")
    if fi.kind == "convention" and convention is not None and not _is_number(convention):
        return None, None, "a convention stated in words: it takes no number, so it has no bounds"
    why_not = ""
    if fi.fields:
        f = _ontology(fi.fields[0])
        if f is None:
            why_not = f" (the ontology's range for {fi.fields[0]} is not exported here)"
        else:
            lo, hi = f["range"]
            try:
                low, high = units.convert(float(lo), f["canonicalUnit"], fi.unit), units.convert(float(hi), f["canonicalUnit"], fi.unit)
            except (TypeError, ValueError):
                why_not = (f" (the ontology's range for {fi.fields[0]} is in {f['canonicalUnit']}, which does not "
                           f"convert into {fi.unit or 'a share'})")
            else:
                return low, high, (f"the ontology's plausibility range for {fi.fields[0]} ({f['name']}), "
                                   f"{_num(lo)} to {_num(hi)} {f['canonicalUnit']}, in {fi.unit}: the validation range "
                                   "that refuses an implausible extraction, not a result")
    if fi.dimension == "fraction":
        return 0.0, 1.0, "a physical limit: a share lies between none and the whole" + why_not
    return 0.0, None, f"a physical limit: no negative {fi.name}" + why_not


def _stated(flowsheet: str) -> dict[str, Any]:
    """The conventions a flowsheet's every run states in its basis, by name,
    as `proforma` writes them (the ethanol flowsheet's fuel grade)."""
    from . import proforma

    if flowsheet != proforma.ETHANOL:
        return {}
    return {b.name: b.value for b in proforma.ethanol_basis() if b.source.kind == "convention"}


def flowsheet_specs(info: FlowsheetInfo) -> list[ParameterSpec]:
    """A shelf flowsheet's inputs as ParameterSpecs, in the shelf's order.
    A process or economic input's rule: a fermOS fit a person chooses for
    titre, yield and productivity (it replaces the records, as
    `proforma.apply_fits` binds it), the records of each field in order, then
    a named person's assumption. A convention takes the value every run's
    basis states. A reference biorefinery's inputs are its package's own
    defaults, read back after the run."""
    from . import proforma

    stated = _stated(info.id)
    out = []
    for fi in info.inputs:
        convention = None
        if info.reference:
            rule = ["library-default"]
            group = "Package defaults"
        elif fi.kind == "convention":
            rule = ["convention"]
            convention = stated.get(fi.name)
            group = _GROUPS[fi.kind]
        else:
            # A fermOS fit or a kept simulation a person chose (§8.R: a
            # simulation is served as one, never as a fit).
            rule = (["fit", "simulation"] if fi.key in proforma.FIT_KEYS else []) + [f"record:{f}" for f in fi.fields] + ["assumption"]
            group = _GROUPS[fi.kind]
        low, high, reason = _bounds(info, fi, convention)
        out.append(ParameterSpec(
            key=fi.key, label=fi.name, symbol="", gloss=fi.note, dimension=fi.dimension, unit=fi.unit,
            min=low, max=high, group=group, sourceRule=rule,
            note=fi.note if fi.kind == "convention" else None, boundsReason=reason, convention=convention))
    return out


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _input_sources(inp, pool, feed: str) -> dict[str, ParameterValue | None]:
    """The candidates one bound ScenarioInput gives, by sourceRule entry."""
    from . import proforma

    flags = list(inp.flags)
    if inp.leftOutNoCarbon:
        flags.append(f"{_plural(inp.leftOutNoCarbon, 'record')} of its fields left out for naming no carbon source")
    if inp.leftOutOtherCarbon:
        flags.append(f"{_plural(inp.leftOutOtherCarbon, 'record')} left out for naming a carbon source other than {feed}")
    tail = ("; " + "; ".join(flags)) if flags else ""
    if inp.binding == "records" and inp.recordIds:
        field = (pool.records_by_id.get(inp.recordIds[0]) or {}).get("field") or ""
        unit = f" {inp.unit}" if inp.unit else ""
        span = (f"{_num(inp.value)}{unit}" if inp.low == inp.high
                else f"{_num(inp.low)} to {_num(inp.high)}{unit}, median {_num(inp.value)}")
        detail = f"{_plural(len(inp.recordIds), 'record')} of {field}, {span}{tail}"
        return {f"record:{field}": ParameterValue(key=inp.key, value=inp.value, low=inp.low, high=inp.high,
                                                  source=inp.source, origin="record", recordIds=list(inp.recordIds),
                                                  detail=detail)}
    if inp.binding == "artifact":
        aid = inp.source.id if inp.source else None
        if proforma.artifact_tool(aid) == "fermos.simulation":
            # §8.R (findings 0, 5, 11): a kept simulation is no fit, and no
            # run identified anything in it; it is served as a simulation,
            # identified null (D2), its basis naming each parameter's source.
            detail = (inp.source.note if inp.source and inp.source.note else "a fermOS simulation a person chose") + tail
            return {"simulation": ParameterValue(key=inp.key, value=inp.value, low=inp.low, high=inp.high,
                                                 source=inp.source, origin="simulation", identified=None, detail=detail)}
        detail = (inp.source.note if inp.source and inp.source.note else "a fermOS fit a person chose") + tail
        # proforma.apply_fits feeds no input from a fit whose μ or Xmax is
        # unidentified (fit_info refuses it), so a fit that feeds is one; a
        # simulation, which fit_info never so refuses, is served above.
        return {"fit": ParameterValue(key=inp.key, value=inp.value, low=inp.low, high=inp.high, source=inp.source,
                                      origin="fit", identified=True, detail=detail)}
    if flags:
        return {"waiting": ParameterValue(key=inp.key, value=None, source=None, origin="waiting", detail="; ".join(flags))}
    return {}


def feed_words(flowsheet: str) -> str:
    """The feed a flowsheet's records must name, as its left-out line says it
    (§2.R, finding 15): the ethanol flowsheet's glucose (FEED_CARBON); the
    PHA draft's rule admits a sugar or a hydrolysate (`proforma.SUGARS`)."""
    from . import proforma

    if flowsheet in proforma.FEED_CARBON:
        return " or ".join(sorted(proforma.FEED_CARBON[flowsheet]))
    if flowsheet == proforma.FLOWSHEET:
        return "a sugar or a hydrolysate"
    return "a fermentable sugar"


def _proforma(ids: tuple[str, ...], req: ParamResolveRequest) -> Provided:
    from . import evidence_pool, proforma
    from .flowsheets import shelf

    (scenario_id,) = ids
    seeds = {s["id"]: s for s in proforma.seed_scenarios()}
    if scenario_id not in seeds and not req.flowsheet and proforma._unrunnable_seed(scenario_id) is None:
        raise ScopeUnknown(f"there is no scenario {scenario_id}: the seed's BioSTEAM scenarios are "
                           f"{', '.join(seeds) or 'none'}, and a scenario made in a browser names the shelf flowsheet "
                           "it runs (?flowsheet=)")
    try:
        flowsheet = proforma.flowsheet_of(scenario_id, req.flowsheet)
        info = shelf.info(flowsheet)
        specs = flowsheet_specs(info)
        # OF-BLD-020 §2.R (findings 0, 9, 13): the scope binds as a run of it
        # binds. A person's overrides, checked as `resolve` checks them, are
        # laid on as the run lays them on (`proforma.named_values`): each wins
        # over the records and any fit for its input (`bound` takes no fit
        # there), and a fit's productivity beside a titre a person typed is
        # refused in the run's own words.
        typed, read = proforma.named_values(scenario_id, list(checked(specs, req.overrides).values()))
        proforma._check_keys(info, typed)
        # A scope names its scenario by id, so its records bind whatever the
        # program switch says, as a run's do (OF-BLD-016).
        pool = evidence_pool.load(include_archived=True)
        bound = proforma.bound(flowsheet, scenario_id=scenario_id, name=seeds.get(scenario_id, {}).get("name") or "",
                               host=req.host, assumptions=typed, pool=pool, fits=req.fits)
    except proforma.ScenarioRefused as e:
        raise ParamRefused(str(e)) from None
    feed = feed_words(flowsheet)
    sources = {inp.key: _input_sources(inp, pool, feed) for inp in bound.inputs}
    # What a run adds to its basis for these overrides, by the run's own
    # functions: each overridden input's value, low and high, then the line
    # saying the run read overrides (§2.R, findings 3 and 19).
    added = [b for inp in bound.inputs if inp.binding == "assumption" for b in proforma.assumption_inputs(inp)]
    name = seeds.get(scenario_id, {}).get("name")
    title = f"{name} ({info.title})" if name else info.title
    notes = [
        f"Bound as a run of {flowsheet} binds it: each process input to the records of its fields on its program's "
        "papers that pass the aggregate gate" + (f" and name {feed} as their carbon source" if flowsheet in proforma.FEED_CARBON else "")
        + ", converted into the input's unit; a fermOS fit a person chose replaces them for titre, yield and productivity.",
        "A person's override wins over the records and any fit for its input, here and in the run, which carries the "
        "overrides and names the person in its basis (OF-BLD-020 D3).",
    ]
    return Provided(title=title, specs=specs, sources=sources, notes=notes,
                    basis=added + proforma.assumptions_read(read))


def _proforma_static() -> Iterable[tuple[str, list[ParameterSpec]]]:
    from .flowsheets import shelf

    for fid, info in shelf.SHELF.items():
        yield f"proforma flowsheet {fid}", flowsheet_specs(info)


register("proforma", _proforma, _proforma_static)


# ── fermOS's model families (`fermos:family:<family id>`) ───────────────


def _fermos_family(ids: tuple[str, ...], req: ParamResolveRequest) -> Provided:
    from . import fermos

    return fermos.family_provided(ids, req)


def _fermos_family_static() -> Iterable[tuple[str, list[ParameterSpec]]]:
    from . import fermos

    yield from fermos._family_static()


register("fermos-family", _fermos_family, _fermos_family_static)


# ── fermOS's forecasts (`fermos:forecast:<kinetic fit artifact id>`) ────
#
# OF-BLD-020 §3.3: a forecast of a logistic_v0 fit starts from the fitted
# run's own start values and runs its own length; a person's other values are
# this scope's overrides (fermos.forecast_provided), so FermOSForecast.tsx
# renders no number box of its own (E.1‴).


def _fermos_forecast(ids: tuple[str, ...], req: ParamResolveRequest) -> Provided:
    from . import fermos

    return fermos.forecast_provided(ids, req)


def _fermos_forecast_static() -> Iterable[tuple[str, list[ParameterSpec]]]:
    from . import fermos

    yield from fermos._forecast_static()


register("fermos-forecast", _fermos_forecast, _fermos_forecast_static)


# ── the guard ──────────────────────────────────────────────────────────


def check() -> tuple[int, list[str]]:
    """Every spec a provider can name statically, read whole: each has a
    written boundsReason (D4), a known source rule, min no greater than max,
    and a key of its own in its scope. Returns the count read and the
    problems, in words."""
    _load_providers()
    problems: list[str] = []
    n = 0
    for kind, static in _STATIC.items():
        try:
            groups = list(static())
        except Exception as e:  # noqa: BLE001 (a spec that cannot be built is the finding)
            problems.append(f"{kind}: the specs could not be read: {e}")
            continue
        for label, specs in groups:
            keys: set[str] = set()
            for spec in specs:
                n += 1
                if not (spec.boundsReason or "").strip():
                    problems.append(f"{label}: {spec.key} has no boundsReason (OF-BLD-020 D4)")
                if spec.min is not None and spec.max is not None and spec.min > spec.max:
                    problems.append(f"{label}: {spec.key} has min above max")
                if spec.key in keys:
                    problems.append(f"{label}: two parameters named {spec.key}")
                keys.add(spec.key)
                try:
                    ParameterSpec.model_validate(spec.model_dump())
                except ValueError as e:
                    problems.append(f"{label}: {spec.key}: {e}")
    return n, problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--check"]:
        print("usage: python -m openferment_core.params --check", file=sys.stderr)
        return 2
    # Run as `python -m`, this file is `__main__`, a module apart from the
    # `params` the provider modules register with: check through that one.
    from importlib import import_module

    module = import_module(f"{__package__}.params")
    n, problems = module.check()
    for p in problems:
        print(f"✗ {p}")
    print(f"  parameters        {n} declared across {', '.join(sorted(module._STATIC))}; "
          f"{'every one has' if not problems else f'{len(problems)} problem(s), and not every one has'} a written bounds reason")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
