"""The collectors: what openFerment fetches or is given, as Sci RAG Kit's
corpus entries (ADR-002; execution prompt §8.2).

FIVE COLLECTORS. A paper on Europe PMC is fetched as JATS XML, named by its
PMCID, its DOI or its PMID (`europepmc`). A report on OSTI is fetched as its
PDF, with its record for the citation (`osti`). A strain entry of the
Saccharomyces Genome Database is fetched as the JSON its backend serves
(`sgd`). A file a person uploads (`upload`) and text a person pastes
(`paste`) are taken as given. Each becomes a `Collected`: the text as
Markdown, a heading a section, and what is known of its citation and its
licence. `kit.ingest` stores it in the kit and links it to the project.

Tables keep their rows. The numbers this project exists to find live in tables
far more often than in prose, and a table flattened into a paragraph loses the
one structure that says which number belongs to which condition. Every
<table-wrap> becomes its own section, one line per row, cells joined with a
bar, and its Markdown is a pipe table, which the kit keeps as one block: a
quote from it is a row, and a row is a fact.

Failure is a result, not an exception. A split returns a `FetchResult` whose
status is `failed:fetch` or `failed:parse` with a reason, and a collector
raises `NotCollected` with that reason, which Intake shows as it stands.

Every source is treated as a colleague's server. At most two requests a
second, a User-Agent that names the project and, when `OPENFERMENT_CONTACT` is
set in `core/.env`, somebody to write to, one retry on a 5xx, and nothing
else. An OSTI report is split by `split_pdf` into one section per page, its
text exactly as the PDF library read it. An SGD strain entry is split by
`split_sgd` into its description, its genotype and the references it cites,
its markup removed and nothing added.

The licence is read from the source and mapped to the kit's classes
(`licence_class`), failing closed: what is not plainly public domain or a
Creative Commons licence is `unknown`, and the kit leaves `unknown` out of
any scope that names classes.

Fixture mode (`OPENFERMENT_FIXTURES=1`) reads XML from `tests/fixtures/jats/`
(and a report from `osti/<id>.pdf` with its record at `osti/<id>.json`, a
strain entry from `sgd/<id>.json` beside it) and refuses the network. It
exists so the parsers and the collectors can be tested offline.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from ..models import FetchedSection, FetchLicense, FetchResult, FetchSource

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
# Where fixture mode reads from, overridable by environment and read once at
# import, so a whole service can be pointed at a fixture directory without
# touching anything fetched for real (§8.1).
_CORE = Path(__file__).parent.parent.parent


def _env_path(name: str, default: Path) -> Path:
    """An override from the environment. A relative one is taken from the
    repository root — the `pnpm intake:*` aliases run from core/, and a path
    typed at the root must not quietly land in core/core/."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else (_CORE.parent / path).resolve()


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


def _get(
    url: str,
    params: dict[str, str] | None = None,
    *,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = False,
) -> httpx.Response:
    """One GET with the project's manners: throttle, User-Agent, one retry on
    5xx. OSTI's purl answers with a redirect to the laboratory that holds the
    file, so a caller may ask for redirects to be followed."""
    if fixtures_only():
        raise NetworkRefused(f"OPENFERMENT_FIXTURES is set; refusing to GET {url}")
    headers = {**(headers or {}), "User-Agent": _user_agent()}
    last: httpx.Response | None = None
    for attempt in (1, 2):
        _throttle()
        response = httpx.get(
            url, params=params, headers=headers, timeout=TIMEOUT_S, follow_redirects=follow_redirects,
        )
        if response.status_code < 500:
            return response
        last = response
    assert last is not None
    return last


# ── resolution ─────────────────────────────────────────────────────────


def resolve_pmcid(paper: dict[str, Any]) -> str | None:
    """The PMCID to fetch for a paper's identifiers: its own when it carries
    one, else Europe PMC's answer for its DOI or PMID. None when there is no
    open-access full text. The search is one request, made only when the
    paper names no PMCID."""
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
# contributor and conflict statements. They are dropped as <ack>,
# <fn-group> and <ref-list> are, with every section below them. A
# supplementary section stays: its figure legends can hold values stated
# nowhere else (C4).
_BACK_SEC_TYPES = {
    "ack", "fn-group", "ref-list", "associated-data", "data-availability", "data-availability-statement",
    "contrib-info", "COI-statement", "author-contributions", "glossary", "funding-information",
    "funding-statement",
}
# The same statements often carry no sec-type at all, only their title (ten
# of the 31). A title is compared whole, so 'Funding of the pilot plant' is
# a section of the paper and 'Funding' is not.
_BACK_TITLES = {
    "acknowledgements", "acknowledgments", "acknowledgement", "acknowledgment",
    "author contributions", "author contribution", "authors' contributions", "authors contributions",
    "contributions", "credit authorship contribution statement", "author information",
    "funding", "funding statement", "funding information", "funding sources", "sources of funding",
    "financial support", "conflict of interest", "conflicts of interest", "conflict of interests",
    "conflict of interest statement", "competing interests", "competing interest",
    "declaration of competing interest", "declaration of interests", "disclosure", "disclosures",
    "data availability", "data availability statement", "availability of data and materials",
    "data access statement", "disclaimer", "institutional review board statement",
    "informed consent statement", "ethics statement", "ethics approval and consent to participate",
    "consent for publication", "declarations", "publisher's note", "abbreviations", "footnotes", "notes",
}
# Parts of a structured abstract that are not the abstract's argument.
_ABSTRACT_ASIDES = {
    "electronic supplementary material", "supplementary information", "supplementary material",
    "graphical abstract", "keywords",
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
# A linked citation outside a superscript is held between these two
# characters while a paragraph is assembled, so `_uncite` can drop a group
# of citations in brackets or parentheses and give any other back its text.
_CITE_OPEN, _CITE_CLOSE = "\ue000", "\ue001"
_CITE = "\ue000[^\ue001]*\ue001"
_CITES = rf"(?:\[\s*{_CITE}(?:\s*[,;\u2013\u2014\u2212-]?\s*{_CITE})*\s*\]|\(\s*{_CITE}(?:\s*[,;\u2013\u2014\u2212-]?\s*{_CITE})*\s*\))"
# A citation whose own text carries its brackets, as PLoS writes each one.
_BRACKETED = r"\ue000\s*[\[(][\d\s,;\u2013\u2212-]+[\])]\s*\ue001"
_UNCITE = (
    (re.compile(rf"(?<=\()\s*{_CITES}\s*[;,]\s*"), ""),          # '([13]; Fig. 4)'
    (re.compile(rf"(?<=[;,])\s*{_CITES}\s*[;,](?=\s)"), ""),       # '(kg−1; [13]; Fig. 4)'
    (re.compile(rf"\s*[;,]\s*{_CITES}(?=\s*\))"), ""),            # '(kg−1; [13])'
    (re.compile(rf"\s*{_CITES}"), ""),                               # '68% [10,56]'
    (re.compile(rf"\s*{_BRACKETED}(?:\s*[,;\u2013\u2014\u2212-]\s*{_BRACKETED})*"), ""),  # '<xref>[12]</xref>, <xref>[16]</xref>'
    (re.compile(r"\ue000([^\ue001]*)\ue001"), r"\1"),              # 'Lam et al. (2017)' is the sentence's words
)


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
    follows. On a number, a number or a signed expression is a power ('10⁶',
    '2⁴', '(3/5)²' read '10^6', '2^4', '(3/5)^2', and 2<sup>−ΔΔCt</sup> reads
    '2^−ΔΔCt'), unless it is a label of a footnote under this
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
    on_number = before[-1:].isdigit() or before[-1:] == ")"
    if _NUMERIC.fullmatch(exponent):
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
    elif on_number and exponent[:1] in "-+\u2212" and len(exponent) > 1:
        # A signed expression on a number is a power: '2<sup>−ΔΔCt</sup>'
        # reads 2^−ΔΔCt, never two minus ΔΔCt.
        if parts and parts[-1].rstrip() != parts[-1]:
            parts[-1] = parts[-1].rstrip()
        parts.append("^" + _group(exponent))
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
        exponent = rendered[1].strip()
        if exponent.startswith("^"):
            # An msup on nothing inside an exponent: B^(^2) is B^2.
            return f"{rendered[0]}{exponent}"
        return f"{rendered[0]}^{_group(exponent)}"
    if tag == "msub" and len(rendered) == 2:
        return f"{rendered[0]}{rendered[1]}"
    if tag == "msubsup" and len(rendered) == 3:
        sub = rendered[1].strip()
        if " " in sub:
            # A limit with an operator in it, ∑ from j = 1: grouped, so its
            # last term is not read as the base of the power after it.
            return f"{rendered[0]}_({sub})^{_group(rendered[2].strip())}"
        return f"{rendered[0]}{sub}^{_group(rendered[2].strip())}"
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
    paragraph. `marks` holds the footnote labels of the table being read.
    A linked citation is held between `_CITE_OPEN` and `_CITE_CLOSE` until
    `_text` settles it (`_uncite`)."""
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
        elif tag == "xref" and child.get("ref-type") == "bibr":
            parts.append(_CITE_OPEN + "".join(child.itertext()) + _CITE_CLOSE)
        elif tag == "sub":
            # '(SP)<sub> n </sub>' is (SP)n: the padding is the XML's.
            inner: list[str] = []
            _collect(child, inner, prose=prose, marks=marks)
            parts.append("".join(inner).strip())
        elif tag == "label" and _local(el.tag) == "disp-formula":
            label = _text(child).strip("() ")
            if label:
                parts.append(f" ({label}) ")
        elif tag == "disp-formula":
            parts.append(" ")
            _collect(child, parts, prose=prose, marks=marks)
            parts.append(" ")
        elif tag == "break":
            # 'Purification/<break/>Detection' is one word pair.
            if not (parts and parts[-1].endswith("/")):
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
    return _WS.sub(" ", _uncite("".join(parts))).strip()


def _uncite(text: str) -> str:
    """Drop every group of linked citations in brackets or parentheses,
    '68% [10,56]' → '68%', with the separator a dropped group leaves inside
    a parenthesis; a citation is never the paper's words, and a quote that
    holds '[10,56]' holds 10 and 56 as numbers beside the value. A linked
    citation outside such a group, 'as Lam et al. (2017) found', keeps its
    text."""
    for pattern, replacement in _UNCITE:
        text = pattern.sub(replacement, text)
    return text


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


def _title_key(sec: ET.Element) -> str:
    return _WS.sub(" ", _text(sec.find("title"))).strip().rstrip(".:").replace("\u2019", "'").lower()


def _structured(abstract: ET.Element) -> str:
    """A structured abstract, which has sections and no paragraph of its own:
    each part's heading and its words, 'Background The study.', leaving out
    the abstract's own title, its keywords and its supplement notes (O5)."""
    parts: list[str] = []
    for sec in abstract.iter("sec"):
        if sec.get("sec-type") == "kwd-group" or _title_key(sec) in _ABSTRACT_ASIDES | _BACK_TITLES:
            continue
        words = " ".join(p for p in (_text(sec.find("title")), _own_paragraphs(sec)) if p)
        if words:
            parts.append(words)
    return " ".join(parts)


def _is_back_matter(sec: ET.Element) -> bool:
    return (sec.get("sec-type") or "").strip() in _BACK_SEC_TYPES or _title_key(sec) in _BACK_TITLES


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
        # Below a match too: eLife nests each figure supplement inside its
        # figure (fig > p > fig), and `_caption` reads only its own caption.
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
                if label:
                    labels.add(label.rstrip(".):"))
                labels.update(_note_marks(item))
    return lines, frozenset(labels)


def _note_marks(fn: ET.Element) -> set[str]:
    """The marks that open notes inside one <fn>. B5 writes two notes in one
    paragraph, '<sup>1</sup> Same part … <sup>2</sup> Shortened …', so every
    superscript that follows no number is a label; one that follows a number,
    '10<sup>6</sup> cells', is a power and labels nothing."""
    marks: set[str] = set()
    for p in fn.iter("p"):
        seen = p.text or ""
        for child in p:
            if _local(child.tag) == "sup":
                before = seen.rstrip()[-1:]
                mark = _text(child).rstrip(".):")
                if mark and len(mark) <= 3 and not (before.isdigit() or before == ")"):
                    marks.add(mark)
            seen += "".join(child.itertext()) + (child.tail or "")
    return marks


def _table_rows(wrap: ET.Element, marks: frozenset[str] = frozenset()) -> list[str]:
    """One line per row, cells joined with ' | '. The row is the unit a quote
    from a table should be, because the row is what says which number goes
    with which condition, so the rows are laid out as the table's grid: an
    empty cell keeps its place, a cell that spans rows is repeated in every
    row it spans, and a header that spans columns is repeated over each of
    them, so every value sits under its own column."""
    lines: list[str] = []
    carried: dict[int, tuple[str, int]] = {}  # column → (text, rows still to fill)
    # Frontiers writes every header cell as <td>; inside <thead> it is a header.
    head = {id(tr) for thead in wrap.iter("thead") for tr in thead.iter("tr")}
    for row in wrap.iter("tr"):
        out: list[str] = []
        cells = [c for c in row if _local(c.tag) in ("th", "td")]
        # A lone cell across the row is a title or a note, written once (N3).
        alone = len(cells) == 1

        def take_carried() -> None:
            while len(out) in carried:
                text, left = carried[len(out)]
                if left <= 1:
                    del carried[len(out)]
                else:
                    carried[len(out)] = (text, left - 1)
                out.append(text)

        for cell in cells:
            take_carried()
            text = _text(cell, marks=marks)
            rows = _span(cell, "rowspan")
            header = (_local(cell.tag) == "th" or id(row) in head) and not alone
            for k in range(_span(cell, "colspan")):
                value = text if (k == 0 or header) else ""
                if rows > 1:
                    carried[len(out)] = (value, rows - 1)
                out.append(value)
        take_carried()
        if any(out):
            # No strip: a row that ends in empty cells keeps their slots, so
            # it splits on ' | ' into as many cells as its header (F3, F4, O3).
            lines.append(" | ".join(out))
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
    if not href and text:
        # I6: the URL is only in the sentence, '(http://…/by/4.0/).'
        found = re.search(r"https?://[^\s)\]>]+", text)
        if found:
            href = found.group(0).rstrip(".,;")
    return FetchLicense(href=href or None, text=text)


def split_jats(xml: str, *, paper_id: str = "", pmcid: str | None = None) -> FetchResult:
    """JATS XML → a FetchResult whose sections are the paper's own words.

    Order: the abstract first as 'abstract'; then every body <sec>, depth-first,
    as 's1', 's2', … with nested headings prefixed; then every <table-wrap> as
    't1', 't2', … one line per row of its grid, with its footnotes after the
    rows; then every <fig> caption as 'f1', 'f2', …. Tables and figures are
    found in the body, in <floats-group> and in <back>. <ref-list>, <ack> and
    <fn-group> are dropped, and so is a <sec> whose sec-type or whole title
    names back matter (`_BACK_SEC_TYPES`, `_BACK_TITLES`). A group of linked
    citations in brackets or parentheses is dropped (`_uncite`). The
    <license> element is read into `license`.

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
        text = _own_paragraphs(plain[0]) or _structured(plain[0]) or _text(plain[0])
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


# ── sources outside Europe PMC: OSTI and SGD ───────────────────────────

# Every page of the Saccharomyces Genome Database carries a rel="license" link
# to CC BY 4.0 whose image's alt text is 'Creative Commons License'; that link
# and those words are a strain entry's licence.
SGD_LICENCE = FetchLicense(href="http://creativecommons.org/licenses/by/4.0/", text="Creative Commons License")
NO_LICENCE = "The source states no licence."
# An NREL report says how it may be had in a sentence of its own, on its cover
# and often on every page after. The first of these found, in this order, is
# its licence text.
_AVAILABILITY = (
    re.compile(r"This report is available at no cost\b.{0,300}?\.(?=\s|$)", re.S),
    re.compile(r"Available electronically at \S+"),
)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^<>]*>")


class NotFetched(RuntimeError):
    """The source answered, and what it answered is not the text: a page
    served in place of a PDF. A miss, and cached as one."""


def source_of(paper: dict[str, Any]) -> FetchSource:
    """Where a paper's text is fetched: OSTI or the Saccharomyces Genome
    Database when its `sourceUrl` is on one of their hosts, Europe PMC
    otherwise."""
    host = (urlsplit(str(paper.get("sourceUrl") or "").strip()).hostname or "").lower()
    if host == "osti.gov" or host.endswith(".osti.gov"):
        return "osti"
    if host == "yeastgenome.org" or host.endswith(".yeastgenome.org"):
        return "sgd"
    return "europepmc"


def _last_segment(url: str) -> str:
    """The id at the end of a source address: an OSTI id, an SGD id."""
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]


def fetch_pdf(url: str) -> bytes:
    """An OSTI report's PDF, as bytes, with the redirects from OSTI's purl to
    the laboratory that holds the file followed. Raises on anything but a 200
    that is a PDF: served as application/pdf, or starting as a PDF starts.

    In fixture mode the file comes from tests/fixtures/osti/{id}.pdf and the
    network is never touched.
    """
    if fixtures_only():
        path = FIXTURE_ROOT / "osti" / f"{_last_segment(url)}.pdf"
        if not path.exists():
            raise NetworkRefused(f"fixture mode and no fixture at {path}")
        return path.read_bytes()
    response = _get(url, follow_redirects=True)
    if response.status_code >= 500:
        raise Transient(f"OSTI returned {response.status_code} for {url}")
    # OSTI asks a client to slow down with a 429, or by redirecting it to its
    # rate-limit page (seen 2026-10-30): the network's condition, asked again later.
    if response.status_code == 429 or "error429" in response.url.path:
        raise Transient(f"OSTI asked to slow down (its rate limit) for {url}")
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"OSTI returned {response.status_code} for {url}", request=response.request, response=response,
        )
    kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if kind != "application/pdf" and not response.content.startswith(b"%PDF-"):
        raise NotFetched(f"{url} answered {kind or 'with no content type'}, not a PDF")
    return response.content


def _report_licence(texts: list[str], source_url: str) -> FetchLicense:
    """The report's own availability sentence, its words as extracted with
    each run of white space read as one space, or `NO_LICENCE` when it holds
    none. The href is the report's record on OSTI."""
    osti_id = _last_segment(source_url)
    href = f"https://www.osti.gov/biblio/{osti_id}" if osti_id.isdigit() else (source_url or None)
    for pattern in _AVAILABILITY:
        for text in texts:
            found = pattern.search(text)
            if found:
                return FetchLicense(href=href, text=_WS.sub(" ", found.group(0)).strip())
    return FetchLicense(href=href, text=NO_LICENCE)


def split_pdf(data: bytes, *, paper_id: str = "", source_url: str = "") -> FetchResult:
    """An OSTI report's PDF → a FetchResult, one section per page.

    Page N is section `sN` under the heading 'Page N', its text exactly as
    pypdf extracted it: no reflow, no dehyphenation, its line breaks kept. A
    page with no text is left out and the numbering keeps to the pages, so
    `s7` is page 7 whatever came before it. Never a `t` or `f` id: those name
    tables and figures, and a page is neither.

    The licence is the report's availability sentence (`_report_licence`).
    A file that does not parse, or that has no text layer, is returned as
    `failed:parse` with the reason, never raised.
    """
    # Imported here, so a service whose environment predates the dependency
    # still starts and still fetches from Europe PMC.
    from pypdf import PdfReader

    now = datetime.now(timezone.utc).isoformat()
    try:
        texts = [page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages]
    except Exception as e:  # pypdf raises several kinds on a damaged file; each is a parse failure
        return FetchResult(
            paperId=paper_id, status="failed:parse", reason=f"the PDF did not parse: {e}",
            fetchedAt=now, bytes=len(data), source="osti",
        )
    sections = [
        FetchedSection(id=f"s{n}", heading=f"Page {n}", text=text)
        for n, text in enumerate(texts, start=1)
        if text.strip()
    ]
    if not sections:
        return FetchResult(
            paperId=paper_id, status="failed:parse",
            reason=f"the PDF has no text layer on any of its {len(texts)} pages",
            fetchedAt=now, bytes=len(data), source="osti",
        )
    return FetchResult(
        paperId=paper_id, status="complete", fetchedAt=now, license=_report_licence(texts, source_url),
        sections=sections, bytes=len(data), source="osti",
    )


def fetch_sgd(url: str) -> str:
    """A strain entry of the Saccharomyces Genome Database, as the JSON its
    backend serves. Raises on anything but a 200.

    In fixture mode the entry comes from tests/fixtures/sgd/{id}.json and the
    network is never touched.
    """
    if fixtures_only():
        path = FIXTURE_ROOT / "sgd" / f"{_last_segment(url)}.json"
        if not path.exists():
            raise NetworkRefused(f"fixture mode and no fixture at {path}")
        return path.read_text(encoding="utf-8")
    response = _get(url, headers={"Accept": "application/json"})
    if response.status_code >= 500:
        raise Transient(f"the Saccharomyces Genome Database returned {response.status_code} for {url}")
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"the Saccharomyces Genome Database returned {response.status_code} for {url}",
            request=response.request, response=response,
        )
    return response.text


def _html_words(value: object) -> str:
    """SGD's markup as words: tags removed, entities read ('MAT&alpha;' is
    MATα), white space collapsed. Nothing is added."""
    if not isinstance(value, str):
        return ""
    return _WS.sub(" ", html.unescape(_HTML_TAG.sub("", value))).strip()


def split_sgd(text: str, *, paper_id: str = "") -> FetchResult:
    """An SGD strain entry's JSON → a FetchResult whose sections are the
    database's own words.

    'abstract' is the entry's description and then its paragraph, a line
    each; then `s1`, `s2`, … are its genotype and the references its
    paragraph cites, one citation a line, each when the entry has it. Markup
    is removed (`_html_words`) and nothing SGD did not write is added: the
    assembly's figures, the links and the contigs are left out, because none
    of them is a sentence. The licence is `SGD_LICENCE`. JSON that does not
    parse, or an entry that holds none of these, is returned as
    `failed:parse` with the reason, never raised.
    """
    now = datetime.now(timezone.utc).isoformat()
    size = len(text.encode("utf-8"))
    try:
        entry = json.loads(text)
    except ValueError as e:
        return FetchResult(
            paperId=paper_id, status="failed:parse", reason=f"the SGD entry did not parse as JSON: {e}",
            fetchedAt=now, bytes=size, source="sgd",
        )
    if not isinstance(entry, dict):
        return FetchResult(
            paperId=paper_id, status="failed:parse", reason="the SGD entry is not a JSON object",
            fetchedAt=now, bytes=size, source="sgd",
        )
    paragraph = entry.get("paragraph") if isinstance(entry.get("paragraph"), dict) else {}
    sections: list[FetchedSection] = []
    abstract = "\n".join(p for p in (_html_words(entry.get("description")), _html_words(paragraph.get("text"))) if p)
    if abstract:
        sections.append(FetchedSection(id="abstract", heading="Description", text=abstract))
    more: list[tuple[str, str]] = []
    genotype = _html_words(entry.get("genotype"))
    if genotype:
        more.append(("Genotype", genotype))
    cited = [_html_words(r.get("citation")) for r in paragraph.get("references") or [] if isinstance(r, dict)]
    if any(cited):
        more.append(("References", "\n".join(c for c in cited if c)))
    for n, (heading, words) in enumerate(more, start=1):
        sections.append(FetchedSection(id=f"s{n}", heading=heading, text=words))
    if not sections:
        return FetchResult(
            paperId=paper_id, status="failed:parse",
            reason="the SGD entry holds no description, paragraph, genotype or reference",
            fetchedAt=now, bytes=size, source="sgd",
        )
    return FetchResult(
        paperId=paper_id, status="complete", fetchedAt=now, license=SGD_LICENCE,
        sections=sections, bytes=size, source="sgd",
    )


# ── citation metadata ──────────────────────────────────────────────────


@dataclass
class Citation:
    """What a source says of itself: enough for the kit's citation line."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    journal: str | None = None
    pmcid: str | None = None


def _year(value: object) -> int | None:
    found = re.search(r"\b(1[5-9]\d\d|2\d\d\d)\b", str(value or ""))
    return int(found.group(1)) if found else None


def jats_citation(xml: str) -> Citation:
    """The article's own front matter: its title, its authors as 'Given
    Surname', its year of publication, its DOI, its journal and its PMCID.
    What the XML does not hold stays empty."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return Citation()
    article = root if root.tag == "article" else root.find(".//article")
    if article is None:
        return Citation()
    meta = article.find("front/article-meta")
    if meta is None:
        return Citation()
    authors = []
    for contrib in meta.findall(".//contrib-group/contrib"):
        if contrib.get("contrib-type", "author") != "author":
            continue
        name = contrib.find("name")
        if name is not None:
            given, surname = _text(name.find("given-names")), _text(name.find("surname"))
            full = " ".join(p for p in (given, surname) if p)
        else:
            full = _text(contrib.find("collab"))
        if full:
            authors.append(full)
    ids = {el.get("pub-id-type"): _text(el) for el in meta.findall("article-id")}
    dates = meta.findall("pub-date")
    preferred = [d for d in dates if d.get("pub-type") in ("epub", "ppub") or d.get("date-type") == "pub"] or dates
    year = next((_year(_text(d.find("year"))) for d in preferred if _text(d.find("year"))), None)
    journal = _text(article.find("front/journal-meta/journal-title-group/journal-title")) or _text(
        article.find("front/journal-meta/journal-title")
    )
    pmcid = ids.get("pmc") or ids.get("pmcid")
    if pmcid and not pmcid.upper().startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    return Citation(
        title=_text(meta.find("title-group/article-title")),
        authors=authors,
        year=year,
        doi=ids.get("doi") or None,
        journal=journal or None,
        pmcid=pmcid or None,
    )


# ── licences, as the kit's classes ─────────────────────────────────────

_CC_HREF = re.compile(r"creativecommons\.org/(?:licen[cs]es/(?P<kind>[a-z-]+)|publicdomain/(?P<pd>zero|mark))", re.I)
_CC_WORDS = re.compile(
    r"creative\s+commons\s+(?:(?P<zero>cc0|zero)|attribution(?P<rest>[\s-]*(?:non-?commercial|share-?alike|no-?deriv\w*|[\s-])*)?)",
    re.I,
)
_CC_SHORT = re.compile(r"\bCC[\s-]*(?P<zero>0)\b|\bCC[\s-]+BY(?P<rest>(?:[\s-]+(?:NC|SA|ND)\b)*)", re.I)


def licence_class(licence: FetchLicense | None) -> str:
    """The kit's class for a licence as the source stated it: `public` for a
    public domain dedication (CC0, the public domain mark), `open_commercial`
    for CC BY and CC BY-SA, `open_noncommercial` for any non-commercial
    Creative Commons licence, and `unknown` for everything else, a
    no-derivatives licence among it. Fails closed: the kit leaves `unknown`
    out of any scope that names classes."""
    if licence is None:
        return "unknown"
    for value in (licence.href or "", licence.text or ""):
        found = _CC_HREF.search(value)
        if found:
            if found.group("pd"):
                return "public"
            parts = found.group("kind").lower().split("-")
            if "nc" in parts:
                return "open_noncommercial"
            if "nd" in parts:
                return "unknown"
            return "open_commercial" if parts[0] == "by" else "unknown"
    words = _CC_WORDS.search(licence.text or "")
    if words:
        if words.group("zero"):
            return "public"
        rest = (words.group("rest") or "").lower().replace(" ", "").replace("-", "")
        if "noncommercial" in rest:
            return "open_noncommercial"
        if "noderiv" in rest:
            return "unknown"
        return "open_commercial"
    short = _CC_SHORT.search(licence.text or "")
    if short:
        if short.group("zero"):
            return "public"
        parts = (short.group("rest") or "").upper().split()
        parts = [x for part in parts for x in part.split("-") if x]
        if "NC" in parts:
            return "open_noncommercial"
        return "unknown" if "ND" in parts else "open_commercial"
    return "unknown"


# ── the text, as the kit reads it ──────────────────────────────────────


def _lines_of_table(text: str) -> str:
    return "\n".join(f"| {line.strip()} |" for line in text.splitlines() if line.strip())


def markdown(title: str, sections: list[FetchedSection]) -> str:
    """The document as Markdown: the title as its one H1, then each section
    under its own heading, a table (`t1`, `t2`, …) as a pipe table so the
    kit keeps it as one block. The words are the source's own."""
    parts = [f"# {title.strip() or 'Untitled'}"]
    for section in sections:
        parts.append(f"## {section.heading.strip() or section.id}")
        parts.append(_lines_of_table(section.text) if section.id.startswith("t") else section.text.strip())
    return "\n\n".join(p for p in parts if p) + "\n"


# ── the collectors ─────────────────────────────────────────────────────

#: What a person may upload: the kit's parsers' suffixes, and JATS XML.
UPLOAD_SUFFIXES = (".pdf", ".md", ".markdown", ".txt", ".html", ".htm", ".xml")


class NotCollected(RuntimeError):
    """A source that gave nothing to store, with the reason in words: no
    open-access text, a file that did not parse, an identifier not
    recognised. `transient` marks the network's condition (an outage), which
    a later attempt may not meet."""

    def __init__(self, reason: str, *, transient: bool = False) -> None:
        super().__init__(reason)
        self.transient = transient


@dataclass
class Collected:
    """One document, ready for the kit: its Markdown (or, for a file the kit
    parses itself, its bytes and suffix), its citation and its licence."""

    collector: str
    identifier: str
    citation: Citation
    licence: FetchLicense | None
    text: str = ""
    data: bytes = b""
    suffix: str = ".md"
    url: str | None = None
    sections: int = 0
    tables: int = 0
    #: The class a person chose for what they uploaded or pasted, which
    #: stands in place of one read from the licence.
    stated_class: str | None = None

    @property
    def licence_class(self) -> str:
        return self.stated_class or licence_class(self.licence)

    def selection(self, reason: str = "") -> dict[str, Any]:
        """What is kept on the project's link: what was asked for, from
        where, the licence as the source stated it, and why."""
        return {
            "collector": self.collector,
            "identifier": self.identifier,
            "url": self.url,
            "pmcid": self.citation.pmcid,
            "licence": self.licence.model_dump() if self.licence else None,
            "reason": reason,
            "collectedAt": datetime.now(timezone.utc).isoformat(),
        }

    def write(self, folder: Path) -> Path:
        """The document as a file in `folder`, for the kit's ingester."""
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", self.identifier).strip("-.")[:80] or "document"
        path = folder / f"{name}{self.suffix}"
        if self.data:
            path.write_bytes(self.data)
        else:
            path.write_text(self.text, encoding="utf-8")
        return path


def _complete(result: FetchResult) -> FetchResult:
    if result.status != "complete":
        raise NotCollected(result.reason or result.status)
    return result


_PMCID = re.compile(r"^PMC\d+$", re.I)
_DOI = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)$", re.I)
_PMID = re.compile(r"^(?:pmid:?\s*)(\d{1,9})$", re.I)
_OSTI = re.compile(r"^(?:osti:?\s*)(\d{1,10})$", re.I)
_SGD = re.compile(r"^(?:sgd:?\s*)(S\d{9})$", re.I)
# Where SGD serves a strain entry as JSON, by its SGDID.
SGD_STRAIN = "https://www.yeastgenome.org/backend/strain"


def europepmc_hit(query: str) -> dict[str, Any] | None:
    """Europe PMC's first open-access hit for a search, or None."""
    response = _get(
        f"{EUROPE_PMC}/search", {"query": query, "format": "json", "resultType": "lite", "pageSize": "5"},
    )
    if response.status_code >= 500:
        raise Transient(f"Europe PMC returned {response.status_code} looking up {query}")
    if response.status_code != 200:
        return None
    for hit in response.json().get("resultList", {}).get("result", []):
        if hit.get("isOpenAccess") == "Y" and hit.get("pmcid"):
            return dict(hit)
    return None


def _network(what: str, call: Any, *args: Any) -> Any:
    try:
        return call(*args)
    except (httpx.TransportError, Transient) as e:
        raise NotCollected(f"{what} could not be reached; try again: {e}", transient=True) from e
    except (httpx.HTTPError, NetworkRefused, NotFetched, ValueError) as e:
        raise NotCollected(f"{what}: {e}") from e


def europepmc(identifier: str) -> Collected:
    """A paper's open-access full text from Europe PMC, by PMCID, DOI or PMID."""
    asked = identifier.strip()
    pmcid = asked.upper() if _PMCID.match(asked) else None
    if pmcid is None:
        doi, pmid = _DOI.match(asked), _PMID.match(asked)
        if doi:
            query = f'DOI:"{doi.group(1)}"'
        elif pmid:
            query = f"EXT_ID:{pmid.group(1)} AND SRC:MED"
        else:
            raise NotCollected(f"{asked!r} is not a PMCID, a DOI or a PMID")
        hit = _network("Europe PMC", europepmc_hit, query)
        if hit is None:
            raise NotCollected(f"Europe PMC has no open-access full text for {asked}")
        pmcid = str(hit["pmcid"])
    xml = _network("Europe PMC", fetch_fulltext, pmcid)
    result = _complete(split_jats(xml, paper_id=asked, pmcid=pmcid))
    citation = jats_citation(xml)
    citation.pmcid = citation.pmcid or pmcid
    title = citation.title or pmcid
    return Collected(
        collector="europepmc", identifier=asked, citation=citation, licence=result.license,
        text=markdown(title, result.sections), url=f"https://europepmc.org/article/PMC/{pmcid.upper()}",
        sections=len(result.sections), tables=sum(1 for s in result.sections if s.id.startswith("t")),
    )


OSTI = "https://www.osti.gov"


def osti_record(osti_id: str) -> dict[str, Any]:
    """OSTI's record of a report, as its API serves it ({} when it has none).
    In fixture mode, tests/fixtures/osti/{id}.json, or {}."""
    if fixtures_only():
        path = FIXTURE_ROOT / "osti" / f"{osti_id}.json"
        found = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    else:
        response = _get(f"{OSTI}/api/v1/records/{osti_id}", headers={"Accept": "application/json"})
        if response.status_code >= 500:
            raise Transient(f"OSTI returned {response.status_code} for record {osti_id}")
        if response.status_code != 200:
            return {}
        found = response.json()
    # The API answers with a list of one record.
    if isinstance(found, list):
        found = found[0] if found else {}
    return found if isinstance(found, dict) else {}


def osti(identifier: str) -> Collected:
    """An OSTI report's PDF, by its OSTI id (`OSTI:1234567`) or an osti.gov address."""
    asked = identifier.strip()
    matched = _OSTI.match(asked)
    osti_id = matched.group(1) if matched else _last_segment(asked)
    if not osti_id.isdigit():
        raise NotCollected(f"{asked!r} names no OSTI report")
    url = f"{OSTI}/servlets/purl/{osti_id}"
    result = _complete(split_pdf(_network("OSTI", fetch_pdf, url), paper_id=asked, source_url=url))
    record = _network("OSTI", osti_record, osti_id)
    authors = [re.sub(r"\s*\[.*?\]\s*", " ", str(a)).strip() for a in record.get("authors") or []]
    citation = Citation(
        title=str(record.get("title") or f"OSTI report {osti_id}"),
        authors=[a for a in authors if a],
        year=_year(record.get("publication_date")),
        doi=str(record["doi"]) if record.get("doi") else None,
        journal=str(record["journal_name"]) if record.get("journal_name") else None,
    )
    return Collected(
        collector="osti", identifier=asked, citation=citation, licence=result.license,
        text=markdown(citation.title, result.sections), url=f"{OSTI}/biblio/{osti_id}",
        sections=len(result.sections),
    )


def sgd(identifier: str) -> Collected:
    """A strain entry of the Saccharomyces Genome Database, by its address."""
    asked = identifier.strip()
    host = (urlsplit(asked).hostname or "").lower()
    if not (host == "yeastgenome.org" or host.endswith(".yeastgenome.org")):
        raise NotCollected(f"{asked!r} is not an address on yeastgenome.org")
    text = _network("The Saccharomyces Genome Database", fetch_sgd, asked)
    result = _complete(split_sgd(text, paper_id=asked))
    entry = json.loads(text)
    title = _html_words(entry.get("display_name")) or _last_segment(asked)
    return Collected(
        collector="sgd", identifier=asked, citation=Citation(title=f"{title} (Saccharomyces Genome Database)"),
        licence=result.license, text=markdown(title, result.sections), url=asked, sections=len(result.sections),
    )


def by_identifier(identifier: str) -> Collected:
    """The collector an identifier names: an osti.gov address or `OSTI:<id>`
    is OSTI's, a yeastgenome.org address or `SGD:<SGDID>` SGD's, and a
    PMCID, a DOI or `PMID:<id>` Europe PMC's. A bare number is refused, since
    PMIDs and OSTI ids look alike."""
    asked = identifier.strip()
    if not asked:
        raise NotCollected("no identifier given")
    host = (urlsplit(asked).hostname or "").lower()
    if host == "osti.gov" or host.endswith(".osti.gov") or _OSTI.match(asked):
        return osti(asked)
    if host == "yeastgenome.org" or host.endswith(".yeastgenome.org"):
        return sgd(asked)
    if strain := _SGD.match(asked):
        return sgd(f"{SGD_STRAIN}/{strain.group(1).upper()}")
    if asked.isdigit():
        raise NotCollected(f"{asked} could be a PMID or an OSTI id; write PMID:{asked} or OSTI:{asked}")
    return europepmc(asked)


def _stated(chosen: str) -> str | None:
    """A class a person chose, checked against the kit's; None for `unknown`
    or nothing chosen, so the licence's own words still count."""
    from sci_rag.licensing import LICENSE_CLASSES

    cleaned = (chosen or "").strip()
    if not cleaned or cleaned == "unknown":
        return None
    if cleaned not in LICENSE_CLASSES:
        raise NotCollected(f"{cleaned!r} is not a licence class; the classes are {', '.join(LICENSE_CLASSES)}")
    return cleaned


def uploaded(filename: str, data: bytes, *, title: str = "", licence_class: str = "", licence: str = "") -> Collected:
    """A file a person uploaded. A PDF is split a page a section and JATS XML
    as Europe PMC's is; Markdown, HTML and plain text go to the kit as they
    are. `licence_class` is the class the person chose and `licence` what
    they say of it in words."""
    name = Path(unquote(filename or "")).name
    suffix = Path(name).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise NotCollected(f"{name or 'the file'} is not one of {', '.join(UPLOAD_SUFFIXES)}")
    if not data:
        raise NotCollected(f"{name} is empty")
    chosen = _stated(licence_class)
    stated = FetchLicense(text=licence.strip()) if licence.strip() else None
    stem = Path(name).stem
    if suffix == ".pdf":
        result = _complete(split_pdf(data, paper_id=name))
        result_title = title.strip() or stem
        return Collected(
            collector="upload", identifier=name, citation=Citation(title=result_title), licence=stated,
            text=markdown(result_title, result.sections), sections=len(result.sections), stated_class=chosen,
        )
    if suffix == ".xml":
        xml = data.decode("utf-8", errors="replace")
        result = _complete(split_jats(xml, paper_id=name))
        citation = jats_citation(xml)
        citation.title = title.strip() or citation.title or stem
        return Collected(
            collector="upload", identifier=name, citation=citation, licence=stated or result.license,
            text=markdown(citation.title, result.sections), sections=len(result.sections),
            tables=sum(1 for s in result.sections if s.id.startswith("t")), stated_class=chosen,
        )
    return Collected(
        collector="upload", identifier=name, citation=Citation(title=title.strip() or _own_title(data, suffix) or stem),
        licence=stated, data=data, suffix=suffix, stated_class=chosen,
    )


_MD_TITLE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_HTML_TITLE = re.compile(r"<title[^>]*>(.*?)</title>|<h1[^>]*>(.*?)</h1>", re.I | re.S)


def _own_title(data: bytes, suffix: str) -> str:
    """The title a Markdown or HTML file gives itself: its first H1, or its
    <title>. Empty when it gives none."""
    text = data[:200_000].decode("utf-8", errors="replace")
    if suffix in (".md", ".markdown"):
        found = _MD_TITLE.search(text)
        return found.group(1).strip() if found else ""
    if suffix in (".html", ".htm"):
        found = _HTML_TITLE.search(text)
        return _html_words(found.group(1) or found.group(2)) if found else ""
    return ""


def pasted(title: str, text: str, *, url: str = "", licence_class: str = "", licence: str = "") -> Collected:
    """Text a person pasted, under the title they gave it."""
    if not title.strip():
        raise NotCollected("pasted text needs a title")
    if not text.strip():
        raise NotCollected("nothing was pasted")
    chosen = _stated(licence_class)
    stated = FetchLicense(href=url.strip() or None, text=licence.strip()) if licence.strip() else None
    return Collected(
        collector="paste", identifier=title.strip(), citation=Citation(title=title.strip()), licence=stated,
        text=f"# {title.strip()}\n\n{text.strip()}\n", url=url.strip() or None, stated_class=chosen,
    )


def folder() -> tempfile.TemporaryDirectory[str]:
    """Where a collected document waits for the kit's ingester, removed after."""
    return tempfile.TemporaryDirectory(prefix="openferment-collected-")
