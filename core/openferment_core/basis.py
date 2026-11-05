"""The provenance of a computed value (OF-BLD-014 §3.1, E.4).

A computed value is a deterministic calculation whose every input names a
source. Its provenance follows from those sources and from nothing else: no
model output and no person sets it, and the browser shows what this function
returned. There is no TypeScript copy of the rule.

- Any input whose source is an `assumption` (a named person's value) or a
  `model-estimate` (a model's, ADR-006) makes the value `assumed`, which the
  product labels *Assumed · not measured*; so does a record or an artifact it
  rests on that is assumed itself, or one the caller cannot find.
- Otherwise a value with at least one input that is a measurement (a reading
  a person deposited at the bench, `measurement_source`) is `measured`:
  beyond the library's defaults and the conventions, it rests on
  measurements, records and artifacts free of any assumption alone.
- Otherwise the value is the weakest of: `computed`; the provenance of every
  `record` input; `measured` for a `deposition` input that names a whole
  series (the readings a kinetic fit is made on, fermos.py); the provenance
  of every `artifact` input.
- `model` and `convention` inputs do not weaken it.

So a price resting on three assumptions is assumed; it becomes a computed
value as records replace the assumptions, and a measured one once records
and a deposition's readings stand where the assumptions stood. A library
plant's run at its package's own settings sets nothing and carries neither
label: it is computed, as its package computes it.

A model's estimate never enters a record store (ADR-006): `refuse_estimates`
is what each store runs on what it is asked to keep.

A value a request sets arrives as a typed quantity with its origin (an
`EngineInput`), and a resolver takes it as an `Override` of its scope:
`override_of` is the one converter between the two (alpha 2.2 D2). A value
that is a deposition's reading is looked up in the project's depositions
before it is converted (`resolved`, measurements.py), at every door.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .models import (READING_REF, BasisSource, ComputedBasis, EngineInput, Origin, Override, non_finite,
                     weakest_provenance)

# The sources whatever rests on is `assumed`: a named person's value and a
# model's estimate.
ASSUMED_KINDS = ("assumption", "model-estimate")
# The source kinds of a value a run sets, as its basis names them: a named
# person's assumption, a model's estimate and a deposition, of which the one
# a run sets is a reading (a measurement, `measurement_source`); a deposition
# naming a whole series is the record a kinetic fit rests on. Every reader of
# "a value this run set" asks `is_set`, which holds a deposition to being a
# reading: the values a library run hands its worker, its regression gate and
# its SFF file, a run's parameters, the comparisons and the tools' words. A
# record, an artifact, a library default and a convention are bound by the
# module that runs.
SET_KINDS = (*ASSUMED_KINDS, "deposition")
# The same three as an Origin and an Override name them (ADR-006) ...
SET_ORIGINS = ("person-assumption", "model-estimate", "measurement")
# ... and as a parameter's value names where it came from (ParamOrigin).
SET_PARAM_ORIGINS = ("assumption", "model-estimate", "measurement")

# A provenance `weakest_provenance` does not know sorts as the weakest there
# is. A record or artifact the caller cannot find gets this, so a missing
# source never reads as a strong one.
_UNKNOWN = "unknown"


def _provenance_of(item: Any) -> str:
    """The provenance an item carries, as a dict key or an attribute."""
    if item is None:
        return _UNKNOWN
    if isinstance(item, Mapping):
        p = item.get("provenance")
    else:
        p = getattr(item, "provenance", None)
    return p if isinstance(p, str) and p else _UNKNOWN


def assumption_source(by: str, at: str, note: str | None = None) -> BasisSource:
    """The source of a value a named person typed: a Proforma assumption, or
    an `Override` from the parameter panel (OF-BLD-020 D3). Its kind is
    `assumption`, the person is `by`, and `note` says the day it was typed and
    what it rests on, so the basis names both and `basis_provenance` makes
    whatever rests on it `assumed`."""
    return BasisSource(kind="assumption", by=by.strip(), note=f"typed on {at}" + (f": {note}" if note else ""))


def estimate_source(model: str, at: str, note: str | None = None) -> BasisSource:
    """The source of a number a model estimated (ADR-006): its kind is
    `model-estimate`, the model's id is `by`, and `note` says when it was
    estimated and what it rests on; whatever rests on it is `assumed`."""
    return BasisSource(kind="model-estimate", by=model.strip(),
                       note=f"estimated on {at}" + (f": {note}" if note else ""))


def measurement_source(ref: str, by: str, at: str, note: str | None = None) -> BasisSource:
    """The source of a value a deposition's reading gives a run (ADR-006's
    measurement): its kind is `deposition`, its id the reading,
    `<deposition id>/<entry id>`, `by` the person who deposited it, and
    `note` says when the reading was taken and any conversion into the
    parameter's unit, so the basis names the reading and `basis_provenance`
    makes whatever rests on it, records and defaults beside it, `measured`."""
    return BasisSource(kind="deposition", id=ref.strip(), by=by.strip(),
                       note=f"measured on {at}" + (f": {note}" if note else ""))


def override_source(o: Override) -> BasisSource:
    """An Override's source: a person's assumption, a model's estimate or a
    deposition's reading, as its origin says."""
    if o.origin == "model-estimate":
        return estimate_source(o.by, o.at, o.note)
    if o.origin == "measurement":
        return measurement_source(o.ref or "", o.by, o.at, o.note)
    return assumption_source(o.by, o.at, o.note)


class InputRefused(ValueError):
    """A value a request sets that its parameter cannot take, in words."""


def resolved(value: EngineInput, unit: str) -> EngineInput:
    """A value as a run takes it, in the parameter's unit `unit`: a
    deposition's reading looked up in the project's depositions, held to the
    lookup's rules and set in `unit`, its origin the reading's (who
    deposited it, when it was taken, any conversion in its note;
    measurements.py), or its refusal in words (an InputRefused); any other
    value as it stands. The one function every door that takes values calls
    before anything runs: `override_of` for every value it converts, a
    contract engine's run and a study scenario for theirs."""
    origin = value.quantity.origin
    if origin is None or origin.kind != "measurement":
        return value
    from .measurements import looked_up

    return looked_up(value, unit)


def override_of(scope: str, value: EngineInput, unit: str) -> Override:
    """The Override of `scope` a resolver takes for a value a request sets:
    the one converter from a typed quantity with its origin (alpha 2.2 D2).
    Its key is the input's name; its value, low and high are the
    quantity's; its by, at and note are the origin's; its origin is the
    person's assumption, the model's estimate or the deposition's reading
    the quantity names, a reading with its ref.

    An Override holds its value in the parameter's own unit and names no
    basis of its own, so the quantity is set in `unit`, the parameter's, and
    carries no basis. A reading is looked up first (`resolved`), which sets
    it in `unit` where its own unit converts into it: a page keeps a reading
    in its own value and unit (`Override.unit`) and sends it so, and the
    Override this returns holds the value set in `unit`, its own `unit`
    left empty. A quantity in another
    unit, one carrying a basis, one whose origin is a record, an artifact, a
    library default or a convention (the module that runs binds those
    itself), and one that does not say when it was set are each refused in
    words (InputRefused), as is a reading the lookup refuses, and a number
    that is NaN or infinite."""
    name, q = value.name, value.quantity
    infinite = non_finite(q)
    if infinite:
        raise InputRefused(f"{name}: {infinite}, and a number a run sets is finite; nothing runs on it")
    origin = q.origin
    if origin is None or origin.kind not in SET_ORIGINS:
        said = f"a {origin.kind} value" if origin is not None else "a value with no origin"
        raise InputRefused(f"{name}: a value a run sets is a person's assumption or a model's estimate, its origin "
                           f"naming who set it, or a deposition's reading, its origin naming the reading; {said} is "
                           "bound by the module that runs")
    if origin.kind == "measurement":
        q = resolved(value, unit).quantity
        origin = q.origin
        assert origin is not None  # the lookup answers the reading's origin
    if not (origin.at or "").strip():
        raise InputRefused(f"{name}: a value a run sets says when it was set (quantity.origin.at)")
    if q.unit != unit:
        raise InputRefused(f"{name} is set in {q.unit!r}, and the parameter's unit is {unit!r}")
    if q.basis is not None:
        raise InputRefused(f"{name}: a value a run sets is in its parameter's own unit, which says what it is "
                           f"reckoned on; this quantity also carries the basis {q.basis!r}")
    return Override(scope=scope, key=name, value=q.value, low=q.low, high=q.high, by=origin.by or "", at=origin.at,
                    note=origin.note, origin=origin.kind, ref=origin.ref if origin.kind == "measurement" else None)


# "typed on <at>", "estimated on <at>" or "measured on <at>", then ": <note>"
# when there is one; an `at` may hold colons of its own (a time of day).
_STAMPED = re.compile(r"^(?:typed|estimated|measured) on (\S+?)(?:: |$)")
_MEASURED = re.compile(r"^measured on \S")
# A basis source's kind, as ADR-006 names the origin it stands for. A
# deposition naming a whole series (a kinetic fit's readings) is a record a
# person made at the bench; one naming a reading is a measurement
# (`is_measurement`); a model file or a library's package is where a library
# default is read.
_ORIGIN_KINDS = {"record": "record", "deposition": "record", "artifact": "artifact", "model": "library-default",
                 "convention": "convention", "assumption": "person-assumption", "model-estimate": "model-estimate"}


def is_measurement(source: BasisSource) -> bool:
    """Whether a basis source is a deposition's reading a run set
    (`measurement_source`): a deposition naming one reading,
    `<deposition id>/<entry id>`, its note saying when the reading was
    taken. A deposition naming a whole series (the readings a kinetic fit is
    made on, fermos.py) is the bench's record the fit rests on."""
    return (source.kind == "deposition" and bool(READING_REF.fullmatch(source.id or ""))
            and bool(_MEASURED.match(source.note or "")))


def is_set(source: BasisSource) -> bool:
    """Whether a basis source is a value a run set (SET_KINDS): a person's
    assumption, a model's estimate, or a deposition's reading
    (`is_measurement`)."""
    return source.kind in ASSUMED_KINDS or is_measurement(source)


def origin_of(source: BasisSource) -> Origin:
    """The origin (ADR-006) a basis source stands for: the record, artifact
    or library entry it names, the reading a measurement is, the person or
    model, and the day stamped in its note."""
    stamped = _STAMPED.match(source.note or "")
    kind = "measurement" if is_measurement(source) else _ORIGIN_KINDS[source.kind]
    return Origin(kind=kind, ref=source.id, by=source.by, at=stamped.group(1) if stamped else None,
                  note=source.note)


def estimate_in(value: Any, path: str = "") -> str | None:
    """Where in a JSON value a model's estimate stands: an origin or a basis
    source whose kind is `model-estimate`, or a provenance `assumed`; None
    when there is none."""
    if isinstance(value, Mapping):
        if value.get("kind") == "model-estimate":
            return path or "the value"
        if value.get("provenance") == "assumed":
            return f"{path}.provenance" if path else "provenance"
        for k, v in value.items():
            found = estimate_in(v, f"{path}.{k}" if path else str(k))
            if found:
                return found
        return None
    if isinstance(value, (list, tuple)):
        for n, v in enumerate(value):
            found = estimate_in(v, f"{path}[{n}]")
            if found:
                return found
    return None


class EstimateRefused(ValueError):
    """A record store asked to keep a model's estimate (ADR-006)."""


def refuse_estimates(value: Any, store: str) -> None:
    """Refuse, in words, a value for a record store that holds a model's
    estimate or anything assumed (ADR-006; acceptance A6): an estimate may
    reach a scenario and a run, never a record."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    found = estimate_in(value)
    if found:
        raise EstimateRefused(f"{store} keeps records, and {found} is a model's estimate or rests on an assumption: "
                              "an estimate may reach a scenario or a run, never a record (ADR-006)")


def basis_provenance(
    basis: ComputedBasis,
    records_by_id: Mapping[str, Any],
    artifacts_by_id: Mapping[str, Any],
) -> str:
    """The provenance of a value computed on `basis` (E.4; ADR-006; the
    module's docstring): `assumed` when any input is a person's assumption
    or a model's estimate, or rests on one; else `measured` when any input is
    a measurement; else the weakest of its sources' classes, `computed` at
    best."""
    if any(i.source.kind in ASSUMED_KINDS for i in basis.inputs):
        return "assumed"
    classes = ["computed"]
    for i in basis.inputs:
        kind = i.source.kind
        if kind == "record":
            classes.append(_provenance_of(records_by_id.get(i.source.id or "")))
        elif kind == "deposition":
            classes.append("measured")
        elif kind == "artifact":
            classes.append(_provenance_of(artifacts_by_id.get(i.source.id or "")))
        # `model` and `convention` change nothing.
    found = weakest_provenance(classes)
    if found != "assumed" and any(is_measurement(i.source) for i in basis.inputs):
        return "measured"
    return found
