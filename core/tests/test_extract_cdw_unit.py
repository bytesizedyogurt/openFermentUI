"""A cell-mass fraction's unit is chosen from a list that holds "% CDW"
(live test, 2026-10-16).

Seventy anchored values were rejected because the model wrote "%" for a
field whose canonical unit is "% CDW", and "%" is another family. The
schema now enumerates the unit for such a field and the prompt names it.
"""
from __future__ import annotations

from openferment_core import extract, llm
from openferment_core.units import tables


def _cdw_fields() -> list[str]:
    return [fid for fid, d in tables()["ontology"].items() if d.get("canonicalUnit") == "% CDW"]


def test_the_ontology_has_a_cell_mass_fraction_field():
    assert "pha_content_cdw" in _cdw_fields()


def test_a_cell_mass_fraction_field_takes_its_unit_from_an_enumeration():
    fields = list(tables()["ontology"])
    tool = extract.build_tool(["s1"], fields)
    item = tool["input_schema"]["properties"]["candidates"]["items"]
    variants = item["anyOf"]
    cdw = [v for v in variants if set(v["properties"]["field"]["enum"]) == set(_cdw_fields())]
    assert len(cdw) == 1
    assert "% CDW" in cdw[0]["properties"]["unit"]["enum"]
    others = [v for v in variants if v is not cdw[0]]
    assert len(others) == 1
    assert set(others[0]["properties"]["field"]["enum"]) == set(fields) - set(_cdw_fields())
    assert "enum" not in others[0]["properties"]["unit"]


def test_the_strict_schema_keeps_both_variants_closed():
    tool = extract.build_tool(["s1"], list(tables()["ontology"]))
    strict = llm.strict_schema(tool["input_schema"])
    for v in strict["properties"]["candidates"]["items"]["anyOf"]:
        assert v["additionalProperties"] is False


def test_the_prompt_names_the_unit():
    assert "% CDW" in extract.SYSTEM
