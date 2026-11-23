"""H9-01: which key the kit's cited answer carries to the model API when the request names its own.

    bh_py drive.py ORIGIN PROJECT SENTINEL ENVKEY STANDIN_RECORD RAG_KEY OUT_JSON

Two requests, each naming SENTINEL in X-OpenFerment-Key: the subject, POST /api/literature/answer,
then a control on the same kit answer through its other door, POST /rag/v1/answer. For each, the
stand-in's record before and after ties every model request to the route that made it and says
which key it carried (x-api-key). Then the project's key_override audit rows.
"""
from __future__ import annotations

import json
import sys
import time

import httpx

ORIGIN, PROJECT, SENTINEL, ENVKEY, RECORD, RAG_KEY, OUT = sys.argv[1:8]
K = {"X-OpenFerment-Project": PROJECT, "X-OpenFerment-Key": SENTINEL}
http = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=httpx.Timeout(120.0, connect=10.0))


def record() -> list[dict]:
    try:
        with open(RECORD, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def name(k: str | None) -> str:
    return "SENTINEL" if k == SENTINEL else "ENVKEY" if k == ENVKEY else repr(k)


def ask(label: str, path: str, body: dict, extra: dict | None = None) -> dict:
    before = len(record())
    r = http.post(path, headers={**K, **(extra or {})}, json=body)
    time.sleep(1.5)  # a thread the route started may still be calling
    sent = record()[before:]
    events = [line.split(":", 1)[1].strip() for line in r.text.splitlines() if line.startswith("event:")]
    row = {"route": label, "status": r.status_code, "events": events,
           "modelRequests": len(sent),
           "keysUsed": [name(x["headers"].get("x-api-key") or x["headers"].get("X-Api-Key")) for x in sent],
           "sentinelInResponse": SENTINEL in r.text}
    print(f"## {label}: {json.dumps(row)}", flush=True)
    return row


subject = ask("POST /api/literature/answer", "/api/literature/answer",
              {"question": "What does the yeast ferment?"})
control = ask("POST /rag/v1/answer (control: the kit's answer through its REST door)", "/rag/v1/answer",
              {"query": "What does the yeast ferment?"}, {"Authorization": f"Bearer {RAG_KEY}"})

audit = http.get("/api/audit", params={"action": "key_override"},
                 headers={"X-OpenFerment-Project": PROJECT}).json()
rows = [{"target": a.get("target"), "detail": a.get("detail")} for a in audit]
print(f"## GET /api/audit?action=key_override: {json.dumps(rows)}", flush=True)
audited = any(a.get("target") == "POST /api/literature/answer" and (a.get("detail") or {}).get("override")
              for a in audit)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"subject": subject, "control": control, "audited": audited}, f)
