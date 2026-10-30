"""pnpm ready: each check says the right thing, and never the key (OF-BLD-012 §B.9).

Offline: the model check is handed a fake client that answers or raises the
way the Anthropic SDK does; the network checks run in fixture mode, where
they skip.
"""
from __future__ import annotations

import plistlib
from pathlib import Path

import anthropic
import httpx

import pytest

from openferment_core import api, db, llm, projects, ready
from openferment_core.db import migrate

# Shaped like a key, so check_key accepts it; random, so no piece of it turns
# up in the report by coincidence. Built from parts so check:secrets, which
# scans committed files for key-shaped strings, never sees one here.
FAKE_KEY = "sk-ant-" + "Q7zX9kWv3JpL8rTb" + "2NcY6hMd4FgS1aEu"
URL = "https://api.anthropic.com/v1/models/x"


def _http():
    try:
        import httpx2 as h  # what anthropic 1.x builds its errors from
    except ImportError:  # pragma: no cover
        import httpx as h
    return h


def status_error(cls, code):
    h = _http()
    return cls("x", response=h.Response(code, request=h.Request("GET", URL)), body=None)


class FakeClient:
    """The Models API. `raises` is one error for every model, or a dict from
    model id to the error that model's lookup raises."""

    def __init__(self, raises=None):
        self.raises = raises
        self.models = self
        self.asked: list[str] = []

    def retrieve(self, model_id, **_):
        assert model_id in llm.chain()
        self.asked.append(model_id)
        error = self.raises.get(model_id) if isinstance(self.raises, dict) else self.raises
        if error is not None:
            raise error
        return {"id": model_id}


@pytest.fixture(autouse=True)
def _scratch(monkeypatch, tmp_path, test_database):
    monkeypatch.delenv("OPENFERMENT_FIXTURES", raising=False)
    # The data row reads the database at the address set: the session's own,
    # migrated to head.
    test_database.open()
    monkeypatch.setenv(db.URL_SETTING, test_database.url.render_as_string(hide_password=False))


# ── the key ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "mark"),
    [(None, "fail"), ("", "fail"), ("sk-ant-...", "fail"), ("not-a-key", "warn"), (FAKE_KEY, "ok")],
)
def test_key(monkeypatch, value, mark):
    if value is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", value)
    assert ready.check_key().mark == mark


def test_the_report_never_shows_the_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    out = ready.report(ready.run(port=1))
    body = FAKE_KEY[len("sk-ant-"):]
    leaked = [body[i:i + 4] for i in range(len(body) - 3) if body[i:i + 4] in out]
    assert not leaked, f"pieces of the key in the report: {leaked}"


def test_an_sdk_error_that_quotes_the_key_is_not_repeated():
    for cls, code in ((anthropic.AuthenticationError, 401), (anthropic.InternalServerError, 500)):
        h = _http()
        error = cls(f"bad key {FAKE_KEY}", response=h.Response(code, request=h.Request("GET", URL)), body=None)
        detail = ready.check_model(True, client_factory=lambda: FakeClient(error)).detail
        assert FAKE_KEY[len("sk-ant-"):][:4] not in detail


# ── the model ──────────────────────────────────────────────────────────


OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"


@pytest.fixture(autouse=True)
def _default_chain(monkeypatch):
    for name in ("OPENFERMENT_MODEL", "OPENFERMENT_FALLBACK_MODEL", "OPENFERMENT_EFFORT"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("errors", "mark", "says"),
    [
        (None, "ok", f"{OPUS} then {SONNET}"),
        (lambda: status_error(anthropic.AuthenticationError, 401), "fail", "rejected the key"),
        (lambda: {OPUS: status_error(anthropic.NotFoundError, 404)}, "warn", f"every call runs on {SONNET}"),
        (lambda: {SONNET: status_error(anthropic.PermissionDeniedError, 403)}, "warn", f"every call runs on {OPUS}"),
        (lambda: {OPUS: status_error(anthropic.NotFoundError, 404), SONNET: status_error(anthropic.NotFoundError, 404)},
         "fail", "no model in the chain"),
        (lambda: status_error(anthropic.InternalServerError, 500), "fail", "answered 500"),
        (lambda: anthropic.APIConnectionError(request=_http().Request("GET", URL)), "fail", "could not reach"),
    ],
)
def test_model_checks_both_models_in_the_chain(errors, mark, says):
    client = FakeClient(errors() if errors else None)
    check = ready.check_model(True, client_factory=lambda: client)
    assert check.mark == mark and says in check.detail, check.detail


def test_a_model_with_no_price_on_file_is_named(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FALLBACK_MODEL", "claude-some-future-model")
    check = ready.check_model(True, client_factory=FakeClient)
    assert check.mark == "warn" and "no price on file for claude-some-future-model" in check.detail


def test_an_effort_the_api_does_not_accept_fails_before_any_call(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_EFFORT", "maximum")
    check = ready.check_model(False)
    assert check.mark == "fail" and "OPENFERMENT_EFFORT=maximum" in check.detail
    monkeypatch.setenv("OPENFERMENT_EFFORT", "xhigh")
    assert ready.check_model(False).mark == "skip"


def test_model_waits_for_a_key_and_for_the_network():
    assert ready.check_model(False).mark == "skip"


def test_a_routing_table_that_cannot_route_fails_before_any_call(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_ROUTES", '{"plan": {"effort": "huge"}}')
    check = ready.check_model(False)
    assert check.mark == "fail" and "OPENFERMENT_ROUTES.plan.effort" in check.detail


def test_a_route_to_a_provider_that_waits_is_named(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_ROUTES", '{"index": {"models": ["openai-compatible:qwen3-32b"]}}')
    check = ready.check_model(True, client_factory=FakeClient)
    assert check.mark == "warn" and "openai-compatible:qwen3-32b" in check.detail, check.detail
    assert "waits for the owner" in check.detail


def test_network_checks_skip_in_fixture_mode(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    assert ready.check_model(True, client_factory=FakeClient).mark == "skip"
    assert ready.check_europe_pmc().mark == "skip"
    assert ready.check_huggingface().mark == "skip"
    assert ready.check_backup().mark == "skip"


# ── Hugging Face, the optional row (OF-BLD-014 §1.3) ───────────────────


def _hf_answers(monkeypatch, outcome):
    def head(url, **_):
        assert url == ready.HUGGINGFACE
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome, request=httpx.Request("HEAD", url))

    monkeypatch.setattr(ready.httpx, "head", head)


@pytest.mark.parametrize(
    ("outcome", "mark", "says"),
    [
        (200, "ok", "huggingface.co answers"),
        (403, "warn", "answered 403"),
        (httpx.ConnectError("blocked"), "warn", "could not reach huggingface.co (ConnectError)"),
    ],
)
def test_huggingface_warns_when_blocked_and_never_fails(monkeypatch, outcome, mark, says):
    _hf_answers(monkeypatch, outcome)
    check = ready.check_huggingface()
    assert check.mark == mark and says in check.detail, check.detail


def test_a_blocked_huggingface_leaves_the_exit_code_alone(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setattr(ready, "load_dotenv", lambda *a, **k: None)
    for name in ("check_model", "check_roles", "check_europe_pmc", "check_backup"):
        row = name.removeprefix("check_").replace("_", "")
        monkeypatch.setattr(ready, name, lambda *a, row=row, **k: ready.Check(row, "ok", "stand-in"))
    monkeypatch.setattr(ready, "check_service", lambda *a, **k: ready.Check("service", "ok", "stand-in"))
    monkeypatch.setattr(ready, "check_corpus", lambda: ready.Check("corpus", "ok", "stand-in"))
    _hf_answers(monkeypatch, httpx.ConnectError("blocked"))
    assert ready.main([]) == 0
    out = capsys.readouterr().out
    assert "! huggingface" in out and out.rstrip().endswith("lane: full")


# ── Graphviz (OF-BLD-019 D8) ───────────────────────────────────────────


def test_graphviz_is_ok_with_dot_on_the_path_and_a_warning_without(monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: "/opt/homebrew/bin/dot" if name == "dot" else None)
    row = ready.check_graphviz()
    assert row.name == "graphviz" and row.mark == "ok" and "/opt/homebrew/bin/dot" in row.detail
    monkeypatch.setattr(shutil, "which", lambda name: None)
    row = ready.check_graphviz()
    assert row.mark == "warn" and "brew install graphviz" in row.detail and "run order" in row.detail


def test_a_missing_graphviz_leaves_the_exit_code_and_the_lane_alone(monkeypatch, capsys):
    import shutil

    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setattr(ready, "load_dotenv", lambda *a, **k: None)
    for name in ("check_model", "check_roles", "check_europe_pmc", "check_backup", "check_huggingface"):
        row = name.removeprefix("check_").replace("_", "")
        monkeypatch.setattr(ready, name, lambda *a, row=row, **k: ready.Check(row, "ok", "stand-in"))
    monkeypatch.setattr(ready, "check_service", lambda *a, **k: ready.Check("service", "ok", "stand-in"))
    monkeypatch.setattr(ready, "check_corpus", lambda: ready.Check("corpus", "ok", "stand-in"))
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert ready.main([]) == 0
    out = capsys.readouterr().out
    assert "! graphviz" in out and out.rstrip().endswith("lane: full")


# ── the lane (OF-BLD-014 A.4) ──────────────────────────────────────────


def _checks(key: str, europepmc: str, model: str = "ok") -> list:
    return [ready.Check("key", key, ""), ready.Check("model", model, ""), ready.Check("europepmc", europepmc, "")]


@pytest.mark.parametrize(
    ("key", "europepmc", "model", "lane"),
    [
        ("ok", "ok", "ok", "full"),
        ("warn", "ok", "ok", "full"),
        ("ok", "fail", "ok", "model-only"),
        ("ok", "skip", "skip", "none"),
        ("ok", "skip", "warn", "model-only"),
        ("fail", "ok", "skip", "none"),
        ("fail", "fail", "skip", "none"),
        ("ok", "ok", "fail", "none"),
        ("ok", "fail", "fail", "none"),
    ],
)
def test_the_three_lanes(key, europepmc, model, lane):
    assert ready.lane(_checks(key, europepmc, model)) == lane
    assert lane in ready.LANES


def test_the_lane_is_the_last_line_of_every_report(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(ready, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ready.report(ready.run(no_network=True, port=1)).splitlines()[-1] == "lane: none"
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    assert ready.report(ready.run(no_network=True, port=1)).splitlines()[-1] == "lane: none", \
        "a model unasked is a key unconfirmed, as Europe PMC unasked is Europe PMC unconfirmed"


# ── what is on disk ────────────────────────────────────────────────────


def test_intake_counts_the_documents_held_and_extracted():
    assert ready.check_intake().mark == "warn", "nothing held is worth knowing"

    async def link() -> None:
        from sqlalchemy import insert

        from openferment_core.db import models as t

        async with db.session() as s:
            await s.execute(insert(t.documents_link).values(
                project_id="test-project", document_id="0" * 32, selection={}, created_by="test"))

    db.run(link())
    check = ready.check_intake()
    assert check.mark == "ok" and check.detail == "1 document held (1 link to projects), 0 extracted"


def test_a_row_that_cannot_be_checked_says_so_and_the_rest_still_run(monkeypatch):
    def broken():
        raise OSError("the cache directory is not readable")

    monkeypatch.setattr(ready, "check_embedder", broken)
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    checks = ready.run(no_network=True, port=1)
    [embedder] = [c for c in checks if c.name == "embedder"]
    assert embedder.mark == "warn" and "could not be checked" in embedder.detail
    assert checks[-1].name == "service", "a row that fails must not stop the checks after it"


def test_the_literature_row_reads_the_kits_schema():
    check = ready.check_literature()
    assert check.mark in ("ok", "warn"), check.detail
    assert check.detail.startswith("pgvector ") and "revision 0006" in check.detail


def test_the_embedder_row_says_when_the_model_file_is_not_cached(monkeypatch, tmp_path):
    import openferment_core.literature as literature

    monkeypatch.setattr(literature, "EMBEDDING_CACHE", tmp_path / "empty")
    check = ready.check_embedder()
    assert check.mark == "warn" and "huggingface.co" in check.detail


def test_the_rag_row_says_whether_a_key_is_set(monkeypatch):
    from openferment_core.literature import kit

    monkeypatch.delenv(kit.RAG_KEY, raising=False)
    assert ready.check_rag().mark == "warn"
    monkeypatch.setenv(kit.RAG_KEY, "a-key")
    assert ready.check_rag().mark == "ok"


def test_a_damaged_corpus_is_a_failure_with_the_fix(monkeypatch):
    def damaged():
        raise ValueError("Expecting value: line 1 column 1")

    monkeypatch.setattr(ready, "load_corpus", damaged)
    check = ready.check_corpus()
    assert check.mark == "fail" and "could not be read" in check.detail and "Expecting value" in check.detail


def test_data_names_the_setting_when_no_database_is_set(monkeypatch):
    monkeypatch.delenv(db.URL_SETTING, raising=False)
    check = ready.check_data()
    assert check.mark == "fail" and db.URL_SETTING in check.detail


def test_data_reports_a_database_that_does_not_answer(monkeypatch):
    monkeypatch.setenv(db.URL_SETTING, "postgresql://nobody:nothing@127.0.0.1:9/none")
    check = ready.check_data()
    assert check.mark == "fail" and "did not answer" in check.detail and "nothing@" not in check.detail


def test_data_reports_a_database_behind_the_newest_schema(monkeypatch, test_database):
    test_database.open()
    name = f"{test_database.name}_bare"
    bare = migrate.create(name, test_database.server)
    try:
        monkeypatch.setenv(db.URL_SETTING, bare.render_as_string(hide_password=False))
        check = ready.check_data()
        assert check.mark == "fail" and "pnpm db:migrate" in check.detail
    finally:
        migrate.drop(name, test_database.server)


def test_data_counts_projects_and_decisions(monkeypatch, test_database):
    test_database.open()
    monkeypatch.setenv(db.URL_SETTING, test_database.url.render_as_string(hide_password=False))
    check = ready.check_data()
    assert check.mark == "ok" and check.detail.startswith("1 project, 0 review decisions, at revision")


def test_dist_dir_is_the_one_the_service_mounts():
    assert ready.DIST_DIR == api.DIST_DIR


def test_nothing_listening_is_a_warning_not_a_failure():
    assert ready.check_service(1, have_key=True).mark == "warn"


# ── the whole run ──────────────────────────────────────────────────────


def test_exit_code_follows_the_failures(monkeypatch, capsys):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setenv("OPENFERMENT_PORT", "1")
    monkeypatch.setattr(ready, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ready.main([]) == 1
    assert "✗ key" in capsys.readouterr().out
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    assert ready.main(["--no-network"]) == 0
    assert ready.main(["--bogus"]) == 2


def test_an_offline_run_asks_for_no_key_and_no_network(monkeypatch, capsys):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setenv("OPENFERMENT_PORT", "1")
    monkeypatch.setattr(ready, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ready.main(["--offline"]) == 0
    out = capsys.readouterr().out
    assert "· key" in out and "makes no model call" in out and "✗" not in out
    marks = {c.name: c.mark for c in ready.run(offline=True, port=1)}
    assert marks["key"] == "skip" and all(marks[n] == "skip" for n in ("model", "roles", "europepmc", "huggingface", "backup"))


def test_service_address_comes_from_the_installed_job(tmp_path, monkeypatch):
    launchd = ready._launchd()
    jobs = launchd.daemons(Path("/Users/sean/openferment"), "sean", Path("/Users/sean"), "/usr/bin", "0.0.0.0", 8123)
    (tmp_path / f"{launchd.SERVER}.plist").write_bytes(plistlib.dumps(jobs[launchd.SERVER]))
    monkeypatch.setenv("OPENFERMENT_LAUNCHD_DIR", str(tmp_path))
    monkeypatch.delenv("OPENFERMENT_PORT", raising=False)
    monkeypatch.delenv("OPENFERMENT_POLL_HOST", raising=False)
    assert ready.service_address() == ("127.0.0.1", 8123)
    monkeypatch.setenv("OPENFERMENT_PORT", "9000")
    monkeypatch.setenv("OPENFERMENT_POLL_HOST", "192.168.1.5")
    assert ready.service_address() == ("192.168.1.5", 9000), "what install.sh and deploy.sh pass wins"


def test_service_address_without_an_installed_job(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENFERMENT_LAUNCHD_DIR", str(tmp_path))
    monkeypatch.delenv("OPENFERMENT_PORT", raising=False)
    monkeypatch.delenv("OPENFERMENT_POLL_HOST", raising=False)
    assert ready.service_address() == ("127.0.0.1", 8000)


# ── roles (OF-BLD-014 §3.3) ────────────────────────────────────────────


class FakeRolesClient:
    """The Models API for every model in either role's chain."""

    def __init__(self, missing=()):
        self.missing = set(missing)
        self.models = self

    def retrieve(self, model_id, **_):
        assert any(model_id in llm.chain(r) for r in llm.ROLES)
        if model_id in self.missing:
            raise status_error(anthropic.NotFoundError, 404)
        return {"id": model_id}


def test_roles_names_each_chain_and_todays_spend(monkeypatch):
    for name in ("OPENFERMENT_MODEL", "OPENFERMENT_FALLBACK_MODEL", "OPENFERMENT_INDEX_MODEL"):
        monkeypatch.delenv(name, raising=False)
    check = ready.check_roles(True, client_factory=lambda: FakeRolesClient())
    assert check.mark == "ok"
    assert "index: claude-haiku-5-5 → claude-opus-5-5" in check.detail and "of the $25.00 daily cap" in check.detail
    check = ready.check_roles(True, client_factory=lambda: FakeRolesClient(missing={"claude-haiku-5-5"}))
    assert check.mark == "warn" and "index work runs on the answer chain" in check.detail
    assert ready.check_roles(False).mark == "skip"


def test_roles_fails_on_a_budget_that_is_not_dollars(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "lots")
    check = ready.check_roles(False)
    assert check.mark == "fail" and "OPENFERMENT_DAILY_BUDGET_USD" in check.detail


# ── what OF-BLD-014 added (§10.2) ──────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_worker_start(monkeypatch, request):
    """A real worker takes most of a minute to start; every test but the
    one that asks for it reads the row as skipped."""
    if request.node.name != "test_a_worker_that_does_not_answer_is_said":
        monkeypatch.setattr(ready, "check_workers", lambda ping=True: ready.Check("workers", "skip", "test"))


def test_the_new_rows_are_listed_and_change_no_lane(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    checks = ready.run(no_network=True, port=1)
    names = [c.name for c in checks]
    for n in ("models", "artifacts", "spend", "workers", "graphviz"):
        assert n in names
    assert ready.lane(checks) == "none"


def test_a_model_file_that_is_missing_or_changed_is_named(monkeypatch):
    from openferment_core import geneos_models as shelf

    monkeypatch.setattr(shelf, "available", lambda m: f"{m.id}'s file is not on this machine: run pnpm geneos:fetch" if m.fetched else None)
    c = ready.check_models()
    assert c.mark == "warn" and "iMM904's file is not on this machine" in c.detail and "Yeast9's file" in c.detail


def test_artifacts_are_counted_across_every_project():
    from openferment_core.db import models as t
    from openferment_core.db import rows

    async def keep() -> None:
        async with db.session() as s:
            for aid in ("a" * 16, "b" * 16):
                await rows.put(s, t.artifacts, projects.current(), aid, {}, by="test", tool="t", version="1", output_hash="h")

    db.run(keep())
    assert ready.check_artifacts().detail == "2 kept"


def test_spend_reads_today_against_the_cap_and_unknown_spend_fails(monkeypatch):
    from openferment_core import spend
    from openferment_core.db.engine import make_engine

    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "2")
    spend.charge("answer", 1.5)
    spend.charge("index", 0.25)
    c = ready.check_spend()
    assert c.mark == "ok" and "$1.75 of the $2.00 daily cap" in c.detail
    spend.charge("answer", 0.25)
    assert ready.check_spend().mark == "warn"
    down = make_engine("postgresql://nobody:nothing@127.0.0.1:9/none")
    previous_binding, previous_engine = db.bind(None), db.use_engine(down)
    try:
        assert ready.check_spend().mark == "fail"
    finally:
        db.use_engine(previous_engine)
        db.bind(previous_binding)
        db.run(down.dispose())


def test_a_worker_that_does_not_answer_is_said(monkeypatch):
    from openferment_core import workers

    class Mute:
        def __init__(self, module, timeout_s):
            self.module = module

        def ping(self, timeout_s=None):
            if "proforma" in self.module:
                raise workers.WorkerTimeout("no answer in 240 s")

        def close(self):
            pass

    monkeypatch.setattr(workers, "SimWorker", Mute)
    c = ready.check_workers()
    assert c.mark == "warn" and "geneOS answers" in c.detail and "Proforma does not" in c.detail
    assert ready.check_workers(ping=False).mark == "skip"


def test_r2_a_row_that_crashes_reads_as_a_warning_and_the_rest_still_run(monkeypatch):
    def broken():
        raise AttributeError("'list' object has no attribute 'get'")

    monkeypatch.setattr(ready, "check_models", broken)
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    checks = ready.run(no_network=True, port=1)
    row = next(c for c in checks if c.name == "models")
    assert row.mark == "warn" and "could not be checked" in row.detail and checks[-1].name == "service"


def test_the_workspace_400_names_the_setting_that_fixes_it(monkeypatch):
    from openferment_core import llm

    monkeypatch.delenv(llm.WORKSPACE_SETTING, raising=False)
    e = Exception("400")
    e.body = {"error": {"message": "This API key is not scoped to a workspace, so this request must include the anthropic-workspace-id header"}}
    assert "Set OPENFERMENT_WORKSPACE_ID in core/.env" in ready._said(e)
    monkeypatch.setenv(llm.WORKSPACE_SETTING, "wrkspc_x")
    assert "Set OPENFERMENT_WORKSPACE_ID" not in ready._said(e)
