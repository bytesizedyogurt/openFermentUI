"""Projects (ADR-005): what a request acts in, how one is made, and how the
service answers a request that names none, an unknown one, or a database
that is down."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, audit, db, projects
from openferment_core.db.engine import make_engine
from openferment_core.models import ProjectCreate


def client(**kw) -> TestClient:
    return TestClient(api.app, base_url="http://127.0.0.1", **kw)


# The project conftest.py opens every test in.
TEST_PROJECT = "test-project"


def test_a_project_is_named_from_its_name_and_a_second_of_the_same_name_is_numbered():
    first = projects.create(ProjectCreate(name="Corn stover ethanol", by="Ada Moreno"))
    second = projects.create(ProjectCreate(name="Corn stover ethanol", by="Ada Moreno"))
    assert (first.id, second.id) == ("corn-stover-ethanol", "corn-stover-ethanol-2")
    assert projects.get("corn-stover-ethanol").name == "Corn stover ethanol"
    assert [p.id for p in projects.listed()] == [TEST_PROJECT, "corn-stover-ethanol", "corn-stover-ethanol-2"]


@pytest.mark.parametrize(
    ("name", "made"),
    [("Corn stover ethanol", "corn-stover-ethanol"), ("  Lipase / Yarrowia  ", "lipase-yarrowia"),
     ("Écume", "ecume"), ("!!!", "project"), ("x" * 90, "x" * 63)],
)
def test_the_id_a_name_makes(name, made):
    assert projects.slug(name) == made
    assert projects.valid_id(made)


def test_a_taken_id_is_refused_in_words():
    r = client().post("/api/projects", json={"name": "Again", "id": TEST_PROJECT, "by": "Ada Moreno"})
    assert r.status_code == 409 and "already exists" in r.json()["detail"]


def test_making_a_project_is_audited_under_it():
    made = client().post("/api/projects", json={"name": "Lipase", "by": "Ada Moreno"}).json()
    rows = client(headers={projects.HEADER: made["id"]}).get("/api/audit").json()
    assert [(r["action"], r["who"], r["target"]) for r in rows] == [("create_project", "Ada Moreno", made["id"])]
    # The test project's own log does not hold it.
    assert all(r["target"] != made["id"] for r in client().get("/api/audit").json())


def test_a_request_acts_in_the_project_it_names_and_no_other():
    other = projects.create(ProjectCreate(name="Other", by="Ada Moreno"))
    with projects.using(other.id):
        audit.append(agent="person", who="Ada Moreno", module="home", action="note", state="done")
    mine = client().get("/api/audit").json()
    theirs = client(headers={projects.HEADER: other.id}).get("/api/audit").json()
    assert "note" not in [r["action"] for r in mine]
    assert [r["action"] for r in theirs] == ["create_project", "note"]
    # ?project= names it where a header cannot be sent.
    by_query = client(headers={projects.HEADER: ""}).get(f"/api/audit?project={other.id}").json()
    assert by_query == theirs


def test_a_store_call_in_a_request_that_names_no_project_is_refused_in_words():
    r = client(headers={projects.HEADER: ""}).get("/api/audit")
    assert r.status_code == 422 and projects.HEADER in r.json()["detail"]
    # Listing and making projects need none.
    assert client(headers={projects.HEADER: ""}).get("/api/projects").status_code == 200


def test_an_unknown_project_and_a_malformed_one_stop_before_any_route():
    assert client(headers={projects.HEADER: "no-such-project"}).get("/api/audit").status_code == 404
    r = client(headers={projects.HEADER: "Not An Id"}).get("/api/audit")
    assert r.status_code == 422 and "not a project id" in r.json()["detail"]


def test_health_and_the_projects_answer_a_page_that_remembers_a_project_no_longer_held():
    gone = client(headers={projects.HEADER: "no-such-project"})
    assert gone.get("/api/health").status_code == 200
    assert TEST_PROJECT in [p["id"] for p in gone.get("/api/projects").json()]


def test_a_cross_site_write_is_refused_before_the_database_is_asked():
    r = client().post("/api/projects", json={"name": "Nope", "by": "x y"}, headers={"Origin": "https://elsewhere.example"})
    assert r.status_code == 403
    assert "nope" not in [p.id for p in projects.listed()]


def test_a_database_that_does_not_answer_is_a_503_in_words():
    down = make_engine("postgresql://nobody:nothing@127.0.0.1:9/none")
    previous_binding, previous_engine = db.bind(None), db.use_engine(down)
    try:
        r = client(raise_server_exceptions=False).get("/api/audit")
        assert r.status_code == 503 and "database did not answer" in r.json()["detail"]
        r = client(raise_server_exceptions=False).get("/api/projects")
        assert r.status_code == 503 and "database did not answer" in r.json()["detail"]
    finally:
        db.use_engine(previous_engine)
        db.bind(previous_binding)
        db.run(down.dispose())


def test_a_command_names_its_project_in_the_environment_and_none_means_none(monkeypatch):
    monkeypatch.setenv(projects.ENV, "from-the-environment")
    with projects.using(None):
        with pytest.raises(projects.ProjectRequired):
            projects.current()
    token = projects._CURRENT.set(projects._UNSET)
    try:
        assert projects.current() == "from-the-environment"
    finally:
        projects._CURRENT.reset(token)
