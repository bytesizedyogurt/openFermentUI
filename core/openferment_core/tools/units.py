"""`convert_units`: a record's own value in another unit (OF-BLD-014 §3.4).

The model names a record and a unit; the value is the record's, read from the
pool, and the conversion is `units.convert`, the same engine the browser runs.
The result is stored as an artifact and returned as one `Evidence` whose basis
names the record. A conversion the engine refuses comes back as the result's
`error`, in the engine's words.

The basis carries a second input, the unit asked for, as a convention: it
changes nothing about the provenance, and without it two conversions of one
record into two units would share an artifact id.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .. import artifacts, units
from ..models import BasisInput, BasisSource, Evidence, ToolResult
from . import Tool, ToolContext, register

NAME = "convert_units"


def version() -> str:
    """The engine's code and its tables, hashed: a change to either is a new
    version, and replay says so."""
    code = Path(units.__file__).read_bytes()
    t = units.tables()
    table = json.dumps({"table": t["table"], "si": t.get("si"), "refusals": t.get("refusals")}, sort_keys=True).encode()
    return f"units.py {hashlib.sha256(code).hexdigest()[:12]} · tables {hashlib.sha256(table).hexdigest()[:12]}"


def _convert(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """Pure: everything it needs is in the inputs."""
    value_in = next(i for i in inputs if i.name == "record value")
    target = next(i for i in inputs if i.name == "unit asked for")
    to_unit = str(target.value)
    value = units.convert(float(value_in.value), value_in.unit, to_unit)
    return {
        "label": f"{value_in.source.id} in {to_unit}",
        "value": value,
        "unit": to_unit,
        "from": {"value": value_in.value, "unit": value_in.unit},
    }


class ConvertUnitsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recordId: str = Field(description="The id of the record whose value to convert.")
    toUnit: str = Field(description="The unit to convert it to, written as the records write units.")


def _refusal(record: dict[str, Any], to_unit: str, e: units.UnitError) -> str:
    reason = e.reason or units.explain_refusal(str(record.get("unit") or ""), to_unit)
    said = f"{record['id']} is in {record.get('unit')}, which the unit engine will not convert to {to_unit}"
    return f"{said}: {reason}" if reason else f"{said}: {e}"


def _run(inp: ConvertUnitsInput, ctx: ToolContext) -> ToolResult:
    pool = ctx.pool
    record = pool.record(inp.recordId)
    if record is None:
        return ToolResult(error=f"There is no record {inp.recordId!r} Postdoc may cite.")
    value = record.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ToolResult(error=f"{inp.recordId} holds no number to convert; its value is {value!r}.")
    inputs = [
        BasisInput(
            name="record value",
            value=value,
            unit=str(record.get("unit") or ""),
            source=BasisSource(kind="record", id=record["id"]),
        ),
        BasisInput(
            name="unit asked for",
            value=inp.toUnit,
            unit="",
            source=BasisSource(kind="convention", note="the unit the caller asked for"),
        ),
    ]
    try:
        art = artifacts.compute(NAME, inputs, records_by_id=pool.records_by_id)
    except units.UnitError as e:
        return ToolResult(error=_refusal(record, inp.toUnit, e))
    out = art.output
    evidence = Evidence(
        id=f"ev-{art.id}",
        label=f"{record.get('fieldLabel') or record.get('field')}, {record['id']}, in {out['unit']}",
        value=out["value"],
        unit=out["unit"],
        provenance=art.provenance,
        basis=artifacts.basis_of(art),
    )
    return ToolResult(
        summary={
            "evidenceId": evidence.id,
            "recordId": record["id"],
            "converted": f"{record.get('value')} {record.get('unit')} to {out['unit']}",
            "provenance": art.provenance,
            "artifactId": art.id,
        },
        evidence=[evidence],
        recordIds=[record["id"]],
    )


# The version reads the unit tables (schema/units.json), so the tool registers
# on first use, after import has finished.
artifacts.register_lazy(NAME, lambda: artifacts.register(NAME, version(), _convert))

TOOL = register(
    Tool(
        name=NAME,
        description=(
            "Convert one record's own value into another unit with the platform's unit engine, which refuses a "
            "conversion that needs a quantity it does not have (a percentage of protein into a concentration, say) "
            "and says why. Returns one computed value with its basis, citable as evidence, or the refusal in words. "
            "Name the record by id and the unit in words; the value is read from the record."
        ),
        input_model=ConvertUnitsInput,
        run=_run,
    )
)
