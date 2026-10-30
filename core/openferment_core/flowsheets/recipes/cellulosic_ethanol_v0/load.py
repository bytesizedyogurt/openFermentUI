"""Cellulosic ethanol, version 0: openFerment's flowsheet, composed from the
`biorefineries.cellulosic` factories (ADR-003, ADR-004; execution prompt §8.4).

This file is the flowsheet's recipe in the SFF toolkit's model-directory
shape (beside `environment.yaml` and `extended_metadata.yaml`): the toolkit's
harness (`pisces_sff.export_model`) runs `load()` in the pinned environment
where conda exists, and openFerment's flowsheet module
(`flowsheets/cellulosic_ethanol_v0.py`) builds every case through
`create_system`. It imports nothing of openFerment, so the harness needs
BioSTEAM and biorefineries alone.

THE COMPOSITION IS THE PACKAGE'S. `create_system` runs the body of the
package's own `create_cellulosic_ethanol_system` (the function its
`SystemFactory` wraps) inside a `bst.System`, with the pretreatment factory
and the fermentation kind chosen: the package's body calls
`create_dilute_acid_pretreatment_system` and `create_cellulosic_fermentation_system`,
and while it runs here those two names stand for the chosen factory (given
the inlets it declares) and for the fermentation factory with the chosen
kind. Every number the plant holds is the package's: its streams' defaults,
the settings its body writes, its factories' defaults, its TEA
(`create_cellulosic_ethanol_tea`, over the units its own `Biorefinery` counts
outside the battery limits) and the tolerance its `Biorefinery` sets on a
subsystem's recycle (the wastewater loop), both read from that class's code
by `ast`. The
package's own system declares the acid and ammonia inlets of dilute-acid
pretreatment, and checks that each is used; another pretreatment leaves
them unused, so the system is made here from the units the body builds,
without that check.

    pretreatment   dilute acid (the package's), hot water, AFEX, alkaline
    fermentation   IB (integrated bioprocess, the package's default) or SCF
                   (saccharification, then co-fermentation in batch); the
                   package's SSCF raises "not yet implemented"

With dilute acid and IB the plant is the package's own cellulosic plant
(`biorefineries.cellulosic.Biorefinery`), unit for unit.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from contextlib import contextmanager

#%% Model declarations (read by the SFF toolkit's runner)

SIMULATOR = "biosteam"
SIMULATOR_PACKAGE = "biosteam"
FLOWSHEET_MODEL_PACKAGE = "biorefineries"
MODEL_NAME = "cellulosic_ethanol_v0"
EXPORT_KWARGS = {"stoichiometry": "dict"}

# The pretreatment factories of biorefineries.cellulosic.systems, by the name a
# person chooses; the fermentation kinds its `create_cellulosic_fermentation_system`
# builds. The package's own composition is the first of each.
PRETREATMENTS = {
    "dilute acid": "create_dilute_acid_pretreatment_system",
    "hot water": "create_hot_water_pretreatment_system",
    "AFEX": "create_ammonia_fiber_expansion_pretreatment_system",
    "alkaline": "create_alkaline_pretreatment_system",
}
FERMENTATIONS = ("IB", "SCF")
PACKAGE_DEFAULT = ("dilute acid", "IB")


def osbl_unit_ids() -> tuple[str, ...]:
    """The units the package's own `Biorefinery.create_model` counts outside
    the battery limits, read from its code (`OSBL_units = (self.X, …)`)."""
    tree = _model_code()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "OSBL_units" for t in node.targets):
            if isinstance(node.value, ast.Tuple):
                return tuple(e.attr for e in node.value.elts if isinstance(e, ast.Attribute))
    raise LookupError("biorefineries.cellulosic.Biorefinery.create_model names no OSBL_units")


def _model_code():
    from biorefineries import cellulosic

    return ast.parse(textwrap.dedent(inspect.getsource(cellulosic.Biorefinery.create_model)))


def recycle_tolerances() -> list[tuple[str, dict]]:
    """The tolerances the package's own `Biorefinery.create_model` sets on a
    subsystem's recycle (`X = system.find_system(self.ID)`, then
    `X.set_tolerance(...)` with literal arguments), read from its code: the
    unit whose subsystem it is, and the arguments."""
    tree = _model_code()
    systems = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                and getattr(node.value.func, "attr", "") == "find_system" and node.value.args \
                and isinstance(node.value.args[0], ast.Attribute) and isinstance(node.targets[0], ast.Name):
            systems[node.targets[0].id] = node.value.args[0].attr
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "set_tolerance" \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in systems:
            out.append((systems[node.func.value.id], {k.arg: ast.literal_eval(k.value) for k in node.keywords}))
    return out


@contextmanager
def _chosen(pretreatment: str, fermentation: str):
    """While the package's composition body runs, its two factory names stand
    for the chosen pretreatment (given the inlets it declares) and for the
    fermentation factory with the chosen kind; the package's own are put back
    after."""
    from biorefineries.cellulosic import systems
    from biorefineries.cellulosic.systems import cellulosic_ethanol as package

    if pretreatment not in PRETREATMENTS:
        raise ValueError(f"there is no pretreatment {pretreatment!r}; there are {', '.join(PRETREATMENTS)}")
    if fermentation not in FERMENTATIONS:
        raise ValueError(f"there is no fermentation kind {fermentation!r} here; there are {', '.join(FERMENTATIONS)}")
    factory = getattr(systems, PRETREATMENTS[pretreatment])
    takes = len(factory.ins)

    def pretreat(ins, **kwargs):
        return factory(ins=list(ins)[:takes], **kwargs)

    def ferment(**kwargs):
        return systems.create_cellulosic_fermentation_system(kind=fermentation, **kwargs)

    held = package.create_dilute_acid_pretreatment_system, package.create_cellulosic_fermentation_system
    package.create_dilute_acid_pretreatment_system, package.create_cellulosic_fermentation_system = pretreat, ferment
    try:
        yield package
    finally:
        package.create_dilute_acid_pretreatment_system, package.create_cellulosic_fermentation_system = held


def create_system(pretreatment: str = PACKAGE_DEFAULT[0], fermentation: str = PACKAGE_DEFAULT[1]):
    """The plant, unsimulated, and its TEA: the package's chemicals and
    process settings, a flowsheet of its own, and the package's composition
    with the chosen pretreatment and fermentation kind."""
    import biosteam as bst
    from biorefineries import cellulosic
    from biorefineries.cellulosic import streams
    from biorefineries.tea import create_cellulosic_ethanol_tea

    bst.settings.set_thermo(cellulosic.create_cellulosic_ethanol_chemicals())
    cellulosic.load_process_settings()
    flowsheet = bst.Flowsheet(f"{MODEL_NAME}_{pretreatment}_{fermentation}".replace(" ", "_"))
    bst.main_flowsheet.set_flowsheet(flowsheet)
    ins = [bst.Stream(**streams.cornstover), bst.Stream(**streams.sulfuric_acid), bst.Stream(**streams.ammonia),
           bst.Stream(**streams.denaturant)]
    outs = [bst.Stream(**streams.ethanol)]
    # BioSTEAM's registry renames a second stream of one name (`RO_treated_water`
    # becomes `_1` and `_2`) when the package builds its plant; the body is run
    # with that renaming on, as the package's plant has it, and it is put back.
    import thermosteam as tmo

    renaming = tmo.utils.Registry.AUTORENAME
    tmo.utils.Registry.AUTORENAME = True
    try:
        with _chosen(pretreatment, fermentation) as package, bst.System(f"{MODEL_NAME}_sys") as system:
            package.create_cellulosic_ethanol_system.f(ins, outs)
    finally:
        tmo.utils.Registry.AUTORENAME = renaming
    units = flowsheet.unit
    osbl = [getattr(units, i) for i in osbl_unit_ids() if hasattr(units, i)]
    tea = create_cellulosic_ethanol_tea(system, OSBL_units=osbl)
    for unit_id, arguments in recycle_tolerances():
        if hasattr(units, unit_id):
            system.find_system(getattr(units, unit_id)).set_tolerance(**arguments)
    return system, tea


#%% Loader (the SFF toolkit's entry point)


def load():
    """The package's own composition (dilute acid, IB), simulated, with the
    ethanol priced at the TEA's IRR as the package's `Biorefinery` prices it.

    Returns
    -------
    (biosteam.System, biosteam.TEA)
    """
    system, tea = create_system(*PACKAGE_DEFAULT)
    system.simulate()
    ethanol = next(s for s in system.products if s.ID == "ethanol")
    ethanol.price = tea.solve_price(ethanol)
    return system, tea


if __name__ == "__main__":
    system, tea = load()
    print(system)
    print(f"IRR: {tea.IRR}")
