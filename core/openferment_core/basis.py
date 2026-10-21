"""The provenance of a computed value (OF-BLD-014 §3.1, E.4).

A computed value is a deterministic calculation whose every input names a
source. Its provenance follows from those sources and from nothing else: no
model output and no person sets it, and the browser shows what this function
returned. There is no TypeScript copy of the rule.

- Any input whose source is an `assumption` makes the value `demo`, which the
  product labels *Modeled · not measured*.
- Otherwise the value is the weakest of: `computed`; the provenance of every
  `record` input; `measured` for a `deposition` input; the provenance of every
  `artifact` input.
- `model` and `convention` inputs do not weaken it.

So a price resting on three assumptions is modeled, and it becomes a computed
value as records replace the assumptions.
"""
from __future__ import annotations

from typing import Any, Mapping

from .models import BasisSource, ComputedBasis, weakest_provenance

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
    whatever rests on it `demo`."""
    return BasisSource(kind="assumption", by=by.strip(), note=f"typed on {at}" + (f": {note}" if note else ""))


def basis_provenance(
    basis: ComputedBasis,
    records_by_id: Mapping[str, Any],
    artifacts_by_id: Mapping[str, Any],
) -> str:
    """The provenance of a value computed on `basis` (E.4)."""
    if any(i.source.kind == "assumption" for i in basis.inputs):
        return "demo"
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
