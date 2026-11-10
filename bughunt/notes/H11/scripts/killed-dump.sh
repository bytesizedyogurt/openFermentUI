#!/bin/bash
# killed-dump.sh LIB OUT: the night's dump stopped half way by SIGTERM to its process group (what launchd sends a
# job it stops, and what a restart sends every process), then three ordinary nights. Prints what the folder
# holds after each: a .part file is left by the stopped night, and no later night removes it.
set -uo pipefail
LIB="$1"; OUT="$2"
rm -rf "$OUT"; mkdir -p "$OUT/bin" "$OUT/keg/bin" "$OUT/home"
cat > "$OUT/bin/brew" <<EOF
#!/bin/bash
[ "\$*" = "--prefix --installed postgresql@17" ] && echo "$OUT/keg" && exit 0
exit 1
EOF
cat > "$OUT/bin/date" <<EOF
#!/bin/bash
if [ "\$*" = "+%F" ]; then cat "$OUT/today"; else exec /usr/bin/date "\$@"; fi
EOF
# pg_dump writes half, then waits $OUT/slow seconds before writing the rest.
cat > "$OUT/keg/bin/pg_dump" <<EOF
#!/bin/bash
for a in "\$@"; do case "\$a" in --file=*) out="\${a#--file=}" ;; esac; done
printf 'first half\n' > "\$out"; sleep "\$(cat "$OUT/slow")"; printf 'second half\n' >> "\$out"
EOF
chmod 755 "$OUT/bin/brew" "$OUT/bin/date" "$OUT/keg/bin/pg_dump"
night() {
  printf '%s' "$1" > "$OUT/today"; printf '%s' "$2" > "$OUT/slow"
  setsid env PATH="$OUT/bin:/usr/bin:/bin" HOME="$OUT/home" bash -c 'set -uo pipefail; source "$1"; backup_database' _ "$LIB" \
    >> "$OUT/log" 2>&1 &
  local pid=$!
  if [ "$3" = stop ]; then sleep 1; kill -TERM -- "-$pid"; fi
  wait "$pid"; echo "night $1: exit $? ; folder: $(ls "$OUT/home/openferment-backups" | tr '\n' ' ')"
}
night 2026-11-10 5 stop
night 2026-11-11 0 run
night 2026-11-12 0 run
night 2026-11-13 0 run
