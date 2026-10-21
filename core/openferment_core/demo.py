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
from types import SimpleNamespace
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


def rebuild_prototype(out: Path = PROTOTYPE, *, real_worker: bool | None = None) -> list[Path]:
    """Every prototype fixture. `real_worker` decides whether the vessel
    fixture's designs come from BioSTEAM (None: when the sim extra is
    installed); test:core passes False, so it never starts the worker."""
    from . import proforma

    # OF-BLD-019 §2.R: a run's basis says whether its diagram is drawn, from
    # whether this host has Graphviz. The STAND-IN draws none on any host, so
    # its runs say so, and the fixtures are the same wherever they are made.
    drawn_here = proforma.drawn_here
    proforma.drawn_here = lambda: False
    try:
        return _rebuild_prototype(out, real_worker)
    finally:
        proforma.drawn_here = drawn_here


def _rebuild_prototype(out: Path, real_worker: bool | None = None) -> list[Path]:
    from . import artifacts

    art = prototype_artifact()
    overlay = json.loads((FIXTURES / "overlay-smoke.json").read_text(encoding="utf-8"))
    draft_stream, draft_artifacts = prototype_draft_stream(overlay)
    # OF-BLD-019 §3.3: the yeast scenario's run is kept beside the others, so
    # the double reads it back by id as the service would (the scenario page
    # after a reload, Compare); it follows the PHA run, which tests take first.
    proforma_fixtures = prototype_proforma()
    run_artifacts = proforma_fixtures.pop(PROFORMA_RUN_ARTIFACTS)
    bridge, bridge_artifacts = prototype_fermos_bridge()
    simulate_fixtures, simulate_artifacts = prototype_fermos_simulate()
    replay = artifacts.ReplayResult(
        artifactId=art.id, identical=True, storedHash=art.outputHash, replayedHash=art.outputHash, durationMs=0
    )
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, value in (
        ("artifacts.json", [art.model_dump(mode="json"), *(a.model_dump(mode="json") for a in draft_artifacts),
                            *run_artifacts, *(a.model_dump(mode="json") for a in bridge_artifacts),
                            *(a.model_dump(mode="json") for a in simulate_artifacts)]),
        ("ask-draft-stream.jsonl", draft_stream),
        ("artifact-replay.json", replay.model_dump(mode="json")),
        *prototype_rag().items(),
        *prototype_geneos().items(),
        *prototype_fermos().items(),
        *bridge.items(),
        *simulate_fixtures.items(),
        *prototype_fermos_chemostat().items(),
        *proforma_fixtures.items(),
        *prototype_ceiling_check().items(),
        *prototype_pureos().items(),
        *prototype_thermo().items(),
        *prototype_propose().items(),
        *prototype_proposals().items(),
        *prototype_vessel(real_worker).items(),
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
    from .models import FermosSeries, ProformaRunRequest

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
            a = _standin_overrides(proforma.SCENARIO_ID, PHA_STANDIN_ASSUMED)
            run = proforma.run(ProformaRunRequest(scenarioId=proforma.SCENARIO_ID, overrides=a),
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


# OF-BLD-020 §3.3: fermOS → Simulate for the double. The families as the
# service lists them (the switch off and on); each family's parameter scope
# and binding over the stand-in yeast records (demo's Proforma pool, on a
# paper id no corpus holds) for ethanol on glucose, for every strain of the
# program and for CEN.PK113-7D; the binding with the values a person would
# type for what waits (STAND-INs, named as such, not a batch of anything);
# one batch_v1 simulation run by the real kinetics.py on those values, beside
# a STAND-IN Yeast9 ceiling, in a scratch store; and the simulations list
# that run leaves. Dates are fixed so the files are the same on every run.
SIM_STRAIN = "s-cerevisiae-cenpk113-7d"
SIM_PRODUCT, SIM_SUGAR = "ethanol", "glucose"
SIM_STANDIN = ("STAND-IN for the browser tests: a value typed for the fixture, not a parameter of any batch "
               "(OF-BLD-020 §3.3)")
# What the browser tests type for each parameter that waits on the stand-in
# pool for CEN.PK113-7D: a STAND-IN each, inside its spec's bounds.
SIM_TYPED = (("mu_max", 0.4), ("ks", 0.2), ("yxs", 0.1), ("alpha", 2.0), ("p_max", 90.0), ("x0", 0.2), ("p0", 0.0))


def prototype_fermos_simulate() -> tuple[dict[str, Any], list[Any]]:
    import tempfile
    from types import SimpleNamespace

    from . import artifacts, fermos, kinetics
    from . import intake as _intake
    from .models import Override, ParamResolveRequest, SimulationRequest

    rs = _standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}, hidden={})
    asks = {"": False, SIM_STRAIN: False}

    def ask_of(family: str, strain: str) -> dict[str, Any]:
        archived = kinetics.FAMILIES[family].program is not None
        return {"family": family, "strain": strain or None, "product": SIM_PRODUCT, "sugar": SIM_SUGAR,
                "startFrom": "records", "durationPreset": fermos.UNTIL_RUN_OUT_PRESET, "includeArchived": archived}

    def bound(req: SimulationRequest) -> dict[str, Any]:
        try:
            return {"status": 200, "body": fermos.bind(req, pool=pool).model_dump(mode="json")}
        except fermos.SimulationRefused as e:
            return {"status": 422, "body": {"detail": str(e)}}

    typed = [Override(scope=fermos.family_scope("batch_v1"), key=k, value=v, by="openFerment test fixture",
                      at="2026-10-21T04:00:00Z", note=SIM_STANDIN) for k, v in SIM_TYPED]
    saved = _intake.DATA_DIR
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            scopes: dict[str, Any] = {}
            binds: dict[str, Any] = {}
            with _PoolLoaded(pool):
                for family in kinetics.FAMILIES:
                    for strain in (asks if family == "batch_v1" else {"": False}):
                        a = ask_of(family, strain)
                        key = f"{family}|{strain}"
                        req = ParamResolveRequest(**{k: v for k, v in a.items() if k != "family"})
                        scopes[key] = _param_answer(fermos.family_scope(family), req)
                        binds[key] = bound(SimulationRequest(**a))
                sim_ask = ask_of("batch_v1", SIM_STRAIN)
                with_typed = bound(SimulationRequest(**sim_ask, overrides=typed))
                assert with_typed["status"] == 200 and with_typed["body"]["waiting"] == [], \
                    f"the stand-in values no longer cover what waits: {with_typed}"
                standin_ceiling(STANDIN_CEILING_MODEL, SIM_PRODUCT, SIM_SUGAR, STANDIN_CEILING_G_PER_G)
                request = SimulationRequest(**sim_ask, overrides=typed)
                result = fermos.simulate(request, by_pool=pool)
                result.basis.at = AT
                art = artifacts.get(result.artifactId).model_copy(update={"createdAt": AT, "durationMs": 0})
                listed = [x.model_copy(update={"createdAt": AT}).model_dump(mode="json") for x in fermos.simulations()]
        finally:
            _intake.DATA_DIR = saved
    families = {"off": [f.model_dump(mode="json") for f in fermos.families(False)],
                "on": [f.model_dump(mode="json") for f in fermos.families(True)]}
    return ({"fermos-families.json": families,
             "fermos-simulate.json": {"note": SIM_STANDIN, "scopes": scopes, "bind": binds,
                                      "typed": [o.model_dump(mode="json") for o in typed],
                                      "boundTyped": with_typed,
                                      "simulate": {"request": request.model_dump(mode="json"),
                                                   "body": result.model_dump(mode="json")},
                                      "simulations": listed}}, [art])


# OF-BLD-020 §3.R (finding 17): one chemostat_v1 simulation run by the real
# kinetics.py on values a person would type (STAND-INs, named as such, not a
# culture of anything), over an empty pool, in a scratch store: the smoke
# answers Simulate with it once to hold the end-state card to the steady
# state the service computed (its X, S, P and D·P). The double does not
# serve it; nothing else reads it.
CHEMO_TYPED = (("mu_max", 0.4), ("ks", 0.2), ("yxs", 0.15), ("alpha", 2.0), ("yps", 0.45), ("p_max", 90.0),
               ("dilution_rate", 0.1), ("feed_conc", 20.0), ("x0", 0.5), ("s0", 10.0), ("p0", 0.0),
               ("t_end", 400.0))


def prototype_fermos_chemostat() -> dict[str, Any]:
    import tempfile
    from types import SimpleNamespace

    from . import fermos
    from . import intake as _intake
    from .models import Override, SimulationRequest

    empty = SimpleNamespace(records=[], records_by_id={}, hidden={})
    typed = [Override(scope=fermos.family_scope("chemostat_v1"), key=k, value=v, by="openFerment test fixture",
                      at="2026-10-21T07:00:00Z", note=SIM_STANDIN) for k, v in CHEMO_TYPED]
    request = SimulationRequest(family="chemostat_v1", product=SIM_PRODUCT, sugar=SIM_SUGAR, overrides=typed)
    saved = _intake.DATA_DIR
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            with _PoolLoaded(empty):
                result = fermos.simulate(request, by_pool=empty)
        finally:
            _intake.DATA_DIR = saved
    result.basis.at = AT
    assert result.steadyState is not None and not result.steadyState.washout, "the stand-in no longer holds a culture"
    return {"fermos-chemostat.json": {"note": SIM_STANDIN, "request": request.model_dump(mode="json"),
                                      "body": result.model_dump(mode="json")}}


# OF-BLD-019 §5.1: a fermOS fit feeds the fermenter. The sample time course
# above (INVENTED) relabelled as a STAND-IN ethanol run on a deposition no
# browser holds, fitted and forecast through the real code in a scratch
# store; the forecast runs STANDIN_FORECAST_H hours, a setting of this
# fixture, so that its median sugar is spent. GET /api/fermos/fits for every
# flowsheet with nothing on file and with the two on file (each answered or
# refused in the service's words), and the yeast flowsheet bound with the
# forecast for every input it feeds (GET /api/proforma/bind?fits=). The two
# artifacts join artifacts.json so their links open.
BRIDGE_DEPOSITION = "dep-standin-ethanol"
STANDIN_FORECAST_H = 120.0
BRIDGE_LABELS = {"biomass": "Dry cell weight (STAND-IN)", "product": "Ethanol (STAND-IN)",
                 "substrate": "Glucose (STAND-IN)"}


def _bridge_fits() -> tuple[str, str]:
    """The bridge's STAND-IN fit and its forecast, kept in the current store
    (artifacts.folder()) through the real code: their ids, the fit's first."""
    from . import fermos
    from .models import FermosSeries

    series = [FermosSeries.model_validate({**x, "measureId": f"standin-{x['role']}", "label": BRIDGE_LABELS[x["role"]]})
              for x in fermos_sample_series()]
    fit = fermos.fit(BRIDGE_DEPOSITION, series)
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=STANDIN_FORECAST_H)
    return fit.kineticArtifactId, fc.artifactId


def _bridge_choices(fit_id: str, forecast_id: str) -> list[dict[str, str]]:
    """The fits the browser tests choose (OF-BLD-019 §5.R): the kinetic fit
    for the two inputs it feeds, and the forecast's productivity beside the
    fit's titre and yield, which the binding refuses in words."""
    return [{"titre": fit_id, "yield": fit_id}, {"titre": fit_id, "yield": fit_id, "productivity": forecast_id}]


def prototype_fermos_bridge() -> tuple[dict[str, Any], list[Any]]:
    import tempfile
    from types import SimpleNamespace

    from . import artifacts, proforma
    from . import intake as _intake
    from .flowsheets import shelf as _shelf
    from .models import Override, ParamResolveRequest

    rs = _standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})

    def listed() -> dict[str, Any]:
        out: dict[str, Any] = {}
        for fid in (*_shelf.SHELF, *_shelf.TEST_ONLY):
            try:
                # Newest first, as the service lists them; every one is dated AT.
                infos = sorted(proforma.fermos_fits(fid), key=lambda i: i.artifactId, reverse=True)
                out[fid] = {"status": 200, "body": [i.model_copy(update={"createdAt": AT}).model_dump(mode="json") for i in infos]}
            except proforma.ScenarioRefused as e:
                out[fid] = {"status": 422, "body": {"detail": str(e)}}
        return out

    saved = _intake.DATA_DIR
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            none = listed()
            fit_id, fc_id = _bridge_fits()
            on_file = listed()
            info = proforma.fit_info(artifacts.get(fc_id), proforma.ETHANOL)
            fits = {f.key: fc_id for f in info.feeds if not f.refused}
            assert set(fits) == set(proforma.FIT_KEYS), "the stand-in forecast no longer feeds every input"
            body = proforma.bind_flowsheet(proforma.ETHANOL, pool=pool, fits=fits).model_dump(mode="json")
            # §5.R: the other choices the browser tests make, each bound or
            # refused in the service's words.
            others = []
            for chosen in _bridge_choices(fit_id, fc_id):
                try:
                    others.append({"fits": chosen, "status": 200, "body": proforma.bind_flowsheet(
                        proforma.ETHANOL, pool=pool, fits=chosen).model_dump(mode="json")})
                except proforma.ScenarioRefused as e:
                    others.append({"fits": chosen, "status": 422, "body": {"detail": str(e)}})
            # OF-BLD-020 §2.2: the parameter panel's scope of sc-yeast-1 with
            # each of those choices, as GET /api/params/{scope}?fits= answers.
            scope = f"proforma:{proforma.YEAST_SCENARIO_ID}"
            with _PoolLoaded(pool):
                panel = [{"fits": chosen, **_param_answer(scope, ParamResolveRequest(fits=chosen))}
                         for chosen in (fits, *_bridge_choices(fit_id, fc_id))]
                # OF-BLD-020 §2.R: the forecast chosen for every input it
                # feeds, then titre typed by a person. The resolve binds as
                # the run binds and refuses in the run's words, which the
                # page shows as why Run waits (the double answers the
                # panel's resolve with this recording for those fits and
                # that key).
                key, value = PARAMS_TYPED_BESIDE_A_FIT
                typed = [*_standin_overrides(proforma.YEAST_SCENARIO_ID, YEAST_STANDIN_ASSUMED),
                         Override(scope=scope, key=key, value=value, by="openFerment test fixture", at=AT,
                                  note=PROFORMA_STANDIN)]
                resolves = [{"fits": fits, "keys": sorted(o.key for o in typed), **_resolve_answer(
                    scope, ParamResolveRequest(fits=fits, overrides=typed))}]
            kept = [artifacts.get(i).model_copy(update={"createdAt": AT, "durationMs": 0}) for i in (fit_id, fc_id)]
        finally:
            _intake.DATA_DIR = saved
    return ({"fermos-fits.json": {"none": none, "onFile": on_file},
             "proforma-bind-fits.json": {"flowsheet": proforma.ETHANOL, "fits": fits, "body": body, "others": others},
             "params-proforma-fits.json": {"scope": scope, "answers": panel, "resolves": resolves}}, kept)


# §8.4: Proforma's BioSTEAM scenario for the smoke double. The binding and
# the run go through the real code (proforma.bind, proforma.run, the artifact
# store in a scratch folder); the records are STAND-INs on a paper id no
# corpus holds, and BioSTEAM is replaced by a closed-form STAND-IN evaluator,
# so test:core needs no simulator. Not a price of anything.
PROFORMA_STANDIN = "STAND-IN for the browser tests: invented records and a closed-form evaluator in place of BioSTEAM"
# The economic inputs the PHA draft's stand-in runs take as a person's
# values (a STAND-IN, not a price of anything).
PHA_STANDIN_ASSUMED = (("recovery", 0.95, 0.9, 0.98), ("sugarPrice", 0.4, 0.3, 0.5), ("sugarFeed", 10000.0, 10000.0, 10000.0))


def _standin_overrides(scenario_id: str, rows) -> list[Any]:
    """The stand-in runs' values as the parameter panel sends them
    (OF-BLD-020 §2.2): each an Override of the scenario's scope, named."""
    from .models import Override

    return [Override(scope=f"proforma:{scenario_id}", key=k, value=v, low=lo, high=hi, by="openFerment test fixture",
                     at="2026-10-15", note=PROFORMA_STANDIN) for k, v, lo, hi in rows]


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

    # OF-BLD-019 §2.3: the glucose-to-ethanol flowsheet has a closed form of
    # its own; every other call is the PHA draft's, as before.
    flowsheet = args.get("flowsheet") or "pha_sugar_v0"
    # OF-BLD-020 §6.1: a vessel and a train, priced, answers as the ethanol
    # flowsheet's closed form does, under its own output names (the stand-in
    # reads no structure: it builds nothing).
    composite = flowsheet == "custom_train_v1"
    ethanol = flowsheet == "ethanol_glucose_v0" or composite

    def evaluate(v: dict[str, float]) -> dict[str, Any]:
        if composite:
            out = _standin_ethanol_evaluate(v)
            return {"pricePerKgProduct": out["pricePerKgEthanol"], "productKgPerH": out["ethanolKgPerH"],
                    "costLines": out["costLines"], "readBack": out["readBack"]}
        if ethanol:
            return _standin_ethanol_evaluate(v)
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
    if op == "reference":
        return _standin_reference(str(args["flowsheet"]))
    if op == "run":
        # OF-BLD-019 §2.1: the worker's whole run, composed of the three
        # below, with tables a closed form makes and labels as the stand-in.
        try:
            base_out, base_infeasible = evaluate(args["base"]), None
        except ValueError as e:
            base_out, base_infeasible = None, f"ValueError: {e}"
        grid = (_standin_call("grid", {"flowsheet": flowsheet, "axes": args["axes"], "base": args["base"]})
                if args.get("axes") else None)
        mc = _standin_call("montecarlo", {"flowsheet": flowsheet, "specs": args["specs"], "n": args["samples"],
                                          "seed": args["seed"], "base": args["base"]})
        tables = _standin_ethanol_tables if ethanol else _standin_tables
        shaped = ({**base_out, "ethanolKgPerH": base_out["productKgPerH"]} if composite and base_out else base_out)
        return {"base": base_out, "baseInfeasible": base_infeasible,
                "tables": tables(args["base"], shaped) if base_out else None, "grid": grid, "montecarlo": mc}
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


# The tables of a run (OF-BLD-019 §2.1) in the shape the worker writes, from
# a closed form over the stand-in's inputs and cost lines: three units, six
# streams, a TEA breakdown whose lines sum to the stand-in price. Every
# number is invented and the tables say so in `tablesSource`.
STANDIN_HOURS = 8000.0


def _standin_tables(v: dict[str, float], out: dict[str, Any]) -> dict[str, Any]:
    from .flowsheets.shelf import TABLE_UNITS

    sugar, pha = v["sugarFeed"], v["sugarFeed"] * v["yield"]
    water = pha / v["titre"] * 1000.0
    cells = pha * (1 - v["content"]) / v["content"]
    product = (pha + cells) * v["recovery"]
    broth = sugar + water

    def stream(sid, source, sink, flows, price=None):
        return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price}

    streams = [
        stream("sugar", None, "R1", {"Glucose": sugar}, v["sugarPrice"]),
        stream("process_water", None, "R1", {"Water": water}),
        stream("broth", "R1", "C1", {"Water": water, "Glucose": sugar - pha - cells, "PHB": pha, "Cells": cells}),
        stream("spent_medium", "C1", None, {"Water": water, "Glucose": sugar - pha - cells, "PHB": pha * (1 - v["recovery"]),
                                            "Cells": cells * (1 - v["recovery"])}),
        stream("wet_solids", "C1", "D1", {"PHB": pha * v["recovery"], "Cells": cells * v["recovery"]}),
        stream("product", "D1", None, {"PHB": pha * v["recovery"], "Cells": cells * v["recovery"]}),
    ]
    lines_in = out["costLines"]
    per = pha * v["recovery"] * STANDIN_HOURS
    capital = lines_in["capex"] * per
    units = []
    for n, (uid, share, heat, cool, kw) in enumerate((("R1", 0.7, None, 9.0e6, 400.0), ("C1", 0.2, None, None, 90.0),
                                                       ("D1", 0.1, 4.0e6, None, 170.0))):
        installed = capital * 3.0 * share
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid], "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    annual = {"feedstock": lines_in["media"] * per, "otherMaterials": 0.0,
              "utilities": (lines_in["utilities"] + lines_in["downstream"]) * per,
              "fixedOperating": (lines_in["labor"] + lines_in["other"]) * per, "capitalRecovery": capital}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery"}
    sales = sum(annual.values())
    installed_total = sum(u["installedCost"] for u in units)
    tea = {
        "teaClass": "StandIn", "product": "product", "feedstock": "sugar",
        "productPrice": sales / (product * STANDIN_HOURS), "basisFlow": pha * v["recovery"],
        "basis": "kg of PHA contained in dried cell mass", "operatingHours": STANDIN_HOURS, "sales": sales,
        "materialCost": annual["feedstock"], "feedstockCost": annual["feedstock"], "otherMaterialCost": 0.0,
        "utilityCost": annual["utilities"], "purchaseCost": installed_total / 2.0, "installedEquipmentCost": installed_total,
        "FCI": installed_total, "TCI": installed_total, "FOC": annual["fixedOperating"], "laborCost": lines_in["labor"] * per,
        "capitalRecovery": capital, "coproductCredits": 0.0, "IRR": None, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / per, "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    heating = sum(u["heatingDuty"] or 0.0 for u in units) / 1e6
    cooling = sum(u["coolingDuty"] or 0.0 for u in units) / 1e6
    power = sum(u["power"] or 0.0 for u in units) / 1e3
    return {
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": heating, "heatingUnit": "GJ/hr", "cooling": cooling,
                      "coolingUnit": "GJ/hr", "electricityConsumption": power, "electricityConsumptionUnit": "MW",
                      "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


# A reference biorefinery's run (OF-BLD-019 §2.2) in the shape the worker's
# `reference` op writes, from a closed form: three units, five streams, a
# TEA whose lines sum to the stand-in price, the package test's quantities
# read from those, and every default the shelf lists. Every number is
# invented and the run says so in `simulator` and `tablesSource`; the
# package test's values beside it are the installed file's, as a real run's.
def _standin_reference(flowsheet: str) -> dict[str, Any]:
    from .flowsheets import shelf as _shelf
    from .flowsheets.shelf import TABLE_UNITS

    info = _shelf.info(flowsheet)
    hours, feed, product, price, feed_price = 8000.0, 40000.0, 12000.0, 0.5, 0.15
    lines_in = {"feedstock": feed * feed_price, "otherMaterials": 600.0, "utilities": 900.0,
                "fixedOperating": 500.0, "capitalRecovery": 700.0}
    credit = sum(lines_in.values()) - product * price  # what the co-product must bring for the lines to sum
    annual = {k: v * hours for k, v in lines_in.items()} | {"coproductCredits": -credit * hours}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery",
             "coproductCredits": "Co-product credits"}

    def stream(sid, source, sink, flows, price_=None):
        return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price_}

    streams = [
        stream("feed", None, "R1", {"Starch": feed}, feed_price),
        stream("beer", "R1", "D1", {"Ethanol": product, "Water": 3 * product}),
        stream("product", "D1", "M1", {"Ethanol": product}, price),
        stream("stillage", "D1", None, {"Water": 3 * product}),
        stream("coproduct", "R1", None, {"Solids": feed - product}, credit / (feed - product)),
    ]
    units = []
    for n, (uid, heat, cool, kw) in enumerate((("R1", None, 5.0e6, 300.0), ("D1", 9.0e6, 8.0e6, 120.0),
                                               ("M1", None, None, 40.0))):
        installed = lines_in["capitalRecovery"] * hours * (3 - n)
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid],
                      "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    installed_total = sum(u["installedCost"] for u in units)
    # The TEA prices installation on the purchase costs as a whole, with a
    # STAND-IN Lang factor, as the corn plant's TEA does with its own: so the
    # TEA's installed equipment cost is not the sum of the units' (OF-BLD-019
    # §3.R, finding 19), and a page that summed the units would show another
    # number than the TEA's.
    lang = 3.0
    tea_installed = installed_total / 2.0 * lang
    sales = product * price * hours + credit * hours
    heating = sum(u["heatingDuty"] or 0.0 for u in units) / 1e6
    cooling = sum(u["coolingDuty"] or 0.0 for u in units) / 1e6
    power = sum(u["power"] or 0.0 for u in units) / 1e3
    tea = {
        "teaClass": "StandIn", "product": "product", "feedstock": "feed", "productPrice": price, "basisFlow": product,
        "basis": "kg of the STAND-IN product", "operatingHours": hours, "sales": sales,
        "materialCost": annual["feedstock"] + annual["otherMaterials"], "feedstockCost": annual["feedstock"],
        "otherMaterialCost": annual["otherMaterials"], "utilityCost": annual["utilities"],
        "purchaseCost": installed_total / 2.0, "installedEquipmentCost": tea_installed, "FCI": tea_installed,
        "TCI": tea_installed, "FOC": annual["fixedOperating"], "laborCost": annual["fixedOperating"] / 2.0,
        "capitalRecovery": annual["capitalRecovery"], "coproductCredits": credit * hours, "IRR": 0.1, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / (product * hours), "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    measured = {
        "tea.IRR": tea["IRR"], "feedstock.price": feed_price, "product.price": price, "tea.sales": sales,
        "tea.material_cost": tea["materialCost"], "tea.installed_equipment_cost": tea_installed,
        "tea.utility_cost": tea["utilityCost"], "units.get_heating_duty()": heating, "units.get_cooling_duty()": cooling,
        "units.get_electricity_consumption()": power, "units.get_electricity_production()": 0.0,
    }
    if flowsheet == "corn_drygrind":
        outputs = {"ethanolPriceUsdPerKg": price, "IRR": tea["IRR"], "ethanolKgPerH": product, "cornKgPerH": feed}
    else:
        outputs = {"mespUsdPerGal": price * 3.0, "mespUsdPerKg": price, "ethanolDensityKgPerGal": 3.0,
                   "settings": {"rateOfReturn": 0.1, "operatingDays": hours / 24.0, "incomeTax": 0.35,
                                "startYear": 2007, "endYear": 2037}}
    read_back = {i.key: ("STAND-IN" if i.dimension == "schedule" else lang if i.key == "langFactor" else 1.0) for i in info.inputs}
    return {
        "flowsheet": flowsheet, "simulator": PROFORMA_STANDIN, "package": f"STAND-IN for {flowsheet}",
        **outputs, "references": [PROFORMA_STANDIN], "measured": measured, "readBack": read_back,
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": heating, "heatingUnit": "GJ/hr", "cooling": cooling,
                      "coolingUnit": "GJ/hr", "electricityConsumption": power, "electricityConsumptionUnit": "MW",
                      "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


# OF-BLD-019 §2.3: the yeast flowsheet's STAND-INs. Records on a thread Q
# paper id no corpus holds, and a closed-form evaluator whose theoretical
# yield is its own STAND-IN, not the flowsheet's (which the worker computes
# from the reaction and thermosteam's molecular weights). Not a price of
# anything.
STANDIN_THEORETICAL = 0.511
YEAST_STANDIN_ASSUMED = (("plant_scale", 100000.0, 100000.0, 100000.0), ("glucose_price", 0.4, 0.3, 0.5))


def _standin_yeast_records() -> list[dict[str, Any]]:
    rows = [("medium_component_conc", "g L-1", (20.0, 60.0, 100.0)), ("ethanol_titre", "g L-1", (40.0, 60.0, 90.0)),
            ("ethanol_yield_substrate", "g g-1", (0.4, 0.45, 0.48)), ("ethanol_productivity", "g L-1 h-1", (1.0, 1.8, 2.5))]
    out = []
    for field, unit, values in rows:
        for n, v in enumerate(values):
            out.append({"id": f"standin-{field}-{n}", "paperId": "Q999", "field": field, "value": v, "unit": unit,
                        "carbonSource": "glucose", "strainId": "s-cerevisiae-cenpk113-7d",
                        "organismText": "STAND-IN organism", "provenance": "unverified", "status": "unverified",
                        "primary": True})
    return out


def _standin_ethanol_evaluate(v: dict[str, float]) -> dict[str, Any]:
    if v["yield"] > STANDIN_THEORETICAL:
        raise ValueError("yield")
    lines = {"media": v["glucose_price"] / v["yield"], "utilities": 0.6 / v["feed_glucose_conc"], "labor": 0.02,
             "downstream": 2.0 / v["feed_glucose_conc"], "other": 0.03,
             "capex": 0.05 + 0.002 * v["titre"] / v["productivity"]}
    return {"pricePerKgEthanol": sum(lines.values()), "ethanolKgPerH": v["plant_scale"] * 1000.0 / STANDIN_HOURS,
            "costLines": lines, "readBack": {"standIn": 1.0}}


def _standin_ethanol_tables(v: dict[str, float], out: dict[str, Any]) -> dict[str, Any]:
    """The tables of a run in the shape the worker writes, from a closed form
    over the yeast stand-in's inputs and cost lines: four units, seven
    streams, a TEA breakdown whose lines sum to the stand-in price. Every
    number is invented, and `tablesSource` says so."""
    from .flowsheets.shelf import TABLE_UNITS

    ethanol = out["ethanolKgPerH"]
    glucose = ethanol / v["yield"]
    co2 = ethanol  # STAND-IN: as much carbon dioxide as ethanol, by mass
    left = glucose - ethanol - co2
    water = glucose / v["feed_glucose_conc"] * 1000.0

    def stream(sid, source, sink, flows, price=None, phase="l"):
        return {"id": sid, "source": source, "sink": sink, "phase": phase, "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price}

    streams = [
        stream("glucose", None, "R1", {"Glucose": glucose}, v["glucose_price"]),
        stream("process_water", None, "R1", {"Water": water}),
        stream("vent", "R1", None, {"CO2": co2}, phase="g"),
        stream("beer", "R1", "D302", {"Water": water, "Ethanol": ethanol, "Glucose": left}),
        stream("stillage", "D302", None, {"Water": water, "Glucose": left}),
        stream("distillate", "D302", "U301", {"Ethanol": ethanol}),
        stream("ethanol", "U301", None, {"Ethanol": ethanol}),
    ]
    lines_in = out["costLines"]
    per = ethanol * STANDIN_HOURS
    capital = lines_in["capex"] * per
    units = []
    for n, (uid, share, heat, cool, kw) in enumerate((("R1", 0.5, None, 9.0e6, 300.0), ("D302", 0.3, 6.0e7, 4.0e7, 60.0),
                                                       ("U301", 0.2, 1.0e7, None, 20.0))):
        installed = capital * 3.0 * share
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid], "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    annual = {"feedstock": lines_in["media"] * per, "otherMaterials": 0.0,
              "utilities": (lines_in["utilities"] + lines_in["downstream"]) * per,
              "fixedOperating": (lines_in["labor"] + lines_in["other"]) * per, "capitalRecovery": capital}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery"}
    sales = sum(annual.values())
    installed_total = sum(u["installedCost"] for u in units)
    tea = {
        "teaClass": "StandIn", "product": "ethanol", "feedstock": "glucose",
        "productPrice": sales / per, "basisFlow": ethanol, "basis": "kg of fuel-grade ethanol, as the product leaves its tank",
        "operatingHours": STANDIN_HOURS, "sales": sales,
        "materialCost": annual["feedstock"], "feedstockCost": annual["feedstock"], "otherMaterialCost": 0.0,
        "utilityCost": annual["utilities"], "purchaseCost": installed_total / 2.0, "installedEquipmentCost": installed_total,
        "FCI": installed_total, "TCI": installed_total, "FOC": annual["fixedOperating"], "laborCost": lines_in["labor"] * per,
        "capitalRecovery": capital, "coproductCredits": 0.0, "IRR": None, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / per, "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    return {
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": sum(u["heatingDuty"] or 0.0 for u in units) / 1e6,
                      "heatingUnit": "GJ/hr", "cooling": sum(u["coolingDuty"] or 0.0 for u in units) / 1e6,
                      "coolingUnit": "GJ/hr", "electricityConsumption": sum(u["power"] or 0.0 for u in units) / 1e3,
                      "electricityConsumptionUnit": "MW", "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


# The key under which prototype_proforma hands rebuild_prototype the run
# artifacts artifacts.json carries beside the others: not a file of its own.
PROFORMA_RUN_ARTIFACTS = "(run artifacts for artifacts.json)"

# OF-BLD-020 §2.2: the parameter panel's scopes for the double. A scenario
# made in a browser takes a time-based id; its scope is recorded under this
# one and the double answers it under the id asked.
PARAMS_MADE_HERE = "sc-made-here"
# A STAND-IN override the browser tests type, above the yield's bounds (the
# ontology's plausibility range for ethanol_yield_substrate): the resolve is
# recorded as the real code answers it, warning and all. Not a yield of
# anything.
PARAMS_OUT_OF_BOUNDS = ("yield", 0.7)
# A STAND-IN titre the browser tests type beside a fermOS fit chosen for
# titre, yield and productivity (OF-BLD-020 §2.R): the resolve is recorded as
# the real code answers it, a refusal in the run's words. Not a titre of
# anything; the words name no value.
PARAMS_TYPED_BESIDE_A_FIT = ("titre", 50.0)


class _PoolLoaded:
    """evidence_pool.load answers the stand-in pool while the panel's
    provider binds, as the tests' client fixture has it."""

    def __init__(self, pool) -> None:
        self.pool = pool

    def __enter__(self):
        from . import evidence_pool

        self.saved = evidence_pool.load
        evidence_pool.load = lambda include_archived=False: self.pool
        return self

    def __exit__(self, *exc) -> None:
        from . import evidence_pool

        evidence_pool.load = self.saved


def _param_answer(scope: str, req=None) -> dict[str, Any]:
    """GET /api/params/{scope} as the service answers it: the scope, or the
    refusal in its words with its status."""
    from . import params

    try:
        return {"status": 200, "body": params.scope(scope, req).model_dump(mode="json")}
    except params.ScopeUnknown as e:
        return {"status": 404, "body": {"detail": str(e)}}
    except params.ParamRefused as e:
        return {"status": 422, "body": {"detail": str(e)}}


def _resolve_answer(scope: str, req) -> dict[str, Any]:
    """POST /api/params/{scope}/resolve as the service answers it: the
    result, or the refusal in its words with its status."""
    from . import params

    try:
        return {"status": 200, "body": params.resolve_scope(scope, req).model_dump(mode="json")}
    except params.ScopeUnknown as e:
        return {"status": 404, "body": {"detail": str(e)}}
    except params.ParamRefused as e:
        return {"status": 422, "body": {"detail": str(e)}}


def prototype_params(pool) -> dict[str, Any]:
    """The parameter panel's Proforma scopes over the stand-in records: each
    seed BioSTEAM scenario by its id, each shelf flowsheet as a scenario made
    here names it (or the service's refusal), and one resolve with a yield
    outside its bounds, each as the real code answers it."""
    from . import params, proforma
    from .flowsheets import shelf as _shelf
    from .models import Override, ParamResolveRequest

    with _PoolLoaded(pool):
        scopes = {f"proforma:{sc['id']}": _param_answer(f"proforma:{sc['id']}") for sc in proforma.seed_scenarios()}
        made = f"proforma:{PARAMS_MADE_HERE}"
        flowsheets = {fid: _param_answer(made, ParamResolveRequest(flowsheet=fid)) for fid in (*_shelf.SHELF, *_shelf.TEST_ONLY)}
        key, value = PARAMS_OUT_OF_BOUNDS
        o = Override(scope=f"proforma:{proforma.YEAST_SCENARIO_ID}", key=key, value=value, by="openFerment test fixture",
                     at="2026-10-15", note=PROFORMA_STANDIN)
        req = ParamResolveRequest(overrides=[o])
        resolved = params.resolve_scope(o.scope, req).model_dump(mode="json")
    return {"params-proforma.json": {"scopes": scopes, "madeHere": PARAMS_MADE_HERE, "flowsheets": flowsheets,
                                     "flowsheetOf": {f"proforma:{sc['id']}": sc["modelId"] for sc in proforma.seed_scenarios()},
                                     "resolve": {"flowsheet": proforma.ETHANOL, "request": req.model_dump(mode="json"),
                                                 "body": resolved}}}


def prototype_proforma() -> dict[str, Any]:
    import tempfile
    from types import SimpleNamespace

    from . import artifacts as _artifacts
    from . import intake as _intake
    from . import proforma
    from .flowsheets import shelf as _shelf
    from .models import ProformaRunRequest

    rs = _standin_records() + _standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    a = _standin_overrides(proforma.SCENARIO_ID, PHA_STANDIN_ASSUMED)
    ay = _standin_overrides(proforma.YEAST_SCENARIO_ID, YEAST_STANDIN_ASSUMED)
    saved = (_intake.DATA_DIR, proforma.call, proforma.yield_cap)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_call
            proforma.yield_cap = lambda: None
            run = proforma.run(ProformaRunRequest(scenarioId=proforma.SCENARIO_ID, overrides=a), pool=pool)
            yeast = proforma.run(ProformaRunRequest(scenarioId=proforma.YEAST_SCENARIO_ID, overrides=ay), pool=pool)
            yeast_art = _artifacts.get(yeast.artifactId).model_copy(update={"createdAt": AT, "durationMs": 0})
            # OF-BLD-019 §2.3 (b, c): the seed's scenarios bound with the
            # switch off and on, and every flowsheet a scenario made here
            # can name, bound (or refused, in the service's words) each way.
            scenarios = {inc: [x.model_dump(mode="json") for x in proforma.scenarios(include_archived=inc, pool=pool)]
                         for inc in (False, True)}
            bind: dict[str, dict[str, Any]] = {"off": {}, "on": {}}
            for switch, inc in (("off", False), ("on", True)):
                for fid in (*_shelf.SHELF, *_shelf.TEST_ONLY):
                    try:
                        body = proforma.bind_flowsheet(fid, include_archived=inc, pool=pool).model_dump(mode="json")
                        bind[switch][fid] = {"status": 200, "body": body}
                    except proforma.ScenarioRefused as e:
                        bind[switch][fid] = {"status": 422, "body": {"detail": str(e)}}
            panel = prototype_params(pool)
        finally:
            _intake.DATA_DIR, proforma.call, proforma.yield_cap = saved
    run.evidence.basis.at = AT
    yeast.evidence.basis.at = AT
    # OF-BLD-019 §2.1: the shelf, as GET /api/proforma/shelf serves it with
    # the program switch off and, `?includeArchived=true`, on.
    def shelf(include_archived: bool) -> list[dict[str, Any]]:
        return [f.model_dump(mode="json") for f in proforma.shelf(include_archived=include_archived)]

    # OF-BLD-019 §2.2: each reference biorefinery as GET and POST
    # /api/proforma/reference/{id} answer, its run made through the real
    # code (proforma.run_reference, the artifact store in a scratch folder,
    # the package test's values parsed from the installed file) with the
    # STAND-IN in place of BioSTEAM, and the simulator as the double has it.
    references: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_call
            for fid in (f.id for f in proforma._shelf.SHELF.values() if f.reference):
                art = proforma.run_reference(fid).model_copy(update={"createdAt": AT, "durationMs": 0})
                ref = proforma.reference(fid, art).model_copy(update={"simulator": {"status": "cold", "error": None}})
                references[f"proforma-reference-{fid}.json"] = ref.model_dump(mode="json")
        finally:
            _intake.DATA_DIR, proforma.call, proforma.yield_cap = saved

    return {"proforma-scenarios.json": scenarios[False], "proforma-scenarios-archived.json": scenarios[True],
            "proforma-bind.json": bind, "proforma-run.json": run.model_dump(mode="json"),
            "proforma-run-yeast.json": yeast.model_dump(mode="json"),
            "proforma-shelf.json": shelf(False), "proforma-shelf-archived.json": shelf(True), **references, **panel,
            PROFORMA_RUN_ARTIFACTS: [yeast_art.model_dump(mode="json")]}


# OF-BLD-019 §5.2: a scenario's yield read against the geneOS ceiling. A
# STAND-IN ceiling, labelled so in its basis and never computed by any
# model: its model input is an assumption (so it is `demo`) carrying the
# shelf id it stands in for, so the check maps it to the yeast scenario as
# it maps a real ceiling of that model. STANDIN_CEILING_G_PER_G is a setting
# of this fixture, between the yeast stand-in yields' median and their
# highest, so the browser tests see the flag; its mol per mol is taken at
# the conventions geneos_models states, as a real ceiling's is.
STANDIN_CEILING_G_PER_G = 0.47
STANDIN_CEILING_MODEL = "Yeast9"
STANDIN_CEILING_NOTE = ("STAND-IN ceiling for tests and the browser double: not computed by {model} or any model; "
                        "a value set between the stand-in yields so the flag shows")


def standin_ceiling(model_id: str, product: str, substrate: str, g_per_g: float, *, at: str = AT,
                    version: str = "STAND-IN ceiling 1"):
    """Keep one STAND-IN `geneos.ceiling` artifact in the current store
    (artifacts.folder()), in the shape the geneOS worker writes, for the
    shelf model `model_id`; return it. Its basis is geneos's own but for the
    model input, an assumption that says what it is."""
    from . import artifacts, atomic, geneos, geneos_models
    from .basis import basis_provenance
    from .models import Artifact, BasisInput, BasisSource, ComputedBasis

    inputs = [BasisInput(name="model", value=f"STAND-IN for {model_id}", unit="", source=BasisSource(
        kind="assumption", id=model_id, by="openFerment test fixture", note=STANDIN_CEILING_NOTE.format(model=model_id)))]
    inputs += [i for i in geneos._inputs(model_id, product, [substrate]) if i.name != "model"]
    mol = g_per_g * geneos_models.SUBSTRATES[substrate]["molarMass"] / geneos_models.PRODUCTS[product]["molarMass"]
    output = {"modelId": model_id, "product": product, "substrate": substrate,
              "exchange": geneos_models.exchange_id(model_id, substrate), "uptake": geneos_models.UPTAKE,
              "flux": mol * geneos_models.UPTAKE, "molPerMol": mol, "gPerG": g_per_g, "solver": "STAND-IN",
              "status": "optimal"}
    aid = artifacts.artifact_id(geneos.CEILING, version, inputs)
    basis = ComputedBasis(tool=geneos.CEILING, toolVersion=version, inputs=inputs, artifactId=aid, at=at)
    art = Artifact(id=aid, tool=geneos.CEILING, toolVersion=version, inputs=inputs, output=output,
                   outputHash=artifacts.output_hash(output), provenance=basis_provenance(basis, {}, {}), createdAt=at,
                   durationMs=0)
    artifacts.folder().mkdir(parents=True, exist_ok=True)
    atomic.write_text(artifacts.folder() / f"{aid}.json", art.model_dump_json(indent=2) + "\n")
    return art


def prototype_ceiling_check() -> dict[str, Any]:
    """GET /api/proforma/ceiling-check for the double, through the real code
    over the stand-in records: each seed scenario's check with no ceiling on
    file (a fresh install) and with the STAND-IN ceiling on file, by the
    flowsheet it runs; and (§5.R) sc-yeast-1's with each choice of the
    bridge's fit and forecast the browser tests make, read or refused in the
    service's words (`fitted`, by the same two states)."""
    import tempfile
    from types import SimpleNamespace

    from . import intake as _intake
    from . import proforma

    rs = _standin_records() + _standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})

    def checked() -> dict[str, Any]:
        out: dict[str, Any] = {}
        for sid in (proforma.YEAST_SCENARIO_ID, proforma.SCENARIO_ID):
            body = proforma.ceiling_check(sid, include_archived=True, pool=pool)
            out[body.flowsheet] = {"status": 200, "body": body.model_dump(mode="json")}
        return out

    def fitted(choices: list[dict[str, str]]) -> list[dict[str, Any]]:
        out = []
        for chosen in choices:
            try:
                body = proforma.ceiling_check(proforma.YEAST_SCENARIO_ID, pool=pool, fits=chosen)
                out.append({"fits": chosen, "status": 200, "body": body.model_dump(mode="json")})
            except proforma.ScenarioRefused as e:
                out.append({"fits": chosen, "status": 422, "body": {"detail": str(e)}})
        return out

    saved = _intake.DATA_DIR
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            fit_id, fc_id = _bridge_fits()
            choices = [{k: fc_id for k in proforma.FIT_KEYS}, *_bridge_choices(fit_id, fc_id)]
            none, fitted_none = checked(), fitted(choices)
            standin_ceiling(STANDIN_CEILING_MODEL, "ethanol", "glucose", STANDIN_CEILING_G_PER_G)
            on_file, fitted_on_file = checked(), fitted(choices)
        finally:
            _intake.DATA_DIR = saved
    return {"proforma-ceiling-check.json": {"none": none, "onFile": on_file,
                                            "fitted": {"none": fitted_none, "onFile": fitted_on_file}}}


def _kept_standin_runs(then=None) -> list:
    """The two runs the double keeps (OF-BLD-019 §7.R): sc-pha-1's and
    sc-yeast-1's, made through the real code with the STAND-IN evaluator
    exactly as prototype_proforma makes them, so their ids are the ones
    artifacts.json carries. `then(arts)`, given, runs while the scratch
    store still holds the runs (thermo.py reads a run's streams there)."""
    import tempfile
    from types import SimpleNamespace

    from . import artifacts, proforma
    from . import intake as _intake
    from .models import ProformaRunRequest

    rs = _standin_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    ry = _standin_records() + _standin_yeast_records()
    pool_y = SimpleNamespace(records=ry, records_by_id={r["id"]: r for r in ry})
    a = _standin_overrides(proforma.SCENARIO_ID, PHA_STANDIN_ASSUMED)
    ay = _standin_overrides(proforma.YEAST_SCENARIO_ID, YEAST_STANDIN_ASSUMED)
    saved = (_intake.DATA_DIR, proforma.call, proforma.yield_cap)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_call
            proforma.yield_cap = lambda: None
            runs = [proforma.run(ProformaRunRequest(scenarioId=proforma.SCENARIO_ID, overrides=a), pool=pool),
                    proforma.run(ProformaRunRequest(scenarioId=proforma.YEAST_SCENARIO_ID, overrides=ay), pool=pool_y)]
            arts = [artifacts.get(r.artifactId).model_copy(update={"createdAt": AT, "durationMs": 0}) for r in runs]
            if then is not None:
                then(arts)
        finally:
            _intake.DATA_DIR, proforma.call, proforma.yield_cap = saved
    return arts


# OF-BLD-019 §4.1: pureOS's trains for the double, read by the real code
# (pureos.trains, pureos.train) from the runs prototype_proforma makes: the
# same artifacts artifacts.json carries, whose tables are the stand-in's and
# say so in `tablesSource`. §7.R: both kept runs, sc-pha-1's and
# sc-yeast-1's, so with the switch off the list holds the yeast train and
# says it hides PHA's, and the double answers either train by its scenario
# or its run's id (`pureos-train.json` PHA's, `pureos-train-yeast.json`).
def prototype_pureos() -> dict[str, Any]:
    from . import proforma, pureos

    arts = _kept_standin_runs()
    scenarios = pureos.seed_scenarios()

    def listed(include_archived: bool) -> list[dict[str, Any]]:
        return [pureos.summary(t).model_dump(mode="json") for t in pureos.trains(include_archived, arts=arts, scenarios=scenarios)]

    train = pureos.train(proforma.SCENARIO_ID, arts=arts, scenarios=scenarios)
    yeast = pureos.train(proforma.YEAST_SCENARIO_ID, arts=arts, scenarios=scenarios)
    return {"pureos-trains.json": listed(False), "pureos-trains-archived.json": listed(True),
            "pureos-train.json": train.model_dump(mode="json"), "pureos-train-yeast.json": yeast.model_dump(mode="json")}


# OF-BLD-019 §4.2: thermosteam's answers for the double, made by the real
# thermo.py over the stand-in runs prototype_pureos reads (one question a
# stream of each, §7.R), the azeotrope preset and a beer at a STAND-IN titre record's
# titre. thermosteam is replaced by a closed-form STAND-IN that knows three
# chemicals and refuses any other in words, as the library refuses a chemical
# it lacks; every number it gives is invented and its `library` says so.
THERMO_STANDIN = "STAND-IN for the browser tests: a closed form in place of thermosteam; every number invented"
# Invented: density kg/m^3, heat capacity J/g/K, viscosity Pa*s, boiling K.
_THERMO_STANDIN_CHEMICALS = {"Water": (1000.0, 4.2, 0.001, 373.0), "Ethanol": (790.0, 2.4, 0.0012, 351.0),
                             "Glucose": (1540.0, 1.2, 0.002, 600.0)}


def _standin_thermo_call(op: str, args: dict[str, Any]) -> Any:
    from .workers import WorkerError

    table = _THERMO_STANDIN_CHEMICALS
    if op == "volatility":  # OF-BLD-020 §7.2: the proposer's question, in the worker's shape
        return _standin_volatility(args)
    if op != "thermo_props":
        raise WorkerError(f"KeyError: the {THERMO_STANDIN} answers thermo_props and volatility alone, not {op!r}")
    solve = args.get("solve") or None
    if solve and solve["kind"] == "titre":
        w = solve["kgPerM3"] / table[solve["solvent"]][0]
        flows = {solve["solvent"]: 1.0 - w, solve["solute"]: w}
    elif solve and solve["kind"] == "azeotrope":
        flows = {solve["light"]: 0.95, solve["heavy"]: 0.05}
    else:
        flows = {k: float(v) for k, v in (args.get("components") or {}).items() if v}
    lacking = sorted(n for n in flows if n not in table)
    if lacking:
        raise WorkerError(f"Refused: the {THERMO_STANDIN} holds {', '.join(sorted(table))} alone; it has no "
                          f"{', '.join(lacking)}")
    total = sum(flows.values())
    w = {k: v / total for k, v in flows.items()}
    boil = sum(w[k] * table[k][3] for k in w)
    return {
        "library": THERMO_STANDIN, "T": args.get("T") or 298.15, "P": args.get("P") or 101325.0,
        "phase": args.get("phase") or "l", "TSource": "given" if args.get("T") is not None else "thermosteam's Stream default",
        "PSource": "given" if args.get("P") is not None else "thermosteam's Stream default", "massFractions": w,
        "density": 1.0 / sum(w[k] / table[k][0] for k in w), "Cp": sum(w[k] * table[k][1] for k in w),
        "viscosity": sum(w[k] * table[k][2] for k in w), "bubblePoint": boil - 5.0, "dewPoint": boil + 5.0,
        "vapourAtBubble": w, "units": {"density": "kg/m^3", "Cp": "J/g/K", "viscosity": "Pa*s", "T": "K", "P": "Pa",
                                       "bubblePoint": "K", "dewPoint": "K", "massFractions": "kg/kg",
                                       "vapourAtBubble": "mol/mol"},
        "solved": {"kind": solve["kind"], "how": THERMO_STANDIN} if solve else None, "notes": [THERMO_STANDIN],
    }


def _standin_volatility(args: dict[str, Any]) -> dict[str, Any]:
    """The worker's `volatility` answer from the STAND-IN's table: the two
    invented boiling points decide which boils first, and the azeotrope is
    said found with invented fractions, as thermosteam finds one for ethanol."""
    from .workers import WorkerError

    table = _THERMO_STANDIN_CHEMICALS
    chem, partner = args["chemical"], args["partner"]
    lacking = sorted(n for n in (chem, partner) if n not in table)
    if lacking:
        raise WorkerError(f"Refused: the {THERMO_STANDIN} holds {', '.join(sorted(table))} alone; it has no "
                          f"{', '.join(lacking)}")
    tb, tbp = table[chem][3], table[partner][3]
    return {
        "library": THERMO_STANDIN, "chemical": chem, "partner": partner, "P": args.get("P") or 101325.0,
        "PSource": "given" if args.get("P") is not None else "thermosteam's Stream default", "boilingPoint": tb,
        "partnerBoilingPoint": tbp, "lighter": chem if tb < tbp else partner, "azeotrope": True,
        "azeotropeMoleFraction": 0.9, "azeotropeMassFraction": 0.95, "azeotropeT": min(tb, tbp) - 1.0,
        "searched": {"of": chem if tb < tbp else partner, "from": 0.1, "to": 0.9, "points": 9, "halvings": 3},
        "units": {"boilingPoint": "K", "partnerBoilingPoint": "K", "azeotropeT": "K", "P": "Pa",
                  "azeotropeMoleFraction": "mol/mol", "azeotropeMassFraction": "kg/kg"},
        "how": THERMO_STANDIN, "notes": [THERMO_STANDIN],
    }


# OF-BLD-020 §7.2: pureOS's proposals for the double, made by the real
# proposer (pureos/proposer.py) over the exported products seed and hosts, in
# a scratch store, with the STAND-IN above answering thermosteam's volatility
# question: each ask the browser tests make, with the service's answer (200,
# or the 404 or 422 in its words). The volatility artifact a proposal names
# is the STAND-IN's, and its `library` says so.
PROPOSE_ASKS = (
    {"product": "ethanol", "host": "s-cerevisiae-s288c", "inletRef": None, "includeArchived": False},
    {"product": "ethanol", "host": "s-cerevisiae-cenpk113-7d", "inletRef": None, "includeArchived": False},
    {"product": "taq-dna-polymerase", "host": "s-cerevisiae-s288c", "inletRef": None, "includeArchived": False},
    {"product": "nonesuch", "host": "s-cerevisiae-s288c", "inletRef": None, "includeArchived": False},
    {"product": "phb", "host": "c-necator-h16", "inletRef": None, "includeArchived": False},
)


def prototype_propose() -> dict[str, Any]:
    import tempfile

    from . import proforma, pureos
    from . import intake as _intake

    entries: list[dict[str, Any]] = []
    saved = (_intake.DATA_DIR, proforma.call)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _intake.DATA_DIR = Path(tmp)
            proforma.call = _standin_thermo_call
            for ask in PROPOSE_ASKS:
                try:
                    body = pureos.propose(ask["product"], ask["host"], ask["inletRef"],
                                          include_archived=ask["includeArchived"]).model_dump(mode="json")
                    entries.append({"request": ask, "status": 200, "body": body})
                except pureos.ProposeUnknown as e:
                    entries.append({"request": ask, "status": 404, "body": {"detail": str(e)}})
                except pureos.ProposeRefused as e:
                    entries.append({"request": ask, "status": 422, "body": {"detail": str(e)}})
        finally:
            _intake.DATA_DIR, proforma.call = saved
    return {"pureos-propose.json": {"entries": entries}}


def prototype_thermo() -> dict[str, Any]:
    from types import SimpleNamespace

    from . import proforma, thermo
    from .models import ThermoPropsRequest

    titre = {"id": "standin-ethanol_titre-0", "paperId": "Q999", "field": "ethanol_titre", "value": 80.0,
             "unit": "g L-1", "provenance": "unverified", "status": "unverified", "primary": True,
             "organismText": "STAND-IN organism"}
    titres = SimpleNamespace(records=[titre], records_by_id={titre["id"]: titre}, record=lambda i: {titre["id"]: titre}.get(i))
    entries: list[dict[str, Any]] = []

    def ask(req: ThermoPropsRequest) -> None:
        asked = {k: v for k, v in req.model_dump().items() if v}
        try:
            art = thermo.props(req, pool=titres)
        except thermo.ThermoNotFound as e:
            entries.append({"request": asked, "status": 404, "body": {"detail": str(e)}})
        except thermo.ThermoRefused as e:
            entries.append({"request": asked, "status": 422, "body": {"detail": str(e)}})
        else:
            art = art.model_copy(update={"createdAt": AT, "durationMs": 0})
            entries.append({"request": asked, "status": 200, "body": art.model_dump(mode="json")})

    # §7.R: one question a stream of each kept run, sc-pha-1's and
    # sc-yeast-1's, so the yeast train's Properties card is answered too.
    def asked(arts: list) -> None:
        proforma.call = _standin_thermo_call
        for art in arts:
            for st in proforma.tables_of(art).streams:
                ask(ThermoPropsRequest(artifactId=art.id, streamId=st.id))
        ask(ThermoPropsRequest(preset=thermo.AZEOTROPE))
        ask(ThermoPropsRequest(preset=thermo.BEER, recordId=titre["id"]))

    _kept_standin_runs(then=asked)
    return {"thermo-props.json": {"entries": entries}}


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


# OF-BLD-020 §4.2: fermOS → Vessel against the double. Two batch_v1 runs
# made by the real fermos.simulate (scipy, no BioSTEAM) on STAND-IN overrides
# named as such, aerobic (Yx/o set) and anaerobic; the vessel scope each
# serves and the designs the browser tests ask for, made by the real Proforma
# worker on BioSTEAM when the sim extra is installed, else by a STAND-IN
# worker, the fixture saying which (`worker.kind`). A design from BioSTEAM
# moves in its last digits from one process to the next (§4.1, measured), so
# test_demo holds this file to the code by its requests and its simulations,
# and test:sim holds its numbers to the worker within VESSEL_FIXTURE_RTOL.
VESSEL_STANDIN = "STAND-IN for the vessel fixture: invented kinetics and an invented plant scale; none is a result"
VESSEL_BY = "openFerment test fixture"
VESSEL_AT = "2026-10-21"
VESSEL_SIM = {"mu_max": 0.3, "ks": 0.5, "yxs": 0.1, "alpha": 2.0, "yps": 0.45, "p_max": 95.0, "x0": 0.5,
              "s0": 100.0, "p0": 0.0}
VESSEL_AEROBIC = {"yxo": 1.0}
VESSEL_PLANT_SCALE = 50000.0
# §4.R: a STAND-IN person's heat per oxygen consumed (kJ kmol⁻¹), typed so the
# browser tests see a duty BioSTEAM forces from it, said so on the screen.
VESSEL_Q_STANDIN = -400000.0
VESSEL_FIXTURE_RTOL = 1e-6


def _biosteam_here() -> bool:
    import importlib.util

    return importlib.util.find_spec("biosteam") is not None


def _standin_vessel_call(op: str, args: dict[str, Any]) -> Any:
    """The Proforma worker's `vessel_specs` and `vessel_design` in the JSON
    contract's shape, with STAND-IN defaults and an invented design, for a
    machine without the sim extra. Nothing here is BioSTEAM's."""
    from . import vessel

    if op == "vessel_specs":
        kind = args["kind"]
        words = {"vessel_type": "Vertical", "vessel_material": "Stainless steel 316",
                 "heat_exchanger_configuration": "recirculation loop", "design": "Stirred tank"}
        keys = [d.key for d in vessel._decls(kind)] + ["batch", "Nmin", "Nmax", "reactions"]
        out: dict[str, Any] = {
            "kind": kind, "unitClass": "AeratedBioreactor" if kind == vessel.AEROBIC else "NRELAnaerobicBatchBioreactor",
            "parameters": {k: {"default": None if k in ("N", "loading_time", "Q_O2_consumption") else words.get(k, 0.5),
                               "from": VESSEL_STANDIN} for k in keys},
            "biosteam": "stand-in", "thermosteam": "stand-in", "biorefineries": "stand-in", "chemicals": VESSEL_STANDIN,
            "operatingHours": 1000.0, "operatingHoursFrom": VESSEL_STANDIN, "costIndex": 500.0, "costIndexYear": None}
        if kind == vessel.AEROBIC:
            out["designs"] = {
                "Stirred tank": {"method": "Riet", "optimize_power": True, "kW_per_m3": 0.5, "runs": ["Riet"],
                                 "solvesPower": ["Riet"], "registered": ["Riet"]},
                "Bubble column": {"method": "Dewes", "optimize_power": False, "kW_per_m3": 0.5, "runs": ["Dewes"],
                                  "solvesPower": [], "registered": ["Dewes"]},
            }
            out["defaultDesign"] = "Stirred tank"
            out["choices"] = {"vessel_material": ["Carbon steel", "Stainless steel 316"],
                              "vessel_type": ["Horizontal", "Vertical"],
                              "heat_exchanger_configuration": ["jacketed", "recirculation loop"]}
            out["heatPerO2"], out["heatPerO2From"] = -1.0, VESSEL_STANDIN
            out["aerationFloorMolPerS"], out["aerationFloorFrom"] = 0.0, VESSEL_STANDIN
            out["refuses"] = {}
        else:
            # What the NREL class's setters refuse, as the worker reads them from its code (§4.R).
            out["refuses"] = {k: {"atOrBelow": 1.0, "from": VESSEL_STANDIN} for k in ("N", "V_max")}
        return out
    if op == "vessel_design":
        aerobic = args["kind"] == vessel.AEROBIC
        ox = None
        if aerobic:
            ys = list(args["our"]["value"])
            ox = {"t": list(args["our"]["t"]), "our": ys, "unit": "mmol L⁻¹ h⁻¹", "otr": max(ys), "short": [],
                  "kLa": 1.0, "kLaNeededAtPeak": 1.0, "kLaUnit": "h⁻¹",
                  "method": (args["params"].get("method") or ("Dewes" if args["design"] == "Bubble column" else "Riet")),
                  "aerated": True, "oxygenBasis": args["oxygenBasis"], "targetUptake": max(ys), "sized": max(ys),
                  "balancedUptake": max(ys), "scale": 1.0, "cStar": 1.0, "cL": 0.5, "drivingForce": 0.5,
                  "reactionO2KmolPerH": 1.0, "scaledO2KmolPerH": 1.0, "simulatedO2KmolPerH": 1.0, "floorKmolPerH": 0.0}
        row = lambda label, value, unit: {"label": label, "value": value, "unit": unit, "readFrom": VESSEL_STANDIN}  # noqa: E731
        return {"unitClass": "AeratedBioreactor" if aerobic else "NRELAnaerobicBatchBioreactor", "unitId": "R1",
                "aerobic": aerobic, "design": [row("Vessels", 2.0, ""), row("Volume of each vessel", 10.0, "m3"),
                                               row("Batch time (reacting)", args["tau"], "hr")],
                "designResults": {"Number of reactors": 2.0, "Reactor volume": 10.0}, "auxiliaries": {},
                "used": {}, "coolingAgents": [], "cost": {
                    "purchase": 1.0, "installed": 2.0, "byItem": {"Vessel": {"purchase": 1.0, "installed": 2.0}},
                    "utility": 1.0, "costIndex": 500.0, "costIndexYear": None, "note": VESSEL_STANDIN},
                "versions": {"biosteam": "stand-in"}, "chemicals": VESSEL_STANDIN, "dutyRead": -1.0,
                "scale": {"how": VESSEL_STANDIN}, "reaction": {"equation": VESSEL_STANDIN, "notes": []}, "oxygen": ox,
                "warnings": [], "utilitySettings": {}, "designNotes": [],
                "heat": {"bst": -1.0, "method": "heats-of-formation", "consumedKmolPerH": 1.0 if aerobic else None,
                         "convention": -1.0 if aerobic else None, "oxygenKmolPerH": 1.0 if aerobic else None,
                         "conventionNote": VESSEL_STANDIN}}
    raise ValueError(f"the stand-in vessel worker has no op {op}")


# The designs the browser tests ask for: (which simulation, vessel type,
# the overrides beyond the plant scale), each with the plant scale typed.
VESSEL_ASKS = (
    ("aerobic", None, ()),
    ("aerobic", "bubble-column", (("design", "Bubble column"),)),
    ("anaerobic", None, ()),
    ("aerobic", None, (("Q_O2_consumption", VESSEL_Q_STANDIN),)),
)


# The pool a fixture's simulation binds from: no records at all (see
# prototype_vessel).
_NO_RECORDS = SimpleNamespace(records=[], records_by_id={}, hidden={})


def prototype_vessel(real_worker: bool | None = None) -> dict[str, Any]:
    from . import fermos, params, proforma, vessel
    from . import intake as _intake
    from .models import Override, SimulationRequest, VesselRequest

    real = _biosteam_here() if real_worker is None else real_worker
    family = "fermos:family:batch_v1"

    def simulate(extra: dict[str, float]) -> Any:
        values = {**VESSEL_SIM, **extra}
        # An empty evidence pool: the fixture's simulation binds the named
        # stand-ins and the conventions alone, never this machine's thread Q
        # candidates, so the fixture is the same wherever it is rebuilt.
        return fermos.simulate(SimulationRequest(family="batch_v1", product="ethanol", sugar="glucose", overrides=[
            Override(scope=family, key=k, value=v, by=VESSEL_BY, at=VESSEL_AT, note=VESSEL_STANDIN)
            for k, v in values.items()]), by_pool=_NO_RECORDS)

    def typed(aid: str, key: str, value: Any) -> Override:
        return Override(scope=f"fermos:vessel:{aid}", key=key, value=value, by=VESSEL_BY, at=VESSEL_AT,
                        note=VESSEL_STANDIN if key in ("plant_scale", "Q_O2_consumption") else None)

    def stamped(body: dict[str, Any]) -> dict[str, Any]:
        out = {**body, "createdAt": AT}
        out["evidence"] = {**body["evidence"], "basis": {**body["evidence"]["basis"], "at": AT}}
        return out

    saved = (_intake.DATA_DIR, proforma.call, dict(vessel._SPECS))
    with _scratch() as scratch:
        try:
            _intake.DATA_DIR = scratch
            vessel._SPECS.clear()
            if not real:
                proforma.call = _standin_vessel_call
            sims = {"aerobic": simulate(VESSEL_AEROBIC), "anaerobic": simulate({})}
            ids = {k: v.artifactId for k, v in sims.items()}
            listed = {s.artifactId: s for s in fermos.simulations()}
            simulations = [listed[ids[k]].model_copy(update={"createdAt": AT}).model_dump(mode="json")
                           for k in ("aerobic", "anaerobic")]
            scopes = []
            for which, kind in (("aerobic", None), ("aerobic", "bubble-column"), ("anaerobic", None)):
                body = vessel.scope(ids[which], kind).model_dump(mode="json")
                scopes.append({"simulation": ids[which], "vesselType": kind, "status": 200, "body": body})
            # §4.R: the bridge's STAND-IN fit and forecast (fermos-fits.json lists them), each one's vessel scope
            # as the service serves or refuses it, so the browser can choose a fit when no simulation is kept.
            for fid in _bridge_fits():
                try:
                    scopes.append({"fit": fid, "vesselType": None, "status": 200,
                                   "body": vessel.scope(fid).model_dump(mode="json")})
                except params.ParamRefused as e:
                    scopes.append({"fit": fid, "vesselType": None, "status": 422, "body": {"detail": str(e)}})
            designs = []
            refused = VesselRequest(simulation=ids["aerobic"])
            try:
                vessel.design(refused)
            except vessel.VesselRefused as e:
                designs.append({"request": refused.model_dump(mode="json"), "status": 422, "body": {"detail": str(e)}})
            for which, kind, more in VESSEL_ASKS:
                aid = ids[which]
                req = VesselRequest(simulation=aid, vesselType=kind, overrides=[
                    *(typed(aid, k, v) for k, v in more), typed(aid, "plant_scale", VESSEL_PLANT_SCALE)])
                body = stamped(vessel.design(req).model_dump(mode="json"))
                designs.append({"request": req.model_dump(mode="json"), "status": 200, "body": body})
            ws = vessel.worker_specs(vessel.AEROBIC)
        finally:
            _intake.DATA_DIR, proforma.call = saved[0], saved[1]
            vessel._SPECS.clear()
            vessel._SPECS.update(saved[2])
    worker = {"kind": "biosteam" if real else "stand-in",
              "note": ("designed by the real Proforma worker on BioSTEAM, from STAND-IN simulations and a STAND-IN plant "
                       "scale" if real else VESSEL_STANDIN + "; the worker is a stand-in too, as the sim extra is not "
                                                             "installed here"),
              "versions": {k: ws[k] for k in ("biosteam", "thermosteam", "biorefineries")}}
    return {"fermos-vessel.json": {"worker": worker, "aerobic": ids["aerobic"], "anaerobic": ids["anaerobic"],
                                   "plantScale": VESSEL_PLANT_SCALE, "by": VESSEL_BY, "simulations": simulations,
                                   "scopes": scopes, "designs": designs}}


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
