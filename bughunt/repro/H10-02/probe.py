"""H10-02's probe: the same NUL-bearing value (U+0000) at doors over text columns and at the doors
that already answer it in words. Each request names project r1. Prints one row per door: method,
path, status, whether the body is JSON with a `detail` in words, and the first bytes of the body.
The last line is a JSON summary run.sh reads.
Usage: python probe.py http://127.0.0.1:9960 r1 RAG_KEY"""
import http.client
import json
import sys
from urllib.parse import urlsplit

origin, project, rag_key = sys.argv[1], sys.argv[2], sys.argv[3]
u = urlsplit(origin)
N = "a%00b"  # the id a\x00b, percent-encoded in the path or the query

# The doors that answer this value in words today (the candidate's controls), and one ordinary
# missing id at a door the candidate names, to show what that door says for an id it does not hold.
CONTROLS = [
    ("GET", f"/api/studies/runbooks/{N}", None),
    ("GET", f"/api/biorepo/artifacts/{N}", None),
    ("GET", f"/api/catalogues/strain/{N}", None),
    ("GET", "/api/runs/no-such-run", None),
    ("GET", "/api/projects/no-such-project", None),
]
DOORS = [
    ("GET", f"/api/projects/{N}", None), ("GET", f"/api/runs/{N}", None),
    ("GET", f"/api/flowsheets/{N}", None), ("GET", f"/api/flowsheets/{N}/file", None),
    ("GET", f"/api/protocols/{N}", None), ("GET", f"/api/conversations/{N}", None),
    ("GET", f"/api/conversations/{N}/turns/t/calls", None),
    ("GET", f"/api/studies/scenarios/{N}", None), ("GET", f"/api/studies/comparisons/{N}", None),
    ("GET", f"/api/audit?who={N}", None), ("GET", f"/api/audit?action={N}", None),
    ("GET", f"/api/audit?target={N}", None), ("GET", f"/api/runs?engine={N}", None),
    ("GET", f"/api/biorepo/artifacts?tool={N}", None), ("GET", f"/api/proposals?state={N}", None),
    ("POST", "/api/projects", {"id": "nul-name", "name": "a\u0000b", "by": "bughunt"}),
    ("POST", "/api/projects", {"id": "nul-by", "name": "ab", "by": "bug\u0000hunt"}),
    ("POST", "/api/projects", {"id": "nul-desc", "name": "ab", "by": "bughunt", "description": "x\u0000"}),
    ("POST", f"/api/studies/scenarios/{N}/run", {"by": "bughunt"}),
    ("POST", "/api/practice/record", {"sessionId": "a\u0000b"}),
]
RAG = [
    ("GET", f"/rag/v1/documents/{N}", None),
    ("GET", f"/rag/v1/documents?search={N}", None),
]


def send(method, path, body=None, rag=False):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=60)
    h = {"Host": f"127.0.0.1:{u.port}", "X-OpenFerment-Project": project}
    if rag:
        h["Authorization"] = f"Bearer {rag_key}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    c.request(method, path, body=data, headers=h)
    r = c.getresponse()
    raw = r.read()
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)
        detail = parsed.get("detail") if isinstance(parsed, dict) else None
    except ValueError:
        detail = None
    worded = isinstance(detail, str) and len(detail.split()) >= 2
    return r.status, worded, text


def row(group, method, path, body=None, rag=False):
    s, worded, text = send(method, path, body, rag)
    label = path if body is None else f"{path} {json.dumps(body)}"
    shown = text[:70]
    if rag:
        try:
            j = json.loads(text)
            shown = f"title={j.get('title')!r} detail={str(j.get('detail'))[:60]!r}"
        except ValueError:
            pass
    print(f"  {method:4s} {label[:78]:78s} {s} {'words' if worded else 'BARE '} {shown!r}")
    return {"group": group, "method": method, "path": label, "status": s, "worded": worded, "body": text[:200]}


out = []
print("-- controls: the doors that answer a NUL id in words, and a plain missing id")
out += [row("control", m, p, b) for m, p, b in CONTROLS]
print("-- /api doors over text columns: the same NUL value")
out += [row("api", m, p, b) for m, p, b in DOORS]
print("-- /rag doors (the kit), with the mount's key")
out += [row("rag", m, p, b, rag=True) for m, p, b in RAG]
print("SUMMARY " + json.dumps(out))
