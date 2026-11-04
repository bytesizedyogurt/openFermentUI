"""Every dependency's licence, read, listed and checked (OF-BLD-014 §1.2, E.9).

    pnpm check:licences           check every licence, and regenerate THIRD_PARTY.md
    pnpm check:licences --list    print each distinct licence string and the packages carrying it

Two sides are read. Python: every distribution installed in core/.venv that
core/uv.lock names, through its own metadata: the `License` field, the
`License-Expression` field and the `License ::` classifiers. A package that
states an expression is decided by it alone, as PEP 639 makes the expression
the licence; for any other package, any of the License field and the
classifiers can decide. JavaScript: every production dependency, as
`pnpm licenses list --json --prod` reports it. Beside the lock: every
distribution installed in core/.venv that registers an entry point in the
group `openferment.engines` and that core/uv.lock does not name, and each
dependency of one that the lock does not name (`engine_side`). An engine
installed from under examples/ is the project's own and declares no licence
(ADR-012: a declared one fails the stage in words); any other engine, and
every such dependency, is held to the ledger as any dependency is. They are
reported here and left out of THIRD_PARTY.md, which lists what the lock
installs, so the listing reads the same with an engine installed or not.

A string passes when core/licences.toml allows it, in the spelling the
metadata uses, or when a named person accepted that package under that same
string in [accepted]. Anything else fails the stage, by name. The project's
own package carries no licence metadata, because the repository declares no
licence yet, and is skipped by name.

THIRD_PARTY.md is regenerated on every run. When the file on disk differs
from what is installed, the new one is written and the stage fails, so a
dependency change lands with its listing.

It reads the interpreter it runs in, so the pnpm alias runs it inside core's
environment: `cd core && uv run --all-extras python ../scripts/check-licences.py`.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "core"
POLICY = CORE / "licences.toml"
LOCK = CORE / "uv.lock"
LISTING = REPO / "THIRD_PARTY.md"
SRC = REPO / "src"
# The examples the repository's builders keep (stage D's engine among them):
# the project's own packages, which declare no licence (ADR-012).
EXAMPLES = REPO / "examples"
# The entry-point group an engine registers under (docs/api/engines.md).
ENGINE_GROUP = "openferment.engines"
# The project's own distribution, skipped by name: it is what the listing is
# about, and it carries no licence metadata.
SELF = "openferment-core"
# Which part of openFerment an extra serves. An extra missing here is named
# as itself.
EXTRA_PART = {"dev": "tests", "sim": "the simulation workers"}


def canonical(name: str) -> str:
    """PEP 503: one spelling per distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Acceptance:
    package: str
    licence: str
    by: str
    date: str
    why: str


@dataclass(frozen=True)
class DataFile:
    """A model file read as data (E.9): where it comes from, the revision and
    hash it is pinned to, its licence, and who accepted it."""

    id: str
    licence: str
    source: str
    revision: str
    sha256: str
    by: str
    date: str
    why: str


DATA_FIELDS = ("licence", "source", "revision", "sha256", "by", "date", "why")


@dataclass(frozen=True)
class VendoredCode:
    """Source copied into the repository at a pinned commit (ADR-003): where
    it comes from, the commit, the directory it lives in with its LICENSE,
    what was left out, and why it is vendored. Its licence must be one the
    ledger allows."""

    id: str
    licence: str
    source: str
    revision: str
    path: str
    left_out: str
    why: str


VENDORED_FIELDS = ("licence", "source", "revision", "path", "left_out", "why")


@dataclass(frozen=True)
class Policy:
    allowed: frozenset[str]
    accepted: dict[str, Acceptance]  # canonical package name → its acceptance
    data: tuple[DataFile, ...] = ()
    vendored: tuple[VendoredCode, ...] = ()


@dataclass(frozen=True)
class Verdict:
    ok: bool
    string: str | None  # the licence string that decided it
    how: str  # "allowed", "accepted by <name> on <date>", or why it fails


@dataclass(frozen=True)
class Package:
    side: str  # "python" or "javascript"
    name: str
    version: str
    strings: tuple[str, ...]  # every licence string its metadata carries
    part: str  # which part of openFerment uses it
    verdict: Verdict
    listed: str = ""  # the version the listing shows, when it differs from `version`


# ── the ledger ──────────────────────────────────────────────────────────


def load_policy(path: Path = POLICY) -> Policy:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    allowed = raw.get("allowed")
    if not isinstance(allowed, list) or not all(isinstance(s, str) and s for s in allowed):
        raise ValueError(f"{path.name}: `allowed` must be a list of licence strings")
    accepted: dict[str, Acceptance] = {}
    for name, entry in (raw.get("accepted") or {}).items():
        missing = [k for k in ("licence", "by", "date", "why") if not str(entry.get(k, "")).strip()]
        if missing:
            raise ValueError(f"{path.name}: [accepted.{name}] lacks {', '.join(missing)}; "
                             "an acceptance names its licence, who accepted it, the date and why")
        accepted[canonical(name)] = Acceptance(
            name, str(entry["licence"]), str(entry["by"]), str(entry["date"]), str(entry["why"])
        )
    data = []
    for name, entry in (raw.get("data") or {}).items():
        missing = [k for k in DATA_FIELDS if not str(entry.get(k, "")).strip()]
        if missing:
            raise ValueError(f"{path.name}: [data.{name}] lacks {', '.join(missing)}; "
                             "a model file names its licence, source, revision, hash, who accepted it, the date and why")
        data.append(DataFile(name, *(str(entry[k]) for k in DATA_FIELDS)))
    vendored = []
    for name, entry in (raw.get("vendored") or {}).items():
        missing = [k for k in VENDORED_FIELDS if not str(entry.get(k, "")).strip()]
        if missing:
            raise ValueError(f"{path.name}: [vendored.{name}] lacks {', '.join(missing)}; "
                             "vendored code names its licence, source, revision, directory, what was left out and why")
        vendored.append(VendoredCode(name, *(str(entry[k]) for k in VENDORED_FIELDS)))
    return Policy(frozenset(allowed), accepted, tuple(sorted(data, key=lambda d: d.id)),
                  tuple(sorted(vendored, key=lambda v: v.id)))


def vendored_faults(policy: Policy, repo: Path = REPO) -> list[str]:
    """What is wrong with each vendored entry: a licence the ledger does not
    allow, or a directory or LICENSE that is not where the entry says."""
    faults = []
    for v in policy.vendored:
        if v.licence not in policy.allowed:
            faults.append(f"[vendored.{v.id}] is under {v.licence}, which `allowed` does not list; vendored code "
                          "carries a permissive licence")
        where = repo / v.path
        if not where.is_dir():
            faults.append(f"[vendored.{v.id}] names {v.path}, which is not a directory")
        elif not (where / "LICENSE").is_file():
            faults.append(f"[vendored.{v.id}]: {v.path} holds no LICENSE file")
    return faults


# What an acceptance names for a package whose metadata states no licence.
NO_METADATA = "no licence metadata"


def decide(package: str, strings: list[str] | tuple[str, ...], policy: Policy) -> Verdict:
    """Whether one package passes. `strings` are every licence string its
    metadata carries, and any one of them can decide it."""
    for s in strings:
        if s in policy.allowed:
            return Verdict(True, s, "allowed")
    acceptance = policy.accepted.get(canonical(package))
    if acceptance is not None:
        # A package whose metadata states no licence can be accepted only
        # under this exact string, and stops passing once it states one.
        if not strings and acceptance.licence == NO_METADATA:
            return Verdict(True, NO_METADATA, f"accepted by {acceptance.by} on {acceptance.date}")
        if acceptance.licence in strings:
            return Verdict(True, acceptance.licence, f"accepted by {acceptance.by} on {acceptance.date}")
        return Verdict(False, None, f"accepted as {acceptance.licence} by {acceptance.by}, and its metadata "
                       f"now says {', '.join(strings) or 'nothing'}: the acceptance covers that string alone")
    said = ", ".join(strings) if strings else "no licence metadata"
    return Verdict(False, None, f"{said}: neither allowed nor accepted in core/licences.toml")


# ── Python: what core/.venv holds and core/uv.lock names ────────────────


def python_strings(metadata) -> tuple[str, ...]:
    out: list[str] = []
    for key in ("License-Expression", "License"):
        value = (metadata.get(key) or "").strip()
        if value and value != "UNKNOWN":
            out.append(value)
    out += [c for c in (metadata.get_all("Classifier") or []) if c.startswith("License ::")]
    return tuple(out)


def deciding_strings(metadata) -> tuple[str, ...]:
    """The strings that decide a package: its License-Expression alone when it
    states one (PEP 639), else its License field and licence classifiers."""
    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        return (expression,)
    return tuple(s for s in python_strings(metadata) if s != expression)


def listed_version(name: str, installed: str, lock: dict) -> str:
    """The version the listing shows. uv.lock can lock one package at two
    versions, picked by Python version (numpy is one); the listing names both,
    so it reads the same on every interpreter the project supports."""
    versions = sorted({e["version"] for e in lock["package"] if canonical(e["name"]) == canonical(name) and "version" in e},
                      key=lambda v: [int(x) if x.isdigit() else x for x in re.split(r"[.+-]", v)])
    return f"{' or '.join(versions)}, by Python version" if len(versions) > 1 else installed


def _closure(roots: list[dict], entries: dict[str, list[dict]]) -> dict[str, set[str]]:
    """Every locked package reachable from `roots`, mapped to the roots it is
    reached through. A dependency asked for with extras (uvicorn[standard])
    brings that package's optional dependencies for those extras."""
    reached: dict[str, set[str]] = {}
    for root in roots:
        top = canonical(root["name"])
        stack = [(top, tuple(root.get("extra", [])))]
        seen: set[tuple[str, tuple[str, ...]]] = set()
        while stack:
            name, extras = stack.pop()
            if (name, extras) in seen:
                continue
            seen.add((name, extras))
            reached.setdefault(name, set()).add(top)
            for entry in entries.get(name, []):
                deps = list(entry.get("dependencies", []))
                for extra in extras:
                    deps += entry.get("optional-dependencies", {}).get(extra, [])
                stack += [(canonical(d["name"]), tuple(d.get("extra", []))) for d in deps]
    return reached


def python_parts(lock: dict) -> dict[str, str]:
    """For each locked package, which part of openFerment pulls it in: the
    service's own dependencies, or an extra, and through which direct
    dependency when it is not one itself."""
    entries: dict[str, list[dict]] = {}
    for entry in lock["package"]:
        entries.setdefault(canonical(entry["name"]), []).append(entry)
    project = entries[SELF][0]
    groups = [("service", _closure(project.get("dependencies", []), entries))]
    for extra, deps in sorted(project.get("optional-dependencies", {}).items()):
        groups.append((EXTRA_PART.get(extra, f"extra {extra}"), _closure(deps, entries)))
    parts: dict[str, str] = {}
    for name in entries:
        labels = []
        for label, reached in groups:
            if name not in reached:
                continue
            through = sorted(reached[name] - {name})
            labels.append(label if name in reached[name] or not through else f"{label}, through {', '.join(through)}")
            if label == "service":
                break  # what the service needs, its tests need too
        if labels:
            parts[name] = "; ".join(labels)
    return parts


def python_side(policy: Policy, lock_path: Path = LOCK) -> list[Package]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked = {canonical(e["name"]) for e in lock["package"]}
    parts = python_parts(lock)
    found: dict[str, Package] = {}
    for dist in md.distributions():
        name = canonical(dist.metadata["Name"] or "")
        if name == SELF or name not in locked or name in found:
            continue
        strings = python_strings(dist.metadata)
        found[name] = Package("python", dist.metadata["Name"], dist.version, strings,
                              parts.get(name, "service"), decide(name, deciding_strings(dist.metadata), policy),
                              listed=listed_version(name, dist.version, lock))
    return sorted(found.values(), key=lambda p: canonical(p.name))


# ── Python: an engine installed beside the lock (alpha 2.2 D0.10) ───────


def _source_dir(dist) -> Path | None:
    """The directory an installed distribution was installed from, as its
    PEP 610 `direct_url.json` names it (an editable install's, `uv pip
    install -e <path>`); None for one installed from an index or an archive."""
    try:
        raw = dist.read_text("direct_url.json")
    except (OSError, ValueError):
        return None
    if not raw:
        return None
    try:
        url = str(json.loads(raw).get("url") or "")
    except (ValueError, AttributeError):
        return None
    if not url.startswith("file://"):
        return None
    from urllib.parse import unquote, urlsplit

    return Path(unquote(urlsplit(url).path)).resolve()


def _requirement_names(dist) -> list[str]:
    """The distributions `dist` requires on its own, its extras' left out,
    each in its canonical spelling."""
    out = []
    for req in dist.requires or []:
        if re.search(r"""extra\s*==""", req):
            continue
        found = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req)
        if found:
            out.append(canonical(found.group(1)))
    return out


def engine_side(policy: Policy, lock_path: Path = LOCK, distributions=None, examples: Path = EXAMPLES) -> list[Package]:
    """Every distribution installed in core/.venv that registers an entry
    point in the group `openferment.engines` and that core/uv.lock does not
    name, then each distribution one of them requires that the lock does not
    name. An engine installed from a directory under examples/ is the
    project's own and declares no licence: a declared one fails in words,
    since a licence for the project is the owner's choice (ADR-012). Any
    other engine, and every such dependency, is held to the ledger as any
    dependency is. None of them enters THIRD_PARTY.md, which lists what
    core/uv.lock installs."""
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked = {canonical(e["name"]) for e in lock["package"]}
    installed: dict[str, object] = {}
    for dist in (md.distributions() if distributions is None else distributions):
        installed.setdefault(canonical(dist.metadata["Name"] or ""), dist)
    engines = sorted(name for name, d in installed.items() if name not in locked and name != SELF
                     and any(ep.group == ENGINE_GROUP for ep in d.entry_points))
    out: list[Package] = []
    for name in engines:
        d = installed[name]
        strings = python_strings(d.metadata)
        where = _source_dir(d)
        own = where is not None and where.is_relative_to(examples.resolve())
        if not own:
            verdict = decide(name, deciding_strings(d.metadata), policy)
        elif strings:
            verdict = Verdict(False, None, f"a package under examples/ is the project's own, and this one declares "
                                           f"{', '.join(strings)}: a licence for the project is the owner's choice "
                                           "(ADR-012), so the package declares none")
        else:
            verdict = Verdict(True, None, "the project's own, under examples/, declaring no licence (ADR-012)")
        part = f"an engine installed from {where}" if where is not None else "an engine installed beside the lock"
        out.append(Package("python", d.metadata["Name"], d.version, strings, part, verdict))
    seen = set(engines)
    stack = [(dep, name) for name in engines for dep in _requirement_names(installed[name])]
    while stack:
        dep, by = stack.pop()
        if dep in seen or dep in locked or dep == SELF or dep not in installed:
            continue
        seen.add(dep)
        d = installed[dep]
        out.append(Package("python", d.metadata["Name"], d.version, python_strings(d.metadata),
                           f"a dependency of the engine {by}, beside the lock",
                           decide(dep, deciding_strings(d.metadata), policy)))
        stack += [(x, by) for x in _requirement_names(d)]
    return out


# ── JavaScript: the production dependencies ─────────────────────────────


def _pnpm(*args: str) -> object:
    try:
        r = subprocess.run(["pnpm", *args], cwd=REPO, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SystemExit(f"✗ could not run pnpm {' '.join(args)}: {e}")
    if r.returncode != 0:
        raise SystemExit(f"✗ pnpm {' '.join(args)} failed: {(r.stderr or r.stdout).strip()[:400]}")
    return json.loads(r.stdout)


def imported_under_src(package: str, src: Path = SRC) -> bool:
    """Whether any file under src/ imports the package, as a module or a stylesheet."""
    pattern = re.compile(
        r"""(?:from\s+|import\s+|import\(\s*|require\(\s*|@import\s+)['"]"""
        + re.escape(package) + r"""(?:/[^'"]*)?['"]"""
    )
    for path in src.rglob("*"):
        if path.suffix in (".ts", ".tsx", ".js", ".jsx", ".css") and path.is_file():
            if pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                return True
    return False


def javascript_parts(tree: list[dict], src: Path = SRC) -> dict[str, str]:
    """For each production package, the direct dependency it comes through,
    and whether the browser app imports that dependency at all."""
    roots: dict[str, set[str]] = {}

    def walk(top: str, node: dict) -> None:
        for name, child in (node.get("dependencies") or {}).items():
            if top not in roots.setdefault(name, set()):
                roots[name].add(top)
                walk(top, child)

    direct = tree[0].get("dependencies") or {}
    for top, node in direct.items():
        roots.setdefault(top, set()).add(top)
        walk(top, node)
    used = {top: imported_under_src(top, src) for top in direct}
    parts: dict[str, str] = {}
    for name, tops in roots.items():
        live = sorted(t for t in tops if used[t])
        if name in tops and used[name]:
            parts[name] = "browser app"
        elif live:
            parts[name] = f"browser app, through {', '.join(live)}"
        elif name in tops:
            parts[name] = "listed in package.json; no file under src/ imports it"
        else:
            parts[name] = f"through {', '.join(sorted(tops))}, which no file under src/ imports"
    return parts


def javascript_side(policy: Policy) -> list[Package]:
    by_licence = _pnpm("licenses", "list", "--json", "--prod")
    parts = javascript_parts(_pnpm("list", "--prod", "--json", "--depth", "Infinity"))
    out: list[Package] = []
    for key, entries in by_licence.items():
        for entry in entries:
            licence = entry.get("license") or key
            for version in entry.get("versions") or ["?"]:
                out.append(Package("javascript", entry["name"], version, (licence,),
                                   parts.get(entry["name"], "browser app"),
                                   decide(entry["name"], (licence,), policy)))
    return sorted(out, key=lambda p: (p.name, p.version))


# ── THIRD_PARTY.md ──────────────────────────────────────────────────────


def _cell(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first.replace("|", "\\|")


def shown_licence(p: Package) -> str:
    return p.verdict.string if p.verdict.string else " / ".join(p.strings) or "none stated"


def render(python: list[Package], javascript: list[Package], policy: Policy) -> str:
    lines = [
        "# Third-party software",
        "",
        "Every package openFerment's service and browser app run on: each Python distribution",
        "`core/uv.lock` installs, its extras included, and every JavaScript production",
        "dependency, with its version, the licence its own metadata states, and the part of",
        "openFerment that uses it. The JavaScript build and test tools (`devDependencies`) are",
        "left out. `pnpm check:licences` (`scripts/check-licences.py`, OF-BLD-014 §1.2) writes",
        "this file from what is installed and fails while the committed copy is stale. The",
        "accepted licence strings, and every package a person accepted, are in",
        "`core/licences.toml`.",
        "",
        "## The service and its tests (`core/`)",
        "",
        "| Package | Version | Licence | Used by | Passes as |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {p.name} | {p.listed or p.version} | {_cell(shown_licence(p))} | {p.part} | {p.verdict.how if p.verdict.ok else 'FAILS'} |"
              for p in python]
    lines += [
        "",
        "`openferment-core`, the project itself, is skipped by name: the repository declares no licence yet.",
        "",
        "## The browser app (JavaScript production dependencies)",
        "",
        "| Package | Version | Licence | Used by | Passes as |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {p.name} | {p.version} | {_cell(shown_licence(p))} | {p.part} | {p.verdict.how if p.verdict.ok else 'FAILS'} |"
              for p in javascript]
    if policy.accepted:
        lines += [
            "",
            "## Accepted by a person",
            "",
            "| Package | Licence | Accepted by | Date | Why |",
            "|---|---|---|---|---|",
        ]
        lines += [f"| {a.package} | {a.licence} | {a.by} | {a.date} | {_cell(a.why)} |"
                  for a in sorted(policy.accepted.values(), key=lambda a: canonical(a.package))]
    if policy.data:
        lines += [
            "",
            "## Model files read as data",
            "",
            "Downloaded into `core/data/models/`, which git ignores, or shipped inside a package; read by the",
            "geneOS worker alone (OF-BLD-014 E.9).",
            "",
            "| File | Licence | Source | Revision | sha256 | Accepted by | Date | Why |",
            "|---|---|---|---|---|---|---|---|",
        ]
        lines += [f"| {d.id} | {d.licence} | {_cell(d.source)} | {d.revision} | {d.sha256} | {d.by} | {d.date} | {_cell(d.why)} |"
                  for d in policy.data]
    if policy.vendored:
        lines += [
            "",
            "## Vendored source",
            "",
            "Copied into the repository unmodified at a pinned commit, with its LICENSE beside it.",
            "",
            "| Code | Licence | Source | Revision | Directory | Left out | Why |",
            "|---|---|---|---|---|---|---|",
        ]
        lines += [f"| {v.id} | {v.licence} | {_cell(v.source)} | {v.revision} | `{v.path}` | {_cell(v.left_out)} | {_cell(v.why)} |"
                  for v in policy.vendored]
    return "\n".join(lines) + "\n"


# ── the stage ───────────────────────────────────────────────────────────


def distinct(packages: list[Package]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in packages:
        for s in p.strings or ("(no licence metadata)",):
            out.setdefault(_cell(s), []).append(f"{p.side}:{p.name} {p.version}")
    return dict(sorted(out.items()))


def check(python: list[Package], javascript: list[Package], policy: Policy,
          listing: Path = LISTING, engines: list[Package] | None = None) -> tuple[int, list[str]]:
    """The verdict on both sides, the engines installed beside the lock
    (`engines`, from `engine_side`) and the listing, which leaves the engines
    out. Returns the exit code and the report's lines. Rewrites `listing`
    when it is stale and every package passes; a failing tree leaves it as it
    was."""
    engines = list(engines or [])
    failed = [p for p in python + javascript + engines if not p.verdict.ok]
    accepted = [p for p in python + javascript if p.verdict.ok and p.verdict.how != "allowed"]
    text = render(python, javascript, policy)
    stale = not listing.exists() or listing.read_text(encoding="utf-8") != text
    if stale and not failed:
        listing.write_text(text, encoding="utf-8")
    installed = {canonical(p.name) for p in python + javascript}
    report = [
        "openFerment licence check",
        "─────────────────────────",
        f"  python       {len(python)} packages installed in core/.venv that uv.lock names "
        f"({SELF} skipped by name)",
        f"  javascript   {len(javascript)} production packages",
        f"  allowed      {len(policy.allowed)} licence strings in core/licences.toml",
    ]
    report += [f"  accepted     {p.name} {p.version} ({p.verdict.string}): {p.verdict.how}" for p in accepted]
    report += [f"  accepted     {a.package} ({a.licence}): not installed here"
               for key, a in sorted(policy.accepted.items()) if key not in installed]
    report += [f"  beside lock  {p.name} {p.version} ({shown_licence(p)}), {p.part}: {p.verdict.how}"
               for p in engines if p.verdict.ok]
    report += [f"  data         {d.id} ({d.licence}): accepted by {d.by} on {d.date}" for d in policy.data]
    report += [f"  vendored     {v.id} ({v.licence}) at {v.revision[:12]} in {v.path}" for v in policy.vendored]
    report.append(f"  listing      {listing.name} " + (
        "is current" if not stale else "left as it was while a package fails" if failed
        else "was stale and has been rewritten"))
    faults = vendored_faults(policy)
    if faults:
        report += ["", "✗ The vendored code does not stand as the ledger says:"]
        report += [f"  - {f}" for f in faults]
        return 1, report
    if failed:
        report += ["", f"✗ {len(failed)} package(s) carry a licence the ledger neither allows nor accepts:"]
        report += [f"  - {p.side} {p.name} {p.version}: {p.verdict.how}" for p in failed]
        report.append("  A permissive string joins `allowed` in core/licences.toml in its own spelling; "
                      "anything else waits for a named person's [accepted] entry.")
        return 1, report
    if stale:
        report += ["", f"✗ {listing.name} did not match what is installed. It has been rewritten; "
                   "read the diff and commit it."]
        return 1, report
    report += ["", "✓ Every dependency's licence is allowed or accepted by a named person."]
    return 0, report


def main(argv: list[str]) -> int:
    if any(a not in ("--list",) for a in argv):
        print("usage: check-licences.py [--list]")
        return 2
    policy = load_policy()
    python, javascript, engines = python_side(policy), javascript_side(policy), engine_side(policy)
    if "--list" in argv:
        for string, holders in distinct(python + javascript + engines).items():
            print(f"{string}\n    {', '.join(holders)}")
        return 0
    code, report = check(python, javascript, policy, engines=engines)
    print("\n".join(report), file=sys.stdout if code == 0 else sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
