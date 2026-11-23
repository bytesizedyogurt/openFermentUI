"""Writes bughunt/notes/H10/coverage.jsonl from what H10 ran (see notes.md)."""
import csv
import json
import re

ROOT = "/home/user/openFermentUI"
rows = list(csv.DictReader(open(f"{ROOT}/bughunt/coverage.csv")))
spec = json.load(open(f"{ROOT}/docs/api/openapi.json"))
mine = [r for r in rows if "H10" in r["assigned"].split()]
known = {(r["kind"], r["item"]) for r in rows}

NUL500 = {"GET /api/projects/{project_id}", "GET /api/runs/{run_id}", "GET /api/flowsheets/{record_id}",
          "GET /api/flowsheets/{record_id}/file", "GET /api/protocols/{protocol_id}",
          "GET /api/conversations/{conversation_id}", "GET /api/conversations/{conversation_id}/turns/{turn_id}/calls",
          "GET /api/studies/scenarios/{scenario_id}", "GET /api/studies/comparisons/{comparison_id}",
          "POST /api/studies/scenarios/{scenario_id}/run", "GET /api/audit", "GET /api/runs",
          "GET /api/biorepo/artifacts", "GET /api/proposals", "POST /api/projects", "POST /api/practice/record"}
REBIND = {"GET /api/guild", "GET /api/audit", "GET /api/state", "GET /api/conversations", "GET /api/studies/export",
          "GET /api/biorepo/overlay", "GET /api/literature/documents"}
SKIPPED_PATHS = {"/api/intake/{paper_id}/extract", "/api/guild/checks/{check_id}/brief"}
REACHES_OUT = {"/api/ask", "/api/ask/stream", "/api/literature/answer", "/api/intake/{paper_id}/extract",
               "/api/intake/collect", "/api/flowsheets/import-url", "/api/flowsheets/library/{file_id}",
               "/api/guild/checks/{check_id}/brief", "/api/guild/checks/propose", "/api/pureos/propose",
               "/api/practice/turn", "/api/practice/draft", "/api/tools/{name}"}
EXECUTED_POSTS = {
    "POST /api/biorepo/check": "the guard matrix (30 header shapes, 7 methods), the cross-site page, 64 MB, deep and million-key bodies, the key-override sentinel",
    "POST /api/projects": "the cross-site page's fetch, form and beacon (each 403), NUL in name, by and description",
    "POST /api/guild/people": "a person kept and read back; a NUL name",
    "POST /api/tools/{name}": "the cross-site page's no-cors POST (403); path sweep; key sentinel on an unknown tool",
    "POST /api/catalogues/{kind}": "path sweep; a NUL name kept (json body column takes it)",
    "POST /api/flowsheets/import": "malformed SFF files, a traversal filename, a file naming another project in its metadata",
    "POST /api/intake/paste": "a NUL title and text; a pasted document for the /rag manifest",
}

out = []
ops = {}
for path, item in spec["paths"].items():
    for m, op in item.items():
        if m in ("get", "post", "put", "delete", "patch"):
            ops[f"{m.upper()} {path}"] = path


def line(kind, item, method, findings=(), note=""):
    d = {"kind": kind, "item": item, "method": method, "findings": list(findings)}
    if note:
        d["note"] = note
    out.append(d)


for key, path in ops.items():
    m = key.split()[0]
    f = []
    if key in NUL500:
        f.append("H10-02")
    if "{" in path and path not in SKIPPED_PATHS and m == "GET":
        line("operation", key, "fuzzed", f, "path_sweep.py: 17 values in each path parameter (traversal, %2e%2e, double "
             "encoding, backslash, absolute, NUL, 20000 characters, SQL, format strings); no traversal answer, no leak"
             + ("; NUL answers 500" if "H10-02" in f else ""))
    elif m == "GET" and path != "/api/events":
        line("operation", key, "executed", f, "get_sweep.py with ?project= (row counts of every table unchanged)"
              + ("; nul_probe.py" if "H10-02" in f else ""))
    elif key == "GET /api/events":
        line("operation", key, "executed", f, "after=NUL answers 422 in words; the stream opens like any GET")
    elif key in EXECUTED_POSTS:
        line("operation", key, "fuzzed", f, EXECUTED_POSTS[key] + "; body_sweep.py")
    elif m in ("POST", "PUT", "DELETE"):
        line("operation", key, "fuzzed", f, "body_sweep.py: broken JSON, a list, a string, wrong types"
             + (", an empty object and every string a NUL" if path not in REACHES_OUT else
                " (a valid body left: the route reaches a model or the network)")
             + ("; path_sweep.py on its path parameters" if "{" in path and path not in SKIPPED_PATHS else "")
             + ("; the NUL body answers 500" if "H10-02" in f else ""))

FILES = {
    "core/openferment_core/api.py": ("fuzzed", ["H10-02"], "read in full for middleware, handlers, the /rag mount and the dist mount; every route fuzzed"),
    "core/openferment_core/guard.py": ("executed", ["H10-05"], "read; guard_matrix.py over raw HTTP and cross_site.mjs in Chromium"),
    "core/openferment_core/ready.py": ("executed", ["H10-03"], "the rag row run with OPENFERMENT_RAG_KEY unset"),
    "core/openferment_core/literature/kit.py": ("executed", ["H10-03"], "the /rag key map, settings and rest_app read; /rag probed with the key set, wrong, empty and unset"),
    "scripts/host/launchd.py": ("read", [], "the plist's --host defaults to 127.0.0.1; poll_host; nothing widens the bind without OPENFERMENT_HOST"),
    "scripts/prototype-up.sh": ("executed", [], "both servers bind 127.0.0.1; its static and decode logic run as serve_dist_probe.mjs (no file outside dist/); the whole script left: it writes core/.env"),
    "scripts/prove.py": ("read", [], "HOST 127.0.0.1 for the service and its port probe"),
    "package.json": ("read", [], "every start (dev, prototype:up, prove, smoke) binds loopback"),
    "core/openferment_core/audit.py": ("read", ["H10-02"], "audit.read's filters bind; a NUL filter reaches the text column and answers 500"),
    "core/openferment_core/catalogues.py": ("executed", [], "routes fuzzed; a NUL name keeps (json body)"),
    "core/openferment_core/guild.py": ("executed", [], "a person kept through POST /api/guild/people and read back"),
    "core/openferment_core/project_state.py": ("executed", [], "GET /api/state read; PUT and DELETE path-fuzzed"),
    "core/openferment_core/protocols.py": ("fuzzed", ["H10-02"], "GET /api/protocols/{id} with NUL answers 500"),
    "core/openferment_core/practice.py": ("fuzzed", ["H10-02"], "POST /api/practice/record with a NUL sessionId answers 500"),
}
for r in mine:
    if r["kind"] != "file":
        continue
    if r["item"] in FILES:
        m, f, n = FILES[r["item"]]
        line("file", r["item"], m, f, n)
    else:
        line("file", r["item"], "left", [], "module logic is H5's half of this assignment; H10 reached it only through "
             "its routes in path_sweep.py and get_sweep.py, which found nothing in it")
for item in ("core/openferment_core/literature/kit.py", "scripts/host/launchd.py", "scripts/prototype-up.sh",
             "scripts/prove.py", "package.json"):
    if ("file", item) in known and not any(d["item"] == item for d in out):
        m, f, n = FILES[item]
        line("file", item, m, f, n)

unknown = [d for d in out if (d["kind"], d["item"]) not in known]
assert not unknown, unknown
missing = [r["item"] for r in mine if not any(d["item"] == r["item"] for d in out)]
assert not missing, missing
with open(f"{ROOT}/bughunt/notes/H10/coverage.jsonl", "w") as fh:
    for d in out:
        fh.write(json.dumps(d) + "\n")
print(len(out), "lines;", sum(1 for d in out if d["method"] == "left"), "left")
