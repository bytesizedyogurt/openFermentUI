#!/bin/bash
# nightly-cases.sh CHECKOUT OUT: scripts/host/nightly.sh in the hunt's worktree, as launchd runs it
# (/bin/bash nightly.sh, a PATH and HOME alone, HOME holding a space), on the stand-ins of standins.sh.
# The checkout's python records each module call with the two settings nightly.sh exports, and fails
# the modules FAIL names. Prints the order of the night's five steps, what each was given, and the exit.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home dir"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
cat > "$CO/core/.venv/bin/python" <<EOF
#!/bin/bash
printf '%s\n' "python \$* DB=\${OPENFERMENT_DATABASE_URL:-<unset>} PROJECT=\${OPENFERMENT_PROJECT:-<unset>}" >> "$OUT/standins/calls"
case " \${FAIL:-} " in *" \$2 "*) exit 1 ;; esac
exit 0
EOF
chmod 755 "$CO/core/.venv/bin/python"
night() { # night LABEL ENV-FILE-CONTENT [FAIL=...]
  printf '%s' "$2" > "$CO/core/.env"; : > "$OUT/standins/calls"
  env -i PATH="$PATH" HOME="$OUT/home dir" ${3:+"$3"} /bin/bash "$CO/scripts/host/nightly.sh" > "$OUT/log" 2>&1
  local s=$?
  printf '== %s: exit %s\n' "$1" "$s"
  grep -E '^(python|pg_dump)' "$OUT/standins/calls" | sed 's/^/   /'
  grep -E 'waits|failed|removed' "$OUT/log" | sed 's/^/   log: /'
}
night "a project named" $'OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment\nexport OPENFERMENT_PROJECT="ethanol" # the live one\n'
night "no project named" $'OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/openferment\n'
night "extraction fails" $'OPENFERMENT_PROJECT=ethanol\n' FAIL=openferment_core.extract
night "the URL names another database" $'OPENFERMENT_DATABASE_URL=postgresql://sean@127.0.0.1:5432/ethanol_live\nOPENFERMENT_PROJECT=ethanol\n'
rm -f "$CO/core/.env"
