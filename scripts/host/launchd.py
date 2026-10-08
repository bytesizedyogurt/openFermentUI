"""The Mac Mini's two LaunchDaemons (OF-BLD-012 §B.5, §B.8).

    python scripts/host/launchd.py --repo DIR --user NAME --home DIR \
        --path PATH --out DIR [--host 127.0.0.1] [--port 8000]

writes `com.umutuzo.openferment.plist` (the server) and
`com.umutuzo.openferment.nightly.plist` (fetch and extract at 03:00) into
--out. `install.sh` calls this and copies both into /Library/LaunchDaemons.
They are rendered here, by plistlib, so they are valid by construction and
can be checked on any operating system (core/tests/test_host.py).

A LaunchDaemon starts at power-on, before anyone logs in, and keeps running
with the screen locked. `UserName` makes each job run as the person who owns
the checkout and never as root: every file it writes belongs to them, and
core/.env is read with their permissions and nobody else's.

The server binds to loopback. The service has no login of its own (Guild's
write endpoint answers whoever reaches it), so the bind address IS the access
control, the rule scripts/lib/serve-dist.mjs follows for the test servers
(OF-BLD-012.1 §6.9). `tailscale serve`, which install.sh sets up, publishes
the loopback port to the owner's own signed-in devices over HTTPS.

Nothing here reads the key or writes it anywhere.
"""
from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path

SERVER = "com.umutuzo.openferment"
NIGHTLY = "com.umutuzo.openferment.nightly"
LOOPBACK = "127.0.0.1"
PORT = 8000
NIGHTLY_AT = {"Hour": 3, "Minute": 0}


def log_dir(home: Path) -> Path:
    """Where both jobs write: the per-user logs folder Console.app reads."""
    return home / "Library" / "Logs" / "openferment"


def daemons(
    repo: Path,
    user: str,
    home: Path,
    path: str,
    host: str = LOOPBACK,
    port: int = PORT,
) -> dict[str, dict]:
    """Label → plist contents for the server and the nightly job."""
    if not repo.is_absolute() or not home.is_absolute():
        raise ValueError("--repo and --home must be absolute; launchd has no working directory to resolve against")
    if not user or user == "root":
        raise ValueError("the jobs run as the person who owns the checkout, never as root")
    if not 0 < port < 65536:
        raise ValueError(f"port {port} is not a port")

    core = repo / "core"
    logs = log_dir(home)
    common = {
        "UserName": user,
        "GroupName": "staff",
        # launchd starts a daemon with almost no environment. PATH carries the
        # Homebrew tools (uv, node, git) and HOME is where uv keeps its cache.
        "EnvironmentVariables": {"PATH": path, "HOME": str(home), "PYTHONUNBUFFERED": "1"},
    }
    return {
        SERVER: {
            "Label": SERVER,
            **common,
            # The venv's own interpreter, which `uv sync` in deploy.sh keeps
            # current: no network and no lock resolution at boot.
            "ProgramArguments": [
                str(core / ".venv" / "bin" / "python"),
                "-m",
                "uvicorn",
                "openferment_core.api:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            "WorkingDirectory": str(core),
            "RunAtLoad": True,
            "KeepAlive": True,
            "ThrottleInterval": 10,
            "StandardOutPath": str(logs / "server.log"),
            "StandardErrorPath": str(logs / "server.log"),
        },
        NIGHTLY: {
            "Label": NIGHTLY,
            **common,
            "ProgramArguments": ["/bin/bash", str(repo / "scripts" / "host" / "nightly.sh")],
            "WorkingDirectory": str(repo),
            "StartCalendarInterval": dict(NIGHTLY_AT),
            "RunAtLoad": False,
            "StandardOutPath": str(logs / "nightly.log"),
            "StandardErrorPath": str(logs / "nightly.log"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render openFerment's LaunchDaemon plists.")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--user", required=True)
    ap.add_argument("--home", required=True, type=Path)
    ap.add_argument("--path", required=True, help="PATH the jobs run with")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--host", default=LOOPBACK)
    ap.add_argument("--port", default=PORT, type=int)
    a = ap.parse_args(argv)
    try:
        jobs = daemons(a.repo, a.user, a.home, a.path, a.host, a.port)
    except ValueError as e:
        print(f"launchd.py: {e}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    for label, job in jobs.items():
        target = a.out / f"{label}.plist"
        target.write_bytes(plistlib.dumps(job, sort_keys=False))
        print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
