#!/usr/bin/env bash
# H8-01: a pasted text one letter's case apart from a held one ("2000 mg" against "2000 Mg") is
# answered `linked`, and the project's passages read the other project's "2000 Mg".
#   bash bughunt/repro/H8-01/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, the head's service on 127.0.0.1:10240 (keyless), two pastes and a control,
# the kit's own chunk rows read back, then the service stopped and the database dropped.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
HERE=/home/user/openFermentUI/bughunt/repro/H8-01
DB=bh_r_h8_01_case
PORT=""
for p in $(seq 10240 10249); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 10240-10249"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log" "$BH_WORK/svc-$PORT.pid"; }
trap cleanup EXIT

ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "the service did not start"; tail -20 "$BH_WORK/svc-$PORT.log"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN  database: $DB (fresh)"

OUT=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/probe.py" "$ORIGIN" 2>&1)
echo "$OUT"

# What the kit stored, read with psql: every chunk row holding "2000 ?g", case kept as stored.
echo "the kit's chunk rows (sci_rag.chunks) naming 2000 of a gram unit:"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "select substring(content from '2000 [A-Za-z]g') as unit, count(*) from sci_rag.chunks
    where content ~* '2000 [a-z]g' group by 1 order by 1" | sed 's/^/  /'
LOWER=$(psql "$BH_SERVER/$DB" -qXAt -c "select count(*) from sci_rag.chunks where content like '%2000 mg%'")
echo "chunk rows holding rb's own words \"2000 mg\": $LOWER"

echo "EXPECTED: rb's \"... 2000 mg ...\" is other text from ra's \"... 2000 Mg ...\" (docs/api/intake.md:53, linked means the kit held the same text): rb's paste is ingested as a document of its own and rb's passage reads \"2000 mg\"."
if echo "$OUT" | grep -q '^VERDICT: DEFECT' && [ "$LOWER" = 0 ]; then
  echo "OBSERVED: rb's paste is answered linked to ra's document; rb's passage and search read ra's \"2000 Mg\" (a unit 10^9 times rb's), and no chunk row holds rb's \"2000 mg\"; the control one word apart (\"2000 kg\") is ingested as its own."
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: rb's paste kept its own words, or the steps did not complete (see the lines above)."
  echo "RESULT: NO-DEFECT"
fi
exit 0
