/**
 * Does the port still agree with the Python?
 *
 * Every case below is a value bioSTEAM itself asserts — a docstring example in
 * the module this code was ported from, or a constant read straight out of the
 * source. They are checked on every `pnpm verify` because a port is only worth
 * having while it stays faithful, and a transposed digit in a cost correlation
 * is exactly the kind of defect that produces a plausible number.
 *
 * Where a case has no upstream doctest the expectation is derived by hand from
 * the Python and the derivation is written into the case name, so a reader can
 * disagree with the check rather than only with the code.
 */
import { CE, CEPCI_BY_YEAR } from '../src/engine/biosteam/cepci';
import { computeVesselWeightAndWallThickness } from '../src/engine/biosteam/vessel';
import { fieldErectedTankPurchaseCost } from '../src/engine/biosteam/tanks';
import { sizeBatch } from '../src/engine/biosteam/batch';
import { wegstein, solveBrentq } from '../src/engine/biosteam/solvers';
import { ELECTRICITY_PRICE, costHeatUtility, getAgent } from '../src/engine/biosteam/utilities';
import { DEPRECIATION_SCHEDULES } from '../src/engine/biosteam/tea';
import { spearmanRho } from '../src/engine/biosteam/stats';
import { C_O2_L, PAtKLaRiet, kLaStirredRiet, henrysLawConstant } from '../src/engine/biosteam/aeration';
import { FLOWSHEETS } from '../src/sim/flowsheets/plants';
import { evaluatePlant } from '../src/engine/plant';

const failures: string[] = [];
let checked = 0;

function eq(name: string, got: number, want: number, tol = 0): void {
  checked += 1;
  const ok = tol === 0 ? got === want : Math.abs(got - want) <= tol * Math.max(1, Math.abs(want));
  if (!ok) failures.push(`${name}: got ${got}, expected ${want}${tol ? ` (rel tol ${tol})` : ''}`);
}

function ok(name: string, condition: boolean, detail = ''): void {
  checked += 1;
  if (!condition) failures.push(`${name}${detail ? `: ${detail}` : ''}`);
}

// ── cost index ─────────────────────────────────────────────────────────
eq('CEPCI 2021 (cost_index.py)', CEPCI_BY_YEAR[2021], 708);
eq('CEPCI 1980 (cost_index.py)', CEPCI_BY_YEAR[1980], 261);
eq('default CE (biosteam/__init__.py)', CE.value, 567.5);

// ── vessel design (flash_vessel_design.py doctest) ─────────────────────
{
  const { weight, thickness } = computeVesselWeightAndWallThickness(14.7, 3, 10, 490);
  eq('compute_vessel_weight_and_wall_thickness weight', weight, 1116.83);
  eq('compute_vessel_weight_and_wall_thickness thickness', thickness, 0.25);
}

// ── tank cost (tank_design.py doctest) ─────────────────────────────────
eq('field_erected_tank_purchase_cost(300)', fieldErectedTankPurchaseCost(300), 112610);

// ── size_batch (batch.py) ──────────────────────────────────────────────
//
// The expectations below come from bioSTEAM's CODE, not from its docstring,
// because the two disagree and the code wins.
//
// `size_batch`'s docstring shows the V_max-with-Wegstein case returning
// {'Reactor volume': 992.6900584795799, 'Batch time': 33.95000000000163,
//  'Loading time': 0.950000000001627, 'Number of reactors': 36}. Transcribing
// the upstream function body into Python and running it returns 992.4812030075188,
// 33.94285714285714 and 0.9428571428571428 instead — only the reactor count
// matches. The reason is visible in the source: the `N_reactors is None` branch
// computes V_T and V_i from the Wegstein loading time, and then falls through to
// three more lines that recompute V_T, V_i and tau_loading from N_reactors
// alone. The docstring records the values from before that fall-through existed.
// The first two examples print 992.48, which is the same number to the precision
// shown.
//
// Recorded rather than quietly reconciled: a stale docstring in the reference
// implementation is exactly the kind of thing this app exists to make visible,
// and a port that silently matched the prose instead of the code would be wrong
// in the direction that is hardest to notice.
{
  const a = sizeBatch(1e3, 30, 3, 0.95, { V_max: 1e3, loading_time: 0 });
  eq('size_batch V_max, loading 0 — volume', a.reactorVolume, 992.4812030075188, 1e-12);
  eq('size_batch V_max, loading 0 — batch time', a.batchTime, 33);
  eq('size_batch V_max, loading 0 — reactors', a.nReactors, 35);

  const b = sizeBatch(1e3, 30, 3, 0.95, { N_reactors: 35, loading_time: 0 });
  eq('size_batch N=35, loading 0 — volume', b.reactorVolume, 992.4812030075188, 1e-12);

  const c = sizeBatch(1e3, 30, 3, 0.95, { V_max: 1000 });
  eq('size_batch V_max, Wegstein — volume', c.reactorVolume, 992.4812030075188, 1e-9);
  eq('size_batch V_max, Wegstein — batch time', c.batchTime, 33.94285714285714, 1e-9);
  eq('size_batch V_max, Wegstein — loading time', c.loadingTime, 0.9428571428571428, 1e-9);
  eq('size_batch V_max, Wegstein — reactors', c.nReactors, 36);

  const d = sizeBatch(1e3, 30, 3, 0.95, { N_reactors: 36 });
  eq('size_batch N=36, Wegstein — volume', d.reactorVolume, 992.4812030075188, 1e-9);
  eq('size_batch N=36, Wegstein — loading time', d.loadingTime, 0.9428571428571428, 1e-9);
}

// ── solvers ────────────────────────────────────────────────────────────
eq('wegstein on cos', wegstein((x) => Math.cos(x), 0.5), 0.7390851332151607, 1e-7);
eq('brentq on x²−2', solveBrentq((x) => x * x - 2, 0, 2), Math.SQRT2, 1e-9);

// ── utilities (_heat_utility.py, _power_utility.py) ────────────────────
eq('PowerUtility default price', ELECTRICITY_PRICE, 0.0782);
eq('low_pressure_steam T', getAgent('low_pressure_steam').T, 412.189);
eq('low_pressure_steam regeneration price', getAgent('low_pressure_steam').regenerationPrice, 0.2378);
eq('cooling_water T', getAgent('cooling_water').T, 305.372);
eq('cooling_water regeneration price', getAgent('cooling_water').regenerationPrice, 4.8785e-4);
eq('chilled_water heat transfer price', getAgent('chilled_water').heatTransferPrice, 5e-6);

// A cooling agent only achieves its full temperature rise against a hot enough
// process. The ratio below was measured against a live bioSTEAM 2.53.11 run:
// the same 1000 kJ/hr costs 0.000333 USD/hr cooling from 340 K and 0.000673
// cooling from 320 K, because the return temperature is min(T_limit, T_in - 5)
// and cooling water is billed per mole.
{
  const hot = costHeatUtility('cooling_water', -1000, 340);
  const tepid = costHeatUtility('cooling_water', -1000, 320);
  eq('cooling water at a hot process reaches its full rise', hot, 3.3316882671025717e-4, 1e-9);
  eq('cooling water costs 2.02x as much against a 320 K process', tepid / hot, 2.019, 1e-3);
  let threw = false;
  try {
    costHeatUtility('cooling_water', -1000, 298);
  } catch {
    threw = true;
  }
  ok('a cooling tower refuses to chill a 25 °C culture', threw);
  ok('a NaN duty prices as NaN rather than free', Number.isNaN(costHeatUtility('cooling_water', NaN, 340)));
  eq('a zero duty is free', costHeatUtility('cooling_water', 0, 340), 0);
}

// ── aeration (aeration.py) ─────────────────────────────────────────────
//
// Upstream ships no doctest for these, so the cases are identities rather than
// remembered values: inverting the kLa correlation must return the power that
// produced it, and the Henry constant at the reference temperature must be the
// reference constant. Both would catch a transposed exponent, which is the
// failure mode that matters here — power goes as kLa^(1/b), so an error in b
// is magnified rather than damped.
eq('P_at_kLa_Riet inverts kLa_stirred_Riet', PAtKLaRiet(kLaStirredRiet(5000, 10, 0.03), 10, 0.03), 5000, 1e-9);
eq('Henry constant at the reference temperature', henrysLawConstant(298.15, 0.0013, 1500), 0.0013, 1e-12);
// Air-water at 25 °C and one atmosphere: 8.85 mg/L, the textbook value.
eq('dissolved oxygen at saturation, 25 °C, 1 atm air', C_O2_L(298.15, 0.21 * 101325) * 32e3, 8.85, 5e-3);

// ── depreciation (_tea.py) ─────────────────────────────────────────────
{
  const macrs7 = DEPRECIATION_SCHEDULES.MACRS7;
  ok('MACRS7 has 8 entries', macrs7.length === 8, `got ${macrs7.length}`);
  eq('MACRS7 year 1', macrs7[0], 0.1429);
  eq('MACRS7 year 8', macrs7[7], 0.0446);
  for (const [name, sched] of Object.entries(DEPRECIATION_SCHEDULES) as [string, number[]][]) {
    const total = sched.reduce((t: number, x: number) => t + x, 0);
    ok(`${name} sums to 1`, Math.abs(total - 1) < 5e-4, `sums to ${total}`);
  }
}

// ── rank statistics ────────────────────────────────────────────────────
eq('spearman on a monotone series', spearmanRho([1, 2, 3, 4, 5], [2, 4, 8, 16, 32]), 1, 1e-12);
eq('spearman on a reversed series', spearmanRho([1, 2, 3, 4, 5], [32, 16, 8, 4, 2]), -1, 1e-12);

// ── the plants actually solve ──────────────────────────────────────────
//
// An MSP that does not drive NPV to zero is a solver failure wearing a
// plausible number, which is the single most dangerous thing this app could
// render. Checked at the reference point of every flowsheet.
for (const spec of FLOWSHEETS) {
  const point: Record<string, number> = {};
  for (const p of spec.parameters) point[p.key] = p.baseline;
  let r;
  try {
    r = evaluatePlant(spec, point);
  } catch (e) {
    failures.push(`${spec.modelId}: flowsheet failed to build at its baseline — ${String(e)}`);
    continue;
  }
  ok(`${spec.modelId} MSP is finite and positive`, Number.isFinite(r.msp) && r.msp > 0, `msp=${r.msp}`);
  ok(
    `${spec.modelId} NPV is zero at the solved price`,
    Math.abs(r.npvResidual) < Math.max(1000, r.capital.TCI * 1e-6),
    `residual ${r.npvResidual.toExponential(2)} USD against TCI ${r.capital.TCI.toExponential(2)}`,
  );
  const lineSum = Object.values(r.costLines).reduce((t, v) => t + v, 0);
  ok(
    `${spec.modelId} cost lines sum to MSP`,
    Math.abs(lineSum - r.msp) < 1e-6 * Math.max(1, r.msp),
    `lines ${lineSum} vs msp ${r.msp}`,
  );
  ok(`${spec.modelId} has equipment`, r.units.length > 0, `${r.units.length} units`);
  ok(
    `${spec.modelId} capital ladder is monotone`,
    r.capital.purchaseCost <= r.capital.installedEquipmentCost &&
      r.capital.installedEquipmentCost <= r.capital.DPI &&
      r.capital.DPI <= r.capital.TDC &&
      r.capital.TDC <= r.capital.FCI &&
      r.capital.FCI <= r.capital.TCI,
    `${r.capital.purchaseCost} → ${r.capital.installedEquipmentCost} → ${r.capital.DPI} → ${r.capital.TDC} → ${r.capital.FCI} → ${r.capital.TCI}`,
  );

  // Every parameter must declare where it comes from, and a record binding must
  // name a record that exists. This is the same circuit the scenario
  // assumptions run through, applied to the numbers that now size equipment.
  for (const p of spec.parameters) {
    ok(
      `${spec.modelId}.${p.key} declares a basis`,
      p.basis.kind === 'record' || p.basis.kind === 'model' || p.basis.kind === 'unsourced',
    );
    if (p.basis.kind === 'unsourced') {
      failures.push(
        `${spec.modelId}.${p.key} is unsourced — a flowsheet parameter with no record and no justification sizes equipment on nothing`,
      );
    }
    ok(
      `${spec.modelId}.${p.key} baseline is inside its bounds`,
      p.baseline >= p.bounds[0] && p.baseline <= p.bounds[1],
      `${p.baseline} outside [${p.bounds[0]}, ${p.bounds[1]}]`,
    );
  }

  const split = r.costSourceSplit;
  const total = split.biosteam + split.authored;
  // Purity is checked, not just reported. bioSTEAM prices a stream, so a plant
  // whose powder is mostly unconverted substrate or spent cells would quote a
  // cheerful price for something nobody would buy — which is exactly what the
  // first connected mass balance revealed.
  ok(
    `${spec.modelId} sells a powder that is mostly product`,
    r.product.purity > 0.5,
    `purity ${(r.product.purity * 100).toFixed(0)}%`,
  );
  console.log(
    `  ${spec.modelId}  MSP $${r.msp.toFixed(2)}/kg · TCI $${(r.capital.TCI / 1e6).toFixed(1)}M · ` +
      `${r.units.length} units · purity ${(r.product.purity * 100).toFixed(0)}% · ` +
      `${((split.authored / total) * 100).toFixed(0)}% authored capital · ` +
      `${r.warnings.length} design warnings`,
  );
}

console.log(`\nbioSTEAM port: ${checked} checks`);
if (failures.length) {
  console.error(`\n✗ ${failures.length} disagreement(s) with the Python source:`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log('✓ The port agrees with bioSTEAM everywhere it is checked.\n');
