#!/usr/bin/env bash
# H8-04: a JATS XML upload declaring ISO-8859-1 is decoded as UTF-8 with replacement and ingested without
# a word, its "5 µg/L ... 30 °C" kept as "5 \ufffdg/L ... 30 \ufffdC"; the same Latin-1 bytes as Markdown
# are refused in words.
#   bash bughunt/repro/H8-04/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, the head's service on 127.0.0.1:9050-9059 (keyless, no model call), three
# uploads, the kit's chunk rows read back with psql, then the service stopped and the database dropped.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
HERE=/home/user/openFermentUI/bughunt/repro/H8-04
DB=bh_r_h8_04_latin1
PORT=""
for p in $(seq 9050 9059); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9050-9059"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log" "$BH_WORK/svc-$PORT.pid"; }
trap cleanup EXIT

ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "the service did not start"; tail -20 "$BH_WORK/svc-$PORT.log"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN  database: $DB (fresh)"

OUT=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/probe.py" "$ORIGIN" 2>&1)
echo "$OUT"

# What the kit stored: chunk rows of the furfural sentence, with U+FFFD or with the micro sign.
BAD=$(psql "$BH_SERVER/$DB" -qXAt -c "select count(*) from sci_rag.chunks where content like '%furfural%' and content like '%' || U&'\FFFD' || 'g/L%'")
GOOD=$(psql "$BH_SERVER/$DB" -qXAt -c "select count(*) from sci_rag.chunks where content like '%furfural%' and content like '%' || U&'\00B5' || 'g/L%'")
echo "the kit's chunk rows (sci_rag.chunks) of the sentence: with U+FFFD before g/L: $BAD; with the micro sign: $GOOD"

echo "EXPECTED: the XML read in the encoding it declares, its passage keeping \"5 µg/L of furfural at 30 °C\", or the file refused in words (status failed with a reason) as the Markdown door refuses the same Latin-1 bytes (docs/api/intake.md:17, :52-54)."
if echo "$OUT" | grep -q '^VERDICT: DEFECT' && [ "$BAD" -ge 1 ] && [ "$GOOD" -ge 1 ]; then
  echo "OBSERVED: assay.xml is answered ingested with no reason, and the project and the kit's chunk rows keep \"5 \\ufffdg/L of furfural at 30 \\ufffdC\" (the units lost); the same bytes as assay.md are answered failed in words; the UTF-8 control keeps \"5 µg/L\"."
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: the Latin-1 XML kept its units or was refused in words, or the steps did not complete (see the lines above)."
  echo "RESULT: NO-DEFECT"
fi
exit 0
