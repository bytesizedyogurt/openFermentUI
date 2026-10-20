"""`pnpm check:tools` (OF-BLD-015 §7.6), a stage of `pnpm verify`.

Fails when:

1. a module store has no read tool or no write tool in the registry;
2. a write tool reaches a store without going through its module's write
   function: `tools/writes.py` may name only the write functions listed in
   `ALLOWED_WRITES`, and no file write of its own. The file is parsed, and
   every name is followed through its import, aliases included, to the
   object it names, so `from ..biorepo import write as keep` or
   `from .. import guild as g` is the module it is; a store's exception or
   constant may be named, a store module handed around bare or a dynamic
   import may not;
2b. a tool file other than `tools/writes.py` reaches `proforma.run` or
   `audit.append` itself (OF-BLD-019 §6.1): `run_flowsheet` is a free,
   audited write, and runs through `writes.run_scenario`, so rule 2 reads its
   one call to `proforma.run`;
3. a gated action can complete without a person's id on it: every (module,
   action) in `gates.GATES` comes back `proposed` with nothing written but
   the proposal, and carrying it out with no name, a placeholder or one
   character is refused;
4. the gate table in `docs/TOOLS.md` and `gates.GATES` name different gates:
   the list lives in both places, one row a gate, and a row dropped from one
   is a gate the other still promises;
5. the registry is not the closed list: a name in `WHITELIST` with no tool
   registered under it, or one `docs/TOOLS.md` never names in backticks
   (OF-BLD-019 §4.2 added the thirtieth, `thermo_props`, and §6.1
   `run_flowsheet` and `stream_table`, by the build document's authority; a
   name added to the code alone is a tool nobody wrote down).

Runs on a throwaway data directory with no key and no network, in a few
seconds. Negative-tested on 2026-10-20: a module added with no tools,
`atomic.write_text` planted in writes.py, and a gate row deleted from one
table each made it fail (STATE.md). Rule 2 read text until the review of
OF-BLD-016 §1.R found that a write reached through an aliased import passed
it. It parses now, and was negative-tested the same day on a copy of the
package: `from ..biorepo import write as keep_decision`, `from .. import
guild as g; g.write_evidence(d)`, a plain `from ..guild import
write_evidence`, `import openferment_core.checks as c`, a store module handed
to `getattr`, and `importlib`, each planted in the copy's writes.py, each
passed the text rule and each was named by this one; an exception and a
constant of a store passed, as did writes.py restored.
"""
from __future__ import annotations

import ast
import importlib
import os
import re
import sys
import tempfile
import types
from pathlib import Path
from typing import Iterable

CORE = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE))
os.environ["OPENFERMENT_DATA_DIR"] = tempfile.mkdtemp(prefix="check-tools-")
os.environ.setdefault("OPENFERMENT_MODEL", "claude-haiku-5-5")
os.environ.setdefault("OPENFERMENT_FIXTURES", "1")

try:
    from openferment_core import audit, intake, module_stores, proposals, tools  # noqa: E402
    from openferment_core.tools import gates, writes  # noqa: E402
except Exception as e:  # a module with no tool, or a tool outside WHITELIST, fails the registry's import
    print(f"✗ check:tools  the registry did not load: {type(e).__name__}: {e}")
    sys.exit(1)

# The write functions a write tool may call: each module's own, where its
# rules live. A new free write adds its function here and in docs/TOOLS.md.
ALLOWED_WRITES = (
    "geneos.ceiling", "geneos.frontier", "geneos.mix",
    "fermos.forecast_run",
    # proforma_write's run and the registry's run_flowsheet alike, both through
    # writes.run_scenario (OF-BLD-019 §6.1; rule 2b).
    "proforma.run",
    "extract.add_candidate",
    "intake.fetch_paper",
    "extract.extract_paper",
    "proposals.propose",
    "audit.append",
)
# The modules that keep a store: anything of theirs a write tool names is a
# write function in ALLOWED_WRITES, an exception, or a constant.
STORES = ("geneos", "fermos", "proforma", "extract", "intake", "proposals", "audit", "checks", "guild", "biorepo",
          "artifacts", "atomic")
# What a write tool may never do itself.
FORBIDDEN = ("write_text", "open(", "json.dump", ".write(", "atomic.", "_persist", "Path(", "write_bytes", "unlink(", "rename(")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


# 1. every module has its pair
names = {t.name for t in tools.infos()}
for module in module_stores.MODULES:
    for kind in ("read", "write"):
        if f"{module}_{kind}" not in names or f"{module}_{kind}" not in tools.WHITELIST:
            fail(f"{module} has no {kind} tool in the registry")

# 2. writes reach no store but through a module's write function
src = Path(writes.__file__).read_text(encoding="utf-8")
body = src.split('"""', 2)[-1]  # past the module docstring
for token in FORBIDDEN:
    if token in body:
        fail(f"tools/writes.py holds {token!r}: a write tool never touches a store itself")


def _absolute(node: ast.ImportFrom, package: str) -> str:
    """The module a `from … import` names, a relative one resolved against
    the importing file's package."""
    if not node.level:
        return node.module or ""
    parts = package.split(".")
    parts = parts[: len(parts) - (node.level - 1)]
    return ".".join(parts + ([node.module] if node.module else []))


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef, ast.ListComp, ast.SetComp, ast.DictComp,
           ast.GeneratorExp)


def _own(node: ast.AST) -> Iterable[ast.AST]:
    """A scope's nodes, parents before children, without its nested scopes'
    insides (the nested scope's own node is yielded: its name is bound here)."""
    stack = list(ast.iter_child_nodes(node))[::-1]
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, _SCOPES):
            stack.extend(list(ast.iter_child_nodes(n))[::-1])


def _scope(node: ast.AST, outer: dict[str, set[str]], package: str) -> dict[str, set[str]]:
    """The names an import binds as seen inside `node`, to the dotted path
    each stands for. An import inside a function binds its name for the whole
    function; a name the function assigns otherwise hides the outer import."""
    imported: dict[str, set[str]] = {}
    local: set[str] = set()
    declared: set[str] = set()
    for n in _own(node):
        if isinstance(n, ast.Import):
            for a in n.names:
                imported.setdefault(a.asname or a.name.split(".")[0], set()).add(a.name if a.asname else a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            base = _absolute(n, package)
            for a in n.names:
                imported.setdefault(a.asname or a.name, set()).add(f"{base}.{a.name}")
        elif isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            local.add(n.id)
        elif isinstance(n, ast.arg):
            local.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            local.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            local.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            declared.update(n.names)
    hidden = local - declared - set(imported) if isinstance(node, _SCOPES) else set()
    return {**{k: v for k, v in outer.items() if k not in hidden}, **imported}


def _chains(node: ast.AST, scope: dict[str, set[str]], package: str,
            out: list[tuple[str, list[str], int, set[str]]]) -> None:
    """Every name read in `node`'s scope and the ones inside it, with the
    attributes taken from it and what an import bound it to there:
    `g.write_evidence` is ("g", ["write_evidence"], line, {"…guild"})."""
    inner: set[int] = set()
    for n in _own(node):
        if isinstance(n, _SCOPES):
            _chains(n, _scope(n, scope, package), package, out)
        elif id(n) in inner:
            continue
        elif isinstance(n, ast.Attribute):
            attrs, cur = [], n
            while isinstance(cur, ast.Attribute):
                inner.add(id(cur))
                attrs.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                inner.add(id(cur))
                out.append((cur.id, attrs[::-1], n.lineno, scope.get(cur.id, set())))
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.append((n.id, [], n.lineno, scope.get(n.id, set())))


_STORE_NAMES = {f"openferment_core.{m}": m for m in STORES}


def _reach(path: list[str]) -> tuple[str | None, object]:
    """Follow a dotted path to what it names: the store member it reaches
    ("guild.write_evidence") with the object, a store module named bare
    ("guild", the module), or (None, None) for anything else."""
    obj, rest = None, []
    for i in range(len(path), 0, -1):
        try:
            obj, rest = importlib.import_module(".".join(path[:i])), path[i:]
            break
        except ImportError:
            continue
    if obj is None:
        return None, None
    while True:
        store = _STORE_NAMES.get(getattr(obj, "__name__", "")) if isinstance(obj, types.ModuleType) else None
        if store and rest:
            return f"{store}.{rest[0]}", getattr(obj, rest[0], None)
        if store:
            return store, obj
        if not rest or not hasattr(obj, rest[0]):
            return None, None
        obj, rest = getattr(obj, rest[0]), rest[1:]


tree = ast.parse(src)
package = writes.__package__ or "openferment_core.tools"
chains: list[tuple[str, list[str], int, set[str]]] = []
_chains(tree, _scope(tree, {}, package), package, chains)
reached: set[str] = set()
for root, attrs, line, targets in chains:
    if root == "__import__" or any(t.split(".")[0] == "importlib" for t in targets):
        fail(f"tools/writes.py line {line} imports by name at run time ({root}): every module it reaches is named by an import")
        continue
    for target in sorted(targets):
        member, obj = _reach(target.split(".") + attrs)
        if member is None:
            continue
        spelled = ".".join([root, *attrs])
        if "." not in member:
            fail(f"tools/writes.py line {line} hands the store module {member} around bare ({spelled}): "
                 f"a write tool names one of its write functions or nothing")
        elif member in ALLOWED_WRITES:
            reached.add(member)
        elif not (isinstance(obj, type) and issubclass(obj, BaseException)) and callable(obj):
            fail(f"tools/writes.py line {line} reaches {member} (as {spelled}), which is not one of the module write "
                 f"functions ALLOWED_WRITES names")
for fn in ALLOWED_WRITES:
    if fn not in reached:
        fail(f"tools/writes.py no longer calls {fn}(): the action it served has lost its write function, or the table is stale")

# 2b. an audited write outside writes.py goes through it (OF-BLD-019 §6.1)
THROUGH_WRITES = ("proforma.run", "audit.append")
for other in sorted(Path(writes.__file__).parent.glob("*.py")):
    if other.name == "writes.py":
        continue
    other_tree = ast.parse(other.read_text(encoding="utf-8"))
    other_chains: list[tuple[str, list[str], int, set[str]]] = []
    _chains(other_tree, _scope(other_tree, {}, package), package, other_chains)
    for root, attrs, line, targets in other_chains:
        for target in sorted(targets):
            member, _ = _reach(target.split(".") + attrs)
            if member in THROUGH_WRITES:
                fail(f"tools/{other.name} line {line} reaches {member} itself: a tool that writes and audits goes "
                     f"through tools/writes.py, where rule 2 reads it")

# 3. a gated action completes only with a person's name on it
data = Path(os.environ["OPENFERMENT_DATA_DIR"])
assert intake.DATA_DIR == data, "the throwaway data directory is not in use"
ctx = tools.ToolContext(pool_factory=lambda: None, stores_factory=lambda: None)
ctx.ask_id = "ask-check-tools"
if not gates.GATES:
    fail("gates.GATES is empty")
for gate in gates.GATES:
    for module, action in gate.actions:
        if gate.id == "spend":
            continue  # reached at run time, when the budget refuses; test_writes covers it
        before = {p.name for p in data.iterdir()} if data.exists() else set()
        r = tools.run(f"{module}_write", {"action": action, "target": "t", "fields": {"personId": "p-1", "skillIds": "SK-OD"}, "note": "n"}, ctx)
        if r.error or r.summary.get("state") != "proposed" or r.summary.get("gate") != gate.id:
            fail(f"{module}_write {action} did not come back proposed at gate {gate.id}: {r.error or r.summary}")
            continue
        after = {p.name for p in data.iterdir()}
        extra = after - before - {"proposals.json", "proposals.json.lock", "audit.jsonl", "audit.jsonl.lock"}
        if extra:
            fail(f"{module}_write {action} wrote {sorted(extra)} besides the proposal")
        pid = r.summary["proposalId"]
        for bad in ("", " ", "x", "you", "me", "model", "reviewer"):
            try:
                proposals.carry_out(pid, bad)
                fail(f"proposal {pid} ({module} {action}) was carried out with no person's name ({bad!r})")
            except proposals.ProposalRefused:
                pass
        if proposals.get(pid).state != "proposed":
            fail(f"proposal {pid} changed state without a person's name")
# 4. the two copies of the gate table agree
doc = (Path(__file__).resolve().parent.parent / "docs" / "TOOLS.md").read_text(encoding="utf-8")
documented = set(re.findall(r"^\| `([a-z]+)` \| [^|]+ \| [^|]*`[a-z]+ [a-z_]+`", doc, re.MULTILINE))
coded = {g.id for g in gates.GATES}
for missing in sorted(documented - coded):
    fail(f"docs/TOOLS.md names gate {missing!r} and gates.py has no such row")
for missing in sorted(coded - documented):
    fail(f"gates.py has gate {missing!r} and docs/TOOLS.md has no row for it")
# 5. the registry is the closed list, and every name of it is written down
for name in tools.WHITELIST:
    if name not in tools.REGISTRY:
        fail(f"{name} is in WHITELIST and no tool is registered under it")
    if f"`{name}`" not in doc:
        fail(f"{name} is in WHITELIST and docs/TOOLS.md never names it")
lines = audit.read()
if any(a.agent == "person" for a in lines):
    fail("a person's line entered the audit log with no person's name")
if not lines or any(a.agent != "model" or not a.askId for a in lines):
    fail("a model's write is missing its mark (agent, ask id) in the audit log")

if errors:
    print("✗ check:tools")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"✓ check:tools  {len(module_stores.MODULES)} modules with a read and a write tool; writes.py calls only "
      f"{len(ALLOWED_WRITES)} module write functions, and no other tool file reaches {' or '.join(THROUGH_WRITES)}; {sum(len(g.actions) for g in gates.GATES)} gated actions need a person; "
      f"{len(coded)} gates in gates.py and docs/TOOLS.md alike; {len(tools.WHITELIST)} tools, each registered and "
      f"written down")
