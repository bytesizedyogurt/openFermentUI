"""Is this machine ready for the live loop? (OF-BLD-012 §B.9)

    pnpm ready                 every check
    pnpm ready --no-network    only what needs no network

One line per check: ✓ ready, ! works with a gap worth knowing, ✗ the live
loop fails here, · skipped. Each ✗ and ! says what to do. Exits 1 when any
check is ✗, so install.sh and deploy.sh can show it.

It spends nothing. The model check asks Anthropic's Models API whether the key
may use each model in the chain (llm.py: Opus, then Sonnet), which is free and
is also how a retired model shows up before a real call fails; the Europe PMC
check is one search. The key itself is never printed, in whole or in part.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
from dotenv import load_dotenv

from . import biorepo, extract, intake
from .corpus import load_corpus
from . import llm

CORE = Path(__file__).parent.parent
REPO = CORE.parent
MARKS = {"ok": "✓", "warn": "!", "fail": "✗", "skip": "·"}
PLACEHOLDER_KEY = "sk-ant-..."
# A paper with a PMCID in the seed: B5's, the one the offline demo replays.
PROBE_PMCID = "PMC8471596"
# Where api.py mounts the build from, worked out the same way and kept equal to
# it by test_ready; importing api for it would start the app and log as it.
DIST_DIR = intake._env_path("OPENFERMENT_DIST_DIR", REPO / "dist")


@dataclass
class Check:
    name: str
    mark: str  # one of MARKS
    detail: str


# ── what is on disk ────────────────────────────────────────────────────


def check_key() -> Check:
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key or key == PLACEHOLDER_KEY:
        return Check("key", "fail", "core/.env holds no key. Postdoc's Live mode and Extract need one: set a "
                     "spend cap in the Anthropic console, copy core/.env.example to core/.env, add the key")
    if not key.startswith("sk-ant-"):
        return Check("key", "warn", "core/.env holds a key that does not start the way Anthropic keys do")
    return Check("key", "ok", "core/.env holds a key")


def check_corpus() -> Check:
    try:
        corpus = load_corpus()
    except FileNotFoundError:
        return Check("corpus", "fail", "the service has no corpus to answer from. Run: pnpm export:corpus")
    except (ValueError, KeyError):
        return Check("corpus", "fail", "the corpus projection is damaged. Run: pnpm export:corpus")
    return Check("corpus", "ok", f"{len(corpus.records)} records on {len(corpus.papers)} papers")


def check_build() -> Check:
    if (DIST_DIR / "index.html").is_file():
        return Check("app", "ok", "built; the service serves it at /")
    return Check("app", "warn", "not built, so the service answers /api alone. Run: pnpm build")


def check_data() -> Check:
    folder = biorepo.PATH.parent
    if folder.exists() and not os.access(folder, os.W_OK):
        return Check("data", "fail", f"{folder} is not writable, so Guild decisions cannot be kept")
    try:
        repo = biorepo.read()
    except ValueError as e:
        return Check("data", "fail", f"core/data/biorepo.json does not parse: {str(e).splitlines()[0]}")
    n = len(repo.decisions)
    return Check("data", "ok", f"{n} review decision{'s' if n != 1 else ''} in core/data/biorepo.json")


def check_intake() -> Check:
    complete = missed = 0
    damaged: list[str] = []
    for path in sorted(intake.FULLTEXT_DIR.glob("*.json")):
        try:
            hit = intake.cached(path.stem)
        except ValueError:
            damaged.append(path.name)
            continue
        if hit is not None and hit.status == "complete":
            complete += 1
        else:
            missed += 1
    extracted = len(list(extract.CANDIDATES_DIR.glob("*.json")))
    summary = f"{complete} papers fetched with full text, {missed} misses cached, {extracted} extracted"
    if damaged:
        return Check("intake", "warn", f"{summary}; {len(damaged)} damaged ({', '.join(damaged[:5])}). "
                     "Delete them from core/data/fulltext/ and they are fetched again tonight")
    if complete == 0:
        return Check("intake", "warn", f"{summary}. Fetch now: scripts/host/nightly.sh (or pnpm intake:fetch --all)")
    return Check("intake", "ok", summary)


# ── what is out there ──────────────────────────────────────────────────


def check_model(have_key: bool, client_factory: Callable[[], object] | None = None) -> Check:
    """Both models in the chain, through the free Models API: the primary every
    call starts on and the fallback it moves to (llm.py)."""
    if llm.effort() not in llm.EFFORTS:
        return Check("model", "fail", f"OPENFERMENT_EFFORT={llm.effort()} is not one of "
                     f"{', '.join(llm.EFFORTS)}, so every call would be refused")
    if not have_key:
        return Check("model", "skip", "needs the key")
    if intake.fixtures_only():
        return Check("model", "skip", "OPENFERMENT_FIXTURES is set")
    import anthropic

    client = (client_factory or anthropic.Anthropic)()
    offered: list[str] = []
    missing: list[str] = []
    for model in llm.chain():
        try:
            client.models.retrieve(model, timeout=15)
        except anthropic.AuthenticationError:
            return Check("model", "fail", "Anthropic rejected the key. Make a new one in the console and put it in core/.env")
        except (anthropic.PermissionDeniedError, anthropic.NotFoundError):
            missing.append(model)
            continue
        except anthropic.APIConnectionError:
            return Check("model", "fail", "could not reach api.anthropic.com")
        except anthropic.APIStatusError as e:
            return Check("model", "fail", f"api.anthropic.com answered {e.status_code}")
        offered.append(model)
    unpriced = [m for m in offered if m not in llm.PRICES]
    if not offered:
        return Check("model", "fail", f"no model in the chain is available to this key ({', '.join(missing)}). "
                     "Set OPENFERMENT_MODEL in core/.env to one that is")
    if missing:
        return Check("model", "warn", f"{', '.join(missing)} is not available to this key, so every call runs on "
                     f"{', '.join(offered)}. Set OPENFERMENT_MODEL or OPENFERMENT_FALLBACK_MODEL in core/.env")
    if unpriced:
        return Check("model", "warn", f"no price on file for {', '.join(unpriced)}, so its cost shows as $0. "
                     "Add it to PRICES in core/openferment_core/llm.py")
    return Check("model", "ok", f"the key is accepted; {' then '.join(offered)}, effort {llm.effort()}")


def check_europe_pmc() -> Check:
    if intake.fixtures_only():
        return Check("europepmc", "skip", "OPENFERMENT_FIXTURES is set")
    try:
        r = intake._get(
            f"{intake.EUROPE_PMC}/search",
            params={"query": f"PMCID:{PROBE_PMCID}", "format": "json", "resultType": "lite"},
        )
    except httpx.HTTPError as e:
        return Check("europepmc", "fail", f"could not reach Europe PMC: {type(e).__name__}")
    if r.status_code != 200:
        return Check("europepmc", "fail", f"Europe PMC answered {r.status_code}")
    return Check("europepmc", "ok", "Europe PMC answers")


def _launchd():
    import importlib.util

    spec = importlib.util.spec_from_file_location("of_launchd", REPO / "scripts" / "host" / "launchd.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def service_address() -> tuple[str, int]:
    """Where to ask the service for its health: the environment first (what
    install.sh and deploy.sh pass), else the address the installed server
    job was given, else 127.0.0.1:8000. So `pnpm ready` typed by hand asks
    the job where it actually listens."""
    host, port = os.environ.get("OPENFERMENT_POLL_HOST"), os.environ.get("OPENFERMENT_PORT")
    launchd = _launchd()
    plist = Path(os.environ.get("OPENFERMENT_LAUNCHD_DIR", "/Library/LaunchDaemons")) / f"{launchd.SERVER}.plist"
    installed: tuple[str, int] | None = None
    if not (host and port) and plist.is_file():
        try:
            installed = launchd.installed_address(plist)
        except (OSError, ValueError, KeyError, IndexError):
            installed = None
    return (
        host or launchd.poll_host(installed[0] if installed else ""),
        int(port) if port else (installed[1] if installed else 8000),
    )


def check_service(port: int, have_key: bool, host: str = "127.0.0.1") -> Check:
    try:
        body = httpx.get(f"http://{host}:{port}/api/health", timeout=3).json()
    except (httpx.HTTPError, ValueError):
        return Check("service", "warn", f"nothing answers on {host}:{port}. Expected before install.sh; "
                     "after it: sudo launchctl kickstart -k system/com.umutuzo.openferment")
    if have_key and not body.get("hasKey"):
        return Check("service", "warn", "running, but started before the key was added. "
                     "Restart it: sudo launchctl kickstart -k system/com.umutuzo.openferment")
    if not body.get("ok"):
        return Check("service", "warn", f"running, but reports: {body.get('corpusError') or 'not ok'}")
    return Check("service", "ok", f"answers on {host}:{port} with {body.get('records')} records")


def check_backup() -> Check:
    if intake.fixtures_only():
        return Check("backup", "skip", "OPENFERMENT_FIXTURES is set")
    try:
        r = subprocess.run(
            ["git", "push", "--dry-run", "origin", "HEAD"],
            cwd=REPO, capture_output=True, text=True, timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""},
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return Check("backup", "warn", f"could not ask GitHub: {type(e).__name__}")
    said = (r.stdout + r.stderr).lower()
    # A dry run that GitHub answered at all, accepted or rejected as behind,
    # means the credentials work.
    if r.returncode == 0 or "rejected" in said:
        return Check("backup", "ok", "this checkout can push, so Guild decisions made here can be backed up")
    if "not a git repository" in said:
        return Check("backup", "skip", "not a git checkout")
    return Check("backup", "warn", "this checkout cannot push to GitHub, so decisions made here stay on this "
                 "machine. Sign in once: gh auth login (or set up an SSH key)")


# ── the report ─────────────────────────────────────────────────────────


def run(no_network: bool = False, port: int | None = None) -> list[Check]:
    load_dotenv(CORE / ".env", override=False)
    host, found_port = service_address()
    port = port or found_port
    key = check_key()
    have_key = key.mark in ("ok", "warn")
    checks = [key, check_corpus(), check_build(), check_data(), check_intake()]
    if no_network:
        checks += [Check(n, "skip", "--no-network") for n in ("model", "europepmc", "backup")]
    else:
        checks += [check_model(have_key), check_europe_pmc(), check_backup()]
    checks.append(check_service(port, have_key, host))
    return checks


def report(checks: list[Check]) -> str:
    width = max(len(c.name) for c in checks)
    lines = ["openFerment: is this machine ready for the live loop?", ""]
    lines += [f"{MARKS[c.mark]} {c.name:<{width}}  {c.detail}" for c in checks]
    failed = sum(c.mark == "fail" for c in checks)
    lines.append("")
    lines.append(
        f"{failed} problem{'s' if failed != 1 else ''}. Fix the ✗ lines, then run pnpm ready again."
        if failed else "Ready."
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if any(a != "--no-network" for a in argv):
        print("usage: python -m openferment_core.ready [--no-network]")
        return 2
    checks = run(no_network="--no-network" in argv)
    print(report(checks))
    return 1 if any(c.mark == "fail" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
