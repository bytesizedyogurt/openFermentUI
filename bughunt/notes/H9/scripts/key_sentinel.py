"""H9: the per-request key override (X-OpenFerment-Key) on every route that may call a
model, against a service whose model API is a loopback stand-in (standin_model_api.py).

    bh_py ../bughunt/notes/H9/scripts/key_sentinel.py ORIGIN PROJECT DOCUMENT_ID SENTINEL ENVKEY STANDIN_RECORD OUT_DIR

For each route: the stand-in's record before and after, so each model request is tied to
the route that made it, and which key it carried (x-api-key). Every response's status,
headers and body is saved under OUT_DIR, and the project's event stream is read the whole
time into OUT_DIR/events.txt.
"""
from __future__ import annotations

import json
import sys
import threading
import time

import httpx

ORIGIN, PROJECT, DOC, SENTINEL, ENVKEY, RECORD, OUT = sys.argv[1:8]
P = {"X-OpenFerment-Project": PROJECT}
K = {**P, "X-OpenFerment-Key": SENTINEL}
http = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=httpx.Timeout(300.0, connect=10.0))

stop = threading.Event()


def read_events() -> None:
    with httpx.Client(base_url=ORIGIN, trust_env=False, timeout=None) as c, \
            c.stream("GET", "/api/events", params={"project": PROJECT}) as r, open(f"{OUT}/events.txt", "w") as f:
        for chunk in r.iter_text():
            f.write(chunk)
            f.flush()
            if stop.is_set():
                return


threading.Thread(target=read_events, daemon=True).start()
time.sleep(1.0)


def record() -> list[dict]:
    try:
        return [json.loads(line) for line in open(RECORD)]
    except FileNotFoundError:
        return []


ROUTES = [
    ("ask", "POST", "/api/ask", {"json": {"question": "Which sugars does the yeast ferment?", "by": "Tester"}}),
    ("ask-stream", "POST", "/api/ask/stream", {"json": {"question": "And the ethanol yield?", "by": "Tester"}}),
    ("extract", "POST", f"/api/intake/{DOC}/extract", {}),
    ("literature-answer", "POST", "/api/literature/answer", {"json": {"question": "What does the yeast ferment?"}}),
    ("literature-search-deep", "GET", "/api/literature/search", {"params": {"q": "xylose uptake", "profile": "deep"}}),
    ("rag-answer", "POST", "/rag/v1/answer", {"json": {"query": "What does the yeast ferment?"},
                                               "headers": {"Authorization": "Bearer bh-h9-ragkey"}}),
    ("rag-query-deep", "POST", "/rag/v1/query", {"json": {"query": "xylose uptake", "profile": "deep"},
                                                  "headers": {"Authorization": "Bearer bh-h9-ragkey"}}),
    ("tool-intake-extract", "POST", "/api/tools/intake_write",
     {"json": {"action": "extract", "target": DOC, "fields": {}, "note": "extract it"},
      "headers": {"X-OpenFerment-Assistant": "keybot/1.0"}}),
    ("tool-search-passages", "POST", "/api/tools/search_passages", {"json": {"query": "glucose", "k": 3}}),
    ("health", "GET", "/api/health", {}),
]

summary = []
for label, method, path, kw in ROUTES:
    before = len(record())
    headers = {**K, **kw.pop("headers", {})}
    t0 = time.monotonic()
    try:
        r = http.request(method, path, headers=headers, **kw)
        status, text, rh = r.status_code, r.text, dict(r.headers)
    except httpx.HTTPError as e:
        status, text, rh = -1, f"{type(e).__name__}: {e}", {}
    time.sleep(1.5)  # a thread the route started may still be calling
    after = record()[before:]
    keys = [x["headers"].get("x-api-key") or x["headers"].get("X-Api-Key") for x in after]
    with open(f"{OUT}/{label}.response.txt", "w") as f:
        f.write(f"{status}\n{json.dumps(rh)}\n{text}")
    row = {"route": label, "status": status, "seconds": round(time.monotonic() - t0, 1),
           "modelRequests": len(after),
           "keysUsed": sorted({("SENTINEL" if k == SENTINEL else "ENVKEY" if k == ENVKEY else repr(k)) for k in keys}),
           "sentinelInResponse": SENTINEL in text or SENTINEL in json.dumps(rh),
           "answerHead": text[:300]}
    summary.append(row)
    print(json.dumps(row), flush=True)

stop.set()
time.sleep(1)
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
