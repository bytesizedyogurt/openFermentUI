"""H8-07 probe, three steps run by run.sh.

  paste ORIGIN PROJECT        two documents pasted through POST /api/intake/paste, both titled "Strain report";
                              prints "doc A <id>" and "doc B <id>".
  candidate PROJECT DOC_A     one candidate kept on A's first passage through extract.add_candidate (no model call);
                              run from core/ with OPENFERMENT_DATABASE_URL set.
  verdict RUN_FILE DB_URL     reads the kept run of `literature_live report` and prints what each rule scored for the
                              one question, with EXPECTED, OBSERVED and RESULT lines.
"""
from __future__ import annotations

import json
import subprocess
import sys

TITLE = "Strain report"
QUOTE = "The batch fermentation reached an ethanol titre of 41 g/L after 48 h in the H8 lane probe."
A_TEXT = QUOTE + "\n\nAgitation was held constant through the run and the vessel was sampled twice a day."
B_TEXT = ("What ethanol titre is reported? This review lists what ethanol titre is reported across strains and "
          "feeds, and which titre each study reported, as a guide to the reported ethanol titres.")


def paste(origin: str, project: str) -> None:
    import httpx

    root = httpx.Client(base_url=origin, trust_env=False, timeout=120)
    made = root.post("/api/projects", json={"id": project, "name": project, "by": "h8-07"})
    print("project:", made.status_code)
    c = httpx.Client(base_url=origin, trust_env=False, timeout=300, headers={"X-OpenFerment-Project": project})
    for name, text in (("A", A_TEXT), ("B", B_TEXT)):
        r = c.post("/api/intake/paste", json={"title": TITLE, "text": text, "by": "h8-07"}).json()
        print(f"doc {name} {r['documentId']} status={r['status']} title={r['title']!r}")


def candidate(project: str, doc: str) -> None:
    sys.path.insert(0, ".")
    from openferment_core import extract, projects

    with projects.using(project):
        made, rule, detail = extract.add_candidate(doc, {
            "sectionId": "p0", "field": "ethanol_titre", "value": 41, "unit": "g/L", "quote": QUOTE}, who="h8-07")
    print("candidate:", made.id if made else None, "refused:", rule, detail)


def _sql(db_url: str, q: str) -> list[list[str]]:
    out = subprocess.run(["psql", db_url, "-qXAt", "-F", "\t", "-c", q], capture_output=True, text=True, check=True)
    return [line.split("\t") for line in out.stdout.splitlines() if line]


def verdict(run_file: str, db_url: str) -> None:
    run = json.load(open(run_file, encoding="utf-8"))
    questions = run["truth"]["questions"]
    print("questions built:", len(questions))
    q = questions[0]
    print(f"question {q['id']}: {q['question']!r}; its document {q['documentId']}, its passage (chunk) "
          f"{q['chunkId']}, its evidence phrases {q['evidence']!r}")
    rows = _sql(db_url, "SELECT d.id::text, d.title FROM sci_rag.documents d ORDER BY d.ingested_at")
    titles = {i: t for i, t in rows}
    for i, t in rows:
        print(f"  document {i} titled {t!r}")
    defect_lanes = []
    for config, lane in run["retrieval"].items():
        ranked = lane["ranked"][q["id"]]
        k = next(r for r in lane["kit"]["records"] if r["question_id"] == q["id"])
        p = next(r for r in lane["passage"]["records"] if r["question_id"] == q["id"])
        print(f"[{config}] kit rule relevant ranks {k['relevant_ranks']} (first {k['first_relevant_rank']}); "
              f"passage rule relevant ranks {p['relevant_ranks']} (first {p['first_relevant_rank']}); "
              f"kit MRR {lane['kit']['metrics'].get('mrr')}, passage MRR {lane['passage']['metrics'].get('mrr')}")
        wrong = []
        for rank in k["relevant_ranks"]:
            item = ranked[rank - 1]
            content = _sql(db_url, "SELECT regexp_replace(content, '\\s+', ' ', 'g') FROM sci_rag.chunks "
                                   f"WHERE id::text = '{item['chunkId']}'")
            text = " ".join((content[0][0] if content else "").lower().split())
            holds = any(" ".join(e.lower().split()) in text for e in q["evidence"])
            own = item["documentId"] == q["documentId"]
            print(f"    rank {rank}: chunk {item['chunkId']} of document {item['documentId']} "
                  f"(titled {titles.get(item['documentId'])!r}); the question's document: {own}; "
                  f"holds an evidence phrase (the quote): {holds}")
            if not own and not holds:
                wrong.append(rank)
        if wrong:
            defect_lanes.append(f"{config} ranks {wrong}")
    print("EXPECTED: the kit rule counts only a passage of the question's document or one holding its candidate's "
          "quote, so document B's passage (another document, no quote) is irrelevant and the kit rule's first "
          "relevant rank is A's passage, as the passage rule's is")
    if defect_lanes:
        print("OBSERVED: the kit rule counts document B's passage as relevant (it shares only the title "
              f"{TITLE!r} with A): {'; '.join(defect_lanes)}")
        print("RESULT: DEFECT")
    else:
        print("OBSERVED: every passage the kit rule counts is of the question's document or holds its quote")
        print("RESULT: NO-DEFECT")


if __name__ == "__main__":
    step = sys.argv[1]
    if step == "paste":
        paste(sys.argv[2], sys.argv[3])
    elif step == "candidate":
        candidate(sys.argv[2], sys.argv[3])
    else:
        verdict(sys.argv[2], sys.argv[3])
