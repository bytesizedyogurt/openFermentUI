#!/bin/bash
# install-twice.sh CHECKOUT OUT: run scripts/host/install.sh twice from CHECKOUT (a worktree of the
# hunt's own, reached through a path with a space) against the stand-ins of standins.sh, with a
# scratch HOME holding a space, and snapshot what each run left: the daemons folder, the jobs
# launchd holds, core/.env, the logs folder and the calls each stand-in received.
# Nothing here reaches launchd, PostgreSQL, Tailscale or the network.
set -uo pipefail
CO="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT"
SPACED="$OUT/check out"          # the checkout, reached by a path with a space
ln -s "$CO" "$SPACED"
export HOME="$OUT/home dir"      # a HOME with a space
mkdir -p "$HOME"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
unset OPENFERMENT_HOST OPENFERMENT_PORT OPENFERMENT_DATABASE_URL OPENFERMENT_API_KEY ANTHROPIC_API_KEY
# core/.env as the runbook's step 1 leaves it: the example, its database line taken out.
rm -f "$CO/core/.env"
(umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' "$CO/core/.env.example" > "$CO/core/.env")

snap() { # snap N
  local s="$OUT/run$1"; mkdir -p "$s"
  cp -R "$OUT/standins/daemons" "$s/daemons"
  cp -R "$OUT/standins/state" "$s/state"
  cp "$CO/core/.env" "$s/core.env"
  stat -c '%a %n' "$CO/core/.env" > "$s/modes"
  (cd "$HOME" && find . -printf '%M %p\n' | sort) > "$s/home.txt"
  mv "$OUT/standins/calls" "$s/calls"; : > "$OUT/standins/calls"
}
for n in 1 2; do
  (cd "$SPACED" && /bin/bash scripts/host/install.sh) > "$OUT/run$n.out" 2>&1
  echo "run $n exit $?" | tee -a "$OUT/exits"
  snap "$n"
done
echo "== differences between the state the two runs left (daemons, launchd, core/.env, HOME):"
diff -r "$OUT/run1/daemons" "$OUT/run2/daemons" && diff -r "$OUT/run1/state" "$OUT/run2/state" &&
  diff "$OUT/run1/core.env" "$OUT/run2/core.env" && diff "$OUT/run1/home.txt" "$OUT/run2/home.txt" &&
  diff "$OUT/run1/modes" "$OUT/run2/modes" && echo "none"
echo "== differences between the calls the two runs made:"
diff "$OUT/run1/calls" "$OUT/run2/calls"
