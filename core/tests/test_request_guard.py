"""Only the owner's own pages may change anything (OF-BLD-012 §B.6).

Through the app: a changing request blocked by the guard comes back 403 with
the reason; one it lets through reaches the endpoint, which answers an empty
body with 422. `POST /api/biorepo/check` writes nothing either way.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import guard
from openferment_core.api import app

PATH = "/api/biorepo/check"


@pytest.fixture
def client():
    return TestClient(app)


def post(client, **headers):
    return client.post(PATH, json={}, headers=headers)


# ── refused ────────────────────────────────────────────────────────────


def test_a_page_on_another_site_is_refused(client):
    r = post(client, host="127.0.0.1:8000", origin="https://evil.example.com")
    assert r.status_code == 403
    assert "evil.example.com" in r.json()["detail"]


def test_a_rebound_hostile_name_is_refused(client):
    # The page and the service look like one site, so Origin matches Host.
    r = post(client, host="rebind.evil.example.com:8000", origin="http://rebind.evil.example.com:8000")
    assert r.status_code == 403
    assert "does not answer to" in r.json()["detail"]


def test_a_sandboxed_page_or_a_file_is_refused(client):
    assert post(client, host="127.0.0.1:8000", origin="null").status_code == 403


@pytest.mark.parametrize(
    "headers",
    [
        {"host": "127.0.0.1:8000", "origin": "http://127.0.0.1:3000"},  # another local app
        {"host": "127.0.0.1:8000", "origin": "http://localhost:8888"},  # a notebook server
        {"host": "mini.tail1234.ts.net", "origin": "https://mini.tail1234.ts.net:8443"},  # another serve port
        {"host": "localhost:8000", "origin": "http://127.0.0.1:5173"},  # a dev proxy that does not say who it forwards for
    ],
)
def test_another_port_is_another_site(client, headers):
    assert post(client, **headers).status_code == 403


def test_a_request_through_funnel_is_refused(client):
    headers = {
        "host": "mini.tail1234.ts.net",
        "origin": "https://mini.tail1234.ts.net",
        "tailscale-funnel-request": "?1",
    }
    r = post(client, **headers)
    assert r.status_code == 403 and "Funnel" in r.json()["detail"]


def test_a_forwarded_name_cannot_launder_a_hostile_host(client):
    r = post(
        client,
        host="rebind.evil.example.com",
        origin="http://rebind.evil.example.com",
        **{"x-forwarded-host": "127.0.0.1"},
    )
    assert r.status_code == 403


# ── let through ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "headers",
    [
        {"host": "127.0.0.1:8000", "origin": "http://127.0.0.1:8000"},  # the Mini itself
        {"host": "localhost:8000", "origin": "http://127.0.0.1:5173", "x-forwarded-host": "127.0.0.1:5173"},  # pnpm dev
        {
            "host": "localhost:8000",
            "origin": "http://100.101.102.103:5173",
            "x-forwarded-host": "100.101.102.103:5173",
        },  # pnpm dev, opened from another device
        {"host": "[::1]:8000", "origin": "http://[::1]:8000"},
        {
            "host": "mini.tail1234.ts.net",
            "origin": "https://mini.tail1234.ts.net",
            "x-forwarded-host": "mini.tail1234.ts.net",
        },  # tailscale serve: Host kept, X-Forwarded-Host set
        {
            "host": "127.0.0.1:8000",
            "origin": "https://mini.tail1234.ts.net",
            "x-forwarded-host": "mini.tail1234.ts.net",
        },  # a proxy that rewrites Host
        {"host": "192.168.1.5:4173", "origin": "http://192.168.1.5:4173"},  # the demo, on purpose
        {"host": "mac-mini.local:8000", "origin": "http://mac-mini.local:8000"},
        {"host": "mac-mini:8000", "origin": "http://mac-mini:8000"},  # a MagicDNS short name
        {"host": "127.0.0.1:8000"},  # curl or a script: no Origin
    ],
)
def test_the_owners_own_requests_reach_the_endpoint(client, headers):
    assert post(client, **headers).status_code == 422


def test_reads_stay_open(client):
    r = client.get("/api/health", headers={"host": "rebind.evil.example.com"})
    assert r.status_code == 200


def test_a_listed_name_is_answered(client, monkeypatch):
    headers = {"host": "openferment.example.org", "origin": "https://openferment.example.org"}
    assert post(client, **headers).status_code == 403
    monkeypatch.setenv("OPENFERMENT_ALLOWED_HOSTS", "other.example.net, openferment.example.org")
    assert post(client, **headers).status_code == 422


# ── the parts ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("127.0.0.1:8000", "127.0.0.1"),
        ("[::1]:8000", "::1"),
        ("Mini.Tail1234.TS.net", "mini.tail1234.ts.net"),
        ("https://mini.tail1234.ts.net", "mini.tail1234.ts.net"),
        ("null", None),
        ("", None),
        (None, None),
    ],
)
def test_hostname(value, expected):
    assert guard.hostname(value) == expected


@pytest.mark.parametrize(
    ("origin", "host", "same"),
    [
        ("http://127.0.0.1:8000", "127.0.0.1:8000", True),
        ("http://localhost:8000", "127.0.0.1:8000", True),
        ("http://127.0.0.1:8001", "127.0.0.1:8000", False),
        ("https://mini.tail1234.ts.net", "mini.tail1234.ts.net", True),
        ("http://mini.local", "mini.local", True),
        ("https://mini.tail1234.ts.net:8443", "mini.tail1234.ts.net", False),
        ("https://mini.tail1234.ts.net:8443", "mini.tail1234.ts.net:8443", True),
        ("http://other.local:8000", "mini.local:8000", False),
        ("null", "127.0.0.1:8000", False),
        ("chrome-extension://abc", "abc", False),
    ],
)
def test_same_site(origin, host, same):
    assert guard.same_site(origin, host) is same


def test_only_changing_methods_are_checked():
    hostile = {"host": "rebind.evil.example.com", "origin": "https://evil.example.com"}
    for method in ("GET", "HEAD", "OPTIONS"):
        assert guard.refusal(method, hostile) is None
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert guard.refusal(method, hostile) is not None
