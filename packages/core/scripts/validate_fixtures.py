"""Validate every seeded entity against the Pydantic models.

This is the acceptance test for Phase 1 and the reason the models can be
believed at all. The rule it enforces is one-directional: where a real corpus
instance fails to parse, the MODEL is wrong and the model gets fixed. The corpus
is real literature, unevenly keyed on purpose, and its gaps are documented
deliberately — a schema that only accepts the tidy half of it has not described
the corpus, it has described a wish.

Every failure is reported before anything is changed, with the entity id and the
field, so the fix is made deliberately rather than by hammering at the model
until the errors stop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openferment_core import schema as S

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "schema-instances.json"

COLLECTIONS: list[tuple[str, type[BaseModel]]] = [
    ("papers", S.Paper),
    ("records", S.ExtractionRecord),
    ("strains", S.Strain),
    ("protocols", S.Protocol),
    ("ontology", S.ParameterDef),
    ("scenarios", S.Scenario),
    ("learnModules", S.LearnModule),
]


def identify(item: Any, index: int) -> str:
    if isinstance(item, dict):
        for key in ("id", "modelId", "name", "title"):
            if key in item:
                return str(item[key])
    return f"[{index}]"


def main() -> int:
    data = json.loads(FIXTURES.read_text("utf-8"))
    failures: list[str] = []
    total = 0
    roundtrip_failures: list[str] = []

    print("openFerment schema validation")
    print("─────────────────────────────")

    for key, model in COLLECTIONS:
        items = data.get(key, [])
        ok = 0
        for i, raw in enumerate(items):
            total += 1
            ident = identify(raw, i)
            try:
                parsed = model.model_validate(raw)
            except ValidationError as e:
                for err in e.errors():
                    loc = ".".join(str(p) for p in err["loc"])
                    failures.append(
                        f"{key}/{ident}: {loc} — {err['msg']} (got {err.get('input')!r})"
                    )
                continue
            ok += 1
            # Round-trip: dump by alias and compare against the input. A model
            # that parses but re-emits something different has silently dropped
            # or renamed a field, which would corrupt the corpus on the way to
            # the database in Phase 3.
            emitted = parsed.model_dump(by_alias=True, exclude_none=True, mode="json")
            pruned = prune_none(raw)
            if emitted != pruned:
                roundtrip_failures.append(f"{key}/{ident}: {diff_summary(pruned, emitted)}")
        print(f"  {key:<14} {ok:>4}/{len(items)}")

    if failures:
        print(f"\n✗ {len(failures)} validation failure(s) — the MODEL is wrong, not the data:")
        for f in failures[:60]:
            print(f"  - {f}")
        if len(failures) > 60:
            print(f"  … and {len(failures) - 60} more")

    if roundtrip_failures:
        print(f"\n✗ {len(roundtrip_failures)} round-trip mismatch(es):")
        for f in roundtrip_failures[:40]:
            print(f"  - {f}")
        if len(roundtrip_failures) > 40:
            print(f"  … and {len(roundtrip_failures) - 40} more")

    if failures or roundtrip_failures:
        return 1

    print(f"\n✓ {total} seeded entities parse and round-trip.\n")
    return 0


def prune_none(node: Any) -> Any:
    """Drop null-valued keys, matching `exclude_none` on the way out.

    TypeScript writes an absent optional as an absent key, but a few seed
    entries carry an explicit `undefined` that JSON serialisation turned into
    `null`. Those two mean the same thing here and comparing them literally
    would report a difference that is not one.
    """
    if isinstance(node, list):
        return [prune_none(x) for x in node]
    if isinstance(node, dict):
        return {k: prune_none(v) for k, v in node.items() if v is not None}
    return node


def diff_summary(a: Any, b: Any, path: str = "") -> str:
    """First real difference between two nested structures, as a path."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return f"{path}.{k} added by the model"
            if k not in b:
                return f"{path}.{k} dropped by the model"
            sub = diff_summary(a[k], b[k], f"{path}.{k}")
            if sub:
                return sub
        return ""
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path} length {len(a)} -> {len(b)}"
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            sub = diff_summary(x, y, f"{path}[{i}]")
            if sub:
                return sub
        return ""
    if a != b:
        # Float formatting differs harmlessly between the two sides; only report
        # a real change in value.
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and float(a) == float(b):
            return ""
        return f"{path}: {a!r} -> {b!r}"
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
