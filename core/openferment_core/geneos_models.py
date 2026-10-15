"""geneOS's shelf of published reaction networks (OF-BLD-014 §6.2).

Data alone: which models there are, where each file comes from, how a sugar
enters each, and the add-on route to the product where a model lacks one. The
geneOS worker (workers/geneos_worker.py) is the only module that reads these
into cobra; nothing here imports it.

    e_coli_core   E. coli K-12 central metabolism, bundled with cobra as `textbook`, + phaCAB
    iJO1366       E. coli K-12 MG1655, genome scale, bundled with cobra,                + phaCAB
    RehMBEL1391   C. necator H16, genome scale, fetched by `pnpm geneos:fetch`        native PHAS, phb_c

The conventions here (the uptake rate, the repeat unit's formula, the
substrates' molar masses) are settings a ceiling is computed under, recorded
in every result's basis as `convention` inputs. Every other bound stays as the
model file publishes it.
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

# The product, as the demand the network is asked to maximise.
PRODUCTS: dict[str, dict] = {
    "phb": {
        "name": "poly(3-hydroxybutyrate)",
        "metabolite": "phb_c",
        # The repeat unit, C4H6O2: the convention that turns mol per mol into
        # g per g. RehMBEL1391's phb_c carries no formula, so it is used for
        # every model alike.
        "formula": "C4H6O2",
        "molarMass": 86.09,
        "note": "the PHB repeat unit C4H6O2 (86.09 g mol-1), used to turn mol per mol into g per g",
    },
}

# Each substrate: its exchange reaction in the BiGG namespace the three models
# share, its molar mass (g mol-1) and its carbon atoms, which set equal total
# carbon for a mix.
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

# phaCAB: acetoacetyl-CoA reductase (PHAB) and PHA synthase (PHAC), the route
# the C. necator reconstruction carries natively (cited as model RehMBEL1391);
# the core model also lacks the thiolase, ACACT1r, and gains it here. The
# worker checks each added reaction with check_mass_balance() and refuses an
# add-on that does not balance.
PHACAB = {
    "id": "phaCAB",
    "source": "model: RehMBEL1391",
    "metabolites": [
        {"id": "aacoa_c", "formula": "C25H36N7O18P3S", "charge": -4, "name": "Acetoacetyl-CoA"},
        {"id": "3hbcoa__R_c", "formula": "C25H38N7O18P3S", "charge": -4, "name": "(R)-3-Hydroxybutanoyl-CoA"},
        {"id": "phb_c", "formula": "C4H6O2", "charge": 0, "name": "PHB repeat unit"},
    ],
    "reactions": [
        # Added only where the model lacks it (the core model does).
        {"id": "ACACT1r", "equation": "2 accoa_c <=> aacoa_c + coa_c", "lowerBound": -1000.0, "ifMissing": True},
        {"id": "PHAB", "equation": "aacoa_c + nadph_c + h_c --> 3hbcoa__R_c + nadp_c", "lowerBound": 0.0},
        {"id": "PHAC", "equation": "3hbcoa__R_c --> phb_c + coa_c", "lowerBound": 0.0},
    ],
}

ADDONS = {"phaCAB": PHACAB}

# ── the shelf ──────────────────────────────────────────────────────────

def model_dir() -> Path:
    """Read at call time, so a test's data directory holds its own models."""
    return intake.DATA_DIR / "models"


@dataclass(frozen=True)
class FetchedFile:
    repository: str
    commit: str
    path: str
    sha256: str
    licence: str

    @property
    def local(self) -> Path:
        return model_dir() / Path(self.repository).name / self.path


@dataclass(frozen=True)
class ShelfModel:
    id: str
    name: str
    # The strain id the model describes, when the catalogue has one.
    host: str | None
    scope: str  # "central carbon" or "genome scale"
    # Where the file comes from: a model bundled with cobra, or a fetched file.
    bundled: str | None = None
    fetched: FetchedFile | None = None
    addon: str | None = None
    # How the product is made: the add-on's name, or the model's own route.
    route: str = ""
    licence: str = ""
    notes: list[str] = field(default_factory=list)


C_NECATOR = FetchedFile(
    repository="https://github.com/m-jahn/genome-scale-models",
    commit="00c70c5",
    path="Ralstonia_eutropha/sbml/RehMBEL1391_sbml_L3V1.xml",
    sha256="85f761aa177a38d18b49dd32656875631f036f362f84571c4ee390d026b02d89",
    licence="GPL-3.0",
)

SHELF: dict[str, ShelfModel] = {
    "e_coli_core": ShelfModel(
        id="e_coli_core", name="E. coli K-12 central metabolism (core model)", host=None,
        scope="central carbon", bundled="textbook", addon="phaCAB",
        route="add-on phaCAB (PHAB, PHAC and the thiolase ACACT1r), the route RehMBEL1391 carries",
        licence="BiGG Models, bundled with cobra 0.32.1",
    ),
    "iJO1366": ShelfModel(
        id="iJO1366", name="E. coli K-12 MG1655 (iJO1366)", host=None,
        scope="genome scale", bundled="iJO1366", addon="phaCAB",
        route="add-on phaCAB (PHAB, PHAC), the route RehMBEL1391 carries",
        licence="BiGG Models, bundled with cobra 0.32.1",
    ),
    "RehMBEL1391": ShelfModel(
        id="RehMBEL1391", name="Cupriavidus necator H16 (RehMBEL1391)", host="c-necator-h16",
        scope="genome scale", fetched=C_NECATOR,
        route="native: PHA synthase PHAS and phb_c, with its own demand DM_phb_c",
        licence="GPL-3.0",
        notes=["Its phb_c carries no formula; g per g uses the repeat unit's formula, as for the other models."],
    ),
}


def available(model: ShelfModel) -> str | None:
    """Why the model cannot be loaded here, or None when it can."""
    if model.fetched and not model.fetched.local.is_file():
        return f"{model.id}'s file is not on this machine: run pnpm geneos:fetch"
    return None
