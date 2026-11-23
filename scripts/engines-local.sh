#!/bin/bash
# The engines this machine keeps installed beside core/uv.lock (alpha 2.2 D0.11).
#
#   bash scripts/engines-local.sh
#
# `uv sync` keeps only what core/uv.lock names, so an engine package installed
# into core's environment with `uv pip install -e <path>` leaves with each sync.
# core/engines.local (ignored by git) names each one to keep: one package
# directory a line, relative to core/ or absolute; a line whose first character
# past its spaces is # is a comment, and a blank line is skipped. This script
# installs each named directory again (`uv pip install -e`), and
# scripts/session-start.sh and scripts/host/deploy.sh run it after their
# `uv sync`, so `pnpm session:start`, `pnpm prototype:up` and a deploy keep the
# engines it names. An engine is taken out with its line and
# `cd core && uv pip uninstall <distribution>`.
#
# EVERY PACKAGE core/uv.lock PINS STAYS AT ITS LOCKED VERSION. The lock's
# versions (`uv export --frozen`) are each install's constraints, so a package
# whose dependencies would move one (BioSTEAM, thermosteam and biorefineries
# among them) is refused in uv's words and installs nothing; a dependency the
# lock does not name is installed beside it, and `pnpm check:licences` holds
# it to core/licences.toml.
#
# With no core/engines.local it says so and exits 0. A line naming no
# directory, and a directory that fails to install, are each said in words,
# the rest installed, and it exits 1; a lock that cannot be read as the
# constraints is said in words, nothing installed, and it exits 1.
#
# The tests name another list and another uv (OPENFERMENT_ENGINES_LOCAL,
# OPENFERMENT_UV); a machine names neither.
set -uo pipefail
cd "$(dirname "$0")/../core" || exit 1

list="${OPENFERMENT_ENGINES_LOCAL:-engines.local}"
uv="${OPENFERMENT_UV:-uv}"

if [ ! -f "$list" ]; then
  echo "no core/engines.local, so no engine is installed beside core/uv.lock"
  exit 0
fi

# The lock's versions, the constraints every install below is held to.
constraints="$(mktemp)" || exit 1
trap 'rm -f "$constraints"' EXIT
if ! "$uv" export --frozen --all-extras --no-hashes --no-emit-project --quiet > "$constraints"; then
  echo "✗ core/uv.lock could not be read as the installs' constraints (uv export --frozen), so no engine was installed"
  exit 1
fi

failed=0
named=0
while IFS= read -r line || [ -n "$line" ]; do
  # The line without the spaces around it.
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  case "$line" in
    "" | "#"*) continue ;;
  esac
  named=$((named + 1))
  case "$line" in
    /*) path="$line" ;;
    *) path="$PWD/$line" ;;
  esac
  if [ ! -d "$path" ]; then
    echo "✗ core/engines.local names $line, and no directory is there"
    failed=1
    continue
  fi
  if "$uv" pip install --python .venv/bin/python -c "$constraints" -e "$path"; then
    echo "installed $line into core's environment, beside core/uv.lock"
  else
    echo "✗ $line did not install (uv pip install -e, each package core/uv.lock pins held at its locked version); the lines above say why"
    failed=1
  fi
done < "$list"

[ "$named" -gt 0 ] || echo "core/engines.local names no engine"
exit "$failed"
