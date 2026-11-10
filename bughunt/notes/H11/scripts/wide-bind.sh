#!/bin/bash
# wide-bind.sh CHECKOUT OUT: install.sh run once on the stand-ins of standins.sh with OPENFERMENT_HOST=0.0.0.0
# in the environment, as a shell that still holds it would run it. Prints what install.sh said about the
# address, the host the server's LaunchDaemon was given, and guard.refusal's answer to a POST from another
# machine on the network (Host: the Mini's LAN address, no Origin, as curl or a script sends).
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/home"
export HOME="$OUT/home"
eval "$(bash "$HERE/standins.sh" "$OUT/standins" "$CO")"
rm -f "$CO/core/.env"; (umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' "$CO/core/.env.example" > "$CO/core/.env")
(cd "$CO" && OPENFERMENT_HOST=0.0.0.0 /bin/bash scripts/host/install.sh) > "$OUT/install.out" 2>&1
echo "install.sh exit $?"
echo "--- every line install.sh printed that names the address or a warning:"
grep -n -i 'listen\|0\.0\.0\.0\|loopback\|warn\|wider' "$OUT/install.out"
echo "--- the server job's arguments:"
/home/user/openFermentUI/core/.venv/bin/python -I -c '
import plistlib, sys
a = plistlib.loads(open(sys.argv[1], "rb").read())["ProgramArguments"]
print("--host", a[a.index("--host") + 1], "--port", a[a.index("--port") + 1])' "$OUT/standins/daemons/com.umutuzo.openferment.plist"
echo "--- guard.refusal for a POST from another machine on the LAN:"
cd /home/user/openFermentUI/core && /home/user/openFermentUI/core/.venv/bin/python -I -c '
import sys; sys.path.insert(0, ".")
from openferment_core import guard
for h in ("192.168.1.20:8000", "mini.local:8000"):
    print(h, "->", guard.refusal("POST", {"host": h}) or "allowed")'
