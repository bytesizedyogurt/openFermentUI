#!/usr/bin/env bash
# H8-10: a catalogue file naming one id on two rows answers both rows kept, and the catalogue holds the
# second row alone: the first row's entry is gone with no refusal and no word in the answer.
# The head's own service on a fresh database, port 9140; keyless, no model call, no engine worker.
# usage, from the repository root: bash bughunt/repro/H8-10/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h8_10_svc
PORT=9140
T=$BH_WORK/H8-10; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: POST /api/intake/catalogue with the CSV 'id,name / S5,First / S5,Second' keeps every row that is an"
echo "EXPECTED: entry and refuses every other row with its reason (docs/api/intake.md:104): each row the answer counts"
echo "EXPECTED: as kept is held after the request, so the second S5 row is refused in words (or the answer names the"
echo "EXPECTED: replacement), and the answer's kept list names S5 once"

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" h810 >/dev/null

cat > "$T/probe.py" <<'PY'
import json, sys
import httpx
origin = sys.argv[1]
c = httpx.Client(base_url=origin, trust_env=False, timeout=60, headers={"X-OpenFerment-Project": "h810"})
r = c.post("/api/intake/catalogue", files={"file": ("dup.csv", b"id,name\nS5,First\nS5,Second\n", "text/csv")},
           data={"kind": "strain", "by": "h8-10 repro"})
ans = r.json()
held = [(e["id"], e["name"]) for e in c.get("/api/catalogues/strain").json()]
aud = c.get("/api/audit", params={"action": "keep_catalogue", "target": "strain/S5"}).json()
print(f"OBSERVED: HTTP {r.status_code}, answer {json.dumps(ans)}")
print(f"OBSERVED: the strain catalogue holds {held}")
print(f"OBSERVED: {len(aud)} keep_catalogue audit rows on strain/S5, states {[a.get('state') for a in aud]}")
lost = [n for n in ("First", "Second") if ("S5", n) not in held]
print(f"OBSERVED: rows of the file whose entry the catalogue does not hold: {lost}")
defect = (r.status_code == 200 and ans.get("kept", []).count("S5") == 2 and not ans.get("refused")
          and held == [("S5", "Second")])
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
out=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$T/probe.py" "$O" 2>&1)
echo "$out" | grep -v '^RESULT:'
if echo "$out" | grep -qx 'RESULT: DEFECT'; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
