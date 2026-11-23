"""H3: the provenance each mix of inputs earns, worked out by hand from ADR-006 (C.5 note) and runs.md,
beside what basis.basis_provenance computes and what weakest_provenance gives a claim citing the run with
a gold record (validate_plan's rule). Prints one row per mix and flags any disagreement.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/provenance_table.py
"""
from openferment_core import basis
from openferment_core.models import BasisInput, BasisSource, ComputedBasis, weakest_provenance

REC = {"r-gold": {"provenance": "gold"}, "r-ver": {"provenance": "verified"}, "r-unv": {"provenance": "unverified"},
       "r-ind": {"provenance": "industry-estimate"}, "r-ass": {"provenance": "assumed"}}
ART = {"a-comp": {"provenance": "computed"}, "a-meas": {"provenance": "measured"}, "a-ass": {"provenance": "assumed"},
       "a-unv": {"provenance": "unverified"}}

S = {
    "default": BasisSource(kind="model", id="biorefineries"),
    "convention": BasisSource(kind="convention", note="precision"),
    "person": basis.assumption_source("Ada Lovelace", "2026-11-09"),
    "estimate": basis.estimate_source("claude-x", "2026-11-09"),
    "reading": basis.measurement_source("dep1/e1", "Ada Lovelace", "2026-11-09T10:00:00Z"),
    "series": BasisSource(kind="deposition", id="dep1", note="the readings of measure m1"),
    "gold": BasisSource(kind="record", id="r-gold"), "verified": BasisSource(kind="record", id="r-ver"),
    "unverified": BasisSource(kind="record", id="r-unv"), "industry": BasisSource(kind="record", id="r-ind"),
    "missing-record": BasisSource(kind="record", id="r-none"),
    "artifact-computed": BasisSource(kind="artifact", id="a-comp"), "artifact-measured": BasisSource(kind="artifact", id="a-meas"),
    "artifact-assumed": BasisSource(kind="artifact", id="a-ass"), "artifact-missing": BasisSource(kind="artifact", id="a-none"),
}

# (mix, expected by hand, why)
TABLE = [
    (["default"], "computed", "runs.md: a run at the package's own settings is computed"),
    (["default", "convention"], "computed", "model and convention change nothing"),
    (["default", "person"], "assumed", "any person's assumption"),
    (["default", "estimate"], "assumed", "any model's estimate"),
    (["default", "reading"], "measured", "a reading, nothing assumed"),
    (["default", "reading", "person"], "assumed", "assumed wins over measured"),
    (["default", "reading", "estimate"], "assumed", "assumed wins over measured"),
    (["default", "reading", "gold"], "measured", "C.5: measured when any input is a measurement"),
    (["default", "reading", "unverified"], "measured", "C.5 names this consequence (ranks above gold)"),
    (["default", "reading", "industry"], "measured", "C.5 names this consequence"),
    (["default", "reading", "artifact-computed"], "measured", "C.5: an artifact computed with no assumption"),
    (["default", "reading", "artifact-assumed"], "assumed", "rests on an assumed artifact"),
    (["default", "reading", "missing-record"], "assumed", "a source the caller cannot find never reads strong"),
    (["default", "reading", "artifact-missing"], "assumed", "a source the caller cannot find never reads strong"),
    (["default", "gold"], "computed", "weakest of computed and gold"),
    (["default", "unverified"], "unverified", "weakest of computed and unverified"),
    (["default", "industry"], "industry-estimate", "weakest"),
    (["default", "series"], "computed", "a deposition series reads as measured, weaker computed wins"),
    (["default", "series", "unverified"], "unverified", "weakest"),
    (["default", "artifact-measured"], "computed", "an artifact input's class, weakest with computed"),
    (["default", "missing-record"], "assumed", "unknown sorts weakest"),
]

bad = 0
for mix, want, why in TABLE:
    b = ComputedBasis(tool="t", toolVersion="v", artifactId="x", at="2026-11-09",
                      inputs=[BasisInput(name=f"{k}{n}", value=1.0, unit="", source=S[k]) for n, k in enumerate(mix)])
    got = basis.basis_provenance(b, REC, ART)
    claim = weakest_provenance([got, "gold"])
    flag = "" if got == want else "   <-- DIFFERS"
    bad += got != want
    print(f"{' + '.join(mix):48} hand {want:18} code {got:18} claim with gold {claim:18}{flag}  ({why})")
print("disagreements:", bad)
