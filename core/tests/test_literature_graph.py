"""The concept graph over a project's passages (literature/graph.py; ADR-002):
a build reads the project's chunks alone, through the kit's own batch step,
and each read shows what the project's own passages prove.

Offline: the kit embeds with its local embedder (conftest), and the model is a
stand-in that reads the kit's extraction prompt and names each placeholder
entity in the passages that hold it. The kit's rows are committed in the
session's database, and the kit keeps one entity a name across the store, so
every text and every entity name a test writes carries a tag of its own.
"""
from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from sci_rag.db.models import Chunk, KgEntity, KgRelationship
from sci_rag.graph import extractor
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import LLMClient
from sqlalchemy import insert, select

from openferment_core import db, projects
from openferment_core.db import models as t
from openferment_core.literature import graph, kit

HERE = "test-project"
THERE = "other-project"
HEADS = ("Methods", "Results", "Discussion", "Outlook")


@pytest.fixture(autouse=True)
def _kit(kit_database):
    pass


@pytest.fixture
def two_projects():
    async def add() -> None:
        async with db.session() as s:
            await s.execute(insert(t.projects).values(id=THERE, name=THERE, created_by="test"))

    db.run(add())


def _tag() -> str:
    return uuid.uuid4().hex[:10]


def _store(tmp_path, project_id: str, tag: str, *sections: str) -> kit.Stored:
    """A placeholder document, one passage a section, held by the project."""
    title = f"Placeholder study {tag}"
    text = f"# {title}\n\n" + "".join(f"## {HEADS[i]}\n\n{words} Run {tag}.\n\n" for i, words in enumerate(sections))
    path = tmp_path / f"{uuid.uuid4().hex}.md"
    path.write_text(text, encoding="utf-8")
    entry = CorpusEntry(path=path, title=title, source=kit.source(project_id, "paste"), license_class="public")
    [stored] = kit.ingest([entry], project_id=project_id, selections=[{"collector": "paste"}], by="test")
    assert stored.document_id and (stored.status != "ingested" or stored.chunks == len(sections)), stored
    return stored


@dataclass
class Named:
    """An entity the stand-in names in each passage holding `surface` (its
    name, unless another is given)."""

    type: str
    description: str = ""
    surface: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass
class Stated:
    """A relationship the stand-in states in each passage holding `at` (its
    quote, unless another is given)."""

    source: str
    type: str
    target: str
    evidence: str
    at: str | None = None


def _numbered(prompt: str) -> dict[int, str]:
    """The numbered passages of the kit's extraction prompt."""
    block = prompt.split("Passages:\n\n", 1)[1].split("\n\nRespond with JSON only", 1)[0]
    parts = re.split(r"(?m)^(\d+)\. ", block)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


class Reader(LLMClient):
    """A stand-in for the index route's model: it answers the kit's extraction
    prompt with the entities whose surface each passage holds and the
    relationships whose quote it holds, as the kit's prompt asks."""

    def __init__(self, entities: dict[str, Named], relations: Sequence[Stated] = (), *,
                 fails: Exception | None = None, prose: bool = False) -> None:
        self.entities = entities
        self.relations = list(relations)
        self.fails = fails
        self.prose = prose
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                       max_tokens: int = 2048, json_mode: bool = False) -> str:
        self.prompts.append(prompt)
        if self.fails is not None:
            raise self.fails
        if self.prose:
            return "The passages name several placeholder things."
        passages = _numbered(prompt)
        found, named = [], set()
        for name, e in self.entities.items():
            where = [n for n, words in passages.items() if (e.surface or name) in words]
            if where:
                found.append({"name": name, "type": e.type, "description": e.description, "passages": where,
                              "aliases": list(e.aliases)})
                named.add(name)
        stated = [{"source": r.source, "target": r.target, "type": r.type, "evidence": r.evidence, "passage": n,
                   "confidence": 1.0}
                  for r in self.relations if {r.source, r.target} <= named
                  for n, words in passages.items() if (r.at or r.evidence) in words]
        return json.dumps({"entities": found, "relationships": stated})

    def stream(self, prompt: str, **_: object):
        raise NotImplementedError("a build streams nothing")


def _build(project_id: str, model: LLMClient, **kw) -> graph.Built:
    return db.run(graph.build(project_id, llm=model, rate_limit_s=0, **kw))


def _pending(project_id: str, **kw) -> list:
    return db.run(graph.pending(project_id, **kw))


def _entities(project_id: str, name_contains: str = "", **kw) -> dict:
    async def go():
        with projects.using(project_id):
            return await kit.service().search_entities(name_contains, **kw)

    return db.run(go())


def _edges(project_id: str, entity_name: str) -> dict:
    async def go():
        with projects.using(project_id):
            return await kit.service().entity_relationships(entity_name)

    return db.run(go())


def _counts(project_id: str) -> dict:
    async def go():
        documents = (await kit.visible(project_id)).documents
        return await graph.counts(kit.service().session_factory, documents)

    return db.run(go())


def _passage(document_id: str, passage_id: str, project_id: str = HERE) -> str:
    return {p["id"]: p["text"] for p in kit.passages(document_id, project_id=project_id).sections}[passage_id]


# ── the build ──────────────────────────────────────────────────────────────


def test_a_build_reads_the_projects_chunks_alone(tmp_path, two_projects):
    tag = _tag()
    first = _store(tmp_path, HERE, tag, f"The organism-a{tag} grew in a placeholder vessel.",
                   f"The organism-a{tag} was harvested.")
    second = _store(tmp_path, HERE, tag + "b", f"The organism-b{tag} grew in a placeholder vessel.")
    theirs = _store(tmp_path, THERE, tag + "t", f"The organism-t{tag} grew in a placeholder vessel.")

    def kits_order(stored: list[kit.Stored]) -> list[str]:
        held = {d.id: d for d, _ in kit.documents(HERE)}
        rows = [(held[s.document_id].content_hash, c.chunk_index, c.id)
                for s in stored for c in kit.document(s.document_id, project_id=HERE)[1]]
        return [chunk_id for _, _, chunk_id in sorted(rows)]

    waiting = _pending(HERE)
    assert [r[0] for r in waiting] == kits_order([first, second]), "the kit's order: content hash, then chunk index"
    assert {r[1] for r in waiting} == {first.document_id, second.document_id}
    assert all(f"Run {tag}" in r[2] for r in waiting), "each row carries its chunk's words"
    assert [r[0] for r in _pending(HERE, limit=2)] == [r[0] for r in waiting[:2]]

    model = Reader({f"organism-a{tag}": Named("Organism"), f"organism-b{tag}": Named("Organism"),
                    f"organism-t{tag}": Named("Organism")})
    built = _build(HERE, model, batch_size=2)
    assert (built.chunks_pending, built.chunks_processed, built.chunks_left, built.batches_run) == (3, 3, 0, 2)
    assert (built.batches_failed, built.entities_created, built.stopped) == (0, 2, None)
    assert model.prompts and all(f"Run {tag}t" not in p and f"organism-t{tag}" not in p for p in model.prompts)
    assert sum(len(_numbered(p)) for p in model.prompts) == 3, "each of the project's passages was read once"
    assert _pending(HERE) == [] and len(_pending(HERE, rebuild=True)) == 3
    assert [r[1] for r in _pending(THERE)] == [theirs.document_id], "the other project's chunks wait unread"


def test_a_second_build_reads_nothing_and_calls_no_model(tmp_path):
    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew in a placeholder vessel.")
    assert _build(HERE, Reader({f"organism-{tag}": Named("Organism")})).chunks_processed == 1
    again = Reader({f"organism-{tag}": Named("Organism")})
    built = _build(HERE, again)
    assert (built.chunks_pending, built.batches_run, built.chunks_processed, again.prompts) == (0, 0, 0, [])


def test_a_batch_the_model_answers_unusably_is_split_and_left_for_the_next_build(tmp_path):
    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew.", f"The organism-{tag} was fed.",
           f"The organism-{tag} was harvested.")
    unusable = Reader({}, prose=True)
    built = _build(HERE, unusable)
    # Three chunks, halved: one, then two halved again into one and one.
    assert (built.batches_run, built.batches_split, built.batches_failed) == (1, 2, 3)
    assert (built.chunks_processed, built.chunks_left, len(unusable.prompts)) == (0, 3, 5)
    assert len(_pending(HERE)) == 3, "a failed batch leaves its chunks for the next build"
    built = _build(HERE, Reader({f"organism-{tag}": Named("Organism")}))
    assert (built.chunks_processed, built.entities_created, _pending(HERE)) == (3, 1, [])


def test_a_shared_document_is_built_once_and_serves_both_projects(tmp_path, two_projects):
    tag = _tag()
    words = f"The organism-{tag} grew on substrate-{tag} in a placeholder vessel."
    shared = _store(tmp_path, HERE, tag, words)
    assert _store(tmp_path, THERE, tag, words).status == "linked"
    model = Reader({f"organism-{tag}": Named("Organism"), f"substrate-{tag}": Named("Substrate")},
                   [Stated(f"organism-{tag}", "GROWN_ON", f"substrate-{tag}", f"organism-{tag} grew on substrate-{tag}")])
    assert _build(HERE, model).chunks_processed == 1
    assert _pending(THERE) == []
    later = Reader({})
    assert (_build(THERE, later).batches_run, later.prompts) == (0, [])
    for project_id in (HERE, THERE):
        listed = _entities(project_id)["entities"]
        assert [(e["name"], e["evidence_chunk_count"]) for e in listed] == [(f"organism-{tag}", 1),
                                                                            (f"substrate-{tag}", 1)]
        [edge] = _edges(project_id, f"substrate-{tag}")["relationships"]
        assert edge["document_id"] == shared.document_id


def test_a_build_stops_in_words_when_no_model_answers(tmp_path):
    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew.", f"The organism-{tag} was fed.",
           f"The organism-{tag} was harvested.")
    silent = Reader({}, fails=RuntimeError("a placeholder outage"))
    words = "No model of the index route answered: a placeholder outage."
    built = _build(HERE, silent, batch_size=1, stop=lambda: words if silent.prompts else None)
    assert (built.stopped, built.batches_run, len(silent.prompts)) == (words, 1, 1)
    assert (built.batches_failed, built.chunks_processed, built.chunks_left) == (1, 0, 3)
    assert len(_pending(HERE)) == 3, "the chunks the build had yet to read wait for the next one"


def test_the_kits_batch_step_is_the_one_this_build_calls(tmp_path, monkeypatch):
    assert graph._extract_with_recovery is extractor._extract_with_recovery
    step = inspect.signature(extractor._extract_with_recovery).parameters
    assert [(p.name, p.kind) for p in step.values()] == [
        ("batch", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("session_factory", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("llm", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("domain", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("stats", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("rate_limit_s", inspect.Parameter.KEYWORD_ONLY),
    ], "Sci RAG Kit 0.5.0's batch step: an upgrade that moves it fails here first (ADR-002's revisit condition)"
    assert [f.name for f in dataclasses.fields(extractor.ExtractionStats)] == [
        "chunks_processed", "batches_failed", "batches_split", "entities_created", "entities_updated",
        "relationships_created"]
    assert set(inspect.signature(extractor.extract_graph).parameters) == {
        "session_factory", "llm", "domain", "batch_size", "reprocess_all", "rate_limit_s", "max_chunks"
    }, "the kit's own build takes no document filter, which is why graph.py reads the project's chunks itself"

    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew.")
    seen = []

    async def step_recorded(batch, session_factory, llm, domain, stats, *, rate_limit_s):
        seen.append((list(batch), session_factory, llm, domain, stats, rate_limit_s))
        await extractor._extract_with_recovery(batch, session_factory, llm, domain, stats, rate_limit_s=rate_limit_s)

    monkeypatch.setattr(graph, "_extract_with_recovery", step_recorded)
    model = Reader({f"organism-{tag}": Named("Organism")})
    built = _build(HERE, model)
    [(batch, session_factory, llm, domain, stats, rate_limit_s)] = seen
    service = kit.service()
    assert [r[0] for r in batch] == [c.id for c in kit.document(batch[0][1], project_id=HERE)[1]]
    assert (session_factory, llm, domain, stats, rate_limit_s) == (service.session_factory, model, service.domain,
                                                                   built, 0)


# ── the reads, under the rule ──────────────────────────────────────────────


@pytest.fixture
def graphs(tmp_path, two_projects):
    """Two projects' graphs, built one after the other. The other project's
    passage names an organism, a substrate they share and a vessel of its
    own; this project's passages name an organism of their own and the
    substrate, and one of them writes the other's organism under another
    name, which this project's model reads as that organism."""
    tag = _tag()
    n = SimpleNamespace(
        here=f"organism-h{tag}", there=f"organism-t{tag}", shared=f"substrate-s{tag}", vessel=f"vessel-t{tag}",
        alias=f"moniker-t{tag}", here_says=f"described in this project's build {tag}",
        there_says=f"described in the other project's build {tag}",
    )
    n.there_quote = f"{n.there} grew on {n.shared}"
    n.here_quote = f"{n.here} grew on {n.shared}"
    n.alias_quote = f"{n.alias} grew on {n.shared}"
    n.alias_affects = f"{n.alias} grew on {n.shared} as well"
    n.theirs = _store(tmp_path, THERE, tag + "t", f"The {n.there} grew on {n.shared} in the {n.vessel}.",
                      "The placeholder vessel was cleaned afterwards.")
    n.mine = _store(tmp_path, HERE, tag + "h", f"The {n.here} grew on {n.shared} in a placeholder vessel.",
                    f"The {n.alias} grew on {n.shared} as well.", f"The {n.shared} was named once more.")
    _build(THERE, Reader(
        {n.there: Named("Organism", f"A placeholder organism {n.there_says}."),
         n.shared: Named("Substrate", f"A placeholder substrate {n.there_says}."),
         n.vessel: Named("Equipment", f"A placeholder vessel {n.there_says}.")},
        [Stated(n.there, "GROWN_ON", n.shared, n.there_quote)],
    ))
    _build(HERE, Reader(
        {n.here: Named("Organism", f"A placeholder organism {n.here_says}."),
         n.shared: Named("Substrate", f"A placeholder substrate {n.here_says}."),
         n.there: Named("Organism", f"A placeholder organism {n.here_says}.", surface=n.alias, aliases=(n.alias,))},
        [Stated(n.here, "GROWN_ON", n.shared, n.here_quote), Stated(n.there, "GROWN_ON", n.shared, n.alias_quote),
         Stated(n.shared, "AFFECTS", n.there, n.alias_affects)],
    ))
    return n


def test_an_entity_is_listed_where_the_projects_passages_name_it(graphs):
    n = graphs
    listed = _entities(HERE)
    assert "note" not in listed
    assert listed["entities"] == [
        {"name": n.here, "type": "Organism", "description": f"A placeholder organism {n.here_says}.",
         "evidence_chunk_count": 1},
        {"name": n.shared, "type": "Substrate", "description": None, "evidence_chunk_count": 3,
         "description_note": graph.DESCRIPTION_WITHHELD},
    ], "the other project's organism is absent; the shared substrate counts this project's passages alone"
    assert [e["name"] for e in _entities(HERE, "SUBSTRATE-S")["entities"]] == [n.shared], "a name matched case aside"
    assert [e["name"] for e in _entities(HERE, entity_type="Organism")["entities"]] == [n.here]
    assert [e["name"] for e in _entities(HERE, limit=1)["entities"]] == [n.here]
    nothing = _entities(HERE, entity_type="Equipment")
    assert nothing == {"entities": [], "note": "No entity of type Equipment is named in this project's passages."}
    assert _entities(HERE, "vessel", entity_type="Organism")["note"] == (
        'No entity of type Organism whose name holds "vessel" is named in this project\'s passages.')

    theirs = _entities(THERE)["entities"]
    assert [(e["name"], e["evidence_chunk_count"]) for e in theirs] == [(n.there, 1), (n.shared, 1), (n.vessel, 1)]
    by_name = {e["name"]: e for e in theirs}
    assert by_name[n.vessel]["description"] == f"A placeholder vessel {n.there_says}."
    # This project's model named the other's organism in a passage of its own,
    # so that organism is named in a document the other project does not hold.
    assert by_name[n.there]["description"] is None and by_name[n.there]["description_note"] == graph.DESCRIPTION_WITHHELD


def test_an_alias_finds_nothing_under_a_projects_scope(graphs):
    n = graphs

    async def aliases():
        async with kit.service().session_factory() as session:
            return await session.scalar(select(KgEntity.aliases).where(KgEntity.name == n.there))

    assert db.run(aliases()) == [n.alias], "the kit holds the other name as the organism's alias"
    found = _entities(HERE, n.alias)
    assert found["entities"] == [] and n.alias in found["note"]
    assert _edges(HERE, n.alias)["found"] is False
    assert _entities(THERE, n.alias)["entities"] == [] and _edges(THERE, n.alias)["found"] is False


def test_an_edge_is_listed_with_its_passage_where_the_project_holds_its_evidence(graphs):
    n = graphs
    mine = _edges(HERE, n.shared)
    assert (mine["entity"], mine["found"], mine["type"], "note" in mine) == (n.shared, True, "Substrate", False)
    [edge] = mine["relationships"]
    assert edge["statement"] == f"{n.here} GROWN_ON {n.shared}" and edge["evidence"] == n.here_quote
    assert edge["document_id"] == n.mine.document_id and edge["confidence"] == 1.0
    assert n.here_quote in _passage(n.mine.document_id, edge["passage_id"])
    chunk_ids = {c.id: c.chunk_index for c in kit.document(n.mine.document_id, project_id=HERE)[1]}
    assert edge["passage_id"] == kit.passage_id(chunk_ids[edge["chunk_id"]])
    # The two edges this project's passage states of the other's organism,
    # written there under another name, are absent, one from each end: that
    # organism is the other project's.
    assert _edges(HERE, n.here)["relationships"] == [edge]

    async def stated_here():
        async with kit.service().session_factory() as session:
            return (await session.execute(select(KgRelationship.relation_type).join(
                Chunk, Chunk.id == KgRelationship.chunk_id).where(Chunk.document_id == n.mine.document_id)
                .order_by(KgRelationship.relation_type))).scalars().all()

    assert db.run(stated_here()) == ["AFFECTS", "GROWN_ON", "GROWN_ON"], "the kit holds all three"

    [theirs] = _edges(THERE, n.shared)["relationships"]
    assert theirs["statement"] == f"{n.there} GROWN_ON {n.shared}" and theirs["evidence"] == n.there_quote
    assert theirs["document_id"] == n.theirs.document_id
    assert n.there_quote in _passage(n.theirs.document_id, theirs["passage_id"], THERE)
    assert _edges(THERE, n.there)["relationships"] == [theirs]


def test_an_entity_the_project_does_not_name_is_not_found_in_words(graphs):
    n = graphs
    for project_id, other in ((HERE, n.there), (HERE, n.vessel), (THERE, n.here), (HERE, f"no-such-{_tag()}")):
        missing = _edges(project_id, other)
        assert missing == {"entity": other, "found": False,
                           "hint": f"No entity named in this project's passages is called \"{other}\": "
                                   "search_entities lists the names they hold."}


def test_neither_project_reads_the_others_entities_edges_or_descriptions(graphs):
    n = graphs

    def everything(project_id: str) -> str:
        listed = _entities(project_id)
        read = [listed] + [_edges(project_id, e["name"]) for e in listed["entities"]]
        return json.dumps([read, _counts(project_id), kit.stats(project_id)])

    mine, theirs = everything(HERE), everything(THERE)
    for word in (n.here, n.shared, n.here_says, n.here_quote, n.mine.document_id):
        assert word in mine, word
    for word in (n.there, n.vessel, n.alias, n.there_says, n.there_quote, n.alias_quote, n.alias_affects,
                 n.theirs.document_id):
        assert word not in mine, word
    for word in (n.there, n.shared, n.vessel, n.there_says, n.there_quote, n.theirs.document_id):
        assert word in theirs, word
    for word in (n.here, n.alias, n.here_says, n.here_quote, n.alias_quote, n.alias_affects, n.mine.document_id):
        assert word not in theirs, word

    async def free(project_id: str) -> dict:
        with projects.using(project_id):
            return await kit.service("free").search_entities("")

    assert asyncio.run(free(HERE)) == _entities(HERE), "the MCP server's service reads as the service in process does"


def test_an_edges_quote_is_shown_where_its_words_stand_in_its_passage(tmp_path):
    tag = _tag()
    a, b = f"organism-{tag}", f"substrate-{tag}"
    stored = _store(tmp_path, HERE, tag, f"The {a} grew on {b} in a placeholder vessel.")
    _build(HERE, Reader({a: Named("Organism"), b: Named("Substrate")}, [
        Stated(a, "GROWN_ON", b, f"{a.upper()}  grew on\n{b}", at=a),
        Stated(a, "AFFECTS", b, "words the passage never says", at=a),
    ]))
    affects, grown = _edges(HERE, a)["relationships"]
    assert grown["statement"] == f"{a} GROWN_ON {b}" and grown["evidence"] == f"{a.upper()}  grew on\n{b}", (
        "a quote is compared as a name is: case and runs of other characters aside")
    assert "evidence_note" not in grown
    assert affects["statement"] == f"{a} AFFECTS {b}" and affects["evidence"] is None
    assert affects["evidence_note"] == graph.EVIDENCE_WITHHELD
    assert affects["document_id"] == grown["document_id"] == stored.document_id


def test_a_project_with_no_graph_is_told_how_to_build_one(tmp_path, two_projects):
    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew in a placeholder vessel.")
    for project_id in (HERE, THERE):  # one holds a passage no build has read; the other holds nothing
        words = graph.no_graph(project_id)
        assert f"pnpm lit:graph --project {project_id} --by <name>" in words
        assert _entities(project_id) == {"entities": [], "note": words}
        assert _edges(project_id, f"organism-{tag}") == {"entity": f"organism-{tag}", "found": False, "hint": words}
    assert _counts(HERE) == {"chunks": 1, "chunks_read": 0, "entities": 0, "relationships": 0, "entity_types": {},
                             "relation_types": {}}


def test_a_graph_a_build_has_read_in_part_says_so(tmp_path):
    tag = _tag()
    _store(tmp_path, HERE, tag, f"The organism-{tag} grew.", f"The organism-{tag} was fed.")
    _build(HERE, Reader({f"organism-{tag}": Named("Organism")}), limit=1)
    partly = (f"The concept graph covers 1 of this project's 2 passages: `pnpm lit:graph --project {HERE} --by "
              "<name>` reads the rest.")
    assert _entities(HERE)["note"] == partly and _edges(HERE, f"organism-{tag}")["note"] == partly


def test_stats_count_the_projects_graph(graphs):
    n = graphs
    for project_id, entities, types in ((HERE, 2, {"Organism": 1, "Substrate": 1}),
                                        (THERE, 3, {"Equipment": 1, "Organism": 1, "Substrate": 1})):
        counts = kit.stats(project_id)
        assert (counts["entities"], counts["relationships"], counts["communities"]) == (entities, 1, 0), project_id
        shape = _counts(project_id)
        assert (shape["entities"], shape["entity_types"], shape["relation_types"]) == (entities, types,
                                                                                     {"GROWN_ON": 1})
        assert shape["chunks"] == shape["chunks_read"] == counts["chunks"]
    assert kit.stats(HERE)["chunks"] == n.mine.chunks


def test_the_fingerprint_counts_the_projects_corpus_and_its_graph(graphs):
    n = graphs
    chunks = kit.document(n.mine.document_id, project_id=HERE)[1]
    printed = db.run(kit.fingerprint(HERE))
    assert {k: printed[k] for k in ("project", "documents", "chunks", "tokens", "entities", "relationships",
                                    "communities")} == {
        "project": HERE, "documents": 1, "chunks": len(chunks), "tokens": sum(c.token_count for c in chunks),
        "entities": 2, "relationships": 1, "communities": 0}
    assert printed["embedding_versions"] == sorted({c.embedding_version for c in chunks})
    assert printed["latest_ingested_at"] and printed["graph"] == _counts(HERE)

    async def stamped():
        async with kit.service().session_factory() as session:
            return (await session.execute(select(Chunk.graph_extracted_at).where(
                Chunk.document_id == n.theirs.document_id))).scalars().all()

    assert all(db.run(stamped())), "the other project's build stamped its own chunks"
    assert db.run(kit.fingerprint(THERE))["documents"] == 1
