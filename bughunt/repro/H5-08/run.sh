#!/usr/bin/env bash
# H5-08: the sci-rag MCP server, started with --project naming a project the database does not hold
# (bh-zzz), a malformed id (../bh-a) or an upper-case id (BH-A), answers every call as a held empty project,
# while the openferment MCP server refuses the same ids in words naming the database and the project.
#   bash bughunt/repro/H5-08/run.sh        (from the repository root; exits 0 either way)
# A fresh test database holding one project (bh-a, empty); both servers over stdio from a scratch worktree
# of 2047f5a, whose core/ holds no .env. No service, no key, no model call, no network.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h5_08_mcp
HERE=/home/user/openFermentUI/bughunt/repro/H5-08
WT=$BH_WORK/H5-08/wt
cleanup() {
  PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rm -rf "$WT"
}
trap cleanup EXIT

mkdir -p "$BH_WORK/H5-08"; : > "$BH_WORK/H5-08/servers.log"
git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 \
  || { echo "worktree add failed"; echo "RESULT: NO-DEFECT (the worktree could not be made)"; exit 0; }
echo "worktree: $WT at $(git -C "$WT" rev-parse --short HEAD); core/.env there: $([ -e "$WT/core/.env" ] && echo yes || echo no)"
(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") \
  || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"

OUT=$(cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" H5_WT="$WT/core" H5_ERRLOG="$BH_WORK/H5-08/servers.log" \
      "$BH_ROOT/core/.venv/bin/python" "$HERE/probe.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo "the projects the database holds:"
psql "$BH_SERVER/$DB" -qXAt -c "SELECT id FROM openferment.projects ORDER BY id" 2>&1 | sed 's/^/  /'
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
