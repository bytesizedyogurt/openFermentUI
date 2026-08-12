# bioSTEAM in openFerment

The modules in this directory are TypeScript ports of algorithms from
**BioSTEAM: The Biorefinery Simulation and Techno-Economic Analysis Modules**,
v2.53.11.

> Copyright (c) 2019–2023 BioSTEAM Development Group. All rights reserved.
> Developed by the BioSTEAM Development Group, University of Illinois at
> Urbana-Champaign. Distributed under the University of Illinois/NCSA Open
> Source License. The software is provided "as is", without warranty of any
> kind; see `LICENSE.txt` in the upstream repository for the full text.
>
> Neither the names of the BioSTEAM Development Group, the University of
> Illinois, nor the names of its contributors may be used to endorse or promote
> products derived from this software without specific prior written
> permission.

Cite the method, not this port:

> Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S. BioSTEAM: A Fast and
> Flexible Platform for the Design, Simulation, and Techno-Economic Analysis of
> Biorefineries under Uncertainty. *ACS Sustainable Chem. Eng.* **2020**, 8 (8),
> 3302–3310.

## What is ported

Costing and techno-economic analysis — the part of bioSTEAM that turns a sized
piece of equipment into a number a reviewer can argue with.

| Module | Upstream source |
| --- | --- |
| `cepci.ts` | `units/design_tools/cost_index.py` |
| `vessel.ts` | `units/design_tools/flash_vessel_design.py`, `pressure_vessel.py`, `specification_factors.py` |
| `tanks.ts` | `units/design_tools/tank_design.py` |
| `batch.ts` | `units/design_tools/batch.py` |
| `aeration.ts` | `units/design_tools/aeration.py` |
| `utilities.ts` | `_heat_utility.py`, `_power_utility.py` |
| `unit.ts` | `_unit.py`, `units/decorators/_cost.py` |
| `tea.ts` | `_tea.py` |
| `model.ts` | `evaluation/_model.py`, `evaluation/_parameter.py` |
| `solvers.ts` | `flexsolve` (Wegstein, IQ-interpolation) |

Ported functions keep upstream names, argument order, and units of measure, so
a reader who knows bioSTEAM can check them line by line. Where a doctest exists
upstream, its value is reproduced in `scripts/check-biosteam.mjs`.

## What is NOT ported

**ThermoSTEAM.** There is no chemical property package here, no vapour–liquid
equilibrium, no rigorous energy balance, and no recycle convergence over a
flowsheet graph. Streams are lumped component mass flows at a stated
temperature and pressure.

That is a real limitation and the app says so on the screen rather than in a
footnote. What runs here is bioSTEAM's **costing and TEA engine over lumped
process models written by hand** — not a bioSTEAM simulation. A separation
whose cost turns on a relative volatility cannot be sized by this code, and
nothing in openFerment claims otherwise.

## Why port at all, instead of calling it

openFerment is a session-only browser application: no server, no Python, no
persistence. A worker calling real bioSTEAM is the right architecture for a
deployment that has a backend. This port exists so the arithmetic in front of
the reader is the published arithmetic, with the same constants and the same
depreciation schedule, rather than an invented curve that happens to slope the
same way.
