"""Postdoc's SFF tools (alpha 2.1 stage B; ADR-003): the toolkit's reference
files listed, one imported into the project and marked as the caller's, a
kept record read back with what its graph counts as evidence. The tool
takes a reference file's id alone: an address is a person's to name, at
POST /api/flowsheets/import-url (alpha 2.2 D10, its amendment at C.6).

Asked live to import a reference file and say what plant it describes,
Postdoc had no tool for it. The toolkit is test_sff's stand-in and the
reference file its small one, fetched before the tools run, so nothing is
fetched from the network here.
"""
from __future__ import annotations

from openferment_core import audit, llm, tools
from openferment_core.engine import sff

from test_sff import PROJECT, corpus, toolkit  # noqa: F401
from test_sff_url import ADDRESS, host  # noqa: F401

MODEL = llm.DEFAULT_PRIMARY


def as_model() -> tools.ToolContext:
    return tools.ToolContext(model=MODEL, project=PROJECT)


def test_a_reference_file_is_listed_imported_as_the_callers_and_read_back(toolkit, corpus):  # noqa: F811
    sff.fetch("SF_BST_99", get=corpus["get"])
    listed = tools.run("flowsheet_library", {"words": "small"}, as_model())
    assert listed.error is None and [(f["id"], f["fetched"]) for f in listed.summary["files"]] == [("SF_BST_99", True)]

    got = tools.run("flowsheet_import", {"file": "SF_BST_99", "note": "what plant it describes"}, as_model())
    assert got.error is None, got.error
    s = got.summary
    rid = s["recordId"]
    held = sff.get(rid, project_id=PROJECT)
    assert (s["title"], s["origin"], s["libraryId"], s["valid"]) == ("The small plant", "library", "SF_BST_99",
                                                                       held.validation.valid)
    counted = {e.id: e for e in got.evidence}
    assert counted[f"sff:{rid}:units"].value == held.units and counted[f"sff:{rid}:streams"].value == held.streams
    assert all(e.provenance == "computed" and e.basis.artifactId == rid for e in got.evidence), "a reference file's counts"
    assert s["unitTypes"] and isinstance(s["feeds"], list) and isinstance(s["products"], list)
    lines = [(a.agent, a.who, a.action, a.target) for a in audit.read() if a.module == "proforma"]
    assert ("model", MODEL, "flowsheet_import", rid) in lines, "kept as the model's, audited"

    again = tools.run("flowsheet_read", {"record": rid}, as_model())
    assert again.error is None and [e.id for e in again.evidence] == [e.id for e in got.evidence]
    every = tools.run("flowsheet_read", {}, as_model())
    assert [r["recordId"] for r in every.summary["records"]] == [rid]


def test_what_cannot_be_imported_or_read_is_refused_in_words(toolkit, corpus):  # noqa: F811
    missing = tools.run("flowsheet_import", {"file": "SF_BST_00"}, as_model())
    assert missing.error and "flowsheet_library lists" in missing.error
    registry = tools.run("flowsheet_import", {"file": "all_models"}, as_model())
    assert registry.error and "registry" in registry.error
    unknown = tools.run("flowsheet_read", {"record": "nonesuch"}, as_model())
    assert unknown.error and "holds no flowsheet nonesuch" in unknown.error


def test_the_import_tool_takes_no_address_so_no_model_has_the_service_fetch_one(toolkit, host):  # noqa: F811
    schema = tools.REGISTRY["flowsheet_import"].input_model.model_json_schema()
    assert set(schema["properties"]) == {"file", "note"}, "the tool names a reference file, never an address"
    asked = tools.run("flowsheet_import", {"url": ADDRESS, "note": "a colleague's plant"}, as_model())
    assert asked.error and "file" in asked.error, asked.error
    assert host.asked == [] and host.resolved == [] and toolkit.calls == [], "nothing was resolved, fetched or kept"
    assert sff.listed(project_id=PROJECT) == []
