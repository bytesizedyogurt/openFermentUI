#!/usr/bin/env bash
# H10-02: a NUL character (U+0000) in a path id, a query filter or a body text field answers a bare
# 500 "Internal Server Error" at /api doors over text columns and at two /rag doors, where the
# runbook, artifact and catalogue doors answer the same id with a 404 in words.
#   bash bughunt/repro/H10-02/run.sh            (from the repository root)
# Fresh database bh_r_h10_02_svc, the service on 127.0.0.1:9960, keyless, no model call. The /rag
# mount gets a throwaway local key in the service's environment so its doors are reached at all.
set -u
export PGOPTIONS="-c client_min_messages=warning"
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
HERE="$BH_ROOT/bughunt/repro/H10-02"
DB=bh_r_h10_02_svc; PORT=9960; O="http://127.0.0.1:$PORT"; LOG="$BH_WORK/svc-$PORT.log"
RAG_KEY="bh-h10-02-throwaway-rag-key"
OUT="$BH_WORK/H10-02"; mkdir -p "$OUT"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$OUT" "$BH_WORK/data-$DB"; }
trap cleanup EXIT
cleanup; mkdir -p "$OUT"

echo "tree: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ src/ scripts/ examples/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core src scripts examples && echo yes || echo NO)"
export OPENFERMENT_RAG_KEY="$RAG_KEY"
bh_svc_start "$DB" "$PORT" >/dev/null || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
unset OPENFERMENT_RAG_KEY
echo "service on $O over fresh database $DB"
echo "project r1: $(bh_project "$O" r1 | cut -c1-80)"
echo

bh_py "$HERE/probe.py" "$O" r1 "$RAG_KEY" > "$OUT/probe.txt" 2>&1
grep -v '^SUMMARY ' "$OUT/probe.txt"
echo
echo "-- after the probe (what the 500s left behind)"
for id in r1 nul-name nul-by nul-desc; do
  printf '  GET /api/projects/%-9s %s\n' "$id" "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "$O/api/projects/$id")"
done
echo
echo "-- the service's log"
NUL_ERRS=$(grep -c 'CharacterNotInRepertoireError' "$LOG")
echo "  lines naming asyncpg's CharacterNotInRepertoireError: $NUL_ERRS"
grep -m1 'CharacterNotInRepertoireError' "$LOG" | cut -c1-160 | sed 's/^/  first: /'
echo "  what the handlers map (core/openferment_core/api.py:424-426):"
sed -n 424,426p core/openferment_core/api.py | sed 's/^/    /'
echo
echo "-- the contract"
sed -n 208p core/openferment_core/api.py | sed 's/^/  core\/openferment_core\/api.py:208: /'
grep -n 'a refusal is a 422 in words' CLAUDE.md | sed 's/^/  CLAUDE.md:/'
python3 - <<'PY'
import json
d = json.load(open("docs/api/openapi.json"))
print("  openapi.json GET /api/runs/{run_id} 404:", d["paths"]["/api/runs/{run_id}"]["get"]["responses"]["404"]["description"][:48])
PY

python3 - "$OUT/probe.txt" "$NUL_ERRS" > "$OUT/verdict.txt" <<'PY'
import json, sys
rows = json.loads([l for l in open(sys.argv[1]) if l.startswith("SUMMARY ")][0][8:])
nul_errs = int(sys.argv[2])
ctl = [r for r in rows if r["group"] == "control"]
api = [r for r in rows if r["group"] == "api"]
rag = [r for r in rows if r["group"] == "rag"]
ctl_ok = all(400 <= r["status"] < 500 and r["worded"] for r in ctl)
api_bare = [r for r in api if r["status"] >= 500 and not r["worded"]]
rag_bare = [r for r in rag if r["status"] >= 500]
bare_text = all(r["body"].strip() == "Internal Server Error" for r in api_bare)
ctl_words = ", ".join(f"{r['status']}" for r in ctl)
print(f"EXPECTED: a NUL-bearing id the project does not hold answers a 404 in words and a NUL-bearing filter or text field a 422 in words at every door (api.py:208 'A refusal is a status with its reason in `detail`, in words.'), as the five controls answer: {ctl_words}, each with a detail in words")
print(f"OBSERVED: {len(api_bare)} of {len(api)} /api doors answer 500 with the bare body 'Internal Server Error' (bare text at each: {bare_text}); {len(rag_bare)} of {len(rag)} /rag doors answer 500; the service log names CharacterNotInRepertoireError {nul_errs} times; the controls answer in words: {ctl_ok}")
defect = ctl_ok and len(api_bare) >= 1 and bare_text and nul_errs >= 1
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
echo
cat "$OUT/verdict.txt"
exit 0
