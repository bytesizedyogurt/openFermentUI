#!/usr/bin/env bash
# P-01: a route that names a local model alone fails with no Anthropic key, because llm._call builds the
# Anthropic client before it reads the route's provider; the local endpoint is never asked.
# A stub OpenAI-compatible endpoint on 127.0.0.1:9160 stands for the local model; 9161 is a dead port every
# proxy points at. A fresh database bh_r_p_01_<pid> backs the run (llm.call's local path reads none of it).
# Keyless, no model spend, nothing reaches api.anthropic.com (ANTHROPIC_BASE_URL points at the stub too).
# usage, from the repository root: bash bughunt/repro/P-01/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/P-01
STUB=9160
DEAD=9161
DB=bh_r_p_01_$$
T=$BH_WORK/P-01-run-$$; mkdir -p "$T"
STUB_PID=
cleanup() {
  [ -n "$STUB_PID" ] && kill "$STUB_PID" 2>/dev/null && wait "$STUB_PID" 2>/dev/null
  bh_db_drop "$DB"; rm -rf "$T"
}
trap cleanup EXIT

echo "EXPECTED: with OPENFERMENT_LOCAL_BASE_URL naming a local OpenAI-compatible endpoint and the explain route"
echo "EXPECTED: naming openai-compatible:local-stub alone, llm.call(family='explain') is answered by the local"
echo "EXPECTED: endpoint at no charge whatever ANTHROPIC_API_KEY holds (CLAUDE.md:104 'a local model ... which"
echo "EXPECTED: answers single calls through the kit's adapter'; core/openferment_core/llm.py:160-165)."

bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make the database $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
python3 "$HERE/stub_models.py" "$STUB" "$T/stub.jsonl" > "$T/stub.out" 2>&1 &
STUB_PID=$!
for i in $(seq 1 40); do
  curl -s --noproxy '*' -o /dev/null -X POST "http://127.0.0.1:$STUB/ping" -d '{}' && break; sleep 0.25
done
: > "$T/stub.jsonl"   # forget the readiness ping

probe() {  # probe ARM: one llm.call through the repository's Python, keyless; prints the probe's lines
  (cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     .venv/bin/python "$HERE/local_call.py" "$STUB" "$DEAD" "$@") 2>&1 | grep -E "^(route|ANSWERED|RAISED)"
}
count() { grep -c "\"path\": \"$1\"" "$T/stub.jsonl"; }

echo "--- arm 1: ANTHROPIC_API_KEY empty (a deployment with a local model alone)"
A1=$(probe); echo "$A1"
k_chat=$(count /v1/chat/completions); k_msg=$(count /v1/messages)
echo "stub saw: $k_chat POST /v1/chat/completions, $k_msg POST /v1/messages"
: > "$T/stub.jsonl"

echo "--- arm 2 (control): ANTHROPIC_API_KEY a placeholder that is never sent anywhere"
A2=$(probe placeholder); echo "$A2"
p_chat=$(count /v1/chat/completions); p_msg=$(count /v1/messages)
echo "stub saw: $p_chat POST /v1/chat/completions, $p_msg POST /v1/messages"

echo "--- where the order is set, and the test that pays the row"
grep -n "client = (client_factory or _default_client)()" "$BH_ROOT/core/openferment_core/llm.py"
grep -n "if provider == LOCAL:" "$BH_ROOT/core/openferment_core/llm.py"
grep -n "ANTHROPIC_API_KEY is not set" "$BH_ROOT/core/openferment_core/llm.py"
grep -n "client_factory=lambda: unasked" "$BH_ROOT/core/tests/test_llm.py"
echo "a caller that names no client_factory: extract.py:$(grep -n 'result = llm.call(' "$BH_ROOT/core/openferment_core/extract.py")"

echo "OBSERVED: keyless arm: $(echo "$A1" | grep -E '^(ANSWERED|RAISED)'); the stub was asked $k_chat time(s)"
echo "OBSERVED: placeholder arm: $(echo "$A2" | grep -E '^(ANSWERED|RAISED)'); the stub was asked $p_chat time(s), Anthropic path $p_msg"
if echo "$A1" | grep -q "^RAISED ModelUnavailable: ANTHROPIC_API_KEY is not set" && [ "$k_chat" = 0 ] \
   && echo "$A2" | grep -q "^ANSWERED openai-compatible:local-stub cost=0.0" && [ "$p_chat" = 1 ] && [ "$p_msg" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
