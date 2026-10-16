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

The last line is the lane (OF-BLD-014 A.4), what this machine can run:
`full` with a key the Models API accepted and Europe PMC answering,
`model-only` with that key alone, `none` otherwise. The `huggingface` row is optional: a
blocked host is a warning, and it never changes the exit code.
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
from . import llm, spend

CORE = Path(__file__).parent.parent
REPO = CORE.parent
MARKS = {"ok": "✓", "warn": "!", "fail": "✗", "skip": "·"}
PLACEHOLDER_KEY = "sk-ant-..."
# A paper with a PMCID in the seed: B5's, the one the offline demo replays.
PROBE_PMCID = "PMC8471596"
# Where the meaning-match search lanes download their one model file from
# (OF-BLD-014 §4.2).
HUGGINGFACE = "https://huggingface.co"
LANES = ("full", "model-only", "none")
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


# ── what this document added (OF-BLD-014 §10.2) ───────────────────────


def _fetched_complete() -> int:
    n = 0
    for path in intake.FULLTEXT_DIR.glob("*.json"):
        try:
            hit = intake.cached(path.stem)
        except ValueError:
            continue
        n += hit is not None and hit.status == "complete"
    return n


def check_index() -> Check:
    from . import passages

    st = passages.status()
    fetched = _fetched_complete()
    detail = f"{st.papersIndexed} papers indexed of {fetched} fetched, {st.passages} passages; lane {st.chosenLane}"
    if st.papersIndexed < fetched:
        return Check("index", "warn", f"{detail}. Rebuild: pnpm index:build")
    return Check("index", "ok", detail)


def check_workers(ping: bool = True) -> Check:
    """Each simulation worker answering ping. BioSTEAM takes most of a
    minute to import, so this row is slow on a cold machine."""
    if not ping:
        return Check("workers", "skip", "--no-workers")
    from .workers import SimWorker

    said = []
    worst = "ok"
    for name, module in (("geneOS", "openferment_core.workers.geneos_worker"),
                         ("Proforma", "openferment_core.workers.proforma_worker")):
        w = SimWorker(module, timeout_s=240)
        try:
            w.ping(timeout_s=240)
            said.append(f"{name} answers")
        except Exception as e:  # any failure is the row's answer, in words
            worst = "warn"
            said.append(f"{name} does not: {_said(e)}")
        finally:
            w.close()
    return Check("workers", worst, "; ".join(said))


def check_models() -> Check:
    from . import geneos_models as shelf

    said, worst = [], "ok"
    for m in shelf.SHELF.values():
        if not m.fetched:
            said.append(f"{m.id} bundled")
            continue
        why = shelf.available(m)
        if why:
            worst = "warn"
            said.append(why)
        else:
            said.append(f"{m.id} present, sha256 {m.fetched.sha256[:12]} matches")
    return Check("models", worst, "; ".join(said))


def check_artifacts() -> Check:
    from . import artifacts

    try:
        n = len(list(artifacts.folder().glob("*.json")))
    except OSError as e:
        return Check("artifacts", "warn", f"the artifact store cannot be read: {e}")
    return Check("artifacts", "ok", f"{n} kept")


def check_spend() -> Check:
    try:
        cap = spend.daily_budget()
        day = spend.today()
        spent = sum(float(v) for v in spend._read(day)["byRole"].values())
    except (spend.BudgetSettingInvalid, spend.SpendFileDamaged) as e:
        return Check("spend", "fail", str(e))
    mark = "warn" if spent >= cap else "ok"
    return Check("spend", mark, f"${spent:.2f} of the ${cap:.2f} daily cap spent today ({day}, UTC)")


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
            return Check("model", "fail", f"api.anthropic.com answered {e.status_code}{_said(e)}")
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


def _said(e: Exception) -> str:
    """What the API said about a refused request, from its error body, cut
    short. The body describes the request and never holds the key."""
    body = getattr(e, "body", None)
    inner = body.get("error") if isinstance(body, dict) else None
    message = inner.get("message") if isinstance(inner, dict) else None
    if not isinstance(message, str) or not message.strip():
        return ""
    message = " ".join(message.split())
    return f": {message[:200]}{'…' if len(message) > 200 else ''}"


def check_roles(have_key: bool, client_factory: Callable[[], object] | None = None) -> Check:
    """Each role's models (OF-BLD-014 §3.3, E.7), whether the Models API lists
    them for this key, and today's spend against the daily cap."""
    try:
        cap = spend.daily_budget()
        spend.ask_budget()
    except spend.BudgetSettingInvalid as e:
        return Check("roles", "fail", str(e))
    try:
        today = f"today ${spend.total_today():.2f} of the ${cap:.2f} daily cap"
    except spend.SpendFileDamaged as e:
        return Check("roles", "fail", str(e))
    chains = {role: llm.chain(role) for role in llm.ROLES}
    named = "; ".join(f"{role}: {' → '.join(models)}" for role, models in chains.items())
    if not have_key or intake.fixtures_only():
        return Check("roles", "skip", f"{named}; {today}")
    import anthropic

    client = (client_factory or anthropic.Anthropic)()
    listed: dict[str, bool] = {}
    for model in dict.fromkeys(m for models in chains.values() for m in models):
        try:
            client.models.retrieve(model, timeout=15)
            listed[model] = True
        except (anthropic.PermissionDeniedError, anthropic.NotFoundError):
            listed[model] = False
        except (anthropic.APIConnectionError, anthropic.APIStatusError):
            return Check("roles", "skip", f"{named}; {today}; the model row says why the models could not be asked")
    unlisted = [m for m in listed if not listed[m]]
    if unlisted:
        index_first = chains["index"][0]
        why = (
            f"{index_first} is not listed for this key, so index work runs on the answer chain"
            if index_first in unlisted
            else f"{', '.join(unlisted)} not listed for this key"
        )
        return Check("roles", "warn", f"{named}; {why}; {today}")
    return Check("roles", "ok", f"{named}; every model listed for this key; {today}")


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


def check_huggingface() -> Check:
    """Optional, so a warning at most: the two hybrid search lanes need one
    model download from here, and the other lanes work without it."""
    if intake.fixtures_only():
        return Check("huggingface", "skip", "OPENFERMENT_FIXTURES is set")
    gap = "so the two hybrid search lanes will report themselves unavailable"
    try:
        r = httpx.head(HUGGINGFACE, timeout=10, follow_redirects=True)
    except httpx.HTTPError as e:
        return Check("huggingface", "warn", f"could not reach huggingface.co ({type(e).__name__}), {gap}")
    if r.status_code >= 400:
        return Check("huggingface", "warn", f"huggingface.co answered {r.status_code}, {gap}")
    return Check("huggingface", "ok", "huggingface.co answers")


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


def run(no_network: bool = False, port: int | None = None, workers: bool = True) -> list[Check]:
    load_dotenv(CORE / ".env", override=False)
    host, found_port = service_address()
    port = port or found_port
    key = check_key()
    have_key = key.mark in ("ok", "warn")
    checks = [key, check_corpus(), check_build(), check_data(), check_intake()]
    # §10.R: one damaged file must not stop the report; a row that cannot be
    # checked says why and the rest still run.
    for name, row in (("index", check_index), ("models", check_models), ("artifacts", check_artifacts),
                      ("spend", check_spend), ("workers", lambda: check_workers(workers))):
        try:
            checks.append(row())
        except Exception as e:  # any failure is the row's answer, in words
            checks.append(Check(name, "warn", f"could not be checked: {type(e).__name__}: {e}"))
    if no_network:
        checks += [Check(n, "skip", "--no-network") for n in ("model", "roles", "europepmc", "huggingface", "backup")]
    else:
        checks += [check_model(have_key), check_roles(have_key), check_europe_pmc(), check_huggingface(), check_backup()]
    checks.append(check_service(port, have_key, host))
    return checks


def lane(checks: list[Check]) -> str:
    """What this machine can run (OF-BLD-014 A.4). The key counts when its
    check passed or warned and the Models API accepted it: a key Anthropic
    rejects, a model this machine cannot reach, or a model check that never
    ran (--no-network, fixture mode) confirms nothing. Europe PMC answers when
    its check passed."""
    marks = {c.name: c.mark for c in checks}
    if marks.get("key") not in ("ok", "warn") or marks.get("model") not in ("ok", "warn"):
        return "none"
    return "full" if marks.get("europepmc") == "ok" else "model-only"


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
    lines.append(f"lane: {lane(checks)}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if any(a not in ("--no-network", "--no-workers") for a in argv):
        print("usage: python -m openferment_core.ready [--no-network] [--no-workers]")
        return 2
    checks = run(no_network="--no-network" in argv, workers="--no-workers" not in argv)
    print(report(checks))
    return 1 if any(c.mark == "fail" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
