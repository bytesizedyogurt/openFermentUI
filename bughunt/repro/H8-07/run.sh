#!/usr/bin/env bash
# H8-07: the project retrieval report's kit rule (literature/report.py _retrieval) counts a passage of another
# document as relevant when that document shares the question's document title.
#   bash bughunt/repro/H8-07/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, the head's service on 127.0.0.1:10330 (keyless), two documents pasted through Intake
# with the one title "Strain report", one candidate kept on A by hand, then `literature_live report --project`
# over interactive, vector_only and keyword_only (no judge, no --render: no model call, no committed file
# written). The kept run is read for the one question built from A's candidate.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1
unset OPENFERMENT_FIXTURES OPENFERMENT_FIXTURE_DIR
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h8_07_title
PORT=10330
PROJECT=h8-07
HERE=/home/user/openFermentUI/bughunt/repro/H8-07
SCRATCH="$BH_WORK/H8-07"
cleanup() {
  bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$SCRATCH" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"
}
trap cleanup EXIT
no_result() { echo "RESULT: NO-DEFECT ($1)"; exit 0; }

mkdir -p "$SCRATCH/data"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { cat "$BH_WORK/svc-$PORT.log" 2>/dev/null | tail -20; no_result "the service did not start"; }
echo "database: $DB (fresh, migrated to head); service: $ORIGIN"

PASTED=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/probe.py" paste "$ORIGIN" "$PROJECT" 2>&1)
echo "$PASTED"
A=$(echo "$PASTED" | awk '$1=="doc" && $2=="A" {print $3}')
[ -n "$A" ] || no_result "document A was not pasted"

(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$SCRATCH/data" \
   .venv/bin/python -I "$HERE/probe.py" candidate "$PROJECT" "$A") 2>&1 | grep -E '^candidate:'

OUT=$(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$SCRATCH/data" \
        .venv/bin/python -I -m openferment_core.literature_live report --project "$PROJECT" --by h8-07 \
        --configs interactive,vector_only,keyword_only 2>"$SCRATCH/report.err" | tail -1)
FILE=$(echo "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["file"])' 2>/dev/null)
[ -n "$FILE" ] && [ -f "$FILE" ] || { tail -20 "$SCRATCH/report.err"; no_result "the report kept no run"; }
echo "report: $(echo "$OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("questions", d["questions"], "stopped", d["stopped"], "usd", d["cost"]["total"])')"

V=$(python3 "$HERE/probe.py" verdict "$FILE" "$BH_SERVER/$DB" 2>&1)
echo "$V" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo
echo "$V" | grep -E '^(EXPECTED|OBSERVED):'
echo "$V" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the verdict did not complete; see the lines above)"
exit 0
