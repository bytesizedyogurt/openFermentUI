"""POST /api/flowsheets/import-url with every address form the brief names; record each answer.

Usage: python import_url_probe.py ORIGIN PROJECT OUT.jsonl
Start listeners.py on 127.0.0.1:8882-8885 first: a line in its log means a request reached
loopback. No address here names a public host the service would connect to: every public
name is refused before a connection (scheme, credentials, length) or resolves to a private
address.
"""
from __future__ import annotations

import json
import sys

import httpx

origin, project, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = 8882
URLS = [
    # loopback, every spelling
    f"https://127.0.0.1:{P}/a.json", f"https://localhost:{P}/a.json", f"https://LOCALHOST.:{P}/a.json",
    f"https://localhost.localdomain:{P}/a.json", f"https://[::1]:{P}/a.json", f"https://0.0.0.0:{P}/a.json",
    f"https://0:{P}/a.json", f"https://127.1:{P}/a.json", f"https://127.0.1:{P}/a.json",
    f"https://2130706433:{P}/a.json", f"https://017700000001:{P}/a.json", f"https://0x7f000001:{P}/a.json",
    f"https://0x7f.0.0.1:{P}/a.json", f"https://0177.0.0.1:{P}/a.json", f"https://127.0.0.1.:{P}/a.json",
    f"https://127.000.000.001:{P}/a.json", f"https://%31%32%37.0.0.1:{P}/a.json",
    f"https://１２７.０.０.１:{P}/a.json",
    f"https://[::ffff:127.0.0.1]:{P}/a.json", f"https://[::ffff:7f00:1]:{P}/a.json",
    f"https://[0:0:0:0:0:ffff:127.0.0.1]:{P}/a.json", f"https://[::127.0.0.1]:{P}/a.json",
    f"https://[64:ff9b::7f00:1]:{P}/a.json", f"https://[2002:7f00:1::]:{P}/a.json",
    f"https://[fe80::1%25lo]:{P}/a.json", f"https://[::]:{P}/a.json",
    # private, link-local, shared, reserved, multicast
    "https://10.0.0.1/a.json", "https://10.255.255.255/a.json", "https://172.16.0.1/a.json",
    "https://172.31.255.255/a.json", "https://192.168.1.1/a.json", "https://169.254.169.254/latest/meta-data/",
    "https://100.64.0.1/a.json", "https://198.18.0.1/a.json", "https://192.0.0.1/a.json", "https://192.0.2.1/a.json",
    "https://240.0.0.1/a.json", "https://255.255.255.255/a.json", "https://224.0.0.1/a.json",
    "https://[fc00::1]/a.json", "https://[fd12:3456::1]/a.json", "https://[::ffff:169.254.169.254]/a.json",
    "https://[::ffff:a9fe:a9fe]/a.json", "https://[::ffff:10.0.0.1]/a.json", "https://[ff02::1]/a.json",
    "https://[2001:db8::1]/a.json", "https://[100::1]/a.json",
    # a public name that resolves to a private address
    "https://10.0.0.1.nip.io/a.json",
    # schemes
    f"http://127.0.0.1:{P}/a.json", "http://example.com/a.json", "file:///etc/passwd", f"ftp://127.0.0.1:{P}/a.json",
    f"gopher://127.0.0.1:{P}/", "data:application/json,{}", "javascript:alert(1)", "//example.com/a.json",
    "example.com/a.json", "https:///a.json", "https://", "", "   ",
    # credentials
    "https://user:pass@example.com/a.json", f"https://user@127.0.0.1:{P}/a.json", "https://:pw@example.com/a.json",
    # header injection, spaces
    f"https://127.0.0.1:{P}/a.json\r\nX-Injected: 1", f"https://127.0.0.1:{P}/a b.json",
    # very long
    "https://example.com/" + "a" * 2100, "https://10.0.0.1/" + "a" * 2000,
]

c = httpx.Client(base_url=origin, trust_env=False, timeout=120, headers={"X-OpenFerment-Project": project})
rows = []
for url in URLS:
    try:
        r = c.post("/api/flowsheets/import-url", json={"url": url, "by": "h8"})
        try:
            body = r.json()
        except ValueError:
            body = r.text[:200]
        status = r.status_code
    except httpx.HTTPError as e:
        status, body = "client-error", f"{type(e).__name__}: {e}"
    detail = body.get("detail") if isinstance(body, dict) else body
    if isinstance(detail, list):
        detail = "; ".join(f"{d.get('loc')}: {d.get('msg')}" for d in detail)
    rows.append({"url": url, "status": status, "detail": detail})
    print(f"{status} | {url[:80]!r} | {str(detail)[:230]}")
open(out, "w").write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
kept = c.get("/api/flowsheets").json()
print("records kept in the project:", len(kept), [k["id"] for k in kept])
