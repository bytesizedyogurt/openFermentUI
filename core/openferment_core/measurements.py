"""A deposition's reading as a value a run sets (ADR-006's measurement;
alpha 2.2 §6.3, D7).

A value a request sets may be a reading a person deposited at the bench: a
quantity whose origin is `{"kind": "measurement", "ref": "<deposition
id>/<entry id>"}`, its value and unit the reading's own.
Before anything runs, the service looks the reading up in the project's
depositions (project_state's depositions rows), in one function every door
that takes values calls (`basis.resolved`, which calls `looked_up`): the one
converter, basis.override_of, for each value it converts (a library plant's
run, fermOS, pureOS, Proforma, the parameter panels' resolve), a contract
engine's run, and a study scenario when it is made and when it runs. The
rules, each refusal in words (MeasurementRefused, an InputRefused, which each
door says as its own refusal: a 422 at a route, an error from a tool), and
nothing runs:

    held        the deposition and its entry are the project's own
    confirmed   a person confirmed the entry's number at the bench
    standing    the entry is the reading that stands for its measure: a
                later entry on the same measure with no time of its own
                corrects an earlier one with none, and a reading in a series
                (an entry with a sample time) is its own, corrected by a
                later entry at its time alone, as the bench's correction
                carries the time across (src/store.ts `amendEntry`); a
                later entry still waiting to be read back corrects it too,
                and the refusal says the newer number waits
    named       the person who deposited it is named (the row's maker, who
                first kept it, as biorepo.reviewer_refusal holds a name): a
                deposition a browser kept with no person set in Settings
                names nobody (project_state.UNNAMED)
    its own     the value and the unit the request carries are the entry's
                own, and the quantity carries no low, high or basis: a
                reading is one value
    its maker   `by` is the person who deposited the reading and `at` the
                time the entry was taken; each is filled from the rows when
                the request leaves it out, and a request naming another
                person or time is refused
    its unit    the entry's unit is the parameter's, or converts into it
                through units.convert to a finite number, the conversion
                stated in the value's note and so in the run's basis

What comes back is the value as the run takes it: in the parameter's unit,
its origin the reading's (`measurement`, its ref, its depositor, its time,
its note), which basis.measurement_source writes into the run's basis, so
the run's provenance is `measured` where nothing assumed stands beside it.

What a person chooses from is `readings(unit)` (GET
/api/depositions/readings, the readings NewScenarioDialog offers beside a
typed value, and a Proforma scenario's parameter panel on a row that takes a
person's value): every reading these rules let a run take in `unit`, each
with the runbook and the measure it was recorded against, its depositor and
its time.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from . import units
from .basis import InputRefused
from .models import READING_REF, DepositionReading, EngineInput, Origin, Quantity


class MeasurementRefused(InputRefused):
    """A deposition's reading a run may not take, in words."""


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _time(text: Any) -> datetime | None:
    """A time as an ISO 8601 string names it; None for anything else."""
    if not isinstance(text, str) or not text.strip() or any(ch.isspace() for ch in text.strip()):
        return None
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _shown(x: float) -> str:
    return f"{x:.12g}"


def corrected_by(deposition: dict[str, Any], entry: dict[str, Any]) -> str | None:
    """The id of the entry that corrects `entry` in its deposition, or None
    when `entry` is the reading that stands for its measure: the latest
    entry on the same measure that shares its sample time, or that has none
    when `entry` has none (the module's docstring). Entries are appended, so
    a later one stands after an earlier one in the list."""
    times = deposition.get("sampleTimes") if isinstance(deposition.get("sampleTimes"), dict) else {}
    entries = [e for e in deposition.get("entries") or [] if isinstance(e, dict)]
    at = next((n for n, e in enumerate(entries) if e is entry or e.get("id") == entry.get("id")), None)
    if at is None:
        return None
    when = times.get(entry.get("id"))
    later = [e for e in entries[at + 1:] if e.get("measureId") == entry.get("measureId")
             and times.get(e.get("id")) == when]
    return str(later[-1].get("id")) if later else None


def unnamed(maker: str) -> str | None:
    """Why a deposition kept by `maker` names no person who deposited its
    readings, in words that end a sentence about one of them; None when
    `maker` names one. A browser with no person set in Settings keeps its
    rows as project_state.UNNAMED, and a placeholder name is refused as
    biorepo.reviewer_refusal refuses it."""
    from .biorepo import reviewer_refusal
    from .project_state import UNNAMED

    name = (maker or "").strip()
    if not name or name == UNNAMED:
        return ("was kept by a browser with no person's name set, and a measurement names the person who took it: "
                "set your name in Settings before you deposit")
    why = reviewer_refusal(name)
    return f"was kept under the name {name!r}, which names nobody: {why}" if why else None


def reading(ref: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """The deposition, its entry and the person who deposited it, for a
    reading's ref `<deposition id>/<entry id>` in the current project; or
    the refusal in words, naming what the project holds."""
    from . import project_state

    if not READING_REF.fullmatch((ref or "").strip()):
        raise MeasurementRefused(f"a measurement names the reading it is as <deposition id>/<entry id>; {ref!r} is "
                                 "not one")
    deposition_id, _, entry_id = ref.strip().partition("/")
    held = project_state.deposited(deposition_id)
    if not held:
        raise MeasurementRefused(f"the project holds no deposition {deposition_id}, so it holds no reading {ref}")
    body, maker = held[0]
    entries = [e for e in body.get("entries") or [] if isinstance(e, dict)]
    entry = next((e for e in entries if e.get("id") == entry_id), None)
    if entry is None:
        n = len(entries)
        raise MeasurementRefused(f"deposition {deposition_id} holds no reading {entry_id}; it holds {n} "
                                 f"reading{'s' if n != 1 else ''}")
    return body, entry, (maker or "").strip()


def looked_up(value: EngineInput, unit: str) -> EngineInput:
    """A measurement as a run takes it, in the parameter's unit `unit`, held
    to the module's rules; refused in words (MeasurementRefused). A value
    that is no measurement comes back as it stands."""
    origin = value.quantity.origin
    if origin is None or origin.kind != "measurement":
        return value
    ref = (origin.ref or "").strip()
    try:
        deposition, entry, maker = reading(ref)
    except MeasurementRefused as e:
        raise MeasurementRefused(f"{value.name}: {e}") from None
    return _held_to_rules(value, unit, deposition, entry, maker)


def _held_to_rules(value: EngineInput, unit: str, deposition: dict[str, Any], entry: dict[str, Any],
                   maker: str) -> EngineInput:
    """`looked_up` once the reading is found: the module's rules from
    `confirmed` on, held to `entry` of `deposition`, kept by `maker`."""
    q, origin = value.quantity, value.quantity.origin
    assert origin is not None  # a measurement, as `looked_up` and `readings` hand it
    name, ref = value.name, (origin.ref or "").strip()
    if entry.get("confirmed") is not True:
        raise MeasurementRefused(f"{name}: reading {ref} waits for a person to confirm its number at the bench, and "
                                 "an unconfirmed number is no measurement")
    newer = corrected_by(deposition, entry)
    if newer is not None:
        later = next((e for e in deposition.get("entries") or [] if isinstance(e, dict) and e.get("id") == newer), {})
        now = ("which waits for a person to confirm its number at the bench" if later.get("confirmed") is not True
               else "the reading that stands for its measure now")
        raise MeasurementRefused(f"{name}: reading {ref} was corrected by {ref.partition('/')[0]}/{newer}, {now}")
    why = unnamed(maker)
    if why:
        raise MeasurementRefused(f"{name}: reading {ref} {why}")
    own, own_unit = entry.get("value"), entry.get("unit")
    if not _number(own) or not isinstance(own_unit, str):
        raise MeasurementRefused(f"{name}: reading {ref} holds no number in a unit")
    carried = [k for k in ("low", "high", "basis") if getattr(q, k) is not None]
    if carried:
        raise MeasurementRefused(f"{name}: a measurement is its reading's one value, and this quantity also carries "
                                 f"{' and '.join(carried)}")
    if not _number(q.value) or float(q.value) != float(own) or q.unit != own_unit:
        raise MeasurementRefused(f"{name}: reading {ref} is {_shown(float(own))} {own_unit}, and the value sent is "
                                 f"{q.value} {q.unit}: a measurement carries its reading's own value and unit")
    taken = entry.get("at")
    when = _time(taken)
    if when is None:
        raise MeasurementRefused(f"{name}: reading {ref} names no time it was taken")
    if (origin.by or "").strip() and origin.by.strip() != maker:
        raise MeasurementRefused(f"{name}: reading {ref} was deposited by {maker or 'nobody named'}, and the value "
                                 f"sent names {origin.by.strip()}")
    if (origin.at or "").strip() and _time(origin.at) != when:
        raise MeasurementRefused(f"{name}: reading {ref} was taken at {taken}, and the value sent names {origin.at}")
    if own_unit == unit:
        set_to, said = float(own), None
    else:
        try:
            set_to = units.convert(float(own), own_unit, unit)
        except units.UnitError as e:
            why = f" ({e.reason})" if e.reason else ""
            raise MeasurementRefused(f"{name} is denominated in {unit or 'no unit'}, and reading {ref} is in "
                                     f"{own_unit}, which does not convert into it: {e}{why}") from None
        if not math.isfinite(set_to):
            raise MeasurementRefused(f"{name}: reading {ref} is {_shown(float(own))} {own_unit}, which in {unit} is no "
                                     "finite number")
        said = (f"{_shown(float(own))} {own_unit} as deposited, {_shown(set_to)} {unit} in the parameter's unit "
                "(units.convert)")
    note = "; ".join(x for x in (said, (origin.note or "").strip()) if x) or None
    return EngineInput(name=name, quantity=Quantity(value=set_to, unit=unit, origin=Origin(
        kind="measurement", ref=ref, by=maker, at=str(taken).strip(), note=note)))


def _instant(text: str) -> float:
    """A time as the seconds it names, a time with no zone read as UTC, so
    readings sort by when they were taken."""
    when = _time(text)
    if when is None:
        return float("-inf")
    return (when if when.tzinfo else when.replace(tzinfo=timezone.utc)).timestamp()


def readings(unit: str | None = None) -> list[DepositionReading]:
    """The project's readings a run may take as measurements, the latest
    taken first: each entry of its depositions a person confirmed that
    stands for its measure, with the runbook and the measure it was recorded
    against as the project keeps them, the person who deposited it and the
    time it was taken (GET /api/depositions/readings; NewScenarioDialog and
    a Proforma scenario's parameter panel).
    With `unit`, the readings whose unit is `unit` or converts into it, each
    with its value in `unit` and the conversion in words. The lookup's own
    rules decide (`_held_to_rules`), so a reading listed is one a run takes
    in that unit, and one the lookup refuses is left out."""
    from . import project_state

    return held_readings(project_state.deposited(), project_state.kept("runbooks"), unit)


def held_readings(deposited: Iterable[tuple[dict[str, Any], str]], runbooks: Iterable[Any],
                  unit: str | None = None) -> list[DepositionReading]:
    """`readings` over the depositions `deposited` (each beside the person who
    deposited it, as project_state.deposited gives them) and the runbooks
    their measures are read from: what the module reads list
    (module_stores.py), so one rule answers what a run may take at every
    door."""
    books = {b.get("id"): b for b in runbooks if isinstance(b, dict)}
    out: list[DepositionReading] = []
    for deposition, maker in deposited:
        if not isinstance(deposition, dict):
            continue
        held = str(deposition.get("id") or "")
        book = books.get(deposition.get("runbookId")) or {}
        measures = {m.get("id"): m for m in book.get("measurementSchema") or [] if isinstance(m, dict)}
        times = deposition.get("sampleTimes") if isinstance(deposition.get("sampleTimes"), dict) else {}
        for entry in deposition.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            ref, own, own_unit = f"{held}/{entry.get('id')}", entry.get("value"), entry.get("unit")
            if not READING_REF.fullmatch(ref) or not _number(own) or not isinstance(own_unit, str):
                continue
            try:
                asked = EngineInput.model_validate({"name": "reading", "quantity": {
                    "value": own, "unit": own_unit, "origin": {"kind": "measurement", "ref": ref}}})
                got = _held_to_rules(asked, own_unit if unit is None else unit, deposition, entry,
                                     (maker or "").strip()).quantity
            except (MeasurementRefused, ValidationError):
                continue
            assert got.origin is not None and isinstance(got.value, (int, float))
            hours = times.get(entry.get("id"))
            measure = measures.get(entry.get("measureId")) or {}
            out.append(DepositionReading(
                ref=ref, depositionId=held, entryId=str(entry.get("id")),
                runbookId=deposition.get("runbookId") if isinstance(deposition.get("runbookId"), str) else None,
                runbook=book.get("title") if isinstance(book.get("title"), str) else None,
                measureId=str(entry.get("measureId") or ""),
                measure=measure.get("label") if isinstance(measure.get("label"), str) else None,
                value=float(own), unit=own_unit, at=got.origin.at or "", by=got.origin.by or "",
                hours=float(hours) if _number(hours) else None,
                inUnit=float(got.value) if unit is not None else None, note=got.origin.note))
    return sorted(out, key=lambda r: _instant(r.at), reverse=True)
