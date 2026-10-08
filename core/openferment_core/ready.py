"""Is this machine ready for the live loop? (OF-BLD-012 §B.9)

    pnpm ready                 every check
    pnpm ready --no-network    only what needs no network

One line per check: ✓ ready, ! works with a gap worth knowing, ✗ the live
loop fails here, · skipped. Each ✗ and ! says what to do. Exits 1 when any
check is ✗, so install.sh and deploy.sh can show it.

It spends nothing. The model check asks Anthropic's Models API whether the key
may use MODEL, which is free and is also how a retired model shows up before a
real call fails; the Europe PMC check is one search. The key itself is never
printed, in whole or in part.
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
from .postdoc import MODEL

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
    for path in intake.FULLTEXT_DIR.glob("*.json"):
        hit = intake.cached(path.stem)
        if hit is not None and hit.status == "complete":
            complete += 1
        else:
            missed += 1
    extracted = len(list(extract.CANDIDATES_DIR.glob("*.json")))
    summary = f"{complete} papers fetched with full text, {missed} misses cached, {extracted} extracted"
    if complete == 0:
        return Check("intake", "warn", f"{summary}. Fetch now: scripts/host/nightly.sh (or pnpm intake:fetch --all)")
    return Check("intake", "ok", summary)


# ── what is out there ──────────────────────────────────────────────────


def check_model(have_key: bool, client_factory: Callable[[], object] | None = None) -> Check:
    if not have_key:
        return Check("model", "skip", "needs the key")
    if intake.fixtures_only():
        return Check("model", "skip", "OPENFERMENT_FIXTURES is set")
    import anthropic

    client = (client_factory or anthropic.Anthropic)()
    try:
        client.models.retrieve(MODEL, timeout=15)
    except anthropic.AuthenticationError:
        return Check("model", "fail", "Anthropic rejected the key. Make a new one in the console and put it in core/.env")
    except anthropic.PermissionDeniedError:
        return Check("model", "fail", f"the key may not use {MODEL}")
    except anthropic.NotFoundError:
        return Check("model", "fail", f"{MODEL} is not available to this key; it may have been retired. "
                     "The model name and its prices are at the top of core/openferment_core/postdoc.py")
    except anthropic.APIConnectionError:
        return Check("model", "fail", "could not reach api.anthropic.com")
    except anthropic.APIStatusError as e:
        return Check("model", "fail", f"api.anthropic.com answered {e.status_code}")
    return Check("model", "ok", f"the key is accepted and {MODEL} is available")


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


def check_service(port: int, have_key: bool) -> Check:
    try:
        body = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=3).json()
    except (httpx.HTTPError, ValueError):
        return Check("service", "warn", f"nothing answers on 127.0.0.1:{port}. Expected before install.sh; "
                     "after it: sudo launchctl kickstart -k system/com.umutuzo.openferment")
    if have_key and not body.get("hasKey"):
        return Check("service", "warn", "running, but started before the key was added. "
                     "Restart it: sudo launchctl kickstart -k system/com.umutuzo.openferment")
    if not body.get("ok"):
        return Check("service", "warn", f"running, but reports: {body.get('corpusError') or 'not ok'}")
    return Check("service", "ok", f"answers on 127.0.0.1:{port} with {body.get('records')} records")


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
    port = port or int(os.environ.get("OPENFERMENT_PORT", "8000"))
    key = check_key()
    have_key = key.mark in ("ok", "warn")
    checks = [key, check_corpus(), check_build(), check_data(), check_intake()]
    if no_network:
        checks += [Check(n, "skip", "--no-network") for n in ("model", "europepmc", "backup")]
    else:
        checks += [check_model(have_key), check_europe_pmc(), check_backup()]
    checks.append(check_service(port, have_key))
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
