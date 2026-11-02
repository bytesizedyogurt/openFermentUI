"""geneOS's shelf of published reaction networks (OF-BLD-014 §6.2).

Data alone: which models there are, where each file comes from, how a sugar
enters each and the product leaves, and the add-on route to the product where
a model lacks one. The geneOS worker (workers/geneos_worker.py) is the only
module that reads these into cobra; nothing here imports it.

    iMM904        S. cerevisiae S288C, genome scale, fetched from BiGG    native, EX_etoh_e        ethanol
    Yeast9        S. cerevisiae S288C, genome scale, fetched from GitHub  native, r_1761           ethanol

`pnpm geneos:fetch` brings the fetched files. (alpha 2.0 removed the PHA
program's entries, ADR-010: the PHB product, the phaCAB add-on and the
models that carried it; the add-on mechanism stays.) The conventions here (the
uptake rate, each product's formula, the substrates' molar masses) are
settings a ceiling is computed under, recorded in every result's basis as
`convention` inputs. Every other bound stays as the model file publishes it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import intake

# ── conventions (E.1) ──────────────────────────────────────────────────

# The substrate's uptake, mmol per gram dry weight per hour, opened for a
# ceiling. The ceiling in mol per mol does not depend on it while no other
# bound binds; it is a convention and the basis says so.
UPTAKE = 10.0
UPTAKE_UNIT = "mmol gDW-1 h-1"

# The product, as the flux the network is asked to maximise: a demand on its
# metabolite, which the worker adds where the file lacks one (a product kept
# in the cell), or the exchange it is secreted through (ethanol), named by
# its BiGG id; a model on another namespace maps it in `exchanges`. `label`
# is how a result's label names it.
PRODUCTS: dict[str, dict] = {
    "ethanol": {
        "name": "ethanol",
        "label": "ethanol",
        "exchange": "EX_etoh_e",
        # C2H6O at the IUPAC standard atomic weights (C 12.011, H 1.008,
        # O 15.999), the ones the sugars' molar masses below are taken at.
        "formula": "C2H6O",
        "molarMass": 46.069,
        "note": "ethanol C2H6O (46.069 g mol-1, at the standard atomic weights the sugars' molar masses use), used to turn mol per mol into g per g",
    },
}

# Each substrate: its exchange reaction in the BiGG namespace four of the
# models share (Yeast9 maps its own in `exchanges`), its molar mass (g mol-1)
# and its carbon atoms, which set equal total carbon for a mix.
SUBSTRATES: dict[str, dict] = {
    "glucose": {"name": "glucose", "exchange": "EX_glc__D_e", "molarMass": 180.156, "carbons": 6},
    "fructose": {"name": "fructose", "exchange": "EX_fru_e", "molarMass": 180.156, "carbons": 6},
    "xylose": {"name": "xylose", "exchange": "EX_xyl__D_e", "molarMass": 150.13, "carbons": 5},
}

# A frontier is sampled at this many growth rates, from zero to the most the
# model allows; a mix at this many proportions, from all of one sugar to all
# of the other.
FRONTIER_POINTS = 12
MIX_POINTS = 11

# ── the add-on route ───────────────────────────────────────────────────

# Routes the worker adds to a model that lacks one, checked for mass balance
# (workers/geneos_worker.py apply_addon). None is held now.
ADDONS: dict[str, dict] = {}

# ── the shelf ──────────────────────────────────────────────────────────

def model_dir() -> Path:
    """Read at call time, so a test's data directory holds its own models."""
    return intake.DATA_DIR / "models"


@dataclass(frozen=True)
class FetchedFile:
    """A file in a git repository, pinned to a commit."""

    repository: str
    commit: str
    path: str
    sha256: str
    licence: str
    # The release the commit is tagged as, when it is one.
    release: str = ""

    @property
    def local(self) -> Path:
        return model_dir() / Path(self.repository).name / self.path

    @property
    def revision(self) -> str:
        return self.commit

    @property
    def source(self) -> str:
        return f"{self.repository} at {f'{self.release} ({self.commit})' if self.release else self.commit}"

    @property
    def where(self) -> str:
        return f"{self.source}, {self.path}"


@dataclass(frozen=True)
class UrlFile:
    """A file a server publishes at a fixed address, with no commit to pin
    it: the hash is the pin, and `revision` records what the server said of
    the file (its ETag and Last-Modified) when the hash was taken."""

    url: str
    revision: str
    # Where it lands, under core/data/models/.
    path: str
    sha256: str
    licence: str

    @property
    def local(self) -> Path:
        return model_dir() / self.path

    @property
    def source(self) -> str:
        return f"{self.url} ({self.revision})"

    @property
    def where(self) -> str:
        return self.source


@dataclass(frozen=True)
class ShelfModel:
    id: str
    name: str
    # The strain id the model describes, when the catalogue has one.
    host: str | None
    scope: str  # "central carbon" or "genome scale"
    # Where the file comes from: a model bundled with cobra, or a fetched file.
    bundled: str | None = None
    fetched: FetchedFile | UrlFile | None = None
    addon: str | None = None
    # How the product is made: the add-on's name, or the model's own route.
    route: str = ""
    licence: str = ""
    # The sugar a view opens on: one the model can take up.
    feed: str = "glucose"
    notes: list[str] = field(default_factory=list)
    # The products this entry names a route to, the first the one a view
    # opens on. What the network can make is the worker's to say (describe).
    products: tuple[str, ...] = ()
    # A substrate's or a product's exchange where the file does not use the
    # BiGG id SUBSTRATES and PRODUCTS name, by key; and the name the file
    # gives each such reaction, which the worker checks when it loads the
    # file, so a reaction renumbered in another release is refused, not used.
    exchanges: dict[str, str] = field(default_factory=dict)
    exchange_names: dict[str, str] = field(default_factory=dict)

    @property
    def product(self) -> str:
        return self.products[0]


# Yeast9, the community consensus reconstruction of S. cerevisiae: release
# v9.1.1 of SysBioChalmers/yeast-GEM, whose LICENSE.md is CC-BY-4.0.
YEAST9 = FetchedFile(
    repository="https://github.com/SysBioChalmers/yeast-GEM",
    commit="2d594ae1c4a2d550ccef120d96a58c7bbf586255",
    release="v9.1.1",
    path="model/yeast-GEM.xml",
    sha256="30842b15eefb0ef7e36cbdea86a9efddfacf69a871c8b054165faa9af9f6c8eb",
    licence="CC-BY-4.0",
)

# iMM904 as BiGG Models serves it. BiGG's terms (bigg.ucsd.edu/license) grant
# educational, research and non-profit use without fee, require the notice to
# travel with every copy, and leave commercial use to an agreement with UC San
# Diego. The file stays on the machine that fetched it and is never committed,
# so no copy leaves it.
BIGG_IMM904 = UrlFile(
    url="https://bigg.ucsd.edu/static/models/iMM904.xml",
    revision='ETag "017c86841952cc365f20a8b466292b31", Last-Modified 2019-11-01',
    path="bigg/iMM904.xml",
    sha256="a4bcff4f8f2228a5b1553264c3bcb1e8a8093907754446007f3f3b529d29d3e1",
    licence="BiGG Models terms: educational, research and non-profit use; commercial use by agreement with UC San Diego",
)

SHELF: dict[str, ShelfModel] = {
    "iMM904": ShelfModel(
        id="iMM904", name="Saccharomyces cerevisiae S288C (iMM904)", host="s-cerevisiae-s288c",
        scope="genome scale", fetched=BIGG_IMM904, products=("ethanol",),
        route="native: pyruvate decarboxylase (PYRDC) and alcohol dehydrogenase (ALCD2ir); ethanol leaves through EX_etoh_e",
        licence=BIGG_IMM904.licence,
        notes=[
            "Mo, Palsson and Herrgård, BMC Systems Biology 2009 (PMID 19321003), as BiGG Models serves it.",
            "The file publishes oxygen uptake at 2 mmol gDW-1 h-1 (EX_o2_e) and ATP maintenance fixed at 1 mmol "
            "gDW-1 h-1 (ATPM); both stand as published, so its envelope is a cell's short of oxygen.",
        ],
    ),
    "Yeast9": ShelfModel(
        id="Yeast9", name="Saccharomyces cerevisiae S288C (Yeast9)", host="s-cerevisiae-s288c",
        scope="genome scale", fetched=YEAST9, products=("ethanol",),
        route="native: pyruvate decarboxylase (r_0959) and alcohol dehydrogenase (r_2115); ethanol leaves through r_1761, the file's ethanol exchange",
        licence=YEAST9.licence,
        exchanges={"glucose": "r_1714", "fructose": "r_1709", "xylose": "r_1718", "ethanol": "r_1761"},
        exchange_names={"glucose": "D-glucose exchange", "fructose": "D-fructose exchange",
                        "xylose": "D-xylose exchange", "ethanol": "ethanol exchange"},
        notes=[
            "Zhang et al., Yeast9: a consensus genome-scale metabolic model for S. cerevisiae curated by the "
            "community, Molecular Systems Biology 2024, doi:10.1038/s44320-024-00060-7.",
            "Its reactions are numbered, not named in BiGG's namespace: the shelf maps glucose to r_1714, fructose to "
            "r_1709, xylose to r_1718 and ethanol to r_1761, and the worker refuses the file when one of them no "
            "longer carries the name it is mapped by.",
            "The file publishes oxygen uptake open (r_1992) and non-growth maintenance fixed at 0.7 mmol gDW-1 h-1 "
            "(r_4046); both stand as published.",
        ],
    ),
}


def exchange_id(model_id: str, key: str) -> str:
    """The reaction a substrate enters, or an exchange-defined product leaves,
    model `model_id` through: the model's own id where the shelf maps one, the
    BiGG id otherwise (the toy, and the models in BiGG's namespace)."""
    entry = SHELF.get(model_id)
    if entry is not None and key in entry.exchanges:
        return entry.exchanges[key]
    if key in SUBSTRATES:
        return SUBSTRATES[key]["exchange"]
    return PRODUCTS[key]["exchange"]


# A file's hash, remembered against its size and modification time, so a
# file is hashed once and again only when it changes.
_HASHED: dict[str, tuple[int, int, str]] = {}


def file_sha256(path: Path) -> str:
    import hashlib

    st = path.stat()
    seen = _HASHED.get(str(path))
    if seen and seen[:2] == (st.st_size, st.st_mtime_ns):
        return seen[2]
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    _HASHED[str(path)] = (st.st_size, st.st_mtime_ns, h.hexdigest())
    return h.hexdigest()


def available(model: ShelfModel) -> str | None:
    """Why the model cannot be loaded here, or None when it can. A fetched
    file is checked against its pinned hash every time it is used (§6.R)."""
    if not model.fetched:
        return None
    if not model.fetched.local.is_file():
        return f"{model.id}'s file is not on this machine: run pnpm geneos:fetch"
    if file_sha256(model.fetched.local) != model.fetched.sha256:
        return f"{model.id}'s file does not match its pinned sha256: run pnpm geneos:fetch, which fetches it again"
    return None
