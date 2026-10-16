#!/bin/bash
# The review decisions made on this machine, pushed (OF-BLD-014 §1.3, E.10).
#
#   bash scripts/decisions-push.sh        pnpm decisions:push
#
# Guild writes every decision into core/data/biorepo.json, the one data file
# git keeps. This commits that file alone, as `Guild decisions <date>`, and
# pushes the branch this checkout is on, so the next session starts from the
# decisions made here. It refuses while any other file is staged, so nothing
# rides along with them. The Mac Mini's own nightly backup is
# scripts/host/sync_decisions.sh, which deploy.sh runs.
set -euo pipefail
cd "$(dirname "$0")/.."
FILE=core/data/biorepo.json

die() { printf '✗ %s\n' "$*" >&2; exit 1; }

others="$(git diff --cached --name-only | grep -vxF "$FILE" || true)"
[ -z "$others" ] || die "other files are staged: ${others//$'\n'/, }. This commits $FILE alone; unstage them first (git restore --staged <file>)"
branch="$(git symbolic-ref --quiet --short HEAD)" || die "this checkout is on no branch, so there is nowhere to push"

git add -- "$FILE"
if git diff --cached --quiet -- "$FILE"; then
  echo "No new decisions in $FILE."
else
  message="Guild decisions $(date +%Y-%m-%d)"
  git commit --quiet -m "$message" -- "$FILE"
  echo "Committed $FILE as \"$message\"."
fi

if git rev-parse --verify --quiet '@{u}' >/dev/null && [ -z "$(git rev-list '@{u}..HEAD')" ]; then
  echo "Nothing to push: $branch on GitHub already has it."
  exit 0
fi
git push --quiet -u origin "$branch" \
  || die "the commit is here and the push was refused. When $branch moved on GitHub: git pull --rebase (biorepo.json merges by record), then pnpm decisions:push again"
echo "Pushed $branch."
