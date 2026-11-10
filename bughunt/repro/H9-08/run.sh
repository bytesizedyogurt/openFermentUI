#!/usr/bin/env bash
# H9-08: budget settings of nan or inf are taken as numbers of dollars. A daily cap of nan or inf
# holds a 1000 USD call and ready marks the spend row sound; an ask budget of nan or inf makes the
# ask raise, and through the service POST /api/ask answers a 500 with the turn kept failed.
# A negative value, the control, is refused in words at every one of these doors.
#   bash bughunt/repro/H9-08/run.sh        (from the repository root)
# Keyless: ANTHROPIC_API_KEY is empty and ANTHROPIC_BASE_URL names 127.0.0.1:9159, where nothing
# listens, so no request can leave the machine; every defect shown here happens before a model call.
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H9-08
W="$BH_WORK/H9-08"; mkdir -p "$W"
DBC=bh_r_h9_08_caps; DBN=bh_r_h9_08_askneg; DBI=bh_r_h9_08_askinf
PN=9150; PI=9151; NOWHERE=9159; P=caps

cleanup() {
  bh_svc_stop "$PN" >/dev/null 2>&1; bh_svc_stop "$PI" >/dev/null 2>&1
  for d in "$DBC" "$DBN" "$DBI"; do bh_db_drop "$d" >/dev/null 2>&1; rm -rf "$BH_WORK/data-$d"; done
}
trap cleanup EXIT
cleanup

# ── 1. In process: the daily cap's gate and ready's row; the ask cap through Postdoc's loop ──
bh_db_fresh "$DBC" || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DBC" ANTHROPIC_BASE_URL="http://127.0.0.1:$NOWHERE" \
   OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= .venv/bin/python "$HERE/caps.py") > "$W/caps.out" 2>&1
cat "$W/caps.out"
caps_defects=$(sed -n 's/^DEFECTS \([0-9]*\)$/\1/p' "$W/caps.out"); caps_defects=${caps_defects:-0}

# ── 2. Through the service: POST /api/ask with an ask budget of -1 (control) and of inf ──
start() {  # start NAME PORT ASK_BUDGET
  local n="$1" port="$2" data; data=$(bh_data "$n")
  (
    cd "$BH_ROOT/core" || exit 1
    bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
      OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
      OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= OPENFERMENT_WORKSPACE_ID= \
      OPENFERMENT_ASK_BUDGET_USD="$3" ANTHROPIC_BASE_URL="http://127.0.0.1:$NOWHERE" \
      setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
      --log-level warning < /dev/null > "$W/svc-$port.log" 2>&1 &
  )
}
bh_db_fresh "$DBN" && bh_db_fresh "$DBI" || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }
start "$DBN" "$PN" -1; start "$DBI" "$PI" inf
for port in "$PN" "$PI"; do
  up=0; for i in $(seq 1 240); do
    curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && { up=1; break; }; sleep 0.5; done
  [ "$up" = 1 ] || { echo "service on $port did not start; see $W/svc-$port.log"; echo "RESULT: NO-DEFECT (setup failed: service)"; exit 0; }
done

ask() {  # ask PORT LABEL: prints the HTTP status, the answer's head, and the turn the service kept
  local O="http://127.0.0.1:$1" H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
  bh_project "$O" "$P" >/dev/null
  local code; code=$(curl -s --noproxy '*' -o "$W/ask-$1.body" -w '%{http_code}' -X POST "$O/api/ask" "${H[@]}" \
    -d '{"question":"Which scenarios does the project keep?","by":"bughunt"}')
  echo "## POST /api/ask, OPENFERMENT_ASK_BUDGET_USD=$2: HTTP $code"
  python3 - "$W/ask-$1.body" <<'PY'
import json, sys
raw = open(sys.argv[1]).read()
try:
    d = json.loads(raw)
    print(f"    answer: declined={d.get('declined')!r}")
except Exception:
    print(f"    answer: {raw[:120]!r}")
PY
  curl -s --noproxy '*' "$O/api/conversations" "${H[@]}" > "$W/conv-$1.json"
  python3 - "$W/conv-$1.json" <<'PY'
import json, sys
for c in json.load(open(sys.argv[1])):
    for t in c["turns"]:
        e = t.get("error") or {}
        print(f"    turn kept: status={t['status']!r} error={e.get('message')!r}")
PY
  echo "$code" > "$W/ask-$1.code"
}
ask "$PN" -1
ask "$PI" inf
echo "## the service's log on $PI (the exception the 500 hides):"
grep -E "^(OverflowError|ValueError)|Error: cannot convert" "$W/svc-$PI.log" | sort -u | sed 's/^/    /'
neg_code=$(cat "$W/ask-$PN.code"); inf_code=$(cat "$W/ask-$PI.code")
neg_declined=$(python3 -c 'import json,sys; print(bool(json.load(open(sys.argv[1])).get("declined")))' "$W/ask-$PN.body" 2>/dev/null)

echo "## the cause: spend._setting checks a parsed float for value < 0 alone, and nan < 0 and inf < 0 are both false"
bh_py -c 'import math, inspect; from openferment_core import spend
src = inspect.getsource(spend._setting)
print("    _setting tests finiteness:", any(w in src for w in ("isfinite", "isnan", "isinf")))
print("    float(\"nan\") < 0 =", float("nan") < 0, "; float(\"inf\") < 0 =", float("inf") < 0)'

# ── verdict ──
echo "EXPECTED: a daily cap or an ask budget of nan or inf is refused as BudgetSettingInvalid in words, as -1 is:" \
     "no call held against it, ready's spend row failing, the ask a 200 plan with declined set."
echo "OBSERVED: in process $caps_defects of 4 nan/inf cases taken as numbers of dollars (daily cap nan and inf each" \
     "hold a 1000 USD call and ready marks the row ok; ask budget nan and inf raise ValueError and OverflowError);" \
     "POST /api/ask answers HTTP $neg_code (declined: $neg_declined) at -1 and HTTP $inf_code at inf."
if [ "$caps_defects" -gt 0 ] || [ "${inf_code:0:1}" = 5 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
