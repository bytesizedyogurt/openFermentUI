"""Write bughunt/notes/H5/coverage.jsonl: one line for each item of coverage.csv assigned to H5, and for the
files of the brief's code list H5 read outside its assignment, with the method and the candidates found."""
import csv
import json

ROWS = list(csv.DictReader(open("/home/user/openFermentUI/bughunt/coverage.csv")))
HEAVY = {"POST /api/library/{plant}/run", "POST /api/proforma/run", "POST /api/pureos/train/run",
         "POST /api/studies/scenarios/{scenario_id}/run", "POST /api/ask", "POST /api/ask/stream", "POST /api/geneos/ceiling",
         "POST /api/geneos/frontier", "POST /api/geneos/mix", "POST /api/studies/scenarios", "POST /api/pureos/train/check"}
OPS = {
    "GET /api/literature/search": (["H5-01", "H5-02"], "B's hits during A's pastes (race.py), and A's title and licence class on a shared document"),
    "POST /api/literature/answer": (["H5-01"], "same narrowing as search (kit.ProjectService.answer_stream); keyless, so the race was shown on search alone"),
    "GET /api/literature/documents": (["H5-02"], "B's list shows A's title, url, source and licence class for a shared document"),
    "GET /api/literature/stats": (["H5-02"], "B's sources name project:bh-a:paste and count A's licence class"),
    "GET /api/biorepo/overlay": (["H5-02"], "B's paper shows A's title, url and licence class beside B's licence words"),
    "POST /api/intake/paste": (["H5-02"], "the answer says B's title and class; every read after says A's"),
    "PUT /api/state/{kind}/{item_id}": (["H5-03"], "a Proforma scenario and a made train PUT under a study scenario's and a kept train's ids replace them"),
    "DELETE /api/state/{kind}/{item_id}": (["H5-04", "H5-03"], "a locked study runbook is taken back; the study scenario overwritten by H5-03 is then removed"),
    "POST /api/fermos/forecast": (["H5-05"], "an artifact id the project does not hold answers 500"),
    "GET /api/protparam": (["H5-06"], "no project named: 404 'no product in the products catalogue'"),
    "POST /api/protparam": (["H5-06"], "no project named: 404 'no product in the products catalogue'"),
    "POST /api/pureos/propose": (["H5-06"], "no project named: 404 about the catalogue"),
    "GET /api/thermo/volatility": (["H5-06"], "no project named: 404 about the product"),
    "POST /api/thermo/volatility": (["H5-06"], "no project named: 404 about the product"),
    "POST /api/guild/check": (["H5-06", "H5-07"], "no project named: 200 ok:false 'not a skill Guild holds (none ship with alpha 2.0)'"),
    "POST /api/guild/evidence": (["H5-06", "H5-07"], "no project named: 422 about the skill; the words name alpha 2.0"),
    "POST /api/tools/{name}": (["H5-06", "H5-01", "H5-02"], "no project named: 200 with '<tool> failed: ProjectRequired'; search_passages raced (race_tool.py)"),
    "GET /api/engines": (["H5-06"], "no project named: 200, the train engine listing no things"),
    "GET /api/events": ([], "B's stream and replays (Last-Event-ID 0, A's id - 1, after=0, after=-5) carry no event of A's (sse.py)"),
}
TOOLS = {
    "search_passages": (["H5-01", "H5-02"], "A's race notes in B's results during A's pastes; paperTitle is A's on a shared document"),
    "literature_sources": (["H5-02"], "A's title and class on a shared document"),
    "literature_document": (["H5-02", "H5-06"], "A's title; with no project, 'the project holds no readable document'"),
    "catalogue_read": (["H5-06"], "no project: 200 'catalogue_read failed: ProjectRequired'"),
    "growth_forecast": (["H5-05"], "refused in words that are only the artifact id; the HTTP route answers 500"),
    "fermos_write": (["H5-05"], "action forecast: refused in words that are only the artifact id"),
    "search_corpus": (["H5-01", "H5-02", "H5-08"], "same narrowing as /api/literature/search; unknown --project answers as an empty corpus"),
    "answer_question": (["H5-01", "H5-08"], "keyless; same narrowing; unknown --project answers as an empty corpus"),
    "get_document": (["H5-02", "H5-08"], "B reads A's title, source and source_ref on a shared document"),
    "list_sources": (["H5-02", "H5-08"], "B's sources name project:bh-a:paste"),
    "corpus_stats": (["H5-02", "H5-08"], "B's sources and licence classes carry A's"),
    "get_citations": (["H5-08"], "unknown --project: 'No such document'"),
    "search_entities": (["H5-08"], "graph rows by hand (graph_rows.sql): B lists no A-only entity, descriptions held to the rule; unknown --project: 'holds no passage yet'"),
    "get_entity_relationships": (["H5-08"], "B lists no A-only edge; an A-only quote withheld; unknown --project: 'holds no passage yet'"),
}
FILES = {
    "core/openferment_core/api.py": ("read", ["H5-05", "H5-06"], "the project middleware, every route's scope, the SSE route, /rag mount"),
    "core/openferment_core/project_state.py": ("read", ["H5-03", "H5-04"], "kinds sharing tables; _held reads the kind, rows.put writes the key"),
    "core/openferment_core/catalogues.py": ("read", ["H5-06"], "_entries swallows ProjectRequired"),
    "core/openferment_core/protocols.py": ("read", ["H5-06"], "held() swallows ProjectRequired"),
    "core/openferment_core/guild.py": ("read", ["H5-06", "H5-07"], "skill refusal names alpha 2.0"),
    "core/openferment_core/practice.py": ("read", ["H5-07"], "skill refusal names alpha 2.0"),
    "core/openferment_core/artifacts.py": ("read", [], "every read and write filtered by project; ids are content hashes, keyed per project"),
    "core/openferment_core/audit.py": ("read", [], "reads and filters by project; ids are one sequence across projects (noted in held)"),
    "core/openferment_core/biorepo.py": ("read", [], "decisions and records filtered by project"),
    "core/openferment_core/proposals.py": ("read", [], "random ids; _RUNNING is process-wide but ids are uuid4"),
    "core/openferment_core/module_stores.py": ("read", [], "Stores is per question; no process-wide cache of rows"),
    "core/openferment_core/checks.py": ("read", [], "scope scan: every store call names the project"),
    "core/openferment_core/evidence_pool.py": ("read", [], "scope scan only"),
    "core/openferment_core/nightly_checks.py": ("read", [], "scope scan only: a command acting in OPENFERMENT_PROJECT"),
    "core/openferment_core/vessel.py": ("read", [], "scope scan: _SPECS caches the library's vessel specs, no project data"),
    "core/openferment_core/geneos_models.py": ("read", [], "scope scan: _HASHED caches file hashes, no project data"),
    "core/openferment_core/guard.py": ("read", [], "middleware order: guard first, then the project, then the key"),
}
SCAN = ("atomic.py", "binding.py", "competence.py", "composite.py", "evaluation.py", "geneos.py", "protparam.py", "quotes.py",
        "ready.py", "runbook_draft.py", "runbook_lock.py", "validate.py", "witness.py", "schema/fields.yaml",
        "schema/vocabulary.yaml")
EXTRA = {
    "core/openferment_core/literature/kit.py": ("read", ["H5-01", "H5-02"], "visible() snapshots the exclusion list; reads take the kit row's title, class, source_ref"),
    "core/openferment_core/literature/graph.py": ("executed", [], "scoped reads held under hand-made graph rows (graph_reads.py)"),
    "core/openferment_core/literature_mcp.py": ("executed", ["H5-08"], "every tool called from bh-b and from unknown, malformed and upper-case projects"),
    "core/openferment_core/mcp_server.py": ("executed", [], "own process and --service, from bh-b and unknown, malformed, upper-case projects: refusals in words"),
    "core/openferment_core/intake.py": ("read", ["H5-02"], "overlay_papers takes title, url and licence class from the kit's document"),
    "core/openferment_core/db/rows.py": ("read", [], "every helper keys on (project_id, id)"),
    "core/openferment_core/db/models.py": ("read", ["H5-03"], "scenarios and trains each hold two kinds under one key"),
    "core/openferment_core/tools/__init__.py": ("read", ["H5-06"], "tools.run sets the context's project; a ProjectRequired becomes '<tool> failed'"),
    "core/openferment_core/studies/scenarios.py": ("read", ["H5-03"], "study scenarios share the scenarios table with kind engine"),
}
out = []
for r in ROWS:
    if "H5" not in r["assigned"].split():
        continue
    kind, item = r["kind"], r["item"]
    if kind == "operation":
        f, note = OPS.get(item, ([], None))
        variants = "from bh-b only (a heavy or model route)" if item in HEAVY else "from bh-b and with the header missing, empty, spaces, upper case, unicode, 200 characters, a path, a tab, unknown, and header B over ?project=A"
        out.append({"kind": kind, "item": item, "method": "fuzzed", "findings": f,
                    "note": (note + "; " if note else "") + f"probe_ops.py {variants}; A's rows unchanged"})
    elif kind == "tool":
        f, note = TOOLS.get(item, ([], None))
        door = "sci-rag MCP server from bh-b, bh-zzz, ../bh-a, BH-A" if r["detail"] == "sci-rag" else \
            "POST /api/tools, the openferment MCP server in its own process and through --service, from bh-b with A's ids; unknown, malformed, upper-case projects"
        out.append({"kind": kind, "item": item, "method": "fuzzed", "findings": f,
                    "note": (note + "; " if note else "") + f"probe_tools.py: {door}; no answer carried A's words or ids"})
    elif kind == "file":
        if item in FILES:
            m, f, note = FILES[item]
        elif any(item.endswith(s) for s in SCAN):
            m, f, note = "read", [], "scope scan only (projects.current, project_id, module-level state); no store call or none unscoped; the rest is H10's"
        else:
            m, f, note = "read", [], "scope scan only"
        out.append({"kind": kind, "item": item, "method": m, "findings": f, "note": note})
for item, (m, f, note) in EXTRA.items():
    if any(r["kind"] == "file" and r["item"] == item for r in ROWS):
        out.append({"kind": "file", "item": item, "method": m, "findings": f, "note": note + " (outside H5's assignment, in its brief)"})
with open("/home/user/openFermentUI/bughunt/notes/H5/coverage.jsonl", "w") as fh:
    for o in out:
        fh.write(json.dumps(o, ensure_ascii=False) + "\n")
print(len(out), "lines")
