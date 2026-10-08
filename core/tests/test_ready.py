"""pnpm ready: each check says the right thing, and never the key (OF-BLD-012 §B.9).

Offline: the model check is handed a fake client that answers or raises the
way the Anthropic SDK does; the network checks run in fixture mode, where
they skip.
"""
from __future__ import annotations

import plistlib
from pathlib import Path

import anthropic
import pytest

from openferment_core import api, biorepo, extract, intake, llm, ready

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
def _scratch(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENFERMENT_FIXTURES", raising=False)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


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


def test_network_checks_skip_in_fixture_mode(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    assert ready.check_model(True, client_factory=FakeClient).mark == "skip"
    assert ready.check_europe_pmc().mark == "skip"
    assert ready.check_backup().mark == "skip"


# ── what is on disk ────────────────────────────────────────────────────


def test_intake_counts_what_was_fetched_and_extracted(monkeypatch):
    assert ready.check_intake().mark == "warn", "nothing fetched is worth knowing"
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    intake.fetch_paper({"id": "B5", "pmcid": "structural"})
    check = ready.check_intake()
    assert check.mark == "ok" and check.detail.startswith("1 papers fetched with full text")


def test_a_damaged_fetch_is_named_and_the_rest_still_run(monkeypatch):
    intake.FULLTEXT_DIR.mkdir(parents=True)
    (intake.FULLTEXT_DIR / "A1.json").write_text('{"paperId": "A1", "sta', encoding="utf-8")
    check = ready.check_intake()
    assert check.mark == "warn" and "1 damaged (A1.json)" in check.detail
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    names = [c.name for c in ready.run(no_network=True, port=1)]
    assert names[-1] == "service", "a damaged file must not stop the checks after it"


def test_a_damaged_corpus_is_a_failure_with_the_fix(monkeypatch):
    def damaged():
        raise ValueError("Expecting value: line 1 column 1")

    monkeypatch.setattr(ready, "load_corpus", damaged)
    check = ready.check_corpus()
    assert check.mark == "fail" and "pnpm export:corpus" in check.detail


def test_data_reports_a_file_that_does_not_parse():
    biorepo.PATH.write_text("{ not json", encoding="utf-8")
    assert ready.check_data().mark == "fail"


def test_data_counts_decisions():
    check = ready.check_data()
    assert check.mark == "ok" and check.detail.startswith("0 review decisions")


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
