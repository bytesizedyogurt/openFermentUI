"""A project's protocols (alpha 2.2 E.12a; ADR-017; protocols.py).

A protocol is a row of the project's `protocols` table, served whole: made
once under its id, a version added under a version of its own and made the
current one, every version kept as it was kept, each keep audited in the
keeper's name. A step names the skills a person needs, held at the keep to
the project's skill catalogue, and Guild's step skills, Practice's sources and
the runbooks module read the steps from the store. Every protocol, number and
unit here is a placeholder.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, audit, catalogues, guild, module_stores, practice, protocols
from openferment_core.models import EvidenceSource, GuildEvidence, Protocol, ProtocolVersion

# Guild's own projection, before conftest hands every test alpha 1.0's frozen export in its place.
GUILD_PROJECTION = guild.projection

POLICY = {"criticality": "routine", "recencyDays": 30, "supervisedRuns": 1}


def skill(skill_id: str) -> None:
    catalogues.keep(catalogues.CatalogueEntry(kind="skill", id=skill_id, name=f"Placeholder skill {skill_id}",
                                              family="placeholder", mastery=["criterion one"], **POLICY), by="Ada")


def version(number: str = "1.0", **over) -> dict:
    v = {"version": number,
         "baseBatch": {"value": 1, "unit": "placeholder-unit", "label": "placeholder batch"},
         "materials": [{"name": "Material A", "amount": 2.5, "unit": "placeholder-unit", "scaling": "per_batch_volume",
                        "precision": 0.5, "stock": {"conc": 0.5, "unit": "placeholder-volume"}},
                       {"name": "Material B", "amount": 1, "unit": "placeholder-unit", "scaling": "fixed",
                        "precision": 0}],
         "steps": [{"id": "s1", "text": "Add {{qty:Material A}} as {{stock:Material A}} of its stock.",
                    "skills": ["SK-PH-A"]},
                   {"id": "s2", "text": "Add {{qty:Material B}}.", "note": "A placeholder note.", "skills": []}],
         "estMinutes": {"active": 1, "total": 2}}
    v.update(over)
    return v


def protocol(pid: str = "PR-PLACEHOLDER", **over) -> dict:
    p = {"id": pid, "title": "A placeholder protocol", "category": "sop", "bsl": 1,
         "organisms": ["Placeholder organism"], "purpose": "A placeholder purpose.", "currentVersion": "1.0",
         "versions": [version()]}
    p.update(over)
    return p


def client() -> TestClient:
    return TestClient(api.app, base_url="http://127.0.0.1")


def test_a_protocol_is_made_listed_and_read_back_whole():
    skill("SK-PH-A")
    made = client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"})
    assert made.status_code == 200, made.text
    body = made.json()
    (v,) = body["versions"]
    assert (v["by"], v["at"].endswith("+00:00")) == ("Ada", True), "the service writes who kept a version, and when"
    assert body == Protocol.model_validate(body).model_dump(mode="json"), "served whole, every field written"
    assert [p["id"] for p in client().get("/api/protocols").json()] == ["PR-PLACEHOLDER"]
    assert client().get("/api/protocols/PR-PLACEHOLDER").json() == body
    missing = client().get("/api/protocols/PR-NONE")
    assert missing.status_code == 404 and missing.json()["detail"] == "the project keeps no protocol PR-NONE"
    assert ("runbooks", "person", "Ada", "keep_protocol", "PR-PLACEHOLDER") in [
        (a.module, a.agent, a.who, a.action, a.target) for a in audit.read()]


def test_a_step_names_the_skills_the_skill_catalogue_holds():
    refused = client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"})
    assert refused.status_code == 422
    assert refused.json()["detail"].startswith(
        "step s1 of version 1.0 needs SK-PH-A, which the project's skill catalogue does not hold")
    assert client().get("/api/protocols").json() == [], "nothing kept"
    skill("SK-PH-A")
    assert client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"}).status_code == 200
    unheld = version("1.1", steps=[{"id": "s1", "text": "A placeholder step.", "skills": ["SK-PH-NONE"]}])
    later = client().post("/api/protocols/PR-PLACEHOLDER/versions", json={"version": unheld, "by": "Ada"})
    assert later.status_code == 422 and "needs SK-PH-NONE" in later.json()["detail"]


def test_a_protocol_is_made_once_and_a_kept_version_stays_as_it_was_kept():
    skill("SK-PH-A")
    first = client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"}).json()
    again = client().post("/api/protocols", json={"protocol": protocol(title="Another placeholder title"), "by": "Ada"})
    assert again.status_code == 422 and again.json()["detail"] == (
        "the project keeps a protocol PR-PLACEHOLDER already; a protocol is made once, and a new version of it is "
        "kept at /api/protocols/PR-PLACEHOLDER/versions")
    newer = client().post("/api/protocols/PR-PLACEHOLDER/versions",
                          json={"version": version("1.1", changelog="A placeholder change."), "by": "Grace"})
    assert newer.status_code == 200, newer.text
    body = newer.json()
    assert body["currentVersion"] == "1.1" and [v["version"] for v in body["versions"]] == ["1.0", "1.1"]
    assert [v["by"] for v in body["versions"]] == ["Ada", "Grace"]
    assert body["versions"][0] == first["versions"][0] and body["title"] == first["title"]
    kept = client().post("/api/protocols/PR-PLACEHOLDER/versions", json={"version": version("1.0", steps=[]),
                                                                         "by": "Grace"})
    assert kept.status_code == 422 and kept.json()["detail"] == (
        "version 1.0 of PR-PLACEHOLDER is kept as it was kept; a change is a new version, under a version of its own")
    assert client().get("/api/protocols/PR-PLACEHOLDER").json() == body, "nothing changed"
    assert client().post("/api/protocols/PR-NONE/versions", json={"version": version("2.0"), "by": "Grace"}
                         ).status_code == 404
    for nobody, said in ((" ", "names nobody"), ("me", "is a placeholder")):
        asked = client().post("/api/protocols/PR-PLACEHOLDER/versions", json={"version": version("1.2"), "by": nobody})
        assert asked.status_code == 422 and said in asked.json()["detail"], nobody
    assert ("runbooks", "Grace", "keep_protocol_version", "PR-PLACEHOLDER/1.1") in [
        (a.module, a.who, a.action, a.target) for a in audit.read()]


@pytest.mark.parametrize("change, said", [
    ({"steps": [{"id": "s1", "text": "Add {{qty:Material C}}."}]},
     "step s1 binds 'Material C', which is no material of version 1.0"),
    ({"steps": [{"id": "s1", "text": "Add {{stock:Material B}}."}]},
     "step s1 asks for a volume of the stock of 'Material B', and 'Material B' names no stock solution"),
    ({"steps": [{"id": "s1", "text": "A placeholder step."}, {"id": "s1", "text": "Another placeholder step."}]},
     "version 1.0 has two steps s1"),
    ({"materials": [{"name": "Material A", "amount": 1, "unit": "placeholder-unit", "scaling": "fixed", "precision": 0},
                    {"name": "Material A", "amount": 1, "unit": "placeholder-unit", "scaling": "fixed",
                     "precision": 0}], "steps": []},
     "version 1.0 names the material 'Material A' twice"),
    ({"materials": [{"name": "Material {A}", "amount": 1, "unit": "placeholder-unit", "scaling": "fixed",
                     "precision": 0}], "steps": []},
     "holds a brace"),
    ({"steps": [{"id": "s 1", "text": "A placeholder step."}]}, "String should match pattern"),
])
def test_a_version_binds_its_own_materials(change, said):
    with pytest.raises(ValueError) as caught:
        ProtocolVersion.model_validate(version(**change))
    assert said in str(caught.value)


def test_a_protocol_names_its_current_version_once_and_holds_finite_numbers():
    with pytest.raises(ValueError, match="current version '9.9' is none of its versions"):
        Protocol.model_validate(protocol(currentVersion="9.9"))
    with pytest.raises(ValueError, match="holds version 1.0 twice"):
        Protocol.model_validate(protocol(versions=[version(), version()]))
    with pytest.raises(ValueError, match="String should match pattern"):
        Protocol.model_validate(protocol(pid="PR:PLACEHOLDER"))
    skill("SK-PH-A")
    for where, bad in (("materials", "NaN"), ("baseBatch", "Infinity")):
        text = json.dumps({"protocol": protocol(), "by": "Ada"})
        text = text.replace('"amount": 2.5', f'"amount": {bad}') if where == "materials" else \
            text.replace('"value": 1', f'"value": {bad}')
        asked = client().post("/api/protocols", content=text, headers={"Content-Type": "application/json"})
        assert asked.status_code == 422 and any("finite number" in d["msg"] for d in asked.json()["detail"]), where
    assert client().get("/api/protocols").json() == []


def test_a_steps_skills_come_from_a_kept_protocol(monkeypatch):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    skill("SK-PH-A")
    skill("SK-PH-B")
    assert guild.step_skills("PR-PLACEHOLDER", "s1") is None
    protocols.make(Protocol.model_validate(protocol()), by="Ada")
    assert guild.step_skills("PR-PLACEHOLDER", "s1") == ["SK-PH-A"]
    assert guild.step_skills("PR-PLACEHOLDER", "s2") == [] and guild.step_skills("PR-PLACEHOLDER", "s9") is None
    protocols.add_version("PR-PLACEHOLDER", ProtocolVersion.model_validate(
        version("1.1", steps=[{"id": "s1", "text": "Add {{qty:Material B}}.", "skills": ["SK-PH-B"]}])), by="Ada")
    assert guild.step_skills("PR-PLACEHOLDER", "s1") == ["SK-PH-A", "SK-PH-B"], "across every version"
    # A run's entry is held to the skills its step needs before the ledger is read.
    at = GuildEvidence(id="e-run-1", personId="p-nobody", skillId="SK-PH-A", kind="independent", at="2026-11-04",
                       source=EvidenceSource(kind="deposition", ref="PR-PLACEHOLDER", stepId="s2"),
                       raw="Ran the placeholder step")
    with pytest.raises(guild.GuildRefused) as caught:
        guild.write_evidence(at, dry_run=True)
    assert (caught.value.rule, caught.value.why) == ("source", "PR-PLACEHOLDER step s2 does not need SK-PH-A; it needs "
                                                               "no skill")
    with pytest.raises(guild.GuildRefused) as caught:
        guild.write_evidence(at.model_copy(update={"source": EvidenceSource(kind="deposition", ref="PR-PLACEHOLDER",
                                                                            stepId="s1")}), dry_run=True)
    assert caught.value.rule == "person", "the step needs the skill, so the entry reaches the ledger's rules"


def test_practice_quotes_the_current_version_at_its_base_batch(monkeypatch):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    skill("SK-PH-A")
    protocols.make(Protocol.model_validate(protocol()), by="Ada")
    (quoted,) = guild.projection()["protocols"]
    assert (quoted["protocolId"], quoted["version"], quoted["baseBatch"]) == (
        "PR-PLACEHOLDER", "1.0", "1 placeholder-unit placeholder batch")
    sources = practice.sources_for("SK-PH-A", [])
    step = sources["step:PR-PLACEHOLDER:s1"]
    assert step["text"] == "Add 2.5 placeholder-unit as 5 placeholder-volume of its stock."
    assert step["basis"] == "PR-PLACEHOLDER as written, for its base batch (1 placeholder-unit placeholder batch)"
    material = sources["material:PR-PLACEHOLDER:Material A"]
    assert (material["value"], material["unit"]) == (2.5, "placeholder-unit"), "the protocol's own number"
    assert "step:PR-PLACEHOLDER:s2" not in sources, "a step that needs no skill is no source for one"
    assert practice.step_needs("PR-PLACEHOLDER", "s1") == ["SK-PH-A"]
    assert [s.stepId for s in practice.check_steps(["PR-PLACEHOLDER:s1"], "SK-PH-A")] == ["s1"]


def test_a_protocol_no_step_of_which_needs_a_skill_is_listed_and_quoted_by_none(monkeypatch):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    protocols.make(Protocol.model_validate(protocol(versions=[version(steps=[
        {"id": "s1", "text": "A placeholder step."}])])), by="Ada")
    assert guild.projection()["protocols"] == []
    assert [(s["stepId"], s["skills"]) for s in guild.projection()["steps"]] == [("s1", [])]
    stores = module_stores.Stores()
    (row,) = [r for r in stores.rows("runbooks") if r.kind == "protocol"]
    assert (row.id, row.label, row.state) == ("PR-PLACEHOLDER", "A placeholder protocol", "approved")
    assert row.detail["versions"] == ["1.0"] and row.detail["currentVersion"] == "1.0"
    assert stores.error("runbooks") is None


def test_the_bench_rounds_an_amount_as_the_browser_does():
    assert protocols.round_to_precision(2.26, 0.5) == 2.5
    assert protocols.round_to_precision(2.24, 0.5) == 2.0
    assert protocols.round_to_precision(2.5, 1) == 3.0, "half up, as Math.round rounds"
    assert protocols.round_to_precision(7.0, 0) == 7.0, "no increment rounds nothing"
    assert protocols.round_to_precision(1e308, 1e-308) == 1e308, "a step count past a float's range rounds nothing"
    assert (protocols.number(5.0), protocols.number(2.5), protocols.number(0.1)) == ("5", "2.5", "0.1")


def test_no_project_open_reads_no_protocol():
    from openferment_core import projects

    with projects.using(None):
        assert protocols.held() == []
        with pytest.raises(projects.ProjectRequired):
            protocols.listed()


def _kept_in_an_older_shape(protocol_id: str, body: dict) -> None:
    """A protocol row kept in a shape the model no longer reads, written straight into its table."""
    from openferment_core import db, projects
    from openferment_core.db import models as t
    from openferment_core.db import rows

    async def put() -> None:
        async with db.session() as s:
            await rows.put(s, t.protocols, projects.current(), protocol_id, body, by="Ada")

    db.run(put())


def test_one_row_that_does_not_read_leaves_the_rest_and_every_reader_reading(monkeypatch, caplog):
    monkeypatch.setattr(guild, "projection", GUILD_PROJECTION)
    skill("SK-PH-A")
    assert client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"}).status_code == 200
    _kept_in_an_older_shape("PR-OLDER", {**protocol("PR-OLDER"), "category": "a placeholder word"})
    unraised = TestClient(api.app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    with caplog.at_level("WARNING", logger="openferment_core.protocols"):
        listed = unraised.get("/api/protocols")
    assert listed.status_code == 200 and [p["id"] for p in listed.json()] == ["PR-PLACEHOLDER"]
    assert any("row PR-OLDER does not read as a protocol and is left out" in r.getMessage() for r in caplog.records)
    one = unraised.get("/api/protocols/PR-OLDER")
    assert one.status_code == 404 and "no longer reads as a protocol" in one.json()["detail"]
    grown = unraised.post("/api/protocols/PR-OLDER/versions", json={"version": version("1.1"), "by": "Ada"})
    assert grown.status_code == 422 and "so no version is added to it" in grown.json()["detail"]
    assert [p["protocolId"] for p in guild.projection()["protocols"]] == ["PR-PLACEHOLDER"]


def test_a_protocol_is_held_to_its_rows_size(monkeypatch):
    skill("SK-PH-A")
    monkeypatch.setattr(protocols, "MAX_BYTES", 4000)
    many = [{"id": f"s{n}", "text": "A placeholder step, written out at some length to fill the row."}
            for n in range(1, 60)]
    refused = client().post("/api/protocols", json={"protocol": protocol(versions=[version(materials=[], steps=many)]),
                                                    "by": "Ada"})
    assert refused.status_code == 422 and "bytes as its row keeps it, over the 4,000" in refused.json()["detail"]
    assert client().get("/api/protocols").json() == [], "nothing kept"
    assert client().post("/api/protocols", json={"protocol": protocol(), "by": "Ada"}).status_code == 200
    grown = client().post("/api/protocols/PR-PLACEHOLDER/versions",
                          json={"version": version("1.1", materials=[], steps=many), "by": "Ada"})
    assert grown.status_code == 422 and "bytes as its row keeps it, over the 4,000" in grown.json()["detail"]
    assert [v["version"] for v in client().get("/api/protocols/PR-PLACEHOLDER").json()["versions"]] == ["1.0"]
