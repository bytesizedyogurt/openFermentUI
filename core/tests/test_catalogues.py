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
    csv = (b"id,name,species,aliases\n"
           b"test-strain-2,Test strain two,Testus exemplaris,TS-2; two\n"
           b"bad id!,Broken,,\n")
    got = catalogues.intake("strain", csv, "strains.csv", by="Ada")
    assert got.kept == ["test-strain-2"] and len(got.refused) == 1 and got.refused[0].startswith("row 2: id")
    entry = catalogues.get("strain", "test-strain-2")
    assert entry.aliases == ["TS-2", "two"] and entry.source == "the file strains.csv"
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
