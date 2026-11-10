"""fill_extra.py ORIGIN PROJECT DATA_DIR: fill an alpha 2.1 service (main, 112eb8b) with one of each kind
of row fill_prove.py leaves out, through alpha 2.1's own API, in the shapes its client sent
(src/data/types.ts at 112eb8b). Each request is printed with its status; a refused one does not stop the
rest. What was made is written to DATA_DIR/extra.json for check_head.py to read back at the head.

Keyless and offline: the service runs in fixture mode; nothing here calls a model.
"""
from __future__ import annotations

import json
import shutil
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
made: dict[str, Any] = {}
log: list[dict[str, Any]] = []


def call(name: str, method: str, path: str, body: Any = None, **kw: Any) -> Any:
    t0 = time.monotonic()
    r = c.request(method, path, json=body, **kw)
    dt = time.monotonic() - t0
    try:
        out = r.json()
    except ValueError:
        out = r.text[:300]
    ok = 200 <= r.status_code < 300
    print(f"{'ok ' if ok else 'NO '} {r.status_code} {name} {method} {path} ({dt:.1f}s)"
          + ("" if ok else f": {str(out)[:400]}"), flush=True)
    log.append({"name": name, "method": method, "path": path, "status": r.status_code,
                "detail": None if ok else str(out)[:600]})
    return out if ok else None


def state(kind: str, item_id: str, value: Any) -> Any:
    return call(f"state {kind}", "PUT", f"/api/state/{kind}/{item_id}", {"by": PERSON, "value": value})


# ── Intake: a pasted document, two collected through fixtures, a catalogue file ──
fx = data_dir / "fixtures"
core_fx = Path(sys.argv[4]) if len(sys.argv) > 4 else None
if core_fx:
    (fx / "jats").mkdir(parents=True, exist_ok=True)
    (fx / "sgd").mkdir(parents=True, exist_ok=True)
    shutil.copy(core_fx / "jats" / "structural.xml", fx / "jats" / "PMC9999999.xml")
    shutil.copy(core_fx / "sgd" / "S000203483.json", fx / "sgd" / "S000203483.json")
pasted = call("intake paste", "POST", "/api/intake/paste", {
    "title": "A pasted note on stover handling", "by": PERSON, "url": "https://example.org/note",
    "licenceClass": "open", "licence": "CC BY 4.0, as its page states",
    "text": "# Stover handling\n\nA pasted note. The bales were stored under cover for a season before milling. "
            "Moisture was read on arrival and again before pretreatment.\n"})
made["pasted"] = (pasted or {}).get("documentId")
for ident in ("PMC9999999", "SGD:S000203483"):
    got = call(f"intake collect {ident}", "POST", "/api/intake/collect", {"identifier": ident, "by": PERSON,
                                                                          "reason": "upgrade hunt"})
    made.setdefault("collected", []).append({"identifier": ident, "outcome": got})
csv = "id,name,species,aliases\nsc-h6,Saccharomyces cerevisiae H6,Saccharomyces cerevisiae,yeast H6;H6\n"
call("intake catalogue", "POST", "/api/intake/catalogue", files={"file": ("strains.csv", csv.encode(), "text/csv")},
     data={"kind": "strain", "by": PERSON})

# ── Catalogues: one of each kind, a product in alpha 2.1's free-text category beside one in a class ──
entries = [
    ("strain", {"kind": "strain", "id": "ethanol-red", "name": "Ethanol Red", "species": "Saccharomyces cerevisiae",
                "program": "yeast", "aliases": ["ER"], "source": PERSON}),
    ("product", {"kind": "product", "id": "ethanol", "name": "Ethanol", "category": "biofuel",
                 "note": "the plant's product", "source": PERSON}),
    ("product", {"kind": "product", "id": "cellulase", "name": "Cellulase", "category": "industrial_enzyme",
                 "sequence": "MKLLAAGAVLSLAAQ", "sequenceSource": "a typed example for the hunt", "source": PERSON}),
    ("skill", {"kind": "skill", "id": "aseptic-sampling", "name": "Aseptic sampling", "family": "bench",
               "summary": "Taking a sample without contaminating the vessel", "mastery": ["no contamination"],
               "source": PERSON}),
    ("lesson", {"kind": "lesson", "id": "sampling-101", "name": "Sampling 101", "skills": ["aseptic-sampling"],
                "summary": "How to take a sample", "note": "a first lesson", "source": PERSON}),
]
for kind, e in entries:
    call(f"catalogue {kind} {e['id']}", "POST", f"/api/catalogues/{kind}", {"entry": e, "by": PERSON})
made["catalogue"] = [(k, e["id"]) for k, e in entries] + [("strain", "sc-h6")]

# ── Guild ──
person = {"id": "p-ada", "name": PERSON, "role": "lead", "title": "Process engineer", "joinedAt": DAY,
          "active": True, "addedBy": PERSON, "addedAt": NOW}
call("guild person", "POST", "/api/guild/people", person)
call("guild policy", "POST", "/api/guild/policy", {"routineGate": "advise", "criticalGate": "enforce",
                                                    "checksPerQuarter": 2, "updatedBy": PERSON, "updatedAt": NOW})
ev = {"id": "ev-1", "personId": "p-ada", "skillId": "aseptic-sampling", "kind": "observed", "outcome": "pass",
      "at": NOW, "observerId": "p-ada", "source": "manual", "raw": "took three clean samples", "recordedAt": NOW}
call("guild evidence", "POST", "/api/guild/evidence", ev)
chk = call("guild check request", "POST", "/api/guild/checks/request",
           {"personId": "p-ada", "skillIds": ["aseptic-sampling"], "by": PERSON})
if chk:
    made["check"] = chk.get("id")
    call("guild check schedule", "POST", f"/api/guild/checks/{chk['id']}/schedule",
         {"by": PERSON, "scheduledFor": DAY})

# ── State: a page-made runbook and its lock, a deposition with a series, measured evidence ──
runbook = {
    "id": "rb-page-1", "kind": "fermentation", "title": "Batch on hydrolysate", "status": "queued", "stages": [],
    "note": "adopted from a draft", "eta": None, "outputs": [], "productId": "ethanol", "progressPct": 0,
    "estCostUsd": None, "strainId": "ethanol-red",
    "predictions": [{"id": "pr-1", "label": "Final titre", "value": 40.0, "unit": "g/L", "confidence": "medium",
                     "basis": "a person's assumption"}],
    "measurementSchema": [{"id": "m-x", "label": "Biomass", "unit": "g/L", "timepoint": "series", "predictionId": None},
                          {"id": "m-p", "label": "Ethanol", "unit": "g/L", "timepoint": "series", "predictionId": "pr-1"},
                          {"id": "m-s", "label": "Glucose", "unit": "g/L", "timepoint": "series", "predictionId": None}],
    "lockedAt": None, "lockHash": None,
}
state("runbooks", runbook["id"], runbook)
sys.path.insert(0, str(Path(sys.argv[5]) / "core")) if len(sys.argv) > 5 else None
try:
    from openferment_core.runbook_lock import lock_hash  # alpha 2.1's own
    digest = lock_hash(runbook["predictions"], runbook["measurementSchema"])
except Exception as e:  # noqa: BLE001
    print("no lock_hash:", e)
    digest = None
if digest:
    state("runbookLocks", runbook["id"], {"lockedAt": NOW, "lockHash": digest})
    state("runbooks", runbook["id"], {**runbook, "lockedAt": NOW, "lockHash": digest, "status": "running"})
hours = [0, 4, 8, 12, 16, 20, 24]
X = [0.5, 0.9, 1.7, 3.0, 4.6, 5.6, 6.0]
P = [0.0, 1.0, 4.0, 10.0, 20.0, 30.0, 36.0]
S = [100.0, 98.0, 91.0, 78.0, 56.0, 34.0, 22.0]
entries_, times = [], {}
for i, h in enumerate(hours):
    for mid, v in (("m-x", X[i]), ("m-p", P[i]), ("m-s", S[i])):
        eid = f"e-{mid}-{i}"
        entries_.append({"id": eid, "measureId": mid, "stepId": "s-sample", "at": NOW, "value": v, "unit": "g/L",
                         "raw": f"{v} grams per litre", "confirmed": True})
        times[eid] = float(h)
dep = {"id": "dep-h6-1", "runbookId": runbook["id"], "protocolId": "proto-batch", "operatorId": None,
       "startedAt": NOW, "closedAt": None, "state": "running", "entries": entries_,
       "observations": [{"id": "ob-1", "stepId": "s-sample", "at": NOW, "raw": "foam at hour twelve",
                         "structured": None}],
       "reconciliation": None, "sampleTimes": times,
       "seriesRoles": {"m-x": "biomass", "m-p": "product", "m-s": "substrate"}}
state("depositions", dep["id"], dep)
me = {"id": "me-1", "depositionId": dep["id"], "runbookId": runbook["id"], "productId": "ethanol",
      "predictionId": "pr-1", "label": "Final titre", "value": 36.0, "unit": "g/L", "provenance": "measured",
      "conditions": {"protocolId": "proto-batch", "scale": 2.0, "strainId": "ethanol-red"}, "deviations": [],
      "confirmed": True, "at": NOW}
state("measuredEvidence", me["id"], me)
made["state"] = {"runbook": runbook["id"], "deposition": dep["id"], "measured": me["id"]}

# ── fermOS: a fit of the deposition's series, a forecast, a simulation, a vessel ──
series = [{"measureId": mid, "label": lab, "unit": "g/L", "role": role,
           "points": [{"t": float(h), "value": v} for h, v in zip(hours, vals)]}
          for mid, lab, role, vals in (("m-x", "Biomass", "biomass", X), ("m-p", "Ethanol", "product", P),
                                       ("m-s", "Glucose", "substrate", S))]
fit = call("fermos fit", "POST", "/api/fermos/fit", {"depositionId": dep["id"], "series": series})
fit_id = None
if fit:
    fit_id = (fit.get("kinetic") or fit.get("fit") or {}).get("id") or fit.get("artifactId") or \
        next((v.get("id") for v in fit.values() if isinstance(v, dict) and v.get("id")), None)
    made["fit"] = {k: (v.get("id") if isinstance(v, dict) else v) for k, v in fit.items()}
    print("fit keys:", list(fit))
if fit_id:
    call("fermos forecast", "POST", "/api/fermos/forecast", {"fitArtifactId": fit_id})
sim = call("fermos simulate", "POST", "/api/fermos/simulate", {
    "family": "batch_v1", "startFrom": "records", "overrides": [
        {"scope": "fermos:family:batch_v1", "key": k, "value": v, "by": PERSON, "at": DAY,
         "origin": "person-assumption"} for k, v in (("mu_max", 0.3), ("Ks", 0.5), ("Yxs", 0.1), ("Yps", 0.45),
                                                      ("X0", 0.5), ("S0", 100.0), ("P0", 0.0), ("alpha", 2.0),
                                                      ("beta", 0.1), ("ms", 0.0), ("kd", 0.0))]})
if sim is None:
    sim = call("fermos simulate (fewer)", "POST", "/api/fermos/simulate", {"family": "batch_v1"})
sim_id = (sim or {}).get("artifact", {}).get("id") if isinstance((sim or {}).get("artifact"), dict) else (sim or {}).get("id")
made["simulation"] = sim_id
if sim_id:
    call("fermos vessel", "POST", "/api/fermos/vessel", {"simulation": sim_id, "vesselType": "stirred-tank"})

# ── Proforma: a scenario the page makes, its overrides and fits, a run; the retired benchmark and reference ──
sid = "sc-h6-glucose"
scenario = {"id": sid, "modelId": "ethanol_glucose_v0", "kind": "biosteam", "name": "Glucose, dearer sugar",
            "description": "made in Proforma", "product": "ethanol", "dims": [], "point": {}, "assumptions": [],
            "pinned": True, "flowsheetId": "ethanol_glucose_v0", "lastRunId": None, "createdAt": NOW}
state("scenarios", sid, scenario)
ov = [{"scope": f"proforma:{sid}", "key": "price.glucose", "value": 0.45, "by": PERSON, "at": DAY,
       "origin": "person-assumption", "note": "quoted"}]
state("overrides", f"proforma:{sid}", ov)
if fit_id:
    state("fits", sid, {"mu_max": fit_id})
run = call("proforma run", "POST", "/api/proforma/run", {"scenarioId": sid, "flowsheet": "ethanol_glucose_v0",
                                                         "overrides": ov, "samples": 20})
prun = (run or {}).get("artifact", {}).get("id") if run else None
made["proformaRun"] = prun
run2 = call("proforma run (assumptions)", "POST", "/api/proforma/run", {
    "scenarioId": sid, "flowsheet": "ethanol_glucose_v0", "samples": 20,
    "assumptions": [{"key": "price.glucose", "value": 0.5, "low": 0.4, "high": 0.6, "by": PERSON, "at": DAY}]})
made["proformaRunAssumptions"] = (run2 or {}).get("artifact", {}).get("id") if run2 else None
if prun:
    state("scenarios", sid, {**scenario, "lastRunId": prun})
bench = call("proforma benchmark", "POST", "/api/proforma/benchmark")
made["benchmark"] = (bench or {}).get("artifact", {}).get("id") if bench else None
ref = call("proforma reference corn_drygrind", "POST", "/api/proforma/reference/corn_drygrind")
made["reference"] = ((ref or {}).get("run") or {}).get("id") if ref else None
print("reference keys:", list(ref or {}))

# ── pureOS: a train read from the Proforma run, run, saved in the Builder; a proposal ──
if prun:
    tr = call("pureos from-run", "POST", "/api/pureos/train/from-run", {"artifactId": prun, "trainId": "tr-h6"})
    train = (tr or {}).get("train")
    if train:
        state("trains", train["id"], {"train": train, "savedAt": NOW, "by": PERSON})
        made["trainMade"] = train["id"]
        trun = call("pureos train run", "POST", "/api/pureos/train/run", {"train": train, "by": PERSON})
        made["trainRun"] = ((trun or {}).get("artifact") or {}).get("id") if trun else None
        print("train run keys:", list(trun or {}))
call("pureos propose", "POST", "/api/pureos/propose", {"product": "ethanol", "host": "ethanol-red"})

# ── Artifacts beside: thermo, protparam, volatility, geneos; an SFF export and upload ──
call("thermo volatility", "POST", "/api/thermo/volatility", {"product": "ethanol"})
call("protparam", "POST", "/api/protparam", {"product": "cellulase"})
if prun:
    call("thermo props", "POST", "/api/thermo/props", {"artifactId": prun, "streamId": "s1"})
    exp = call("flowsheet export", "POST", "/api/flowsheets/export", {"artifactId": prun, "by": PERSON})
    made["sffExport"] = (exp or {}).get("id")
lib = data_dir / "sff-library"
some = sorted(lib.rglob("*.json"))
sff_file = next((p for p in some if "SF_BST_01" in p.name), some[0] if some else None)
if sff_file:
    up = call("flowsheet upload", "POST", "/api/flowsheets/import",
              files={"file": (sff_file.name, sff_file.read_bytes(), "application/json")}, data={"by": PERSON})
    made["sffUpload"] = (up or {}).get("id")
call("geneos models", "GET", "/api/geneos/models")

# ── Postdoc's Live conversation written by a page ──
live = {"id": "lc-page-1", "title": "What limits the titre?", "startedAt": NOW,
        "turns": [{"id": "t-page-1", "question": "What limits the titre?", "askedAt": NOW, "steps": [], "plan": None,
                   "error": {"kind": "network", "message": "the page lost its connection"}, "status": "failed"}]}
state("conversations", live["id"], live)
made["live"] = live["id"]

(data_dir / "extra.json").write_text(json.dumps({"made": made, "log": log}, indent=1, default=str))
print(json.dumps({"ok": sum(1 for x in log if 200 <= x["status"] < 300), "refused": [x["name"] for x in log
                                                                                    if not 200 <= x["status"] < 300]}))
