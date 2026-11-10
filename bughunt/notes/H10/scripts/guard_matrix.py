"""Guard probe matrix over real HTTP: each row sends a changing request (POST /api/biorepo/check, which
writes nothing) with forged Host / Origin / Referer / X-Forwarded-* headers and prints the status.
403 = the guard refused; 422 = it reached the endpoint (empty body refused by the endpoint itself).
Usage: python guard_matrix.py http://127.0.0.1:8900"""
import socket
import sys
from urllib.parse import urlsplit

origin = sys.argv[1]
u = urlsplit(origin)
PATH = "/api/biorepo/check"


def raw(headers: list[tuple[str, str]], method="POST", path=PATH, body=b"{}"):
    """Send exactly these header lines (Host included) over a raw socket; return the status line."""
    s = socket.create_connection((u.hostname, u.port), timeout=10)
    lines = [f"{method} {path} HTTP/1.1"] + [f"{k}: {v}" for k, v in headers]
    lines += ["Content-Type: application/json", f"Content-Length: {len(body)}", "Connection: close", "", ""]
    s.sendall("\r\n".join(lines).encode("latin-1") + body)
    data = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    head, _, rest = data.partition(b"\r\n\r\n")
    return head.split(b"\r\n")[0].decode(), rest[:200].decode("latin-1", "replace")


H = f"127.0.0.1:{u.port}"
rows = [
    ("own page", [("Host", H), ("Origin", f"http://{H}")]),
    ("no origin (script)", [("Host", H)]),
    ("cross-site origin", [("Host", H), ("Origin", "https://evil.example.com")]),
    ("origin null", [("Host", H), ("Origin", "null")]),
    ("rebound hostile host", [("Host", f"evil.example.com:{u.port}"), ("Origin", f"http://evil.example.com:{u.port}")]),
    ("rebound hostile host, no origin", [("Host", f"evil.example.com:{u.port}")]),
    ("host trailing dot localhost.", [("Host", f"localhost.:{u.port}"), ("Origin", f"http://localhost.:{u.port}")]),
    ("dotless host (search-domain name)", [("Host", f"evil:{u.port}"), ("Origin", f"http://evil:{u.port}")]),
    ("x.localhost", [("Host", f"evil.localhost:{u.port}"), ("Origin", f"http://evil.localhost:{u.port}")]),
    ("x.local (mDNS)", [("Host", f"evil.local:{u.port}"), ("Origin", f"http://evil.local:{u.port}")]),
    ("ts.net", [("Host", f"attacker.tailabcd.ts.net"), ("Origin", "https://attacker.tailabcd.ts.net")]),
    ("referer only, cross-site", [("Host", H), ("Referer", "https://evil.example.com/page")]),
    ("xfh forged, cross-site origin", [("Host", H), ("Origin", "https://evil.example.com"), ("X-Forwarded-Host", "evil.example.com")]),
    ("xfh loopback, other-port origin", [("Host", H), ("Origin", "http://127.0.0.1:3000"), ("X-Forwarded-Host", "127.0.0.1:3000")]),
    ("xff forged", [("Host", H), ("Origin", "https://evil.example.com"), ("X-Forwarded-For", "127.0.0.1")]),
    ("two origins (good first)", [("Host", H), ("Origin", f"http://{H}"), ("Origin", "https://evil.example.com")]),
    ("two origins (evil first)", [("Host", H), ("Origin", "https://evil.example.com"), ("Origin", f"http://{H}")]),
    ("two hosts (evil first)", [("Host", f"evil.example.com:{u.port}"), ("Host", H), ("Origin", f"http://evil.example.com:{u.port}")]),
    ("origin uppercase", [("Host", H), ("Origin", f"HTTP://127.0.0.1:{u.port}")]),
    ("origin with path", [("Host", H), ("Origin", f"http://{H}/x")]),
    ("origin userinfo", [("Host", H), ("Origin", f"http://evil.example.com@{H}")]),
    ("host userinfo", [("Host", f"evil.example.com@127.0.0.1:{u.port}"), ("Origin", f"http://evil.example.com@127.0.0.1:{u.port}")]),
    ("origin ws scheme", [("Host", H), ("Origin", f"ws://{H}")]),
    ("origin file://", [("Host", H), ("Origin", "file://")]),
    ("origin empty", [("Host", H), ("Origin", "")]),
    ("decimal IP host", [("Host", f"2130706433:{u.port}"), ("Origin", f"http://2130706433:{u.port}")]),
    ("ipv6 mapped", [("Host", f"[::ffff:127.0.0.1]:{u.port}"), ("Origin", f"http://[::ffff:127.0.0.1]:{u.port}")]),
    ("public IP host", [("Host", f"93.184.216.34:{u.port}"), ("Origin", f"http://93.184.216.34:{u.port}")]),
    ("funnel header", [("Host", H), ("Tailscale-Funnel-Request", "?1")]),
    ("no host header", [("Origin", f"http://{H}")]),
]
for name, headers in rows:
    try:
        status, body = raw(headers)
    except Exception as e:  # noqa: BLE001
        status, body = f"ERR {e}", ""
    print(f"{name:40s} {status:28s} {body[:110]!r}")

print("\n-- methods (cross-site origin) --")
for m in ("PATCH", "PUT", "DELETE", "post", "OPTIONS", "FOO", "PROPFIND"):
    status, body = raw([("Host", H), ("Origin", "https://evil.example.com")], method=m)
    print(f"{m:10s} {status:28s} {body[:110]!r}")
