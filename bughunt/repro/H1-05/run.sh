#!/usr/bin/env bash
# H1-05: the biosteam engine lists cellulosic_ethanol_v0 in the four configurations it built in here; its run
# route builds it in 'AFEX, IB', a fifth the listing omits, and keeps a refused runs row for it, and its
# parameters route builds it in 'AFEX, IB' too. docs/api/engines.md:242-248 refuses in words, at every door, a
# configuration the thing does not name. lactic, which the listing omits, is run and reported beside it.
# Usage, from the repository root: bash bughunt/repro/H1-05/run.sh
# The head's own service and venv on a fresh test database, keyless, a port in 9360-9369; nothing under core/,
# src/, scripts/ or examples/ is touched. Exits 0 whatever it finds; its last line is RESULT: DEFECT or NO-DEFECT.
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h1_05_svc
OUT=$(mktemp -d "$BH_WORK/H1-05.XXXXXX")
PORT=""
cleanup() {
  [ -n "$PORT" ] && bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$OUT"
}
trap cleanup EXIT
verdict() { echo "RESULT: $1"; exit 0; }

# start_ours: the head's service over $DB on a free port of 9360-9369; PORT is set only when the listener's
# environment names our database, so cleanup never stops another's service.
start_ours() {
  local p q o pid; PORT=""; O=""
  for q in $(seq 9360 9369); do [ -z "$(bh_port_pid "$q")" ] && { p=$q; break; }; done
  [ -n "$p" ] || { echo "no free port in 9360-9369"; return 1; }
  o=$(bh_svc_start "$DB" "$p") || { echo "the service did not start on $p"; return 1; }
  pid=$(bh_port_pid "$p")
  tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -q "^OPENFERMENT_DATABASE_URL=.*/$DB\$" \
    || { echo "port $p is served by another process"; return 1; }
  PORT=$p; O=$o
}
rm -rf "$BH_WORK/data-$DB"
start_ours || verdict NO-DEFECT
echo "service $O over fresh database $DB"
bh_project "$O" h1r05 >/dev/null
H=(-H 'content-type: application/json' -H 'X-OpenFerment-Project: h1r05')
T=cellulosic_ethanol_v0

# ask NAME METHOD URL [BODY]: one request, its code and seconds kept as $OUT/NAME.code and $OUT/NAME.secs.
ask() {
  local name=$1 method=$2 url=$3 body=${4:-} t0; t0=$(date +%s)
  if [ -n "$body" ]; then
    curl -s --noproxy '*' -m 900 -o "$OUT/$name.json" -w '%{http_code}' -X "$method" "$url" "${H[@]}" -d "$body" > "$OUT/$name.code"
  else
    curl -s --noproxy '*' -m 900 -o "$OUT/$name.json" -w '%{http_code}' -X "$method" "$url" "${H[@]}" > "$OUT/$name.code"
  fi
  echo $(( $(date +%s) - t0 )) > "$OUT/$name.secs"
  printf '%s %s -> HTTP %s in %s s: ' "$method" "${url#"$O"}" "$(cat "$OUT/$name.code")" "$(cat "$OUT/$name.secs")"
  python3 -c "import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d=open(sys.argv[1]).read()
print((d.get('detail') if isinstance(d,dict) and 'detail' in d else json.dumps(d))[:300] if not isinstance(d,list) else f'a list of {len(d)}')" "$OUT/$name.json"
}

# 1. What the engine lists (GET /api/engines).
ask engines GET "$O/api/engines"
python3 - "$OUT/engines.json" <<'PY'
import json, sys
e = next(x for x in json.load(open(sys.argv[1])) if x["name"] == "biosteam")
t = next(x for x in e["things"] if x["id"] == "cellulosic_ethanol_v0")
print("listed configurations of biosteam/cellulosic_ethanol_v0:", t["configurations"], "default:", t["defaultConfiguration"])
print("lactic listed among biosteam's things:", any(x["id"] == "lactic" for x in e["things"]))
PY

# 2. A control: a configuration named nowhere ('dilute acid, SSCF') is refused before any build. Its words
#    show which list the door holds a configuration to.
ask ctl POST "$O/api/engines/biosteam/run" "{\"thing\":\"$T\",\"configuration\":\"dilute acid, SSCF\",\"by\":\"H1-05 repro\"}"

# 3. The run route, in the unlisted 'AFEX, IB', on a cold worker (its seconds are BioSTEAM's import and build).
ask afex POST "$O/api/engines/biosteam/run" "{\"thing\":\"$T\",\"configuration\":\"AFEX, IB\",\"by\":\"H1-05 repro\"}"

# 4. The parameters route, in the unlisted 'AFEX, IB' (the worker builds it once more to read it back).
ask params GET "$O/api/engines/biosteam/parameters?thing=$T&configuration=AFEX,%20IB"

# 5. Beside it: lactic, which the listing omits and the shelf holds.
ask lactic POST "$O/api/engines/biosteam/run" '{"thing":"lactic","by":"H1-05 repro"}'

# 6. The rows the project now keeps.
ask runs GET "$O/api/runs"
python3 - "$OUT/runs.json" <<'PY'
import json, sys
for r in json.load(open(sys.argv[1])):
    print(f"  kept row {r['id']}: engine {r['engine']}, plant {r['plant']}, configuration {r.get('configuration')!r}, "
          f"status {r['status']}, refused {(r.get('refused') or '')[:120]!r}")
PY

python3 - "$OUT" <<'PY' > "$OUT/verdict.txt"
import json, sys, os
out = sys.argv[1]
def j(n): return json.load(open(os.path.join(out, n + ".json")))
def code(n): return open(os.path.join(out, n + ".code")).read().strip()
def secs(n): return int(open(os.path.join(out, n + ".secs")).read().strip())
e = next(x for x in j("engines") if x["name"] == "biosteam")
listed = next(x for x in e["things"] if x["id"] == "cellulosic_ethanol_v0")["configurations"]
rows = j("runs")
afex_rows = [r for r in rows if r["plant"] == "cellulosic_ethanol_v0" and r.get("configuration") == "AFEX, IB"]
lactic_rows = [r for r in rows if r["plant"] == "lactic"]
afex_words = j("afex").get("detail", "") if isinstance(j("afex"), dict) else ""
params = j("params")
params_words = params.get("detail", "") if isinstance(params, dict) else f"{len(params)} parameters"
built_words = ("InfeasibleRegion", "M207", "could not be built")
unlisted = "AFEX, IB" not in listed
run_built = any(w in afex_words for w in built_words) or bool(afex_rows)
params_built = code("params") == "200" or any(w in params_words for w in built_words)
print(f"EXPECTED: the listing names {listed}; a run or a parameters read naming 'AFEX, IB' is a 422 naming those "
      "configurations, said before anything is built, and keeps no row")
print(f"OBSERVED: run route HTTP {code('afex')} after {secs('afex')} s in BioSTEAM's words {afex_words[:160]!r}, "
      f"{len(afex_rows)} refused row(s) kept for 'AFEX, IB' ({', '.join(r['id'] for r in afex_rows) or 'none'}); "
      f"parameters route HTTP {code('params')} after {secs('params')} s: {params_words[:160]!r}")
print(f"OBSERVED (beside it, not in the verdict): lactic run HTTP {code('lactic')}, {len(lactic_rows)} refused "
      f"row(s) kept ({', '.join(r['id'] for r in lactic_rows) or 'none'}); the control 'dilute acid, SSCF' HTTP "
      f"{code('ctl')}: {(j('ctl').get('detail', '') if isinstance(j('ctl'), dict) else '')[:200]!r}")
print(f"DOORS: run route built and kept a row: {run_built and bool(afex_rows)}; parameters route built: {params_built}")
print("VERDICT", "DEFECT" if unlisted and ((run_built and afex_rows) or params_built) else "NO-DEFECT")
PY
grep -v '^VERDICT' "$OUT/verdict.txt"
v=$(sed -n 's/^VERDICT //p' "$OUT/verdict.txt")
verdict "${v:-NO-DEFECT}"
