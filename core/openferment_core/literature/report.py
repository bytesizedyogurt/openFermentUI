"""`python -m openferment_core.literature.report` — the retrieval report
(ADR-002; execution prompt §8.2): Sci RAG Kit's own evaluation harness run
over its demo corpus, as openFerment runs the kit.

    pnpm lit:report        writes docs/reports/literature-retrieval.md and .json

In a database of its own on the tests' server (OPENFERMENT_TEST_DATABASE_URL,
dropped after), a project holds the five demo documents
(core/tests/fixtures/kit-demo/, CC0, fictional), embedded by FastEmbed. Each
of the kit's seed questions for that corpus is asked of the retriever inside
the project's scope, in the configurations that ask no model (vector and
keyword together, as Search runs; each alone), and the kit scores where the
passage holding the answer's evidence ranks: hit at 5 and 10, mean reciprocal
rank, nDCG at 10, each with a bootstrap interval. The layers that call a model
(graph, HyDE) are left out, because a report anyone can regenerate must not
need a key; the answers' grading by a judge model likewise.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

from sci_rag.evals.report import corpus_fingerprint, retrieval_markdown, retrieval_payload
from sci_rag.evals.retrieval_eval import DEFAULT_ABLATIONS, run_retrieval_eval
from sci_rag.evals.seeds import load_seed_questions
from sci_rag.ingest.manifest import CorpusEntry
from sqlalchemy import insert

from .. import db, migrations, projects
from ..db import migrate
from ..db import models as t
from . import EMBEDDING_DIM, EMBEDDING_MODEL, kit

CORE = Path(__file__).parent.parent.parent
DEMO = CORE / "tests" / "fixtures" / "kit-demo"
OUT = CORE.parent / "docs" / "reports" / "literature-retrieval"
PROJECT = "retrieval-report"
# The kit's configurations that ask no model.
CONFIGS = ("interactive", "vector_only", "keyword_only")


def _entries() -> list[CorpusEntry]:
    rows = [json.loads(line) for line in (DEMO / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
    return [CorpusEntry(**{**row, "path": DEMO / row["path"], "source": kit.source(PROJECT, "upload")}) for row in rows]


async def _project() -> None:
    async with db.session() as s:
        await s.execute(insert(t.projects).values(id=PROJECT, name="Retrieval report", created_by="the report"))


def _run() -> tuple[str, dict]:
    db.run(_project())
    entries = _entries()
    kit.ingest(entries, project_id=PROJECT, selections=[{"collector": "upload"} for _ in entries], by="the report")
    questions = load_seed_questions(DEMO / "eval_seed_questions.jsonl")
    configs = [c for c in DEFAULT_ABLATIONS if c.name in CONFIGS]
    service = kit.service()

    async def evaluate():
        with projects.using(PROJECT):
            scope = await kit._narrowed(None)
            results = await run_retrieval_eval(service.retriever, questions, configs=configs, scope=scope)
        return results, await corpus_fingerprint(service.session_factory)

    results, fingerprint = db.run(evaluate())
    provenance = {"embedding": f"fastembed:{EMBEDDING_MODEL}@{EMBEDDING_DIM}", "models": "none asked",
                  "corpus": "Sci RAG Kit 0.5.0 demo corpus (data/demo at 26b3990)"}
    payload = retrieval_payload(results, fingerprint, questions=questions, provenance=provenance)
    when = datetime.now(UTC).strftime("%Y-%m-%d")
    head = [
        "<!-- Written by `pnpm lit:report` (core/openferment_core/literature/report.py); regenerate, do not edit. -->",
        "",
        "# Literature retrieval report",
        "",
        f"Sci RAG Kit's retrieval evaluation over its demo corpus, as openFerment runs the kit ({when}):",
        f"FastEmbed `{EMBEDDING_MODEL}` ({EMBEDDING_DIM} dimensions), the project's scope, and the",
        "configurations that ask no model. `interactive` is what BioRepo → Search runs. The kit's",
        "note below compares rows with `full_deep`, which asks a model and is not run here: read",
        "`interactive` as the baseline instead.",
        "",
    ]
    kit_text = retrieval_markdown(results, fingerprint, questions=questions).replace(
        "# Retrieval evaluation", "## The kit's retrieval evaluation", 1
    )
    return "\n".join(head) + "\n" + kit_text, payload


def main(argv: list[str]) -> int:
    server = os.environ.get("OPENFERMENT_TEST_DATABASE_URL", "").strip() or \
        "postgresql://openferment:openferment@127.0.0.1:5432/openferment_test"
    name = f"lit_report_{os.getpid()}_{secrets.token_hex(3)}"
    url = migrate.create(name, server)
    try:
        migrations.upgrade(url)
        db.use_engine(db.make_engine(url, pool_size=2, max_overflow=2))
        kit.use_database(url)
        markdown, payload = _run()
    finally:
        kit.use_database(None)
        engine = db.use_engine(None)
        if engine is not None:
            db.run(engine.dispose())
        migrate.drop(name, server)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".md").write_text(markdown + "\n", encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(markdown)
    print(f"\nwritten to {OUT.with_suffix('.md').relative_to(CORE.parent)} and .json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
