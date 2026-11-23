"""fill_extra3.py ORIGIN PROJECT DATA_DIR: the third pass, reading back the ids the second pass's answers held
under other names (`growthArtifactId`, `kineticArtifactId`, `artifactId`) and asking what stands on them: a
forecast of the fit, a vessel design of the simulation, a train read from the Proforma run, its run and its
save in the Builder, the run's stream properties, its SFF export; Guild's evidence under an entry id and a
check asked by the person it is for. Appends to DATA_DIR/extra.json.
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


fits = c.get("/api/fermos/fits").json()
print("fits:", json.dumps(fits)[:300])
sims = c.get("/api/fermos/simulations").json()
made["simulation"] = sims[0]["artifactId"] if sims and "artifactId" in sims[0] else (sims[0].get("id") if sims else None)
print("simulation:", made["simulation"], list(sims[0]) if sims else None)
growth = fits[0].get("growthArtifactId") if isinstance(fits, list) and fits else None
if isinstance(fits, list) and fits:
    made["fit"] = {k: v for k, v in fits[0].items() if k.endswith("ArtifactId") or k == "id"}
for fid in [v for v in (made.get("fit") or {}).values() if isinstance(v, str)]:
    fc = call("fermos forecast", "POST", "/api/fermos/forecast", {"fitArtifactId": fid})
    if fc:
        made["forecast"] = fc.get("artifactId") or (fc.get("artifact") or {}).get("id")
        print("forecast keys:", list(fc)[:10])
        break
if made.get("simulation"):
    v = call("fermos vessel", "POST", "/api/fermos/vessel", {"simulation": made["simulation"], "vesselType": "stirred-tank"})
    made["vessel"] = (v or {}).get("artifactId") or (v or {}).get("id")
    print("vessel keys:", list(v or {})[:12])

sid = "sc-h6-glucose"
latest = c.get("/api/proforma/runs", params={"scenarioId": sid}).json().get("artifact") or {}
prun = latest.get("id")
made["proformaRun"] = prun
arts = c.get("/api/biorepo/artifacts").json()
arts = arts if isinstance(arts, list) else arts.get("artifacts", [])
made["artifactsByTool"] = {}
for a in arts:
    made["artifactsByTool"].setdefault(a.get("tool"), []).append(a.get("id"))
print("artifacts by tool:", {k: len(v) for k, v in made["artifactsByTool"].items()})
if prun:
    sc = next(s for s in c.get("/api/state").json()["scenarios"] if s["id"] == sid)
    call("state scenarios", "PUT", f"/api/state/scenarios/{sid}", {"by": PERSON, "value": {**sc, "lastRunId": prun}})
    tr = call("pureos from-run", "POST", "/api/pureos/train/from-run", {"artifactId": prun, "trainId": "tr-h6"})
    print("from-run keys:", list(tr or {}))
    train = (tr or {}).get("train")
    if train:
        call("state trains", "PUT", f"/api/state/trains/{train['id']}",
             {"by": PERSON, "value": {"train": train, "savedAt": NOW, "by": PERSON}})
        made["trainMade"] = train["id"]
        trun = call("pureos train run", "POST", "/api/pureos/train/run", {"train": train, "by": PERSON})
        print("train run keys:", list(trun or {})[:12])
        made["trainRun"] = (trun or {}).get("artifactId") or ((trun or {}).get("artifact") or {}).get("id")
    streams = [s.get("id") for s in (latest.get("output") or {}).get("streams", [])]
    if streams:
        p = call("thermo props", "POST", "/api/thermo/props", {"artifactId": prun, "streamId": streams[0]})
        made["thermo"] = (p or {}).get("id")
    exp = call("flowsheet export", "POST", "/api/flowsheets/export", {"artifactId": prun, "by": PERSON})
    made["sffExport"] = (exp or {}).get("id")
ref = (made.get("artifactsByTool") or {}).get("proforma.reference") or []
if ref:
    made["reference"] = ref[0]
    call("pureos from-run (reference)", "POST", "/api/pureos/train/from-run", {"artifactId": ref[0], "trainId": "tr-h6-ref"})

call("guild evidence", "POST", "/api/guild/evidence", {
    "id": "e-h6-0001", "personId": "p-ben", "skillId": "aseptic-sampling", "kind": "witnessed", "outcome": "pass",
    "at": NOW, "observerId": "p-ada", "source": {"kind": "signoff", "ref": "proto-batch", "stepId": "s-sample"},
    "raw": "took three clean samples", "recordedAt": NOW})
chk = call("guild check request", "POST", "/api/guild/checks/request",
           {"personId": "p-ben", "skillIds": ["aseptic-sampling"], "by": "p-ben"})
if chk:
    made["check"] = chk.get("id")
    call("guild check schedule", "POST", f"/api/guild/checks/{chk['id']}/schedule", {"by": "p-ada", "scheduledFor": DAY})
docs = c.get("/api/literature/documents").json()
made["documents"] = [(d.get("documentId"), d.get("title")) for d in docs]
(data_dir / "extra.json").write_text(json.dumps({"made": made, "log": log}, indent=1, default=str))
print(json.dumps({k: v for k, v in made.items() if k != "artifactsByTool"}, default=str)[:2500])
