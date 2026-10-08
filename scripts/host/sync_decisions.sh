#!/bin/bash
# Back up the review decisions Guild wrote on this machine (OF-BLD-012 §B.8).
# `deploy.sh --keep-decisions` runs this; running it alone does the same.
#
# Every decision made here since the last push becomes ONE commit, which is
# rebased onto GitHub's decisions through the record-level merge driver
# (merge_biorepo.py) and pushed. One commit matters: a rebase replays commits
# one by one, so an old unpushed commit that disagreed with GitHub would fail
# again on every later run, even after the two machines came to agree.
#
# What only a person can settle (a record withdrawn on one machine and changed
# on the other) stops it with the rebase undone, so the file the service
# reads keeps this machine's decisions and stays valid.
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$REPO"
FILE=core/data/biorepo.json

refuse_unfinished_git
register_merge_driver

changed="$(git diff --name-only HEAD)"
if [ -n "$changed" ] && [ "$changed" != "$FILE" ]; then
  die "uncommitted changes in: ${changed//$'\n'/ }. Commit or stash them first."
fi
git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1 || die "this branch follows no branch on GitHub, so there is nowhere to back up to"
git fetch --quiet

base="$(git merge-base HEAD '@{u}')"
unpushed="$(git diff --name-only "$base" HEAD)"
if [ -z "$unpushed" ] || [ "$unpushed" = "$FILE" ]; then
  git reset --soft "$base"
fi
git add "$FILE"
if ! git diff --cached --quiet; then
  say "Committing the review decisions made on this machine"
  git commit --quiet -m "BioRepo: review decisions from $(hostname -s), $(date +%F)"
fi

if ! git pull --rebase --quiet; then
  git rebase --abort 2>/dev/null || true
  die "the records listed above were withdrawn on one machine and changed on the other, or decided at the same instant, which only a person can settle. This machine's decisions are kept, committed here and in the file the service reads. Make both machines agree on those records in Guild, then run this again"
fi
if [ -n "$(git rev-list '@{u}..HEAD')" ]; then
  git push --quiet || die "the decisions are committed here but could not be pushed. Check this machine can push (pnpm ready), then run this again"
  say "Decisions backed up"
else
  say "Nothing new to back up"
fi
