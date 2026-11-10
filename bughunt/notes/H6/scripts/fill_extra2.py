"""fill_extra2.py ORIGIN PROJECT DATA_DIR: the second pass of fill_extra.py, the requests its first pass sent
in a shape alpha 2.1 refused, sent again in the shape alpha 2.1's own words named: Guild's first person
(added by nobody), its lead's policy, evidence and a check; the deposition's series fitted (each point with
its entry), a forecast; a batch simulation on a person's assumptions; Proforma runs on ethanol_glucose_v0
with every waiting value a person's assumption (through `overrides`, and through the older `assumptions`);
a train read from that run, run and saved; the run's stream properties and SFF export; a Live conversation.
Appends to DATA_DIR/extra.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

origin, project, data_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
PERSON = "Ada Moreno"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
DAY = NOW[:10]
c = httpx.Client(base_url=origin, trust_env=False, timeout=1800, headers={"X-OpenFerment-Project": project})
kept = json.loads((data_dir / "extra.json").read_text())
made, log = kept["made"], kept["log"]


def call(name: str, method: str, path: str, body: Any = None, **kw: Any) -> Any:
    t0 = time.monotonic()
    r = c.request(method, path, json=body, **kw)
    try:
        out = r.json()
    except ValueError:
        out = r.text[:300]
    ok = 200 <= r.status_code < 300
    print(f"{'ok ' if ok else 'NO '} {r.status_code} {name} {method} {path} ({time.monotonic() - t0:.1f}s)"
          + ("" if ok else f": {str(out)[:500]}"), flush=True)
    log.append({"name": name, "method": method, "path": path, "status": r.status_code,
                "detail": None if ok else str(out)[:600]})
    return out if ok else None


def state(kind: str, item_id: str, value: Any) -> Any:
    return call(f"state {kind}", "PUT", f"/api/state/{kind}/{item_id}", {"by": PERSON, "value": value})


# Guild
call("guild person", "POST", "/api/guild/people", {"id": "p-ada", "name": PERSON, "role": "lead",
                                                   "title": "Process engineer", "joinedAt": DAY, "active": True,
                                                   "addedBy": None, "addedAt": NOW})
call("guild person 2", "POST", "/api/guild/people", {"id": "p-ben", "name": "Ben Ortiz", "role": "member",
                                                     "title": "Technician", "joinedAt": DAY, "active": True,
                                                     "addedBy": "p-ada", "addedAt": NOW})
call("guild policy", "POST", "/api/guild/policy", {"routineGate": "advise", "criticalGate": "enforce",
                                                    "checksPerQuarter": 2, "updatedBy": "p-ada", "updatedAt": NOW})
call("guild evidence", "POST", "/api/guild/evidence", {
    "id": "ev-1", "personId": "p-ben", "skillId": "aseptic-sampling", "kind": "witnessed", "outcome": "pass",
    "at": NOW, "observerId": "p-ada", "source": {"kind": "signoff", "ref": "proto-batch", "stepId": "s-sample"},
    "raw": "took three clean samples", "recordedAt": NOW})
chk = call("guild check request", "POST", "/api/guild/checks/request",
           {"personId": "p-ben", "skillIds": ["aseptic-sampling"], "by": "p-ada"})
if chk:
    made["check"] = chk.get("id")
    call("guild check schedule", "POST", f"/api/guild/checks/{chk['id']}/schedule", {"by": "p-ada",
                                                                                    "scheduledFor": DAY})

# fermOS: the deposition's series, each point with its entry id (as the bench's seriesOf makes them)
dep = next(d for d in c.get("/api/state").json()["depositions"] if d["id"] == "dep-h6-1")
times = dep["sampleTimes"]
series = []
for mid, lab, role in (("m-x", "Biomass", "biomass"), ("m-p", "Ethanol", "product"), ("m-s", "Glucose", "substrate")):
    pts = [{"t": times[e["id"]], "value": e["value"], "entryId": e["id"], "confirmed": True}
           for e in dep["entries"] if e["measureId"] == mid]
    series.append({"measureId": mid, "label": lab, "unit": "g/L", "role": role, "points": pts})
fit = call("fermos fit", "POST", "/api/fermos/fit", {"depositionId": dep["id"], "series": series})
if fit:
    print("fit keys:", {k: (type(v).__name__, (v or {}).get("id") if isinstance(v, dict) else None) for k, v in fit.items()})
    ids = {k: v.get("id") for k, v in fit.items() if isinstance(v, dict) and v.get("id")}
    made["fit"] = ids
    fid = next(iter(ids.values()), None)
    if fid:
        fc = call("fermos forecast", "POST", "/api/fermos/forecast", {"fitArtifactId": ids.get("growth", fid)})
        if fc is None and len(ids) > 1:
            for k, v in ids.items():
                fc = call(f"fermos forecast ({k})", "POST", "/api/fermos/forecast", {"fitArtifactId": v})
                if fc:
                    break
        made["forecast"] = (fc or {}).get("artifact", {}).get("id") if isinstance((fc or {}).get("artifact"), dict) else None
vals = {"mu_max": 0.3, "ks": 0.5, "kd": 0.0, "yxs": 0.1, "alpha": 2.0, "beta": 0.1, "yps": 0.45, "maintenance": 0.0,
        "p_max": 100.0, "n_inhibition": 1.0, "ki_substrate": 200.0, "yxo": 1.0, "mo": 0.0, "x0": 0.5, "s0": 100.0,
        "p0": 0.0, "v0": 1.0, "t_end": 48.0}
sim = call("fermos simulate", "POST", "/api/fermos/simulate", {"family": "batch_v1", "overrides": [
    {"scope": "fermos:family:batch_v1", "key": k, "value": v, "by": PERSON, "at": DAY, "origin": "person-assumption"}
    for k, v in vals.items()]})
if sim:
    print("sim keys:", list(sim)[:12])
    made["simulation"] = (sim.get("artifact") or {}).get("id") if isinstance(sim.get("artifact"), dict) else sim.get("id")
    if made["simulation"]:
        v = call("fermos vessel", "POST", "/api/fermos/vessel", {"simulation": made["simulation"],
                                                                 "vesselType": "stirred-tank"})
        made["vessel"] = (v or {}).get("artifactId") or (v or {}).get("id")

# Proforma on ethanol_glucose_v0, every waiting value a person's assumption
sid = "sc-h6-glucose"
asm = {"feed_glucose_conc": 200.0, "titre": 90.0, "yield": 0.45, "productivity": 2.0, "plant_scale": 100000.0,
       "glucose_price": 0.4}
ov = [{"scope": f"proforma:{sid}", "key": k, "value": v, "by": PERSON, "at": DAY, "origin": "person-assumption",
       "note": "the hunt's assumption"} for k, v in asm.items()]
state("overrides", f"proforma:{sid}", ov)
run = call("proforma run", "POST", "/api/proforma/run", {"scenarioId": sid, "flowsheet": "ethanol_glucose_v0",
                                                         "overrides": ov, "samples": 20})
prun = ((run or {}).get("artifact") or {}).get("id")
made["proformaRun"] = prun
print("run keys:", list(run or {}))
run2 = call("proforma run (assumptions)", "POST", "/api/proforma/run", {
    "scenarioId": sid, "flowsheet": "ethanol_glucose_v0", "samples": 20,
    "assumptions": [{"key": k, "value": v, "low": v * 0.9, "high": v * 1.1, "by": PERSON, "at": DAY}
                    for k, v in asm.items()]})
made["proformaRunAssumptions"] = ((run2 or {}).get("artifact") or {}).get("id")
est = [{**o, "origin": "model-estimate", "by": "claude-opus-5-5", "at": NOW} if o["key"] == "titre" else o for o in ov]
run3 = call("proforma run (an estimate)", "POST", "/api/proforma/run", {"scenarioId": sid,
                                                                        "flowsheet": "ethanol_glucose_v0",
                                                                        "overrides": est, "samples": 20})
made["proformaRunEstimate"] = ((run3 or {}).get("artifact") or {}).get("id")
if prun:
    sc = next(s for s in c.get("/api/state").json()["scenarios"] if s["id"] == sid)
    state("scenarios", sid, {**sc, "lastRunId": prun})
    tr = call("pureos from-run", "POST", "/api/pureos/train/from-run", {"artifactId": prun, "trainId": "tr-h6"})
    train = (tr or {}).get("train")
    print("from-run keys:", list(tr or {}))
    if train:
        state("trains", train["id"], {"train": train, "savedAt": NOW, "by": PERSON})
        made["trainMade"] = train["id"]
        trun = call("pureos train run", "POST", "/api/pureos/train/run", {"train": train, "by": PERSON})
        print("train run keys:", list(trun or {}))
        made["trainRun"] = ((trun or {}).get("artifact") or {}).get("id")
    streams = [s.get("id") for s in ((run or {}).get("artifact") or {}).get("output", {}).get("streams", [])][:3]
    if streams:
        p = call("thermo props", "POST", "/api/thermo/props", {"artifactId": prun, "streamId": streams[0]})
        made["thermo"] = (p or {}).get("id")
    exp = call("flowsheet export", "POST", "/api/flowsheets/export", {"artifactId": prun, "by": PERSON})
    made["sffExport"] = (exp or {}).get("id")
bench = made.get("benchmark")
if bench:
    call("pureos from-run (benchmark)", "POST", "/api/pureos/train/from-run", {"artifactId": bench})

# A Live conversation a page wrote: its failed turn with the words and the remedy
live = {"id": "lc-page-1", "title": "What limits the titre?", "startedAt": NOW,
        "turns": [{"id": "t-page-1", "question": "What limits the titre?", "askedAt": NOW, "steps": [], "plan": None,
                   "error": {"message": "the page lost its connection", "remedy": "ask again"}, "status": "error"}]}
if state("conversations", live["id"], live) is None:
    live["turns"][0]["status"] = "failed"
    state("conversations", live["id"], live)
made["live"] = live["id"]

(data_dir / "extra.json").write_text(json.dumps({"made": made, "log": log}, indent=1, default=str))
print(json.dumps(made, default=str)[:2000])
