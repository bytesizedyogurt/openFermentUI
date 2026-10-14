"""Thread P: proposed by a fixed rule, written on a named person's approval
(OF-BLD-014 §2.3).

PHA from waste cellulosic sugars is the platform's second program. Its papers
are not curated by hand. A rule asks Europe PMC, orders what comes back, and
writes a proposal file; a person reads it, marks the rows they approve, and
`apply` writes those rows, and only those, into `src/data/corpus/threadP.ts`.
This is the second sanctioned way into `src/data/corpus/`, after the approved
DOIs of `identifiers.py`, and it follows the same pattern: a machine
proposes, a person approves.

    pnpm thread:propose                                       # LIVE, no key
    pnpm thread:apply <file.tsv> --approved-by "<name>"

The rule (every constant below is a selection convention, never a result):

- one search, `QUERY`, `resultType=core`, `pageSize=100`, ordered by
  citations;
- keep a result with a PMCID, `isOpenAccess` equal to `Y`, a publication year
  of `MIN_YEAR` or later, and a licence that starts with `cc`;
- order the kept results by `citedByCount`: the first `PROPOSE_RESEARCH`
  research articles and the first `PROPOSE_REVIEWS` reviews are `PROPOSE`,
  the rest `REVIEW`;
- every id in `docs/thread-p-include.txt` is looked up and is `INCLUDE`
  whatever the rule says; one with no open-access text is catalogued with
  `openAccess: false`.

`PROPOSE` is this module's opinion. `apply` writes `APPROVED` and `INCLUDE`
rows alone, and refuses a reviewer name `biorepo.write` would refuse.

An entry holds what Europe PMC returned and nothing else: no organism, no
topic, no number. Its one section says nobody has read it. The licence stays
out of the seed: the overlay sets it when the text is fetched.
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

from .biorepo import MIN_REVIEWER_CHARS, PLACEHOLDER_REVIEWERS

_CORE = Path(__file__).parent.parent
ROOT = _CORE.parent
SEED_FILE = ROOT / "src" / "data" / "corpus" / "threadP.ts"
PROPOSALS = _CORE / "data" / "thread-p-proposed.tsv"
INCLUDE_FILE = ROOT / "docs" / "thread-p-include.txt"

# ── the rule ───────────────────────────────────────────────────────────

QUERY = (
    '(polyhydroxyalkanoate* OR polyhydroxybutyrate* OR "PHA" OR "PHB") AND '
    '(lignocellulos* OR hydrolysate OR "waste paper" OR "paper sludge" OR "textile waste" '
    "OR cotton OR xylose OR cellulosic) AND OPEN_ACCESS:y AND HAS_FT:y"
)
PAGE_SIZE = 100
SORT = "CITED desc"
MIN_YEAR = 2012
PROPOSE_RESEARCH = 30
PROPOSE_REVIEWS = 5

# The fields of a search result this module reads. The first live call checks
# them, and a missing one stops the run: they were not confirmed when the
# document was written (§2.3).
REQUIRED_KEYS = ("pmcid", "isOpenAccess", "pubYear", "license", "citedByCount", "authorString", "journalInfo", "pubTypeList")

VERDICTS = ("PROPOSE", "REVIEW", "INCLUDE", "APPROVED")
COLUMNS = (
    "verdict", "id", "pmcid", "doi", "year", "journal", "title",
    "firstAuthor", "licence", "citations", "publicationType", "authors",
)

CATALOGUED_SENTENCE = (
    "Catalogued on {date} by the thread P selection rule from Europe PMC metadata. "
    "No curator has read this paper. Fetch its full text in Intake to read it."
)


class ThreadPRefused(RuntimeError):
    """Apply would write something no person approved, or no person approved it."""


class MissingKeys(RuntimeError):
    """A search result lacks a field the rule reads (§2.3: stop)."""


@dataclass
class Row:
    verdict: str
    id: str = ""
    pmcid: str = ""
    doi: str = ""
    year: int | None = None
    journal: str = ""
    title: str = ""
    firstAuthor: str = ""
    licence: str = ""
    citations: int | None = None
    publicationType: str = ""
    authors: list[str] = field(default_factory=list)


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
    types = pub_types(result)
    return Row(
        verdict=verdict,
        pmcid=str(result.get("pmcid") or "").strip(),
        doi=str(result.get("doi") or "").strip(),
        year=_year(result),
        journal=str(((result.get("journalInfo") or {}).get("journal") or {}).get("title") or "").strip(),
        title=_plain(str(result.get("title") or "")),
        firstAuthor=authors[0] if authors else "",
        licence=str(result.get("license") or "").strip(),
        citations=_citations(result),
        publicationType="review" if is_review(result) else (types[0] if types else ""),
        authors=authors,
    )


_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _plain(text: str) -> str:
    """A title as words: Europe PMC writes italics as <i>…</i>."""
    return re.sub(r"\s+", " ", _TAG.sub("", text)).strip().rstrip(".")


def eligible(result: dict[str, Any]) -> bool:
    year = _year(result)
    return (
        bool(str(result.get("pmcid") or "").strip())
        and result.get("isOpenAccess") == "Y"
        and year is not None
        and year >= MIN_YEAR
        and str(result.get("license") or "").strip().lower().startswith("cc")
    )


# ── propose ────────────────────────────────────────────────────────────


def propose(
    results: Sequence[dict[str, Any]],
    includes: Sequence[dict[str, Any] | str] = (),
    seeded: dict[str, str] | None = None,
) -> list[Row]:
    """The proposal, from one page of search results and the include list.

    `includes` holds, for each id in the include file, the search result that
    id resolved to, or the bare id when Europe PMC knew no open-access text
    for it. `seeded` maps a PMCID or DOI already in threadP.ts to its paper
    id, so a paper keeps its id across runs.
    """
    if results:
        check_keys(results[0])
    seeded = seeded or {}
    kept = sorted((r for r in results if eligible(r)), key=_citations, reverse=True)
    research = reviews = 0
    rows: list[Row] = []
    seen: set[str] = set()

    for inc in includes:
        if isinstance(inc, str):
            key = inc.strip()
            row = Row(verdict="INCLUDE", pmcid=key if key.upper().startswith("PMC") else "",
                      doi="" if key.upper().startswith("PMC") else key)
        else:
            row = row_of(inc, "INCLUDE")
        rows.append(row)
        seen.update(k.lower() for k in (row.pmcid, row.doi) if k)

    for r in kept:
        keys = {k.lower() for k in (str(r.get("pmcid") or ""), str(r.get("doi") or "")) if k}
        if keys & seen:
            continue
        seen |= keys
        if is_review(r):
            verdict = "PROPOSE" if reviews < PROPOSE_REVIEWS else "REVIEW"
            reviews += 1
        elif is_research(r):
            verdict = "PROPOSE" if research < PROPOSE_RESEARCH else "REVIEW"
            research += 1
        else:
            verdict = "REVIEW"
        rows.append(row_of(r, verdict))

    for row in rows:
        row.id = seeded.get(row.pmcid.lower(), "") or seeded.get(row.doi.lower(), "")
    return rows


def read_includes(path: Path = INCLUDE_FILE) -> list[str]:
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
            r.verdict, r.id, r.pmcid, r.doi, "" if r.year is None else r.year, r.journal, r.title,
            r.firstAuthor, r.licence, "" if r.citations is None else r.citations, r.publicationType,
            "; ".join(r.authors),
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
            year=int(cell("year")) if cell("year").isdigit() else None,
            journal=cell("journal"),
            title=cell("title"),
            firstAuthor=cell("firstAuthor"),
            licence=cell("licence"),
            citations=int(cell("citations")) if cell("citations").isdigit() else None,
            publicationType=cell("publicationType"),
            authors=[a.strip() for a in cell("authors").split(";") if a.strip()],
        ))
    return rows


# ── the seed file ──────────────────────────────────────────────────────

BEGIN = "  // ── written by pnpm thread:apply; one approval line, then one paper ──"
END = "  // ── end of the papers thread:apply wrote ──"
_APPROVAL = re.compile(r"^  // (P\d+) · approved by (.+) on (\d{4}-\d{2}-\d{2}) · (\S+)$")

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


@dataclass
class Entry:
    paper: dict[str, Any]
    approvedBy: str
    approvedOn: str
    verdict: str


def read_seed(path: Path = SEED_FILE) -> list[Entry]:
    """The entries an earlier apply wrote, in file order."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if BEGIN not in lines:
        return []
    out: list[Entry] = []
    pending: tuple[str, str, str] | None = None
    for line in lines[lines.index(BEGIN) + 1:]:
        if line == END:
            break
        m = _APPROVAL.match(line)
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
        for k in (e.paper.get("pmcid"), e.paper.get("doi")):
            if k:
                out[str(k).lower()] = e.paper["id"]
    return out


def paper_of(row: Row, paper_id: str, on: str) -> dict[str, Any]:
    sentence = CATALOGUED_SENTENCE.format(date=on)
    paper: dict[str, Any] = {
        "id": paper_id,
        "title": row.title or (row.pmcid or row.doi),
        "authors": row.authors,
        "year": row.year if row.year is not None else 0,
        "venue": row.journal,
        "organisms": [],
        "topics": [],
        "abstract": sentence,
        "sections": [{"id": f"{paper_id}-s1", "heading": "Catalogue note", "text": sentence}],
        "ingest": "catalogued",
        "thread": "P",
        "sourceType": "review" if row.publicationType == "review" else "journal-article",
        "textSource": "curation-note",
        "openAccess": bool(row.pmcid),
        "tranche": 1,
    }
    if row.doi:
        paper["doi"] = row.doi
    if row.pmcid:
        paper["pmcid"] = row.pmcid
    if not row.title or row.year is None or not row.authors:
        paper["verifyNeeded"] = True
    return paper


def reviewer_refusal(name: str) -> str | None:
    """The reviewer-name rule `biorepo.write` applies, word for word."""
    name = (name or "").strip()
    if not name:
        return "an approval needs a name; an empty name is nobody approving"
    if len(name) < MIN_REVIEWER_CHARS or name.lower() in PLACEHOLDER_REVIEWERS:
        return f"{name!r} is a placeholder, not a person"
    return None


def apply(
    rows: Sequence[Row],
    approved_by: str,
    *,
    seed: Path = SEED_FILE,
    on: str | None = None,
    types_import: str = "../types",
) -> list[str]:
    """Write every APPROVED or INCLUDE row into the seed file and return one
    line per paper added. A paper already in the file keeps its id and its
    entry; a new one takes the next free `P<n>` in file order."""
    refusal = reviewer_refusal(approved_by)
    if refusal:
        raise ThreadPRefused(refusal)
    chosen = [r for r in rows if r.verdict in ("APPROVED", "INCLUDE")]
    for r in chosen:
        if r.verdict == "APPROVED" and not r.pmcid:
            raise ThreadPRefused(
                f"row {r.doi or r.title or '(blank)'} is APPROVED with no PMCID; only an INCLUDE row "
                "may be catalogued without open-access text"
            )
        if not (r.pmcid or r.doi):
            raise ThreadPRefused(f"row {r.title or '(blank)'} names neither a PMCID nor a DOI")
    on = on or date.today().isoformat()
    entries = read_seed(seed)
    known = seeded_ids(entries)
    next_n = 1 + max((int(e.paper["id"][1:]) for e in entries), default=0)
    added: list[str] = []
    for r in chosen:
        if known.get(r.pmcid.lower()) or known.get(r.doi.lower()):
            continue
        pid = f"P{next_n}"
        next_n += 1
        entries.append(Entry(paper_of(r, pid, on), approved_by.strip(), on, r.verdict))
        for k in (r.pmcid, r.doi):
            if k:
                known[k.lower()] = pid
        added.append(f"{pid}  {r.verdict:8} {r.pmcid or r.doi}  {r.title[:70]}")
    seed.parent.mkdir(parents=True, exist_ok=True)
    seed.write_text(render(entries, types_import), encoding="utf-8")
    return added


def render(entries: Sequence[Entry], types_import: str = "../types") -> str:
    lines = [HEADER.rstrip("\n"), f"import type {{ ExtractionRecord, Paper }} from '{types_import}';", ""]
    if not entries:
        lines.append("export const THREAD_P_PAPERS: Paper[] = [];")
    else:
        lines.append("export const THREAD_P_PAPERS: Paper[] = [")
        lines.append(BEGIN)
        for e in entries:
            lines.append(f"  // {e.paper['id']} · approved by {e.approvedBy} on {e.approvedOn} · {e.verdict}")
            lines.append("  " + json.dumps(e.paper, ensure_ascii=False) + ",")
        lines.append(END)
        lines.append("];")
    lines.append("")
    lines.append("export const THREAD_P_RECORDS: ExtractionRecord[] = [];")
    return "\n".join(lines) + "\n"


# ── the network ────────────────────────────────────────────────────────


def search(query: str = QUERY, page_size: int = PAGE_SIZE) -> list[dict[str, Any]]:
    """One page of Europe PMC's search, ordered by citations. LIVE, no key."""
    from . import intake

    response = intake._get(
        f"{intake.EUROPE_PMC}/search",
        {"query": query, "format": "json", "resultType": "core", "pageSize": str(page_size), "sort": SORT},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Europe PMC answered {response.status_code} to the thread P search")
    return list(response.json().get("resultList", {}).get("result", []))


def lookup(identifier: str) -> dict[str, Any] | str:
    """An include-file id as Europe PMC knows it, or the id itself when it
    holds no open-access text for it."""
    key = identifier.strip()
    if key.upper().startswith("PMC"):
        query = f"PMCID:{key.upper()}"
    elif key.isdigit():
        query = f"EXT_ID:{key} AND SRC:MED"
    else:
        query = f'DOI:"{key}"'
    for hit in search(query, 5):
        if hit.get("isOpenAccess") == "Y" and hit.get("pmcid"):
            return hit
    return key


def as_dict(row: Row) -> dict[str, Any]:
    return asdict(row)
