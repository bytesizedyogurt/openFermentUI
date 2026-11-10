#!/bin/bash
# cdpath.sh CHECKOUT OUT: scripts/host/install.sh run as the runbook writes it (scripts/host/install.sh from the
# checkout), on the stand-ins of standins.sh, with CDPATH exported as `.:$HOME` (a setting some shells' profiles
# export). lib.sh's `cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd` then prints the directory twice.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"; export HOME="$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
for cdp in "" ".:$HOME"; do
  (cd "$CO" && env CDPATH="$cdp" /bin/bash scripts/host/install.sh) > "$OUT/out" 2>&1
  echo "== CDPATH='$cdp': install.sh exit $?"; head -3 "$OUT/out" | sed 's/^/   /'
done
rm -f "$CO/core/.env"
