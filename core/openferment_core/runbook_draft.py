"""A runbook Postdoc drafts, with every number written by the service
(OF-BLD-014 §9.2).

The agent names what to predict and what to measure, in ids and words: an
item points at one computed evidence item, or at records of one field, and a
measure names the item it tests. Nothing it sends is a number. This module
writes the numbers:

- an evidence item takes that artifact's value and interval: a ceiling becomes
  a bound, anything carrying an interval (a forecast's final value, a price)
  becomes an interval;
- a records item becomes an interval from the smallest to the largest of the
  records that pass the statistics gate, in the field's canonical unit, with
  their median as its value, and a basis sentence code writes.

Every id must have been returned earlier in the same run (the agent's
`SeenSet`), every unit must normalise, the product and strain must resolve,
and the title and every label must pass the number rule claims pass. A draft
with no valid item is refused whole; a refusal reaches the model as the
tool's error. The person adopts the draft and locks it on the runbook's page.
"""
from __future__ import annotations

import statistics
from typing import Any

from . import units
from .models import DraftItem, DraftMeasure, Measure, Prediction, Range, RunbookDraft
from .validate import find_number

# How a record-built prediction is graded: a three-way sort, not a probability.
# Three or more records give a range somebody measured more than once.
RECORDS_FOR_MEDIUM = 3


class DraftRefused(ValueError):
    """The draft cannot be assembled, in words the model can act on."""


def _no_number(what: str, text: str) -> None:
    hit = find_number(text)
    if hit:
        raise DraftRefused(f"{what} holds a number ({hit!r}); the service writes every number")


def _gate(record: dict[str, Any]) -> bool:
    from .proforma import _exclusion

    return _exclusion(record) is None


def _from_evidence(item: DraftItem, ev: Any, n: int) -> Prediction:
    base = dict(id=f"p{n}", label=item.label, unit=ev.unit, artifactId=_artifact_of(ev))
    basis = f"{ev.label} ({ev.provenance}); computed, kept as artifact {_artifact_of(ev)}"
    if ev.figure == "ceiling":
        return Prediction(**base, value=float(ev.value), confidence="medium", basis=basis, kind="bound")
    if ev.interval is not None:
        return Prediction(**base, value=float(ev.value), confidence="medium", basis=basis, kind="interval",
                          interval=Range(low=ev.interval.low, high=ev.interval.high))
    raise DraftRefused(f"evidence {ev.id} has neither a ceiling nor an interval, so it cannot become a prediction")


def _artifact_of(ev: Any) -> str:
    return getattr(ev.basis, "artifactId", None) or ev.id


def _from_records(item: DraftItem, pool: Any, n: int) -> tuple[Prediction | None, str | None]:
    spec = units.field(item.field)
    if spec is None:
        return None, f"there is no field {item.field!r}"
    canonical = spec.get("canonicalUnit")
    values, used = [], []
    for rid in item.recordIds:
        r = pool.record(rid)
        if r is None or r.get("field") != item.field or not _gate(r):
            continue
        try:
            values.append(units.to_canonical(float(r["value"]), r.get("unit") or canonical, item.field))
        except (TypeError, ValueError, units.UnitError):
            continue
        used.append(rid)
    if not values:
        return None, f"none of the records named for {item.label!r} is a {item.field} record that passes the statistics gate"
    lo, hi = min(values), max(values)
    basis = f"Range of {len(values)} reported value{'s' if len(values) != 1 else ''}: {', '.join(used)}"
    return Prediction(id=f"p{n}", label=item.label, value=statistics.median(values), unit=canonical,
                      confidence="medium" if len(values) >= RECORDS_FOR_MEDIUM else "low", basis=basis,
                      kind="interval", interval=Range(low=lo, high=hi), recordIds=used), None


def build(title: str, product_id: str, strain_id: str, items: list[DraftItem], measures: list[DraftMeasure],
          seen: Any, pool: Any, products: set[str], strains: set[str]) -> tuple[RunbookDraft, list[str]]:
    """The draft, and what was left out and why. Raises `DraftRefused`."""
    if seen is None:
        raise DraftRefused("draft_runbook runs inside Postdoc's loop, where the ids it names were returned")
    _no_number("the title", title)
    if product_id not in products:
        raise DraftRefused(f"there is no product {product_id!r}")
    if strain_id not in strains:
        raise DraftRefused(f"there is no strain {strain_id!r}")
    labels = [i.label for i in items]
    if len(set(labels)) != len(labels):
        raise DraftRefused("two items share a label; each prediction needs its own")
    left_out: list[str] = []
    predictions: list[Prediction] = []
    by_label: dict[str, Prediction] = {}
    for n, item in enumerate(items, start=1):
        _no_number(f"the label {item.label!r}", item.label)
        if bool(item.evidenceId) == bool(item.field or item.recordIds):
            left_out.append(f"{item.label}: name one evidence id, or a field with its record ids, and leave the other empty")
            continue
        if item.evidenceId:
            ev = seen.evidence.get(item.evidenceId)
            if ev is None:
                left_out.append(f"{item.label}: evidence {item.evidenceId} was not returned in this run")
                continue
            try:
                p = _from_evidence(item, ev, n)
            except DraftRefused as e:
                left_out.append(f"{item.label}: {e}")
                continue
        else:
            unseen = [r for r in item.recordIds if r not in seen.records]
            if unseen:
                left_out.append(f"{item.label}: records {', '.join(unseen)} were not returned in this run")
                continue
            p, why = _from_records(item, pool, n)
            if p is None:
                left_out.append(f"{item.label}: {why}")
                continue
        predictions.append(p)
        by_label[item.label] = p
    if not predictions:
        raise DraftRefused("no item could become a prediction: " + "; ".join(left_out))
    out_measures: list[Measure] = []
    for n, m in enumerate(measures, start=1):
        _no_number(f"the measure {m.label!r}", m.label)
        if units.normalize(m.unit) is None:
            raise DraftRefused(f"the measure {m.label!r} has a unit that does not normalise: {m.unit!r}")
        target = by_label.get(m.itemLabel)
        if target is None:
            left_out.append(f"measure {m.label}: it tests {m.itemLabel!r}, which is not a prediction in this draft")
            continue
        # Reconciliation compares the reading with the prediction as numbers,
        # so they must share a unit: a measure of another dimension cannot
        # test it, and one of the same dimension records in the prediction's
        # unit (§9.R).
        if not units.same_family(m.unit, target.unit):
            left_out.append(f"measure {m.label}: {m.unit} cannot test {m.itemLabel!r}, which is in {target.unit}")
            continue
        out_measures.append(Measure(id=f"m{n}", label=m.label, unit=target.unit, timepoint=m.timepoint, predictionId=target.id))
    return RunbookDraft(title=title, productId=product_id, strainId=strain_id, predictions=predictions,
                        measures=out_measures), left_out
