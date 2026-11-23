"""gen_alpha1.py MODELS_A1 OUT_DIR: alpha 1.0 data directories, each file written by alpha 1.0's own models
(`git show alpha-1.0:core/openferment_core/models.py`, which imports pydantic alone), in the shapes
core/data/ held at alpha 1.0: biorepo.json, guild.json, checks.json, practice.json, proposals.json,
audit.jsonl, artifacts/<id>.json, candidates/<paper>.json, candidates/hand/<paper>.json, pureos-trains.json.
The records are placeholders. OUT_DIR gets one directory a case:

  tag           the tag's own core/data/biorepo.json, as committed (empty)
  full          one of everything, decisions labelled as alpha 1.0's browser sent them (curated, gold, demo)
  bad-json      full, biorepo.json cut short
  bad-shape     full, a decision whose status is no status
  estimate      full, a verified decision whose gold value is a model's estimate (an origin alpha 2.0 types)
  noreviewer    full, a verified decision that names no reviewer
  mismatch      full, a decision kept under one record's id that names another
  empty-file    full, biorepo.json empty
  empty-dir     nothing at all
  dup-person    full, guild.json naming one person twice under one id
  dup-paper     full, two extraction files for one paper
  dup-artifact  full, two artifact files holding one artifact id
  big           full, biorepo.json with 30000 decisions
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("models_a1", sys.argv[1])
m = importlib.util.module_from_spec(spec)
sys.modules["models_a1"] = m
spec.loader.exec_module(m)
for name in dir(m):
    obj = getattr(m, name)
    if isinstance(obj, type) and hasattr(obj, "model_rebuild"):
        try:
            obj.model_rebuild()
        except Exception:  # noqa: BLE001
            pass
out = Path(sys.argv[2])
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)

Q = m.Quantity
C1 = m.Candidate(id="cl1-P1-0001", paperId="P1", sectionId="s1", quote="Placeholder A | 3 | mg L-1",
                 field="titer_secreted", value=3, unit="mg L-1", si=Q(value=0.003, unit="g L-1"))
C2 = m.Candidate(id="cl1-P1-0002", paperId="P1", sectionId="s1", quote="Placeholder B | 5 | mg L-1",
                 field="titer_secreted", value=5, unit="mg L-1", si=Q(value=0.005, unit="g L-1"))
C3 = m.Candidate(id="cl1-P1-0003", paperId="P1", sectionId="s2", quote="Placeholder C | 7 | mg L-1",
                 field="titer_secreted", value=7, unit="mg L-1", si=Q(value=0.007, unit="g L-1"))
D1 = m.ReviewDecision(status="verified", provenance="curated", reviewer="Ada Moreno", recordId=C1.id,
                      at="2026-10-20T00:00:00Z", gold=Q(value=3, unit="mg L-1"))
D2 = m.ReviewDecision(status="verified", provenance="gold", reviewer="Ada Moreno", recordId=C2.id,
                      at="2026-10-20T00:01:00Z")
D3 = m.ReviewDecision(status="rejected", provenance="demo", reviewer="Ada Moreno", recordId=C3.id,
                      at="2026-10-20T00:02:00Z", rejectReason="a placeholder row")
repo = m.BioRepo(decisions={C1.id: D1, C2.id: D2, C3.id: D3}, records=[C1, C2, C3])

lead = m.GuildPerson(id="p-ada", name="Ada Moreno", role="lead", joinedAt="2026-10-01", addedAt="2026-10-01T00:00:00Z")
tech = m.GuildPerson(id="p-ben", name="Ben Ortiz", role="member", joinedAt="2026-10-02", addedAt="2026-10-02T00:00:00Z",
                     addedBy="p-ada")
ev = m.GuildEvidence(id="e-0001", personId="p-ben", skillId="SK-OD", kind="independent", at="2026-10-03",
                     source=m.EvidenceSource(kind="lead", ref="a placeholder training record"), raw="a placeholder entry")
guild = m.Guild(people=[lead, tech], evidence=[ev], policy=m.GuildPolicy(checksPerQuarter=2, updatedBy="p-ada",
                                                                        updatedAt="2026-10-01T00:00:00Z"))
check = m.Check(id="ck-0001", personId="p-ben", skillIds=["SK-OD"], proposedAt="2026-10-04T00:00:00Z",
                proposedBy="system")
checks = m.Checks(checks=[check])
sc = m.PracticeScenario(id="ps-0001", skillId="SK-OD", title="A placeholder scenario", situation="s", prompt="p",
                        model="claude-x", createdAt="2026-10-05T00:00:00Z")
ss = m.PracticeSession(id="pss-0001", scenarioId="ps-0001", skillId="SK-OD", personId="p-ben",
                       startedAt="2026-10-05T00:10:00Z")
practice = m.Practice(scenarios=[sc], sessions=[ss])
prop = m.Proposal(id="pr-0001", at="2026-10-06T00:00:00Z", module="runbooks", action="lock", gate="lock",
                  title="Runbooks: lock — rb-1", why="w", how="h", by="claude-x", target="rb-1")
proposals = m.Proposals(proposals=[prop])
audit = [m.AuditEntry(at="2026-10-06T00:00:00Z", agent="model", who="claude-x", module="runbooks", action="lock",
                      state="proposed", target="rb-1"),
         m.AuditEntry(at="2026-10-06T00:01:00Z", agent="person", who="Ada Moreno", module="biorepo", action="decide",
                      state="verified", target=C1.id)]
out_ = {"evidence": {"provenance": "demo", "value": 1.5}, "note": "a placeholder"}
import hashlib
def ohash(o):  # alpha 1.0's own rule is in artifacts.py; the importer recomputes it when the output renames
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
art = m.Artifact(id="00000000000000aa", tool="proforma.run", toolVersion="1", provenance="demo",
                 inputs=[m.BasisInput(name="price", value=0.5, unit="USD/kg",
                                      source=m.BasisSource(kind="assumption", by="Ada Moreno", note="typed"))],
                 output=out_, outputHash=ohash(out_), createdAt="2026-10-07T00:00:00Z", durationMs=1)
ext = m.ExtractResponse(paperId="P1", extractedAt="2026-10-02T00:00:00Z", candidates=[C1, C2, C3])
hand = m.ExtractResponse(paperId="P1", run="hand" if "hand" in str(m.ExtractorRun) else "claude-1",
                         extractedAt="2026-10-02T01:00:00Z", candidates=[C2])
try:
    train = m.TrainSpec.model_validate({"id": "tr-0001", "name": "A placeholder train", "program": "yeast",
                                        "product": "ethanol", "inlet": {"kind": "typed", "params": {}},
                                        "units": [{"id": "U1", "type": "centrifuge"}]})
    kept = m.KeptTrains(trains=[m.KeptTrain(spec=train, madeBy="claude-x", at="2026-10-08T00:00:00Z",
                                            updatedAt="2026-10-08T00:00:00Z")])
except Exception as e:  # noqa: BLE001
    print("no kept train:", type(e).__name__, str(e).splitlines()[0])
    kept = None


def write(d: Path, *, repo_json: str | None = None) -> None:
    (d / "artifacts").mkdir(parents=True)
    (d / "candidates" / "hand").mkdir(parents=True)
    (d / "biorepo.json").write_text(repo_json if repo_json is not None else repo.model_dump_json(indent=2))
    (d / "guild.json").write_text(guild.model_dump_json(indent=2))
    (d / "checks.json").write_text(checks.model_dump_json(indent=2))
    (d / "practice.json").write_text(practice.model_dump_json(indent=2))
    (d / "proposals.json").write_text(proposals.model_dump_json(indent=2))
    (d / "audit.jsonl").write_text("".join(a.model_dump_json() + "\n" for a in audit))
    (d / "artifacts" / f"{art.id}.json").write_text(art.model_dump_json(indent=2))
    (d / "candidates" / "P1.json").write_text(ext.model_dump_json(indent=2))
    (d / "candidates" / "hand" / "P1.json").write_text(hand.model_dump_json(indent=2))
    if kept is not None:
        (d / "pureos-trains.json").write_text(kept.model_dump_json(indent=2))


tag = out / "tag"
tag.mkdir()
(tag / "biorepo.json").write_bytes(subprocess.run(["git", "-C", "/home/user/openFermentUI", "show",
                                                   "alpha-1.0:core/data/biorepo.json"], capture_output=True).stdout)
write(out / "full")
full = json.loads(repo.model_dump_json())
write(out / "bad-json", repo_json=repo.model_dump_json()[:200])
bad = json.loads(json.dumps(full)); bad["decisions"][C1.id]["status"] = "maybe"
write(out / "bad-shape", repo_json=json.dumps(bad))
est = json.loads(json.dumps(full))
est["decisions"][C1.id]["gold"] = {"value": 3, "unit": "mg L-1", "origin": {"kind": "model-estimate", "by": "claude-x",
                                                                           "at": "2026-10-20T00:00:00Z"}}
write(out / "estimate", repo_json=json.dumps(est))
nor = json.loads(json.dumps(full)); nor["decisions"][C2.id]["reviewer"] = None
write(out / "noreviewer", repo_json=json.dumps(nor))
mis = json.loads(json.dumps(full)); mis["decisions"][C3.id]["recordId"] = C1.id
write(out / "mismatch", repo_json=json.dumps(mis))
write(out / "empty-file", repo_json="")
(out / "empty-dir").mkdir()
write(out / "dup-person")
g = json.loads(guild.model_dump_json()); g["people"].append({**g["people"][1], "name": "Ben Ortiz (again)"})
(out / "dup-person" / "guild.json").write_text(json.dumps(g))
write(out / "dup-paper")
(out / "dup-paper" / "candidates" / "P1-again.json").write_text(ext.model_dump_json())
write(out / "dup-artifact")
(out / "dup-artifact" / "artifacts" / "copy.json").write_text(art.model_dump_json())
big = {"version": 1, "decisions": {}, "records": []}
for i in range(30000):
    cid = f"cl1-P9-{i:06d}"
    big["records"].append({**json.loads(C1.model_dump_json()), "id": cid, "paperId": "P9"})
    big["decisions"][cid] = {**json.loads(D3.model_dump_json()), "recordId": cid}
write(out / "big", repo_json=json.dumps(big))
for d in sorted(out.iterdir()):
    print(d.name, sum(f.stat().st_size for f in d.rglob("*") if f.is_file()), "bytes")
