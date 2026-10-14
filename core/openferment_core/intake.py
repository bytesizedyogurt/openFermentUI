"""Intake — the first network request the pipeline has ever made (OF-BLD-012 §5).

Until this file, Intake was timers. `IntakeIngest.tsx` said so in its own
header: the five-stage board advanced on a schedule and fetched nothing. This
is the real path. A paper with a PMCID is fetched from Europe PMC as JATS XML,
split into sections, and cached under `core/data/fulltext/{paperId}.json` with
the licence string the article carried — at which point `PaperReader` can show
the paper's own words instead of the curator's note, and extraction (§6) has
something to anchor to.

THREE THINGS THIS FILE IS CAREFUL ABOUT.

Tables keep their rows. The numbers this project exists to find live in tables
far more often than in prose, and a table flattened into a paragraph loses the
one structure that says which number belongs to which condition. Every
<table-wrap> becomes its own section, one line per row, cells joined with a
bar, so a quote from it is a row and a row is a fact.

Failure is a result, not an exception. `fetch_paper` returns a `FetchResult`
whose status is `failed:fetch` or `failed:parse` with a reason, because the
ingest board already renders both states and a stack trace renders as nothing.
The DOI-only papers are asked once: a miss is cached as a miss, so the batch
does not re-query Europe PMC for the same 26 papers every run.

Europe PMC is treated as a colleague's server. At most two requests a second,
a User-Agent that names the project and — when `OPENFERMENT_CONTACT` is set in
`core/.env` — somebody to write to, one retry on a 5xx, and nothing else.

Fixture mode (`OPENFERMENT_FIXTURES=1`) reads XML from `tests/fixtures/jats/`
and refuses the network. It exists so the parser and the persistence can be
tested offline, and so §8.1's demo can replay the loop with no connection.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import atomic
from .models import FetchedSection, FetchLicense, FetchResult, IntakeStatus, OverlayPaper

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
# Where the service keeps what it fetched, extracted and decided (§2.2), and
# where fixture mode reads from. Both overridable by environment, read once
# at import, so `pnpm demo:offline` can point a whole service at
# tests/fixtures/demo/ and a scratch data directory without touching
# core/data/biorepo.json — the committed file — or anything anyone fetched
# for real (§8.1).
_CORE = Path(__file__).parent.parent


def _env_path(name: str, default: Path) -> Path:
    """An override from the environment. A relative one is taken from the
    repository root — the `pnpm intake:*` aliases run from core/, and a path
    typed at the root must not quietly land in core/core/."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else (_CORE.parent / path).resolve()


DATA_DIR = _env_path("OPENFERMENT_DATA_DIR", _CORE / "data")
FULLTEXT_DIR = DATA_DIR / "fulltext"
FIXTURE_ROOT = _env_path("OPENFERMENT_FIXTURE_DIR", _CORE / "tests" / "fixtures")
FIXTURE_DIR = FIXTURE_ROOT / "jats"
TIMEOUT_S = 20.0
# §11: at most two requests per second. Enforced here rather than remembered by
# every caller, so the batch and a burst of UI clicks are held to the same rate.
MIN_INTERVAL_S = 0.5

XLINK = "{http://www.w3.org/1999/xlink}"
_last_request_at = 0.0


class NetworkRefused(RuntimeError):
    """Raised in fixture mode when something tries to reach the network."""


class Transient(RuntimeError):
    """The network's condition, not the paper's: a 5xx that survived the one
    retry. Never cached — the next run asks again (OF-BLD-012.1 §6.9)."""


def fixtures_only() -> bool:
    return os.environ.get("OPENFERMENT_FIXTURES", "") not in ("", "0", "false")


def _user_agent() -> str:
    ua = "openferment-core/0.1 (+https://github.com/bytesizedyogurt/openFermentUI)"
    contact = os.environ.get("OPENFERMENT_CONTACT", "").strip()
    return f"{ua} {contact}" if contact else ua


_throttle_lock = threading.Lock()


def _throttle() -> None:
    """Held under a lock: FastAPI runs the sync endpoints in a thread pool, and
    two clicks arriving together must queue behind one another, not both read
    the same timestamp and fire at once."""
    global _last_request_at
    with _throttle_lock:
        wait = MIN_INTERVAL_S - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _get(url: str, params: dict[str, str] | None = None) -> httpx.Response:
    """One GET with the project's manners: throttle, User-Agent, one retry on 5xx."""
    if fixtures_only():
        raise NetworkRefused(f"OPENFERMENT_FIXTURES is set; refusing to GET {url}")
    headers = {"User-Agent": _user_agent()}
    last: httpx.Response | None = None
    for attempt in (1, 2):
        _throttle()
        response = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT_S)
        if response.status_code < 500:
            return response
        last = response
    assert last is not None
    return last


# ── resolution ─────────────────────────────────────────────────────────


def resolve_pmcid(paper: dict[str, Any]) -> str | None:
    """The PMCID to fetch, from the seed when it has one and Europe PMC when it
    has only a DOI or PMID. None when there is no open-access full text.

    The search is one request and is only made for papers the seed could not
    name; `fetch_paper` caches the answer, including a None, so each DOI-only
    paper is asked exactly once.
    """
    pmcid = (paper.get("pmcid") or "").strip()
    if pmcid:
        return pmcid
    doi = (paper.get("doi") or "").strip()
    pmid = (paper.get("pmid") or "").strip()
    if doi:
        query = f'DOI:"{doi}"'
    elif pmid:
        query = f"EXT_ID:{pmid} AND SRC:MED"
    else:
        return None
    response = _get(
        f"{EUROPE_PMC}/search",
        {"query": query, "format": "json", "resultType": "lite", "pageSize": "5"},
    )
    if response.status_code >= 500:
        raise Transient(f"Europe PMC returned {response.status_code} looking up {query}")
    if response.status_code != 200:
        return None
    for hit in response.json().get("resultList", {}).get("result", []):
        if hit.get("isOpenAccess") == "Y" and hit.get("pmcid"):
            return str(hit["pmcid"])
    return None


# ── fetch ──────────────────────────────────────────────────────────────


def fetch_fulltext(pmcid: str) -> str:
    """The JATS XML for a PMCID, as a string. Raises on anything but a 200.

    In fixture mode the XML comes from tests/fixtures/jats/{pmcid}.xml and the
    network is never touched.
    """
    if fixtures_only():
        path = FIXTURE_DIR / f"{pmcid}.xml"
        if not path.exists():
            raise NetworkRefused(f"fixture mode and no fixture at {path}")
        return path.read_text(encoding="utf-8")
    response = _get(f"{EUROPE_PMC}/{pmcid}/fullTextXML")
    if response.status_code >= 500:
        raise Transient(f"Europe PMC returned {response.status_code} for {pmcid}")
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"Europe PMC returned {response.status_code} for {pmcid}",
            request=response.request,
            response=response,
        )
    return response.text


# ── JATS → sections ────────────────────────────────────────────────────

_WS = re.compile(r"\s+")


# Elements that are not the paper's prose. They never leak into a section's
# paragraphs, wherever JATS nests them — a <table-wrap> inside a <p> is common
# — and tables and figures become their own sections instead.
_NOT_PROSE = {"table-wrap", "fig", "ref-list", "ack", "fn-group"}
# Elements whose text is not the paper's argument and must not become a section
# or leak into a parent's paragraphs.
_DROP = _NOT_PROSE | {"sec", "title", "label"}
# Europe PMC serves the back matter inside <body>, as <sec sec-type=...>: of
# the first 31 real fetches (OF-BLD-014 §1.5, 2026-10-14), 18 carried
# fn-group and ref-list sections there, 15 ack, and others the data,
# supplementary, contributor and conflict statements. They are dropped as
# <ack>, <fn-group> and <ref-list> are, with every section below them.
_BACK_SEC_TYPES = {
    "ack", "fn-group", "ref-list", "associated-data", "data-availability", "data-availability-statement",
    "supplementary-material", "supplementary-materials", "contrib-info", "COI-statement",
    "author-contributions", "glossary", "funding-information", "funding-statement",
}
# Elements that end a run of words: the text either side of one is two runs,
# never one word glued to the next ('Background' + 'The study').
_BLOCK = {"p", "title", "label", "caption", "list-item", "def-item", "term", "def", "disp-quote", "license-p", "fn"}
_MATHML = "{http://www.w3.org/1998/Math/MathML}"
_ALI = "{http://www.niso.org/schemas/ali/1.0/}"

_NUMERIC = re.compile(r"[-\u2212\u207b]?\d+")
# Typography inside an exponent: '10<sup>− 15</sup>' is 10^-15, and a thin
# space after the minus is as common as a plain one.
_INNER_SPACE = re.compile(r"[\s\u00a0\u2009\u200a\u202f]+")
# A run of reference numbers: '13,14' or '3–5'.
_RUN = re.compile(r"\d+[\d,\s\u2013\u2212-]*[,\u2013\u2212-][\d,\s\u2013\u2212-]*")
# What a mark's text is when it is no word: digits and their punctuation.
_MARKISH = re.compile(r"[\d\s.,;:()\[\]\u2013\u2212-]+")


def _local(tag: object) -> str:
    return tag if isinstance(tag, str) else ""


def _mark(el: ET.Element, parts: list[str], ref_type: str | None) -> None:
    """A superscript that links somewhere: a citation, or a footnote mark.
    A citation is never the paper's words and is dropped; so is a numeric
    footnote mark, which glued to a number would change it ('0.5' plus mark
    '1.' read as '0.51'). A footnote letter or symbol reads inline, '7.2a',
    as it always has."""
    inner = "".join(el.itertext()).strip()
    if ref_type == "bibr" or not inner or _MARKISH.fullmatch(inner):
        return
    parts.append(inner)


def _sup(el: ET.Element, parts: list[str], *, prose: bool, marks: frozenset[str]) -> None:
    """What an unlinked superscript means, from what it holds and what it
    follows. On a number, a number is a power ('10⁶', '2⁴', '(3/5)²' read
    '10^6', '2^4', '(3/5)^2'), unless it is a label of a footnote under this
    very table, which marks a cell and is dropped. On a letter it is a unit's
    exponent and reads inline, 'L<sup>-1</sup>' as 'L-1'; after a bracket or
    a dash it is an isotope's mass, '[α-<sup>32</sup>P]' as '[α-32P]'. A run
    of numbers is citations. Anything else, an ordinal, a footnote letter, a
    dagger, a charge, reads inline."""
    inner: list[str] = []
    _collect(el, inner, prose=prose, marks=marks)
    raw = "".join(inner).strip()
    exponent = _INNER_SPACE.sub("", raw)
    before = "".join(parts).rstrip()
    if _NUMERIC.fullmatch(exponent):
        on_number = before[-1:].isdigit() or before[-1:] == ")"
        if on_number and exponent.rstrip(".") in marks:
            return
        if on_number:
            # Close up '10 ⁶' as well as '10⁶': the space is typography.
            if parts and parts[-1].rstrip() != parts[-1]:
                parts[-1] = parts[-1].rstrip()
            parts.append("^" + exponent)
            return
        parts.append(exponent)
    elif _RUN.fullmatch(raw):
        return
    else:
        parts.append(raw)


def _group(s: str) -> str:
    return s if re.fullmatch(r"[\w.\u2212-]+", s) else f"({s})"


_SPACED_OPERATORS = {"=", "+", "×", "·", "<", ">", "≤", "≥", "±", "≈", "∼", "~", "→", "−"}


def _math(el: ET.Element) -> str:
    """MathML written out as a line a reader can quote: a fraction as a/b,
    a power as a^b, a subscript inline as <sub> reads, a root as √(x)."""
    tag = _local(el.tag).replace(_MATHML, "")
    kids = [c for c in el if _local(c.tag)]
    rendered = [_math(c) for c in kids]
    if tag in ("mi", "mn", "mtext", "ms"):
        return (el.text or "").strip()
    if tag == "mo":
        op = (el.text or "").strip()
        return f" {op} " if op in _SPACED_OPERATORS else op
    if tag == "mspace":
        return " "
    if tag in ("annotation", "annotation-xml", "none", "mprescripts"):
        return ""
    if tag == "semantics":
        return rendered[0] if rendered else ""
    if tag == "mfrac" and len(rendered) == 2:
        return f"{_group(rendered[0].strip())}/{_group(rendered[1].strip())}"
    if tag == "msup" and len(rendered) == 2:
        return f"{rendered[0]}^{_group(rendered[1].strip())}"
    if tag == "msub" and len(rendered) == 2:
        return f"{rendered[0]}{rendered[1]}"
    if tag == "msubsup" and len(rendered) == 3:
        return f"{rendered[0]}{rendered[1]}^{_group(rendered[2].strip())}"
    if tag == "msqrt":
        return f"√({''.join(rendered).strip()})"
    if tag == "mroot" and len(rendered) == 2:
        return f"{_group(rendered[0].strip())}^(1/{rendered[1].strip()})"
    if tag == "mfenced":
        return f"{el.get('open', '(')}{el.get('separators', ',')[:1].join(rendered)}{el.get('close', ')')}"
    return "".join(rendered)


def _tex(el: ET.Element) -> str:
    """A <tex-math> formula, when no MathML stands beside it: the expression
    alone, without the LaTeX document Europe PMC wraps it in."""
    src = "".join(el.itertext())
    m = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", src, re.S)
    return (m.group(1) if m else src).replace("$", " ").strip()


def _collect(el: ET.Element, parts: list[str], *, prose: bool, marks: frozenset[str] = frozenset()) -> None:
    """Text in document order. <sup> and <sub> contribute their characters
    inline, so L<sup>-1</sup> reads 'L-1' and CO<sub>2</sub> reads 'CO2', the
    spellings §2.4's normalisation expects; a superscript on a number is a
    power, '10^6' (`_sup`); a superscript that links to a citation or a
    footnote is a mark (`_mark`). In prose mode, tables and figures nested
    anywhere below are skipped: they are sections of their own, not this
    paragraph. `marks` holds the footnote labels of the table being read."""
    if el.text:
        parts.append(el.text)
    for child in el:
        tag = _local(child.tag)
        if prose and tag in _NOT_PROSE:
            pass
        elif tag == "alternatives":
            # One rendering of a formula: MathML when there is one, else the TeX.
            math = child.find(f"{_MATHML}math")
            tex = child.find("tex-math")
            if math is not None:
                parts.append(_math(math))
            elif tex is not None:
                parts.append(_tex(tex))
        elif tag == f"{_MATHML}math":
            parts.append(_math(child))
        elif tag == "tex-math":
            parts.append(_tex(child))
        elif tag == "xref" and child.find(".//sup") is not None:
            _mark(child, parts, child.get("ref-type"))
        elif tag == "sup" and child.find(".//xref") is not None:
            _mark(child, parts, child.find(".//xref").get("ref-type"))
        elif tag == "sup":
            _sup(child, parts, prose=prose, marks=marks)
        elif tag == "break":
            parts.append(" ")
        else:
            _collect(child, parts, prose=prose, marks=marks)
            if tag in _BLOCK:
                parts.append(" ")
        if child.tail:
            parts.append(child.tail)


def _text(el: ET.Element | None, *, prose: bool = False, marks: frozenset[str] = frozenset()) -> str:
    """All text under an element, inline markup dropped, whitespace collapsed."""
    if el is None:
        return ""
    parts: list[str] = []
    _collect(el, parts, prose=prose, marks=marks)
    return _WS.sub(" ", "".join(parts)).strip()


def _own_paragraphs(sec: ET.Element) -> str:
    """The text of a <sec> that belongs to it directly: paragraphs and lists,
    but not its nested <sec>s, its tables, or its figures — those become their
    own sections, wherever they are nested. Its <title> is the heading and is
    left out here."""
    parts: list[str] = []
    for child in sec:
        tag = child.tag
        if tag in _DROP:
            continue
        text = _text(child, prose=True)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _is_back_matter(sec: ET.Element) -> bool:
    return (sec.get("sec-type") or "").strip() in _BACK_SEC_TYPES


def _walk_secs(parent: ET.Element, prefix: str, out: list[tuple[str, str]]) -> None:
    """Depth-first over <sec>, document order. Nested sections flatten to
    their own entries with the parent heading prefixed ('Results › Growth').
    A back-matter section is dropped with everything below it."""
    for sec in parent.findall("sec"):
        if _is_back_matter(sec):
            continue
        title = _text(sec.find("title")) or "Untitled section"
        heading = f"{prefix} › {title}" if prefix else title
        text = _own_paragraphs(sec)
        if text:
            out.append((heading, text))
        _walk_secs(sec, heading, out)


def _floats(el: ET.Element, tag: str):
    """Every <table-wrap> or <fig> below `el`, in document order, leaving out
    those inside back matter: a dropped section, a reference list, footnotes."""
    for child in el:
        name = _local(child.tag)
        if name in ("ref-list", "fn-group", "ack") or (name == "sec" and _is_back_matter(child)):
            continue
        if name == tag:
            yield child
            continue
        yield from _floats(child, tag)


def _span(cell: ET.Element, name: str) -> int:
    try:
        return min(max(int(cell.get(name) or 1), 1), 100)
    except ValueError:
        return 1


def _footnotes(wrap: ET.Element) -> tuple[list[str], frozenset[str]]:
    """The lines under a table, and the labels its cells may carry as marks."""
    lines: list[str] = []
    labels: set[str] = set()
    for foot in wrap.iter("table-wrap-foot"):
        for item in foot:
            text = _text(item)
            if text:
                lines.append(text)
            if _local(item.tag) == "fn":
                label = _text(item.find("label"))
                if not label:
                    lead = item.find("p/sup")
                    label = _text(lead) if lead is not None else ""
                if label:
                    labels.add(label.rstrip(".):"))
    return lines, frozenset(labels)


def _table_rows(wrap: ET.Element, marks: frozenset[str] = frozenset()) -> list[str]:
    """One line per row, cells joined with ' | '. The row is the unit a quote
    from a table should be, because the row is what says which number goes
    with which condition, so the rows are laid out as the table's grid: an
    empty cell keeps its place, a cell that spans rows is repeated in every
    row it spans, and a header that spans columns is repeated over each of
    them, so every value sits under its own column."""
    lines: list[str] = []
    carried: dict[int, tuple[str, int]] = {}  # column → (text, rows still to fill)
    for row in wrap.iter("tr"):
        out: list[str] = []

        def take_carried() -> None:
            while len(out) in carried:
                text, left = carried[len(out)]
                if left <= 1:
                    del carried[len(out)]
                else:
                    carried[len(out)] = (text, left - 1)
                out.append(text)

        for cell in row:
            if _local(cell.tag) not in ("th", "td"):
                continue
            take_carried()
            text = _text(cell, marks=marks)
            rows = _span(cell, "rowspan")
            for k in range(_span(cell, "colspan")):
                value = text if (k == 0 or cell.tag == "th") else ""
                if rows > 1:
                    carried[len(out)] = (value, rows - 1)
                out.append(value)
        take_carried()
        if any(out):
            lines.append(" | ".join(out).rstrip())
    return lines


def _caption(el: ET.Element) -> str:
    label = _text(el.find("label"))
    caption = _text(el.find("caption"))
    return " ".join(p for p in (label, caption) if p).strip()


def _license(root: ET.Element) -> FetchLicense | None:
    lic = root.find(".//front/article-meta/permissions/license")
    if lic is None:
        return None
    href = lic.get(f"{XLINK}href") or lic.get("href")
    # Some articles put the URL on an <ext-link> inside the licence paragraph,
    # and others in <ali:license_ref>.
    if not href:
        link = lic.find(f".//ext-link[@{XLINK}href]")
        if link is not None:
            href = link.get(f"{XLINK}href")
    if not href:
        ref = lic.find(f"{_ALI}license_ref")
        if ref is not None and (ref.text or "").strip():
            href = ref.text.strip()
    paragraphs = [_text(p) for p in lic.findall("license-p")]
    text = " ".join(p for p in paragraphs if p) or _text(lic) or None
    return FetchLicense(href=href or None, text=text)


def split_jats(xml: str, *, paper_id: str = "", pmcid: str | None = None) -> FetchResult:
    """JATS XML → a FetchResult whose sections are the paper's own words.

    Order: the abstract first as 'abstract'; then every body <sec>, depth-first,
    as 's1', 's2', … with nested headings prefixed; then every <table-wrap> as
    't1', 't2', … one line per row of its grid, with its footnotes after the
    rows; then every <fig> caption as 'f1', 'f2', …. Tables and figures are
    found in the body, in <floats-group> and in <back>. <ref-list>, <ack> and
    <fn-group> are dropped, and so is a <sec> whose sec-type names back
    matter (`_BACK_SEC_TYPES`). The <license> element is read into `license`.

    A parse failure — malformed XML, or a document with no article body — is
    returned as `failed:parse` with the reason, never raised.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:parse",
            reason=f"XML did not parse: {e}", fetchedAt=now, bytes=len(xml.encode("utf-8")),
        )

    # Europe PMC wraps a missing article in an error document rather than a 404.
    article = root if root.tag == "article" else root.find(".//article")
    if article is None:
        return FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:parse",
            reason=f"no <article> element (root is <{root.tag}>)", fetchedAt=now,
            bytes=len(xml.encode("utf-8")),
        )

    sections: list[FetchedSection] = []

    # The abstract. The first one with no abstract-type is the real one; the
    # typed ones are graphical or teaser abstracts.
    abstracts = article.findall(".//front/article-meta/abstract")
    plain = [a for a in abstracts if not a.get("abstract-type")] or abstracts
    if plain:
        text = _own_paragraphs(plain[0]) or _text(plain[0])
        if text:
            sections.append(FetchedSection(id="abstract", heading="Abstract", text=text))

    body = article.find("body")
    if body is None:
        return FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:parse",
            reason="article has no <body> — Europe PMC serves abstracts for some records, not full text",
            fetchedAt=now, license=_license(article), sections=sections,
            bytes=len(xml.encode("utf-8")),
        )

    walked: list[tuple[str, str]] = []
    # Paragraphs sitting directly in <body> with no <sec> around them — rare,
    # but a short communication can be written that way.
    loose = _own_paragraphs(body)
    if loose:
        walked.append(("Body", loose))
    _walk_secs(body, "", walked)
    for n, (heading, text) in enumerate(walked, start=1):
        sections.append(FetchedSection(id=f"s{n}", heading=heading, text=text))

    # Tables and figures wherever the article keeps them: in the body, in
    # <floats-group> (where MDPI and others put every one), and in <back>.
    holders = [el for el in (body, article.find("floats-group"), article.find("back")) if el is not None]
    wraps = [w for holder in holders for w in _floats(holder, "table-wrap")]
    n = 0
    for wrap in wraps:
        notes, marks = _footnotes(wrap)
        caption = _caption(wrap)
        # A table given only as an image has no rows; its caption still says
        # what it is, and is kept as the table's text.
        lines = _table_rows(wrap, marks) or ([caption] if caption else [])
        if lines:
            n += 1
            sections.append(FetchedSection(
                id=f"t{n}", heading=caption or f"Table {n}", text="\n".join(lines + notes),
            ))

    n = 0
    for fig in (f for holder in holders for f in _floats(holder, "fig")):
        caption = _caption(fig)
        if caption:
            n += 1
            sections.append(FetchedSection(id=f"f{n}", heading=f"Figure {n}", text=caption))

    return FetchResult(
        paperId=paper_id, pmcid=pmcid, status="complete", fetchedAt=now,
        license=_license(article), sections=sections, bytes=len(xml.encode("utf-8")),
    )


# ── persistence ────────────────────────────────────────────────────────


def _path(paper_id: str) -> Path:
    return FULLTEXT_DIR / f"{paper_id}.json"


def cached(paper_id: str) -> FetchResult | None:
    path = _path(paper_id)
    if not path.exists():
        return None
    return FetchResult.model_validate_json(path.read_text(encoding="utf-8"))


def _persist(result: FetchResult) -> FetchResult:
    atomic.write_text(_path(result.paperId), result.model_dump_json(indent=2) + "\n")
    return result


def fetch_paper(paper: dict[str, Any], *, force: bool = False) -> FetchResult:
    """Resolve, fetch, split, persist. Returns the cached result when one
    exists unless `force`, so the batch is idempotent and a miss is not
    re-asked.

    A MISS is cached: no open-access text, a 404, a document with nothing in
    it. An OUTAGE is not — a timeout, a connection that dropped, a 5xx that
    survived the retry — because that is the network's condition and not the
    paper's, and a batch that cached it would show every paper a brief outage
    touched as halted until somebody forced each one by hand."""
    paper_id = str(paper["id"])
    if not force:
        hit = cached(paper_id)
        if hit is not None:
            return hit

    now = datetime.now(timezone.utc).isoformat()
    try:
        pmcid = resolve_pmcid(paper)
    except (httpx.TransportError, Transient) as e:
        return FetchResult(
            paperId=paper_id, status="failed:fetch", fetchedAt=now,
            reason=f"PMCID lookup failed, not cached — try again: {e}",
        )
    except (httpx.HTTPError, NetworkRefused, ValueError) as e:
        return _persist(FetchResult(
            paperId=paper_id, status="failed:fetch", reason=f"PMCID lookup failed: {e}", fetchedAt=now,
        ))
    if not pmcid:
        what = paper.get("doi") or paper.get("pmid") or "no identifier"
        return _persist(FetchResult(
            paperId=paper_id, status="failed:fetch", fetchedAt=now,
            reason=f"no open-access full text on Europe PMC for {what}",
        ))
    try:
        xml = fetch_fulltext(pmcid)
    except (httpx.TransportError, Transient) as e:
        return FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:fetch", fetchedAt=now,
            reason=f"not cached — try again: {e}",
        )
    except (httpx.HTTPError, NetworkRefused) as e:
        return _persist(FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:fetch", reason=str(e), fetchedAt=now,
        ))
    return _persist(split_jats(xml, paper_id=paper_id, pmcid=pmcid))


def status_of(paper_id: str) -> IntakeStatus | None:
    """A paper's fetch state, summarised for `GET /api/intake/status`."""
    result = cached(paper_id)
    if result is None:
        return None
    return IntakeStatus(
        paperId=paper_id,
        pmcid=result.pmcid,
        ingest=result.status,
        textSource="full-text" if result.status == "complete" else "curation-note",
        sections=len(result.sections),
        tables=sum(1 for s in result.sections if s.id.startswith("t")),
        license=(result.license.href or result.license.text) if result.license else None,
        fetchedAt=result.fetchedAt,
        reason=result.reason,
    )


def all_statuses() -> dict[str, IntakeStatus]:
    if not FULLTEXT_DIR.exists():
        return {}
    out: dict[str, IntakeStatus] = {}
    for path in sorted(FULLTEXT_DIR.glob("*.json")):
        status = status_of(path.stem)
        if status is not None:
            out[path.stem] = status
    return out


def overlay_papers() -> dict[str, OverlayPaper]:
    """Every cached fetch as the overlay's `papers` map (§2.1).

    A success carries the paper's own sections and the licence string; a
    failure carries its status and reason and no sections, so the store keeps
    the seed's curation note for it and the board can say why it halted.
    """
    out: dict[str, OverlayPaper] = {}
    if not FULLTEXT_DIR.exists():
        return out
    for path in sorted(FULLTEXT_DIR.glob("*.json")):
        result = cached(path.stem)
        if result is None:
            continue
        ok = result.status == "complete"
        out[path.stem] = OverlayPaper(
            ingest=result.status,
            textSource="full-text" if ok else "curation-note",
            sections=result.sections if ok else [],
            license=(result.license.href or result.license.text) if result.license else None,
            fetchedAt=result.fetchedAt,
            reason=result.reason,
        )
    return out


# ── batch ──────────────────────────────────────────────────────────────


def _papers() -> list[dict[str, Any]]:
    from .corpus import load_corpus

    return load_corpus().papers


def fetch_all(papers: list[dict[str, Any]], *, force: bool = False) -> list[FetchResult]:
    """Every paper with a PMCID first, then the DOI-only and PMID-only ones
    through `resolve_pmcid`. Papers with no identifier at all are skipped
    without a request — there is nothing to ask."""
    ordered = sorted(
        (p for p in papers if p.get("pmcid") or p.get("doi") or p.get("pmid")),
        key=lambda p: (0 if p.get("pmcid") else 1, str(p["id"])),
    )
    return [fetch_paper(p, force=force) for p in ordered]


def _print_table(results: list[FetchResult]) -> None:
    print(f"{'id':<6} {'pmcid':<13} {'sections':>8} {'tables':>6}  {'licence':<44} {'bytes':>8}  status")
    for r in results:
        tables = sum(1 for s in r.sections if s.id.startswith("t"))
        lic = ((r.license.href or r.license.text or "") if r.license else "")[:44]
        print(
            f"{r.paperId:<6} {(r.pmcid or '-'):<13} {len(r.sections):>8} {tables:>6}  {lic:<44} "
            f"{r.bytes:>8}  {r.status}{' — ' + r.reason if r.reason else ''}"
        )
    ok = sum(1 for r in results if r.status == "complete")
    print(f"\n{ok} of {results and len(results)} fetched with full text")


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
    force = "--force" in argv
    if "--all" in argv:
        results = fetch_all(_papers(), force=force)
        _print_table(results)
        # A miss is an answer and is cached; an outage is not (fetch_paper).
        # A result the cache does not hold is one this run could not get, and
        # the batch exits 1 for it so the nightly log shows a failed night
        # as one (OF-BLD-012 §B.8).
        unreached = [r.paperId for r in results if cached(r.paperId) != r]
        if unreached:
            print(f"{len(unreached)} not reached, will be asked again: {', '.join(unreached)}")
        return 1 if unreached else 0
    ids = [a for a in argv if not a.startswith("--")]
    if not ids:
        print("usage: python -m openferment_core.intake --all [--force] | <paperId> [...]")
        return 2
    by_id = {p["id"]: p for p in _papers()}
    results = []
    for paper_id in ids:
        if paper_id not in by_id:
            print(f"{paper_id}: not in the corpus")
            return 1
        results.append(fetch_paper(by_id[paper_id], force=force))
    _print_table(results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
