"""Parameter ontology v1 — what the corpus is allowed to measure.

Ported from `src/data/types.ts`. The docstrings came with the types and are not
decoration: they record why `undetermined` is a value rather than a gap, and why
`% TSP` and `g/L` are kept apart. Anyone tempted to tidy them should read them
first.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from ._base import OFModel

__all__ = [
    "AnalysisMethod",
    "FieldId",
    "NumberingConvention",
    "ParameterDef",
    "ParameterFamily",
    "RefuseConversion",
]


class ParameterFamily(StrEnum):
    EXPRESSION = "expression"
    PTM = "ptm"
    FUNCTIONAL = "functional"
    CULTIVATION = "cultivation"
    DOWNSTREAM = "downstream"


class FieldId(StrEnum):
    """Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families."""

    # Family 1 — expression performance
    EXPRESSION_PCT_TSP = "expression_pct_tsp"
    TITER_INTRACELLULAR = "titer_intracellular"
    TITER_SECRETED = "titer_secreted"
    SECRETED_FRACTION = "secreted_fraction"
    FOLD_IMPROVEMENT = "fold_improvement"
    TRANSFORMATION_EFFICIENCY = "transformation_efficiency"
    TIME_TO_COLONY = "time_to_colony"
    # Family 2 — post-translational modification
    PHOSPHATE_COUNT = "phosphate_count"
    PHOSPHORYLATION_DEGREE = "phosphorylation_degree"
    PHOSPHO_SITE_POSITION = "phospho_site_position"
    GLYCAN_SPECIES = "glycan_species"
    KINASE_IDENTITY = "kinase_identity"
    # Family 3 — functional performance
    MICELLE_DIAMETER = "micelle_diameter"
    MICELLAR_FRACTION = "micellar_fraction"
    GELATION_PH = "gelation_ph"
    CALCIUM_BINDING = "calcium_binding"
    MELT_STRETCH_LENGTH = "melt_stretch_length"
    # Family 4 — cultivation
    GROWTH_RATE_MU = "growth_rate_mu"
    FINAL_BIOMASS_DENSITY = "final_biomass_density"
    VOLUMETRIC_PRODUCTIVITY = "volumetric_productivity"
    MEDIUM_COMPONENT_CONC = "medium_component_conc"
    # Family 5 — downstream and economics
    DISRUPTION_PROTEIN_YIELD = "disruption_protein_yield"
    DISRUPTION_ENERGY = "disruption_energy"
    MINIMUM_SELLING_PRICE = "minimum_selling_price"


class AnalysisMethod(StrEnum):
    """Analytical method behind a PTM or functional measurement (OF-COR-001 §17
    Rule 1). 'undetermined' is a first-class value: Mora Vásquez et al. record
    it for most bacterial studies because the analysis was never done, and the
    platform must distinguish *absence of measurement* from *measurement of
    absence*.
    """

    LC_ESI_MS = "LC-ESI-MS"
    MALDI_MS = "MALDI-MS"
    PHOS_TAG = "Phos-tag"
    UREA_PAGE = "urea-PAGE"
    UREA_PAGE_PHOSPHATASE = "urea-PAGE + phosphatase"
    SDS_PAGE_MOBILITY = "SDS-PAGE mobility"
    ETHYL_STAINS_ALL = "Ethyl Stains-All"
    CD_SPECTROSCOPY = "CD spectroscopy"
    SAXS = "SAXS"
    SANS = "SANS"
    DLS = "DLS"
    CRYO_TEM = "cryo-TEM"
    HPLC = "HPLC"
    GRAVIMETRIC = "gravimetric"
    SPECTROPHOTOMETRIC = "spectrophotometric"
    PROCESS_MODEL = "process model"
    UNDETERMINED = "undetermined"


class NumberingConvention(StrEnum):
    """Residue-numbering convention (OF-COR-001 §19, first trap)."""

    PRECURSOR = "precursor"
    MATURE = "mature"


class RefuseConversion(OFModel):
    """One entry in `ParameterDef.refuseConversionTo`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. The `because` string is user-facing product copy and is reproduced
    verbatim wherever it appears — a refusal that cannot say why is just an
    error message.
    """

    field: FieldId
    because: str


class ParameterDef(OFModel):
    id: FieldId
    family: ParameterFamily
    name: str
    definition: str
    canonical_unit: str = Field(
        description="'' for categorical fields (kinase_identity, glycan_species)."
    )
    range: tuple[float, float]
    notes: str
    categorical: bool | None = Field(
        default=None, description="Categorical fields hold a string value, not a number."
    )
    requires_method: bool | None = Field(
        default=None,
        description="OF-COR-001 §17 Rule 1: a value without its method is not interpretable.",
    )
    refuse_conversion_to: list[RefuseConversion] | None = Field(
        default=None,
        description=(
            "Unit families this field must NOT be auto-converted into, with the reason. "
            "OF-COR-001 §17 Rule 2: %TSP and g/L are not interconvertible without cell "
            "density and total-protein fraction. The engine refuses and says why."
        ),
    )
