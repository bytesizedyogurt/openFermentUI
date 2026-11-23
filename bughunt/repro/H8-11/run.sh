#!/usr/bin/env bash
# H8-11: a catalogue file's row that carries a `source` is kept with the row's words as the entry's source, and
# the file it came in by is named nowhere on the entry (only in the audit row's detail).
# The head's own service on a fresh database, port 9811; keyless, no model call, no engine worker.
# usage, from the repository root: bash bughunt/repro/H8-11/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h8_11_svc
PORT=9811
T=$BH_WORK/H8-11; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: POST /api/intake/catalogue (kind strain) with the JSON file rows.json holding S6 (a row with"
echo "EXPECTED: source \"a row's own words\") and S7 (a row with no source) keeps every row that is an entry"
echo "EXPECTED: \"with the file as its source\" (docs/api/intake.md:104): both entries' source names the file rows.json"

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" h811 >/dev/null

cat > "$T/probe.py" <<'PY'
import json, sys
import httpx
origin = sys.argv[1]
c = httpx.Client(base_url=origin, trust_env=False, timeout=60, headers={"X-OpenFerment-Project": "h811"})
rows = json.dumps([{"id": "S6", "name": "Six", "source": "a row's own words"},
                   {"id": "S7", "name": "Seven"}]).encode()
r = c.post("/api/intake/catalogue", files={"file": ("rows.json", rows, "application/json")},
           data={"kind": "strain", "by": "h8-11 repro"})
print(f"OBSERVED: HTTP {r.status_code}, answer {json.dumps(r.json())}")
src = {}
for i in ("S6", "S7"):
    e = c.get(f"/api/catalogues/strain/{i}").json()
    src[i] = e.get("source")
    print(f"OBSERVED: GET /api/catalogues/strain/{i} source: {json.dumps(src[i])}")
for i in ("S6", "S7"):
    aud = c.get("/api/audit", params={"action": "keep_catalogue", "target": f"strain/{i}"}).json()
    print(f"OBSERVED: keep_catalogue audit on strain/{i}, detail {[a.get('detail') for a in aud]}")
defect = (r.status_code == 200 and src["S7"] == "the file rows.json"
          and src["S6"] == "a row's own words" and "rows.json" not in (src["S6"] or ""))
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
out=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$T/probe.py" "$O" 2>&1)
echo "$out" | grep -v '^RESULT:'
if echo "$out" | grep -qx 'RESULT: DEFECT'; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
