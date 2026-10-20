"""`pnpm check:tools` (OF-BLD-015 §7.6), a stage of `pnpm verify`.

Fails when:

1. a module store has no read tool or no write tool in the registry;
2. a write tool reaches a store without going through its module's write
   function: `tools/writes.py` may name only the write functions listed in
   `ALLOWED_WRITES`, and no file write of its own;
3. a gated action can complete without a person's id on it: every (module,
   action) in `gates.GATES` comes back `proposed` with nothing written but
   the proposal, and carrying it out with no name, a placeholder or one
   character is refused;
4. the gate table in `docs/TOOLS.md` and `gates.GATES` name different gates:
   the list lives in both places, one row a gate, and a row dropped from one
   is a gate the other still promises.

Runs on a throwaway data directory with no key and no network, in a few
seconds. Negative-tested on 2026-10-20: a module added with no tools,
`atomic.write_text` planted in writes.py, and a gate row deleted from one
table each made it fail (STATE.md).
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

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
    "proforma.run",
    "extract.add_candidate",
    "intake.fetch_paper",
    "extract.extract_paper",
    "proposals.propose",
    "audit.append",
)
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
called = set(re.findall(r"\b([a-z_]+\.[a-z_]+)\(", body))
writers = {c for c in called if c.split(".")[0] in {"geneos", "fermos", "proforma", "extract", "intake", "proposals", "audit",
                                                   "checks", "guild", "biorepo", "artifacts", "atomic"}}
for c in sorted(writers):
    if c not in ALLOWED_WRITES and not c.startswith(("intake.NetworkRefused", "intake.Transient")):
        fail(f"tools/writes.py calls {c}(), which is not one of the module write functions ALLOWED_WRITES names")
for fn in ALLOWED_WRITES:
    if fn not in body:
        fail(f"tools/writes.py no longer calls {fn}(): the action it served has lost its write function, or the table is stale")

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
      f"{len(ALLOWED_WRITES)} module write functions; {sum(len(g.actions) for g in gates.GATES)} gated actions need a person; "
      f"{len(coded)} gates in gates.py and docs/TOOLS.md alike")
