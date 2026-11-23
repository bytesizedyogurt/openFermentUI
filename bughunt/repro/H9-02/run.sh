#!/usr/bin/env bash
# H9-02: the spend gate never proposes. With the day's cap too small for an extraction, intake_write
# extract at the tool door should become a spend proposal (tools/gates.py, docs/TOOLS.md's gate table);
# it answers an error and keeps no proposal. The model API is a loopback stand-in that answers every
# request with an error, so no request leaves the machine and nothing is spent; the key is a dummy.
#   bash bughunt/repro/H9-02/run.sh        (from the repository root)
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H9-02
PORT=9650; STANDIN=9651; DB=bh_r_h9_02_gate; P=pg
W="$BH_WORK/H9-02"; mkdir -p "$W"; REC="$W/standin.jsonl"; : > "$REC"
O="http://127.0.0.1:$PORT"

cleanup() {
  bh_svc_stop "$PORT" >/dev/null 2>&1
  pkill -f "standin_model_api.py $STANDIN" >/dev/null 2>&1
  bh_db_drop "$DB" >/dev/null 2>&1
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT

# 1. The stand-in model API, then the service over a fresh database with a cap of a tenth of a cent.
setsid python3 "$HERE/standin_model_api.py" "$STANDIN" "$REC" 400 </dev/null >/dev/null 2>&1 &
sleep 0.5
bh_db_fresh "$DB" || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }
data=$(bh_data "$DB")
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$data" \
    OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$PORT" \
    OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= OPENFERMENT_WORKSPACE_ID= \
    OPENFERMENT_DAILY_BUDGET_USD=0.001 ANTHROPIC_API_KEY=bh-dummy-not-a-key \
    ANTHROPIC_BASE_URL="http://127.0.0.1:$STANDIN" PYTHONDONTWRITEBYTECODE=1 \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$PORT" \
    --log-level warning < /dev/null > "$W/svc.log" 2>&1 &
)
up=0; for i in $(seq 1 240); do
  curl -sf --noproxy '*' "$O/api/health" >/dev/null 2>&1 && { up=1; break; }; sleep 0.5; done
[ "$up" = 1 ] || { echo "service did not start; see $W/svc.log"; echo "RESULT: NO-DEFECT (setup failed: service)"; exit 0; }

H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
bh_project "$O" "$P" >/dev/null

# 2. A pasted document, the one thing an extraction needs.
DOC=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" "${H[@]}" \
  -d '{"title":"Notes","text":"Yeast ferments glucose to ethanol. Xylose is not consumed.","by":"Tester Person"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["documentId"])')
echo "document: $DOC"

# 3. intake_write extract at the tool door, a person calling, then an outside assistant calling.
call() {
  curl -s --noproxy '*' -X POST "$O/api/tools/intake_write$1" "${H[@]}" "${@:2}" \
    -d "{\"action\":\"extract\",\"target\":\"$DOC\",\"fields\":{},\"note\":\"extract it\"}"
}
call '?by=Alice%20Person' > "$W/person.json"
call '' -H 'X-OpenFerment-Assistant: bughunt-client/0.1' > "$W/assistant.json"
show() {
  python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
s = d.get("summary") or {}
print(f"  summary.state={s.get('state')!r} gate={s.get('gate')!r} proposalId={s.get('proposalId')!r} "
      f"auditIds={d.get('auditIds')!r}")
print(f"  error={d.get('error')!r}")
PY
}
echo "## intake_write extract, ?by=Alice Person"; show "$W/person.json"
echo "## intake_write extract, X-OpenFerment-Assistant: bughunt-client/0.1"; show "$W/assistant.json"

# 4. What the project holds and what reached the model API.
curl -s --noproxy '*' "$O/api/proposals" "${H[@]}" > "$W/proposals.json"
echo "## GET /api/proposals: $(cat "$W/proposals.json")"
sent=$(wc -l < "$REC" | tr -d ' ')
echo "## model requests that reached the stand-in: $sent"
echo "## the cause: BudgetExhausted is a ModelUnavailable, so extract.call_model's except clause takes it"
bh_py -c 'from openferment_core import llm, extract; import inspect
print("  issubclass(llm.BudgetExhausted, llm.ModelUnavailable) =", issubclass(llm.BudgetExhausted, llm.ModelUnavailable))
src = inspect.getsource(extract.call_model)
print("  call_model re-raises ModelUnavailable as ExtractUnavailable:", "except llm.ModelUnavailable as e" in src and "raise ExtractUnavailable" in src)'

echo "EXPECTED: with the daily cap at 0.001 USD, each call answers summary.state 'proposed', gate 'spend', a proposalId and no error; GET /api/proposals lists the spend proposal Home shows with its button; no model request is sent"
python3 - "$W/person.json" "$W/assistant.json" "$W/proposals.json" "$sent" <<'PY2'
import json, sys
p, a, props = (json.load(open(f)) for f in sys.argv[1:4])
sent = sys.argv[4]
def gated(d):
    s = d.get("summary") or {}
    return s.get("state") == "proposed" and s.get("gate") == "spend" and not d.get("error")
def said(d):
    s = d.get("summary") or {}
    e = d.get("error") or ""
    cap = "the error names the daily cap" if "daily cap" in e else "no daily-cap words"
    return f"state={s.get('state')!r} gate={s.get('gate')!r} error={'set' if e else 'none'} ({cap})"
spend = [x for x in props if x.get("gate") == "spend"]
print(f"OBSERVED: person: {said(p)}; assistant: {said(a)}; spend proposals listed: {len(spend)} of {len(props)}; "
      f"model requests sent: {sent}")
print("RESULT: " + ("NO-DEFECT" if gated(p) and gated(a) and spend else "DEFECT"))
PY2
exit 0
