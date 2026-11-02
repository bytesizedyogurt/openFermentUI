#!/bin/bash
# A session starts the same way each time (OF-BLD-014 §1.3).
#
#   bash scripts/session-start.sh        pnpm session:start
#
# Idempotent: run it at the start of every session, on a fresh clone or a
# warm one. In order:
#   1. core/.env from OPENFERMENT_API_KEY, when the file is missing. A cloud
#      session receives the key under that name because Claude Code reads
#      ANTHROPIC_API_KEY for its own sign-in; the file gives it to the
#      service under the name the service reads. Mode 600, confirmed ignored
#      by git, and the value is never printed.
#   2. pnpm install --frozen-lockfile
#   3. uv sync --all-extras, in core/
#   4. the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and
#      core/.env names none, the development address (compose.yaml's) joins
#      core/.env; then pnpm db:migrate, whatever it exits with
#   5. pnpm ready, whatever it exits with
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

say() { printf '\n── %s\n' "$*"; }
die() { printf '\n✗ %s\n' "$*" >&2; exit 1; }

say "the key"
if [ -e core/.env ]; then
  echo "core/.env is present; left as it is"
elif [ -n "${OPENFERMENT_API_KEY:-}" ]; then
  key="${OPENFERMENT_API_KEY//[[:space:]]/}"
  (umask 177 && printf 'ANTHROPIC_API_KEY=%s\n' "$key" > core/.env)
  unset key
  chmod 600 core/.env
  if ! git check-ignore -q core/.env; then
    rm -f core/.env
    die "git would track core/.env, so it was removed again. Restore the core/.env rule in .gitignore"
  fi
  echo "core/.env written from OPENFERMENT_API_KEY: mode 600, ignored by git"
else
  echo "no core/.env and no OPENFERMENT_API_KEY, so the steps that need the model wait (pnpm ready names them)"
fi
# A key not scoped to a workspace needs the workspace named on each request
# (llm.make_client). The id is not a secret; it joins core/.env when the file
# lacks it, so a service started from the file sends it too.
if [ -n "${OPENFERMENT_WORKSPACE_ID:-}" ] && [ -e core/.env ] && ! grep -q '^OPENFERMENT_WORKSPACE_ID=' core/.env; then
  printf 'OPENFERMENT_WORKSPACE_ID=%s\n' "${OPENFERMENT_WORKSPACE_ID//[[:space:]]/}" >> core/.env
  echo "OPENFERMENT_WORKSPACE_ID added to core/.env"
fi

say "pnpm install --frozen-lockfile"
pnpm install --frozen-lockfile || die "pnpm install failed"

say "uv sync --all-extras"
(cd core && uv sync --all-extras) || die "uv sync failed"

say "the database"
if [ -e core/.env ] && ! grep -q '^OPENFERMENT_DATABASE_URL=' core/.env && command -v pg_isready >/dev/null && pg_isready -q -h 127.0.0.1; then
  printf 'OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev\n' >> core/.env
  echo "OPENFERMENT_DATABASE_URL added to core/.env (the development address)"
fi
pnpm --silent db:migrate || echo "the database is not migrated; pnpm ready says what is missing"

say "pnpm ready"
pnpm --silent ready || true
