#!/usr/bin/env bash
# run_imports.sh: `pnpm db:import-alpha1` (package.json's own command, `cd core && uv run --frozen python -m
# openferment_core.import_alpha1`) run from a worktree of the head (wt-head, its own environment) on each
# alpha 1.0 data directory gen_alpha1.py wrote, into one test database, bh_h6_imp, made fresh and migrated
# to head. For each case: the exit status, what it printed, the projects the database holds after it.
# Then a second import of `full` under the same name, and the environment's packages before and after.
source /home/user/openFermentUI/bughunt/lib/env.sh
W=$BH_WORK/H6
WT=$W/wt-head
DATA=$W/a1data
DB=bh_h6_imp
URL=$BH_SERVER/$DB
bh_db_fresh $DB || exit 1
(cd "$WT/core" && bh_env uv pip list --python .venv/bin/python 2>/dev/null) > "$W/pkgs-before.txt"
imp() {  # imp CASE NAME
  echo "== $1 (--name '$2')"
  local t0=$SECONDS
  ( cd "$WT" && bh_env OPENFERMENT_DATABASE_URL="$URL" \
      pnpm --silent db:import-alpha1 --name "$2" --by "Ada Moreno" --data "$DATA/$1" ) > "$W/imp-$1.out" 2>&1
  local rc=$?
  grep -v "^$" "$W/imp-$1.out" | head -30
  echo "   exit $rc, $((SECONDS - t0)) s"
  psql "$URL" -XAtc "select string_agg(id, ', ' order by created_at) from openferment.projects" | sed 's/^/   projects: /'
}
for c in tag full bad-json bad-shape estimate noreviewer mismatch empty-file empty-dir dup-person dup-paper dup-artifact big; do
  imp "$c" "Alpha 1.0 $c"
done
echo "== full again, under the name it was carried under"
imp full "Alpha 1.0 full"
(cd "$WT/core" && bh_env uv pip list --python .venv/bin/python 2>/dev/null) > "$W/pkgs-after.txt"
echo "== packages before and after (empty = the command changed none):"
diff "$W/pkgs-before.txt" "$W/pkgs-after.txt" && echo "(none)"
wc -l < "$W/pkgs-after.txt"
