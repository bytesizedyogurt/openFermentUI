"""POST /api/flowsheets/import-url through the app itself, with a stand-in network and resolver.

Usage (from core/): OPENFERMENT_DATABASE_URL=<a bh_ test database holding project sffp>
       .venv/bin/python -I import_url_route.py
The host public.test (a stand-in resolving to 93.184.216.34) answers /start with a redirect
whose Location is malformed, or serves a file with a title holding a NUL. Nothing leaves the
machine: httpx's AsyncHTTPTransport is replaced, for this process alone, by a MockTransport.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")
import httpx  # noqa: E402

REAL = httpx.AsyncHTTPTransport
SFF_NUL = b'{"units": [], "streams": [], "metadata": {"process_title": "nul \\u0000 title"}}'


async def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.raw_path.decode()
    if path == "/bad-location":
        return httpx.Response(302, headers={"location": "https:127.0.0.1/x"})
    if path == "/js-location":
        return httpx.Response(302, headers={"location": "javascript:alert(1)"})
    if path == "/nul.json":
        return httpx.Response(200, content=SFF_NUL, headers={"content-type": "application/json"})
    return httpx.Response(404)


httpx.AsyncHTTPTransport = lambda *a, **k: httpx.MockTransport(handler)  # type: ignore[misc]

from fastapi.testclient import TestClient  # noqa: E402

from openferment_core import api  # noqa: E402
from openferment_core.literature import collectors  # noqa: E402

collectors._resolve = lambda host, port: ["93.184.216.34"] if host == "public.test" else []
client = TestClient(api.app, raise_server_exceptions=False, base_url="http://127.0.0.1")
for path in ("/bad-location", "/js-location", "/nul.json"):
    r = client.post("/api/flowsheets/import-url", json={"url": f"https://public.test{path}", "by": "h8"},
                    headers={"X-OpenFerment-Project": "sffp"})
    print(path, "->", r.status_code, r.text[:300])
