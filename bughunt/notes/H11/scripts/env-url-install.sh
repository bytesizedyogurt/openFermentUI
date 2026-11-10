#!/bin/bash
# env-url-install.sh CHECKOUT OUT: install.sh on the stand-ins of standins.sh, run from a shell that exports
# OPENFERMENT_DATABASE_URL while core/.env (runbook step 1's file) names no database. Prints what install.sh
# said about the database, the database line core/.env holds afterwards (as python-dotenv reads it, the way the
# service reads core/.env), and the environment the server's LaunchDaemon was given.
# A second case exports the example's development address, and prints the refusal's advice.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"; export HOME="$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
for url in postgresql://sean@127.0.0.1:5432/openferment \
           postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev; do
  rm -f "$CO/core/.env"; (umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' "$CO/core/.env.example" > "$CO/core/.env")
  rm -rf "$OUT/standins/daemons"/* "$OUT/standins/state"/*
  (cd "$CO" && OPENFERMENT_DATABASE_URL="$url" /bin/bash scripts/host/install.sh) > "$OUT/out" 2>&1
  echo "== the shell exports OPENFERMENT_DATABASE_URL=$url; install.sh exit $?"
  grep -n -i 'database\|OPENFERMENT_DATABASE_URL' "$OUT/out" | sed 's/^/   said: /' | cut -c1-260
  echo "   core/.env's database, as the service reads it: $(/home/user/openFermentUI/core/.venv/bin/python -I -c '
import sys; from dotenv import dotenv_values; print(dotenv_values(sys.argv[1]).get("OPENFERMENT_DATABASE_URL"))' "$CO/core/.env")"
  [ -f "$OUT/standins/daemons/com.umutuzo.openferment.plist" ] &&
    echo "   the server job's environment: $(/home/user/openFermentUI/core/.venv/bin/python -I -c '
import plistlib, sys; print(sorted(plistlib.loads(open(sys.argv[1], "rb").read())["EnvironmentVariables"]))' \
    "$OUT/standins/daemons/com.umutuzo.openferment.plist")"
done
rm -f "$CO/core/.env"
