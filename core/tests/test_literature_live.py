"""The command over the literature lanes that call a model (literature_live.py;
ADR-002, Implementation F): a dry run that calls nothing, a build and a run
audited under the person named, the run whole kept in the data folder and its
numbers rendered, the stop read from the command's own tally, and core/.env
read with a setting the environment holds standing.

Offline: no key, no model. The kit's model is a stand-in where a build or a
run asks one, and the loader of core/.env is a stand-in everywhere except its
own test, which reads a file of its own.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import LLMClient
from sqlalchemy import insert

from openferment_core import audit, db, extract, literature_live, llm, projects
from openferment_core.db import models as t
from openferment_core.literature import graph, kit, report
from openferment_core.models import Candidate, ExtractResponse, Quantity

HERE = "test-project"
BY = "A placeholder person"
LOAD_ENV = extract.load_env


@pytest.fixture(autouse=True)
def _offline(kit_database, monkeypatch):
    monkeypatch.setattr(extract, "load_env", lambda path=None: None)
    yield
    kit.install_model(None)


class Quiet(LLMClient):
    """A stand-in model that names nothing in any passage."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                       max_tokens: int = 2048, json_mode: bool = False) -> str:
        self.prompts.append(prompt)
        return json.dumps({"entities": [], "relationships": []})

    def stream(self, prompt: str, **_: object):
        raise NotImplementedError


def _store(tmp_path, words: str) -> kit.Stored:
    tag = uuid.uuid4().hex[:10]
    path = tmp_path / f"{tag}.md"
    path.write_text(f"# Placeholder study {tag}\n\n## Part\n\n{words} Run {tag}.\n", encoding="utf-8")
    entry = CorpusEntry(path=path, title=f"Placeholder study {tag}", source=kit.source(HERE, "paste"),
                        license_class="public")
    [stored] = kit.ingest([entry], project_id=HERE, selections=[{"collector": "paste"}], by="test")
    return stored


def _said(capsys) -> dict:
    """The command's answer: the last line it printed (the kit logs its ingests above it)."""
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _audited(action: str) -> list:
    with projects.using(HERE):
        return audit.read(action=action)


def test_the_stop_says_the_first_call_no_model_answered_and_a_refusal_stops_nothing():
    spent: list = []
    watch = literature_live.Watch(spent)
    assert watch() is None
    spent.append(SimpleNamespace(outcome="refused", failure="declined in words"))
    spent.append(SimpleNamespace(outcome="answered", failure=None))
    assert watch() is None
    spent.append(SimpleNamespace(outcome="unavailable", failure="The day's cap holds (a placeholder)."))
    assert watch() == "The day's cap holds (a placeholder)." and watch() is None


def test_a_dry_run_measures_what_a_build_would_send_and_calls_no_model(tmp_path, monkeypatch, capsys):
    _store(tmp_path, "The placeholder organism grew.")

    def asked(*_, **__):
        raise AssertionError("a dry run asked for a model")

    monkeypatch.setattr(llm, "kit_client", asked)
    assert literature_live.main(["graph", "--project", HERE, "--dry-run"]) == 0
    said = _said(capsys)
    rows = db.run(graph.pending(HERE))
    assert said["chunks"] == len(rows) >= 1 and said["batches"] == len(graph.prompts(rows))
    assert said["promptCharacters"] == sum(len(p) for p in graph.prompts(rows)) and said["model"] == llm.chain("index")[0]
    assert 0 < said["inputUsd"] < said["mostUsd"] and not _audited("literature_graph")


def test_a_build_is_audited_under_the_person_named(tmp_path, monkeypatch, capsys):
    _store(tmp_path, "The placeholder organism grew.")
    model = Quiet()
    monkeypatch.setattr(llm, "kit_client", lambda role="answer": model)
    assert literature_live.main(["graph", "--project", HERE, "--by", BY]) == 0
    said = _said(capsys)
    assert said["chunks_processed"] >= 1 and said["stopped"] is None and model.prompts
    [row] = _audited("literature_graph")
    assert (row.agent, row.who, row.module, row.state) == ("person", BY, "intake", "done")
    assert row.detail["chunks_processed"] == said["chunks_processed"]


def _kept_candidate(stored: kit.Stored, words: str) -> None:
    passage = next(p["id"] for p in kit.passages(stored.document_id, project_id=HERE).sections if words in p["text"])
    body = ExtractResponse(paperId=stored.document_id, extractedAt="2026-11-08T00:00:00Z", candidates=[Candidate(
        id="c-placeholder", paperId=stored.document_id, sectionId=passage, quote=words, field="titer_secreted",
        value=1.0, unit="g L⁻¹", si=Quantity(value=1.0, unit="g L⁻¹"))])

    async def put() -> None:
        async with db.session() as s:
            await s.execute(insert(t.candidates).values(project_id=HERE, document_id=stored.document_id,
                                                        source="model", body=body.model_dump(mode="json"),
                                                        created_by="test"))

    db.run(put())


def test_a_run_keeps_its_whole_in_the_data_folder_and_renders_its_numbers_alone(tmp_path, monkeypatch, capsys):
    words = f"the placeholder reading {uuid.uuid4().hex[:8]} stood at its mark"
    _kept_candidate(_store(tmp_path, f"In this run {words}."), words)
    monkeypatch.setenv("OPENFERMENT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(report, "OUT", tmp_path / "reports" / "literature-retrieval")
    assert literature_live.main(["report", "--project", HERE, "--by", BY, "--configs", "interactive,keyword_only",
                                 "--render"]) == 0
    said = _said(capsys)
    kept = json.loads((tmp_path / "data" / "literature" / said["file"].rsplit("/", 1)[-1]).read_text())
    assert said["file"].startswith(str(tmp_path / "data" / "literature" / f"{HERE}-"))
    assert kept["truth"]["questions"][0]["evidence"] == [words] and kept["by"] == BY and kept["public"]
    md = report.OUT.with_suffix(".md").read_text()
    assert f"`{HERE}`" in md and words not in md and words not in report.OUT.with_suffix(".json").read_text()
    [row] = _audited("literature_report")
    assert (row.who, row.state, row.detail["file"], row.detail["questions"]) == (BY, "done", said["file"], 1)

    # A kept run's file renders alone, and spends nothing.
    report.OUT.with_suffix(".md").unlink()
    assert literature_live.main(["report", "--project", HERE, "--render", "--from", said["file"]]) == 0
    assert f"`{HERE}`" in report.OUT.with_suffix(".md").read_text() and len(_audited("literature_report")) == 1


def test_a_project_the_store_does_not_hold_and_a_run_with_no_question_are_refused_in_words(tmp_path, monkeypatch,
                                                                                        capsys):
    assert literature_live.main(["report", "--project", "no-such-project", "--by", BY]) == 2
    assert "holds no project 'no-such-project'" in capsys.readouterr().err
    monkeypatch.setenv("OPENFERMENT_DATA_DIR", str(tmp_path / "data"))
    assert literature_live.main(["report", "--project", HERE, "--by", BY, "--configs", "interactive"]) == 2
    assert "holds no kept candidate" in capsys.readouterr().err and not (tmp_path / "data").exists()
    with pytest.raises(SystemExit):
        literature_live.main(["report", "--project", HERE])
    assert "--by names the person" in capsys.readouterr().err


def test_core_env_is_read_with_a_setting_the_environment_holds_standing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OPENFERMENT_PLACEHOLDER_A=from-the-file\nOPENFERMENT_PLACEHOLDER_B=from-the-file\n")
    monkeypatch.setenv("OPENFERMENT_PLACEHOLDER_A", "from-the-environment")
    monkeypatch.delenv("OPENFERMENT_PLACEHOLDER_B", raising=False)
    LOAD_ENV(env)
    import os

    assert os.environ["OPENFERMENT_PLACEHOLDER_A"] == "from-the-environment"
    assert os.environ.pop("OPENFERMENT_PLACEHOLDER_B") == "from-the-file"
