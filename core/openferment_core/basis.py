"""The provenance of a computed value (OF-BLD-014 §3.1, E.4).

A computed value is a deterministic calculation whose every input names a
source. Its provenance follows from those sources and from nothing else: no
model output and no person sets it, and the browser shows what this function
returned. There is no TypeScript copy of the rule.

- Any input whose source is an `assumption` (a named person's value) or a
  `model-estimate` (a model's, ADR-006) makes the value `assumed`, which the
  product labels *Assumed · not measured*.
- Otherwise the value is the weakest of: `computed`; the provenance of every
  `record` input; `measured` for a `deposition` input; the provenance of every
  `artifact` input.
- `model` and `convention` inputs do not weaken it.

So a price resting on three assumptions is assumed, and it becomes a computed
value as records replace the assumptions.

A model's estimate never enters a record store (ADR-006): `refuse_estimates`
is what each store runs on what it is asked to keep.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .models import BasisSource, ComputedBasis, Origin, Override, weakest_provenance

# The sources whatever rests on is `assumed`: a named person's value and a
# model's estimate.
ASSUMED_KINDS = ("assumption", "model-estimate")

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


def override_source(o: Override) -> BasisSource:
    """An Override's source: a person's assumption or a model's estimate, as
    its origin says."""
    if o.origin == "model-estimate":
        return estimate_source(o.by, o.at, o.note)
    return assumption_source(o.by, o.at, o.note)


# "typed on <at>" or "estimated on <at>", then ": <note>" when there is one;
# an `at` may hold colons of its own (a time of day).
_STAMPED = re.compile(r"^(?:typed|estimated) on (\S+?)(?:: |$)")
# A basis source's kind, as ADR-006 names the origin it stands for. A
# deposition is a record a person made at the bench; a model file or a
# library's package is where a library default is read.
_ORIGIN_KINDS = {"record": "record", "deposition": "record", "artifact": "artifact", "model": "library-default",
                 "convention": "convention", "assumption": "person-assumption", "model-estimate": "model-estimate"}


def origin_of(source: BasisSource) -> Origin:
    """The origin (ADR-006) a basis source stands for: the record, artifact
    or library entry it names, the person or model, and the day stamped in
    its note."""
    stamped = _STAMPED.match(source.note or "")
    return Origin(kind=_ORIGIN_KINDS[source.kind], ref=source.id, by=source.by,
                  at=stamped.group(1) if stamped else None, note=source.note)


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
    """The provenance of a value computed on `basis` (E.4; ADR-006)."""
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
    return weakest_provenance(classes)
