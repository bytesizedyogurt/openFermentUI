#!/bin/bash
# pipefail-grep-q.sh: the mechanism behind install.sh's `tailscale serve status 2>/dev/null | grep -q ":$PORT"`
# under `set -o pipefail`: a writer that prints its matching line and then one more line after grep -q has
# exited dies of SIGPIPE, and the pipeline reads as false. The writer stands in for tailscale; whether the
# real CLI writes after its matching line, and late enough, is not known here.
set -o pipefail
writer() { echo "https://mini.tailnet.ts.net (tailnet only)"; echo "|-- / proxy http://127.0.0.1:8000"; sleep 0.2; echo; }
if writer | grep -q ":8000"; then echo "taken as serving"; else echo "taken as not serving (pipeline status ${PIPESTATUS[*]})"; fi
