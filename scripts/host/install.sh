#!/bin/bash
# Make this Mac openFerment's always-on host (OF-BLD-012 Appendix B, §B.3–B.6
# and §B.8). Run as yourself, from the checkout, after `git clone`:
#
#   scripts/host/install.sh              install, or reinstall after a change here
#   scripts/host/install.sh --uninstall  stop both jobs and remove them
#
# What it does, in order: checks the tools and where the checkout lives;
# builds the app and the service's environment; sets the power settings an
# always-on machine needs; installs two LaunchDaemons (the server, which starts
# at power-on before anyone logs in, and the 03:00 fetch-and-extract); waits for
# /api/health; then publishes the port to your own devices with Tailscale.
#
# It asks for your password (sudo) for the power settings and for the two files
# it puts in /Library/LaunchDaemons. It never reads the key and never prints it.
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$REPO"

[ "$(uname -s)" = Darwin ] || die "install.sh sets up macOS launchd jobs, and this machine runs $(uname -s)."
[ "$(id -u)" != 0 ] || die "run this as yourself, without sudo. It asks for your password when it needs it, and the jobs must belong to you."

if [ "${1:-}" = --uninstall ]; then
  for label in "$SERVER" "$NIGHTLY"; do
    sudo launchctl bootout "system/$label" 2>/dev/null || true
    sudo rm -f "$DAEMONS/$label.plist"
  done
  # Only openFerment's own serve: `serve reset` would remove every one.
  command -v tailscale >/dev/null && tailscale_cli serve --https=443 off >/dev/null 2>&1 || true
  say "Both jobs are stopped and removed. The checkout and core/data are untouched."
  exit 0
fi
[ -z "${1:-}" ] || die "unknown option $1. Usage: install.sh [--uninstall]"
install_address

say "Checking the checkout and the tools"
# macOS privacy protection stops background jobs reading these folders: the
# service would start, then fail to open its own files.
case "$REPO/" in
  "$HOME"/Documents/* | "$HOME"/Desktop/* | "$HOME"/Downloads/* | "$HOME/Library/Mobile Documents"/*)
    die "the checkout is at $REPO. macOS blocks background jobs from reading Documents, Desktop, Downloads and iCloud Drive. Move it to $HOME/openferment and run this again." ;;
esac
for tool in git node pnpm uv curl; do
  command -v "$tool" >/dev/null || die "$tool is not installed. Run: brew install $tool"
done
if has_key; then
  echo "core/.env holds a key."
else
  echo "core/.env holds no key yet. The app runs; Postdoc's Live mode and Extract stay off until you"
  echo "copy core/.env.example to core/.env and add one (set a spend cap in the Anthropic console first)."
fi

"$REPO/scripts/host/deploy.sh" --no-pull --no-restart

say "Power: never sleep, restart after a power failure, wake for network access"
sudo pmset -a sleep 0 autorestart 1 womp 1
if fdesetup isactive >/dev/null 2>&1; then
  echo "FileVault is on: after a power cut the Mini waits at the unlock screen until someone types"
  echo "the password, and the service starts after that. Planned restarts: sudo fdesetup authrestart"
fi

say "Installing the two LaunchDaemons"
mkdir -p "$LOGS"
# The jobs start with almost no environment; give them the folders these tools live in.
JOB_PATH="$(for t in uv node pnpm git; do dirname "$(command -v "$t")"; done | awk '!seen[$0]++' | paste -sd: -):/usr/bin:/bin:/usr/sbin:/sbin"
STAGE="$(mktemp -d)"
"$REPO/core/.venv/bin/python" "$REPO/scripts/host/launchd.py" \
  --repo "$REPO" --user "$(id -un)" --home "$HOME" --path "$JOB_PATH" \
  --host "$HOST" --port "$PORT" --out "$STAGE" >/dev/null
plutil -lint "$STAGE"/*.plist
for label in "$SERVER" "$NIGHTLY"; do
  sudo launchctl bootout "system/$label" 2>/dev/null && sleep 1 || true
  sudo install -m 644 -o root -g wheel "$STAGE/$label.plist" "$DAEMONS/$label.plist"
  sudo launchctl bootstrap system "$DAEMONS/$label.plist"
done
rm -rf "$STAGE"

say "Waiting for the service"
wait_for_health

say "Reaching it from your other devices"
if [ "$HOST" != 127.0.0.1 ]; then
  echo "The server listens on $HOST:$PORT (OPENFERMENT_HOST), so Tailscale is left alone."
elif command -v tailscale >/dev/null && tailscale status >/dev/null 2>&1; then
  # The Tailscale apps (App Store and standalone) run only while someone is
  # logged in; only the background service, tailscaled, runs from power-on,
  # which is what a host that restarts itself after a power cut needs.
  if ! pgrep -x tailscaled >/dev/null; then
    echo "Tailscale here is the app, which runs only while someone is logged in: after a restart the Mini"
    echo "is unreachable until a login. For an always-on host, quit the app and use the background service:"
    echo "  brew install tailscale && sudo brew services start tailscale && sudo tailscale up"
    echo "then run this again."
  fi
  # Shown, never hidden: when HTTPS is off for the tailnet, this prints the link
  # that turns it on, and still exits 0. The status check below is the answer.
  tailscale_cli serve --bg "$PORT" || true
  if tailscale serve status 2>/dev/null | grep -q ":$PORT"; then
    tailscale serve status
  else
    echo "Tailscale is not serving it yet. If a link to enable HTTPS appeared above, open it, then run:"
    echo "  tailscale serve --bg $PORT"
  fi
else
  echo "Tailscale is not installed or not signed in. For an always-on host, use its background service:"
  echo "  brew install tailscale && sudo brew services start tailscale && sudo tailscale up"
  echo "then run this again. It publishes the service over HTTPS to the devices your tailnet allows"
  echo "(by default, only yours), and opens nothing on the router."
fi

say "Checking the live loop"
run_ready

say "Done"
cat <<EOF
On this Mac:      http://127.0.0.1:$PORT
Logs:             tail -f "$LOGS/server.log"   ·   "$LOGS/nightly.log"
After a change:   scripts/host/deploy.sh
Nightly intake:   03:00, or now by hand: scripts/host/nightly.sh
Is it all wired:  pnpm ready
EOF
