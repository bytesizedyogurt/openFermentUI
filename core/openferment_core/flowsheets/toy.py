"""The toy flowsheet (OF-BLD-014 §8.1): two units whose mass balance is worked
by hand. A STAND-IN for tests and fixtures, not a process.

    water (kg/h) ─┐
                  ├─ Mixer M ── Splitter S ── top    (split × each component)
    ethanol (kg/h)┘                       └── bottom (the rest)

With 100 kg/h water, 50 kg/h ethanol and a split of 0.6, the top carries
60 water and 30 ethanol, and the bottom 60 kg/h in all.
"""
from __future__ import annotations

from typing import Any

import biosteam as bst

NAME = "toy"
INPUTS = {
    "water": ("water fed", "kg h-1", 100.0),
    "ethanol": ("ethanol fed", "kg h-1", 50.0),
    "split": ("share to the top", "", 0.6),
}
OUTPUTS = {"topEthanol": "kg h-1", "topWater": "kg h-1", "bottomTotal": "kg h-1"}


def build() -> Any:
    bst.main_flowsheet.set_flowsheet("toy")
    bst.settings.set_thermo(["Water", "Ethanol"], cache=True)
    a = bst.Stream("toy_water", Water=INPUTS["water"][2], units="kg/hr")
    b = bst.Stream("toy_ethanol", Ethanol=INPUTS["ethanol"][2], units="kg/hr")
    m = bst.Mixer("toy_M", ins=(a, b))
    s = bst.Splitter("toy_S", ins=m - 0, split=INPUTS["split"][2])
    system = bst.System("toy_sys", path=(m, s))
    system.simulate()
    return system


def evaluate(system: Any, values: dict[str, float]) -> dict[str, float]:
    m, s = system.path
    a, b = m.ins
    v = {k: float(values.get(k, spec[2])) for k, spec in INPUTS.items()}
    if not 0 <= v["split"] <= 1:
        raise ValueError("the share to the top must lie between 0 and 1")
    a.set_flow(v["water"], "kg/hr", "Water")
    b.set_flow(v["ethanol"], "kg/hr", "Ethanol")
    s.split[:] = v["split"]
    system.simulate()
    top, bottom = s.outs
    return {"topEthanol": float(top.imass["Ethanol"]), "topWater": float(top.imass["Water"]), "bottomTotal": float(bottom.F_mass)}
