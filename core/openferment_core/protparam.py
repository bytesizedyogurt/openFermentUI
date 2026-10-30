"""A protein product's properties from its sequence (OF-BLD-020 §7.1, D12).

Biopython is an open-source library of tools for biological sequences. Its
ProtParam module (`Bio.SeqUtils.ProtParam.ProteinAnalysis`) computes, from a
protein's one-letter amino-acid sequence, its molecular weight, its
isoelectric point, its molar extinction coefficients at 280 nm (with every
cysteine reduced, and with every pair of cysteines a cystine) and its GRAVY
(the grand average of hydropathy). pureOS's proposer (§7.2) reads them: a
capture step keyed on the isoelectric point, a membrane's cut-off on the
molecular weight.

EVERY NUMBER IS THE LIBRARY'S. Nothing here computes a property or types a
value: the sequence goes to `ProteinAnalysis` with the library's own defaults
(average masses, Kyte and Doolittle's hydropathy scale), read from its
signature and named in the basis, and the answer is what it returns.

A SEQUENCE IS NAMED, NEVER TYPED BY A MODEL. A product entry carries its own
chain (`sequence`, with `sequenceSource` saying where it was read, a UniProt
accession say) in the products catalogue the corpus carries
(`corpus.Corpus.products`); the endpoints take a product id, and `protparam()`
takes a sequence only from a caller that names its source. No product entry
carries a sequence (none is invented), so every product's properties are
missing: `ProtParamMissing`, a 404 whose words say the entry carries none.

REFUSED WHOLE. A sequence holding anything but the twenty standard amino
acids' one-letter codes (the library's own `protein_letters`), in upper case,
is refused in words naming each letter and its positions, and an empty one is
refused too (`ProtParamRefused`, a 422). Nothing is repaired: no letter is
dropped, read as another or upper-cased.

THE ANSWER IS ONE ARTIFACT. `artifacts.compute` keeps one `protparam`
artifact, versioned with Biopython's installed version; its basis names the
sequence and its source (a product entry, or a record), the library and its
settings. A product entry's sequence is a `convention` input, so the answer is
`computed`; a record's takes the record's provenance.

    POST /api/protparam   {product}: computes (or returns the stored answer)
    GET  /api/protparam   ?product=: the stored answer, or none; computes nothing
"""
from __future__ import annotations

import inspect
from importlib.metadata import version as _version
from typing import Any, Mapping

from .models import Artifact, BasisInput, BasisSource, Evidence, ProtParam

TOOL = "protparam"
VERSION_WORDS = "protparam 1"
LIBRARY = "biopython"
# The library's own name, as the basis's `library` input and every label
# write it; the input adds the installed version, a label never does.
LIBRARY_NAME = "Biopython"
# The unit each of ProtParam's numbers is read in: daltons (grams per mole)
# for the mass, per molar per centimetre for the extinction coefficients at
# 280 nm, and none for the isoelectric point (a pH) and GRAVY (a mean over a
# hydropathy scale).
UNITS = {"molecularWeight": "Da", "isoelectricPoint": "", "extinctionReduced": "M⁻¹ cm⁻¹",
         "extinctionCystines": "M⁻¹ cm⁻¹", "gravy": ""}
HOW = {
    "molecularWeight": "ProteinAnalysis.molecular_weight, on the library's masses as the basis's `monoisotopic` names them",
    "isoelectricPoint": "ProteinAnalysis.isoelectric_point: the pH at which the library's own charge model gives the chain "
                        "no net charge",
    "extinctionReduced": "ProteinAnalysis.molar_extinction_coefficient at 280 nm, from the chain's tryptophans and "
                         "tyrosines, every cysteine reduced",
    "extinctionCystines": "ProteinAnalysis.molar_extinction_coefficient at 280 nm, every pair of cysteines a cystine",
    "gravy": "ProteinAnalysis.gravy on the hydropathy scale the basis names",
}
# What the evidence of an answer names, in the order a page shows them. A
# label is words and ids alone: the library by its name, never its version
# (the basis's `library` input carries that, and every evidence carries the
# basis), and the subject a product's or a record's id. So a claim that copies
# a label word for word copies no number (validate.find_number finds none;
# OF-BLD-020 §7.R, finding 33).
PROPERTIES = (
    ("molecularWeight", "Molecular weight"),
    ("isoelectricPoint", "Isoelectric point"),
    ("extinctionReduced", "Molar extinction coefficient, cysteines reduced"),
    ("extinctionCystines", "Molar extinction coefficient, cysteines paired as cystines"),
    ("gravy", "GRAVY (grand average of hydropathy)"),
)
# A refusal names at most this many positions of one letter, then says how
# many more: a page and a log line stay readable.
SHOWN_POSITIONS = 10


class ProtParamRefused(ValueError):
    """The sequence cannot be computed from, in words."""


class ProtParamMissing(LookupError):
    """No sequence to compute from: no such product, or its entry carries
    none. The property is missing, not refused (§7.2's proposer says so)."""


# ── the library ──────────────────────────────────────────────────────────


def library_version() -> str:
    return _version(LIBRARY)


def version() -> str:
    return f"{VERSION_WORDS} · biopython {library_version()}"


def standard_letters() -> str:
    """The twenty standard amino acids' one-letter codes, as the library holds them."""
    from Bio.Data.IUPACData import protein_letters

    return protein_letters


def library_defaults() -> dict[str, str]:
    """The settings ProtParam uses when nobody sets them, read from its own
    signatures: average or monoisotopic masses, and the hydropathy scale."""
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    return {
        "monoisotopic": str(inspect.signature(ProteinAnalysis.__init__).parameters["monoisotopic"].default),
        "hydropathy scale": str(inspect.signature(ProteinAnalysis.gravy).parameters["scale"].default),
    }


# ── the sequence ─────────────────────────────────────────────────────────


def _where(positions: list[int]) -> str:
    shown = ", ".join(str(p) for p in positions[:SHOWN_POSITIONS])
    more = len(positions) - SHOWN_POSITIONS
    return shown + (f" and {more} more" if more > 0 else "")


def check(sequence: Any) -> str:
    """The sequence as ProtParam will read it, or `ProtParamRefused` naming
    every letter outside the twenty standard amino acids and its positions
    (counted from 1). Nothing is repaired."""
    if not isinstance(sequence, str) or not sequence:
        raise ProtParamRefused("the sequence is empty: there is nothing for ProtParam to compute from")
    letters = set(standard_letters())
    bad: dict[str, list[int]] = {}
    for n, ch in enumerate(sequence, start=1):
        if ch not in letters:
            bad.setdefault(ch, []).append(n)
    if bad:
        said = "; ".join(f"{ch!r} at {_where(at)}" for ch, at in bad.items())
        raise ProtParamRefused(
            f"the sequence holds letters outside the twenty standard amino acids ({''.join(sorted(letters))}, upper "
            f"case): {said}. ProtParam computes from those twenty alone, so nothing is computed and no letter is "
            "dropped, upper-cased or read as another")
    return sequence


# ── the computation (registered with artifacts) ─────────────────────────


def _named(inputs: list[BasisInput], name: str) -> BasisInput | None:
    return next((i for i in inputs if i.name == name), None)


def _library_input() -> BasisInput:
    v = library_version()
    return BasisInput(name="library", value=f"{LIBRARY_NAME} {v}", unit="", source=BasisSource(
        kind="model", id=f"biopython@{v}",
        note="Bio.SeqUtils.ProtParam.ProteinAnalysis, as shipped: its masses, its charge model and its scales"))


def basis_inputs(sequence: str, source: BasisSource, product: str | None = None) -> list[BasisInput]:
    """The answer's basis: the sequence with its source, the product it is
    read for, the library and the settings it ran with (its own defaults,
    read from its signatures)."""
    seq = check(sequence)
    v = library_version()
    default = BasisSource(kind="model", id=f"biopython@{v}", note="ProtParam's own default, read from its signature")
    out = [BasisInput(name="sequence", value=seq, unit="", source=source)]
    if product:
        out.append(BasisInput(name="product", value=product, unit="", source=BasisSource(
            kind="convention", note="the product entry the sequence is read from")))
    out += [BasisInput(name=k, value=d, unit="", source=default) for k, d in library_defaults().items()]
    out.append(_library_input())
    return out


def _compute(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """ProtParam's answer, from the basis alone. Pure, so a replay recomputes it."""
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    seq_input = _named(inputs, "sequence")
    seq = check(str(seq_input.value))
    product = _named(inputs, "product")
    mono = str(_named(inputs, "monoisotopic").value) == "True"
    scale = str(_named(inputs, "hydropathy scale").value)
    pa = ProteinAnalysis(seq, monoisotopic=mono)
    reduced, cystines = pa.molar_extinction_coefficient()
    src = seq_input.source
    if product is not None:
        subject = f"the sequence of product {product.value}"
    elif src.kind == "record" and src.id:
        subject = f"the sequence of record {src.id}"
    else:
        subject = "a sequence"
    out = {
        "subject": subject,
        "product": str(product.value) if product is not None else None,
        "sequenceSource": src.note or (f"record {src.id}" if src.kind == "record" and src.id else src.kind),
        "length": len(seq),
        "library": str(_named(inputs, "library").value),
        "molecularWeight": pa.molecular_weight(),
        "isoelectricPoint": pa.isoelectric_point(),
        "extinctionReduced": reduced,
        "extinctionCystines": cystines,
        "gravy": pa.gravy(scale=scale),
        "units": dict(UNITS),
        "how": dict(HOW),
        "notes": [],
    }
    return ProtParam.model_validate(out).model_dump(mode="json")


def _register() -> None:
    from . import artifacts

    artifacts.register(TOOL, version(), _compute)


def _register_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(TOOL, _register)


_register_lazy()


# ── what callers use ─────────────────────────────────────────────────────


def protparam(sequence: str, *, source: BasisSource, product: str | None = None,
              records_by_id: Mapping[str, Any] | None = None) -> Artifact:
    """ProtParam's answer for `sequence`, computed or returned as stored: one
    `protparam` artifact whose basis names `source` (a product entry's
    `convention`, or a `record`; its provenance then enters the answer's).
    `ProtParamRefused` for an empty sequence or a letter outside the twenty."""
    from . import artifacts

    return artifacts.compute(TOOL, basis_inputs(sequence, source, product), records_by_id=records_by_id)


def products() -> list[dict[str, Any]]:
    """The products catalogue: each entry's id and name, and its sequence and
    source when it has one. No store holds a product catalogue yet, so it is
    empty (alpha 2.0 deleted the seed's, ADR-010); tests supply one here."""
    return []


def sequence_of(product: str) -> tuple[str, BasisSource]:
    """The product entry's own sequence and its source, or
    `ProtParamMissing` (no such product, or its entry carries no sequence) or
    `ProtParamRefused` (a sequence that names no source), in words."""
    pid = (product or "").strip()
    if not pid:
        raise ProtParamRefused("a product's properties name the product by its id")
    entry = next((p for p in products() if p.get("id") == pid), None)
    if entry is None:
        raise ProtParamMissing(f"there is no product {pid!r} in the products catalogue, so it carries no sequence to compute from")
    seq = entry.get("sequence")
    if not seq:
        raise ProtParamMissing(f"product {pid}'s entry carries no sequence, so its molecular weight, isoelectric point, "
                               "extinction coefficients and GRAVY are not computed: a sequence enters the products catalogue "
                               "with where it was read (sequenceSource), never invented")
    where = (entry.get("sequenceSource") or "").strip()
    if not where:
        raise ProtParamRefused(f"product {pid}'s entry carries a sequence and names no source for it; a sequence enters "
                               "with where it was read (sequenceSource), so nothing is computed from this one")
    return str(seq), BasisSource(kind="convention", note=f"product {pid}'s own sequence in the products catalogue, read from {where}")


def of_product(product: str) -> Artifact:
    """ProtParam's answer for a product entry's own sequence, computed or
    returned as stored."""
    seq, source = sequence_of(product)
    return protparam(seq, source=source, product=(product or "").strip())


def stored(product: str) -> Artifact | None:
    """The answer stored for a product entry's sequence, or None: a read,
    which computes nothing. The same refusals as `of_product`."""
    from . import artifacts

    seq, source = sequence_of(product)
    inputs = basis_inputs(seq, source, (product or "").strip())
    reg = artifacts.registered(TOOL)
    try:
        return artifacts.get(artifacts.artifact_id(reg.tool, reg.version_for(inputs), inputs))
    except artifacts.ArtifactNotFound:
        return None


def output_of(art: Artifact) -> ProtParam:
    if art.tool != TOOL:
        raise ProtParamRefused(f"artifact {art.id} is a {art.tool} artifact, not a {TOOL} answer")
    return ProtParam.model_validate(art.output)


def evidence_of(art: Artifact) -> list[Evidence]:
    """One Evidence a property (`<artifact id>:<key>`), each carrying the
    artifact's basis, so a reason or a claim cites the one value it reads.
    Its label names the library and not its version, which the basis holds."""
    from . import artifacts

    o = output_of(art)
    return [Evidence(id=f"{art.id}:{key}", label=f"{what} of {o.subject}, as {LIBRARY_NAME}'s ProtParam computes it",
                     value=getattr(o, key), unit=o.units.get(key, ""), provenance=art.provenance,
                     basis=artifacts.basis_of(art), figure=None)
            for key, what in PROPERTIES]
