"""pureOS's tools: `pureos_build` and `pureos_propose`.

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
                     (`pureos.propose`, for the product made in `host`, a
                     geneOS host id), kept as the model's

Ids and words only: every field is a string, a list of strings or a word, and
a number anywhere refuses the call, as the registry does for every tool (E.4‴
holds the schema to no numeric field, `check:tools` rule 6). D13 lists seven
inputs; the tree adds `unitId`, the unit `remove_unit` and `set_from_record`
act on, because `afterUnitId` names where a unit goes and not which one, and
`host`, which §7.2's proposer needs (the cells the product is made in).

Every action is a free write through `tools/writes.py` (the same function as
`pureos_write`'s `new_train`, `add_unit`, `remove_unit`, `set_from_record` and
`run_train`), at no gate, audited with the model as agent. The train itself is
kept on the service (`pureos.kept`, rows of the `trains` table), marked as
the model's; a person's trains are the project's rows the Builder keeps. The service holds no
person's value, so a value nothing binds waits at the run, and the call returns
the refusal's words: a person types it in pureOS → Builder.

`pureos_propose`: a train proposed by written rules, a read. Ids and words in
(a product's id, a host strain's id, an inlet's artifact id or
`<run artifact id>/<stream id>`, each a string, an empty one meaning none);
no field of its schema is numeric (E.4‴, `check:tools` rule 6), and a number
anywhere refuses the call as the registry does for every tool. The service
reads the product's class and the properties its class's rule splits on
(`pureos.proposer`: thermosteam's volatility, ProtParam on the entry's
sequence, where the products seed says the product is) and proposes a
`TrainSpec` whose units are catalogue types in order, every parameter at its
library default or waiting for a person, each unit with one reason naming the
rule, the property it read and the artifact that holds it; or none, naming
each missing property.

It keeps nothing but the property artifacts §7.1's functions keep, and it is
no write: the proposal goes to a person (pureOS → Builder), and no run starts
from it. The summary names each unit's rule and property and the artifact
ids, in words and ids alone; each property read comes back as its own
`Evidence` (`<artifact id>:<property>`), so a claim cites the property and its
value is read from the artifact, never stated; the whole proposal is in
`data`, which no model reads. Offered loose, the module tools' way.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import pureos
from ..models import ToolResult
from ..workers import WorkerCrashed, WorkerError, WorkerTimeout
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
    "propose": ("product", "host", "inletRef"),
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
    product: str = Field("", description=(
        "new: the product the train recovers, by its id (ethanol); empty takes a simulation inlet's own product. "
        "propose: the product's id, required (the proposer reads its class from it)."))
    host: str = Field("", description="propose: the host strain's id on geneOS's shelf of hosts, the cells the product "
                                      "is made in (the proposer's rules read where the product is made).")
    inletRef: str = Field("", description=(
        "new: the artifact the inlet is read from: a kept simulation's artifact id (its broth at harvest; its broth "
        "flow then waits for a person), a kept vessel design's artifact id (the harvest of the simulation it was "
        "designed for, the broth flow read from the design), or a kept run's stream as <artifact id>/<stream id> "
        "(stream_table lists a Proforma run's streams). propose: a kept simulation's artifact id (its broth at "
        "harvest) or a kept run's stream as <artifact id>/<stream id>, or empty for none (a person types the inlet "
        "in pureOS → Builder)."))
    recordsByParam: dict[str, list[str]] = Field(default_factory=dict, description=(
        "set_from_record: a parameter's key on the unit (split.Ethanol, P, and the rest) to the record ids that bind "
        "it, exactly those records (search_records returns them); ids only, never a value."))


def _build(inp: PureosBuildInput, ctx: ToolContext) -> ToolResult:
    from . import writes

    given = {k for k in ("trainId", "unitType", "afterUnitId", "unitId", "product", "host", "inletRef")
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
    return writes.propose_train(BUILD, inp.product, inp.host, inp.inletRef, "", ctx)


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
            "binds it; propose keeps the train the proposer's rules propose for the product (its id) made in host (a "
            "host strain id), its inlet a kept simulation's id, a kept run's stream or none (inletRef). You never type a "
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
        writes=True,
    )
)


# ── pureos_propose (OF-BLD-020 §7.2) ──────────────────────────────────────

NAME = "pureos_propose"


class PureosProposeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str = Field(description=(
        "The product's id: a products seed entry (Dominion's molecules), or a product thermosteam's library is asked "
        "about by name (ethanol)."))
    host: str = Field(description="The host strain's id on geneOS's shelf of hosts: the cells the product is made in.")
    inletRef: str = Field(default="", description=(
        "The train's inlet: a kept fermOS simulation's artifact id (its broth at harvest), or a kept run's artifact id "
        "and one of its streams as <artifact id>/<stream id>; an empty string for none (a person types the inlet)."))


def _run(inp: PureosProposeInput, ctx: ToolContext) -> ToolResult:
    from .. import artifacts

    try:
        p = pureos.propose(inp.product, inp.host, inp.inletRef or None)
        evidence = pureos.proposer.evidence(p)
    except (pureos.ProposeUnknown, pureos.ProposeRefused) as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    except artifacts.ArtifactDamaged as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{NAME} could not ask thermosteam: {e}")
    types = {u.id: u.type for u in (p.train.units if p.train else [])}
    return ToolResult(
        summary={
            "product": p.product,
            "host": p.host,
            "program": p.program,
            "productClass": p.productClass,
            "proposed": p.train is not None,
            "inlet": p.train.inlet.kind if p.train else None,
            "units": [{"unitId": r.unitId, "type": types.get(r.unitId), "rule": r.rule, "property": r.property,
                       "artifactId": r.artifactId, "why": r.words} for r in p.reasons],
            "missing": [m.model_dump() for m in p.missing],
            "propertyEvidence": [e.id for e in evidence],
            "notes": p.notes,
            "meaning": ("a train proposed by written rules, each naming the property it read; every parameter stays at "
                        "its library default or waits for a person in pureOS's Builder, and nothing runs until a person "
                        "fills what waits; each property is cited by its evidence id and its value read from it"),
        },
        evidence=evidence,
        data=p.model_dump(mode="json"),
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "Propose a downstream train for a product made in a host, by written rules that each name the property "
            "they read: a small molecule lighter than water by thermosteam's boiling points is distilled, then dried "
            "on a molecular sieve where thermosteam finds an azeotrope with water; a secreted protein is clarified, "
            "concentrated by ultrafiltration, captured and polished by chromatography (keyed on ProtParam's "
            "isoelectric point and molecular weight) and spray-dried; an intracellular one is harvested and disrupted "
            "first. Ids and words in: a product id, a host strain id, and optionally an inlet (a kept simulation's "
            "artifact id, or <run artifact id>/<stream id>). Returns the units in order, each with its rule, property "
            "and artifact, every parameter left at its library default or waiting for a person; or what property is "
            "missing. Each property read is one evidence id to cite. Proposes only: nothing runs."
        ),
        input_model=PureosProposeInput,
        run=_run,
        strict=False,
    )
)
