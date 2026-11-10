#!/usr/bin/env bash
# H6-03: `pnpm db:import-alpha1` answers a Python traceback and exits 1, with no line beginning `refused:`,
# for three inputs: an alpha 1.0 data directory holding two extraction files of one paper, a configured
# database its server does not hold, and a server that does not answer. `pnpm db:migrate` names the last two
# in words (refused:, exit 2).
# The import's command (package.json: `cd core && uv run --frozen python -m openferment_core.import_alpha1`)
# runs here as `python -m openferment_core.import_alpha1` from core/ of a worktree of 2047f5a made by this
# run, on the repository's venv (uv run would sync a venv; the worktree holds no core/.env, so nothing is
# read from one). The data directories are written by alpha 1.0's own models (gen.py beside this file).
#   bash bughunt/repro/H6-03/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
R=$BH_ROOT/bughunt/repro/H6-03
DB=bh_r_h6_03_dup                    # a fresh database migrated to head
ABSENT=bh_r_h6_03_absent             # a name the server holds no database under
DEAD=9729                            # a port nothing listens on
S=$BH_WORK/H6-03; mkdir -p "$S"
WT=$S/wt-$$                          # 2047f5a's tree, this run's own
T=$(mktemp -d "$S/run.XXXXXX")       # this run's data and answers
cleanup() {
  bh_db_drop "$DB"; bh_db_drop "$ABSENT"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree list --porcelain | grep -qx "worktree $WT" && { rm -rf "$WT"; git -C "$BH_ROOT" worktree prune; }
  rm -rf "$T" "$WT"
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }
[ -z "$(bh_port_pid "$DEAD")" ] || fail "port $DEAD is taken"

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
[ -e "$WT/core/.env" ] && fail "the worktree holds a core/.env"
echo "module: $(cd "$WT/core" && bh_env .venv/bin/python -c 'import openferment_core.import_alpha1 as m; print(m.__file__)')"

git -C "$BH_ROOT" show alpha-1.0:core/openferment_core/models.py > "$T/models-a1.py" || fail "alpha 1.0's models"
bh_env "$BH_ROOT/core/.venv/bin/python" -I "$R/gen.py" "$T/models-a1.py" "$T/data" | sed 's/^/alpha 1.0 data /' \
  || fail "gen.py"
cmp -s "$T/data/dup/candidates/P1.json" "$T/data/dup/candidates/P1 copy.json" && echo "alpha 1.0 data dup: the two files hold the same bytes (paperId P1)"
BH_ROOT=$WT bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "database $DB (fresh): openferment at $(psql "$BH_SERVER/$DB" -XAtc 'select version_num from openferment.alembic_version')"
bh_db_drop "$ABSENT"
echo "database $ABSENT on the server: $(psql "$BH_SERVER/postgres" -XAtc "select count(*) from pg_database where datname='$ABSENT'") (none held)"

declare -A RC
imp() {  # imp CASE URL DATA
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$2" .venv/bin/python -m openferment_core.import_alpha1 \
      --name "Repro H6-03 $1" --by "Ada Moreno" --data "$3") > "$T/$1.out" 2>&1
  RC[$1]=$?
  echo "import $1: exit ${RC[$1]}; $(grep -c '^refused:' "$T/$1.out") refused: lines; $(grep -c '^Traceback' "$T/$1.out") tracebacks; last line: $(tail -1 "$T/$1.out" | sed "s|$T/||" | cut -c1-170)"
}
mig() {  # mig URL: pnpm db:migrate's command on URL
  local out rc; out=$(cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$1" .venv/bin/python -m openferment_core.migrations migrate 2>&1); rc=$?
  echo "exit $rc: $(echo "$out" | tail -1 | cut -c1-200)"
}
verdict() {  # verdict CASE: DEFECT when the answer is anything beside a refused: line and exit 2
  if [ "${RC[$1]}" = 2 ] && grep -q '^refused:' "$T/$1.out" && ! grep -q '^Traceback' "$T/$1.out"; then echo ok; else echo DEFECT; fi
}

echo
echo "== 1. two extraction files of one paper, into $DB"
imp dup "$BH_SERVER/$DB" "$T/data/dup"
grep 'import_alpha1.py", line' "$T/dup.out" | tail -1 | sed "s|$WT/||; s/^ */  the import's last frame: /"
grep -m1 'UniqueViolationError' "$T/dup.out" | cut -c1-170 | sed 's/^ */  the error: /'
grep -m1 'DETAIL:' "$T/dup.out" | sed 's/^ */  /'
echo "  rows written: $(psql "$BH_SERVER/$DB" -XAtc "select (select count(*) from openferment.projects) || ' projects, ' || (select count(*) from openferment.candidates) || ' candidate rows'")"
echo "  control, the same directory without the copy:"
imp one "$BH_SERVER/$DB" "$T/data/one"; sed -n '1p' "$T/one.out" | sed "s|$T/||; s/^/  /"

echo
echo "== 2. a database the server does not hold ($BH_SERVER/$ABSENT)"
imp absent "$BH_SERVER/$ABSENT" "$T/data/one"
grep -m1 'does not exist' "$T/absent.out" | cut -c1-170 | sed 's/^ */  the error: /'
echo "  pnpm db:migrate on the same address: $(mig "$BH_SERVER/$ABSENT")"

echo
echo "== 3. a server that does not answer (127.0.0.1:$DEAD)"
imp dead "postgresql://openferment:openferment@127.0.0.1:$DEAD/bh_r_h6_03_x" "$T/data/one"
echo "  pnpm db:migrate on the same address: $(mig "postgresql://openferment:openferment@127.0.0.1:$DEAD/bh_r_h6_03_x")"

echo
V1=$(verdict dup) V2=$(verdict absent) V3=$(verdict dead)
echo "EXPECTED: each of the three answers one line beginning refused: in words and exits 2, writing nothing" \
     "(docs/runbooks/live-host-install.md:218-219 'A line beginning \`refused:\` says why, and the import has written nothing');" \
     "the duplicate named by its second file, the database and the server named as pnpm db:migrate names them"
echo "OBSERVED: two files of one paper: exit ${RC[dup]}, $(grep -c '^refused:' "$T/dup.out") refused: lines, $(grep -c '^Traceback' "$T/dup.out") tracebacks ($V1);" \
     "no database: exit ${RC[absent]}, $(grep -c '^refused:' "$T/absent.out") refused: lines, $(grep -c '^Traceback' "$T/absent.out") tracebacks ($V2);" \
     "no server: exit ${RC[dead]}, $(grep -c '^refused:' "$T/dead.out") refused: lines, $(grep -c '^Traceback' "$T/dead.out") tracebacks ($V3);" \
     "control (one file): exit ${RC[one]}"
if [ "${RC[one]}" != 0 ]; then echo "the control did not import"; echo "RESULT: NO-DEFECT"
elif [ "$V1$V2$V3" != okokok ]; then echo "RESULT: DEFECT"
else echo "RESULT: NO-DEFECT"; fi
exit 0
