"""Emit JSON Schema for every openFerment entity, for the TypeScript generator.

One bundled document rather than one file per model, because the models share
types heavily — `FieldId` alone is referenced by nine of them — and a per-model
emission would give the TypeScript generator nine chances to name the same union
differently.

Two normalisations happen on the way out, both because the generator reads
draft-07 and Pydantic writes 2020-12. They rewrite the *schema*, never the
generated TypeScript: patching generated output is how a generated file quietly
stops being generated.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import models_json_schema

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openferment_core import schema as S

OUT = Path(__file__).resolve().parents[1] / "schema" / "openferment.schema.json"

# The types that are not models. `models_json_schema` takes models, so a union
# alias never reaches `$defs` on its own — the arms generate and the name that
# joins them does not — and a standalone enum reaches it only if some field
# happens to reference it. The application imports four of these by name, so
# without this they would have to be hand-written in TypeScript, which is
# precisely the two-schemas failure this phase exists to remove.
ALIASES: list[tuple[str, Any]] = [
    ("AssumptionBasis", S.AssumptionBasis),
    ("ChatMessage", S.ChatMessage),
    ("LessonBlock", S.LessonBlock),
    ("PublicationStatus", S.PublicationStatus),
    ("RefereeStatus", S.RefereeStatus),
    # Referenced by no field: `IngestStatus` spells the coupling as
    # `stage:{IngestStage}`, which JSON Schema cannot express, so the two enums
    # are written out separately and this one would otherwise vanish.
    ("IngestStage", S.IngestStage),
]

# Every entity the UI imports a type for. Listed explicitly rather than
# discovered by reflection: a model that nothing references is a model nobody
# noticed had been orphaned, and a list you have to edit is the cheapest place
# to notice.
ROOTS: list[type[BaseModel]] = [
    # corpus
    S.Paper,
    S.PaperSection,
    S.CoverageDispute,
    # ontology
    S.ParameterDef,
    S.RefuseConversion,
    # records
    S.ExtractionRecord,
    S.AuditEvent,
    S.RunOutput,
    S.RunResult,
    S.FalsePositive,
    S.CuratorNote,
    S.SIValue,
    S.GoldValue,
    S.CorrectedValue,
    S.ValueRange,
    # bio
    S.Strain,
    # protocol
    S.Protocol,
    S.ProtocolVersion,
    S.ProtocolReference,
    S.Material,
    S.StockSolution,
    S.Step,
    S.ResultField,
    S.DecisiveMeasurement,
    S.BaseBatch,
    S.EstimatedMinutes,
    S.Deviation,
    S.RunState,
    S.TimerState,
    S.RunOutcome,
    # econ
    S.ScenarioDim,
    S.ScenarioAssumption,
    S.Scenario,
    S.GridPointResult,
    S.SensitivityRow,
    # the frame a price is quoted in — see econ.py for why this is Python
    S.CostIndex,
    S.FxTreatment,
    S.RegionDeclared,
    S.RegionUndeclared,
    S.AccuracyStated,
    S.AccuracyUnstated,
    S.QuotationBasis,
    S.BasisRecord,
    S.BasisModel,
    S.BasisUnsourced,
    # learn
    S.Collection,
    S.CheckpointQuestion,
    S.NumericAnswer,
    S.Lesson,
    S.ProseBlock,
    S.EmbedBlock,
    S.LearnModule,
    # session
    S.ChatRetrievalHit,
    S.ChatToolCall,
    S.ChatFlow,
    S.ClarifyOption,
    S.ClarifyPrompt,
    S.UserMessage,
    S.PlanMessage,
    S.ToolMessage,
    S.AnswerMessage,
    S.ClarifyMessage,
    S.SystemMessage,
    S.ChatSession,
    S.SessionScope,
    S.ActivityEvent,
    S.JobStage,
    S.Job,
    # ledger
    S.Contradiction,
    S.ConstraintCheck,
    S.UncheckedStatus,
    S.ConsistentStatus,
    S.ContradictedStatus,
    S.Aggregate,
    S.AggregateStratum,
    S.ParameterView,
    S.ExcludedRecord,
    # design
    S.ClaimBound,
    S.ClaimScope,
    S.Patent,
    S.TierValue,
    S.MSPDistribution,
    S.SensitivityEntry,
    S.TierResult,
    S.EmbargoStatus,
    S.ScopeHit,
    S.DesignRecord,
]


def normalise(node: Any) -> Any:
    """Rewrite 2020-12 constructs the TypeScript generator does not read.

    `prefixItems` is how 2020-12 spells a fixed-length tuple; draft-07 spells it
    as an array-valued `items`. Left alone, `range: tuple[float, float]`
    generates as `unknown[]` and the ontology loses the one thing that makes a
    range a range.

    `const` is how Pydantic writes a single-member Literal, which is every
    discriminator in the schema. draft-07 wants a one-member `enum`, and a
    discriminated union whose discriminators are all `unknown` generates as a
    union of structurally identical interfaces.
    """
    if isinstance(node, list):
        return [normalise(x) for x in node]
    if not isinstance(node, dict):
        return node

    out = {k: normalise(v) for k, v in node.items()}

    if "prefixItems" in out:
        out["items"] = out.pop("prefixItems")
        # `items` as a list already implies the length; the bounds stay because
        # they are true and a validator that reads them is not wrong.

    if "const" in out and "enum" not in out:
        out["enum"] = [out["const"]]

    if isinstance(out.get("properties"), dict):
        required = set(out.get("required", []))
        out["properties"] = {
            name: normalise_property(prop, name in required)
            for name, prop in out["properties"].items()
        }

        # A discriminator is declared `state: Literal["unchecked"] = "unchecked"`,
        # and the default is what makes Pydantic call it optional — you need not
        # pass it to the constructor. But nothing ever SERIALISES without it, so
        # a schema that calls it optional is describing a document that cannot
        # exist. TypeScript then generates `state?: 'unchecked'`, and an optional
        # discriminator cannot narrow a union: `RefereeStatus` becomes three
        # interfaces no `if` can tell apart. Every one-member enum carrying its
        # own value as a default is such a tag, so it is marked required.
        req = list(out.get("required", []))
        for name, prop in out["properties"].items():
            if (
                isinstance(prop, dict)
                and isinstance(prop.get("enum"), list)
                and len(prop["enum"]) == 1
                and prop.get("default") == prop["enum"][0]
                and name not in req
            ):
                req.append(name)
        if req:
            out["required"] = req

    return out


def normalise_property(prop: Any, required: bool) -> Any:
    """Rewrite one field's schema, which needs to know whether it is required.

    Three things Pydantic writes that mean something different by the time the
    TypeScript generator has read them. All three are fixed here rather than in
    the generated file, for the reason in the module docstring.
    """
    if not isinstance(prop, dict):
        return prop
    out = dict(prop)

    # Pydantic titles every field — "Doi", "Paper Id", "Action". The generator
    # mints a named type for any titled schema, so `doi: str | None` arrives as
    # `doi?: Doi` with `type Doi = string | null`, and the file fills with alias
    # types that name nothing. The titles that matter are the ones on the $defs
    # entries, which are what name the interfaces; those are not touched.
    out.pop("title", None)

    # `X | None = None` carries `default: null`. It says nothing that absence
    # from `required` does not already say, and the generator reads a schema
    # whose only content is `{"default": null}` as an OPEN OBJECT — which is how
    # `AuditEvent.from`, declared `Any` to match the TypeScript's `unknown`,
    # generated as an interface with an index signature instead.
    if out.get("default", ...) is None:
        out.pop("default")

    # `X | None` on an OPTIONAL field means "absent, or an X". TypeScript spells
    # that `x?: X`, not `x?: X | null` — nothing in the application ever writes
    # a null, and the seed omits the key entirely.
    #
    # On a REQUIRED field it is left alone, because there it means something
    # real: `ParameterView.aggregate` is `Aggregate | null` on purpose, since
    # "checked, and there is no aggregate" is a different claim from "not
    # checked", and collapsing it would erase the distinction.
    if not required and isinstance(out.get("anyOf"), list):
        arms = [a for a in out["anyOf"] if a != {"type": "null"}]
        if len(arms) < len(out["anyOf"]):
            if len(arms) == 1:
                merged = dict(arms[0])
                merged.update({k: v for k, v in out.items() if k != "anyOf" and k not in merged})
                out = merged
            else:
                out["anyOf"] = arms

    return out


def expand_enum_keyed_maps(node: Any, defs: dict[str, Any]) -> Any:
    """Turn a map keyed by an enum into the closed record it actually is.

    `dict[CostLine, float]` emits as an open object with `propertyNames` naming
    the key enum. That is correct JSON Schema and the generator ignores it, so
    `costLines` arrives in TypeScript as `{[k: string]: number}` — where the
    hand-written type is `Record<CostLine, number>`.

    The difference is not cosmetic. The index signature promises nothing: it
    admits a typo as a key and admits an object with no keys at all. The record
    promises every cost line is present, which is what lets the waterfall sum to
    MSP and be believed. Written out as explicit required properties, draft-07
    says the same thing in a form the generator reads.
    """
    if isinstance(node, list):
        return [expand_enum_keyed_maps(x, defs) for x in node]
    if not isinstance(node, dict):
        return node

    out = {k: expand_enum_keyed_maps(v, defs) for k, v in node.items()}

    names = out.get("propertyNames")
    if isinstance(names, dict) and isinstance(names.get("$ref"), str):
        target = names["$ref"].rsplit("/", 1)[-1]
        members = defs.get(target, {}).get("enum")
        value = out.get("additionalProperties")
        if isinstance(members, list) and isinstance(value, dict):
            out.pop("propertyNames")
            out["properties"] = {str(m): deepcopy(value) for m in members}
            out["required"] = [str(m) for m in members]
            out["additionalProperties"] = False

    return out


def main() -> int:
    _, top = models_json_schema(
        [(m, "validation") for m in ROOTS],
        ref_template="#/$defs/{model}",
        title="GeneratedSchemaIndex",
    )
    defs = normalise(top.get("$defs", {}))

    for name, alias in ALIASES:
        # The arms are already in `defs` because every one of them is in ROOTS.
        # Emitting the union's own `$defs` again would duplicate them; dropping
        # it leaves `$ref`s that must already resolve, so assert that they do
        # rather than write a bundle with a dangling reference in it.
        schema = TypeAdapter(alias).json_schema(ref_template="#/$defs/{model}")
        for arm in schema.pop("$defs", {}):
            if arm not in defs:
                raise SystemExit(
                    f"{name} has an arm `{arm}` that is not in ROOTS. Add it there, "
                    f"or the emitted union will reference a definition that does not exist."
                )
        schema["title"] = name
        defs[name] = normalise(schema)

    defs = expand_enum_keyed_maps(defs, defs)

    bundle = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        # The generator walks from a root and names the root after its title, so
        # this name lands in the TypeScript as an interface listing every entity.
        # It is an artifact of the generation, not a concept in the system, and
        # it is named to say so.
        "title": "GeneratedSchemaIndex",
        "description": (
            "GENERATED from the Pydantic models in packages/core/openferment_core/schema. "
            "Do not edit. Edit the models and re-run `pnpm gen:types`."
        ),
        # A root object whose every property is one entity. The TypeScript
        # generator walks from a root, so without this it would emit nothing;
        # the wrapper interface it produces is harmless and is named so that its
        # purpose is obvious in the output.
        "type": "object",
        "additionalProperties": False,
        "properties": {name: {"$ref": f"#/$defs/{name}"} for name in sorted(defs)},
        "$defs": defs,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    print(f"  {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    print(f"  {len(ROOTS)} root models · {len(defs)} definitions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
