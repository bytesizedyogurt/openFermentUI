#!/usr/bin/env bash
# H2-08: a comparison asked again with a title of spaces loses the title it was kept with.
# The head's own service on a fresh database, port 10090; keyless, no model call, no network.
# usage, from the repository root: bash bughunt/repro/H2-08/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H2-08
DB=bh_r_h2_08_svc
PORT=10090
P=h208
T=$BH_WORK/H2-08; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: ComparisonCreate holds a title to min_length 1 (core/openferment_core/models.py:4809), so a title of"
echo "EXPECTED: three spaces asked again over two runs already compared is refused in words (a 422), or the"
echo "EXPECTED: comparison keeps the title it was kept with ('default beside measured')."

O=$(BH_FIXTURES=1 bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null
python3 -I "$HERE/repro.py" "$O" "$P" | tee "$T/out.log"

cid=$(sed -n 's/^COMPARISON_ID //p' "$T/out.log")
row=$(psql "$BH_SERVER/$DB" -AtXc "select format('created_by %L, body title %L, body by %L', created_by, body->>'title', body->>'by') from openferment.comparisons where project_id='$P' and id='$cid'")
echo "OBSERVED: the comparisons row $cid holds $row"
echo "OBSERVED: $(grep '^CASE asked again' "$T/out.log" | sed 's/^CASE //')"
echo "OBSERVED: $(grep '^CASE read back' "$T/out.log" | sed 's/^CASE //')"
if grep -q '^VERDICT DEFECT' "$T/out.log"; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
