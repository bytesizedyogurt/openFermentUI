"""Seed placeholder rows into a hunt copy of the development database through the API (H7).

Every word and number here stands for nothing: the rows exist so the client's detail pages
(a runbook, a protocol, a strain, a lesson, a skill, a Guild person) have something to open.

    python3 seed_full.py http://127.0.0.1:8871 ethanol <run id>
"""
import json
import sys
import urllib.request

ORIGIN, PROJECT, RUN = sys.argv[1], sys.argv[2], sys.argv[3]
BY = "H7 Hunter"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(method, path, body=None):
    req = urllib.request.Request(ORIGIN + path, method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-OpenFerment-Project": PROJECT})
    try:
        with opener.open(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def show(label, answer):
    status, body = answer
    print(label, status, (json.dumps(body) if not isinstance(body, str) else body)[:200])
    return body


book = show("runbook", api("POST", "/api/studies/runbooks", {
    "title": "H7 placeholder runbook", "runId": RUN, "by": BY,
    "predict": [{"output": "outputs.mespUsdPerKg", "label": "A placeholder output"}]}))
if isinstance(book, dict):
    show("lock", api("POST", f"/api/studies/runbooks/{book['id']}/lock", {"by": BY}))
    print("RUNBOOK", book["id"])

show("strain", api("POST", "/api/catalogues/strain", {"by": BY, "entry": {
    "kind": "strain", "id": "h7-strain", "name": "H7 placeholder strain", "aliases": ["H7-A"]}}))
show("product", api("POST", "/api/catalogues/product", {"by": BY, "entry": {
    "kind": "product", "id": "h7-product", "name": "H7 placeholder product"}}))
show("skill", api("POST", "/api/catalogues/skill", {"by": BY, "entry": {
    "kind": "skill", "id": "h7-skill", "name": "H7 placeholder skill", "family": "aseptic",
    "criticality": "critical", "recencyDays": 90, "supervisedRuns": 2}}))
show("lesson", api("POST", "/api/catalogues/lesson", {"by": BY, "entry": {
    "kind": "lesson", "id": "h7-lesson", "name": "H7 placeholder lesson", "minutes": 5, "skills": ["h7-skill"],
    "blocks": [{"kind": "prose", "md": "A placeholder paragraph."}],
    "checkpoint": [{"id": "q1", "prompt": "A placeholder question?", "kind": "mc", "options": ["a", "b"], "answerIndex": 0}]}}))
show("protocol", api("POST", "/api/protocols", {"by": BY, "protocol": {
    "id": "h7-protocol", "title": "H7 placeholder protocol", "category": "culture", "bsl": 1, "currentVersion": "1",
    "versions": [{"version": "1", "baseBatch": {"value": 1, "unit": "L", "label": "placeholder batch"},
                  "estMinutes": {"active": 5, "total": 10},
                  "materials": [{"name": "placeholder material", "amount": 1, "unit": "g", "scaling": "per_batch_volume", "precision": 0.1}],
                  "steps": [{"id": "s1", "text": "A placeholder first step.", "skills": ["h7-skill"]},
                            {"id": "s2", "text": "A placeholder timed step.", "timerSec": 30, "timerLabel": "placeholder wait"},
                            {"id": "s3", "text": "A placeholder last step."}]}]}}))
show("person", api("POST", "/api/guild/people", {
    "id": "h7-person", "name": "H7 Hunter", "role": "lead", "joinedAt": "2026-11-01", "addedAt": "2026-11-10T00:00:00Z", "addedBy": BY}))
