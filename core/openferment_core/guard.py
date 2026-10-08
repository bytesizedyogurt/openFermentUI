"""Which requests may change something (OF-BLD-012 §B.6).

The service has no login. Bound to loopback and published by `tailscale
serve`, only the owner's own devices reach it. Two browser tricks would still
let a web page the owner happens to open change things through his browser:

- **A cross-site request.** A page on another site posts to this service; the
  browser sends it, and it lands. The browser also says where it came from, in
  `Origin`, and that is a host other than this one.
- **DNS rebinding.** A hostile name is made to resolve to the Mini, so the page
  and the service look like one site to the browser. The request then names
  that hostile domain in `Host`.

So a request that changes something (POST, PUT, PATCH, DELETE) must name a
host this service answers to, and when the browser states an Origin, it must
be that same host on the same port: a browser treats another port as another
site, so another local app (a notebook server, a docs preview) is one too.
A request that came in through Tailscale Funnel, from the public internet,
changes nothing. Reads stay open: everything they return is literature and
counts, and the app has to load before anything else can happen.

A host this service answers to: an IP address, a name with no dot, a `.local`
name (Bonjour), a `.ts.net` name (Tailscale's names for the owner's devices),
or one listed in OPENFERMENT_ALLOWED_HOSTS. Each of these is answered by the
owner's own network or by Tailscale; a rebinding attack needs a public domain
whose DNS the attacker answers, and none of these is one.
"""
from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
OWN_SUFFIXES = (".local", ".localhost", ".ts.net")
DEFAULT_PORTS = {"http": 80, "https": 443}
# Set by `tailscale serve` on a request that arrived through Funnel; Tailscale
# deletes any copy a client sends, so its presence is Tailscale's word.
FUNNEL = "tailscale-funnel-request"


def _split(value: str | None) -> tuple[str, int | None, str] | None:
    if not value or value == "null":
        return None
    try:
        parts = urlsplit(value if "//" in value else "//" + value)
        host, port = parts.hostname, parts.port
    except ValueError:
        return None
    return (host, port, parts.scheme) if host else None


def hostname(value: str | None) -> str | None:
    """The host in a Host header or an Origin, lowercased, without port or
    brackets. None for an absent, empty or unparseable value, and for the
    Origin `null` a sandboxed page or a file sends."""
    parts = _split(value)
    return parts[0] if parts else None


def extra_hosts() -> frozenset[str]:
    raw = os.environ.get("OPENFERMENT_ALLOWED_HOSTS", "")
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def answers_to(host: str | None) -> bool:
    if not host:
        return False
    if host in extra_hosts():
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    return "." not in host or host.endswith(OWN_SUFFIXES)


def same_site(origin: str | None, host: str | None) -> bool:
    """Whether a browser Origin names the host a Host-style header does, on
    the same port. A Host with no port means its scheme's default, so the
    Origin must be on 80 or 443. The loopback names count as one machine."""
    o, h = _split(origin), _split(host)
    if o is None or h is None or o[2] not in DEFAULT_PORTS:
        return False
    if not (o[0] == h[0] or (o[0] in LOOPBACK and h[0] in LOOPBACK)):
        return False
    origin_port = o[1] or DEFAULT_PORTS[o[2]]
    return origin_port == h[1] if h[1] is not None else origin_port in DEFAULT_PORTS.values()


def refusal(method: str, headers: Mapping[str, str]) -> str | None:
    """Why this request may not proceed, or None when it may."""
    if method.upper() not in CHANGING:
        return None
    if FUNNEL in headers:
        return "a request through Tailscale Funnel comes from the public internet and may not change anything"
    host = hostname(headers.get("host"))
    if not answers_to(host):
        return (
            f"this service does not answer to {host or 'a request with no Host'!r}. "
            "Add the name to OPENFERMENT_ALLOWED_HOSTS if it is yours"
        )
    if "origin" not in headers:
        return None  # not a browser: curl, a script, the test client
    origin = headers.get("origin")
    # A proxy in front may present itself as Host and pass the address the
    # browser used in X-Forwarded-Host. Both proxies that stand in front of
    # this service set it themselves, overwriting whatever the request
    # carried: Vite's dev proxy (vite.config.ts), and tailscale serve
    # (ipn/ipnlocal/serve.go). A request straight to the service can carry
    # any value, but a cross-site page could only add the header after a
    # preflight, and this service approves none.
    forwarded = headers.get("x-forwarded-host")
    if same_site(origin, headers.get("host")) or (
        forwarded and answers_to(hostname(forwarded)) and same_site(origin, forwarded)
    ):
        return None
    return f"a page on {origin or 'an unnamed origin'!r} may not change anything here"
