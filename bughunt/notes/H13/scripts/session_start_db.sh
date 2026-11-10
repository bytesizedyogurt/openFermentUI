#!/bin/bash
# H13: scripts/session-start.sh's database step (step 4), run as the script holds it, on a fresh
# clone with no key (no core/.env, no OPENFERMENT_API_KEY) and on one with a key (core/.env holding
# the key line alone). The step's lines are read from the script itself; `pnpm` is a stand-in that
# says what it was asked, so no database is touched.
#
# The script's own header: "4. the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and
# core/.env names none, the development address (compose.yaml's) joins core/.env; then pnpm
# db:migrate". README.md: "Without a key the app runs whole."
#
# Usage: bash session_start_db.sh <checkout root>
set -uo pipefail
root="${1:?checkout root}"
block="$(sed -n '/^say "the database"/,/^pnpm --silent db:migrate/p' "$root/scripts/session-start.sh")"
[ -n "$block" ] || { echo "the database step was not found in session-start.sh"; exit 2; }
echo "── the step, as session-start.sh holds it:"; echo "$block" | sed 's/^/   /'
for case in "no key: no core/.env" "a key: core/.env holds its line alone"; do
  t="$(mktemp -d)"; mkdir -p "$t/core"
  [ "$case" = "a key: core/.env holds its line alone" ] && printf 'ANTHROPIC_API_KEY=sk-ant-placeholder\n' > "$t/core/.env"
  (
    cd "$t" || exit 1
    say() { printf '   ── %s\n' "$*"; }
    pnpm() { echo "   pnpm $* (stand-in: OPENFERMENT_DATABASE_URL=${OPENFERMENT_DATABASE_URL:-unset}, core/.env names: $(grep -c '^OPENFERMENT_DATABASE_URL=' core/.env 2>/dev/null || echo 'no file'))"; }
    unset OPENFERMENT_DATABASE_URL
    echo "── case: $case"
    eval "$block"
    if [ -e core/.env ]; then echo "   core/.env after the step:"; sed 's/=.*/=<value>/' core/.env | sed 's/^/     /'
    else echo "   core/.env after the step: absent, so db:migrate and the service find no database"; fi
  )
  rm -rf "$t"
done
