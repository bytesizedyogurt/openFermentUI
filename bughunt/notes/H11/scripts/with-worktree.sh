#!/bin/bash
# with-worktree.sh SCRIPT [lib]: run one of H11's scripts against a fresh detached worktree of 2047f5a, made under
# $BH_WORK/H11/repro-wt and removed after, so nothing in the repository's own checkout is touched.
#   bash bughunt/notes/H11/scripts/with-worktree.sh install-twice.sh
#   bash bughunt/notes/H11/scripts/with-worktree.sh backup-rotation.sh lib
# With `lib` the script is given the worktree's scripts/host/lib.sh; otherwise the worktree itself. Its second
# argument is a scratch folder for its output. Keyless: runs under bughunt/lib/env.sh's bh_env.
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
script="$HERE/$1"; mode="${2:-checkout}"
wt="$BH_WORK/H11/repro-wt"; out="$BH_WORK/H11/repro-out/${1%.sh}"
git -C "$BH_ROOT" worktree remove --force "$wt" >/dev/null 2>&1
git -C "$BH_ROOT" worktree add --detach "$wt" 2047f5a >/dev/null 2>&1 || { echo "could not add the worktree"; exit 2; }
if [ "$mode" = lib ]; then arg="$wt/scripts/host/lib.sh"; else arg="$wt"; fi
bh_env bash "$script" "$arg" "$out"; status=$?
git -C "$BH_ROOT" worktree remove --force "$wt"
exit "$status"
