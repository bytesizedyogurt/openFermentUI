"""Regenerate the offline demo's fixtures as a set (OF-BLD-012 §8.1).

    pnpm demo:fixtures            # offline: the decisions, the export set and the smoke overlay
    pnpm demo:fixtures --real     # + fetch B5's real JATS and save one real model response
    python -m openferment_core.demo --prototype   # the prototype's fixtures (OF-BLD-014 E.2)

The three demo fixtures — the JATS, the saved model response, the decisions
— only make sense together: the response is anchored against that text, and
the decisions are keyed by the content ids the anchoring produced. Replacing
one by hand breaks the other two (test_demo says so), so this rebuilds them
in order, through the real code paths: fixture-mode fetch and extract into a
scratch directory, then `biorepo.write` for each decision.

`--real` first saves the real B5 JATS from Europe PMC and then, with
ANTHROPIC_API_KEY in core/.env, runs one extraction over it (one call, or
more when a response is cut off and the paper is split) and saves the
response with `extract --save-fixture`'s shape, beside what anchoring gave
for it then (`anchoredAtSave`), which test_demo holds every replay to. It
spends what one extraction of B5 costs, and prints it. Without `--real`,
whatever JATS and response are saved are used as they are.

The decisions follow the saved response (OF-BLD-014 §1.5). Over the
hand-written stand-in they demonstrate the review: the titre row promoted to
gold and corrected, the same row rejected as a colony time, and the curated
r-B5-3 accepted. Over a real response, a response whose usage names the
model that answered, they are the accept of r-B5-3 alone: the real
candidates stay undecided for a person in Guild, since two demonstration
decisions over them would record decisions nobody made.

Two fixtures are rebuilt from the structural document and the same two
hand-written raw candidates every time, regardless of `--real`: the smoke
overlay (tests/fixtures/overlay-smoke.json), which the browser tests serve as
the service's overlay, and the export set (tests/fixtures/export/), whose
decisions land all four ways a decision can and which `pnpm test:export`
exports.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

CORE = Path(__file__).parent.parent
FIXTURES = CORE / "tests" / "fixtures"
DEMO = FIXTURES / "demo"
EXPORT = FIXTURES / "export"
PROTOTYPE = FIXTURES / "prototype"
B5 = {"id": "B5", "pmcid": "PMC8471596"}
AT = "2026-09-15T09:00:00Z"
# The key, in a saved real response, of what anchoring gave when it was saved.
ANCHORED_AT_SAVE = "anchoredAtSave"

# The raw candidates the smoke overlay is built from — the same two the demo
# response carries: a titre the seed has no B5 record for, and the same row
# read as a colony time.
SMOKE_RAWS = [
    {
        "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
        "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
    },
    {
        "sectionId": "t1", "field": "time_to_colony", "value": 7, "unit": "d",
        "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.55,
    },
]


@contextmanager
def _scratch() -> Iterator[Path]:
    path = Path(tempfile.mkdtemp(prefix="of-demo-fixtures-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def response_is_real(fixtures: Path) -> bool:
    """Whether the saved response for B5 came from a model: a real one names
    the model that answered in its usage, and the hand-written stand-in names
    none (models.Usage)."""
    from .models import Usage

    saved = json.loads((fixtures / "extract" / "B5.json").read_text(encoding="utf-8"))
    return bool(Usage.model_validate(saved.get("usage") or {}).models)


@contextmanager
def _pointed_at(scratch: Path, fixtures: Path) -> Iterator[None]:
    """Redirect the service's directories for this process, the way the demo
    script does with the environment — but after import, so by attribute —
    and put every one back afterwards, OPENFERMENT_FIXTURES included."""
    from . import biorepo, extract, intake

    moved = {
        (intake, "DATA_DIR"): scratch,
        (intake, "FULLTEXT_DIR"): scratch / "fulltext",
        (intake, "FIXTURE_ROOT"): fixtures,
        (intake, "FIXTURE_DIR"): fixtures / "jats",
        (extract, "CANDIDATES_DIR"): scratch / "candidates",
        (extract, "FIXTURE_DIR"): fixtures / "extract",
        (biorepo, "PATH"): scratch / "biorepo.json",
    }
    before = {key: getattr(*key) for key in moved}
    env = os.environ.get("OPENFERMENT_FIXTURES")
    try:
        for (module, name), value in moved.items():
            setattr(module, name, value)
        yield
    finally:
        for (module, name), value in before.items():
            setattr(module, name, value)
        if env is None:
            os.environ.pop("OPENFERMENT_FIXTURES", None)
        else:
            os.environ["OPENFERMENT_FIXTURES"] = env


def record_anchoring(path: Path, result) -> None:
    """Write into a saved response what anchoring gave for it: the candidate
    ids it kept and how many it rejected. A replay is held to these, so a
    change to anchoring that moves the demo shows as a failing test."""
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved[ANCHORED_AT_SAVE] = {"candidates": [c.id for c in result.candidates], "rejected": result.rejected}
    path.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def real_note(pmcid: str) -> str:
    """The comment a saved paper carries. It names the command in words: two
    hyphens may not appear inside an XML comment, and the flag spelled with
    them broke the saved file (live test, 2026-10-16)."""
    return (
        "<!--\n  pnpm demo:fixtures, real mode: Saved from Europe PMC, "
        f"{pmcid} (B5), for the offline demo (OF-BLD-012 §8.1).\n"
        "  The licence element inside says under what terms.\n-->\n"
    )


def with_note(xml: str, note: str) -> str:
    """The JATS with `note` (a comment) after the XML declaration and before
    everything else. The declaration ends at its own `?>`, never at the first
    newline: Europe PMC sends it and <article> on one line (live test,
    2026-10-16), and a comment after the root element would not parse."""
    if not xml.startswith("<?xml"):
        return note + xml
    end = xml.index("?>") + 2
    return xml[:end] + "\n" + note + xml[end:].lstrip("\r\n")


def save_real(scratch: Path) -> None:
    """The real JATS from Europe PMC, and one real model response over it."""
    from . import extract, intake

    os.environ.pop("OPENFERMENT_FIXTURES", None)
    xml = intake.fetch_fulltext(B5["pmcid"])
    note = real_note(B5["pmcid"])
    (DEMO / "jats").mkdir(parents=True, exist_ok=True)
    (DEMO / "jats" / f"{B5['pmcid']}.xml").write_text(with_note(xml, note), encoding="utf-8")
    print(f"saved {DEMO / 'jats' / (B5['pmcid'] + '.xml')}")

    # Fetch in fixture mode from what was just saved, then one real call.
    os.environ["OPENFERMENT_FIXTURES"] = "1"
    fetched = intake.fetch_paper(B5)
    assert fetched.status == "complete", fetched.reason
    os.environ.pop("OPENFERMENT_FIXTURES", None)
    extract.SAVE_RESPONSES = True
    result = extract.extract_paper("B5", force=True)
    record_anchoring(extract.FIXTURE_DIR / "B5.json", result)
    print(
        f"saved {extract.FIXTURE_DIR / 'B5.json'}: {len(result.candidates)} anchored, "
        f"{result.rejected} rejected, ${result.usage.costUsd:.4f}"
    )


def rebuild_decisions(fixtures: Path = DEMO, out: Path | None = None, note: str | None = None) -> list[str]:
    """biorepo.json for one fixture set, made through biorepo.write against
    its saved JATS and response, and written to `out` (the set's own
    biorepo.json unless told otherwise). Returns the decided ids."""
    from . import biorepo, extract, intake
    from .models import Quantity, ReviewDecision

    out = out or fixtures / "biorepo.json"
    real = response_is_real(fixtures)
    with _scratch() as scratch, _pointed_at(scratch, fixtures):
        os.environ["OPENFERMENT_FIXTURES"] = "1"
        fetched = intake.fetch_paper(B5, force=True)
        assert fetched.status == "complete", fetched.reason
        result = extract.extract_paper("B5", force=True)
        if real and not result.candidates:
            sys.exit(
                f"the saved real response anchors no candidate against the saved JATS ({result.rejected} rejected): "
                "a demo with nothing to decide shows nothing. Save another with pnpm demo:fixtures --real"
            )
        if real:
            # §1.5 — a real response is left for a person to decide. The one
            # decision is the accept of a curated record, which decides no
            # candidate and keeps Guild and Witness opening on something
            # reviewed.
            biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="sean",
                                         recordId="r-B5-3", at=AT))
        else:
            if len(result.candidates) < 2:
                sys.exit(
                    f"the saved response anchors {len(result.candidates)} candidate(s) against the saved JATS; "
                    "the three decisions below need two — nothing to decide on"
                )
            # One of each kind of decision, so `pnpm test:export` has all three merge
            # paths to check (OF-BLD-012.1 F4) and the demo opens on a corpus that has
            # actually been reviewed rather than only rejected:
            #
            #   1. the titre row promoted to gold AND corrected into canonical units —
            #      the paper wrote mg/L, the corpus records g/L, and both the gold
            #      value and the correction have to anchor in that same sentence
            #   2. the same row read as a colony time, rejected — Witness's false
            #      positive
            #   3. a curated B5 record accepted as it stands
            first, second = result.candidates[0], result.candidates[1]
            biorepo.write(ReviewDecision(
                status="verified", provenance="gold", reviewer="sean", recordId=first.id, at=AT,
                gold=Quantity(value=first.value, unit=first.unit),
                corrected=Quantity(value=float(first.value) / 1000.0, unit="g L\u207b\u00b9"),
            ))
            biorepo.write(ReviewDecision(
                status="rejected", provenance="unverified", reviewer="sean", recordId=second.id, at=AT,
                rejectReason="wrong span — a row of titres read as a colony time",
            ))
            biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="sean",
                                         recordId="r-B5-3", at=AT))
        raw = json.loads(biorepo.PATH.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"_note": note or (DEMO_NOTE_REAL if real else DEMO_NOTE), **raw}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ids = list(raw["decisions"])
    print(f"wrote {out}: {ids}")
    return ids


DEMO_NOTE = (
    "pnpm demo:offline (OF-BLD-012 §8.1): a biorepo.json with three decisions, copied "
    "into the demo's scratch data directory at start so Guild and Witness open with "
    "something decided. Written by `pnpm demo:fixtures` through biorepo.write against "
    "the demo fixtures — the titre row promoted to gold and corrected into canonical "
    "units, the same row rejected where it was read as a colony time (Witness's false "
    "positive), and one accept of a curated B5 record. Not the committed "
    "core/data/biorepo.json, which the demo never touches."
)
DEMO_NOTE_REAL = (
    "pnpm demo:offline (OF-BLD-012 §8.1, OF-BLD-014 §1.5): a biorepo.json with one decision, "
    "copied into the demo's scratch data directory at start. Written by `pnpm demo:fixtures` "
    "through biorepo.write against the demo fixtures, which hold B5's real text and a real "
    "model response: the accept of the curated r-B5-3. The real candidates are left "
    "undecided, for a person to decide in Guild. Not the committed core/data/biorepo.json, "
    "which the demo never touches."
)
EXPORT_NOTE = (
    "pnpm test:export (OF-BLD-012.1 F4, OF-BLD-014 §1.5): a biorepo.json whose decisions land "
    "all four ways a decision can — the titre row promoted to gold and corrected into "
    "canonical units, the same row rejected where it was read as a colony time, and one "
    "accept of a curated B5 record — over the structural stand-in document and two "
    "hand-written candidates, whatever the demo set holds. Written by `pnpm demo:fixtures` "
    "through biorepo.write. Not the committed core/data/biorepo.json, which the demo never "
    "touches."
)


def rebuild_export_set(out: Path | None = None) -> list[str]:
    """The decision set `pnpm test:export` exports (OF-BLD-014 §1.5): the
    hand-written stand-in, decided all four ways, rebuilt in a scratch
    fixture root from the structural document and SMOKE_RAWS."""
    with _scratch() as root:
        (root / "jats").mkdir()
        shutil.copy2(FIXTURES / "jats" / "structural.xml", root / "jats" / f"{B5['pmcid']}.xml")
        (root / "extract").mkdir()
        (root / "extract" / "B5.json").write_text(
            json.dumps({"_note": "hand-written stand-in (demo.SMOKE_RAWS)", "raw": {"candidates": SMOKE_RAWS},
                        "usage": {}}),
            encoding="utf-8",
        )
        return rebuild_decisions(root, out=out or EXPORT / "biorepo.json", note=EXPORT_NOTE)


def rebuild_smoke_overlay() -> None:
    """The overlay the browser tests are served: the structural document as
    B5's text, the two raw candidates through the real anchoring, the run
    from the real matcher."""
    from .corpus import load_corpus
    from .intake import split_jats
    from .validate import anchor_all
    from .witness import match_run

    path = FIXTURES / "overlay-smoke.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    structural = (FIXTURES / "jats" / "structural.xml").read_text(encoding="utf-8")
    fetched = split_jats(structural, paper_id="B5", pmcid="structural")
    assert fetched.status == "complete", fetched.reason
    sections = [s.model_dump() for s in fetched.sections]
    anchored = anchor_all(SMOKE_RAWS, sections, paper_id="B5")
    assert anchored.rejected == 0, anchored.details
    seed = [r for r in load_corpus().records if r["paperId"] == "B5"]
    run = match_run(anchored.accepted, seed, papers={"B5"}, dropped=anchored.dropped)
    out = {
        "_note": current["_note"],
        "papers": {
            "B5": {
                "ingest": "complete",
                "textSource": "full-text",
                "sections": sections,
                "license": fetched.license.href if fetched.license else None,
                # Fixed, so regenerating an unchanged set leaves the tree clean.
                "fetchedAt": AT,
                "reason": None,
            }
        },
        "records": {},
        "candidates": [c.model_dump(exclude_none=True) for c in anchored.accepted],
        "runs": [run.model_dump(exclude_none=True)],
    }
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}: {[c.id for c in anchored.accepted]}")


# ── the prototype's fixtures (OF-BLD-014 E.2) ──────────────────────────
#
# Generated by code, through the real code paths, and served by the smoke
# double in the service's place. Each phase adds its fixtures here; test_demo
# fails when a committed file no longer matches what this writes.
#
# §3.2: one artifact made by a test tool, and its replay. The tool counts its
# inputs and lists their names; it exists so the store, the page and the
# replay button have something real to show offline, and it computes no
# process number.
PROTOTYPE_TOOL = "prototype_tally"
PROTOTYPE_TOOL_VERSION = "prototype-1"
PROTOTYPE_NOTE = "TEST FIXTURE: made by `python -m openferment_core.demo --prototype` with a test tool."


def _tally(inputs, seed):
    return {
        "label": "Inputs named in this basis",
        "value": len(inputs),
        "unit": "inputs",
        "names": [i.name for i in inputs],
    }


def register_prototype_tools() -> None:
    from . import artifacts

    artifacts.register(PROTOTYPE_TOOL, PROTOTYPE_TOOL_VERSION, _tally)


def prototype_artifact():
    """The fixture artifact, computed by the real `artifacts.compute` and kept
    nowhere; its date and duration are fixed so the file is the same on every
    run."""
    from . import artifacts
    from .models import BasisInput, BasisSource

    register_prototype_tools()
    inputs = [
        BasisInput(
            name="record read",
            value="B5 titre",
            unit="",
            source=BasisSource(kind="record", id="r-B5-3"),
        ),
        BasisInput(
            name="how the inputs are counted",
            value="one per input",
            unit="",
            source=BasisSource(kind="convention", note=PROTOTYPE_NOTE),
        ),
    ]
    art = artifacts.compute(
        PROTOTYPE_TOOL, inputs, records_by_id={"r-B5-3": {"provenance": "curated"}}, keep=False
    )
    return art.model_copy(update={"createdAt": AT, "durationMs": 0})


# OF-BLD-015 §7.4: one proposal a model made at a gate, through the real
# store in a scratch directory, so Home's card and the smoke have one to
# press. The time and the id are fixed, so the file is the same every run.
PROPOSAL_ID = "pr-standin000001"


def prototype_proposals() -> dict[str, Any]:
    from . import audit, proposals
    from .tools import gates

    with _scratch() as scratch:
        saved = (proposals.PATH, audit.PATH)
        proposals.PATH, audit.PATH = Path(scratch) / "proposals.json", Path(scratch) / "audit.jsonl"
        try:
            made = proposals.propose(module="runbooks", action="lock", gate=gates.BY_ID["lock"],
                                     title="Runbooks: lock a runbook's predictions before a run — rb-brazzein",
                                     why="the draft's predictions are in hand and a run is planned", by="stand-in model",
                                     target="rb-brazzein", note="lock before the pilot run so the ledger can score it",
                                     ask_id="ask-standin", effort="medium")
        finally:
            proposals.PATH, audit.PATH = saved
    made = made.model_copy(update={"id": PROPOSAL_ID, "at": AT})
    return {"proposals.json": [made.model_dump(mode="json")]}


def rebuild_prototype(out: Path = PROTOTYPE) -> list[Path]:
    from . import artifacts

    art = prototype_artifact()
    overlay = json.loads((FIXTURES / "overlay-smoke.json").read_text(encoding="utf-8"))
    draft_stream, draft_artifacts = prototype_draft_stream(overlay)
    replay = artifacts.ReplayResult(
        artifactId=art.id, identical=True, storedHash=art.outputHash, replayedHash=art.outputHash, durationMs=0
    )
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, value in (
        ("artifacts.json", [art.model_dump(mode="json"), *(a.model_dump(mode="json") for a in draft_artifacts)]),
        ("ask-draft-stream.jsonl", draft_stream),
        ("artifact-replay.json", replay.model_dump(mode="json")),
        *prototype_rag().items(),
        *prototype_geneos().items(),
        *prototype_fermos().items(),
        *prototype_proforma().items(),
        *prototype_proposals().items(),
    ):
        path = out / name
        if name.endswith(".jsonl"):
            # One event a line, as the stream sends them; the note leads.
            # §10.3: the note leads, with when the run was recorded and that a
            # scripted stand-in stood in for the model; a replay shows both.
            lines = [{"_fixture": PROTOTYPE_NOTE, "recordedAt": AT, "standIn": True}, *value]
            path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
        else:
            wrapped = {"_fixture": PROTOTYPE_NOTE, "response": value}
            path.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
        print(f"wrote {path}")
    return written


# §4.4: passage search over the structural stand-in paper the smoke overlay
# already serves as B5, through the real cutter, the bm25 lane and the
# scorecard. Timings are zeroed and the date fixed, so the files are the same
# on every run.
RAG_QUESTION = "placeholder rows in the table"


def prototype_rag() -> dict[str, Any]:
    from . import intake as _intake
    from . import passages, rageval, retrieve
    from .models import FetchedSection, FetchResult, RagSearchResponse

    overlay = json.loads((FIXTURES / "overlay-smoke.json").read_text(encoding="utf-8"))
    b5 = overlay["papers"]["B5"]
    saved = (_intake.DATA_DIR, _intake.FULLTEXT_DIR, passages._LOADED, passages._papers_meta)
    # Generated with no key, so the paid lanes say they need one whatever this
    # machine holds, and nothing is ever spent making a fixture.
    key = os.environ.pop("ANTHROPIC_API_KEY", None)
    with _scratch() as scratch:
        try:
            _intake.DATA_DIR = scratch
            _intake.FULLTEXT_DIR = scratch / "fulltext"
            _intake.FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)
            passages._LOADED = None
            passages._papers_meta = lambda: {"B5": {"title": "A structural stand-in article", "year": 2026}}
            fetched = FetchResult(
                paperId="B5", pmcid=B5["pmcid"], status="complete", fetchedAt=b5["fetchedAt"],
                sections=[FetchedSection(**x) for x in b5["sections"]],
            )
            (_intake.FULLTEXT_DIR / "B5.json").write_text(fetched.model_dump_json(), encoding="utf-8")
            passages.build()
            status = passages.status()
            # The stand-in is filed under B5, a casein paper id; the fixture
            # is the search with archived programs shown (OF-BLD-016 §2.3).
            detail = retrieve.search_detail(RAG_QUESTION, k=8, lane="bm25", include_archived=True)
            search = RagSearchResponse(lane=detail.lane, hits=detail.hits, phrasings=[], unverifiedSentences=0, costUsd=0.0)
            items = [dict(raw, id=f"stand-in-{n}", paperId="B5", source="candidate") for n, raw in enumerate(SMOKE_RAWS)]
            k, counts = rageval.build_k(items, passages.read_index(), {"titer_secreted": "Secreted titer", "time_to_colony": "Time to colony"}, {})
            infos = [
                rageval.RagSetInfo(name="K", questions=len(k), note=f"known items: {counts['records']} records and {counts['candidates']} anchored candidates whose quote sits in a passage (stand-in)"),
                rageval.RagSetInfo(name="S", questions=0, note="written questions: none in the stand-in"),
                rageval.RagSetInfo(name="F", questions=0, note="flows: none in the stand-in"),
            ]
            report = rageval.evaluate(sets={"K": k, "S": [], "F": []}, infos=infos, lanes=retrieve.LANES)
            stream = prototype_stream(overlay)
        finally:
            _intake.DATA_DIR, _intake.FULLTEXT_DIR, passages._LOADED, passages._papers_meta = saved
            if key is not None:
                os.environ["ANTHROPIC_API_KEY"] = key
    report.date = AT
    for lane in report.lanes:
        for m in lane.sets.values():
            m.medianSeconds = 0.0
    return {
        "rag-status.json": status.model_dump(mode="json"),
        "rag-search.json": search.model_dump(mode="json"),
        "rag-report.json": report.model_dump(mode="json"),
        "ask-stream.jsonl": stream,
    }


# §5.3: one question through the real loop (postdoc_agent.ask), the model a
# scripted stand-in that searches the records, searches the papers, and
# answers with one claim citing the overlay's candidate and quoting B5's table
# row. Run inside prototype_rag's scratch, so `search_passages` reads the
# index built there. The usage is the stand-in's, fixed, and costs nothing.
STREAM_QUESTION = "What does the stand-in table report for placeholder A?"
STREAM_CANDIDATE = "cl1-B5-a07dd73c"
STREAM_QUOTE = "Placeholder A | 7 | mg L-1"


def _stand_in_converse(turns: list[Any]):
    from . import llm
    from .models import Usage

    def converse(**kw):
        turn = turns.pop(0)
        usage = Usage(models=[kw["model"]])
        if isinstance(turn, dict):
            return llm.Turn(content=[], toolCalls=[], data=turn, stopReason="end_turn", usage=usage, model=kw["model"])
        calls = [llm.ToolCall(id=f"stand-in-{len(turns)}-{i}", name=n, input=inp) for i, (n, inp) in enumerate(turn)]
        content = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
        return llm.Turn(content=content, toolCalls=calls, data=None, stopReason="tool_use", usage=usage, model=kw["model"])

    return converse


def _stream_pool(overlay: dict[str, Any]):
    from . import evidence_pool
    from .corpus import Corpus
    from .models import Candidate

    b5 = overlay["papers"]["B5"]
    # The stand-in corpus holds B5 and no record; the overlay's candidates
    # are everything a search of the pool can find.
    paper = {"id": "B5", "title": "A structural stand-in article", "year": 2026, "textSource": "full-text",
             "sections": [{"id": x["id"], "heading": x["heading"]} for x in b5["sections"]]}
    corpus = Corpus(papers=[paper], records=[], papers_by_id={"B5": paper}, records_by_id={},
                    _bm25=None, _order=[], _tokens={})  # type: ignore[arg-type]
    return evidence_pool.build(
        corpus,
        [Candidate.model_validate(c) for c in overlay["candidates"]],
        {},
        [{"id": "titer_secreted", "name": "Secreted titer"}, {"id": "time_to_colony", "name": "Time to colony"}],
        # B5's letter is casein's, an archived program (OF-BLD-016 §2.3): the
        # recordings run with archived programs shown, as the switch on.
        include_archived=True,
    )


def prototype_stream(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    from . import postdoc_agent, tools

    pool = _stream_pool(overlay)
    turns: list[Any] = [
        [("search_records", {"query": "", "field": "titer_secreted", "organism": "", "limit": 10})],
        [("search_passages", {"query": RAG_QUESTION, "k": 3})],
        {
            "claims": [{
                "id": "c1",
                "text": "The stand-in table reports a secreted titer for placeholder condition A.",
                "recordIds": [STREAM_CANDIDATE], "paperIds": [], "support": "direct",
                "passages": [{"passageId": "B5:t1:0", "quote": STREAM_QUOTE}], "evidenceIds": [],
            }],
            "gaps": ["The stand-in paper states no organism, so nothing here can be compared across hosts."],
            "declined": None,
        },
    ]
    events: list[dict[str, Any]] = []
    plan = postdoc_agent.ask(
        STREAM_QUESTION, converse=_stand_in_converse(turns), ctx=_seed_ctx(pool),
        clock=lambda: 0.0, on_step=lambda st: events.append({"event": "step", "data": st.model_dump(mode="json")}),
    )
    assert plan.claims and not plan.rejected, f"the stand-in plan no longer passes the validator: {plan.rejectionReasons}"
    events.append({"event": "plan", "data": plan.model_dump(mode="json")})
    return events


def _seed_ctx(pool: Any) -> tools.ToolContext:
    """A context whose coverage pass (OF-BLD-015 §7.1) sweeps the seed and
    the stand-in pool alone, so the recorded loop is the same on every
    machine. The stand-in sits under an archived program's letter, so the
    recordings run with the program switch on (OF-BLD-016 §2.3)."""
    from . import module_stores, tools

    return tools.ToolContext(pool_factory=lambda: pool, include_archived=True,
                             stores_factory=lambda: module_stores.Stores(module_stores.seed_sources(lambda: pool),
                                                                         include_archived=True))


# §9.4: a second recorded loop, in which the stand-in asks for a forecast and
# a price and drafts a runbook from them and from the overlay's candidate.
# The forecast is of the invented sample series treated as a STAND-IN
# deposition, the price is the stand-in Proforma run (prototype_proforma's
# evaluator), both computed by the real code in a scratch store; the
# artifacts are returned for artifacts.json so the double can serve them.
DRAFT_QUESTION = "Draft a runbook for the stand-in run."
DRAFT_DEPOSITION = "dep-standin"


def prototype_draft_stream(overlay: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Any]]:
    import tempfile
    from types import SimpleNamespace

    from . import artifacts, fermos, geneos, postdoc_agent, proforma, tools
    from . import intake as _intake
    from .models import FermosSeries, InputAssumption, ProformaRunRequest

    pool = _stream_pool(overlay)
    # The ceiling is the toy network's, a STAND-IN the tool refuses outside
    # fixtures; inside this recording alone it is allowed, labelled as an
    # assumption, so what it computes is demo (geneos.model_args).
    real_ceiling = geneos.ceiling
    saved = (_intake.DATA_DIR, proforma.call, proforma.yield_cap)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_call
            proforma.yield_cap = lambda: None
            geneos.ceiling = lambda model_id, product, substrate, **kw: real_ceiling(model_id, product, substrate, allow_toy=True, **kw)
            ceiling = geneos.ceiling(geneos.TOY, "phb", "glucose")
            fit = fermos.fit(DRAFT_DEPOSITION, [FermosSeries.model_validate(x) for x in fermos_sample_series()])
            fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
            rs = _standin_records()
            a = [InputAssumption(key=k, value=v, low=lo, high=hi, by="openFerment test fixture", at="2026-10-15", note=PROFORMA_STANDIN)
                 for k, v, lo, hi in (("recovery", 0.95, 0.9, 0.98), ("sugarPrice", 0.4, 0.3, 0.5), ("sugarFeed", 10000.0, 10000.0, 10000.0))]
            run = proforma.run(ProformaRunRequest(scenarioId=proforma.SCENARIO_ID, assumptions=a),
                               pool=SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}))
            draft = {"title": "The stand-in run, forecast and priced", "productId": "taq-dna-polymerase",
                     "strainId": "c-necator-h16",
                     "items": [
                         {"label": "Yield ceiling", "evidenceId": ceiling.evidence.id, "field": "", "recordIds": []},
                         {"label": "Final product", "evidenceId": fc.evidence.id, "field": "", "recordIds": []},
                         {"label": "Minimum selling price", "evidenceId": run.evidence.id, "field": "", "recordIds": []},
                         {"label": "Secreted titer", "evidenceId": "", "field": "titer_secreted", "recordIds": [STREAM_CANDIDATE]},
                     ],
                     "measures": [{"label": "Product at harvest", "unit": "g/L", "timepoint": "harvest", "itemLabel": "Final product"}]}
            turns: list[Any] = [
                [("search_records", {"query": "", "field": "titer_secreted", "organism": "", "limit": 10})],
                [("yield_ceiling", {"modelId": geneos.TOY, "product": "phb", "substrate": "glucose"})],
                [("growth_forecast", {"fitArtifactId": fit.kineticArtifactId})],
                [("selling_price", {"scenarioId": proforma.SCENARIO_ID})],
                [("draft_runbook", draft)],
                {"claims": [{"id": "c1", "text": "The stand-in table reports a secreted titer for placeholder condition A.",
                             "recordIds": [STREAM_CANDIDATE], "paperIds": [], "support": "direct", "passages": [], "evidenceIds": []}],
                 "gaps": [], "declined": None},
            ]
            events: list[dict[str, Any]] = []
            plan = postdoc_agent.ask(
                DRAFT_QUESTION, converse=_stand_in_converse(turns), ctx=_seed_ctx(pool),
                clock=lambda: 0.0, on_step=lambda st: events.append({"event": "step", "data": st.model_dump(mode="json")}),
            )
            assert plan.runbookDraft is not None and len(plan.runbookDraft.predictions) == 4, "the stand-in draft no longer assembles"
            for e in plan.evidence:
                e.basis.at = AT
            events.append({"event": "plan", "data": plan.model_dump(mode="json")})
            kept = [artifacts.get(i).model_copy(update={"createdAt": AT, "durationMs": 0})
                    for i in (ceiling.artifactId, fit.kineticArtifactId, fc.artifactId, run.artifactId)]
        finally:
            _intake.DATA_DIR, proforma.call, proforma.yield_cap = saved
            geneos.ceiling = real_ceiling
    return events, kept


# §6.4: geneOS's Model view over the toy network the worker builds, a
# STAND-IN, computed by the real worker and the real artifact code and kept
# nowhere. The shelf the double lists holds the toy, labelled, and the
# C. necator model as a fetched file not on this machine, so a strain page
# shows its card and says so. The double's view is of PHB alone; the yeast
# models stay out of it. Dates are fixed so the files are the same on every
# run.
GENEOS_TOY_NOTE = "STAND-IN toy network built in the geneOS worker (4 metabolites, 6 reactions), for tests and fixtures; not a published model"


def _fixed(result):
    if result.evidence is not None:
        result.evidence.basis.at = AT
    return result.model_dump(mode="json")


def prototype_geneos() -> dict[str, Any]:
    from . import geneos, geneos_models as shelf
    from .models import GeneosModelInfo

    c_necator = shelf.SHELF["RehMBEL1391"]
    models = [
        GeneosModelInfo(id="toy", name="Toy network (STAND-IN)", host=None, scope="central carbon",
                        route="SPLIT then PHAC, built in the worker", licence="test fixture", source=GENEOS_TOY_NOTE,
                        unavailable=None, feed="glucose", notes=[GENEOS_TOY_NOTE], product="phb", products=["phb"]),
        GeneosModelInfo(id=c_necator.id, name=c_necator.name, host=c_necator.host, scope=c_necator.scope,
                        route=c_necator.route, licence=c_necator.licence,
                        source=c_necator.fetched.source,
                        unavailable=f"{c_necator.id}'s file is not on this machine: run pnpm geneos:fetch",
                        feed=c_necator.feed, notes=list(c_necator.notes), product=c_necator.product,
                        products=list(c_necator.products)),
    ]
    subs = list(shelf.SUBSTRATES)
    return {
        "geneos-models.json": [m.model_dump(mode="json") for m in models],
        "geneos-ceiling.json": {s: _fixed(geneos.ceiling("toy", "phb", s, keep=False, allow_toy=True)) for s in subs},
        "geneos-frontier.json": {s: _fixed(geneos.frontier("toy", "phb", s, keep=False, allow_toy=True)) for s in subs},
        "geneos-mix.json": _fixed(geneos.mix("toy", "phb", "glucose", "xylose", keep=False, allow_toy=True)),
    }


# §7.4: fermOS's sample run. INVENTED: a logistic time course with a fixed
# scatter, written to src/data/fermosSample.json for the browser, and fitted
# and forecast here through the real code (inline, kept nowhere) for the
# smoke double. Not a measurement.
FERMOS_SAMPLE = CORE.parent / "src" / "data" / "fermosSample.json"
FERMOS_SAMPLE_NOTE = "SAMPLE: an invented time course, made to show what fermOS does with a run. Not a measurement."
_SHAPE = {"x0": 0.12, "mu": 0.3, "xmax": 9.0, "p0": 0.05, "alpha": 0.35, "beta": 0.015, "s0": 60.0, "gamma": 4.2, "delta": 0.04}


def fermos_sample_series() -> list[dict[str, Any]]:
    import math

    def at(t: float) -> tuple[float, float, float]:
        c = _SHAPE
        denom = c["x0"] + (c["xmax"] - c["x0"]) * math.exp(-c["mu"] * t)
        x = c["x0"] * c["xmax"] / denom
        integral = c["xmax"] * t + (c["xmax"] / c["mu"]) * math.log(denom / c["xmax"])
        return x, c["p0"] + c["alpha"] * (x - c["x0"]) + c["beta"] * integral, c["s0"] - c["gamma"] * (x - c["x0"]) - c["delta"] * integral

    def jitter(i: int, scale: float) -> float:
        u = math.sin(i * 12.9898 + 78.233) * 43758.5453
        return (u - math.floor(u) - 0.5) * 2 * scale

    hours = [i * 2.5 for i in range(14)]
    out = []
    for k, (role, label, scale) in enumerate((("biomass", "Dry cell weight (sample)", 0.15), ("product", "Polymer (sample)", 0.08),
                                             ("substrate", "Sugar (sample)", 0.6))):
        out.append({"measureId": f"sample-{role}", "label": label, "unit": "g L-1", "role": role, "points": [
            {"t": t, "value": round(max(0.0, at(t)[k] + jitter(i + 31 * (k + 1), scale)), 3), "entryId": f"sample-{role}-{i}", "confirmed": True}
            for i, t in enumerate(hours)]})
    return out


def prototype_fermos() -> dict[str, Any]:
    from . import fermos
    from .models import FermosSeries

    series = [FermosSeries.model_validate(s) for s in fermos_sample_series()]
    fit = fermos.fit("sample-run", series, sample=True)
    fc = fermos.forecast_run(fit_inline=fit.kinetic, sample=True)
    if fc.evidence is not None:
        fc.evidence.basis.at = AT
    return {"fermos-fit.json": fit.model_dump(mode="json"), "fermos-forecast.json": fc.model_dump(mode="json")}


# §8.4: Proforma's BioSTEAM scenario for the smoke double. The binding and
# the run go through the real code (proforma.bind, proforma.run, the artifact
# store in a scratch folder); the records are STAND-INs on a paper id no
# corpus holds, and BioSTEAM is replaced by a closed-form STAND-IN evaluator,
# so test:core needs no simulator. Not a price of anything.
PROFORMA_STANDIN = "STAND-IN for the browser tests: invented records and a closed-form evaluator in place of BioSTEAM"


def _standin_records() -> list[dict[str, Any]]:
    rows = [("pha_titre", "g L-1", (20.0, 45.0, 70.0)), ("pha_yield_substrate", "g g-1", (0.22, 0.3, 0.36)),
            ("pha_content_cdw", "% CDW", (65.0, 80.0)), ("pha_productivity", "g L-1 h-1", (0.6, 1.4, 2.0))]
    out = []
    for field, unit, values in rows:
        for n, v in enumerate(values):
            out.append({"id": f"standin-{field}-{n}", "paperId": "P999", "field": field, "value": v, "unit": unit,
                        "carbonSource": "glucose", "strainId": "c-necator-h16", "organismText": "STAND-IN organism",
                        "provenance": "unverified", "status": "unverified", "primary": True})
    return out


def _standin_call(op: str, args: dict[str, Any]) -> Any:
    import itertools

    from scipy.stats import qmc

    def evaluate(v: dict[str, float]) -> dict[str, Any]:
        if v["yield"] / v["content"] > 0.5:
            raise ValueError("carbon")
        lines = {"media": v["sugarPrice"] / v["yield"] / v["recovery"], "utilities": 0.3 / v["productivity"],
                 "labor": 0.1, "downstream": 2.0 / v["titre"], "other": 0.12, "capex": 4.0 / v["titre"] + 0.05}
        return {"pricePerKgPha": sum(lines.values()), "phaKgPerH": v["sugarFeed"] * v["yield"] * v["recovery"],
                "costLines": lines, "readBack": {"standIn": 1.0}}

    def attempt(v):
        try:
            return evaluate(v), None
        except ValueError as e:
            return None, {"reason": str(e), "detail": PROFORMA_STANDIN}

    def sample(spec, u):
        if spec["kind"] == "fixed":
            return spec["value"]
        lo, hi = spec["low"], spec["high"]
        if spec["kind"] == "uniform" or hi == lo:
            return lo + u * (hi - lo)
        c = (spec["mode"] - lo) / (hi - lo)
        return lo + (hi - lo) * ((u * c) ** 0.5 if u < c else 1 - ((1 - u) * (1 - c)) ** 0.5)

    if op == "evaluate":
        return evaluate(args["values"])
    if op == "grid":
        keys = list(args["axes"])
        cells = []
        for combo in itertools.product(*(args["axes"][k] for k in keys)):
            o, r = attempt({**args["base"], **dict(zip(keys, combo))})
            cells.append({"at": dict(zip(keys, combo)), "outputs": o, "infeasible": r})
        return {"axes": args["axes"], "base": args["base"], "cells": cells}
    keys = list(args["specs"])
    samples = []
    for row in qmc.LatinHypercube(d=len(keys), seed=args["seed"]).random(args["n"]):
        v = {**args["base"], **{k: sample(args["specs"][k], float(row[i])) for i, k in enumerate(keys)}}
        o, r = attempt(v)
        samples.append({"inputs": v, "outputs": o, "infeasible": r})
    return {"n": args["n"], "seed": args["seed"], "samples": samples}


def prototype_proforma() -> dict[str, Any]:
    import tempfile
    from types import SimpleNamespace

    from . import intake as _intake
    from . import proforma
    from .models import InputAssumption, ProformaRunRequest

    rs = _standin_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    info = proforma.scenario(pool=pool).model_dump(mode="json")
    a = [InputAssumption(key=k, value=v, low=lo, high=hi, by="openFerment test fixture", at="2026-10-15", note=PROFORMA_STANDIN)
         for k, v, lo, hi in (("recovery", 0.95, 0.9, 0.98), ("sugarPrice", 0.4, 0.3, 0.5), ("sugarFeed", 10000.0, 10000.0, 10000.0))]
    saved = (_intake.DATA_DIR, proforma.call, proforma.yield_cap)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_call
            proforma.yield_cap = lambda: None
            run = proforma.run(ProformaRunRequest(scenarioId=proforma.SCENARIO_ID, assumptions=a), pool=pool)
        finally:
            _intake.DATA_DIR, proforma.call, proforma.yield_cap = saved
    run.evidence.basis.at = AT
    return {"proforma-scenarios.json": [info], "proforma-run.json": run.model_dump(mode="json")}


def rebuild_fermos_sample(out: Path = FERMOS_SAMPLE) -> Path:
    out.write_text(json.dumps({"_sample": FERMOS_SAMPLE_NOTE, "series": fermos_sample_series()}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return out


# §6.1: the figure gallery's sample (/settings/figures). One record per
# provenance class, so every mark of the grammar is drawn; two limits; and a
# frontier. Invented numbers, said so in the file's first field and on the
# page; nothing here is a result.
FIGURE_SAMPLES = CORE.parent / "src" / "data" / "figureSamples.json"
SAMPLE_NOTE = "SAMPLE: invented values that show every mark of the figure grammar. Not a measurement, not a result."
SAMPLE_CLASSES = ["measured", "gold", "verified", "curated", "unverified", "computed", "user", "industry-estimate", "demo"]


def figure_samples() -> dict[str, Any]:
    records = []
    for n, prov in enumerate(SAMPLE_CLASSES):
        records.append({
            "id": f"sample-{n + 1}", "paperId": "sample", "sectionId": "sample", "quote": SAMPLE_NOTE,
            "field": "pha_yield_substrate", "value": round(0.12 + 0.05 * n, 3), "unit": "g g-1",
            "si": {"value": round(0.12 + 0.05 * n, 3), "unit": "g g-1"}, "confidence": 1,
            "status": "verified" if prov in ("verified", "gold") else "unverified",
            "provenance": "curated" if prov in ("verified", "gold") else prov,
            **({"gold": {"value": round(0.12 + 0.05 * n, 3), "unit": "g g-1"}} if prov == "gold" else {}),
            "organism": f"Sample organism {'AB'[n % 2]}", "carbonSource": "sample sugar",
            "isPrimary": True, "audit": [],
        })
    records.append({**records[3], "id": "sample-10", "value": 0.2, "si": {"value": 0.2, "unit": "g g-1"},
                    "isPrimary": False, "organism": "Sample organism B"})
    frontier = [{"growth": round(0.08 * i, 3), "product": round(0.6 * (1 - (i / 11) ** 1.6), 4)} for i in range(12)]
    return {
        "_sample": SAMPLE_NOTE,
        "strip": {"unit": "g g-1", "quantity": "PHB yield on substrate", "records": records,
                  "rules": [{"value": 0.48, "label": "sample core model"}, {"value": 0.59, "label": "sample genome-scale model"}]},
        "frontier": {"growthUnit": "h-1", "productUnit": "g g-1", "productLabel": "PHB yield on substrate",
                     "model": "a sample model", "points": frontier},
    }


def rebuild_figure_samples(out: Path = FIGURE_SAMPLES) -> Path:
    out.write_text(json.dumps(figure_samples(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return out


# §8.1: the fixtures that need BioSTEAM, which are the toy flowsheet's: one
# evaluation, a small grid and a seeded sample, made by the real Proforma
# worker. `pnpm test:sim` regenerates them and fails when they drift;
# `python -m openferment_core.demo --sim` rewrites the file.
SIM_FIXTURES = CORE / "tests" / "fixtures" / "sim" / "toy.json"
SIM_NOTE = "TEST FIXTURE: the toy flowsheet (a mixer and a splitter) through the real BioSTEAM worker; made by `python -m openferment_core.demo --sim`."


def sim_fixtures() -> dict[str, Any]:
    from . import proforma

    evaluate = proforma.call("evaluate", {"flowsheet": "toy", "values": {}})
    grid = proforma.call("grid", {"flowsheet": "toy", "axes": {"split": [0.2, 0.6], "ethanol": [40.0, 50.0]}, "base": {}})
    sample = proforma.call("montecarlo", {"flowsheet": "toy", "specs": {
        "split": {"kind": "uniform", "low": 0.1, "high": 0.9},
        "ethanol": {"kind": "triangular", "low": 40.0, "mode": 50.0, "high": 70.0}}, "n": 8, "seed": 3, "base": {}})
    return {"_fixture": SIM_NOTE, "evaluate": evaluate, "grid": grid, "montecarlo": sample}


def rebuild_sim_fixtures(out: Path = SIM_FIXTURES) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim_fixtures(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return out


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(CORE / ".env", override=False)
    if "--sim" in argv:
        rebuild_sim_fixtures()
        return 0
    if "--prototype" in argv:
        rebuild_prototype()
        rebuild_figure_samples()
        rebuild_fermos_sample()
        return 0
    if "--real" in argv:
        with _scratch() as scratch, _pointed_at(scratch, DEMO):
            save_real(scratch)
    rebuild_decisions(DEMO)
    rebuild_export_set()
    rebuild_smoke_overlay()
    print("\nRun `pnpm test:core` — test_demo and test_api_intake check the sets still fit the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
