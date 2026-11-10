#!/usr/bin/env bash
# baseline.sh: H12's selection on the unmutated worktree (marker set as test:core's), with per-file times.
S=/home/user/openFermentUI/bughunt/notes/H12/scripts
for f in "$@"; do
  start=$(date +%s)
  out=$($S/wtpytest.sh "tests/$f" -m "not live and not sim and not slow and not lit" 2>&1 | tail -1)
  echo "$f	$(( $(date +%s) - start ))s	$out"
done
