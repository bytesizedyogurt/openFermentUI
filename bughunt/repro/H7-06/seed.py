"""H7-06: placeholder rows for each detail page the reproduction opens, kept through the service's own routes.

Every word here stands for nothing: the rows exist so each detail page has something to open with the service up.
Five pages under test (a runbook, a deposition, a paper, a Guild skill, a Postdoc conversation) and three controls
(a protocol, a strain, a lesson). No model call: the paper is pasted text, embedded by the local FastEmbed model.

    python3 seed.py <origin> <project>       prints one JSON object of the ids kept
"""
import json
import sys
import urllib.error
import urllib.request

ORIGIN, PROJECT = sys.argv[1], sys.argv[2]
BY = "H7-06 repro"
AT = "2026-11-10T00:00:00Z"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(method, path, body=None):
    req = urllib.request.Request(ORIGIN + path, method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-OpenFerment-Project": PROJECT})
    try:
        with opener.open(req, timeout=300) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def kept(label, answer):
    status, body = answer
    if status != 200:
        sys.exit(f"seed: {label} answered {status}: {body}")
    return body


ids = {}

# The pages under test.
ids["runbook"] = "rb-h706"
kept("runbook", api("PUT", f"/api/state/runbooks/{ids['runbook']}", {"by": BY, "value": {
    "id": ids["runbook"], "kind": "research", "title": "H7-06 placeholder runbook", "status": "draft"}}))

ids["deposition"] = "dep-h706"
kept("deposition", api("PUT", f"/api/state/depositions/{ids['deposition']}", {"by": BY, "value": {
    "id": ids["deposition"], "runbookId": ids["runbook"], "protocolId": None, "operatorId": None, "startedAt": AT,
    "closedAt": None, "state": "staged", "entries": [], "observations": [], "reconciliation": None}}))

ids["conversation"] = "lc-h706"
kept("conversation", api("PUT", f"/api/state/conversations/{ids['conversation']}", {"by": BY, "value": {
    "id": ids["conversation"], "title": "H7-06 placeholder conversation", "startedAt": AT,
    "turns": [{"id": "lt-h706", "question": "A placeholder question?", "askedAt": AT, "status": "stopped"}]}}))

ids["skill"] = "h706-skill"
kept("skill", api("POST", "/api/catalogues/skill", {"by": BY, "entry": {
    "kind": "skill", "id": ids["skill"], "name": "H7-06 placeholder skill", "family": "aseptic"}}))

outcome = kept("paper", api("POST", "/api/intake/paste", {
    "by": BY, "title": "H7-06 placeholder paper",
    "text": "A placeholder paragraph that stands for nothing. It exists so the paper reader has a document to open."}))
docs = kept("documents", api("GET", "/api/literature/documents"))
if len(docs) != 1:
    sys.exit(f"seed: the paste left {len(docs)} documents in the project ({outcome})")
ids["paper"] = docs[0]["documentId"]

# The controls: pages that read the same failed loads and say the service is not running.
ids["strain"] = "h706-strain"
kept("strain", api("POST", "/api/catalogues/strain", {"by": BY, "entry": {
    "kind": "strain", "id": ids["strain"], "name": "H7-06 placeholder strain"}}))

ids["lesson"] = "h706-lesson"
kept("lesson", api("POST", "/api/catalogues/lesson", {"by": BY, "entry": {
    "kind": "lesson", "id": ids["lesson"], "name": "H7-06 placeholder lesson", "minutes": 5,
    "blocks": [{"kind": "prose", "md": "A placeholder paragraph."}],
    "checkpoint": [{"id": "q1", "prompt": "A placeholder question?", "kind": "mc", "options": ["a", "b"],
                    "answerIndex": 0}]}}))

ids["protocol"] = "h706-protocol"
kept("protocol", api("POST", "/api/protocols", {"by": BY, "protocol": {
    "id": ids["protocol"], "title": "H7-06 placeholder protocol", "category": "culture", "bsl": 1,
    "currentVersion": "1",
    "versions": [{"version": "1", "baseBatch": {"value": 1, "unit": "L", "label": "placeholder batch"},
                  "estMinutes": {"active": 5, "total": 10}, "materials": [],
                  "steps": [{"id": "s1", "text": "A placeholder step."}]}]}}))

print(json.dumps(ids))
