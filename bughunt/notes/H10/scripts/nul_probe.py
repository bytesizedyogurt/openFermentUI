"""A NUL character (U+0000) where a person or a client can put one: an id in the path, a filter in the
query, a text field in a body. Each request names project P; the expected answer is a refusal in words
(4xx with a detail), and a 500 is the finding. Prints status and the first bytes of each answer.
Usage: python nul_probe.py http://127.0.0.1:8900 p1 [RAG_KEY]"""
import http.client
import json
import sys
from urllib.parse import urlsplit

origin, project = sys.argv[1], sys.argv[2]
rag_key = sys.argv[3] if len(sys.argv) > 3 else None
u = urlsplit(origin)
N = "a%00b"
GETS = [
    f"/api/projects/{N}", f"/api/runs/{N}", f"/api/flowsheets/{N}", f"/api/flowsheets/{N}/file",
    f"/api/protocols/{N}", f"/api/conversations/{N}", f"/api/conversations/{N}/turns/t/calls",
    f"/api/studies/scenarios/{N}", f"/api/studies/comparisons/{N}", f"/api/studies/runbooks/{N}",
    f"/api/biorepo/artifacts/{N}", f"/api/catalogues/strain/{N}", f"/api/pureos/train/{N}",
    f"/api/audit?who={N}", f"/api/audit?action={N}", f"/api/audit?target={N}", f"/api/runs?engine={N}",
    f"/api/biorepo/artifacts?tool={N}", f"/api/proposals?state={N}", f"/api/depositions/readings?unit={N}",
]
POSTS = [
    ("/api/projects", {"id": "nul-name", "name": "a\u0000b", "by": "bughunt"}),
    ("/api/projects", {"id": "nul-by", "name": "ab", "by": "bug\u0000hunt"}),
    ("/api/projects", {"id": "nul-desc", "name": "ab", "by": "bughunt", "description": "x\u0000"}),
    (f"/api/studies/scenarios/{N}/run", {"by": "bughunt"}),
    (f"/api/studies/runbooks/{N}/lock", {"by": "bughunt"}),
    (f"/api/proposals/{N}/dismiss", {"by": "bughunt"}),
    ("/api/practice/record", {"sessionId": "a\u0000b"}),
]


def send(method, path, body=None, extra=None):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=60)
    h = {"Host": f"127.0.0.1:{u.port}", "X-OpenFerment-Project": project, **(extra or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    c.request(method, path, body=data, headers=h)
    r = c.getresponse()
    text = r.read()[:160].decode("utf-8", "replace")
    return r.status, text


fives = 0
for p in GETS:
    s, t = send("GET", p)
    fives += s >= 500
    print(f"GET  {p:48s} {s} {t[:100]!r}")
for p, b in POSTS:
    s, t = send("POST", p, b)
    fives += s >= 500
    print(f"POST {p:48s} {s} {t[:100]!r}")
if rag_key:
    for p in (f"/rag/v1/documents/{N}", f"/rag/v1/documents?search={N}"):
        s, t = send("GET", p, extra={"Authorization": f"Bearer {rag_key}"})
        fives += s >= 500
        print(f"GET  {p:48s} {s} {t[:100]!r}")
print(f"\n{fives} answers were a 5xx")
