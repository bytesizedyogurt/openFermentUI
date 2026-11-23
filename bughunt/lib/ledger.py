"""bughunt/lib/ledger.py: the coverage ledger, bughunt/coverage.csv.

  python3 -I bughunt/lib/ledger.py init    rows from the tree: every file changed 112eb8b..HEAD, every
                                          operation in docs/api/openapi.json, every tool in docs/TOOLS.md,
                                          every rail entry and screen, every registered engine
  python3 -I bughunt/lib/ledger.py merge   fills hunts, methods and findings from bughunt/notes/H*/coverage.jsonl
                                          (one JSON object a line: kind, item, method, findings, note)

Columns: kind, item, detail, assigned, examined_by, method, findings, reason.
"""
import csv, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "bughunt" / "coverage.csv"
BASE = "112eb8b"
COLS = ["kind", "item", "detail", "assigned", "examined_by", "method", "findings", "reason"]


def assign_file(p: str) -> str:
    rules = [
        (r"^core/openferment_core/(engine/|fermos_engine|pureos/engine|workers/)", "H1 H2"),
        (r"^core/openferment_core/(studies/|comparisons|proforma|runs)", "H2"),
        (r"^core/openferment_core/(basis|units|params|measurements|models|quantit)", "H3"),
        (r"^core/openferment_core/(kinetics|fermos|pureos|library|flowsheets|thermo)", "H4"),
        (r"^core/openferment_core/(migrations|migrate|kit_alembic|alembic|import_alpha1|db)", "H6"),
        (r"^core/openferment_core/(intake|literature|sff|collect|extract|kit)", "H8"),
        (r"^core/openferment_core/(postdoc|tools|llm|spend|mcp|evaluate)", "H9"),
        (r"^core/openferment_core/(api|guard|project|catalog|audit|writes)", "H5 H10"),
        (r"^core/openferment_core/", "H5 H10"),
        (r"^core/tests/", "H12"),
        (r"^src/", "H7"),
        (r"^scripts/host/", "H11"),
        (r"^scripts/", "H13"),
        (r"^examples/", "H13 H1"),
        (r"^(docs/|README|CLAUDE|COMPONENTS|\.github/|\.mcp)", "H13"),
    ]
    for pat, h in rules:
        if re.search(pat, p):
            return h
    return "H13"


def assign_op(path: str) -> str:
    for pat, h in [(r"/(engines|runs)", "H1 H2"), (r"/(proforma|studies|scenarios|comparisons|library|biorepo/artifacts)", "H2"),
                   (r"/(fermos|pureos|thermo)", "H4"), (r"/(intake|literature|flowsheets|rag|papers)", "H8"),
                   (r"/(postdoc|ask|conversations|eval)", "H9"), (r"/(depositions|runbooks|protocols)", "H3 H7")]:
        if re.search(pat, path):
            return h + " H5"
    return "H5 H10"


def rows_init() -> list[dict]:
    rows = []
    changed = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-status", f"{BASE}", "HEAD", "--", ".",
                              ":(exclude)bughunt", ":(exclude)docs/reports/bug-hunt-2026-11.md"],
                             capture_output=True, text=True, check=True).stdout.splitlines()
    for line in changed:
        st, *paths = line.split("\t")
        p = paths[-1]
        rows.append({"kind": "file", "item": p, "detail": st, "assigned": assign_file(p)})
    api = json.loads((ROOT / "docs/api/openapi.json").read_text())
    for path, ops in api["paths"].items():
        for m, o in ops.items():
            if m in ("get", "post", "put", "patch", "delete"):
                rows.append({"kind": "operation", "item": f"{m.upper()} {path}",
                             "detail": o.get("x-openferment-scope", ""), "assigned": assign_op(path)})
    tools = (ROOT / "docs/TOOLS.md").read_text()
    names = re.findall(r"^#+\s+`?([a-z_]+)`?\s*$", tools, re.M)
    for n in names:
        if n == "thermosteam":
            continue
        rows.append({"kind": "tool", "item": n, "detail": "sci-rag" if n in {
            "answer_question", "corpus_stats", "get_citations", "get_document", "get_entity_relationships",
            "list_sources", "search_corpus", "search_entities"} else "openferment", "assigned": "H9 H5"})
    nav = (ROOT / "src/data/nav.ts").read_text()
    rail_block = nav.split("export const RAIL", 1)[1].split("];", 1)[0]
    for label, to in re.findall(r"label: '([^']+)',\s*to: '([^']+)'", rail_block):
        rows.append({"kind": "rail", "item": label, "detail": to, "assigned": "H7 H14"})
    for f in sorted((ROOT / "src/screens").glob("*.tsx")):
        rows.append({"kind": "screen", "item": f"src/screens/{f.name}", "detail": "", "assigned": "H7 H14"})
    py = (ROOT / "core/pyproject.toml").read_text()
    block = py.split('[project.entry-points."openferment.engines"]', 1)[1].split("[", 1)[0]
    for name, target in re.findall(r'^(\w+)\s*=\s*"([^"]+)"', block, re.M):
        rows.append({"kind": "engine", "item": name, "detail": target, "assigned": "H1 H2 H4"})
    for pp in sorted((ROOT / "examples/engines").glob("*/pyproject.toml")):
        t = pp.read_text()
        if 'openferment.engines' in t:
            b = t.split('[project.entry-points."openferment.engines"]', 1)[1].split("[", 1)[0]
            for name, target in re.findall(r'^(\w+)\s*=\s*"([^"]+)"', b, re.M):
                rows.append({"kind": "engine", "item": name, "detail": f"{target} (examples)", "assigned": "H1 H13"})
    for r in rows:
        for c in COLS:
            r.setdefault(c, "")
    return rows


def write(rows):
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def merge():
    rows = list(csv.DictReader(CSV.open()))
    index = {(r["kind"], r["item"]): r for r in rows}
    unknown = []
    for jl in sorted((ROOT / "bughunt/notes").glob("*/coverage.jsonl")):
        hunt = jl.parent.name
        for line in jl.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (e.get("kind", ""), e.get("item", ""))
            r = index.get(key)
            if r is None:
                unknown.append((hunt, key))
                continue
            def add(col, val):
                vals = [v for v in r[col].split(";") if v]
                for v in (val if isinstance(val, list) else [val]):
                    v = str(v).strip()
                    if v and v not in vals:
                        vals.append(v)
                r[col] = ";".join(vals)
            add("examined_by", hunt)
            add("method", e.get("method", ""))
            add("findings", e.get("findings", []))
            if e.get("note") and not r["reason"]:
                r["reason"] = e["note"][:200]
    write(rows)
    print(f"merged; {len(unknown)} entries named no ledger row")
    for h, k in unknown[:40]:
        print(" ", h, k)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        rows = rows_init()
        write(rows)
        from collections import Counter
        print(len(rows), Counter(r["kind"] for r in rows))
    elif cmd == "merge":
        merge()
    else:
        print(__doc__)
