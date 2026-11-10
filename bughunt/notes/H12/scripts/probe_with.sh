#!/usr/bin/env bash
# probe_with.sh ID PROBE [ARGS...]: run probes/PROBE on the head's code, then in a worktree of 2047f5a with
# mutation ID applied, each over a fresh test database bh_h12_probe; the two answers side by side show the
# behaviour the mutation changes (and survivor.sh ID shows that no test sees it). Keyless; drops the database.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
ID=${1:?mutation id}; PROBE=${2:?probe}; shift 2
N=/home/user/openFermentUI/bughunt/notes/H12
WT=${WT:-$BH_WORK/H12/repro-wt}
if [ ! -d "$WT" ]; then
  git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || exit 2
  (cd "$WT" && git apply "$N/mutations/BASE-scratch-name.patch") || exit 2
fi
PY="$BH_ROOT/core/.venv/bin/python"
run() {  # run TREE ARGS...: the probe with TREE's core first on the path
  local tree=$1; shift
  bh_db_fresh bh_h12_probe || return 1
  (cd "$tree/core" && bh_env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$tree/core" OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h12_probe" \
     timeout 600 "$PY" "$N/scripts/probes/$PROBE" "$@" 2>&1 | tail -3)
}
echo "== head (2047f5a)"; run "$WT" "$@"
(cd "$WT" && git apply "$N/mutations/$ID.patch") || { echo "the patch for $ID does not apply"; exit 2; }
echo "== with $ID"; run "$WT" "$@"
(cd "$WT" && git apply -R "$N/mutations/$ID.patch")
bh_db_drop bh_h12_probe
