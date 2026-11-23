"""H5's operation probe, generated from docs/api/openapi.json: every operation is sent from project bh-b
with project bh-a's ids in its path, query and body, and again with the project header missing, empty,
spaces, upper case, unicode, 200 characters, a path, an unknown project, and the header and ?project=
disagreeing. Each answer is checked for A's content (markers never sent in a request, and A's ids where
the request did not carry them) and for the contract's statuses. Before and after, A's rows are read
whole as A and compared, so a change made from B shows. Writes $H5_OUT/probe.jsonl and prints a summary.

    source bughunt/lib/env.sh; H5_ORIGIN=http://127.0.0.1:8850 bh_py bughunt/notes/H5/scripts/probe_ops.py
"""
import json
import re
import sys
import time

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import ORIGIN, OUT, call, j

SPEC = json.load(open("/home/user/openFermentUI/docs/api/openapi.json"))
A, B = "bh-a", "bh-b"
ids = json.load(open(f"{OUT}/a_ids.json"))
DOC = ids["paste"]["documentId"]
AT = "2026-11-10T08:00:00Z"
# Words that stand only in A's rows and never in a request this probe sends.
CONTENT = ["SECRETWORDA", "only A holds", "A's ", "alice", "SECRET-ALIAS-A", "Placeholder species A",
           "xylofermentans"]
IDS = [ids["state"]["depositions"], ids["state"]["trains"], ids["state"]["conversations"], ids["state"]["turn"],
       ids["protocol"], "SK-A", "strain-a", "product-a", "lesson-a", "e-aaaa1", ids["checks"][0], ids["runbook"],
       ids["run"], ids["run2"], ids["comparison"], ids["flowsheet"], ids["scenario"], ids["proposals"][0], DOC,
       ids["record"], ids["candidate"], "proforma:sc-a", "de-a1"]
# Words whose presence names A in a path like project A's row; "p-a" is short, so only as a JSON value.
ID_PATTERNS = [re.compile(re.escape(x)) for x in IDS] + [re.compile(r'"p-a"')]

PATH_VALUES = {
    "artifact_id": ids["run"], "check_id": ids["checks"][0], "comparison_id": ids["comparison"],
    "conversation_id": ids["state"]["conversations"], "entry_id": "strain-a", "family_id": "batch_v1",
    "file_id": "SF_BST_01", "item_id": None, "key": ids["state"]["trains"], "kind": None, "name": None,
    "paper_id": DOC, "plant": "cornstover", "project_id": A, "proposal_id": ids["proposals"][0],
    "protocol_id": ids["protocol"], "record_id": ids["flowsheet"], "run_id": ids["run"],
    "runbook_id": ids["runbook"], "scenario_id": ids["scenario"], "scope": "proforma", "turn_id": ids["state"]["turn"],
    "type_id": "centrifuge",
}
QUERY_VALUES = {
    "artifactId": ids["run"], "simulation": ids["run"], "fit": ids["run"], "flowsheet": ids["flowsheet"],
    "scenarioId": ids["scenario"], "trainRun": ids["run"], "vessel": ids["run"], "recordId": ids["record"],
    "q": "SECRETWORDA ethanol xylose", "strain": "strain-a", "product": "product-a", "host": "strain-a",
    "family": "batch_v1", "thing": "batch_v1", "tool": "fermos.simulation", "engine": "kinetics", "by": "bob",
    "target": None, "who": None, "action": None, "unit": "g/L", "train": ids["state"]["trains"],
}
# The path-parameter values an operation is tried with beyond the defaults.
SPECIAL = {
    ("/api/catalogues/{kind}", "kind"): "strain", ("/api/catalogues/{kind}/{entry_id}", "kind"): "strain",
    ("/api/engines/{name}/parameters", "name"): "kinetics", ("/api/engines/{name}/run", "name"): "kinetics",
    ("/api/tools/{name}", "name"): "literature_document",
}
STATE_KINDS = {"PUT": [("depositions", ids["state"]["depositions"]), ("trains", ids["state"]["trains"]),
                       ("conversations", ids["state"]["conversations"]), ("runbooks", ids["runbook"]),
                       ("scenarios", ids["scenario"])],
               "DELETE": [("trains", ids["state"]["trains"]), ("fits", ids["state"]["fits"]),
                          ("overrides", ids["state"]["overrides"]), ("runbooks", ids["runbook"]),
                          ("scenarios", ids["scenario"])]}

INPUT = {"name": "mu_max", "quantity": {"value": 0.3, "unit": "h⁻¹", "origin": {
    "kind": "measurement", "ref": f"{ids['state']['depositions']}/de-a1", "by": "bob", "at": AT}}}
BODIES = {
    "AskRequest": {"question": "What is in my documents?", "by": "bob", "conversationId": ids["state"]["conversations"],
                   "turnId": ids["state"]["turn"]},
    "BriefRequest": {"by": "bob"}, "CheckProposeRequest": {"by": "bob"},
    "CatalogueKeep": {"by": "bob", "entry": {"kind": "strain", "id": "strain-a", "name": "B's strain"}},
    "CeilingRequest": {"modelId": "iMM904", "product": "ethanol", "substrate": "glucose"},
    "CheckDismiss": {"by": "bob", "reason": "B dismisses"},
    "CheckRecord": {"at": AT, "by": "bob", "notes": [], "results": []},
    "CheckRequest": {"personId": "p-a", "skillIds": ["SK-A"], "by": "p-a"},
    "CheckSchedule": {"by": "bob", "scheduledFor": "2026-11-20"},
    "CollectRequest": {"by": "bob", "identifier": "PMC0000000", "reason": "probe"},
    "ComparisonCreate": {"title": "B compares A's runs", "runIds": [ids["run"], ids["run2"]], "by": "bob"},
    "EngineRunRequest": {"thing": "batch_v1", "by": "bob", "inputs": [INPUT]},
    "FermosFitRequest": {"depositionId": ids["state"]["depositions"], "series": ["m-a1"]},
    "ForecastRequest": {"by": "bob", "fitArtifactId": ids["run"]},
    "GuildEvidence": {"id": "e-aaaa1", "personId": "p-a", "skillId": "SK-A", "kind": "knowledge", "at": AT,
                      "source": {"kind": "lesson", "ref": "lesson-a"}, "raw": "B writes", "outcome": "pass"},
    "GuildPerson": {"id": "p-a", "name": "B's person", "joinedAt": AT, "addedAt": AT, "role": "lead"},
    "GuildPolicy": {"checksPerQuarter": 1, "criticalGate": "advise", "routineGate": "advise"},
    "GuildWithdrawal": {"at": AT, "by": "p-a", "evidenceId": "e-aaaa1", "reason": "B withdraws"},
    "LibraryRunRequest": {"by": "bob", "inputs": [{"name": "x", "quantity": INPUT["quantity"]}]},
    "LiteratureQuestion": {"question": "SECRETWORDA ethanol", "topK": 4},
    "MixRequest": {"a": "glucose", "b": "xylose", "modelId": "iMM904", "product": "ethanol"},
    "ParamResolveRequest": {"flowsheet": ids["flowsheet"], "fits": {"mu_max": ids["run"]}, "fit": ids["run"],
                            "vessel": ids["run"], "trainRun": ids["run"], "inputs": [INPUT]},
    "PasteRequest": {"title": "B paste", "text": "B's own document about yeast.", "by": "bob"},
    "PracticeDraftRequest": {"skillId": "SK-A", "depositions": [ids["state"]["depositions"]]},
    "PracticeRecordRequest": {"sessionId": "ps-a"},
    "PracticeTurnRequest": {"answer": "x", "scenarioId": "psc-a", "personId": "p-a"},
    "ProductPropertyRequest": {"product": "product-a"},
    "ProformaRunRequest": {"scenarioId": ids["scenario"], "by": "bob", "inputs": [INPUT], "samples": 1},
    "ProposalAction": {"person": "bob", "reason": "B acts on A's proposal"},
    "ProposeRequest": {"host": "strain-a", "product": "product-a", "inletRef": ids["run"]},
    "ProtocolKeep": {"by": "bob", "protocol": {"id": ids["protocol"], "title": "B's", "category": "sop", "bsl": 1,
                                               "currentVersion": "1.0", "versions": [{
                                                   "version": "1.0", "baseBatch": {"value": 1, "unit": "u", "label": "b"},
                                                   "steps": [{"id": "s1", "text": "x", "skills": ["SK-A"]}],
                                                   "estMinutes": {"active": 1, "total": 1}}]}},
    "ProtocolVersionKeep": {"by": "bob", "version": {"version": "9.0", "baseBatch": {"value": 1, "unit": "u", "label": "b"},
                                                     "steps": [{"id": "s1", "text": "x", "skills": []}],
                                                     "estMinutes": {"active": 1, "total": 1}}},
    "ReviewDecision": {"status": "rejected", "provenance": "unverified", "recordId": ids["record"], "at": AT,
                       "reviewer": "bob", "rejectReason": "B rejects A's record"},
    "RunbookCreate": {"title": "B's runbook", "runId": ids["run"], "by": "bob",
                      "predict": [{"label": "t", "output": "values.end.P"}]},
    "SFFExportRequest": {"artifactId": ids["run"], "by": "bob"},
    "SFFLibraryImport": {"by": "bob"},
    "SFFUrlImport": {"by": "bob", "url": "http://127.0.0.1:8850/api/flowsheets/" + ids["flowsheet"] + "/file"},
    "ScenarioCreate": {"title": "B's", "plant": "cornstover", "by": "bob", "values": []},
    "SimulationRequest": {"family": "batch_v1", "by": "bob", "fitArtifact": ids["run"], "strain": "strain-a",
                          "product": "product-a", "inputs": [INPUT]},
    "StateWrite": None,  # by kind below
    "StudyRequest": {"by": "bob"},
    "ThermoPropsRequest": {"artifactId": ids["run"], "recordId": ids["record"]},
    "TrainFromRunRequest": {"artifactId": ids["run"], "trainId": ids["state"]["trains"]},
    "TrainRunRequest": {"by": "bob", "train": {"id": ids["state"]["trains"], "name": "x", "program": "p",
                                               "product": "product-a", "inlet": {"kind": "run", "ref": ids["run"]},
                                               "units": []}},
    "TrainSpec": {"id": ids["state"]["trains"], "name": "x", "program": "p", "product": "product-a",
                  "inlet": {"kind": "run", "ref": ids["run"]}, "units": []},
    "VesselRequest": {"by": "bob", "fit": ids["run"], "simulation": ids["run"], "inputs": [INPUT]},
    "ProjectCreate": {"id": "bh-a", "name": "B takes A's id", "by": "bob"},
    "inline": {"document": DOC},
}
STATE_VALUES = {
    "depositions": {"id": ids["state"]["depositions"], "runbookId": "rb-b", "protocolId": None, "operatorId": None,
                    "startedAt": AT, "closedAt": None, "state": "running", "entries": [], "observations": [],
                    "reconciliation": None},
    "trains": {"train": {"id": ids["state"]["trains"], "name": "B's train", "program": "p", "product": "x",
                         "inlet": {"kind": "typed"}, "units": []}, "savedAt": AT, "by": "bob"},
    "conversations": {"id": ids["state"]["conversations"], "title": "B's", "startedAt": AT,
                      "turns": [{"id": ids["state"]["turn"], "question": "B's", "askedAt": AT, "steps": [],
                                 "plan": None, "error": None, "status": "answered"}]},
    "runbooks": None, "scenarios": None,
}
HEAVY = {("POST", "/api/library/{plant}/run"), ("POST", "/api/proforma/run"), ("POST", "/api/pureos/train/run"),
         ("POST", "/api/studies/scenarios/{scenario_id}/run"), ("POST", "/api/ask"), ("POST", "/api/ask/stream"),
         ("POST", "/api/geneos/ceiling"), ("POST", "/api/geneos/frontier"), ("POST", "/api/geneos/mix"),
         ("POST", "/api/studies/scenarios"), ("POST", "/api/pureos/train/check")}
VARIANTS = {
    "none": None, "empty": "", "spaces": "   ", "upper": "BH-A", "unicode": "bh‑a", "long": "a" * 200,
    "path": "../bh-a", "unknown": "bh-zzz", "newline": "bh-a\tbh-b",
}


def requests_for(path, method, op):
    """Each request this operation is tried with from B: (path, params, json, files)."""
    pnames = [p["name"] for p in op.get("parameters", []) if p["in"] == "path"]
    qnames = [p["name"] for p in op.get("parameters", []) if p["in"] == "query" and p["name"] != "project"]
    params = {q: QUERY_VALUES[q] for q in qnames if QUERY_VALUES.get(q)}
    body = None
    files = None
    for ct, v in op.get("requestBody", {}).get("content", {}).items():
        name = v["schema"].get("$ref", "inline").split("/")[-1]
        if ct.startswith("multipart"):
            files = {"file": ("b.json", b'{"sff_version": "0.2.4"}', "application/json")}
        else:
            body = BODIES.get(name, {})
    out = []
    if path.startswith("/api/state/") and method in STATE_KINDS:
        for kind, item in STATE_KINDS[method]:
            p = path.replace("{kind}", kind).replace("{item_id}", item)
            b = None
            if method == "PUT":
                b = {"by": "bob", "value": STATE_VALUES.get(kind) or {"id": item}}
            out.append((p, {"by": "bob"} if method == "DELETE" else {}, b, None))
        return out
    p = path
    for n in pnames:
        val = SPECIAL.get((path, n)) or PATH_VALUES.get(n) or "x"
        p = p.replace("{" + n + "}", val)
    out.append((p, params, body, files))
    if path == "/api/tools/{name}":
        for tool, args in (("get_artifact", {"id": ids["run"]}), ("engine_report", {"run": ids["run"]}),
                           ("flowsheet_read", {"record": ids["flowsheet"]}), ("study_read", {}),
                           ("catalogue_read", {"kind": "strain"}), ("search_records", {"query": "ethanol", "field": None,
                                                                                         "organism": None, "limit": 10}),
                           ("search_passages", {"query": "SECRETWORDA", "k": 6}), ("literature_sources", {}),
                           ("convert_units", {"recordId": ids["record"], "toUnit": "kg/m3"}),
                           ("biorepo_read", {}), ("guild_read", {}), ("home_read", {}), ("runbooks_read", {}),
                           ("intake_read", {}), ("primer_read", {}), ("fermos_read", {}), ("pureos_read", {}),
                           ("proforma_read", {}), ("geneos_read", {})):
            out.append((f"/api/tools/{tool}", {"by": "bob"}, args, None))
    return out


def leaked(text, sent):
    found = [w for w in CONTENT if w in text and w not in sent]
    found += [p.pattern for p in ID_PATTERNS if p.search(text) and not p.search(sent)]
    return found


def send(method, p, params, body, files, header=..., query=None):
    """One request through http.client, which sends a header value as given (spaces, tabs, unicode)."""
    import http.client
    import urllib.parse
    h = {}
    if header is not ...:
        if header is not None:
            h["X-OpenFerment-Project"] = header
    pr = dict(params or {})
    if query is not None:
        pr["project"] = query
    url = urllib.parse.quote(p, safe="/:@-._~!$&'()*+,;=") + ("?" + urllib.parse.urlencode(pr) if pr else "")
    data = None
    if files:
        boundary = "bhh5boundary"
        name, content, ctype = files["file"]
        data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"by\"\r\n\r\nbob\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        h["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    t0 = time.time()
    conn = http.client.HTTPConnection("127.0.0.1", int(ORIGIN.rsplit(":", 1)[1]), timeout=600)
    enc = {k: v.encode("utf-8") if isinstance(v, str) else v for k, v in h.items()}
    conn.putrequest(method, url, skip_accept_encoding=True)
    for k, v in enc.items():
        conn.putheader(k, v)
    if data is not None:
        conn.putheader("Content-Length", str(len(data)))
    conn.endheaders(data)
    stream = p == "/api/events" or p.endswith("/stream") or p == "/api/literature/answer"
    if stream:
        conn.sock.settimeout(3)
    r = conn.getresponse()
    status = r.status
    if stream and status == 200:
        text = b""
        start = time.time()
        try:
            while time.time() - start < 2 and len(text) < 20000:
                chunk = r.read1(4096)
                if not chunk:
                    break
                text += chunk
        except Exception as e:
            text += f" [{type(e).__name__}]".encode()
    else:
        text = r.read()
    conn.close()
    return status, text.decode("utf-8", "replace"), time.time() - t0


SNAP = ["/api/state", "/api/catalogues/strain", "/api/catalogues/skill", "/api/catalogues/product",
        "/api/catalogues/lesson", "/api/protocols", "/api/guild", "/api/guild/checks", "/api/proposals",
        "/api/runs", "/api/biorepo/artifacts", "/api/studies/scenarios", "/api/studies/comparisons",
        "/api/studies/runbooks", "/api/flowsheets", "/api/conversations", "/api/literature/documents",
        "/api/biorepo/overlay", "/api/practice"]


def snapshot():
    out = {}
    for p in SNAP:
        r = call("GET", p, A)
        out[p] = r.text
    out["audit"] = call("GET", "/api/audit", A, params={"limit": 500}).text
    return out


def main():
    before = snapshot()
    rows = []
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "delete"):
                continue
            M = method.upper()
            scope = op.get("x-openferment-scope")
            for p, params, body, files in requests_for(path, M, op):
                if (M, path) in HEAVY and scope == "project":
                    variants = [("B", B)]
                else:
                    variants = [("B", B)] + list(VARIANTS.items())
                if scope == "none":
                    variants = [("B", B), ("none", None)]
                for vname, header in variants:
                    sent = json.dumps([p, params, body]) + (header or "")
                    status, text, secs = send(M, p, params, body, files, header=header)
                    row = {"op": f"{M} {path}", "path": p, "variant": vname, "status": status,
                           "leak": leaked(text, sent), "secs": round(secs, 2), "answer": text[:300]}
                    rows.append(row)
                    print(json.dumps(row, ensure_ascii=False)[:400])
                    sys.stdout.flush()
                if scope == "project":
                    # The header names B and ?project= names A: the request must act in B.
                    sent = json.dumps([p, params, body])
                    if (M, path) not in HEAVY:
                        status, text, secs = send(M, p, params, body, files, header=B, query=A)
                        rows.append({"op": f"{M} {path}", "path": p, "variant": "header-B-query-A", "status": status,
                                     "leak": leaked(text, sent + A), "secs": round(secs, 2), "answer": text[:300]})
    after = snapshot()
    changed = {k: (before[k][:2000], after[k][:2000]) for k in before if before[k] != after[k]}
    with open(f"{OUT}/probe.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(changed, open(f"{OUT}/probe_changed.json", "w"), indent=1, ensure_ascii=False)
    print("CHANGED IN A:", list(changed))
    print("LEAKS:", [(r["op"], r["path"], r["variant"], r["leak"]) for r in rows if r["leak"]])


if __name__ == "__main__":
    main()
