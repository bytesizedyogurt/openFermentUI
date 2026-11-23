"""collectors.fetch_file under a stand-in network: redirects, sizes, compression, the deadline.

Usage (from core/): .venv/bin/python -I fetch_redirects.py
Nothing leaves the machine: `transport` stands in for the network (it receives the request
the pinned transport would send, its host already replaced by the checked address) and
`resolve` stands in for the system's resolver. Each case prints what fetch_file answered and
every address the stand-in network was asked to connect to.
"""
from __future__ import annotations

import asyncio
import gzip
import sys

sys.path.insert(0, ".")
import httpx  # noqa: E402

from openferment_core.literature import collectors  # noqa: E402

NAMES = {"public.test": ["93.184.216.34"], "other.test": ["151.101.1.1"], "private.test": ["10.0.0.7"],
         "mixed.test": ["93.184.216.34", "127.0.0.1"], "meta.test": ["169.254.169.254"]}


def resolve(host: str, port: int) -> list[str]:
    if host in NAMES:
        return NAMES[host]
    raise OSError(f"stand-in resolver: no such name {host}")


SFF = b'{"units": [], "streams": []}'


def network(script):
    """A stand-in network: `script(request)` answers each request; every connect is recorded."""
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.url.host}:{request.url.port or 443} Host={request.headers.get('host')} "
                    f"sni={request.extensions.get('sni_hostname')} path={request.url.raw_path.decode()}")
        return await script(request)

    return httpx.MockTransport(handler), seen


def case(name: str, url: str, script, limit: int = 16 * 1024 * 1024) -> None:
    transport, seen = network(script)
    try:
        got = collectors.fetch_file(url, limit=limit, transport=transport, resolve=resolve)
        said = f"FETCHED {len(got.data)} bytes served={got.served} kind={got.kind!r}"
    except Exception as e:  # each refusal is a result here
        said = f"{type(e).__name__}: {e}"
    print(f"\n[{name}] {url}\n   -> {said}\n   connects: {seen}")


def redirect_to(location: str, code: int = 302):
    async def script(request: httpx.Request) -> httpx.Response:
        if request.url.raw_path.decode() == "/start":
            return httpx.Response(code, headers={"location": location})
        return httpx.Response(200, content=SFF, headers={"content-type": "application/json"})
    return script


case("plain public file", "https://public.test/f.json", redirect_to("/x"))
for target in ["https://127.0.0.1/x", "https://localhost/x", "https://private.test/x", "https://meta.test/latest",
               "https://mixed.test/x", "http://public.test/x", "file:///etc/passwd", "ftp://public.test/x",
               "https://user:pw@other.test/x", "//127.0.0.1:8882/x", "/relative/ok", "https://other.test:8882/ok",
               "https://[::ffff:127.0.0.1]/x", "https://2130706433/x", "https://0x7f.1/x", "gopher://public.test/",
               "https://other.test/ok", "javascript:alert(1)", "https:/127.0.0.1/x", "https:127.0.0.1/x",
               "https://other.test\\@127.0.0.1/x"]:
    case(f"302 to {target}", "https://public.test/start", redirect_to(target))
case("307 to loopback", "https://public.test/start", redirect_to("https://127.0.0.1/x", 307))


async def loop(request: httpx.Request) -> httpx.Response:
    n = int(request.url.params.get("n", "0"))
    return httpx.Response(302, headers={"location": f"https://public.test/loop?n={n + 1}"})
case("redirect loop", "https://public.test/loop?n=0", loop)


async def big_declared(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers={"content-length": str(20 * 1024 * 1024)}, content=b"{}")
case("declares 20 MB", "https://public.test/big", big_declared)


async def big_streamed(request: httpx.Request) -> httpx.Response:
    async def body():
        for _ in range(20):
            yield b"x" * (1024 * 1024)
    return httpx.Response(200, content=body())
case("streams 20 MB, no length", "https://public.test/big", big_streamed)


async def gzip_bomb(request: httpx.Request) -> httpx.Response:
    raw = gzip.compress(b"\x20" * (40 * 1024 * 1024))
    return httpx.Response(200, headers={"content-encoding": "gzip"}, content=raw)
case("gzip of 40 MB in a small body", "https://public.test/bomb", gzip_bomb)


async def lies_small(request: httpx.Request) -> httpx.Response:
    async def body():
        for _ in range(20):
            yield b"y" * (1024 * 1024)
    return httpx.Response(200, headers={"content-length": "10"}, content=body())
case("says 10 bytes, sends 20 MB", "https://public.test/lie", lies_small)


async def err(request: httpx.Request) -> httpx.Response:
    return httpx.Response(503)
case("503 twice", "https://public.test/err", err)


async def html(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"<html>login</html>", headers={"content-type": "text/html; charset=utf-8"})
case("html page", "https://public.test/page", html)

collectors.FILE_TIMEOUT_S = 2.0


async def slow(request: httpx.Request) -> httpx.Response:
    async def body():
        for _ in range(10):
            await asyncio.sleep(0.5)
            yield b" "
    return httpx.Response(200, content=body())
case("drips past a 2 s deadline (FILE_TIMEOUT_S set to 2 here)", "https://public.test/slow", slow)
