#!/bin/bash
# Data that outlives a VM (OF-BLD-014 §1.3, E.10).
#
#   bash scripts/data-sync.sh push [path...]    pnpm data:push
#   bash scripts/data-sync.sh pull [path...]    pnpm data:pull
#
# A rebuilt cloud VM is a fresh clone that has lost every gitignored file, and
# extraction costs money to repeat. So the outputs worth keeping travel on
# `openferment-data`, an orphan branch of this same repository. `push` copies
# them from this checkout into a throwaway checkout of that branch under
# .data-sync/, commits and pushes; `pull` copies them back. A copy adds files
# and replaces them, and neither direction deletes one.
#
# Only the paths in PATHS travel, or a path inside one of them. Any other is
# refused by name: fetched full text spans several licences and stays on the
# machine that fetched it, and core/.env, spend.json and Guild's files never
# leave it. test_data_sync holds the script to that.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH=openferment-data
WORK="$REPO/.data-sync/$BRANCH"
PATHS=(
  core/data/candidates/
  core/data/artifacts/
  core/data/rageval/
  core/data/index/config.json
  core/data/live/
  core/data/thread-p-proposed.tsv
)

say() { printf '── %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

# The path as the list spells it, when the list carries it; nothing otherwise.
listed() {
  local want="${1#./}" p
  case "/$want/" in */../* | */./* | //*) return 1 ;; esac
  for p in "${PATHS[@]}"; do
    if [ "$want" = "$p" ] || [ "$want/" = "$p" ]; then
      echo "$p"
      return 0
    fi
    case "$p" in
      */) case "$want" in "$p"?*) echo "$want"; return 0 ;; esac ;;
    esac
  done
  return 1
}

[ $# -ge 1 ] || die "usage: data-sync.sh push|pull [path...]. The paths that travel: ${PATHS[*]}"
mode="$1"
shift
case "$mode" in push | pull) ;; *) die "usage: data-sync.sh push|pull [path...]" ;; esac

chosen=()
if [ $# -eq 0 ]; then
  chosen=("${PATHS[@]}")
else
  for arg in "$@"; do
    p="$(listed "$arg")" || die "$arg is outside the list data-sync.sh carries (${PATHS[*]}). Fetched full text, core/.env, spend.json and Guild's files stay on this machine"
    chosen+=("$p")
  done
fi

remote="$(git -C "$REPO" remote get-url origin 2>/dev/null)" || die "this checkout has no origin to sync with"
trap 'rm -rf "$WORK"' EXIT

# A fresh throwaway checkout of the data branch. Exit status 2: the branch
# does not exist yet. Anything else non-zero: origin could not be asked.
checkout() {
  local rc=0 out
  rm -rf "$WORK"
  mkdir -p "$(dirname "$WORK")"
  git ls-remote --exit-code --heads "$remote" "$BRANCH" >/dev/null 2>&1 || rc=$?
  [ "$rc" -eq 0 ] || return "$rc"
  out="$(git clone --quiet --no-local --depth 1 --single-branch --branch "$BRANCH" "$remote" "$WORK" 2>&1)" \
    || die "could not check out $BRANCH: $out"
}

# Copy one listed path from one root to the other. Adds and replaces; never deletes.
copy() {
  local from="$1/$3" to="$2/$3"
  if [ -d "$from" ]; then
    mkdir -p "$to"
    cp -a "$from/." "$to/"
    find "$from" -type f | wc -l | tr -d ' '
  elif [ -f "$from" ]; then
    mkdir -p "$(dirname "$to")"
    cp -a "$from" "$to"
    echo 1
  else
    echo 0
  fi
}

push() {
  local attempt rc n total p name email
  # The throwaway checkout commits as this checkout does.
  name="$(git -C "$REPO" config user.name || true)"
  email="$(git -C "$REPO" config user.email || true)"
  for attempt in 1 2 3; do
    rc=0
    checkout || rc=$?
    if [ "$rc" -eq 2 ]; then
      say "no $BRANCH branch on origin yet: starting it, with no history shared with the code"
      git init --quiet -b "$BRANCH" "$WORK"
      git -C "$WORK" remote add origin "$remote"
      printf '%s\n' "# openFerment data" "" \
        "What live runs produced, kept so a rebuilt machine starts from it (OF-BLD-014 E.10)." \
        "Written by scripts/data-sync.sh. It shares no history with the code and is never merged." \
        > "$WORK/README.md"
    elif [ "$rc" -ne 0 ]; then
      die "could not ask origin about $BRANCH"
    fi
    total=0
    for p in "${chosen[@]}"; do
      n="$(copy "$REPO" "$WORK" "$p")"
      total=$((total + n))
      [ "$n" -eq 0 ] || echo "  $p  $n file(s)"
    done
    git -C "$WORK" add -A
    if git -C "$WORK" diff --cached --quiet; then
      say "nothing new to push: $BRANCH already holds these $total file(s)"
      return 0
    fi
    git -C "$WORK" -c "user.name=${name:-openFerment data sync}" \
      -c "user.email=${email:-data-sync@openferment.invalid}" commit --quiet \
      -m "Data from $(hostname 2>/dev/null || echo this machine), $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if git -C "$WORK" push --quiet origin "HEAD:refs/heads/$BRANCH" 2>/dev/null; then
      say "pushed $(git -C "$WORK" show --stat --format= HEAD | tail -1 | sed 's/^ *//') to $BRANCH"
      return 0
    fi
    say "$BRANCH moved while this ran; trying again from its new tip"
  done
  die "could not push to $BRANCH after three tries"
}

pull() {
  local rc=0 n total=0 p
  checkout || rc=$?
  if [ "$rc" -eq 2 ]; then
    say "no $BRANCH branch on origin yet: nothing to pull"
    return 0
  fi
  [ "$rc" -eq 0 ] || die "could not ask origin about $BRANCH"
  for p in "${chosen[@]}"; do
    n="$(copy "$WORK" "$REPO" "$p")"
    total=$((total + n))
    [ "$n" -eq 0 ] || echo "  $p  $n file(s)"
  done
  say "pulled $total file(s) from $BRANCH"
}

"$mode"
