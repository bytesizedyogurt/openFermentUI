#!/usr/bin/env bash
# H13-04: `pnpm eval` meets a missing or unknown project with a Python traceback (seed) or an empty
# summary with exit 0, where `pnpm lit:graph` and conform refuse the same case in words with exit 2.
# Keyless, no network, no service, no model. A fresh migrated test database holding one project, and a
# detached worktree of 2047f5a (which has no core/.env, so the command's own __main__ loader reads
# nothing of the checkout's settings), run with the checkout's own Python: `pnpm eval` is
# `cd core && uv run --all-extras python -m openferment_core.evaluation`, and this runs that module.
# usage, from the repository root: bash bughunt/repro/H13-04/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h13_04_eval
T=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H13-04/run
WT="$T/wt"
PY="$BH_ROOT/core/.venv/bin/python"
cleanup() {
  bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune
  rm -rf "${T:?}"
}
trap cleanup EXIT
rm -rf "${T:?}"; mkdir -p "$T/data"

echo "EXPECTED: \`pnpm eval seed\` and \`pnpm eval summary\` asked with no OPENFERMENT_PROJECT, or with one the"
echo "EXPECTED: database does not hold, exit 2 with words naming the project and nothing written, as"
echo "EXPECTED: \`pnpm lit:graph --project nope --dry-run\` (\"The store holds no project 'nope'.\") and"
echo "EXPECTED: \`conform train --project nope\` (\"holds no project 'nope': name a project it holds\") answer"
echo "EXPECTED: (projects/__init__.py:10-11 \"A command ... names it once, in OPENFERMENT_PROJECT. A store call"
echo "EXPECTED: that names none is refused in words.\"; evaluation.py:38-39 \"... exits 2 in words, having asked nothing.\")"

bh_db_fresh "$DB" || { echo "OBSERVED: the test database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 \
  || { echo "OBSERVED: the worktree could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
[ -e "$WT/core/.env" ] && { echo "OBSERVED: the worktree holds a core/.env; stopping"; echo "RESULT: NO-DEFECT"; exit 0; }

# Every command: from the worktree's core/, keyless, this database, no project unless one is named.
ev() { (cd "$WT/core" && unset OPENFERMENT_PROJECT && bh_env PYTHONDONTWRITEBYTECODE=1 \
        OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$T/data" "$@"); }
rows() { psql "$BH_SERVER/$DB" -tAXc "SELECT count(*) FROM openferment.eval_questions WHERE project_id = '$1'"; }

ev "$PY" -c "import openferment_core.evaluation as e; print('module', e.__file__)" | sed 's/^/NOTE: /'
ev "$PY" -c "from openferment_core import projects; from openferment_core.models import ProjectCreate
print('NOTE: project made', projects.create(ProjectCreate(id='h13-held', name='H13 held', by='bughunt')).id)"

# 1. seed, no project named.
ev "$PY" -m openferment_core.evaluation seed > "$T/1.out" 2>&1; x1=$?
tb1=$(grep -c '^Traceback' "$T/1.out")
# 2. seed, a project the database does not hold.
ev OPENFERMENT_PROJECT=nope "$PY" -m openferment_core.evaluation seed > "$T/2.out" 2>&1; x2=$?
tb2=$(grep -c '^Traceback' "$T/2.out"); n2=$(rows nope)
# 3. summary, a project the database does not hold; and summary with none named.
ev OPENFERMENT_PROJECT=nope "$PY" -m openferment_core.evaluation summary > "$T/3.out" 2> "$T/3.err"; x3=$?
ev "$PY" -m openferment_core.evaluation summary > "$T/3b.out" 2>&1; x3b=$?
tb3b=$(grep -c '^Traceback' "$T/3b.out")
# Control: the same commands in the project the database holds.
ev OPENFERMENT_PROJECT=h13-held "$PY" -m openferment_core.evaluation seed > "$T/c1.out" 2>&1; xc1=$?
ev OPENFERMENT_PROJECT=h13-held "$PY" -m openferment_core.evaluation summary > "$T/c2.out" 2>&1; xc2=$?
# The other doors, the same unknown project.
ev "$PY" -m openferment_core.literature_live graph --project nope --dry-run > "$T/d.out" 2>&1; xd=$?
ev timeout 120 "$PY" -m openferment_core.engine.conform train --project nope > "$T/e.out" 2>&1; xe=$?

echo "OBSERVED: 1. eval seed, no project: exit $x1, $tb1 traceback(s), $(wc -l < "$T/1.out") lines; last line:"
echo "OBSERVED:    $(tail -1 "$T/1.out" | cut -c1-200)"
echo "OBSERVED: 2. eval seed, OPENFERMENT_PROJECT=nope: exit $x2, $tb2 traceback(s), $(wc -l < "$T/2.out") lines; rows kept for nope: $n2; lines:"
grep -E '^(asyncpg|sqlalchemy)\.[A-Za-z_.]*Error|^\[SQL: |^\[parameters: ' "$T/2.out" | cut -c1-200 | sed 's/^/OBSERVED:    /'
echo "OBSERVED: 3. eval summary, OPENFERMENT_PROJECT=nope: exit $x3, stderr $(wc -c < "$T/3.err") bytes, stdout: $(cut -c1-200 "$T/3.out")"
echo "OBSERVED: 3b. eval summary, no project: exit $x3b, $tb3b traceback(s); last line: $(tail -1 "$T/3b.out" | cut -c1-120)"
echo "OBSERVED: control, project h13-held: seed exit $xc1 $(tail -1 "$T/c1.out" | cut -c1-80); summary exit $xc2 $(tail -1 "$T/c2.out" | cut -c1-80)"
echo "OBSERVED: lit:graph --project nope --dry-run: exit $xd: $(tail -1 "$T/d.out" | cut -c1-160)"
echo "OBSERVED: conform train --project nope: exit $xe: $(grep -v '^$' "$T/e.out" | tail -1 | cut -c1-160)"

# The defect: each eval case answers without a refusal in words and exit 2, where both other doors refuse so.
seed_none_bad=0; [ "$x1" != 2 ] && [ "$tb1" -ge 1 ] && seed_none_bad=1
seed_nope_bad=0; [ "$x2" != 2 ] && [ "$tb2" -ge 1 ] && grep -q ForeignKeyViolation "$T/2.out" && seed_nope_bad=1
summ_nope_bad=0; [ "$x3" = 0 ] && grep -q '"tags": {}' "$T/3.out" && summ_nope_bad=1
doors_refuse=0; [ "$xd" = 2 ] && grep -q "holds no project 'nope'" "$T/d.out" && [ "$xe" = 2 ] \
  && grep -q "holds no project 'nope'" "$T/e.out" && doors_refuse=1
control_ok=0; [ "$xc1" = 0 ] && [ "$xc2" = 0 ] && control_ok=1
echo "NOTE: seed-none=$seed_none_bad seed-nope=$seed_nope_bad summary-nope=$summ_nope_bad other-doors-refuse=$doors_refuse control=$control_ok"
if [ "$seed_none_bad$seed_nope_bad$summ_nope_bad$doors_refuse$control_ok" = 11111 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
