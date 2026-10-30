"""The record fields have one source (alpha 2.0, ADR-010).

`core/openferment_core/schema/fields.yaml` defines them; `src/data/ontology.ts`
mirrors it for the browser until stage 7 serves the fields from the API. The
fixture `pnpm export:unit-fixtures` writes from the TypeScript side must equal
the YAML, field by field, and neither side may carry a range or an example
value. The vocabulary (`schema/vocabulary.yaml`: carbon sources and unit
operations) is mirrored by src/data/vocabulary.ts the same way.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from openferment_core import units

FIXTURE = Path(__file__).parent / "fixtures" / "fields.json"
KEYS = ("id", "family", "name", "definition", "canonicalUnit", "categorical", "requiresMethod", "refuseConversionTo")


def _normal(field: dict) -> dict:
    return {
        "id": field["id"],
        "family": field["family"],
        "name": field["name"],
        "definition": field["definition"],
        "canonicalUnit": field["canonicalUnit"],
        "categorical": bool(field.get("categorical")),
        "requiresMethod": bool(field.get("requiresMethod")),
        "refuseConversionTo": list(field.get("refuseConversionTo") or []),
    }


@pytest.fixture(scope="module")
def source() -> dict:
    return yaml.safe_load(units.FIELDS.read_text())


@pytest.fixture(scope="module")
def mirror() -> dict:
    if not FIXTURE.exists():
        pytest.fail("fields.json is missing: run `pnpm export:unit-fixtures` (pnpm test:core runs it first)")
    return json.loads(FIXTURE.read_text())


def test_the_typescript_mirror_equals_the_yaml(source, mirror):
    assert mirror["families"] == source["families"]
    assert [_normal(f) for f in mirror["fields"]] == [_normal(f) for f in source["fields"]]


def test_no_field_carries_a_range_or_an_example(source, mirror):
    for side in (source["fields"], mirror["fields"]):
        for f in side:
            assert set(f) <= set(KEYS), f"{f['id']} carries {sorted(set(f) - set(KEYS))}"


def test_every_refusal_names_a_field_that_exists(source):
    ids = {f["id"] for f in source["fields"]}
    for f in source["fields"]:
        for r in f.get("refuseConversionTo") or []:
            assert r["field"] in ids and r["because"].strip()


def test_the_typescript_vocabulary_equals_the_yaml(mirror):
    from openferment_core.validate import SCHEMA, unit_operations

    source = yaml.safe_load((SCHEMA / "vocabulary.yaml").read_text())
    assert mirror["carbonSources"] == [{k: c[k] for k in ("id", "label", "spellings")} for c in source["carbonSources"]]
    assert mirror["unitOperations"] == unit_operations()
