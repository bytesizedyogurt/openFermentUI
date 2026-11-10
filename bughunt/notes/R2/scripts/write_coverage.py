"""R2: writes coverage.jsonl, one line an item examined, keys as bughunt/coverage.csv writes them."""
import csv
import json
from pathlib import Path

ROOT = Path("/home/user/openFermentUI")
keys = {(r["kind"], r["item"]) for r in csv.DictReader((ROOT / "bughunt/coverage.csv").open())}
rows = [
    ("file", "docs/reports/handoff-2026-11.md", "executed", ["R2-04"], "every sentence held to the tree: the diff over the core paths, the mirror's files, README lengths, tests (30 pass), the page's install and conform mirror 8 of 8 in my worktree, the record-reader run against my service (exit 0, 50 tools, the entry and audit row as quoted), the audit route at CORE, the six engines.md points, E.16's five payments"),
    ("file", "docs/decisions/ADR-000-fresh-slate.md", "read", [], "alpha 2.2 lines: backticked paths and names held by scripts/adr_refs.py"),
    ("file", "docs/decisions/ADR-001-postgresql.md", "read", [], "alpha 2.2 lines held by adr_refs.py"),
    ("file", "docs/decisions/ADR-002-sci-rag-kit.md", "executed", ["R2-01"], "Implementation F read whole; KIT_ROLES, the batching rule and the dry run checked; the dry run's cost is R2-01"),
    ("file", "docs/decisions/ADR-003-sff.md", "read", [], "library_flowsheets named deleted, as in the tree"),
    ("file", "docs/decisions/ADR-004-biosteam-adapter.md", "read", [], "alpha 2.2 lines held by adr_refs.py"),
    ("file", "docs/decisions/ADR-005-projects.md", "read", [], "the --service loopback rule tried on the MCP server"),
    ("file", "docs/decisions/ADR-006-quantities-and-estimates.md", "executed", [], "C.4, C.5, D.0, E.15, E.17, E.debts notes read; the override unit rules and NaN refusals tried on my service"),
    ("file", "docs/decisions/ADR-007-schema-source.md", "read", [], "E.0a schema counts (189 to 255, 66 new) checked; paths named are deleted files or generated fixtures"),
    ("file", "docs/decisions/ADR-008-postdoc-memory-routing.md", "executed", [], "Implementations 12 to 19 read; routes() defaults and overlays run; arithmetic of 15 to 17 checked"),
    ("file", "docs/decisions/ADR-009-ui.md", "read", [], "alpha 2.2 lines held by adr_refs.py"),
    ("file", "docs/decisions/ADR-010-deletions.md", "read", [], "E.10 note: enumeration.ts gone from the tree"),
    ("file", "docs/decisions/ADR-011-guards.md", "read", [], "E.15 note: check:plan run green in my worktree"),
    ("file", "docs/decisions/ADR-014-durable-write-queue.md", "read", [], "alpha 2.2 lines held by adr_refs.py"),
    ("file", "docs/decisions/ADR-015-engine-contract.md", "executed", ["R2-02"], "read whole; entry points, 48 tools, withheld names, conform biosteam, kinetics and mirror 8 of 8, the missing-database case is R2-02"),
    ("file", "docs/decisions/ADR-016-bench-readings-alone.md", "read", [], "alpha 2.2 decision read"),
    ("file", "docs/decisions/ADR-017-project-protocols.md", "executed", [], "read whole; routes, migration 0010, version-held refusal (M15 caught)"),
    ("file", "docs/decisions/ADR-018-lesson-body.md", "read", [], "the nine embeds match the service and the page"),
    ("file", "docs/PROGRESS.md", "read", ["R2-01"], "the Spend, Known debts and stage-log lines the commit messages cite; sums and row counts checked; lines 609 and 3372 repeat R2-01's numbers"),
    ("file", "docs/reports/literature-retrieval.md", "executed", ["R2-01"], "the ethanol part's counts checked against the .json; the dry run's cost lines are R2-01"),
    ("file", "docs/reports/literature-retrieval.json", "read", [], "questions, groups, documents, chunks and lane numbers set beside the .md"),
    ("file", "docs/reports/model-routing-2026-11.md", "read", [], "the 8 November section's arithmetic checked (differences, means, costs)"),
    ("file", "docs/api/engines.md", "read", [], "the six points of the handoff and the conform paragraph"),
    ("file", "docs/TOOLS.md", "read", ["R2-04"], "line count at CORE, the VIRTUAL_ENV recipe, catalogue_write's input"),
    ("file", "docs/runbooks/live-host-install.md", "read", [], "the backup lines of steps 3, 6 and 7, the routing settings, the pnpm commands"),
    ("file", "examples/agents/record-reader/record_reader.py", "executed", [], "run against my service on 8970: exit 0"),
    ("file", "examples/agents/record-reader/README.md", "read", [], "six lines"),
    ("file", "examples/engines/openferment-engine-mirror/README.md", "read", [], "ten lines"),
    ("file", "examples/engines/openferment-engine-mirror/pyproject.toml", "executed", [], "installed into my worktree's venv with the page's command"),
    ("file", "examples/engines/openferment-engine-mirror/openferment_engine_mirror/worker.py", "executed", [], "conform mirror 8 of 8"),
    ("file", "examples/engines/openferment-engine-mirror/openferment_engine_mirror/engine.py", "executed", [], "listed by the registry beside the core's three"),
    ("file", "examples/engines/openferment-engine-mirror/openferment_engine_mirror/__init__.py", "read", [], ""),
    ("file", "examples/engines/openferment-engine-mirror/tests/test_engine.py", "executed", [], "6 tests pass"),
    ("file", "examples/engines/openferment-engine-mirror/tests/test_worker.py", "executed", [], "24 tests pass"),
    ("file", "core/openferment_core/literature_live.py", "executed", ["R2-01"], "graph_command's dry-run branch driven with stand-ins"),
    ("file", "core/openferment_core/engine/conform.py", "executed", ["R2-02"], "run against a missing database, an unreachable server, and on bh_r2_conform_cfg"),
    ("file", "core/openferment_core/mcp_server.py", "fuzzed", ["R2-03"], "--service refusals tried; trust_env and follow_redirects mutated (M16 survived, M17 caught)"),
    ("file", "core/openferment_core/llm.py", "fuzzed", ["R2-01"], "routes() overlays run; KIT_ROOM, effort overlays mutated (M02, M03, M11 caught); price tiers read"),
    ("file", "core/openferment_core/project_state.py", "fuzzed", [], "M01, M13 caught; a malformed kept row named in refused on my service"),
    ("file", "core/openferment_core/catalogues.py", "fuzzed", [], "M14 caught; twelve categories, nine embeds"),
    ("file", "core/openferment_core/protocols.py", "fuzzed", [], "M15 caught"),
    ("file", "core/openferment_core/models.py", "fuzzed", [], "M12 caught; configurationTitles rules read"),
    ("file", "core/openferment_core/postdoc/plan.py", "fuzzed", [], "M08 caught"),
    ("file", "core/openferment_core/tools/engine.py", "fuzzed", [], "M09 caught"),
    ("file", "core/openferment_core/literature/report.py", "fuzzed", [], "M10 survived; the command's own guard is tested"),
    ("file", "core/openferment_core/literature/collectors.py", "fuzzed", [], "M20 and M21 survive and change nothing: the fetch is always handed its pinned transport"),
    ("file", "core/openferment_core/api.py", "fuzzed", [], "M04, M18 caught; the audit route's filters tried"),
    ("file", "core/openferment_core/ready.py", "executed", [], "ready --offline against bh_r2_svc"),
    ("file", "core/openferment_core/workers/__init__.py", "read", [], "withheld names against ADR-015"),
    ("file", "scripts/host/lib.sh", "fuzzed", [], "backup_database mutated four ways (M05, M06, M07, M19), each caught"),
    ("file", "core/tests/test_host.py", "executed", [], "58 passed with test_guidance.py"),
    ("file", "core/tests/test_mcp_service.py", "executed", ["R2-03"], "run under M16 and M17 with the port-binding test deselected"),
    ("file", "core/tests/test_engines.py", "read", [], "the page-example test and the withheld test"),
    ("file", "core/tests/test_engine_pins.py", "read", [], "17 pins"),
    ("file", "core/tests/test_literature_live.py", "executed", [], "the --limit test, under M10"),
    ("file", "CLAUDE.md", "read", [], "line counts 148 and 149 at ae6f74c and 2047f5a"),
    ("file", "COMPONENTS.md", "read", [], "src/data/'s nine files"),
    ("file", "package.json", "read", [], "which scripts run uv with --frozen"),
    ("operation", "GET /api/audit", "executed", [], "filters, limit, null fields"),
    ("operation", "POST /api/tools/{name}", "executed", [], "auditIds, the by rule"),
    ("operation", "POST /api/engines/{name}/run", "fuzzed", [], "stray fields, booleans, NaN, Infinity, overflow, missing at"),
    ("operation", "POST /api/fermos/simulate", "fuzzed", [], "NaN and Infinity"),
    ("operation", "POST /api/params/{scope}/resolve", "fuzzed", [], "NaN and Infinity"),
    ("operation", "POST /api/library/{plant}/run", "fuzzed", [], "NaN and Infinity"),
    ("operation", "POST /api/studies/scenarios", "fuzzed", [], "NaN and Infinity"),
    ("operation", "GET /api/state", "executed", [], "a malformed kept row named in refused"),
    ("operation", "PUT /api/state/{kind}/{item_id}", "executed", [], "the override unit rules"),
    ("operation", "GET /api/engines", "executed", [], "lists biosteam, kinetics, train"),
    ("operation", "GET /api/engines/{name}/parameters", "executed", [], "kinetics batch_v1"),
    ("operation", "GET /api/health", "executed", [], "names the plan route's models"),
    ("operation", "POST /api/projects", "executed", [], "made r2p"),
    ("tool", "catalogue_write", "executed", [], "through the HTTP door and the MCP relay"),
    ("engine", "biosteam", "executed", ["R2-02"], "conform against a missing database"),
    ("engine", "kinetics", "executed", [], "conform --inputs 8 of 8"),
    ("engine", "mirror", "executed", [], "installed in my worktree; conform 8 of 8"),
    ("engine", "train", "executed", ["R2-02"], "conform --project against a missing database"),
]
out = ROOT / "bughunt/notes/R2/coverage.jsonl"
with out.open("w", encoding="utf-8") as f:
    for kind, item, method, findings, note in rows:
        line = {"kind": kind, "item": item, "method": method, "findings": findings}
        if note:
            line["note"] = note
        if (kind, item) not in keys:
            line["note"] = (note + "; " if note else "") + "not a key of coverage.csv"
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
missing = [(k, i) for k, i, *_ in rows if (k, i) not in keys]
print(len(rows), "lines;", "missing keys:", missing)
