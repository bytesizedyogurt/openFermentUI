"""R2: break the code a commit message says a test holds, in my own worktree, and see whether that test fails.

Each mutation names the commit whose message claims the behaviour, the file and the exact text it
replaces, and the tests the claim rests on. The runner applies one mutation, runs those tests with
-x, records caught (a test failed) or survived (every test passed), and restores the file with
`git checkout` in the worktree. Never point it at the main checkout.

Usage: python mutate.py <worktree root> [ids...]   (writes mutations.json beside this script's notes)
No test that binds a port outside 8970-8979 runs (the served-app test of test_mcp_service.py is deselected).
The tests make their databases under OPENFERMENT_TEST_DATABASE_URL=.../bh_r2_test (named bh_r2_test_<pid>_<hex>).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WT = Path(sys.argv[1]).resolve()
assert "/bh/work/R2/" in str(WT), "the runner mutates my own worktree alone"
ONLY = set(sys.argv[2:])

M = [
    ("M01", "8bde8ab: the state door keeps a reading's own unit on a Proforma scope alone",
     "core/openferment_core/project_state.py",
     'if o.get("unit") is not None and not item_id.startswith(OWN_UNIT_SCOPE):', "if False:",
     ["tests/test_project_state.py"]),
    ("M02", "2ed7dac: OPENFERMENT_EFFORT lays over plan, explain and extract; judge keeps its effort",
     "core/openferment_core/llm.py",
     "        table.update({family: Route(table[family].models, effort()) for family in ANSWERING})",
     "        table.update({family: Route(table[family].models, effort()) for family in table})",
     ["tests/test_llm.py"]),
    ("M03", "2ed7dac: OPENFERMENT_INDEX_MODEL moves index's first model, index keeps its effort",
     "core/openferment_core/llm.py",
     "table[\"index\"] = Route(tuple(dict.fromkeys((index_model(), *index.models[1:]))), index.effort)",
     "table[\"index\"] = Route(tuple(dict.fromkeys((index_model(), *index.models[1:]))), effort())",
     ["tests/test_llm.py"]),
    ("M04", "dc02f20: GET /api/audit takes who beside action and target",
     "core/openferment_core/api.py", "who=who or None)\n", "who=None)\n",
     ["tests/test_agent_interface.py"]),
    ("M05", "2047f5a: the backup folder is 700",
     "scripts/host/lib.sh", 'mkdir -p "$dir" && chmod 700 "$dir" || return 1', 'mkdir -p "$dir" || return 1',
     ["tests/test_host.py"]),
    ("M06", "2047f5a: the newest seven dumps are kept",
     "scripts/host/lib.sh", 'keep=7 keg', 'keep=8 keg', ["tests/test_host.py"]),
    ("M07", "2047f5a: the dump files are 600 (umask 077)",
     "scripts/host/lib.sh", '(umask 077 && "$tool"', '("$tool"', ["tests/test_host.py"]),
    ("M08", "8d0c2a2: a plan turn's room is 128,000 at max",
     "core/openferment_core/postdoc/plan.py", 'ROOM = {"xhigh": 64_000, "max": 128_000}',
     'ROOM = {"xhigh": 64_000, "max": 64_000}', ["tests/test_postdoc_agent.py"]),
    ("M09", "744e32e: a run's IRR is cited with the unit fraction",
     "core/openferment_core/tools/engine.py", 'BLANK_UNITS = {"IRR": "fraction"}', 'BLANK_UNITS = {}',
     ["tests/test_tools_study.py"]),
    ("M10", "4143de3: --limit counts one at least",
     "core/openferment_core/literature/report.py", "if limit is not None and limit < 1:", "if False:",
     ["tests/test_literature_report.py", "tests/test_literature_live.py"]),
    ("M11", "4143de3: KIT_ROOM at max is 32,000, held equal to JUDGE_TOKENS by a test",
     "core/openferment_core/llm.py", '"max": 32000', '"max": 16000', ["tests/test_llm.py"]),
    ("M12", "6f85338: a NaN or infinite input is refused in words at every door",
     "core/openferment_core/models.py",
     "        infinite = non_finite(self.quantity)\n        if infinite:",
     "        infinite = non_finite(self.quantity)\n        if False:",
     ["tests/test_finite_inputs.py"]),
    ("M13", "c34c8c9: a row kept earlier that does not read is named in refused while the rest load",
     "core/openferment_core/project_state.py",
     '            refused.append(RefusedRow(kind=kind, id=row_id, why=f"{subject}{_said(e)}"))\n            return None',
     '            raise',
     ["tests/test_project_state.py"]),
    ("M14", "448adbb: a person's catalogue keep writes a keep_catalogue audit row",
     "core/openferment_core/catalogues.py", "            if audited is not None:\n                await audit.add(",
     "            if False:\n                await audit.add(", ["tests/test_catalogues.py"]),
    ("M15", "37addaf: a version the protocol holds already is refused",
     "core/openferment_core/protocols.py", "        if any(v.version == version.version for v in held.versions):",
     "        if False:", ["tests/test_protocols.py"]),
    ("M16", "6f85338: --service relays through no proxy",
     "core/openferment_core/mcp_server.py", "httpx.Client(base_url=origin, trust_env=False, follow_redirects=False,",
     "httpx.Client(base_url=origin, trust_env=True, follow_redirects=False,", ["tests/test_mcp_service.py", "-k", "not test_the_server_started_with_service_writes_through_it"]),
    ("M17", "6f85338: --service follows no redirect",
     "core/openferment_core/mcp_server.py", "httpx.Client(base_url=origin, trust_env=False, follow_redirects=False,",
     "httpx.Client(base_url=origin, trust_env=False, follow_redirects=True,", ["tests/test_mcp_service.py", "-k", "not test_the_server_started_with_service_writes_through_it"]),
    ("M18", "dc02f20: GET /api/audit leaves a row's null fields out",
     "core/openferment_core/api.py",
     '@app.get("/api/audit", response_model=list[AuditRow], response_model_exclude_none=True)',
     '@app.get("/api/audit", response_model=list[AuditRow])', ["tests/test_agent_interface.py", "tests/test_mcp_service.py", "-k", "not test_the_server_started_with_service_writes_through_it"]),
    ("M19", "2047f5a: a dump is written beside its name and moved into place once whole",
     "scripts/host/lib.sh", '--file="$file.part" openferment); then', '--file="$file" openferment); then',
     ["tests/test_host.py"]),
    ("M20", "f5405f8 (C.6 fix): import-url's pinned fetch skips a proxy (trust_env off)",
     "core/openferment_core/literature/collectors.py",
     "async with httpx.AsyncClient(transport=_Pinned(pins, network), timeout=TIMEOUT_S, trust_env=False,",
     "async with httpx.AsyncClient(transport=_Pinned(pins, network), timeout=TIMEOUT_S, trust_env=True,",
     ["tests/test_sff_url.py", "tests/test_collectors.py"]),
    ("M21", "f5405f8 (C.6 fix): import-url's network transport reads no proxy setting",
     "core/openferment_core/literature/collectors.py",
     "network = network or httpx.AsyncHTTPTransport(trust_env=False,",
     "network = network or httpx.AsyncHTTPTransport(trust_env=True,",
     ["tests/test_sff_url.py", "tests/test_collectors.py"]),
]


def run(tests: list[str]) -> tuple[bool, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"ANTHROPIC_API_KEY", "OPENFERMENT_API_KEY",
                                                             "OPENFERMENT_MODEL", "OPENFERMENT_FALLBACK_MODEL",
                                                             "OPENFERMENT_INDEX_MODEL", "OPENFERMENT_EFFORT",
                                                             "OPENFERMENT_DATA_DIR"}}
    env.update(ANTHROPIC_API_KEY="", OPENFERMENT_DATABASE_URL="", PYTHONDONTWRITEBYTECODE="1",
               OPENFERMENT_TEST_DATABASE_URL="postgresql://openferment:openferment@127.0.0.1:5432/bh_r2_test")
    done = subprocess.run([str(WT / "core/.venv/bin/python"), "-m", "pytest", *tests, "-x", "-q", "-p", "no:randomly",
                           "-p", "no:cacheprovider", "-m", "not live and not sim and not slow and not lit"],
                          cwd=WT / "core", env=env, capture_output=True, text=True, timeout=1500)
    tail = [ln for ln in done.stdout.splitlines() if ln.strip()][-3:]
    return done.returncode == 0, " | ".join(tail)


out = []
for mid, claim, path, old, new, tests in M:
    if ONLY and mid not in ONLY:
        continue
    f = WT / path
    text = f.read_text(encoding="utf-8")
    if text.count(old) != 1:
        out.append({"id": mid, "claim": claim, "result": f"not applied: the text occurs {text.count(old)} times"})
        print(out[-1], flush=True)
        continue
    f.write_text(text.replace(old, new), encoding="utf-8")
    t0 = time.time()
    try:
        passed, tail = run(tests)
    finally:
        subprocess.run(["git", "checkout", "--", path], cwd=WT, check=True)
    out.append({"id": mid, "claim": claim, "file": path, "tests": tests,
                "result": "survived" if passed else "caught", "seconds": round(time.time() - t0, 1), "tail": tail})
    print(json.dumps(out[-1]), flush=True)

dest = Path(__file__).resolve().parent.parent / "mutations.json"
prev = json.loads(dest.read_text()) if dest.exists() else []
keep = {m["id"]: m for m in prev}
keep.update({m["id"]: m for m in out})
dest.write_text(json.dumps(sorted(keep.values(), key=lambda m: m["id"]), indent=1) + "\n")
