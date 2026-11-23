#!/usr/bin/env bash
# H3-16: a unit written with the Greek small letter mu (U+03BC) does not normalise, so a candidate copying
# "μg/mL" as the paper wrote it is refused on rule 'unit'; the micro sign (U+00B5) spelling anchors.
#   bash bughunt/repro/H3-16/run.sh        (from the repository root; exits 0 either way)
# A fresh test database bh_r_h3_16_svc, a keyless service on the first free port of 9200..9209 (no worker,
# no model call), project h3-16, two pasted one-sentence documents and three biorepo_write candidates at
# the HTTP tool door (repro.py); the unit engine on each spelling; the browser's normalizeUnit on the same
# spellings (read only, through tsx); the contract lines as the tree writes them. No worktree is needed:
# nothing is mutated or built. The service is stopped, the database dropped and its data copy removed on exit.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_16_svc
HERE=/home/user/openFermentUI/bughunt/repro/H3-16
PORT=""

mine_on() {
  local pid; pid=$(bh_port_pid "$1"); [ -n "$pid" ] || return 1
  tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -qx "OPENFERMENT_DATABASE_URL=$BH_SERVER/$DB"
}
cleanup() {
  if [ -n "$PORT" ] && mine_on "$PORT"; then bh_svc_stop "$PORT"; fi
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
  [ -n "$PORT" ] && rm -f "$BH_WORK/svc-$PORT.log"
}
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head); tree at $(git -C "$BH_ROOT" rev-parse --short HEAD), core/ and src/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core src && echo yes || echo no)"
O=""
for p in $(seq 9200 9209); do
  [ -n "$(bh_port_pid "$p")" ] && continue
  if o=$(BH_KEEP_DB=1 bh_svc_start "$DB" "$p") && mine_on "$p"; then PORT=$p; O=$o; break; fi
done
[ -n "$O" ] || { echo "no service could start on 9200-9209"; echo "RESULT: NO-DEFECT (no service)"; exit 0; }
echo "service: $O over $DB (keyless)"

echo
echo "== the contract lines, as written =="
grep -n "The table key for a unit as somebody wrote it" "$BH_ROOT/core/openferment_core/units.py"
grep -n "never translate a unit" "$BH_ROOT/core/openferment_core/extract.py"
grep -n "Give the unit as the paper wrote it" "$BH_ROOT/core/openferment_core/extract.py"
grep -n '"The unit as the paper wrote it' "$BH_ROOT/core/openferment_core/extract.py"
sed -n '1137,1140p' "$BH_ROOT/core/openferment_core/validate.py" | nl -ba -v1137 -w4 -s': '
echo "the fold the engine applies before comparing keys (units.py:91-101), U+03BC absent from it:"
sed -n '91,101p' "$BH_ROOT/core/openferment_core/units.py" | nl -ba -v91 -w4 -s': '
for f in core/openferment_core/units.py core/openferment_core/schema/units.json src/engine/units.ts; do
  echo "lines holding U+03BC in $f: $(grep -c $'μ' "$BH_ROOT/$f"); holding U+00B5: $(grep -c $'µ' "$BH_ROOT/$f")"
done
echo "a live extraction emitted the Greek-mu spelling (core/tests/test_units_minus.py, the units of dropped values):"
grep -n $'colonies/μg DNA' "$BH_ROOT/core/tests/test_units_minus.py"

echo
OUT=$(bh_py "$HERE/repro.py" "$O" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo
echo "== the browser's engine on the same spellings (src/engine/units.ts, read only) =="
(cd "$BH_ROOT" && timeout 120 node_modules/.bin/tsx "$HERE/browser.mts" 2>&1) || echo "  (tsx did not run)"
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
