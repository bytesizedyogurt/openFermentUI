# H4-04: a fed-batch whose cells take up nothing is flagged as a mass balance that does not close

**Statement.** fermOS's mass balance divides its gap by the sugar consumed, so a fed-batch whose cells take up no sugar (its series meets the closed form V = V0 + F t, every concentration diluted, within 1.3e-6) reports closure 1 from 8.5e-5 g of integrator error (1.5 with a feed of water), carries the flag "The mass balance does not close: 1 against 1%." and says the rate laws or their parameters do not hold together.

**Contract.**
- `core/openferment_core/kinetics.py:88-94`: "9. The mass balance is checked after every integration on cumulative consumption states ... Both are invariants of the equations, which LSODA keeps to rounding: the check catches a wrong right-hand side (a dropped 1/Yps reads 30 % off), never integrator error, which the tests hold against a run at rtol 1e-12. Within BALANCE_TOL, or the result carries a flag."
- `core/openferment_core/fermos.py:2307`, the note every simulation carries: "The check catches a wrong rate law, not the integrator's error, which the tests hold."

**Command** (from the repository root): `bash bughunt/repro/H4-04/run.sh`

It starts the head's service on a fresh database `bh_r_h4_04_svc` at 127.0.0.1:9110, makes project `h404`, and posts three `fedbatch_v1` simulations to `POST /api/fermos/simulate` (`cases.py`): 1 L start, 0.05 L/h constant feed for 20 h, X0 2, S0 20, P0 3 g/L.
- `noUptakeSugar`: μmax 0, no maintenance, α 0, β 0, the feed at 100 g/L.
- `noUptakeWater`: the same with the feed at 0 g/L.
- `control`: μmax 0.2, α 0.3, X0 1, S0 10, the feed at 100 g/L.

Keyless, no model call. It stops the service and drops the database after.

**Expected.** The two no-uptake runs follow the equations exactly. Their series meet the closed form to the integrator's tolerance, the true sugar consumed is 0 g, and so `massBalance.ok` is true with no "does not close" flag. The control closes too.

**Observed** (both runs, identical):
- `noUptakeSugar`: the series meets the closed form within 1.20e-6 (V 6e-16, X 1.07e-6, S 1.20e-6, P 1.07e-6). The result is `massBalance {closure: 1, ok: false}` with the note "Sugar consumed, 8.45561e-05 g, ... within 1 of it, outside the 1% closure, so the rate laws or their parameters do not hold together" and the flag `The mass balance does not close: 1 against 1%.` The 8.5e-5 g is 7.0e-7 of the 120 g of sugar the vessel held and was fed, which is the integrator's rtol of 1e-6.
- `noUptakeWater`: the series meets the closed form within 1.33e-6. The result is closure 1.5, `ok: false`, sugar consumed −1.5429e-05 g (7.7e-7 of 20 g), and the same flag.
- `control`: closure 2.13e-7, `ok: true`.

**Likely cause** (confidence high). `core/openferment_core/kinetics.py:1346`: `scale = max(abs(consumed), ATOL)`. The closure is the gap divided by the sugar consumed (`kinetics.py:1347`), and `consumed` (`kinetics.py:1338`) is the difference of two sums near 120 g. Each sum is integrated to rtol 1e-6, so consumed carries about 1e-4 g of integrator error. When the true consumption is zero, `aux` and `cross` are zero to rounding and the ratio is |consumed| / |consumed| = 1 (or more). The scale needs to be the sugar the run handled, for example the start plus fed, so that integrator noise stays under BALANCE_TOL. `fermos.py:2300` then marks the run not ok, and `fermos.py:2312` adds the flag.

**Severity.** S3: an edge case (a fed-batch with no uptake, or one whose uptake is under about 1e-4 of the sugar inventory) with a workaround (the series itself is right). The closure number and the flag on such a run are wrong, and the note blames the rate laws.
