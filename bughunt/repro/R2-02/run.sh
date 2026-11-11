#!/usr/bin/env bash
# R2-02: `conform biosteam` against an address whose server answers and holds no such database makes its
# checks, prints why the verdict could not be kept, says "every check holds" and exits 0, where
# `migrations migrate` refuses the same address in words with exit 2.
# Run from the repository root: bash bughunt/repro/R2-02/run.sh
#
# Keyless (bh_env), no model call, nothing under core/ written: the main checkout's own Python runs conform with
# its scratch prefix set in the process (conform.SCRATCH, read by _scratch) so the checks' own database is a
# bh_r_r2_02_cf_* one; PYTHONDONTWRITEBYTECODE, a private data directory and a numba cache under
# $BH_WORK/R2-02 keep every write outside the repository. Steps:
#   0. the contract's words, read from the pages (engines.md, PROGRESS.md D0.7, the two modules' docstrings);
#   1. a fresh migrated database bh_r_r2_02_cfg (the server answers) and bh_r_r2_02_missing made absent;
#   2. migrations migrate, conform biosteam and conform train --project p, each with OPENFERMENT_DATABASE_URL
#      naming bh_r_r2_02_missing; conform train --project p on bh_r_r2_02_cfg as the control.
# The verdict holds the commands to what the pages say. Every bh_r_r2_02_* database is dropped at the end.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
TAG="$(date +%s)-$$"
BASE="$BH_WORK/R2-02"
OUT="$BASE/out-$TAG"
CFG=bh_r_r2_02_cfg
MISSING=bh_r_r2_02_missing
PREFIX=bh_r_r2_02_cf
ENG="$BH_ROOT/docs/api/engines.md"
PROG="$BH_ROOT/docs/PROGRESS.md"

drop_ours() {
  local n
  for n in $(psql "$BH_SERVER/postgres" -AtqXc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_r2\_02\_%'"); do
    bh_db_drop "$n"
  done
}
cleanup() { drop_ours; rm -rf "$OUT"; }
trap cleanup EXIT
mkdir -p "$OUT" "$BASE/numba-cache"
cp -R "$BH_DATA_SRC" "$OUT/data"
verdict() { echo "EXPECTED: $1"; echo "OBSERVED: $2"; echo "RESULT: $3"; exit 0; }

# The repository's Python from core/, keyless, writing nothing under core/.
py() {
  (cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR="$BASE/numba-cache" \
     OPENFERMENT_DATA_DIR="$OUT/data" OPENFERMENT_SFF_LIBRARY="$OUT/data/sff-library" "$@" < /dev/null)
}
# conform with its scratch prefix set in the process; the arguments are conform's own.
conform() {
  local url="$1"; shift
  py OPENFERMENT_DATABASE_URL="$url" timeout 1500 .venv/bin/python -c \
    "import sys; from openferment_core.engine import conform; conform.SCRATCH='$PREFIX'; sys.exit(conform.main(sys.argv[1:]))" "$@"
}

echo "== 0. the contract, as the pages and the modules say it"
grep -n -F 'and `conform` the PostgreSQL server' "$ENG" | cut -c1-140
sed -n 114p "$ENG" | sed 's/^/114:/' | cut -c1-140
grep -n -F 'keeps its verdict in that address' "$ENG" | cut -c1-140
grep -n -F 'keep is printed with the words why' "$ENG" | cut -c1-140
grep -n -F 'says so in words naming `OPENFERMENT_DATABASE_URL`, and exits 2.' "$ENG" | cut -c1-140
grep -n -A2 -F '`conform` with no database (D0.7, A20)' "$PROG" | cut -c1-140
grep -n -A1 -F '`python -m openferment_core.migrations` (R4)' "$PROG" | cut -c1-140
grep -n -A1 -F 'fails, and 2, in words naming OPENFERMENT_DATABASE_URL' "$BH_ROOT/core/openferment_core/engine/conform.py" | cut -c1-140
grep -n -A1 -F 'production database named, a server that does not answer' "$BH_ROOT/core/openferment_core/migrations.py" | cut -c1-140

echo "== 1. the databases"
drop_ours
bh_db_fresh "$CFG" 2>/dev/null || verdict "a fresh database $CFG" "bh_db_fresh failed" NO-DEFECT
held=$(psql "$BH_SERVER/postgres" -AtqXc "SELECT count(*) FROM pg_database WHERE datname = '$MISSING'")
echo "$CFG made fresh and migrated (the server answers); databases named $MISSING on the server: $held"
[ "$held" = 0 ] || verdict "no database $MISSING" "one is held" NO-DEFECT

echo "== 2a. migrations migrate, OPENFERMENT_DATABASE_URL naming $MISSING"
py OPENFERMENT_DATABASE_URL="$BH_SERVER/$MISSING" .venv/bin/python -m openferment_core.migrations migrate > "$OUT/mig.out" 2>&1; xm=$?
tail -1 "$OUT/mig.out" | cut -c1-220; echo "exit $xm"

echo "== 2b. conform biosteam, OPENFERMENT_DATABASE_URL naming $MISSING (the checks build a plant: minutes)"
t0=$(date +%s)
conform "$BH_SERVER/$MISSING" biosteam > "$OUT/cb.out" 2>&1; xb=$?
grep -v '^     ' "$OUT/cb.out" | grep -v '^$' | cut -c1-220
echo "exit $xb ($(( $(date +%s) - t0 )) s)"
left=$(psql "$BH_SERVER/postgres" -AtqXc "SELECT count(*) FROM pg_database WHERE datname LIKE 'bh\_r\_r2\_02\_cf\_%'")
echo "checks' databases ($PREFIX*) left on the server after it: $left"

echo "== 2c. conform train --project p, OPENFERMENT_DATABASE_URL naming $MISSING"
conform "$BH_SERVER/$MISSING" train --project p > "$OUT/ct.out" 2>&1; xt=$?
grep -v '^$' "$OUT/ct.out" | cut -c1-400; echo "exit $xt"
echo "== 2d. the control: conform train --project p, OPENFERMENT_DATABASE_URL naming $CFG (migrated, no project p)"
conform "$BH_SERVER/$CFG" train --project p > "$OUT/cc.out" 2>&1; xc=$?
grep -v '^$' "$OUT/cc.out" | cut -c1-220; echo "exit $xc"

# ── the verdict, held to the pages ──
mig_ok=0; grep -q "holds no database $MISSING" "$OUT/mig.out" && grep -q 'pnpm db:reset' "$OUT/mig.out" && [ "$xm" = 2 ] && mig_ok=1
said=0; grep -q '^! the verdict could not be kept for GET /api/engines: .*database "'"$MISSING"'" does not exist' "$OUT/cb.out" && said=1
rows=$(grep -cE '^(✓|✗) [1-8] ' "$OUT/cb.out"); ran=0; [ "$rows" -ge 8 ] && ran=1
code_ok=0
{ grep -q ': every check holds$' "$OUT/cb.out" && [ "$xb" = 0 ]; } && code_ok=1
{ grep -q ': a check fails$' "$OUT/cb.out" && [ "$xb" = 1 ]; } && code_ok=1
tr_ok=0; [ "$xt" = 2 ] && grep -q 'OPENFERMENT_DATABASE_URL' "$OUT/ct.out" && grep -q "database \"$MISSING\" does not exist" "$OUT/ct.out" && tr_ok=1
ctl_ok=0; [ "$xc" = 2 ] && grep -q "holds no project 'p'" "$OUT/cc.out" && ctl_ok=1
advice=0; grep -q 'Start it (pnpm db:up)' "$OUT/ct.out" && advice=1
echo "== the reading"
echo "migrations refuse in words with db:reset, exit 2: $mig_ok; conform made its eight checks: $ran;" \
     "printed why the verdict was not kept (the missing database named): $said; its exit follows its checks: $code_ok;" \
     "--project refused in words naming the setting and the missing database, exit 2: $tr_ok (control: $ctl_ok);" \
     "--project's words end with 'Start it (pnpm db:up)' for a server that answers: $advice"
EXP="engines.md:805-808 and 113-115 hold conform to a server alone: the checks run on the server the address names, the verdict is kept once the named database is migrated, a verdict it cannot keep is printed with the words why, exit 1 on a failed check and 2 only for no address or a server that does not answer (PROGRESS.md D0.7); migrations alone refuse a database the server does not hold, exit 2 with pnpm db:reset (PROGRESS.md R4)"
OBS="migrations exit $xm; conform biosteam exit $xb, $rows check rows printed, the verdict's failure printed naming database $MISSING, '$(grep -o 'every check holds\|a check fails' "$OUT/cb.out" | head -1)'; conform train --project p exit $xt naming OPENFERMENT_DATABASE_URL and the missing database"
if [ "$mig_ok$ran$said$code_ok$tr_ok$ctl_ok" = 111111 ]; then
  verdict "$EXP" "$OBS: each command does what its page says" NO-DEFECT
fi
verdict "$EXP" "$OBS: flags mig=$mig_ok ran=$ran said=$said code=$code_ok train=$tr_ok control=$ctl_ok" DEFECT
