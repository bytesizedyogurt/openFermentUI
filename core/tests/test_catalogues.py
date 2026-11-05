"""A project's catalogues (alpha 2.1 stage D, debt 1; catalogues.py).

The strains and their aliases, the products, Guild's skills and Primer's
lessons are rows of the project's `catalogue` table: kept by the route, by
Postdoc's `catalogue_write` (marked as the model's, audited) or by Intake from
a file, and read by every reader that had read an empty list: geneOS's hosts
and the strain aliases, ProtParam's products, the proposer's catalogue and
Guild's skills. A lesson keeps its body: its minutes, its blocks and its
checkpoint (alpha 2.2 E.12a, ADR-018). Entries here are test material, words
and placeholder numbers with no measured value.
"""
from __future__ import annotations

import json

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
                                              category="research_protein", location="secreted", sequence="MKTAYIAK",
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
    assert (held.products[0]["category"], held.products[0]["location"]) == ("research_protein", "secreted"), \
        "the proposer reads a product's class and where the cells leave it"
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
    refused = client.post("/api/catalogues/product", json={"entry": {"kind": "product", "id": "p", "name": "P",
                                                                     "species": "x"}, "by": "Ada"})
    assert refused.status_code == 422 and any("belong to a strain" in d["msg"] for d in refused.json()["detail"])
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
    replaced = client.post("/api/catalogues/skill", json={"entry": {"kind": "skill", "id": "test-skill-lane",
                                                                    "name": "A person's now", "agent": "model"},
                                                          "by": "Ada Moreno"})
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


# ── alpha 2.2 E.8: a skill's policy, a product's class and where the cells leave it ──

POLICY = {"criticality": "routine", "recencyDays": 30, "supervisedRuns": 1}


def test_a_products_class_is_one_the_proposer_reads_refused_in_words_at_every_door():
    assert set(catalogues.PRODUCT_CATEGORIES) == set(proposer.CLASS_OF_CATEGORY), "one list of a product's classes"
    with pytest.raises(ValueError, match="one of the classes pureOS's proposer reads"):
        catalogues.CatalogueEntry(kind="product", id="p", name="P", category="protein")
    with pytest.raises(ValueError, match="a category belongs to a product"):
        catalogues.CatalogueEntry(kind="strain", id="s", name="S", category="biopolymer")
    with pytest.raises(ValueError, match="a location belongs to a product"):
        catalogues.CatalogueEntry(kind="strain", id="s", name="S", location="secreted")
    assert catalogues.CatalogueEntry(kind="product", id="p", name="P", category=" ").category is None, "blank is none"
    client = TestClient(api.app, base_url="http://127.0.0.1")
    keep = client.post("/api/catalogues/product", json={"entry": {"kind": "product", "id": "p", "name": "P",
                                                                  "category": "protein"}, "by": "Ada"})
    assert keep.status_code == 422 and "and 'protein' is outside them" in keep.json()["detail"][0]["msg"]
    got = catalogues.intake("product", b"id,name,category,location\np-1,Product one,biopolymer,intracellular\n"
                                       b"p-2,Product two,protein,\n", "products.csv", by="Ada")
    assert got.kept == ["p-1"] and got.refused == [
        "row 2: category: a product's category is one of the classes pureOS's proposer reads ("
        + ", ".join(catalogues.PRODUCT_CATEGORIES) + "), and 'protein' is outside them"]
    assert catalogues.as_products()[0]["location"] == "intracellular"
    wrote = tools.run("catalogue_write", {"kind": "product", "id": "test-model-a.p", "name": "P", "category": "protein"},
                      tools.ToolContext(model="test-model-a"))
    assert wrote.error and "is outside them" in wrote.error and "Value error" not in wrote.error


def test_a_product_kept_with_no_class_is_proposed_nothing_in_words():
    catalogues.keep(STRAIN, by="Ada")
    catalogues.keep(catalogues.CatalogueEntry(kind="product", id="p-open", name="A placeholder product"), by="Ada")
    made = proposer.propose("p-open", "test-strain-1")
    assert made.train is None and [m.property for m in made.missing] == ["class"]
    assert made.missing[0].why.startswith("product p-open's products catalogue entry states no category, and the rules "
                                          "read a product's class from it")


def test_the_keep_route_takes_the_entry_as_the_catalogue_answers_one():
    client = TestClient(api.app, base_url="http://127.0.0.1")
    doc = api.app.openapi()
    assert doc["components"]["schemas"]["CatalogueKeep"]["properties"]["entry"] == {
        "$ref": "#/components/schemas/CatalogueEntry"}
    made = client.post("/api/catalogues/strain", json={"entry": STRAIN.model_dump(mode="json"), "by": "Ada"}).json()
    again = client.post("/api/catalogues/strain", json={"entry": {**made, "aliases": ["TS-1"]}, "by": "Grace"})
    assert again.status_code == 200 and (again.json()["by"], again.json()["aliases"]) == ("Grace", ["TS-1"])
    other = client.post("/api/catalogues/product", json={"entry": made, "by": "Ada"})
    assert other.status_code == 422 and other.json()["detail"] == (
        "the entry names its kind as strain, and this is the product catalogue: an entry is kept at "
        "/api/catalogues/strain")
    kindless = client.post("/api/catalogues/strain", json={"entry": {"id": "s", "name": "S"}, "by": "Ada"})
    assert kindless.status_code == 422 and kindless.json()["detail"][0]["loc"] == ["body", "entry", "kind"]
    nobody = client.post("/api/catalogues/strain", json={"entry": made, "by": " "})
    assert nobody.status_code == 422 and "a person's or a model's name" in nobody.json()["detail"]
    assert [e.id for e in catalogues.listed("strain")] == ["test-strain-1"] and catalogues.listed("product") == []


def test_a_skills_policy_is_kept_whole_or_refused_and_a_file_takes_it():
    kept = catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="SK-A", name="Skill A", **POLICY,
                                                     prerequisites=["SK-B", " SK-B "]), by="Ada")
    assert (kept.criticality, kept.recencyDays, kept.supervisedRuns, kept.prerequisites) == ("routine", 30, 1, ["SK-B"])
    # Each part of a policy is named as the catalogues screen names it, with the field that holds it.
    with pytest.raises(ValueError, match=r"leaves out how critical it is \(criticality\) and the supervised runs "
                                         r"before a check \(supervisedRuns\) \["):
        catalogues.CatalogueEntry(kind="skill", id="SK-C", name="C", recencyDays=30)
    with pytest.raises(ValueError, match=r"leaves out how critical it is \(criticality\), the days a qualification "
                                         r"stands \(recencyDays\) and the supervised runs before a check"):
        catalogues.CatalogueEntry(kind="skill", id="SK-C", name="C", prerequisites=["SK-A"])
    with pytest.raises(ValueError, match="names itself"):
        catalogues.CatalogueEntry(kind="skill", id="SK-C", name="C", **POLICY, prerequisites=["SK-C"])
    with pytest.raises(ValueError, match="a policy belong to a skill"):
        catalogues.CatalogueEntry(kind="lesson", id="l", name="L", criticality="critical")
    with pytest.raises(ValueError, match="less than or equal to"):
        catalogues.CatalogueEntry(kind="skill", id="SK-C", name="C", **{**POLICY, "recencyDays": 10 ** 9})
    csv = (b"id,name,criticality,recencyDays,supervisedRuns,prerequisites\n"
           b"SK-D,Skill D,critical,30,2,SK-A; SK-B\n"
           b"SK-E,Skill E,,30,,\n")
    got = catalogues.intake("skill", csv, "skills.csv", by="Ada")
    assert got.kept == ["SK-D"] and got.refused == [
        "row 2: the entry: a skill's policy names how critical it is (criticality), the days a qualification stands "
        "(recencyDays) and the supervised runs before a check (supervisedRuns) together, and this one leaves out how "
        "critical it is (criticality) and the supervised runs before a check (supervisedRuns)"]
    d = catalogues.get("skill", "SK-D")
    assert (d.criticality, d.recencyDays, d.supervisedRuns, d.prerequisites) == ("critical", 30, 2, ["SK-A", "SK-B"])
    held = {s["id"]: s for s in catalogues.as_skills()}
    assert {k: held["SK-D"][k] for k in ("criticality", "recencyDays", "supervisedRuns", "prerequisites")} == {
        "criticality": "critical", "recencyDays": 30, "supervisedRuns": 2, "prerequisites": ["SK-A", "SK-B"]}


def _ledger_with_a_member():
    from test_guild import person

    guild.write_person(person("p-lead", "Lead Person", role="lead", added_by=None))
    guild.write_person(person("p-member", "Member Person", added_by="p-lead"))


def test_guild_rates_a_catalogue_skill_by_its_policy_and_leaves_one_with_none_out_in_words(monkeypatch):
    """The defect E.8 repairs: as_skills handed Guild no prerequisites, and
    Competence.level read them (KeyError: 'prerequisites'). A skill with a
    policy is rated; one kept with none is left out of every level, of the
    checks' ranking and of a check asked for by name, each in words."""
    from openferment_core import checks
    from openferment_core.competence import Competence, unrated
    from openferment_core.models import CheckRequest, EvidenceSource, GuildEvidence

    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="SK-RATED", name="A rated skill", **POLICY), by="Ada")
    catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="SK-OPEN", name="A skill with no policy"), by="Ada")
    skills = guild.skills()
    assert unrated(skills["SK-RATED"]) is None
    assert unrated(skills["SK-OPEN"]).startswith("A skill with no policy has no policy in the project's skills catalogue")
    signed = [GuildEvidence(id=f"e-know-{k}", personId="p-member", skillId=k, kind="knowledge", at="2026-11-01",
                            observerId="p-lead", source=EvidenceSource(kind="signoff", ref="a placeholder record"),
                            raw="Signed off at a placeholder briefing") for k in ("SK-RATED", "SK-OPEN")]
    c = Competence(signed, skills, "2026-11-04")
    assert (c.level("p-member", "SK-RATED"), c.level("p-member", "SK-OPEN")) == (2, 0)
    left_out = c.status("p-member", "SK-OPEN")
    assert (left_out.level, left_out.effective, left_out.knowledgeComplete) == (0, 0, True)
    assert not c.holds("p-member", "SK-OPEN")
    _ledger_with_a_member()
    ranked = checks.rank_pairs(guild.read(), skills, "2026-11-04")
    assert all(p["skillId"] != "SK-OPEN" for p in ranked)
    with pytest.raises(checks.CheckRefused) as caught:
        checks.request(CheckRequest(personId="p-member", skillIds=["SK-OPEN"], by="p-member"))
    assert caught.value.rule == "skill" and "has no policy" in caught.value.why
    assert caught.value.why.endswith("a check of it waits until its catalogue entry holds its policy")


def test_a_run_of_a_skill_with_no_policy_is_refused_in_words(monkeypatch):
    from openferment_core.models import EvidenceSource, GuildEvidence

    catalogues.keep(catalogues.CatalogueEntry(kind="skill", id="SK-OPEN", name="A skill with no policy"), by="Ada")
    monkeypatch.setattr(guild, "projection", lambda: {
        "skills": catalogues.as_skills(), "lessons": [], "protocols": [],
        "steps": [{"protocolId": "PR-PLACEHOLDER", "stepId": "s1", "skills": ["SK-OPEN"]}]})
    _ledger_with_a_member()
    alone = GuildEvidence(id="e-alone-1", personId="p-member", skillId="SK-OPEN", kind="independent", observerId=None,
                          at="2026-11-04", source=EvidenceSource(kind="deposition", ref="PR-PLACEHOLDER", stepId="s1"),
                          raw="Ran the placeholder step alone")
    with pytest.raises(guild.GuildRefused) as caught:
        guild.write_evidence(alone)
    assert caught.value.rule == "authority"
    assert caught.value.why == (
        "A skill with no policy has no policy in the project's skills catalogue (its criticality, how many days a "
        "qualification stands and how many supervised runs come before a witnessed check), so Guild rates nobody on "
        "it: nobody holds it, and a run of it alone is a deviation until its catalogue entry holds its policy")
    cosigned = alone.model_copy(update={"id": "e-cosign-1", "kind": "supervised", "observerId": "p-lead"})
    with pytest.raises(guild.GuildRefused, match="nobody cosigns it until its catalogue entry holds its policy"):
        guild.write_evidence(cosigned)


# ── alpha 2.2 E.12a: a lesson keeps its body (ADR-018) ──


def _a_unit_the_converter_reads() -> str:
    """A unit from the converter's own table, read at run time."""
    from openferment_core import units

    return next(iter(units.tables()["table"]))


def lesson_with_a_body(**over) -> dict:
    body = {"kind": "lesson", "id": "l-body", "name": "A placeholder lesson", "skills": ["SK-A"], "minutes": 5,
            "blocks": [{"kind": "prose", "md": "A placeholder paragraph."},
                       {"kind": "embed", "embed": "ask-prompt", "arg": "A placeholder question?"},
                       {"kind": "embed", "embed": "mini-queue"}],
            "checkpoint": [{"id": "q1", "prompt": "A placeholder choice?", "kind": "mc",
                            "options": ["Option one", "Option two"], "answerIndex": 1,
                            "explanation": "A placeholder explanation."},
                           {"id": "q2", "prompt": "A placeholder number?", "kind": "numeric",
                            "answer": {"value": 1.5, "unit": "", "tolerancePct": 5}},
                           {"id": "q3", "prompt": "A placeholder quantity?", "kind": "numeric",
                            "answer": {"value": 2, "unit": _a_unit_the_converter_reads(), "tolerancePct": 0}}]}
    body.update(over)
    return body


def test_a_lesson_keeps_its_body_and_the_routes_serve_it_whole():
    client = TestClient(api.app, base_url="http://127.0.0.1")
    made = client.post("/api/catalogues/lesson", json={"entry": lesson_with_a_body(), "by": "Ada"})
    assert made.status_code == 200, made.text
    held = client.get("/api/catalogues/lesson/l-body").json()
    assert held["minutes"] == 5 and [b["kind"] for b in held["blocks"]] == ["prose", "embed", "embed"]
    assert held["blocks"][2] == {"kind": "embed", "embed": "mini-queue", "arg": None}
    assert [q["kind"] for q in held["checkpoint"]] == ["mc", "numeric", "numeric"]
    assert held["checkpoint"][1]["answer"] == {"value": 1.5, "unit": "", "tolerancePct": 5.0}
    assert held["checkpoint"][2]["answer"]["unit"] == _a_unit_the_converter_reads()
    (lesson,) = catalogues.as_lessons()
    assert (lesson["minutes"], lesson["skills"]) == (5, ["SK-A"])
    stores = module_stores.Stores()
    (row,) = stores.rows("primer")
    assert (row.id, row.label, row.detail) == ("l-body", "A placeholder lesson", {"skills": ["SK-A"], "minutes": 5})
    assert stores.error("primer") is None, "a catalogue lesson reads, with no module of alpha 1.0 around it"


@pytest.mark.parametrize("change, said", [
    ({"kind": "skill", "skills": []}, "minutes, blocks and a checkpoint belong to a lesson"),
    ({"blocks": [{"kind": "embed", "embed": "a-placeholder-embed"}]}, "Input should be 'chip-demo'"),
    ({"blocks": [{"kind": "verse", "md": "A placeholder line."}]}, "does not match any of the expected tags"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "mc", "options": ["One"], "answerIndex": 0}]},
     "multiple-choice question q1 offers two options or more"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "mc", "options": ["One", "Two"], "answerIndex": 2}]},
     "names its answer among its options (answerIndex, from 0 to 1)"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "mc", "options": ["One", "Two"], "answerIndex": 0,
                      "answer": {"value": 1, "unit": "", "tolerancePct": 5}}]},
     "a value to answer with belongs to a numeric question, and q1 is multiple choice"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "numeric"}]},
     "numeric question q1 holds its answer: a value, a unit and a tolerance"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "numeric", "options": ["One", "Two"],
                      "answer": {"value": 1, "unit": "", "tolerancePct": 5}}]},
     "options and an answer's index belong to a multiple-choice question, and q1 is numeric"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "numeric",
                      "answer": {"value": 1, "unit": "placeholder-unit", "tolerancePct": 5}}]},
     "the converter reads no 'placeholder-unit'"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "numeric",
                      "answer": {"value": float("nan"), "unit": "", "tolerancePct": 5}}]}, "finite number"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "numeric",
                      "answer": {"value": 1, "unit": "", "tolerancePct": 101}}]}, "less than or equal to 100"),
    ({"checkpoint": [{"id": "q1", "prompt": "P?", "kind": "mc", "options": ["One", "Two"], "answerIndex": 0}] * 2},
     "asks question q1 twice"),
    ({"minutes": 0}, "greater than or equal to 1"),
])
def test_a_lessons_body_is_refused_in_words_where_it_does_not_stand(change, said):
    with pytest.raises(ValueError) as caught:
        catalogues.CatalogueEntry.model_validate(lesson_with_a_body(**change))
    assert said in str(caught.value)


def test_a_file_of_lessons_takes_their_bodies_and_postdoc_reads_a_lesson_with_its_body_left_out():
    rows = [lesson_with_a_body(), lesson_with_a_body(id="l-bad", checkpoint=[{"id": "q1", "prompt": "P?",
                                                                              "kind": "numeric"}])]
    got = catalogues.intake("lesson", json.dumps(rows).encode(), "lessons.json", by="Ada")
    assert got.kept == ["l-body"] and got.refused == [
        "row 2: checkpoint.0: numeric question q1 holds its answer: a value, a unit and a tolerance"]
    assert len(catalogues.get("lesson", "l-body").checkpoint) == 3
    ctx = tools.ToolContext(model="test-model-a")
    (entry,) = tools.run("catalogue_read", {"kind": "lesson"}, ctx).summary["entries"]
    assert entry["minutes"] == 5 and entry["skills"] == ["SK-A"] and {"blocks", "checkpoint"}.isdisjoint(entry)
    numbered = tools.run("catalogue_write", {"kind": "lesson", "id": "l-model", "name": "A model's placeholder lesson",
                                             "minutes": 3}, ctx)
    assert numbered.error.startswith("catalogue_write refused: a number was typed into minutes")
    wrote = tools.run("catalogue_write", {"kind": "lesson", "id": "l-model", "name": "A model's placeholder lesson",
                                          "blocks": [{"kind": "prose", "md": "A placeholder."}]}, ctx)
    assert wrote.error is None
    kept = catalogues.get("lesson", "l-model")
    assert (kept.minutes, kept.blocks, kept.checkpoint) == (None, [], []), "a model's write keeps no lesson's body"


def test_a_lesson_edited_on_the_catalogues_screen_keeps_its_body():
    """The screen's form edits a lesson's name, words and skills, and sends the entry as it opened it with those laid
    over it (src/lib/catalogues.ts `edited`): its body as the lesson holds it, its keeper, lane, door and time blank.
    The keep replaces the entry whole, so the body the edit sends back is the body kept."""
    client = TestClient(api.app, base_url="http://127.0.0.1")
    assert client.post("/api/catalogues/lesson", json={"entry": lesson_with_a_body(), "by": "Ada"}).status_code == 200
    held = client.get("/api/catalogues/lesson/l-body").json()
    sent = {**held, "name": "A placeholder lesson, renamed", "skills": [], "by": "", "at": "", "agent": None,
            "via": None}
    again = client.post("/api/catalogues/lesson", json={"entry": sent, "by": "Ben"})
    assert again.status_code == 200, again.text
    after = client.get("/api/catalogues/lesson/l-body").json()
    assert (after["name"], after["skills"], after["by"], after["agent"]) == ("A placeholder lesson, renamed", [],
                                                                            "Ben", "person")
    assert (after["minutes"], after["blocks"], after["checkpoint"]) == (held["minutes"], held["blocks"],
                                                                        held["checkpoint"]), "the body stays whole"


def test_an_entrys_id_outside_the_rule_is_refused_in_the_words_the_form_uses():
    with pytest.raises(ValueError, match="an entry's id starts with a letter or a digit, then holds letters, digits"):
        catalogues.CatalogueEntry(kind="strain", id="-placeholder", name="A placeholder strain")
    client = TestClient(api.app, base_url="http://127.0.0.1")
    refused = client.post("/api/catalogues/strain", json={"entry": {"kind": "strain", "id": "-bad", "name": "S"},
                                                         "by": "Ada"})
    assert refused.status_code == 422
    (said,) = refused.json()["detail"]
    assert said["loc"] == ["body", "entry", "id"] and "should match pattern" not in said["msg"]
    assert said["msg"].startswith("Value error, an entry's id starts with a letter or a digit")
    got = catalogues.intake("strain", b"id,name\n-bad,A placeholder strain\nok-1,A placeholder strain\n", "s.csv",
                            by="Ada")
    assert got.kept == ["ok-1"] and got.refused[0].startswith("row 1: id: an entry's id starts with a letter")
    # The document still states the rule, for a client that checks an id before it sends one.
    assert catalogues.CatalogueEntry.model_json_schema()["properties"]["id"]["pattern"] == catalogues.ENTRY_ID.pattern


def _kept_in_an_older_shape(kind: str, entry_id: str, body: dict) -> None:
    """A row kept before the model held its kind to what it reads now, written straight into its table."""
    from openferment_core import db, projects
    from openferment_core.db import models as t
    from openferment_core.db import rows

    async def put() -> None:
        async with db.session() as s:
            await rows.put(s, t.catalogue, projects.current(), f"{kind}/{entry_id}",
                           {"kind": kind, "id": entry_id, "by": "Ada", "agent": "person",
                            "at": "2026-11-01T00:00:00+00:00", **body}, by="Ada", kind=kind)

    db.run(put())


def test_one_row_the_model_no_longer_reads_leaves_its_catalogue_and_every_reader_reading(monkeypatch, caplog):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    catalogues.keep(STRAIN, by="Ada")
    # A product's free-text class and a strain's class, as catalogue_write took them before alpha 2.2 E.8.
    _kept_in_an_older_shape("product", "p-old", {"name": "An older placeholder product", "category": "a word"})
    _kept_in_an_older_shape("strain", "s-old", {"name": "An older placeholder strain", "category": "a word"})
    client = TestClient(api.app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    with caplog.at_level("WARNING", logger="openferment_core.catalogues"):
        strains = client.get("/api/catalogues/strain")
        products = client.get("/api/catalogues/product")
    assert strains.status_code == 200 and [e["id"] for e in strains.json()] == ["test-strain-1"]
    assert products.status_code == 200 and products.json() == []
    assert any("row s-old does not read as an entry and is left out" in r.getMessage() for r in caplog.records)
    assert [h["id"] for h in catalogues.as_hosts()] == ["test-strain-1"]
    assert guild.projection()["skills"] == []
    # A model's write under the id is refused in words; a person's keep writes the entry afresh.
    ctx = tools.ToolContext(model="test-model-a")
    wrote = tools.run("catalogue_write", {"kind": "strain", "id": "s-old", "name": "A model's placeholder"}, ctx)
    assert wrote.error and "no longer reads as an entry" in wrote.error
    catalogues.keep(catalogues.CatalogueEntry(kind="strain", id="s-old", name="An older placeholder strain, kept "
                                                                                "afresh"), by="Ada")
    assert [e.id for e in catalogues.listed("strain")] == ["s-old", "test-strain-1"]
