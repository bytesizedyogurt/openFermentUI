#!/usr/bin/env bash
# H6-04: `pnpm db:import-alpha1` prints, and writes into its import_alpha1 audit row, one count a kind taken
# from the entries of each file, while each row is written by rows.put, an upsert on (project_id, id). For a
# guild.json naming one person twice under one id it prints and audits 3 people and the project keeps 2 (the
# second entry replacing the first); for an artifact held by two files (a file manager's copy) it prints and
# audits 2 artifacts and the project keeps 1. A control directory with no duplicate shows the counts agree.
# The import's command (package.json: `cd core && uv run --frozen python -m openferment_core.import_alpha1`)
# runs here as `python -m openferment_core.import_alpha1` from core/ of a worktree of 2047f5a made by this
# run, on the repository's venv (uv run would sync a venv; the worktree holds no core/.env, so nothing is
# read from one). The data directories are written by alpha 1.0's own models (gen.py beside this file).
# No service, no port, no model call.
#   bash bughunt/repro/H6-04/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
R=$BH_ROOT/bughunt/repro/H6-04
DB=bh_r_h6_04_imp
S=$BH_WORK/H6-04; mkdir -p "$S"
WT=$S/wt-$$                          # 2047f5a's tree, this run's own
T=$(mktemp -d "$S/run.XXXXXX")       # this run's data and answers
cleanup() {
  bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree list --porcelain | grep -qx "worktree $WT" && { rm -rf "$WT"; git -C "$BH_ROOT" worktree prune; }
  rm -rf "$T" "$WT"
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: the import prints the new project's id and what it carried, one count a kind"
echo "EXPECTED: (docs/runbooks/live-host-install.md:217); for each kind the printed count, the audit row's"
echo "EXPECTED: detail.counts and the rows the project keeps are one number, or a duplicate id is refused in words."

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
[ -e "$WT/core/.env" ] && fail "the worktree holds a core/.env"
echo "module: $(cd "$WT/core" && bh_env .venv/bin/python -c 'import openferment_core.import_alpha1 as m; print(m.__file__)' | sed "s|$WT|<worktree of 2047f5a>|")"

git -C "$BH_ROOT" show alpha-1.0:core/openferment_core/models.py > "$T/models-a1.py" || fail "alpha 1.0's models"
bh_env "$BH_ROOT/core/.venv/bin/python" -I "$R/gen.py" "$T/models-a1.py" "$T/data" | sed 's/^/alpha 1.0 data /' \
  || fail "gen.py"
BH_ROOT=$WT bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "database $DB (fresh): openferment at $(psql "$BH_SERVER/$DB" -XAtc 'select version_num from openferment.alembic_version')"

q() { psql "$BH_SERVER/$DB" -XAtc "$1"; }
declare -A BAD SAW
imp() {  # imp CASE: import OUT_DIR/CASE into a new project; compare printed, audited and kept counts
  local c=$1 rc pid pp pa ap aa kp ka who
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -m openferment_core.import_alpha1 \
      --name "Repro H6-04 $c" --by "Ada Moreno" --data "$T/data/$c") > "$T/$c.out" 2>&1
  rc=$?
  pid=$(sed -n 's/^carried .* into project \(.*\):$/\1/p' "$T/$c.out")
  echo
  echo "== import $c: exit $rc; project ${pid:-none}; $(grep -c '^refused:' "$T/$c.out") refused: lines"
  [ "$rc" = 0 ] && [ -n "$pid" ] || { sed "s|$T/||" "$T/$c.out" | tail -3 | sed 's/^/  /'; BAD[$c]=refused; return; }
  pp=$(awk '$2=="people"{print $1}' "$T/$c.out"); pa=$(awk '$2=="artifacts"{print $1}' "$T/$c.out")
  ap=$(q "select body->'detail'->'counts'->>'people' from openferment.audit where project_id='$pid' and action='import_alpha1'")
  aa=$(q "select body->'detail'->'counts'->>'artifacts' from openferment.audit where project_id='$pid' and action='import_alpha1'")
  kp=$(q "select count(*) from openferment.guild_people where project_id='$pid'")
  ka=$(q "select count(*) from openferment.artifacts where project_id='$pid'")
  who=$(q "select string_agg(id || ' ' || (body->>'name'), ', ' order by id) from openferment.guild_people where project_id='$pid'")
  echo "  people:    printed $pp; audited $ap; kept $kp ($who)"
  echo "  artifacts: printed $pa; audited $aa; kept $ka ($(q "select string_agg(id, ', ') from openferment.artifacts where project_id='$pid'"))"
  if [ "$pp" = "$kp" ] && [ "$ap" = "$kp" ] && [ "$pa" = "$ka" ] && [ "$aa" = "$ka" ]; then BAD[$c]=agree
  else BAD[$c]=disagree; fi
  echo "  printed, audited and kept counts: ${BAD[$c]}"
  SAW[$c]="printed $pp people, audited $ap, kept $kp; printed $pa artifacts, audited $aa, kept $ka"
}
imp one
imp dup

echo
echo "OBSERVED: control (no duplicate id): ${SAW[one]:-none} (${BAD[one]})"
echo "OBSERVED: duplicate ids, exit 0 with no refused: line: ${SAW[dup]:-none} (${BAD[dup]})"
echo "OBSERVED: the import counts the entries of each file (import_alpha1.py:79-93) and rows.put upserts by (project_id, id)."
if [ "${BAD[one]}" = agree ] && [ "${BAD[dup]}" = disagree ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
