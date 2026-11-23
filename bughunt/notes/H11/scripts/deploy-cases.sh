#!/bin/bash
# deploy-cases.sh CHECKOUT OUT: scripts/host/deploy.sh in the hunt's worktree on the stand-ins of standins.sh
# (pnpm, uv, launchctl, sudo, curl and the checkout's python answer without doing anything), case by case:
# an unknown option, two dirty files, a modified core/data/biorepo.json with and without a database named,
# a rebase left half-done, --no-pull --no-restart, and --verify with each source of the tests' server.
# Restores the worktree's tracked files after each case (git checkout in the worktree alone).
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"
export HOME="$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
# pnpm prints the tests' server it was given for verify.
cat > "$OUT/standins/bin/pnpm" <<EOF
#!/bin/bash
printf '%s\n' "pnpm \$* TEST_DB=\${OPENFERMENT_TEST_DATABASE_URL:-<unset>} UV_FROZEN=\${UV_FROZEN:-<unset>}" >> "$OUT/standins/calls"
EOF
chmod 755 "$OUT/standins/bin/pnpm"
unset OPENFERMENT_TEST_DATABASE_URL OPENFERMENT_DATABASE_URL
run() { # run LABEL ARGS...
  local label="$1"; shift
  : > "$OUT/standins/calls"
  (cd "$CO" && /bin/bash scripts/host/deploy.sh "$@") > "$OUT/out" 2>&1; local s=$?
  printf '== %s (exit %s)\n' "$label" "$s"; grep -v '^$' "$OUT/out" | grep -v '^── ' | sed 's/^/   /' | head -4
  grep -E '^pnpm (verify|build)|^launchctl|^sudo' "$OUT/standins/calls" | sed 's/^/   call: /'
}
reset() { git -C "$CO" checkout -q -- . ; git -C "$CO" clean -qfd core/data >/dev/null 2>&1; rm -f "$CO/core/.env"; }

reset; run "unknown option" --fast
reset; echo x >> "$CO/README.md"; echo x >> "$CO/package.json"; run "two dirty files" --no-pull
reset; echo ' ' >> "$CO/core/data/biorepo.json"; run "biorepo.json modified, no database named" --no-pull
reset; echo ' ' >> "$CO/core/data/biorepo.json"; echo "OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment" > "$CO/core/.env"
run "biorepo.json modified, database named" --no-pull
reset; mkdir -p "$(git -C "$CO" rev-parse --git-path rebase-merge)"; run "a rebase left half-done" --no-pull
rmdir "$(git -C "$CO" rev-parse --git-path rebase-merge)"
reset; run "--no-pull --no-restart" --no-pull --no-restart
reset; run "--no-pull, no job installed" --no-pull
reset; echo "OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment" > "$CO/core/.env"
run "--verify, the tests' server from the live address" --verify --no-pull --no-restart
reset; echo "OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment?sslmode=disable" > "$CO/core/.env"
run "--verify, a live address with a query" --verify --no-pull --no-restart
reset; run "--verify, nothing named" --verify --no-pull --no-restart
reset; printf 'OPENFERMENT_TEST_DATABASE_URL="postgresql://t@127.0.0.1:5433/x"\n' > "$CO/core/.env"
run "--verify, core/.env names the tests' server" --verify --no-pull --no-restart
reset
