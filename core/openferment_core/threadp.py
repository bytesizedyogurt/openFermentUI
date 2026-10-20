"""Program threads proposed by a fixed rule, written on a named person's
approval: thread P (OF-BLD-014 §2.3) and thread Q.

PHA from waste cellulosic sugars is the platform's second program, thread P;
ethanol from glucose by wild-type Saccharomyces cerevisiae is its third,
thread Q. Their papers are not curated by hand. A rule asks Europe PMC, orders
what comes back, and writes a proposal file; a person reads it, marks the rows
they approve, and `apply` writes those rows, and only those, into the
thread's seed file (`src/data/corpus/threadP.ts`, `threadQ.ts`). This is the
second sanctioned way into `src/data/corpus/`, after the approved DOIs of
`identifiers.py`, and it follows the same pattern: a machine proposes, a
person approves.

    pnpm thread:propose                                       # LIVE, no key
    pnpm thread:apply <file.tsv> --approved-by "<name>"
    pnpm thread:propose:q                                     # thread Q, LIVE
    pnpm thread:apply:q <file.tsv> --approved-by "<name>"

Everything one thread's rule holds is in its `ThreadRule`, `THREAD_P` or
`THREAD_Q`, and every function here takes the rule it works under, thread P's
when none is named. The module-level names (`QUERY`, `SEED_FILE`, …) are
thread P's.

The rule (every constant in a `ThreadRule` is a selection convention, never a
result):

- one search, `query`, `resultType=core`, `page_size` results, ordered by
  citations;
- keep a result with a PMCID, `isOpenAccess` equal to `Y`, a publication year
  of `min_year` or later, and a licence that starts with `cc`;
- order the kept results by `citedByCount`: the first `propose_research`
  research articles and the first `propose_reviews` reviews are `PROPOSE`,
  the rest `REVIEW`;
- every id in the thread's include file is looked up and is `INCLUDE`
  whatever the rule says; one with no open-access text is catalogued with
  `openAccess: false`.

`PROPOSE` is this module's opinion. `apply` writes `APPROVED` and `INCLUDE`
rows alone, and refuses a reviewer name `biorepo.write` would refuse.

An entry holds what its source returned and nothing else: no organism, no
topic, no number. Its one section says nobody has read it. The licence stays
out of the seed: the overlay sets it when the text is fetched.

Thread Q's include file may also name a source Europe PMC does not hold:
`osti:<id>`, a report on OSTI, and `sgd:<id>`, a strain entry in the
Saccharomyces Genome Database. Each is looked up at its source and written
with the address Intake fetches its text from, `sourceUrl`: a report as an
industry report, a strain entry as a database entry. A strain entry carries
no PMCID, DOI or PMID, and its address is the identifier it is kept by.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from . import atomic
from .biorepo import MIN_REVIEWER_CHARS, PLACEHOLDER_REVIEWERS

_CORE = Path(__file__).parent.parent
ROOT = _CORE.parent

# ── the rules ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ThreadRule:
    """Everything that makes one thread's rule its own. The rest of this
    module is shared by every thread."""

    letter: str
    query: str
    page_size: int
    sort: str
    min_year: int
    propose_research: int
    propose_reviews: int
    seed_file: Path
    proposals: Path
    include_file: Path
    header: str
    catalogued_sentence: str
    # The names the seed file exports: the paper list and the empty record list.
    papers_name: str
    records_name: str
    # Every id apply writes, as a pattern: the letter, then the next number.
    id_pattern: str
    # Whether the include file may name a source outside Europe PMC
    # (`osti:<id>`, `sgd:<id>`), written with the address Intake fetches it from.
    named_sources: bool = False


SEED_FILE = ROOT / "src" / "data" / "corpus" / "threadP.ts"
PROPOSALS = _CORE / "data" / "thread-p-proposed.tsv"
INCLUDE_FILE = ROOT / "docs" / "thread-p-include.txt"

# Both term groups are held to title and abstract (Sean Creighton, 14 October
# 2026): matched anywhere in the full text, "PHA" also names phytohemagglutinin
# and most of what came back was off-topic (STATE.md, §2.4 the proposal).
QUERY = (
    'TITLE_ABS:(polyhydroxyalkanoate* OR polyhydroxybutyrate* OR "PHA" OR "PHB") AND '
    'TITLE_ABS:(lignocellulos* OR hydrolysate OR "waste paper" OR "paper sludge" OR "textile waste" '
    "OR cotton OR xylose OR cellulosic) AND OPEN_ACCESS:y AND HAS_FT:y"
)
PAGE_SIZE = 100
SORT = "CITED desc"
MIN_YEAR = 2012
PROPOSE_RESEARCH = 30
PROPOSE_REVIEWS = 5

CATALOGUED_SENTENCE = (
    "Catalogued on {date} by the thread P selection rule from Europe PMC metadata. "
    "No curator has read this paper. Fetch its full text in Intake to read it."
)

HEADER = """// openFerment corpus — Thread P: PHA from waste cellulosic sugars, program two
// (OF-BLD-014 Phase 2).
//
// THE PAPER LIST IS WRITTEN BY A SCRIPT. `pnpm thread:apply` (OF-BLD-014 §2.3)
// writes THREAD_P_PAPERS from the rows of `core/data/thread-p-proposed.tsv`
// that a named person approved, filled from Europe PMC's metadata and from
// nothing else. Do not edit the list by hand.
//
// THE RECORD LIST IS EMPTY BY DESIGN. No curator reads these papers. Every
// number about a thread P paper arrives through Intake — fetched full text,
// an anchored extraction candidate — and a Guild decision. A record typed
// here would be a quantity that bypassed both.
"""

THREAD_P = ThreadRule(
    letter="P",
    query=QUERY,
    page_size=PAGE_SIZE,
    sort=SORT,
    min_year=MIN_YEAR,
    propose_research=PROPOSE_RESEARCH,
    propose_reviews=PROPOSE_REVIEWS,
    seed_file=SEED_FILE,
    proposals=PROPOSALS,
    include_file=INCLUDE_FILE,
    header=HEADER,
    catalogued_sentence=CATALOGUED_SENTENCE,
    papers_name="THREAD_P_PAPERS",
    records_name="THREAD_P_RECORDS",
    id_pattern=r"P\d+",
)

# Thread Q (Sean Creighton, 20 October 2026): wild-type S. cerevisiae making
# ethanol from glucose in batch, and the kinetics that describe it. Four term
# groups, each held to title and abstract as thread P's are: the organism, the
# product, a kinetic word, and the substrate or the mode.
THREAD_Q = ThreadRule(
    letter="Q",
    query=(
        'TITLE_ABS:("Saccharomyces cerevisiae" OR "S. cerevisiae" OR yeast) AND '
        'TITLE_ABS:(ethanol OR bioethanol OR "alcoholic fermentation") AND '
        'TITLE_ABS:(Monod OR Luedeking OR "kinetic model" OR "kinetic models" OR "kinetic modeling" '
        'OR "kinetic modelling" OR "kinetic parameters" OR "unstructured model" OR "ethanol inhibition" '
        'OR "product inhibition" OR "substrate inhibition" OR "maximum specific growth rate" '
        'OR "growth kinetics" OR "fermentation kinetics") AND '
        "TITLE_ABS:(glucose OR batch) AND OPEN_ACCESS:y AND HAS_FT:y"
    ),
    page_size=100,
    sort="CITED desc",
    min_year=2005,
    propose_research=20,
    propose_reviews=3,
    seed_file=ROOT / "src" / "data" / "corpus" / "threadQ.ts",
    proposals=_CORE / "data" / "thread-q-proposed.tsv",
    include_file=ROOT / "docs" / "thread-q-include.txt",
    header="""// openFerment corpus — Thread Q: ethanol from glucose by wild-type Saccharomyces
// cerevisiae, program three.
//
// THE PAPER LIST IS WRITTEN BY A SCRIPT. `pnpm thread:apply:q` writes
// THREAD_Q_PAPERS from the rows of `core/data/thread-q-proposed.tsv` that a
// named person approved, and from the sources `docs/thread-q-include.txt`
// names, filled from the metadata Europe PMC, OSTI or the Saccharomyces Genome
// Database returned and from nothing else. Do not edit the list by hand.
//
// THE RECORD LIST IS EMPTY BY DESIGN. No curator reads these papers. Every
// number about a thread Q paper arrives through Intake — fetched full text,
// an anchored extraction candidate — and a Guild decision. A record typed
// here would be a quantity that bypassed both.
""",
    catalogued_sentence=(
        "Catalogued on {date} by the thread Q selection rule from its source's metadata. "
        "No curator has read this entry. Fetch its full text in Intake to read it."
    ),
    papers_name="THREAD_Q_PAPERS",
    records_name="THREAD_Q_RECORDS",
    id_pattern=r"Q\d+",
    named_sources=True,
)

THREADS = {rule.letter: rule for rule in (THREAD_P, THREAD_Q)}

# The fields of a search result this module reads. The first live call checks
# them, and a missing one stops the run: they were not confirmed when the
# document was written (§2.3).
REQUIRED_KEYS = ("pmcid", "isOpenAccess", "pubYear", "license", "citedByCount", "authorString", "journalInfo", "pubTypeList")

VERDICTS = ("PROPOSE", "REVIEW", "INCLUDE", "APPROVED")
# `sourceUrl` is last, so a proposal file written before it existed still
# reads: its rows have none.
COLUMNS = (
    "verdict", "id", "pmcid", "doi", "pmid", "openAccess", "year", "journal", "title",
    "firstAuthor", "licence", "citations", "publicationType", "authors", "sourceUrl",
)

# The two sources outside Europe PMC a thread may name, as the address apply
# writes for each and the source type it writes it as. Intake fetches a
# report's PDF from the first and a strain entry's JSON from the second.
OSTI_API = "https://www.osti.gov/api/v1/records"
OSTI_PURL = "https://www.osti.gov/servlets/purl"
SGD_STRAIN = "https://www.yeastgenome.org/backend/strain"
SGD_VENUE = "Saccharomyces Genome Database"
_OSTI_AFFIX = re.compile(r"\s*(\[[^\]]*\]|\(ORCID:[^)]*\))")
_NAMED = {
    "osti": (re.compile(re.escape(OSTI_PURL) + r"/\d+"), "industry-report"),
    "sgd": (re.compile(re.escape(SGD_STRAIN) + r"/S\d{9}"), "database-entry"),
}


class ThreadRefused(RuntimeError):
    """Apply would write something no person approved, or no person approved it."""


# Its name from when thread P was the only thread; the tests and the script read it.
ThreadPRefused = ThreadRefused


class MissingKeys(RuntimeError):
    """A search result lacks a field the rule reads (§2.3: stop)."""


class LookupFailed(RuntimeError):
    """A source a person named in an include file holds no record under that id."""


@dataclass
class Row:
    verdict: str
    id: str = ""
    pmcid: str = ""
    doi: str = ""
    pmid: str = ""
    openAccess: bool = False
    year: int | None = None
    journal: str = ""
    title: str = ""
    firstAuthor: str = ""
    licence: str = ""
    citations: int | None = None
    publicationType: str = ""
    authors: list[str] = field(default_factory=list)
    # Where Intake fetches the text of a source outside Europe PMC (thread Q).
    sourceUrl: str = ""


# ── reading a result ───────────────────────────────────────────────────

Search = Callable[[str, int], list[dict[str, Any]]]


def check_keys(result: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in result]
    if missing:
        raise MissingKeys(
            "Europe PMC's search result lacks " + ", ".join(missing)
            + ". OF-BLD-014 §2.3 reads these by name; stop and report (A.5)."
        )


def pub_types(result: dict[str, Any]) -> list[str]:
    types = (result.get("pubTypeList") or {}).get("pubType") or []
    return [types] if isinstance(types, str) else [str(t) for t in types]


def is_review(result: dict[str, Any]) -> bool:
    return any("review" in t.lower() for t in pub_types(result))


def is_research(result: dict[str, Any]) -> bool:
    """A research article: typed as one, or as a journal article, and not a
    review. An editorial, a letter or a correction is neither."""
    types = [t.lower() for t in pub_types(result)]
    return not is_review(result) and ("research-article" in types or "journal article" in types)


def publication_type(result: dict[str, Any]) -> str:
    """One word for the TSV: review, research-article, or the first type
    that is not a funding note ("Research Support, …" says who paid)."""
    if is_review(result):
        return "review"
    if is_research(result):
        return "research-article"
    types = [t for t in pub_types(result) if not t.lower().startswith("research support")]
    return types[0] if types else ""


def authors_of(result: dict[str, Any]) -> list[str]:
    raw = str(result.get("authorString") or "").strip().rstrip(".")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _year(result: dict[str, Any]) -> int | None:
    try:
        return int(str(result.get("pubYear") or "").strip())
    except ValueError:
        return None


def _citations(result: dict[str, Any]) -> int:
    try:
        return int(result.get("citedByCount") or 0)
    except (TypeError, ValueError):
        return 0


def row_of(result: dict[str, Any], verdict: str) -> Row:
    authors = authors_of(result)
    return Row(
        verdict=verdict,
        pmcid=str(result.get("pmcid") or "").strip(),
        doi=str(result.get("doi") or "").strip(),
        pmid=str(result.get("pmid") or "").strip(),
        openAccess=result.get("isOpenAccess") == "Y" and bool(str(result.get("pmcid") or "").strip()),
        year=_year(result),
        journal=str(((result.get("journalInfo") or {}).get("journal") or {}).get("title") or "").strip(),
        title=_plain(str(result.get("title") or "")),
        firstAuthor=authors[0] if authors else "",
        licence=str(result.get("license") or "").strip(),
        citations=_citations(result),
        publicationType=publication_type(result),
        authors=authors,
    )


_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _plain(text: str) -> str:
    """A title as words: Europe PMC writes italics as <i>…</i>."""
    return re.sub(r"\s+", " ", _TAG.sub("", text)).strip().rstrip(".")


def eligible(result: dict[str, Any], rule: ThreadRule = THREAD_P) -> bool:
    year = _year(result)
    return (
        bool(str(result.get("pmcid") or "").strip())
        and result.get("isOpenAccess") == "Y"
        and year is not None
        and year >= rule.min_year
        and str(result.get("license") or "").strip().lower().startswith("cc")
    )


def named_source(url: str) -> str | None:
    """'osti' or 'sgd' when `url` is an address apply writes for a named
    source, exactly as it writes it; None for anything else."""
    for kind, (pattern, _) in _NAMED.items():
        if pattern.fullmatch(url or ""):
            return kind
    return None


# ── propose ────────────────────────────────────────────────────────────


def propose(
    results: Sequence[dict[str, Any]],
    includes: Sequence[dict[str, Any] | str | Row] = (),
    seeded: dict[str, str] | None = None,
    rule: ThreadRule = THREAD_P,
) -> list[Row]:
    """The proposal, from one page of search results and the include list.

    `includes` holds, for each id in the include file, the search result that
    id resolved to, the bare id when Europe PMC knew no open-access text for
    it, or the row `lookup` built for a source outside Europe PMC. `seeded`
    maps a PMCID, DOI or source address already in the seed file to its paper
    id, so a paper keeps its id across runs.
    """
    if results:
        check_keys(results[0])
    seeded = seeded or {}
    kept = sorted((r for r in results if eligible(r, rule)), key=_citations, reverse=True)
    research = reviews = 0
    rows: list[Row] = []
    seen: set[str] = set()

    for inc in includes:
        if isinstance(inc, Row):
            row = inc
        elif isinstance(inc, str):
            # Europe PMC holds no open-access text for it: catalogued closed,
            # under the kind of identifier it is.
            key = inc.strip()
            row = Row(verdict="INCLUDE", openAccess=False)
            if key.upper().startswith("PMC"):
                row.pmcid = key.upper()
            elif key.isdigit():
                row.pmid = key
            else:
                row.doi = key
        else:
            row = row_of(inc, "INCLUDE")
        rows.append(row)
        seen.update(k.lower() for k in (row.pmcid, row.doi, row.pmid, row.sourceUrl) if k)

    for r in kept:
        keys = {k.lower() for k in (str(r.get("pmcid") or ""), str(r.get("doi") or "")) if k}
        if keys & seen:
            continue
        seen |= keys
        if is_review(r):
            verdict = "PROPOSE" if reviews < rule.propose_reviews else "REVIEW"
            reviews += 1
        elif is_research(r):
            verdict = "PROPOSE" if research < rule.propose_research else "REVIEW"
            research += 1
        else:
            verdict = "REVIEW"
        rows.append(row_of(r, verdict))

    for row in rows:
        row.id = next((seeded[k.lower()] for k in (row.pmcid, row.doi, row.sourceUrl) if k and k.lower() in seeded), "")
    return rows


def read_includes(path: Path | None = None, rule: ThreadRule = THREAD_P) -> list[str]:
    path = path or rule.include_file
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def to_tsv(rows: Iterable[Row]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow([
            r.verdict, r.id, r.pmcid, r.doi, r.pmid, "Y" if r.openAccess else "N", "" if r.year is None else r.year, r.journal, r.title,
            r.firstAuthor, r.licence, "" if r.citations is None else r.citations, r.publicationType,
            "; ".join(r.authors), r.sourceUrl,
        ])
    return out.getvalue()


def from_tsv(text: str) -> list[Row]:
    rows: list[Row] = []
    for raw in csv.DictReader(io.StringIO(text), delimiter="\t"):
        def cell(name: str) -> str:
            return (raw.get(name) or "").strip()
        rows.append(Row(
            verdict=cell("verdict").upper(),
            id=cell("id"),
            pmcid=cell("pmcid"),
            doi=cell("doi"),
            pmid=cell("pmid"),
            openAccess=cell("openAccess").upper() == "Y",
            year=int(cell("year")) if cell("year").isdigit() else None,
            journal=cell("journal"),
            title=cell("title"),
            firstAuthor=cell("firstAuthor"),
            licence=cell("licence"),
            citations=int(cell("citations")) if cell("citations").isdigit() else None,
            publicationType=cell("publicationType"),
            authors=[a.strip() for a in cell("authors").split(";") if a.strip()],
            sourceUrl=cell("sourceUrl"),
        ))
    return rows


# ── the seed file ──────────────────────────────────────────────────────

BEGIN = "  // ── written by pnpm thread:apply; one approval line, then one paper ──"
END = "  // ── end of the papers thread:apply wrote ──"


def _approval(rule: ThreadRule) -> re.Pattern[str]:
    return re.compile(rf"^  // ({rule.id_pattern}) · approved by (.+) on (\d{{4}}-\d{{2}}-\d{{2}}) · (\S+)$")


_APPROVAL = _approval(THREAD_P)


@dataclass
class Entry:
    paper: dict[str, Any]
    approvedBy: str
    approvedOn: str
    verdict: str


def read_seed(path: Path | None = None, rule: ThreadRule = THREAD_P) -> list[Entry]:
    """The entries an earlier apply wrote, in file order."""
    path = path or rule.seed_file
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if BEGIN not in lines:
        return []
    approval = _approval(rule)
    out: list[Entry] = []
    pending: tuple[str, str, str] | None = None
    for line in lines[lines.index(BEGIN) + 1:]:
        if line == END:
            break
        m = approval.match(line)
        if m:
            pending = (m.group(2), m.group(3), m.group(4))
            continue
        if line.startswith("  {") and line.endswith("},") and pending:
            paper = json.loads(line.strip()[:-1])
            out.append(Entry(paper, *pending))
            pending = None
    return out


def seeded_ids(entries: Sequence[Entry]) -> dict[str, str]:
    out: dict[str, str] = {}
    for e in entries:
        for k in (e.paper.get("pmcid"), e.paper.get("doi"), e.paper.get("pmid"), e.paper.get("sourceUrl")):
            if k:
                out[str(k).lower()] = e.paper["id"]
    return out


def _source_type(row: Row, rule: ThreadRule) -> str:
    """A named source is the type its address says; anything else is a
    review or a journal article, as Europe PMC typed it."""
    kind = named_source(row.sourceUrl) if rule.named_sources else None
    if kind:
        return _NAMED[kind][1]
    return "review" if row.publicationType == "review" else "journal-article"


def paper_of(row: Row, paper_id: str, on: str, rule: ThreadRule = THREAD_P) -> dict[str, Any]:
    sentence = rule.catalogued_sentence.format(date=on)
    paper: dict[str, Any] = {
        "id": paper_id,
        "title": row.title or (row.pmcid or row.doi or row.pmid or row.sourceUrl),
        "authors": row.authors,
        "year": row.year if row.year is not None else 0,
        "venue": row.journal,
        "organisms": [],
        "topics": [],
        "abstract": sentence,
        "sections": [{"id": f"{paper_id}-s1", "heading": "Catalogue note", "text": sentence}],
        "ingest": "catalogued",
        "thread": rule.letter,
        "sourceType": _source_type(row, rule),
        "textSource": "curation-note",
        "openAccess": row.openAccess,
        "tranche": 1,
    }
    if row.doi:
        paper["doi"] = row.doi
    if row.pmcid:
        paper["pmcid"] = row.pmcid
    if row.pmid:
        paper["pmid"] = row.pmid
    if row.sourceUrl and rule.named_sources:
        paper["sourceUrl"] = row.sourceUrl
    if not row.title or row.year is None or not row.authors:
        paper["verifyNeeded"] = True
    return paper


def _fixed(rule: ThreadRule) -> dict[str, Any]:
    return {
        "organisms": [], "topics": [], "ingest": "catalogued", "thread": rule.letter,
        "textSource": "curation-note", "tranche": 1,
    }


_FIXED = _fixed(THREAD_P)
_KEYS = {
    "id", "title", "authors", "year", "venue", "organisms", "topics", "abstract", "sections",
    "ingest", "thread", "sourceType", "textSource", "openAccess", "tranche",
    "doi", "pmcid", "pmid", "verifyNeeded",
}


def seed_problems(entries: Sequence[Entry], rule: ThreadRule = THREAD_P) -> list[str]:
    """What, in the seed file, apply could not have written. Apply writes no
    organism, topic, licence or record, one fixed sentence dated the day of
    its approval, the source type its row decides, a source address only for
    a thread that names sources and only in the shape it writes one, and an
    approver `biorepo.write` would accept; anything else is a hand edit
    (OF-BLD-014 §2.R)."""
    keys = _KEYS | {"sourceUrl"} if rule.named_sources else _KEYS
    out: list[str] = []
    for n, e in enumerate(entries, 1):
        p = e.paper
        pid = str(p.get("id", f"entry {n}"))
        if not re.fullmatch(rule.id_pattern, pid):
            out.append(f"{pid}: an id apply does not write")
        extra = set(p) - keys
        if extra:
            out.append(f"{pid}: fields apply never writes ({', '.join(sorted(extra))})")
        for k, v in _fixed(rule).items():
            if p.get(k) != v:
                out.append(f"{pid}: {k} is {p.get(k)!r}, and apply writes {v!r}")
        sentence = rule.catalogued_sentence.format(date=e.approvedOn)
        if p.get("abstract") != sentence or p.get("sections") != [
            {"id": f"{pid}-s1", "heading": "Catalogue note", "text": sentence}
        ]:
            out.append(f"{pid}: the abstract or section is not the catalogue sentence of {e.approvedOn}")
        url = p.get("sourceUrl")
        kind = named_source(url) if isinstance(url, str) else None
        if url is not None and kind is None:
            out.append(f"{pid}: sourceUrl {url!r} is not an address apply writes")
        expected = {_NAMED[kind][1]} if kind else {"review", "journal-article"}
        if p.get("sourceType") not in expected:
            out.append(f"{pid}: sourceType is {p.get('sourceType')!r}, and apply writes {' or '.join(sorted(expected))}")
        refusal = reviewer_refusal(e.approvedBy)
        if refusal:
            out.append(f"{pid}: approver {e.approvedBy!r} — {refusal}")
        if e.verdict not in ("APPROVED", "INCLUDE"):
            out.append(f"{pid}: verdict {e.verdict}, and apply writes APPROVED or INCLUDE")
    return out


def reviewer_refusal(name: str) -> str | None:
    """The reviewer-name rule `biorepo.write` applies, word for word."""
    if any(ch.isspace() and ch != " " for ch in (name or "")) or any(not ch.isprintable() for ch in (name or "")):
        # The name is written into a comment line of the seed file; a line
        # break in it would end the comment and start code.
        return "a name is one line of plain text"
    name = (name or "").strip()
    if not name:
        return "an approval needs a name; an empty name is nobody approving"
    if len(name) < MIN_REVIEWER_CHARS or name.lower() in PLACEHOLDER_REVIEWERS:
        return f"{name!r} is a placeholder, not a person"
    return None


def _row_refusal(r: Row, rule: ThreadRule) -> str | None:
    """Why apply will not write this chosen row, or None."""
    if r.verdict == "APPROVED" and not (r.pmcid and r.openAccess):
        return (
            f"row {r.doi or r.title or '(blank)'} is APPROVED with no PMCID; only an INCLUDE row "
            "may be catalogued without open-access text"
        )
    if r.sourceUrl and not rule.named_sources:
        return (
            f"row {r.title or '(blank)'} carries a sourceUrl; thread {rule.letter} names its papers "
            "by PMCID, DOI or PMID"
        )
    if r.sourceUrl and named_source(r.sourceUrl) is None:
        return (
            f"row {r.title or '(blank)'} has sourceUrl {r.sourceUrl!r}, which is neither an OSTI report "
            f"({OSTI_PURL}/<id>) nor an SGD strain entry ({SGD_STRAIN}/<id>); Intake reads no other source"
        )
    if not (r.pmcid or r.doi or r.pmid or r.sourceUrl):
        what = "PMCID, DOI, PMID or source address" if rule.named_sources else "PMCID, DOI or PMID"
        return f"row {r.title or '(blank)'} names no {what}"
    return None


def apply(
    rows: Sequence[Row],
    approved_by: str,
    *,
    seed: Path | None = None,
    on: str | None = None,
    types_import: str = "../types",
    rule: ThreadRule = THREAD_P,
) -> list[str]:
    """Write every APPROVED or INCLUDE row into the seed file and return one
    line per paper added. A paper already in the file keeps its id and its
    entry; a new one takes the next free id, the thread's letter and a
    number, in file order."""
    refusal = reviewer_refusal(approved_by)
    if refusal:
        raise ThreadRefused(refusal)
    chosen = [r for r in rows if r.verdict in ("APPROVED", "INCLUDE")]
    for r in chosen:
        refusal = _row_refusal(r, rule)
        if refusal:
            raise ThreadRefused(refusal)
    seed = seed or rule.seed_file
    on = on or date.today().isoformat()
    entries = read_seed(seed, rule)
    problems = seed_problems(entries, rule)
    if problems:
        raise ThreadRefused(f"{seed.name} holds what apply never writes: " + "; ".join(problems))
    known = seeded_ids(entries)
    next_n = 1 + max((int(e.paper["id"][len(rule.letter):]) for e in entries), default=0)
    added: list[str] = []
    for r in chosen:
        keys = [k for k in (r.pmcid, r.doi, r.pmid, r.sourceUrl) if k]
        if any(known.get(k.lower()) for k in keys):
            continue
        pid = f"{rule.letter}{next_n}"
        next_n += 1
        entries.append(Entry(paper_of(r, pid, on, rule), approved_by.strip(), on, r.verdict))
        for k in keys:
            known[k.lower()] = pid
        added.append(f"{pid}  {r.verdict:8} {r.pmcid or r.doi or r.pmid or r.sourceUrl}  {r.title[:70]}")
    atomic.write_text(seed, render(entries, types_import, rule))
    return added


def render(entries: Sequence[Entry], types_import: str = "../types", rule: ThreadRule = THREAD_P) -> str:
    lines = [rule.header.rstrip("\n"), f"import type {{ ExtractionRecord, Paper }} from '{types_import}';", ""]
    if not entries:
        lines.append(f"export const {rule.papers_name}: Paper[] = [];")
    else:
        lines.append(f"export const {rule.papers_name}: Paper[] = [")
        lines.append(BEGIN)
        for e in entries:
            lines.append(f"  // {e.paper['id']} · approved by {e.approvedBy} on {e.approvedOn} · {e.verdict}")
            lines.append("  " + json.dumps(e.paper, ensure_ascii=False) + ",")
        lines.append(END)
        lines.append("];")
    lines.append("")
    lines.append(f"export const {rule.records_name}: ExtractionRecord[] = [];")
    return "\n".join(lines) + "\n"


# ── the network ────────────────────────────────────────────────────────


def search(query: str | None = None, page_size: int | None = None, rule: ThreadRule = THREAD_P) -> list[dict[str, Any]]:
    """One page of Europe PMC's search, ordered by citations. LIVE, no key."""
    from . import intake

    response = intake._get(
        f"{intake.EUROPE_PMC}/search",
        {
            "query": query or rule.query, "format": "json", "resultType": "core",
            "pageSize": str(page_size or rule.page_size), "sort": rule.sort,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Europe PMC answered {response.status_code} to the thread {rule.letter} search")
    return list(response.json().get("resultList", {}).get("result", []))


def lookup(identifier: str, rule: ThreadRule = THREAD_P) -> dict[str, Any] | str | Row:
    """An include-file id as its source knows it. A PMCID, DOI or PMID is
    asked of Europe PMC and answers its search result, or the id itself when
    Europe PMC holds no open-access text for it. `osti:<id>` and `sgd:<id>`,
    which only a thread that names sources reads, answer the row their
    source's record fills; a source with no record under the id stops the
    run, because a person named it."""
    key = identifier.strip()
    prefix, _, rest = key.partition(":")
    if prefix.lower() in _NAMED:
        if not rule.named_sources:
            raise LookupFailed(
                f"thread {rule.letter}'s include file takes a PMCID, DOI or PMID; {key} names a source "
                "only a thread that names sources reads"
            )
        return lookup_osti(rest.strip()) if prefix.lower() == "osti" else lookup_sgd(rest.strip())
    if key.upper().startswith("PMC"):
        query = f"PMCID:{key.upper()}"
    elif key.isdigit():
        query = f"EXT_ID:{key} AND SRC:MED"
    else:
        query = f'DOI:"{key}"'
    for hit in search(query, 5, rule):
        if hit.get("isOpenAccess") == "Y" and hit.get("pmcid"):
            return hit
    return key


def lookup_osti(osti_id: str) -> Row:
    """A report on OSTI as its records API describes it: title, authors,
    publication date, report number and DOI, each as OSTI wrote it. The
    report number is the venue. LIVE, no key."""
    from . import intake

    if not re.fullmatch(r"\d+", osti_id):
        raise LookupFailed(f"osti:{osti_id} is not an OSTI id, which is digits alone")
    response = intake._get(f"{OSTI_API}/{osti_id}", headers={"Accept": "application/json"})
    if response.status_code != 200:
        raise LookupFailed(f"OSTI answered {response.status_code} for record {osti_id}")
    body = response.json()
    records = body if isinstance(body, list) else [body]
    found = [r for r in records if isinstance(r, dict) and str(r.get("osti_id")) == osti_id]
    if not found:
        raise LookupFailed(f"OSTI holds no record {osti_id}")
    rec = found[0]
    # OSTI writes an author's affiliation, and sometimes an ORCID, after the
    # name ('Tao, Ling [National Renewable Energy Laboratory (NREL), …]');
    # the name alone is the author.
    authors = [_OSTI_AFFIX.sub("", str(a)).strip() for a in rec.get("authors") or []]
    authors = [a for a in authors if a]
    published = str(rec.get("publication_date") or "")[:4]
    return Row(
        verdict="INCLUDE",
        doi=str(rec.get("doi") or "").strip(),
        # Open when OSTI links the report's full text.
        openAccess=any(isinstance(link, dict) and link.get("rel") == "fulltext" for link in rec.get("links") or []),
        year=int(published) if published.isdigit() else None,
        journal=str(rec.get("report_number") or "").strip(),
        title=_plain(str(rec.get("title") or "")),
        firstAuthor=authors[0] if authors else "",
        publicationType=str(rec.get("product_type") or "").strip(),
        authors=authors,
        sourceUrl=f"{OSTI_PURL}/{osti_id}",
    )


def lookup_sgd(sgd_id: str) -> Row:
    """A strain entry of the Saccharomyces Genome Database, by its SGD id.
    It names no author and no date; its title is the database's words and
    the strain's display name. LIVE, no key."""
    from . import intake

    if not re.fullmatch(r"S\d{9}", sgd_id):
        raise LookupFailed(f"sgd:{sgd_id} is not an SGD id, an S and nine digits")
    url = f"{SGD_STRAIN}/{sgd_id}"
    response = intake._get(url, headers={"Accept": "application/json"})
    if response.status_code != 200:
        raise LookupFailed(f"the Saccharomyces Genome Database answered {response.status_code} for {sgd_id}")
    body = response.json()
    name = str(body.get("display_name") or "").strip() if isinstance(body, dict) else ""
    if not name:
        raise LookupFailed(f"the Saccharomyces Genome Database holds no strain {sgd_id}")
    return Row(
        verdict="INCLUDE",
        openAccess=True,
        journal=SGD_VENUE,
        title=f"{SGD_VENUE} strain entry: {name}",
        publicationType="database-entry",
        sourceUrl=url,
    )


def as_dict(row: Row) -> dict[str, Any]:
    return asdict(row)
