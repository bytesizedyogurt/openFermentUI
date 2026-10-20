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
2b. a tool file other than `tools/writes.py` reaches what keeps a Proforma
   run or writes an audit line itself (OF-BLD-019 §6.1, §6.R): `run_flowsheet`
   is a free, audited write, and runs through `writes.run_scenario`, so rule 2
   reads its one call to `proforma.run`. What keeps a run is found, not
   listed: every function of the service that calls `artifacts.compute` for a
   `proforma.run`, `proforma.reference` or `proforma_benchmark` artifact (or
   for a tool it cannot name) or `audit.append`, and every function that
   reaches one of those, to a fixed point, each name followed through its
   import as rule 2 follows it. A tool file may reach none of them but
   through writes.py, may not call `artifacts.compute` for a run, and, as in
   rule 2, may not hand a store module around bare or import by name at run
   time;
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
constant of a store passed, as did writes.py restored. Rule 2b caught two
names until the review of OF-BLD-019 §6.R found that
`proforma.run_flowsheet(...)`, `artifacts.compute(proforma.RUN, …)` and
`getattr(proforma, "run")` each kept a run past it; `test_check_tools` plants
those and four more (an aliased `compute` with the tool spelled out,
`importlib`, an aliased `audit.append`, and a function outside tools/ that
calls `proforma.run`) in a copy's tools/, and holds that each is named and
nothing else is.
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

# 2b. what keeps a Proforma run or writes an audit line, a tool file reaches
#     only through writes.py (OF-BLD-019 §6.1, §6.R). The writers are found,
#     not listed: every function of the service that calls `artifacts.compute`
#     for a Proforma run (or for a tool it cannot name) or `audit.append`,
#     then every function that reaches one of those, to a fixed point, each
#     name followed through its import as rule 2 follows it. writes.py is the
#     way through and passes nothing on. The worker side (workers/,
#     flowsheets/) runs in the worker's own process and holds no store.
from openferment_core import proforma as _proforma_mod  # noqa: E402

PACKAGE_DIR = Path(writes.__file__).resolve().parent.parent
TOOLS_DIR = Path(writes.__file__).resolve().parent
WORKER_SIDE = ("workers", "flowsheets")
RUN_KINDS = frozenset({_proforma_mod.RUN, _proforma_mod.REFERENCE, _proforma_mod.BENCHMARK})
COMPUTE = "openferment_core.artifacts.compute"
APPEND = "openferment_core.audit.append"
WRITES = f"{writes.__name__}."
_UNKNOWN = object()


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE_DIR.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _locals(node: ast.AST) -> set[str]:
    """The names a function, lambda, class or comprehension binds itself: a
    root among them is never the module's global of that name."""
    if not isinstance(node, _SCOPES):
        return set()
    names: set[str] = set()
    declared: set[str] = set()
    for n in _own(node):
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            names.add(n.id)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            declared.update(n.names)
    return names - declared


def _refs(node: ast.AST, imports: dict[str, set[str]], local: set[str], package: str, out: list) -> None:
    """`_chains`, with each chain's head node and whether its root is a name
    its scope binds itself: (node, root, attrs, line, targets, local)."""
    inner: set[int] = set()
    for n in _own(node):
        if isinstance(n, _SCOPES):
            _refs(n, _scope(n, imports, package), local | _locals(n), package, out)
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
                out.append((n, cur.id, attrs[::-1], n.lineno, imports.get(cur.id, set()), cur.id in local))
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.append((n, n.id, [], n.lineno, imports.get(n.id, set()), n.id in local))


def _follow(path: tuple[str, ...]) -> object:
    """What a dotted path inside the service names, through its imports; a
    path outside openferment_core is not followed."""
    if path[0] != "openferment_core":
        return _UNKNOWN
    obj, rest = None, []
    for i in range(len(path), 0, -1):
        try:
            obj, rest = importlib.import_module(".".join(path[:i])), list(path[i:])
            break
        except Exception:
            continue
    if obj is None:
        return _UNKNOWN
    for attr in rest:
        if not hasattr(obj, attr):
            return _UNKNOWN
        obj = getattr(obj, attr)
    return obj


def _key(obj: object) -> str | None:
    """A function of the service by its module and qualified name."""
    import inspect

    obj = getattr(obj, "__func__", obj)
    try:
        obj = inspect.unwrap(obj)
    except Exception:
        return None
    if not inspect.isfunction(obj) or not str(obj.__module__).startswith("openferment_core"):
        return None
    return f"{obj.__module__}.{obj.__qualname__}"


class _Module:
    """One file of the service: its syntax tree, its module-level imports, and
    the functions, classes and literal constants it defines."""

    def __init__(self, path: Path):
        self.path = path
        self.name = _module_name(path)
        self.package = self.name if path.name == "__init__.py" else self.name.rpartition(".")[0]
        self.tree = ast.parse(path.read_text(encoding="utf-8"))
        self.imports = _scope(self.tree, {}, self.package)
        self.defs: set[str] = set()
        self.classes: set[str] = set()
        self.consts: dict[str, object] = {}
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defs.add(n.name)
            elif isinstance(n, ast.ClassDef):
                self.classes.add(n.name)
            elif isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None:
                try:
                    value = ast.literal_eval(n.value)
                except Exception:
                    continue
                for t in n.targets if isinstance(n, ast.Assign) else [n.target]:
                    if isinstance(t, ast.Name):
                        self.consts[t.id] = value
                    elif isinstance(t, ast.Tuple) and isinstance(value, tuple) and len(value) == len(t.elts):
                        # `CEILING, FRONTIER, MIX = "geneos.ceiling", …`
                        self.consts.update({e.id: v for e, v in zip(t.elts, value) if isinstance(e, ast.Name)})

    def functions(self) -> Iterable[tuple[str, ast.AST]]:
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield f"{self.name}.{n.name}", n
            elif isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield f"{self.name}.{n.name}.{m.name}", m

    def resolve(self, root: str, attrs: list[str], targets: set[str], local: bool) -> tuple[str | None, object]:
        """(the function's key, or None; the object or constant named, or
        _UNKNOWN) for one chain read in this file."""
        if targets:
            for t in sorted(targets):
                obj = _follow(tuple(t.split(".") + attrs))
                if obj is not _UNKNOWN:
                    return _key(obj), obj
            return None, _UNKNOWN
        if local:
            return None, _UNKNOWN
        if root in self.defs and not attrs:
            return f"{self.name}.{root}", _UNKNOWN
        if root in self.classes and len(attrs) == 1:
            return f"{self.name}.{root}.{attrs[0]}", _UNKNOWN
        if root in self.consts and not attrs:
            return None, self.consts[root]
        return None, _UNKNOWN

    def refs(self, node: ast.AST | None = None) -> list:
        out: list = []
        if node is None:
            _refs(self.tree, self.imports, set(), self.package, out)
        else:
            _refs(node, _scope(node, self.imports, self.package), _locals(node), self.package, out)
        return out

    def run_computes(self, node: ast.AST, refs: list) -> list[tuple[int, str]]:
        """Each call of `artifacts.compute` under `node` that keeps a Proforma
        run, or a tool this cannot name: (line, what it keeps)."""
        heads = {id(r[0]): r for r in refs}
        found = []
        for call in ast.walk(node):
            if not isinstance(call, ast.Call) or id(call.func) not in heads:
                continue
            _, root, attrs, line, targets, local = heads[id(call.func)]
            if self.resolve(root, attrs, targets, local)[0] != COMPUTE:
                continue
            arg = call.args[0] if call.args else next((k.value for k in call.keywords if k.arg == "tool"), None)
            if isinstance(arg, ast.Constant):
                tool = arg.value
            elif arg is not None and id(arg) in heads:
                _, r, a, _, t, lc = heads[id(arg)]
                tool = self.resolve(r, a, t, lc)[1]
            else:
                tool = _UNKNOWN
            if tool is _UNKNOWN or tool in RUN_KINDS:
                found.append((line, "a tool it cannot name" if tool is _UNKNOWN else f"a {tool} artifact"))
        return found


service = [_Module(p) for p in sorted(PACKAGE_DIR.rglob("*.py"))
           if p.relative_to(PACKAGE_DIR).parts[0] not in WORKER_SIDE]
# What each function reaches, and the ones that keep a run or append to the audit log themselves.
edges: dict[str, set[str]] = {}
WRITERS: set[str] = {APPEND}
for mod in service:
    for key, fn in mod.functions():
        fn_refs = mod.refs(fn)
        reached = {k for _, r, a, _, t, lc in fn_refs for k in [mod.resolve(r, a, t, lc)[0]] if k}
        edges[key] = {k for k in reached if not k.startswith(WRITES)}
        if APPEND in reached or mod.run_computes(fn, fn_refs):
            WRITERS.add(key)
grew = True
while grew:
    grew = False
    for key, reached in edges.items():
        if key not in WRITERS and reached & WRITERS:
            WRITERS.add(key)
            grew = True
if not {f"{_proforma_mod.__name__}.run", f"{_proforma_mod.__name__}.run_flowsheet", APPEND} <= WRITERS:
    fail("rule 2b no longer finds proforma.run, proforma.run_flowsheet and audit.append among the writers: it has "
         "stopped reading the service")

for mod in service:
    if mod.path.parent != TOOLS_DIR or mod.path.name == "writes.py":
        continue
    where = f"tools/{mod.path.name}"
    tool_refs = mod.refs()
    own = {key for key, _ in mod.functions()}
    for _, root, attrs, line, targets, local in tool_refs:
        if root == "__import__" or any(t.split(".")[0] == "importlib" for t in targets):
            fail(f"{where} line {line} imports by name at run time ({root}): every module a tool file reaches is "
                 "named by an import")
            continue
        key, obj = mod.resolve(root, attrs, targets, local)
        spelled = ".".join([root, *attrs])
        if isinstance(obj, types.ModuleType) and obj.__name__ in _STORE_NAMES:
            fail(f"{where} line {line} hands the store module {_STORE_NAMES[obj.__name__]} around bare ({spelled}): "
                 "a tool file names what it reads of a store")
        elif key in WRITERS and key not in own and not key.startswith(WRITES):
            fail(f"{where} line {line} reaches {key} (as {spelled}), which keeps a Proforma run or writes an audit "
                 "line: a tool that does goes through tools/writes.py, where rule 2 reads it")
    for line, kept in mod.run_computes(mod.tree, tool_refs):
        fail(f"{where} line {line} keeps {kept} through artifacts.compute itself: a tool that keeps a run goes "
             "through tools/writes.py, where rule 2 reads it")

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
      f"{len(ALLOWED_WRITES)} module write functions, and no other tool file reaches any of the {len(WRITERS)} functions that keep a Proforma run or write an audit line; {sum(len(g.actions) for g in gates.GATES)} gated actions need a person; "
      f"{len(coded)} gates in gates.py and docs/TOOLS.md alike; {len(tools.WHITELIST)} tools, each registered and "
      f"written down")
