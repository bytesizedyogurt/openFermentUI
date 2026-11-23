"""Every POST, PUT and DELETE in docs/api/openapi.json sent bodies a client gets wrong: broken JSON, a
list, a string, an object of wrong types, and (outside the routes that reach a model or the network) an
empty object and one whose every string is a NUL. Path parameters take 'x'. Prints each 5xx and each
answer carrying a stack trace, a file path, SQL or an environment value, then the status counts.
Usage: python body_sweep.py http://127.0.0.1:8906 p1"""
import http.client
import json
import re
import sys
from collections import Counter
from urllib.parse import urlsplit

origin, project = sys.argv[1], sys.argv[2]
u = urlsplit(origin)
spec = json.load(open("/home/user/openFermentUI/docs/api/openapi.json"))
REACHES_OUT = ("/api/ask", "/api/ask/stream", "/api/literature/answer", "/api/intake/{paper_id}/extract",
               "/api/intake/collect", "/api/flowsheets/import-url", "/api/flowsheets/library/{file_id}",
               "/api/guild/checks/{check_id}/brief", "/api/guild/checks/propose", "/api/pureos/propose",
               "/api/practice/turn", "/api/practice/draft", "/api/tools/{name}")
LEAK = re.compile(r"Traceback|File \"|/home/|/tmp/|site-packages|sqlalchemy|asyncpg|psycopg|\bSELECT\b|"
                  r"postgresql|openferment:openferment|OPENFERMENT_|ANTHROPIC|/usr/|/root", re.I)
BODIES = {"broken": b"{", "list": b"[]", "string": b'"x"', "wrongtypes": b'{"by": 5, "id": [], "name": {}}'}


def send(method, path, raw, ctype="application/json"):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=120)
    c.request(method, path, body=raw, headers={"Host": f"127.0.0.1:{u.port}", "X-OpenFerment-Project": project,
                                                "Content-Type": ctype})
    r = c.getresponse()
    return r.status, r.read()[:400].decode("utf-8", "replace")


def nul_body(schema_ref):
    name = schema_ref.rsplit("/", 1)[-1]
    props = spec["components"]["schemas"].get(name, {}).get("properties", {})
    return json.dumps({k: "a\u0000b" for k, v in props.items() if v.get("type") == "string"}).encode()


counts = Counter()
for path, item in spec["paths"].items():
    for method, op in item.items():
        if method not in ("post", "put", "delete"):
            continue
        p = re.sub(r"{[^}]+}", "x", path)
        bodies = dict(BODIES)
        out = path in REACHES_OUT
        content = op.get("requestBody", {}).get("content", {})
        if not out and "application/json" in content:
            bodies["empty"] = b"{}"
            ref = content["application/json"]["schema"].get("$ref")
            if ref:
                bodies["nul-strings"] = nul_body(ref)
        if "multipart/form-data" in content:
            bodies = {"not-multipart": b"{}"}
        for label, raw in bodies.items():
            s, t = send(method.upper(), p, raw)
            counts[s] += 1
            leak = LEAK.search(t)
            if s >= 500 or leak:
                print(f"{method.upper():6s} {path:55s} {label:12s} {s} {(leak.group(0) if leak else '')!r} {t[:140]!r}")
print(dict(sorted(counts.items())))
