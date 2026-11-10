#!/usr/bin/env bash
# H11-09: scripts/host/lib.sh:6 sets REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)". Run as the
# live-host runbook writes it (scripts/host/install.sh, from the checkout), dirname gives the relative path
# scripts/host; with CDPATH exported as `.:$HOME`, bash's cd finds scripts/host/../.. through the CDPATH entry
# `.` and prints the new directory, so REPO captures it twice on two lines, and install.sh, deploy.sh and
# nightly.sh each stop at their own first `cd "$REPO..."`.
# usage, from the repository root: bash bughunt/repro/H11-09/run.sh
#
# Shell alone: no database and no service is touched, so none is made. Everything runs in a detached worktree
# of 2047f5a under $BH_WORK/H11-09/wt, on the H11 hunt's stand-ins for macOS and Homebrew
# (bughunt/notes/H11/scripts/standins.sh: launchctl, sudo, brew, psql, pg_dump, pnpm, uv, curl and the
# checkout's python answer without doing anything; PATH holds the stand-ins and /usr/bin:/bin alone), with a
# git stand-in that answers `pull` and passes every other call to /usr/bin/git. HOME is a scratch folder.
# Keyless and offline: nothing here reads a key or reaches the network.
source /home/user/openFermentUI/bughunt/lib/env.sh
SHA=2047f5a
T=$BH_WORK/H11-09; WT=$T/wt; OUT=$T/out
STANDINS=$BH_ROOT/bughunt/notes/H11/scripts/standins.sh

cleanup() {
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rm -rf "$T"
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT"

echo "EXPECTED: scripts/host/install.sh, deploy.sh and nightly.sh, each run from the checkout as the runbook writes them"
echo "EXPECTED: (docs/runbooks/live-host-install.md:133 'scripts/host/install.sh', :253 'scripts/host/deploy.sh',"
echo "EXPECTED: :257 'scripts/host/nightly.sh'), run the same with CDPATH exported as '.:\$HOME' as with no CDPATH:"
echo "EXPECTED: lib.sh's REPO is the checkout's one absolute path, and each script gets past its first cd."

git -C "$BH_ROOT" worktree add --detach "$WT" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "setup: worktree $(git -C "$WT" rev-parse --short HEAD); lib.sh:6 reads: $(sed -n 6p "$WT/scripts/host/lib.sh")"

# One pass: fresh stand-ins and a fresh HOME, then the three scripts in the runbook's order, each from the
# checkout, under the CDPATH given ("" leaves it empty, which bash reads as unset).
pass() { # pass N CDPATH_VALUE
  local n="$1" cdp="$2" P="$OUT/pass$1"
  mkdir -p "$P/home"
  rm -f "$WT/core/.env"
  (
    export HOME="$P/home"
    eval "$(bash "$STANDINS" "$P/standins" "$WT")"
    printf '#!/bin/bash\nprintf "%%s\\n" "git $*" >> "%s"\n[ "$1" = pull ] && exit 0\nexec /usr/bin/git "$@"\n' \
      "$P/standins/calls" > "$P/standins/bin/git"; chmod 755 "$P/standins/bin/git"
    [ -n "$cdp" ] && cdp="${cdp//\$HOME/$HOME}"
    # REPO as lib.sh computes it, sourced as the scripts source it (BASH_SOURCE[0] = scripts/host/lib.sh).
    (cd "$WT" && env CDPATH="$cdp" /bin/bash -c 'source scripts/host/lib.sh; printf "%q\n" "$REPO"') \
      > "$P/repo" 2>&1
    for s in install deploy nightly; do
      (cd "$WT" && env CDPATH="$cdp" /bin/bash "scripts/host/$s.sh") > "$P/$s.out" 2>&1
      echo $? > "$P/$s.exit"
    done
  )
}

pass 1 ""
pass 2 '.:$HOME'

WTQ="$WT"
show() { sed "s|$WTQ|<checkout>|g"; }
for n in 1 2; do
  P="$OUT/pass$n"; [ "$n" = 1 ] && label="CDPATH unset" || label="CDPATH='.:\$HOME' exported"
  echo "== $label"
  echo "   lib.sh's REPO: $(show < "$P/repo")"
  for s in install deploy nightly; do
    cdline=$(grep -m1 ': cd: ' "$P/$s.out" | show)
    last=$(grep -v '^$' "$P/$s.out" | tail -1 | show)
    echo "   scripts/host/$s.sh: exit $(cat "$P/$s.exit"); ${cdline:-no cd failure}; last line: ${last:0:140}"
  done
done

# The verdict: with no CDPATH, REPO is the checkout and no script fails a cd; with CDPATH exported, REPO
# differs from the checkout and a script stops at a cd.
good_repo=$(cd "$WT" && pwd -P)
p1_repo=$(cat "$OUT/pass1/repo"); p2_repo=$(cat "$OUT/pass2/repo")
p1_cd=$(cat "$OUT"/pass1/*.out | grep -c ': cd: ')
p2_cd=$(cat "$OUT"/pass2/*.out | grep -c ': cd: ')
p2_fail=0; for s in install deploy nightly; do [ "$(cat "$OUT/pass2/$s.exit")" != 0 ] && p2_fail=$((p2_fail+1)); done
p1_fail=0; for s in install deploy nightly; do [ "$(cat "$OUT/pass1/$s.exit")" != 0 ] && p1_fail=$((p1_fail+1)); done

echo "OBSERVED: CDPATH unset: REPO $( [ "$p1_repo" = "$good_repo" ] && echo "is the checkout" || echo "is $p1_repo" ),"\
" $p1_cd cd failures, $p1_fail of 3 scripts exit non-zero."
echo "OBSERVED: CDPATH='.:\$HOME': REPO $( [ "$p2_repo" = "$good_repo" ] && echo "is the checkout" || echo "is $(echo "$p2_repo" | show)" ),"\
" $p2_cd cd failures, $p2_fail of 3 scripts exit non-zero, each at its first cd."
if [ "$p1_repo" = "$good_repo" ] && [ "$p1_cd" = 0 ] && [ "$p2_repo" != "$good_repo" ] && [ "$p2_cd" -ge 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
