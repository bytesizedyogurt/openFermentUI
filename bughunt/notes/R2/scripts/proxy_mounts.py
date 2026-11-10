"""R2: what trust_env decides for the two clients whose 'no proxy' rule no test holds (mutations M16, M20).

collectors._fetch builds httpx.AsyncClient(transport=_Pinned(pins, network), trust_env=False): every request
goes through _Pinned, which connects to the address public_addresses checked. mcp_server's relay builds
httpx.Client(base_url=origin, trust_env=False, ...). Flip trust_env to True (the mutants M16 and M20, which
the suite passes) and, with a proxy in the environment, httpx mounts a proxy transport ahead of the client's
own: the request leaves through the proxy, and the pinned transport never sees it.

Measured: the import-url client keeps its pinned transport either way (httpx reads no proxy from the
environment once a client is handed a transport), so M20 changes nothing and is no hollow test. The relay is
built with no transport in the service's use (mcp_server passes transport=None outside its tests), so M16
sends every relayed call through the environment's proxy; the suite's relay tests hand it a stand-in
transport, which hides the setting, and pass.

This script makes no request: it asks each client which transport it would use for a URL.
Run: core/.venv/bin/python bughunt/notes/R2/scripts/proxy_mounts.py
"""
from __future__ import annotations

import os

import httpx

os.environ.pop("NO_PROXY", None)
os.environ.pop("no_proxy", None)
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8979"  # nothing listens there; no request is sent
os.environ["HTTP_PROXY"] = "http://127.0.0.1:8979"


class Pinned(httpx.AsyncBaseTransport):
    """Stands for collectors._Pinned."""


for trust in (False, True):
    pinned = Pinned()
    client = httpx.AsyncClient(transport=pinned, trust_env=trust)
    used = client._transport_for_url(httpx.URL("https://flowsheets.example/a.sff.json"))
    print(f"import-url fetch, trust_env={trust}: {'the pinned transport' if used is pinned else type(used).__name__ + ' (a proxy)'}")
    relay = httpx.Client(base_url="http://127.0.0.1:8970", trust_env=trust, follow_redirects=False)
    used = relay._transport_for_url(httpx.URL("http://127.0.0.1:8970/api/tools/catalogue_write"))
    print(f"MCP --service relay, trust_env={trust}: {type(used).__name__}"
          f"{' through ' + str(used._pool._proxy_url) if hasattr(used, '_pool') and hasattr(used._pool, '_proxy_url') else ''}")
