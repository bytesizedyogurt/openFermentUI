"""Identifiers proposed by machine, approved by a person (OF-BLD-012.1 F9).

73 of the 132 seed papers carry no PMCID, DOI or PMID. `biorepo.write`
refuses every decision about them (§2.3 rule 'paper'), so 52 unverified
records can be reviewed in the browser and never reach the committed file.
That is not a permanent limit: Crossref will take a title and a year and
come back with a DOI and a score.

WHAT THIS MODULE WILL NOT DO. A Crossref hit is a PROPOSAL, and a proposal
is not a fact. Nothing here writes to `src/data/corpus/` unless it is handed
a row a person has marked APPROVED — not PROPOSE, which is this module's own
opinion, and not a high score, which is Crossref's. A wrong DOI is worse
than no DOI: it attaches a paper's whole record set to somebody else's work,
and every later fetch, quote and promotion inherits the mistake silently.

So the flow is two commands with a person in between:

    pnpm ids:propose            → core/data/identifiers-proposed.tsv
    (a person reads it, marks rows APPROVED, deletes the rest)
    pnpm ids:apply <that file>  → patches the seed, prints what it changed
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# A title has to be this close, after normalisation, and the year this near,
# before the run is willing to say PROPOSE. Both are deliberately tight: the
# cost of a REVIEW row is thirty seconds of a person's attention, and the cost
# of a wrong DOI is a paper's whole record set pointing at another study.
PROPOSE_SIMILARITY = 0.92
YEAR_TOLERANCE = 1

SEED_DIR = Path(__file__).parent.parent.parent / "src" / "data" / "corpus"
PROPOSALS = Path(__file__).parent.parent / "data" / "identifiers-proposed.tsv"

COLUMNS = (
    "verdict", "paperId", "seedTitle", "seedYear",
    "matchTitle", "matchYear", "doi", "score", "similarity",
)


class SeedPatchRefused(RuntimeError):
    """A patch that would have had to guess. Nothing was written."""


@dataclass(frozen=True)
class Match:
    """One Crossref hit, reduced to what a person needs to judge it."""

    title: str
    year: int | None
    doi: str
    score: float


@dataclass
class Proposal:
    """One row of the file a person reads. `verdict` is the column they edit."""

    verdict: str
    paperId: str
    seedTitle: str
    seedYear: int | None
    matchTitle: str = ""
    matchYear: int | None = None
    doi: str = ""
    score: float = 0.0
    similarity: float = 0.0


# ── how close is close ─────────────────────────────────────────────────

_PUNCT = re.compile(r"[^a-z0-9]+")


def normalize_title(title: str) -> str:
    """Case, accents and punctuation removed; whitespace collapsed. Greek
    letters are spelled out, because a paper is as likely to write 'β-casein'
    as 'beta-casein' and they are the same title."""
    folded = title.lower()
    for greek, latin in (("β", "beta"), ("α", "alpha"), ("γ", "gamma"), ("κ", "kappa"), ("μ", "mu")):
        folded = folded.replace(greek, latin)
    folded = unicodedata.normalize("NFKD", folded)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return _PUNCT.sub(" ", folded).strip()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    """1.0 for the same title, 0.0 for nothing in common. Levenshtein over the
    normalised forms, divided by the longer one."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na and not nb:
        return 1.0
    longest = max(len(na), len(nb))
    return 0.0 if longest == 0 else 1 - _levenshtein(na, nb) / longest


def verdict(seed_title: str, seed_year: int | None, match_title: str, match_year: int | None) -> str:
    """PROPOSE only when the title is nearly the same AND the year is within
    one. Everything else is REVIEW — a person's call, not this module's."""
    if not match_title or match_year is None or seed_year is None:
        return "REVIEW"
    if abs(int(match_year) - int(seed_year)) > YEAR_TOLERANCE:
        return "REVIEW"
    return "PROPOSE" if similarity(seed_title, match_title) >= PROPOSE_SIMILARITY else "REVIEW"


# ── the run ────────────────────────────────────────────────────────────

Ask = Callable[[str, int | None], Sequence[Match]]


def propose(papers: Iterable[dict[str, Any]], ask: Ask) -> list[Proposal]:
    """One row per paper, best match first. `ask` is the Crossref query,
    passed in so this can be driven without a network."""
    rows: list[Proposal] = []
    for p in papers:
        title, year = str(p.get("title") or ""), p.get("year")
        hits = list(ask(title, year))
        best = max(hits, key=lambda m: similarity(title, m.title), default=None)
        rows.append(
            Proposal(
                verdict=verdict(title, year, best.title if best else "", best.year if best else None),
                paperId=str(p.get("id") or ""),
                seedTitle=title,
                seedYear=year,
                matchTitle=best.title if best else "",
                matchYear=best.year if best else None,
                doi=best.doi if best else "",
                score=round(best.score, 1) if best else 0.0,
                similarity=round(similarity(title, best.title), 3) if best else 0.0,
            )
        )
    return rows


def to_tsv(rows: Iterable[Proposal]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow([
            r.verdict, r.paperId, r.seedTitle, "" if r.seedYear is None else r.seedYear,
            r.matchTitle, "" if r.matchYear is None else r.matchYear, r.doi, r.score, r.similarity,
        ])
    return out.getvalue()


def from_tsv(text: str) -> list[Proposal]:
    rows: list[Proposal] = []
    for raw in csv.DictReader(io.StringIO(text), delimiter="\t"):
        rows.append(
            Proposal(
                verdict=(raw.get("verdict") or "").strip(),
                paperId=(raw.get("paperId") or "").strip(),
                seedTitle=raw.get("seedTitle") or "",
                seedYear=int(raw["seedYear"]) if (raw.get("seedYear") or "").strip() else None,
                matchTitle=raw.get("matchTitle") or "",
                matchYear=int(raw["matchYear"]) if (raw.get("matchYear") or "").strip() else None,
                doi=(raw.get("doi") or "").strip(),
                score=float(raw["score"]) if (raw.get("score") or "").strip() else 0.0,
                similarity=float(raw["similarity"]) if (raw.get("similarity") or "").strip() else 0.0,
            )
        )
    return rows


# ── the patch ──────────────────────────────────────────────────────────

_VENUE = re.compile(r"^(\s*)venue:")


def apply_approved(rows: Iterable[Proposal], seed_dir: Path | None = None) -> list[str]:
    """Write the DOI of every APPROVED row into the seed, and say what
    changed. Returns one line per paper patched; a row that is not APPROVED,
    carries no DOI, or names a paper that already has one is skipped in
    silence — the caller reports the counts.

    Raises rather than guesses when a paper id is not in the seed at all: a
    patcher that shrugs at an id it cannot find is a patcher that will one day
    write a DOI into the wrong entry.
    """
    directory = seed_dir or SEED_DIR
    files = sorted(directory.glob("*.ts"))
    changed: list[str] = []
    for row in rows:
        if row.verdict != "APPROVED" or not row.doi:
            continue
        where = _find_paper(files, row.paperId)
        if where is None:
            raise SeedPatchRefused(
                f"{row.paperId} is not a paper in {directory}; nothing was written for it or for "
                "any row after it"
            )
        path, lines, at = where
        block = _block_of(lines, at)
        if any(line.lstrip().startswith("doi:") for line in block):
            continue
        for i in range(at, min(at + len(block), len(lines))):
            m = _VENUE.match(lines[i])
            if not m:
                continue
            lines.insert(i + 1, f"{m.group(1)}doi: '{row.doi}',")
            # `split("\n")` leaves a trailing "" for a file that ends in a
            # newline, so joining reproduces the original byte for byte. Adding
            # one here would grow the file by a blank line on every apply.
            path.write_text("\n".join(lines), encoding="utf-8")
            changed.append(f"{row.paperId}: doi '{row.doi}' added to {path.name}")
            break
        else:
            raise SeedPatchRefused(
                f"{row.paperId} in {path.name} has no `venue:` line to write the DOI under; "
                "nothing was written for it"
            )
    return changed


def _find_paper(files: Sequence[Path], paper_id: str) -> tuple[Path, list[str], int] | None:
    needle = f"id: '{paper_id}',"
    for path in files:
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            if line.strip() == needle:
                return path, lines, i
    return None


def _block_of(lines: Sequence[str], at: int) -> list[str]:
    """The paper object the line at `at` opens, to the next paper or the end
    of the array — so a `doi:` belonging to the NEXT entry is never read as
    this one's."""
    out: list[str] = []
    for line in lines[at:]:
        if out and line.strip().startswith("id: '"):
            break
        out.append(line)
    return out


# ── Crossref, the only part that touches the network ───────────────────

CROSSREF = "https://api.crossref.org/works"
# Crossref asks for a contact in the User-Agent so they can reach whoever is
# hammering them. Theirs is the polite pool; without it requests are throttled.
MAILTO = "openferment@example.org"
ROWS = 3


def crossref(title: str, year: int | None, *, timeout: float = 20.0) -> list[Match]:
    """Ask Crossref. The ONLY function here that makes a request; everything
    above it is pure, which is why everything above it is tested offline."""
    import httpx

    params: dict[str, Any] = {"query.bibliographic": title, "rows": ROWS, "mailto": MAILTO}
    if year:
        params["filter"] = f"from-pub-date:{int(year) - 1}-01-01,until-pub-date:{int(year) + 1}-12-31"
    headers = {"User-Agent": f"openFerment/0.1 (mailto:{MAILTO})"}
    response = httpx.get(CROSSREF, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    items = (response.json().get("message") or {}).get("items") or []
    out: list[Match] = []
    for item in items:
        titles = item.get("title") or []
        parts = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
        out.append(
            Match(
                title=titles[0] if titles else "",
                year=parts[0] if parts and isinstance(parts[0], int) else None,
                doi=str(item.get("DOI") or ""),
                score=float(item.get("score") or 0.0),
            )
        )
    return out
