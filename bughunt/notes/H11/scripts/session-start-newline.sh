#!/bin/bash
# session-start-newline.sh CHECKOUT OUT: scripts/session-start.sh in the hunt's worktree on stand-ins for pnpm,
# uv and pg_isready (PostgreSQL answering), over a core/.env whose last line, the key line, has no newline at
# its end (as an editor that adds no final newline saves it). The key line holds the example's placeholder
# text, never a key. Prints the file's lines and what python-dotenv reads for the key and the database after.
# A second case runs with OPENFERMENT_WORKSPACE_ID set, the other line session-start appends.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
cp "$OUT/standins/keg/bin/pg_isready" "$OUT/standins/bin/pg_isready"
show() { /home/user/openFermentUI/core/.venv/bin/python -I -c '
import sys; from dotenv import dotenv_values
v = dotenv_values(sys.argv[1])
k = v.get("ANTHROPIC_API_KEY")
print("   key line reads as", repr(k), "| database reads as", repr(v.get("OPENFERMENT_DATABASE_URL")),
      "| workspace reads as", repr(v.get("OPENFERMENT_WORKSPACE_ID")))' "$CO/core/.env"; }
for ws in "" "wrkspc_h11_placeholder"; do
  printf '# hand-written\nANTHROPIC_API_KEY=sk-ant-...' > "$CO/core/.env"; chmod 600 "$CO/core/.env"
  (cd "$CO" && env -u OPENFERMENT_API_KEY ${ws:+OPENFERMENT_WORKSPACE_ID=$ws} HOME="$OUT/home" bash scripts/session-start.sh) > "$OUT/out" 2>&1
  echo "== OPENFERMENT_WORKSPACE_ID='${ws}': session-start exit $?; core/.env now holds:"
  sed 's/^/   | /' "$CO/core/.env"; echo; show
done
rm -f "$CO/core/.env"
