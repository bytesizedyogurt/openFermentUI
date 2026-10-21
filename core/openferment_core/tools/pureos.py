"""pureOS's tools.

`pureos_build` (OF-BLD-020 §5.4, D9, D13): Postdoc, or an outside assistant
over MCP, builds and runs a train from unit type names and record ids. One
action a call:

    new              a train for a product (its id), from the inlet a kept
                     artifact gives (`inletRef`: a kept simulation's artifact
                     id, its harvest; a kept vessel design's, the harvest of its
                     simulation with the broth flow read from the design; or a
                     kept run's stream as `<artifact id>/<stream id>`)
    add_unit         a unit of a catalogue type (`unitType`, an id of GET
                     /api/pureos/catalogue), after `afterUnitId` (`inlet` for the
                     first place; empty for the end)
    remove_unit      the unit `unitId` taken out
    set_from_record  a parameter of the unit `unitId` bound to exactly the
                     records named for it (`recordsByParam`: {key: [record ids]}),
                     each existing in the evidence pool, of a field the
                     parameter's source rule names, kept by the aggregate gate
                     and in a unit the parameter reads; else refused in words
                     naming the record and why
    run              the train run in the Proforma worker as the service binds
                     it: one `pureos.train_run` artifact, returned as one
                     Evidence whose id is the artifact's
    propose          a train proposed by OF-BLD-020 §7.2's rules
                     (`pureos.propose`), kept as the model's; refused in words
                     until §7.2 has landed

Ids and words only: every field is a string, a list of strings or a word, and
a number anywhere refuses the call, as the registry does for every tool (E.4‴
holds the schema to no numeric field, `check:tools` rule 6). D13 lists seven
inputs; the tree adds `unitId`, the unit `remove_unit` and `set_from_record`
act on, because `afterUnitId` names where a unit goes and not which one.

Every action is a free write through `tools/writes.py` (the same function as
`pureos_write`'s `new_train`, `add_unit`, `remove_unit`, `set_from_record` and
`run_train`), at no gate, audited with the model as agent. The train itself is
kept on the service (`pureos.kept`, `core/data/pureos-trains.json`), marked as
the model's; a person's trains stay in their browser. The service holds no
person's value, so a value nothing binds waits at the run, and the call returns
the refusal's words: a person types it in pureOS → Builder.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models import ToolResult
from . import Tool, ToolContext, register

BUILD = "pureos_build"

# The fields each action takes; another one given is refused in words, never
# passed on and never guessed at.
TAKES = {
    "new": ("product", "inletRef"),
    "add_unit": ("trainId", "unitType", "afterUnitId"),
    "remove_unit": ("trainId", "unitId"),
    "set_from_record": ("trainId", "unitId", "recordsByParam"),
    "run": ("trainId",),
    "propose": ("product", "inletRef"),
}


class PureosBuildInput(BaseModel):
    """No field is numeric and none is nullable: an empty string means
    "none"."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["new", "add_unit", "remove_unit", "set_from_record", "run", "propose"] = Field(description=(
        "new, add_unit, remove_unit, set_from_record, run or propose."))
    trainId: str = Field("", description="The train's id, as new or propose returned it (pureos_read lists the trains a "
                                         "model built, kind train); empty for new and propose.")
    unitType: str = Field("", description="add_unit: a catalogue unit type's id (centrifugation, flash, distillation, "
                                           "molecular-sieve and the rest; GET /api/pureos/catalogue lists them).")
    afterUnitId: str = Field("", description="add_unit: the unit the new one follows, inlet for the first place, or an "
                                             "empty string for the end.")
    unitId: str = Field("", description="remove_unit and set_from_record: the unit acted on, by its id in the train.")
    product: str = Field("", description="new and propose: the product the train recovers, by its id (ethanol); empty "
                                         "takes a simulation inlet's own product.")
    inletRef: str = Field("", description=(
        "new and propose: the artifact the inlet is read from: a kept simulation's artifact id (its broth at harvest; "
        "its broth flow then waits for a person), a kept vessel design's artifact id (the harvest of the simulation it "
        "was designed for, the broth flow read from the design), or a kept run's stream as <artifact id>/<stream id> "
        "(stream_table lists a Proforma run's streams)."))
    recordsByParam: dict[str, list[str]] = Field(default_factory=dict, description=(
        "set_from_record: a parameter's key on the unit (split.Ethanol, P, and the rest) to the record ids that bind "
        "it, exactly those records (search_records returns them); ids only, never a value."))


def _build(inp: PureosBuildInput, ctx: ToolContext) -> ToolResult:
    from . import writes

    given = {k for k in ("trainId", "unitType", "afterUnitId", "unitId", "product", "inletRef")
             if (getattr(inp, k) or "").strip()} | ({"recordsByParam"} if inp.recordsByParam else set())
    extra = sorted(given - set(TAKES[inp.action]))
    if extra:
        return ToolResult(error=f"{BUILD} refused: {inp.action} takes {', '.join(TAKES[inp.action])}; "
                                f"{', '.join(extra)} {'is' if len(extra) == 1 else 'are'} not one of them")
    if inp.action == "new":
        return writes.new_train(BUILD, inp.product, inp.inletRef, "", ctx)
    if inp.action == "add_unit":
        return writes.add_unit(BUILD, inp.trainId, inp.unitType, inp.afterUnitId, "", ctx)
    if inp.action == "remove_unit":
        return writes.remove_unit(BUILD, inp.trainId, inp.unitId, "", ctx)
    if inp.action == "set_from_record":
        return writes.set_from_record(BUILD, inp.trainId, inp.unitId,
                                      {k: list(v) for k, v in inp.recordsByParam.items()}, "", ctx)
    if inp.action == "run":
        return writes.run_train(BUILD, inp.trainId, "", ctx)
    return writes.propose_train(BUILD, inp.product, inp.inletRef, "", ctx)


BUILD_TOOL = register(
    Tool(
        name=BUILD,
        description=(
            "Build a downstream train and run it on BioSTEAM, one action a call, from ids and words. new starts a train "
            "for a product (its id) from the inlet a kept artifact gives (inletRef: a kept simulation's artifact id, a "
            "kept vessel design's, or a kept run's stream as <artifact id>/<stream id>) and returns its trainId. "
            "add_unit adds a unit of a catalogue type (unitType: centrifugation, flash, distillation, molecular-sieve "
            "and the rest) after afterUnitId (inlet for the first place, empty for the end); remove_unit takes unitId "
            "out; set_from_record binds a parameter of unitId to exactly the record ids recordsByParam names for it "
            "(each must be a record of the field the parameter binds from, kept by the aggregate gate; one that cannot "
            "bind is refused naming the record and why); run runs the train in the Proforma worker as the service "
            "binds it; propose keeps the train the proposer's rules propose for the product. You never type a "
            "number: every value binds from the records, the class's own default or a named person. A value nothing "
            "binds waits: the run then refuses naming each one, and nothing is kept; say in gaps that a person types "
            "it in pureOS → Builder. A run comes back as one evidence id (its artifact id) with each unit's recovery, "
            "the overall recovery and the product's share of the product stream read from it, and what bound each "
            "parameter in counts: cite a recovery or a purity by that id and never state it. The train is kept on the "
            "service as yours, every action marked so in the audit log; it spends no model money and is at no gate."
        ),
        input_model=PureosBuildInput,
        run=_build,
        strict=False,
    )
)
