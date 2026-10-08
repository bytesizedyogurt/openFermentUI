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
be that same host. Reads stay open: everything they return is literature and
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


def hostname(value: str | None) -> str | None:
    """The host in a Host header or an Origin, lowercased, without port or
    brackets. None for an absent, empty or unparseable value, and for the
    Origin `null` a sandboxed page or a file sends."""
    if not value or value == "null":
        return None
    try:
        return urlsplit(value if "//" in value else "//" + value).hostname or None
    except ValueError:
        return None


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


def _same(a: str | None, b: str | None) -> bool:
    # The dev proxy asks for localhost while the page may be on 127.0.0.1; the
    # loopback names are one machine.
    return a is not None and (a == b or (a in LOOPBACK and b in LOOPBACK))


def refusal(method: str, headers: Mapping[str, str]) -> str | None:
    """Why this request may not proceed, or None when it may."""
    if method.upper() not in CHANGING:
        return None
    host = hostname(headers.get("host"))
    if not answers_to(host):
        return (
            f"this service does not answer to {host or 'a request with no Host'!r}. "
            "Add the name to OPENFERMENT_ALLOWED_HOSTS if it is yours"
        )
    if "origin" not in headers:
        return None  # not a browser: curl, a script, the test client
    origin = hostname(headers.get("origin"))
    # A proxy in front (tailscale serve) may present itself as Host and pass
    # the name the browser used in X-Forwarded-Host. A cross-site page cannot
    # set that header without a preflight this service never approves.
    forwarded = hostname(headers.get("x-forwarded-host"))
    if _same(origin, host) or (forwarded and answers_to(forwarded) and _same(origin, forwarded)):
        return None
    return f"a page on {origin or 'an unnamed origin'!r} may not change anything here"
