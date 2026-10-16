"""A key not scoped to a workspace needs the workspace named on each request
(the API's 400 says so); OPENFERMENT_WORKSPACE_ID sends it."""
from __future__ import annotations

from openferment_core import llm, ready


def _sent_headers(client) -> dict:
    """The headers the client sends with every request."""
    return dict(client.default_headers)


def test_the_workspace_id_is_sent_when_set(monkeypatch):
    monkeypatch.setenv(llm.WORKSPACE_SETTING, " wrkspc_abc ")
    headers = _sent_headers(llm.make_client(api_key="sk-ant-test"))
    assert headers["anthropic-workspace-id"] == "wrkspc_abc"


def test_nothing_extra_is_sent_when_unset(monkeypatch):
    monkeypatch.delenv(llm.WORKSPACE_SETTING, raising=False)
    headers = _sent_headers(llm.make_client(api_key="sk-ant-test"))
    assert "anthropic-workspace-id" not in headers


def test_every_client_the_service_builds_goes_through_make_client():
    import inspect

    assert "make_client(api_key=key)" in inspect.getsource(llm._default_client)
    assert inspect.getsource(ready).count("client_factory or llm.make_client") == 2
