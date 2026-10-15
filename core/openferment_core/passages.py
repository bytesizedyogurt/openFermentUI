"""The papers' own words, cut into passages and indexed (OF-BLD-014 §4.1).

A record is a value and one quoted sentence; the reasoning around it stays in
the paper. This module cuts every fetched paper into passages a search can
return and a reader can land on, and keeps them under `core/data/index/`:

    passages.jsonl   one passage per line, with the context it is indexed by
    manifest.json    per paper: the hash of its text file, its passage count,
                     the chunker version

    pnpm index:build         rebuilds the papers whose text changed
    pnpm index:build --all   rebuilds every paper

SOURCE. Every `core/data/fulltext/*.json` whose status is `complete`. A
curation note is never indexed: a passage is the paper's own text.

CUTTING. Prose sections split at sentence ends into passages of about
`CHUNK_TARGET` characters and at most `CHUNK_MAX`, each starting with the
last sentence of the one before. A table keeps its rows whole, and every
chunk of it starts with the table's heading and first row, so a row never
loses its column names. A figure caption is one passage; an abstract is one,
or two when it is long. The two lengths are conventions (E.1).

A passage's `start` and `end` are offsets into its section's text, and a
prose passage's text is exactly that slice. Its `context` (the paper's title,
year and the heading) is what it is indexed by beside its text, and is never
shown as the paper's words.

THE FIRST LANE, `bm25`, ranks passages by keyword over context and text, and
keeps the two refusals `Corpus.search` makes: a zero-scoring passage is never
returned, and a question of three or more terms whose best hit matches one
term alone returns nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from rank_bm25 import BM25Okapi

from . import atomic, intake
from .corpus import MIN_QUERY_TOKENS_FOR_COVERAGE, tokenize
from .models import Passage, RagLane, RagStatus

CHUNK_TARGET = 900
CHUNK_MAX = 1400
# Bumped whenever the cutting changes, so every paper is cut again.
CHUNKER_VERSION = "passages-1"


def index_dir() -> Path:
    """Read at call time, so a test that points `intake.DATA_DIR` elsewhere
    moves the index with it."""
    return intake.DATA_DIR / "index"


# ── sentences ──────────────────────────────────────────────────────────

# A sentence ends at . ! or ? followed by space and a capital letter, a digit
# or an opening bracket, unless the word before the stop is a single capital
# (E. coli, P. putida) or a common abbreviation.
_END = re.compile(r"(?<=[.!?])[)\]\"'’”]*\s+(?=[A-Z0-9(\[])")
_ABBREV = re.compile(
    r"(?:\b[A-Z]|\bet al|\be\.g|\bi\.e|\bFig|\bFigs|\bEq|\bRef|\bNo|\bapprox|\bca|\bvs|\bsp|\bspp|\bcf|\bSupp|\bTab)\.$"
)


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Spans that cover `text` end to end, one per sentence; trailing space
    belongs to the sentence before it."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _END.finditer(text):
        head = text[start : m.start()].rstrip()
        if _ABBREV.search(head):
            continue
        spans.append((start, m.end()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _hard_split(text: str, start: int, end: int, limit: int) -> list[tuple[int, int]]:
    """A span longer than `limit`, cut at the last whitespace before it."""
    out: list[tuple[int, int]] = []
    s = start
    while end - s > limit:
        cut = text.rfind(" ", s + 1, s + limit)
        cut = cut + 1 if cut > s else s + limit
        out.append((s, cut))
        s = cut
    out.append((s, end))
    return out


def prose_chunks(text: str, target: int = CHUNK_TARGET, limit: int = CHUNK_MAX) -> list[tuple[int, int]]:
    """Passages of `text` as spans: sentences gathered to about `target`
    characters, never more than `limit`, each passage beginning with the
    last sentence of the one before when that still fits."""
    units: list[tuple[int, int]] = []
    for s, e in sentence_spans(text):
        units += _hard_split(text, s, e, limit) if e - s > limit else [(s, e)]
    chunks: list[tuple[int, int]] = []
    n = len(units)
    i = 0
    overlap = False
    while i < n:
        first = i
        end = units[i][1]
        i += 1
        if overlap and i < n:
            # The repeated sentence never stands alone: the next one joins it
            # (the pair was checked to fit `limit` below).
            end = units[i][1]
            i += 1
        while i < n and units[i][1] - units[first][0] <= target:
            end = units[i][1]
            i += 1
        chunks.append((units[first][0], end))
        # Overlap: the next passage repeats this one's last sentence, when
        # this one held more than one and that sentence and the next fit.
        overlap = i < n and i - first > 1 and units[i][1] - units[i - 1][0] <= limit
        if overlap:
            i -= 1
    return [(s, e) for s, e in chunks if text[s:e].strip()]


# ── sections to passages ───────────────────────────────────────────────


def kind_of(section_id: str) -> str:
    if section_id == "abstract":
        return "abstract"
    if section_id.startswith("t"):
        return "table"
    if section_id.startswith("f"):
        return "figure"
    return "prose"


@dataclass
class Cut:
    passage: Passage
    context: str


def _abstract_chunks(text: str) -> list[tuple[int, int]]:
    if len(text) <= CHUNK_MAX:
        return [(0, len(text))]
    # Two halves, split at the sentence end nearest the middle.
    spans = sentence_spans(text)
    middle = len(text) / 2
    cut = min((e for _, e in spans[:-1]), key=lambda e: abs(e - middle), default=None)
    if cut is None:
        return _hard_split(text, 0, len(text), max(CHUNK_MAX, len(text) // 2 + 1))
    return [(0, cut), (cut, len(text))]


def _table_chunks(heading: str, text: str) -> list[tuple[str, int, int]]:
    """Rows kept whole; each chunk is the heading, the first row, then its
    rows. Offsets cover the chunk's own rows in the section text."""
    lines = text.split("\n")
    if not lines:
        return []
    starts = []
    pos = 0
    for line in lines:
        starts.append(pos)
        pos += len(line) + 1
    header = lines[0]
    lead = f"{heading}\n{header}"
    out: list[tuple[str, int, int]] = []
    i = 1
    if len(lines) == 1:
        return [(lead, 0, len(text))]
    while i < len(lines):
        first = i
        size = len(lead)
        while i < len(lines) and (i == first or size + 1 + len(lines[i]) <= CHUNK_TARGET):
            size += 1 + len(lines[i])
            i += 1
        rows = lines[first:i]
        start = starts[first] if first > 1 else 0
        end = starts[i - 1] + len(lines[i - 1])
        out.append((lead + "\n" + "\n".join(rows), start, end))
    return out


def cut_section(paper_id: str, section: dict[str, Any], context_head: str) -> list[Cut]:
    sid = section["id"]
    heading = section.get("heading") or ""
    text = section.get("text") or ""
    if not text.strip():
        return []
    kind = kind_of(sid)
    context = f"{context_head} — {heading}" if heading else context_head
    pieces: list[tuple[str, int, int]]
    if kind == "table":
        pieces = _table_chunks(heading, text)
    elif kind == "figure":
        pieces = [(text, 0, len(text))]
    elif kind == "abstract":
        pieces = [(text[s:e], s, e) for s, e in _abstract_chunks(text)]
    else:
        pieces = [(text[s:e], s, e) for s, e in prose_chunks(text)]
    return [
        Cut(
            Passage(id=f"{paper_id}:{sid}:{n}", paperId=paper_id, sectionId=sid, heading=heading, kind=kind, text=body, start=s, end=e),
            context,
        )
        for n, (body, s, e) in enumerate(pieces)
        if body.strip()
    ]


def cut_paper(paper_id: str, sections: Iterable[dict[str, Any]], title: str = "", year: Any = None) -> list[Cut]:
    head = " ".join(x for x in (title or "", f"({year})" if year else "") if x).strip() or paper_id
    out: list[Cut] = []
    for section in sections:
        out += cut_section(paper_id, section, head)
    return out


# ── the index on disk ──────────────────────────────────────────────────


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _papers_meta() -> dict[str, dict[str, Any]]:
    try:
        from .corpus import load_corpus

        return load_corpus().papers_by_id
    except FileNotFoundError:
        return {}


def read_manifest() -> dict[str, Any]:
    try:
        return json.loads((index_dir() / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"chunker": None, "papers": {}}


def read_index() -> list[Cut]:
    path = index_dir() / "passages.jsonl"
    if not path.exists():
        return []
    out: list[Cut] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        context = row.pop("context", "")
        out.append(Cut(Passage.model_validate(row), context))
    return out


def build(*, everything: bool = False) -> dict[str, Any]:
    """Bring the index up to date with the fetched text. Returns what it did:
    `{"rebuilt": [...], "kept": [...], "dropped": [...], "papers", "passages"}`."""
    manifest = read_manifest()
    same_chunker = manifest.get("chunker") == CHUNKER_VERSION and not everything
    old_papers: dict[str, Any] = manifest.get("papers", {}) if same_chunker else {}
    existing: dict[str, list[Cut]] = {}
    if same_chunker:
        for c in read_index():
            existing.setdefault(c.passage.paperId, []).append(c)

    meta = _papers_meta()
    papers: dict[str, Any] = {}
    cuts: list[Cut] = []
    rebuilt: list[str] = []
    kept: list[str] = []
    for path in sorted(intake.FULLTEXT_DIR.glob("*.json")) if intake.FULLTEXT_DIR.exists() else []:
        pid = path.stem
        try:
            fetched = intake.cached(pid)
        except ValueError:
            continue
        if fetched is None or fetched.status != "complete":
            continue
        digest = _file_hash(path)
        if pid in old_papers and old_papers[pid].get("hash") == digest and pid in existing:
            mine = existing[pid]
            kept.append(pid)
        else:
            p = meta.get(pid, {})
            mine = cut_paper(pid, [s.model_dump() for s in fetched.sections], p.get("title", ""), p.get("year"))
            rebuilt.append(pid)
        papers[pid] = {"hash": digest, "passages": len(mine)}
        cuts += mine

    dropped = sorted(set(old_papers) - set(papers))
    lines = [json.dumps(c.passage.model_dump() | {"context": c.context}, ensure_ascii=False) for c in cuts]
    atomic.write_text(index_dir() / "passages.jsonl", "\n".join(lines) + ("\n" if lines else ""))
    atomic.write_text(
        index_dir() / "manifest.json",
        json.dumps({"chunker": CHUNKER_VERSION, "papers": papers}, indent=2, sort_keys=True) + "\n",
    )
    return {"rebuilt": rebuilt, "kept": kept, "dropped": dropped, "papers": len(papers), "passages": len(cuts)}


def manifest_hash() -> str:
    path = index_dir() / "manifest.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else ""


# ── the bm25 lane ──────────────────────────────────────────────────────


@dataclass
class Scored:
    passage: Passage
    score: float
    matched: list[str]


class Bm25Index:
    def __init__(self, cuts: list[Cut]):
        self.cuts = cuts
        self.by_id = {c.passage.id: c for c in cuts}
        docs = [tokenize(f"{c.context} {c.passage.text}") for c in cuts]
        self._tokens = [frozenset(d) for d in docs]
        self._bm25 = BM25Okapi(docs) if docs else None

    def search(self, question: str, k: int = 8) -> list[Scored]:
        tokens = tokenize(question)
        if not tokens or self._bm25 is None:
            return []
        unique = set(tokens)
        scores = self._bm25.get_scores(tokens)
        order = sorted(range(len(self.cuts)), key=lambda n: (-scores[n], n))
        hits: list[Scored] = []
        for n in order[: max(k, 0)]:
            if scores[n] <= 0:
                break
            hits.append(Scored(self.cuts[n].passage, round(float(scores[n]), 4), sorted(unique & self._tokens[n])))
        if hits and len(unique) >= MIN_QUERY_TOKENS_FOR_COVERAGE and len(hits[0].matched) < 2:
            return []
        return hits


_LOADED: tuple[str, Bm25Index] | None = None


def bm25_index() -> Bm25Index:
    """The bm25 lane over the index on disk, rebuilt in memory when the
    manifest changes."""
    global _LOADED
    key = manifest_hash()
    if _LOADED is None or _LOADED[0] != key:
        _LOADED = (key, Bm25Index(read_index()))
    return _LOADED[1]


# ── status ─────────────────────────────────────────────────────────────


def chosen_lane() -> str:
    """The lane `core/data/index/config.json` names, else `bm25`."""
    try:
        lane = json.loads((index_dir() / "config.json").read_text(encoding="utf-8")).get("lane")
    except (FileNotFoundError, ValueError):
        lane = None
    return lane if isinstance(lane, str) and lane else "bm25"


def _lanes() -> list[RagLane]:
    from . import retrieve

    return retrieve.lanes()


def status() -> RagStatus:
    manifest = read_manifest()
    papers = manifest.get("papers", {}) if manifest.get("chunker") == CHUNKER_VERSION else {}
    return RagStatus(
        papersIndexed=len(papers),
        passages=sum(int(p.get("passages", 0)) for p in papers.values()),
        lanes=_lanes(),
        chosenLane=chosen_lane(),
    )


# ── the command ────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    unknown = [a for a in argv if a not in ("--all", "--dense")]
    if unknown:
        print("usage: python -m openferment_core.passages [--all] [--dense]")
        return 2
    did = build(everything="--all" in argv)
    print(
        f"index: {did['papers']} papers, {did['passages']} passages · "
        f"{len(did['rebuilt'])} cut, {len(did['kept'])} unchanged, {len(did['dropped'])} dropped"
    )
    if "--dense" in argv:
        try:
            from . import embed
        except ImportError:
            print("dense vectors: not built here; the meaning lane arrives with OF-BLD-014 §4.2")
            return 0
        return embed.main_dense()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
