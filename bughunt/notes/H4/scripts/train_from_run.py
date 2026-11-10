"""H4: read a kept run into a train (POST /api/pureos/train/from-run), run it (POST /api/pureos/train/run),
and keep both answers in the scratch directory.
    cd core && bh_env .venv/bin/python train_from_run.py http://127.0.0.1:8840 h4p <artifact id> <tag>
"""
import json, sys, httpx
O, P, A, TAG = sys.argv[1:5]
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
with httpx.Client(trust_env=False, timeout=900) as c:
    r = c.post(f"{O}/api/pureos/train/from-run", json={"artifactId": A}, headers=H)
    print("from-run", r.status_code)
    fr = r.json()
    json.dump(fr, open(f"{W}/train-{TAG}-fromrun.json", "w"), indent=1)
    if r.status_code != 200:
        print(fr); sys.exit()
    print("units", [u["id"] for u in fr["train"]["units"]], "unmapped", [(u["unitId"], u["why"][:80]) for u in fr["unmapped"]])
    print("refusals", fr["refusals"]); print("notes", [n[:200] for n in fr["notes"]])
    r = c.post(f"{O}/api/pureos/train/check", json={"train": fr["train"], "by": "h4"}, headers=H)
    print("check", r.status_code, json.dumps(r.json())[:1500])
    r = c.post(f"{O}/api/pureos/train/run", json={"train": fr["train"], "by": "h4"}, headers=H)
    print("run", r.status_code)
    tr = r.json()
    json.dump(tr, open(f"{W}/train-{TAG}-run.json", "w"), indent=1)
    if r.status_code != 200:
        print(json.dumps(tr)[:3000])
