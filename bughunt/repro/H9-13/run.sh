#!/usr/bin/env bash
# H9-13: a lone surrogate escape ("\ud800") in a string a tool echoes answers a bare 500 at the REST tool door.
# The head's own service on a fresh database, port 10410; keyless, no model call.
# usage, from the repository root: bash bughunt/repro/H9-13/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h9_13_svc
PORT=10410
P=h913
T=$BH_WORK/H9-13; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: each call below answers a ToolResult with its refusal in error, or a 4xx whose detail says in words"
echo "EXPECTED: why (tools/__init__.py:501-503 'Every refusal is a result with \`error\` set; nothing here raises';"
echo "EXPECTED: api.py:208 'A refusal is a status with its reason in \`detail\`, in words'), whether a string field"
echo "EXPECTED: holds 'ab' or the JSON escape 'a\\ud800b' (a lone surrogate UTF-8 cannot carry)."

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null

# tool | body template, PLACE standing where the string goes
CASES=(
  'search_records|{"query":PLACE,"field":"x","organism":"x","limit":5}'
  'search_records|{"query":"x","field":PLACE,"organism":"x","limit":5}'
  'search_records|{"query":"x","field":"x","organism":PLACE,"limit":5}'
  'search_passages|{"query":PLACE,"k":1}'
  'yield_ceiling|{"modelId":"x","product":PLACE,"substrate":"x"}'
  'selling_price|{"scenarioId":PLACE}'
  'run_flowsheet|{"scenarioId":PLACE}'
)
post() {  # post TOOL BODY -> "STATUS<TAB>first 160 chars of the answer"
  curl -s --noproxy '*' -o "$T/ans" -w '%{http_code}' -X POST "$O/api/tools/$1?by=H9-13%20repro" \
    -H "X-OpenFerment-Project: $P" -H 'content-type: application/json' --data-binary "$2" > "$T/code"
  printf '%s\t%s\n' "$(cat "$T/code")" "$(head -c 160 "$T/ans" | tr '\n' ' ')"
}
bad=0; ctl_ok=0; n=0
for c in "${CASES[@]}"; do
  tool=${c%%|*}; tpl=${c#*|}; n=$((n+1))
  ctl=$(post "$tool" "${tpl/PLACE/\"ab\"}")
  sur=$(post "$tool" "${tpl/PLACE/\"a\\ud800b\"}")
  field=$(printf '%s' "$tpl" | sed -E 's/.*"([A-Za-z]+)":PLACE.*/\1/')
  echo "CASE $tool $field='ab'        -> ${ctl}"
  echo "CASE $tool $field='a\\ud800b'  -> ${sur}"
  [ "${ctl%%	*}" = 200 ] && ctl_ok=$((ctl_ok+1))
  code=${sur%%	*}; text=${sur#*	}
  if [ "$code" -ge 500 ] && ! printf '%s' "$text" | grep -q '"detail"\|"error"'; then bad=$((bad+1)); fi
done
echo "service log, the failure behind the 500s:"
grep -m2 -E "PydanticSerializationError|UnicodeEncodeError" "$BH_WORK/svc-$PORT.log" | cut -c1-220 | sed 's/^/  /'
logged=$(grep -c "UnicodeEncodeError" "$BH_WORK/svc-$PORT.log")
echo "OBSERVED: $ctl_ok of $n calls with 'ab' answered 200 with a ToolResult; $bad of $n calls with 'a\\ud800b' answered"
echo "OBSERVED: a 5xx with no detail and no error in words ('Internal Server Error'); the service log names"
echo "OBSERVED: UnicodeEncodeError $logged time(s) (the answer could not be encoded as UTF-8 after tools.run returned)."
if [ "$bad" -gt 0 ] && [ "$ctl_ok" -gt 0 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
