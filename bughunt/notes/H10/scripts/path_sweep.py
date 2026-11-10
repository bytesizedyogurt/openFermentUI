"""Every operation in docs/api/openapi.json that takes a path parameter, sent with traversal, encoding,
NUL, absolute, injection and very long values in each one, over http.client (the path goes out verbatim).
POST/PUT/DELETE get an empty JSON object; the routes that reach a model or the network are left out.
Prints the status counts and every answer that is a 5xx or carries a stack trace, a file path, SQL,
the database address or an environment value.
Usage: python path_sweep.py http://127.0.0.1:8900 p1"""
import http.client
import json
import re
import sys
from collections import Counter
from urllib.parse import urlsplit

origin, project = sys.argv[1], sys.argv[2]
u = urlsplit(origin)
spec = json.load(open("/home/user/openFermentUI/docs/api/openapi.json"))

PROBES = {
    "dotdot": "../../../../etc/passwd",
    "dotdot-enc": "..%2f..%2f..%2f..%2fetc%2fpasswd",
    "dotdot-enc-dots": "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "double-enc": "%252e%252e%252f%252e%252e%252fetc%252fpasswd",
    "backslash": "..%5c..%5cetc%5cpasswd",
    "absolute": "%2fetc%2fpasswd",
    "nul": "abc%00def",
    "nul-raw-enc-dotdot": "..%00%2f..%2fetc",
    "long": "a" * 20000,
    "sql": "x'%20OR%20'1'='1",
    "sql2": "x%22%3B%20DROP%20TABLE%20projects%3B--",
    "unicode": "%E2%80%AE%F0%9F%A7%AA",
    "dot": ".",
    "dotdot-only": "..",
    "percent": "%25",
    "fmt": "%7B0%7D%25s%25d",
    "json": "%7B%22a%22%3A1%7D",
}
SKIP = {  # reach a model or the network
    "/api/intake/{paper_id}/extract",
    "/api/guild/checks/{check_id}/brief",
}
LEAK = re.compile(r"Traceback|File \"|/home/|/tmp/|site-packages|sqlalchemy|asyncpg|psycopg|\bSELECT\b|\bINSERT\b|"
                  r"postgresql|openferment:openferment|\.py\b|OPENFERMENT_|ANTHROPIC|/usr/|/root", re.I)


def send(method, path, body=None, headers=None):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=120)
    h = {"Host": f"127.0.0.1:{u.port}", "X-OpenFerment-Project": project}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for k, v in h.items():
        c.putheader(k, v)
    data = json.dumps(body).encode() if body is not None else b""
    if body is not None:
        c.putheader("Content-Length", str(len(data)))
    c.endheaders(data if body is not None else None)
    r = c.getresponse()
    text = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, text


def required_query(op):
    out = []
    for p in op.get("parameters", []):
        if p["in"] == "query" and p.get("required") and p["name"] != "project":
            out.append(f"{p['name']}=x")
    return ("?" + "&".join(out)) if out else ""


counts = Counter()
flagged = []
for path, item in spec["paths"].items():
    if "{" not in path or path in SKIP:
        continue
    names = re.findall(r"{([^}]+)}", path)
    for method, op in item.items():
        if method not in ("get", "post", "put", "delete"):
            continue
        for pname in names:
            for label, probe in PROBES.items():
                p = path
                for other in names:
                    p = p.replace("{" + other + "}", probe if other == pname else "ok")
                p += required_query(op)
                body = {} if method in ("post", "put") else None
                try:
                    status, text = send(method.upper(), p, body)
                except Exception as e:  # noqa: BLE001
                    status, text = 0, f"{type(e).__name__}: {e}"
                counts[(method.upper(), path, status)] += 1
                leak = LEAK.search(text)
                if status >= 500 or status == 0 or (leak and label not in ("dotdot",)) or status == 200:
                    flagged.append((method.upper(), path, pname, label, status, (leak.group(0) if leak else ""),
                                    text[:300].replace("\n", " ")))

for k, n in sorted(counts.items()):
    print(*k, n)
print("\n-- flagged --")
for f in flagged:
    print(" | ".join(str(x) for x in f))
