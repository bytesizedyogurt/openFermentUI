<!-- Written by `pnpm library:report` (core/openferment_core/engine/library.py); regenerate, do not edit. -->

# Library plants against their package's own test

Every plant and configuration `biorefineries/tests/test_biorefineries.py` covers, built afresh in the Proforma worker with the
package's own settings (biorefineries 2.35.1, biosteam 2.54.0, thermosteam 0.54.2) and held to the test as the test
holds it (`numpy.allclose` at its `rtol`). A value outside is listed with what this installation
measured.

| Plant | Configuration | Test | Within | Outside: measured against the test's value (relative difference) |
|---|---|---|---|---|
| corn |  | `test_corn` | 11 of 11 |  |
| cornstover |  | `test_cornstover` | 9 of 11 | `tea.installed_equipment_cost` 1.926e+08 against 2.091e+08 (7.9%); `units.get_electricity_consumption()` 20.91 against 22.06 (5.2%) |
| lactic |  | `test_lactic` | not run | Refused: biorefineries.lactic could not be built under biosteam 2.54.0: IndexError: list assignment index out of range |
| lipidcane |  | `test_lipidcane` | 11 of 11 |  |
| oilcane | S1 | `test_oilcane_S1` | 11 of 11 |  |
| oilcane | S2 | `test_oilcane_S2` | 11 of 11 |  |
| oilcane | O1 | `test_oilcane_O1` | 11 of 11 |  |
| oilcane | O2 | `test_oilcane_O2` | 9 of 11 | `tea.utility_cost` -7.263e+06 against -5.954e+06 (22.0%); `units.get_electricity_production()` 58.42 against 53.75 (8.7%) |
| oilcane | O3 | `test_oilcane_O3` | 11 of 11 |  |
| oilcane | O4 | `test_oilcane_O4` | 9 of 11 | `tea.utility_cost` -6.347e+06 against -5.404e+06 (17.5%); `units.get_electricity_production()` 54.8 against 51.44 (6.5%) |
| oilcane | S1* | `test_oilcane_S1_agile` | 11 of 11 |  |
| oilcane | S2* | `test_oilcane_S2_agile` | 11 of 11 |  |
| oilcane | O1* | `test_oilcane_O1_agile` | 11 of 11 |  |
| oilcane | O2* | `test_oilcane_O2_agile` | 9 of 11 | `tea.utility_cost` -8.255e+06 against -6.961e+06 (18.6%); `units.get_electricity_production()` 59.05 against 55.12 (7.1%) |
| oilcane | O6 | `test_oilcane_O6` | 11 of 11 |  |
| oilcane | O8 | `test_oilcane_O8` | 11 of 11 |  |
| oilcane | O9 | `test_oilcane_O9` | 10 of 10 |  |
| sugarcane |  | `test_sugarcane` | 11 of 11 |  |
