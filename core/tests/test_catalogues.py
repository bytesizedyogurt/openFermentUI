"""A project's catalogues (alpha 2.1 stage D, debt 1; catalogues.py).

The strains and their aliases, the products, Guild's skills and Primer's
lessons are rows of the project's `catalogue` table: kept by the route, by
Postdoc's `catalogue_write` (marked as the model's, audited) or by Intake from
a file, and read by every reader that had read an empty list: geneOS's hosts
and the strain aliases, ProtParam's products, the proposer's catalogue and
Guild's skills. Entries here are test material, words with no measured value.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, audit, catalogues, guild, llm, module_stores, protparam, tools
from openferment_core.pureos import proposer

# Guild's own projection, before conftest hands every test alpha 1.0's frozen export in its place.
GUILD_PROJECTION = guild.projection

STRAIN = catalogues.CatalogueEntry(kind="strain", id="test-strain-1", name="Test strain one", species="Testus exemplaris",
                                   program="yeast", aliases=["TS-1", "strain one"])


def test_an_entry_is_kept_by_kind_read_back_and_replaced_under_its_id():
    kept = catalogues.keep(STRAIN, by="Ada")
    assert (kept.by, bool(kept.at)) == ("Ada", True)
    assert [e.id for e in catalogues.listed("strain")] == ["test-strain-1"] and catalogues.listed("product") == []
    catalogues.keep(STRAIN.model_copy(update={"name": "Test strain one, renamed"}), by="Ada")
    assert catalogues.get("strain", "test-strain-1").name == "Test strain one, renamed"
    assert catalogues.counts() == {"strain": 1, "product": 0, "skill": 0, "lesson": 0}
    with pytest.raises(catalogues.CatalogueEntryNotFound):
        catalogues.get("strain", "nonesuch")
    with pytest.raises(catalogues.CatalogueRefused, match="no catalogue"):
        catalogues.listed("enzyme")
    with pytest.raises(catalogues.CatalogueRefused, match="name"):
        catalogues.keep(STRAIN, by="  ")


def test_an_entry_holds_only_what_its_kind_takes():
    with pytest.raises(ValueError, match="belong to a strain"):
        catalogues.CatalogueEntry(kind="product", id="p", name="P", species="Testus")
    with pytest.raises(ValueError, match="belongs to a product"):
        catalogues.CatalogueEntry(kind="strain", id="s", name="S", sequence="MKT")
    with pytest.raises(ValueError, match="twenty residues"):
        catalogues.CatalogueEntry(kind="product", id="p", name="P", sequence="MKT1", sequenceSource="a test")
    with pytest.raises(ValueError, match="where it was read"):
        catalogues.CatalogueEntry(kind="product", id="p", name="P", sequence="MKT")
    assert catalogues.CatalogueEntry(kind="product", id="p", name="P", sequence="mk t",
                                     sequenceSource="a test's own words").sequence == "MKT"


def test_the_readers_that_read_an_empty_list_read_the_catalogues(monkeypatch):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    catalogues.keep(STRAIN, by="Ada")
    catalogues.keep(catalogues.CatalogueEntry(kind="product", id="test-protein", name="A test protein",
                                              category="protein", sequence="MKTAYIAK",
                                              sequenceSource="a test's own words"), by="Ada")
    catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="SK-TEST", name="A test skill", family="testing",
                                              mastery=["criterion one"]), by="Ada")
    catalogues.keep(catalogues.CatalogueEntry(kind="lesson", id="l-test", name="A test lesson", skills=["SK-TEST"]),
                    by="Ada")
    assert [h["id"] for h in module_stores._projection()["geneos"]["hosts"]] == ["test-strain-1"]
    assert module_stores._strain_aliases() == {"test strain one": "test-strain-1", "ts-1": "test-strain-1",
                                               "strain one": "test-strain-1"}
    assert [p["id"] for p in protparam.products()] == ["test-protein"]
    assert protparam.sequence_of("test-protein")[0] == "MKTAYIAK"
    held = proposer._catalogue()
    assert [h["id"] for h in held.strains] == ["test-strain-1"] and [p["id"] for p in held.products] == ["test-protein"]
    assert set(guild.skills()) == {"SK-TEST"} and guild.lesson_skills("l-test") == ["SK-TEST"]
    assert module_stores._projection()["primer"]["lessons"][0]["lessonId"] == "l-test"


def test_a_file_of_entries_is_taken_in_and_its_bad_rows_refused_in_words():
    csv = (b"id,name,species,aliases,agent,via\n"
           b"test-strain-2,Test strain two,Testus exemplaris,TS-2; two,model,mcp\n"
           b"bad id!,Broken,,,,\n")
    got = catalogues.intake("strain", csv, "strains.csv", by="Ada")
    assert got.kept == ["test-strain-2"] and len(got.refused) == 1 and got.refused[0].startswith("row 2: id")
    entry = catalogues.get("strain", "test-strain-2")
    assert entry.aliases == ["TS-2", "two"] and entry.source == "the file strains.csv"
    assert (entry.agent, entry.via) == ("person", None), "a file is taken in a person's name, whatever its rows say"
    js = b'[{"id": "SK-A", "name": "Skill A", "mastery": ["one", "two"]}]'
    assert catalogues.intake("skill", js, "skills.json", by="Ada").kept == ["SK-A"]
    with pytest.raises(catalogues.CatalogueRefused, match="not JSON"):
        catalogues.intake("skill", b"[{", "broken.json", by="Ada")
    with pytest.raises(catalogues.CatalogueRefused, match="'id' and 'name'"):
        catalogues.intake("skill", b"a,b\n1,2\n", "odd.csv", by="Ada")


def test_the_routes_keep_list_and_take_a_file():
    client = TestClient(api.app, base_url="http://127.0.0.1")
    made = client.post("/api/catalogues/strain", json={"entry": STRAIN.model_dump(mode="json"), "by": "Ada"})
    assert made.status_code == 200 and made.json()["by"] == "Ada"
    assert [e["id"] for e in client.get("/api/catalogues/strain").json()] == ["test-strain-1"]
    assert client.get("/api/catalogues/strain/test-strain-1").json()["species"] == "Testus exemplaris"
    assert client.get("/api/catalogues/enzyme").status_code == 404
    refused = client.post("/api/catalogues/product", json={"entry": {"id": "p", "name": "P", "species": "x"}, "by": "Ada"})
    assert refused.status_code == 422 and "belong to a strain" in refused.json()["detail"]
    up = client.post("/api/intake/catalogue", data={"kind": "lesson", "by": "Ada"},
                     files={"file": ("lessons.csv", b"id,name,skills\nl-1,Lesson one,SK-A;SK-B\n", "text/csv")})
    assert up.status_code == 200 and up.json()["kept"] == ["l-1"]


def test_postdoc_reads_a_catalogue_and_keeps_an_entry_as_its_own():
    ctx = tools.ToolContext(model=llm.DEFAULT_PRIMARY)
    wrote = tools.run("catalogue_write", {"kind": "strain", "id": "test-strain-3", "name": "Test strain three",
                                          "species": "Testus exemplaris", "aliases": ["TS-3"],
                                          "note": "named in a document of the project"}, ctx)
    assert wrote.error is None, wrote.error
    held = catalogues.get("strain", "test-strain-3")
    assert held.by == llm.DEFAULT_PRIMARY and held.source == f"Postdoc ({llm.DEFAULT_PRIMARY})"
    lines = [(a.module, a.who, a.action, a.target) for a in audit.read()]
    assert ("geneos", llm.DEFAULT_PRIMARY, "catalogue_write", "strain/test-strain-3") in lines
    read = tools.run("catalogue_read", {"kind": "strain", "words": "ts-3"}, ctx)
    assert read.error is None and [e["id"] for e in read.summary["entries"]] == ["test-strain-3"]
    bad = tools.run("catalogue_write", {"kind": "product", "id": "p", "name": "P", "species": "x"}, ctx)
    assert bad.error and "belong to a strain" in bad.error
    assert tools.run("catalogue_read", {"kind": "enzyme"}, ctx).error.startswith("catalogue_read refused")


# ── alpha 2.2 D.0: a model's write never replaces a person's entry ──────────

SKILL = {"kind": "skill", "id": "test-skill-lane", "name": "A test skill", "family": "testing", "note": "a placeholder"}


def test_a_models_write_never_replaces_an_entry_a_person_kept():
    kept = catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="test-skill-lane", name="Kept by a person"),
                           by="Ada Moreno")
    assert kept.agent == "person"
    refused = tools.run("catalogue_write", {**SKILL, "name": "A model's name"}, tools.ToolContext(model="test-model-a"))
    assert refused.error.startswith("catalogue_write refused: the project's skill catalogue holds test-skill-lane, "
                                    "kept by Ada Moreno in a person's name"), refused.error
    assert "nothing was written" in refused.error
    assert catalogues.get("skill", "test-skill-lane").name == "Kept by a person"
    assert [a for a in audit.read() if a.action == "catalogue_write"] == [], "a refused write is audited as nothing"
    over_mcp = tools.run("catalogue_write", SKILL, tools.ToolContext(model="example-test/0.1", via="mcp"))
    assert "kept by Ada Moreno" in over_mcp.error


def test_a_model_replaces_its_own_entry_and_leaves_another_callers():
    mine = tools.ToolContext(model="test-model-a")
    assert tools.run("catalogue_write", SKILL, mine).error is None
    again = tools.run("catalogue_write", {**SKILL, "name": "Renamed by its keeper"}, mine)
    assert again.error is None and catalogues.get("skill", "test-skill-lane").name == "Renamed by its keeper"
    other = tools.run("catalogue_write", {**SKILL, "name": "Another model's"}, tools.ToolContext(model="test-model-b"))
    assert "kept by test-model-a in Postdoc's name" in other.error
    assert catalogues.get("skill", "test-skill-lane").name == "Renamed by its keeper"
    assert [a.who for a in audit.read() if a.action == "catalogue_write"] == ["test-model-a", "test-model-a"]


def test_a_persons_keep_replaces_whatever_the_id_holds_in_either_lane():
    tools.run("catalogue_write", SKILL, tools.ToolContext(model="test-model-a"))
    client = TestClient(api.app)
    replaced = client.post("/api/catalogues/skill", json={"entry": {"id": "test-skill-lane", "name": "A person's now",
                                                                    "agent": "model"}, "by": "Ada Moreno"})
    assert replaced.status_code == 200 and (replaced.json()["by"], replaced.json()["agent"]) == ("Ada Moreno", "person")
    by_tool = tools.run("catalogue_write", {**SKILL, "name": "Another person's"}, tools.ToolContext(person="Grace Hopper"))
    assert by_tool.error is None and catalogues.get("skill", "test-skill-lane").agent == "person"
    read = client.get("/api/catalogues/skill/test-skill-lane").json()
    assert (read["by"], read["agent"], read["source"]) == ("Grace Hopper", "person", "Grace Hopper")
    assert "kept by Grace Hopper" in tools.run("catalogue_write", SKILL, tools.ToolContext(model="test-model-a")).error


def test_an_entry_kept_before_the_lane_was_written_reads_it_from_its_source():
    from openferment_core import db, projects

    def kept_then(entry_id: str, by: str, source: str) -> None:
        legacy = catalogues.CatalogueEntry(kind="skill", id=entry_id, name="Kept before", by=by, source=source)
        assert legacy.agent is None
        db.run(catalogues._keep(projects.current(), [legacy]))

    kept_then("test-skill-mcp", "example-test/0.1", "example-test/0.1, over MCP")
    kept_then("test-skill-postdoc", "test-model-a", "Postdoc (test-model-a)")
    kept_then("test-skill-person", "Ada Moreno", "a document of the project")
    assert {e.id: (e.agent, e.via) for e in catalogues.listed("skill")} == {
        "test-skill-mcp": ("model", "mcp"), "test-skill-postdoc": ("model", "postdoc"),
        "test-skill-person": ("person", None)}
    assert tools.run("catalogue_write", {**SKILL, "id": "test-skill-postdoc"}, tools.ToolContext(model="test-model-a")).error is None
    assert "kept by Ada Moreno" in tools.run("catalogue_write", {**SKILL, "id": "test-skill-person"},
                                             tools.ToolContext(model="Ada Moreno")).error, "a model named like a person is a model"
    assert "in an outside assistant's name" in tools.run("catalogue_write", {**SKILL, "id": "test-skill-mcp"},
                                                         tools.ToolContext(model="example-test/0.1")).error
    assert tools.run("catalogue_write", {**SKILL, "id": "test-skill-mcp"},
                     tools.ToolContext(model="example-test/0.1", via="http")).error is None


# ── alpha 2.2 D.0 review: the door a model's write came in by ──────────────


def test_an_assistants_entry_is_its_own_through_either_door_and_postdocs_is_postdocs():
    """An outside assistant replaces its own entry through MCP or the HTTP
    endpoint alike; Postdoc's loop, under the same name, is refused, and so
    is an assistant under Postdoc's. Each keep names its door."""
    over_mcp = tools.ToolContext(model="example-test/0.1", via="mcp")
    assert tools.run("catalogue_write", SKILL, over_mcp).error is None
    kept = catalogues.get("skill", "test-skill-lane")
    assert (kept.via, kept.source) == ("mcp", "example-test/0.1, over MCP")
    again = tools.run("catalogue_write", {**SKILL, "name": "Renamed at the endpoint"},
                      tools.ToolContext(model="example-test/0.1", via="http"))
    assert again.error is None and again.summary["via"] == "http"
    assert catalogues.get("skill", "test-skill-lane").source == "example-test/0.1, at the HTTP endpoint"
    postdoc = tools.run("catalogue_write", {**SKILL, "name": "Postdoc's"}, tools.ToolContext(model="example-test/0.1"))
    assert postdoc.error and "kept by example-test/0.1 in an outside assistant's name" in postdoc.error
    rows = [a for a in audit.read() if a.action == "catalogue_write"]
    assert [(a.detail["via"], a.effort) for a in rows] == [("mcp", None), ("http", None)]


def test_catalogue_write_answers_the_entry_as_kept():
    kept = tools.run("catalogue_write", {**SKILL, "summary": "What the placeholder skill is"},
                     tools.ToolContext(model="test-model-a"))
    assert kept.error is None
    s = kept.summary
    assert (s["state"], s["kind"], s["id"], s["name"], s["by"], s["agent"], s["via"]) == (
        "open", "skill", "test-skill-lane", "A test skill", "test-model-a", "model", "postdoc")
    assert (s["note"], s["summary"], s["family"], s["source"]) == (
        "a placeholder", "What the placeholder skill is", "testing", "Postdoc (test-model-a)")
    assert s["at"].endswith("+00:00") and "meaning" in s
    read = tools.run("catalogue_read", {"kind": "skill"}, tools.ToolContext(model="test-model-a")).summary
    (entry,) = read["entries"]
    assert entry["at"] == s["at"] and entry["via"] == "postdoc" and set(read) == {"kind", "matched", "entries", "note"}
