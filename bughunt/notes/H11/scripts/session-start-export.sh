#!/bin/bash
# session-start-export.sh CHECKOUT OUT: scripts/session-start.sh in the hunt's worktree, on stand-ins for
# pnpm, uv and pg_isready (PostgreSQL answering), over a core/.env whose database line is written in a
# form python-dotenv reads (`export NAME=value`, or `NAME = value`). Prints the database python-dotenv
# reads from core/.env before and after the session start. No key is involved: the file holds the
# example's placeholder line alone beside the database line.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
cp "$OUT/standins/keg/bin/pg_isready" "$OUT/standins/bin/pg_isready"
read_db() { /home/user/openFermentUI/core/.venv/bin/python -I -c '
import sys; from dotenv import dotenv_values
print(dotenv_values(sys.argv[1]).get("OPENFERMENT_DATABASE_URL"))' "$CO/core/.env"; }
for line in 'export OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment' \
            'OPENFERMENT_DATABASE_URL = postgresql://sean@127.0.0.1:5432/openferment'; do
  printf 'ANTHROPIC_API_KEY=sk-ant-...\n%s\n' "$line" > "$CO/core/.env"; chmod 600 "$CO/core/.env"
  echo "== core/.env's database line: $line"
  echo "   read before: $(read_db)"
  (cd "$CO" && env -u OPENFERMENT_API_KEY -u OPENFERMENT_WORKSPACE_ID HOME="$OUT/home" bash scripts/session-start.sh) > "$OUT/out" 2>&1
  echo "   session-start exit $?: $(grep 'OPENFERMENT_DATABASE_URL' "$OUT/out")"
  echo "   read after:  $(read_db)"
done
rm -f "$CO/core/.env"
