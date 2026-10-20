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
# .data-sync/, commits and pushes; `pull` copies them back. Neither direction
# deletes a file. A push replaces the branch's copy with this machine's; a
# pull adds what is missing here and keeps a local file that differs from
# the branch's, naming it, so work not yet pushed is never overwritten.
#
# Only the paths in PATHS travel, or a path inside one of them. Any other is
# refused by name: fetched full text spans several licences and stays on the
# machine that fetched it, and core/.env, spend.json and Guild's files never
# leave it. The list is checked by spelling, so a symbolic link anywhere on or
# under a path that travels is refused too: it would carry what its spelling
# hides. test_data_sync holds the script to all of it.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH=openferment-data
WORK="$REPO/.data-sync/$BRANCH"
PATHS=(
  core/data/candidates/
  core/data/artifacts/
  core/data/rageval/
  core/data/index/config.json
  core/data/index/dense.npy
  core/data/index/dense.json
  core/data/live/
  core/data/thread-p-proposed.tsv
  core/data/thread-q-proposed.tsv
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
trap 'rm -rf "$WORK" "$WORK.kept"' EXIT

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

# Refuse a symbolic link on or under one listed path in `root`.
refuse_links() {
  local root="$1" p="$2" rel="${2%/}" part="" seg found segs
  IFS=/ read -r -a segs <<< "$rel"
  for seg in "${segs[@]}"; do
    part="${part:+$part/}$seg"
    if [ -L "$root/$part" ]; then
      [ "$part" = "$rel" ] && part="$p"
      die "$part is a symbolic link$3. data-sync.sh copies files and refuses links: a link would carry what its spelling hides"
    fi
  done
  if [ -d "$root/$rel" ]; then
    found="$(cd "$root/$rel" && find . -type l | head -1)"
    [ -z "$found" ] || die "$rel/${found#./} is a symbolic link$3. data-sync.sh copies files and refuses links: a link would carry what its spelling hides"
  fi
}

# Push one listed path into the checkout: adds and replaces, never deletes.
# Finder's .DS_Store files stay behind.
push_copy() {
  local from="$REPO/$1" to="$WORK/$1"
  if [ -d "$from" ]; then
    mkdir -p "$to"
    cp -a "$from/." "$to/"
    find "$to" -name .DS_Store -type f -exec rm -f {} +
    find "$from" -type f ! -name .DS_Store | wc -l | tr -d ' '
  elif [ -f "$from" ]; then
    mkdir -p "$(dirname "$to")"
    cp -a "$from" "$to"
    echo 1
  else
    echo 0
  fi
}

# Pull one listed path out of the checkout: a file missing here is added, and
# a local file that differs from the branch's is kept and named in $KEPT.
# Prints how many files here now match the branch.
pull_copy() {
  local p="${1%/}" rel n=0 list
  if [ -d "$WORK/$p" ]; then
    list="$(cd "$WORK" && find "$p" -type f)"
  elif [ -f "$WORK/$p" ]; then
    list="$p"
  else
    echo 0
    return
  fi
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    if [ -e "$REPO/$rel" ] && ! cmp -s "$WORK/$rel" "$REPO/$rel"; then
      echo "$rel" >> "$KEPT"
      continue
    fi
    mkdir -p "$(dirname "$REPO/$rel")"
    cp -p "$WORK/$rel" "$REPO/$rel"
    n=$((n + 1))
  done <<< "$list"
  echo "$n"
}

push() {
  local attempt rc n total p name email out
  for p in "${chosen[@]}"; do refuse_links "$REPO" "$p" ""; done
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
      n="$(push_copy "$p")"
      total=$((total + n))
      [ "$n" -eq 0 ] || echo "  $p  $n file(s)"
    done
    git -C "$WORK" add -A
    if git -C "$WORK" diff --cached --quiet; then
      say "nothing new to push: $BRANCH already holds these $total file(s)"
      return 0
    fi
    # The repository is public, so the message names no machine.
    git -C "$WORK" -c "user.name=${name:-openFerment data sync}" \
      -c "user.email=${email:-data-sync@openferment.invalid}" commit --quiet \
      -m "Data pushed $(date -u +%Y-%m-%dT%H:%M:%SZ): $total file(s) under the listed paths"
    if out="$(git -C "$WORK" push --quiet origin "HEAD:refs/heads/$BRANCH" 2>&1)"; then
      say "pushed $(git -C "$WORK" show --stat --format= HEAD | tail -1 | sed 's/^ *//') to $BRANCH"
      return 0
    fi
    # Only a branch that moved on is worth another try; any other refusal is
    # reported in git's own words.
    case "$out" in
      *"(fetch first)"* | *"(non-fast-forward)"*) say "$BRANCH moved while this ran; trying again from its new tip" ;;
      *) die "the push to $BRANCH was refused: $out" ;;
    esac
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
    refuse_links "$WORK" "$p" " on $BRANCH"
    refuse_links "$REPO" "$p" ""
  done
  KEPT="$WORK.kept"
  : > "$KEPT"
  for p in "${chosen[@]}"; do
    n="$(pull_copy "$p")"
    total=$((total + n))
    [ "$n" -eq 0 ] || echo "  $p  $n file(s)"
  done
  say "pulled $total file(s) from $BRANCH"
  if [ -s "$KEPT" ]; then
    say "kept $(wc -l < "$KEPT" | tr -d ' ') local file(s) that differ from $BRANCH:"
    sed 's/^/  /' "$KEPT"
    echo "  Push them to make them the branch's (pnpm data:push), or delete one here and pull again to take the branch's."
  fi
  rm -f "$KEPT"
}

"$mode"
