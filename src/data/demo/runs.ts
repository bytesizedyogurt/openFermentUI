// openFerment demo suite — run time series.
//
// Generated, not hand-written, and deterministic. A seeded PRNG means every
// reviewer sees the same excursion at the same Tick, and a reviewer who
// changes the seed sees a different plausible run rather than a broken one.
// Never `Math.random()` and never `new Date()`.
//
// One Tick is one minute. RUN-042 through RUN-046 are the comparison basis;
// RUN-047 carries the excursion that Archetype 6 adjudicates and Archetype 1
// then excludes.
import type { RunRecord, Channel, Excursion } from './types';
import { HEAT_PER_MOL_O2_KJ, O2_SOLUBILITY } from './core';

// Order statistics, from the one module that has them. `lib/stats` imports
// nothing, so a seed module can use it without a cycle.
import { medianSeries } from '@/lib/stats';
// ── Deterministic PRNG ─────────────────────────────────────────────────

export function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t = (t + 0x6d2b79f5) >>> 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

// ── Process shape ──────────────────────────────────────────────────────

export const RUN_CONFIG = {
  ticksPerHour: 60,
  durationTicks: 2880,          // 48 h
  batchEndTick: 660,            // 11 h — feed starts
  workingVolumeL: 5,
  temperatureC: 30,
  phSetpoint: 7.0,
  doSetpoint: 30,
  /** Batch-phase unrestricted growth, then the imposed feed setpoint. */
  muBatch: 0.34,
  muFeed: 0.15,
  x0: 0.9,                      // g L⁻¹ inoculum
  /** Specific oxygen uptake, mmol gDCW⁻¹ h⁻¹, by phase. */
  qO2Batch: 5.4,
  qO2Feed: 2.9,
  /** Vessel oxygen transfer ceiling at full agitation and air, mmol L⁻¹ h⁻¹. */
  otrMax: 96,
  rqAerobic: 0.96,
};

/** RUN-047 only. Eleven minutes from Tick 340, and it does not fully recover. */
export const EXCURSION_SPEC = {
  startTick: 340,
  endTick: 351,
  doFloor: 8,
  /**
   * RQ never returns to baseline. Small, permanent, and it is what the
   * operator saw as a shifted off-gas CO₂ reading — the percentage is a
   * consequence of this rather than an independent thing to assert.
   */
  rqPersistentOffset: 0.031,
  /** Peak RQ inside the window. */
  rqPeak: 1.31,
};

// ── Generator ──────────────────────────────────────────────────────────

interface GenOpts {
  seed: number;
  withExcursion: boolean;
  /** Small run-to-run offsets so the basis has a real spread. */
  biasTiter: number;
}

function biomassAt(tick: number): number {
  const { ticksPerHour, batchEndTick, muBatch, muFeed, x0 } = RUN_CONFIG;
  const h = tick / ticksPerHour;
  const hb = batchEndTick / ticksPerHour;
  if (tick <= batchEndTick) return x0 * Math.exp(muBatch * h);
  const xb = x0 * Math.exp(muBatch * hb);
  // Feed phase is growth-restricted and saturates as the feed profile flattens.
  return xb + (xb * 1.9) * (1 - Math.exp(-muFeed * (h - hb)));
}

function qO2At(tick: number): number {
  const { batchEndTick, qO2Batch, qO2Feed } = RUN_CONFIG;
  if (tick <= batchEndTick) return qO2Batch;
  // Smooth handover across 90 min rather than a step, which no real process shows.
  const w = Math.min(1, (tick - batchEndTick) / 90);
  return qO2Batch + (qO2Feed - qO2Batch) * w;
}

function generate(opts: GenOpts) {
  const { ticksPerHour, durationTicks, otrMax, doSetpoint, rqAerobic, workingVolumeL, temperatureC } = RUN_CONFIG;
  const rnd = mulberry32(opts.seed);
  const n = durationTicks;
  const noise = (amp: number) => (rnd() - 0.5) * 2 * amp;

  const doPct: number[] = [];
  const rpm: number[] = [];
  const air: number[] = [];
  const our: number[] = [];
  const cer: number[] = [];
  const rq: number[] = [];
  const ph: number[] = [];
  const base: number[] = [];
  const temp: number[] = [];
  const offO2: number[] = [];
  const offCO2: number[] = [];
  const heat: number[] = [];
  const closure: number[] = [];
  const lactate: number[] = [];

  let cumCarbonIn = 0;
  let cumCarbonOut = 0;
  let lac = 0;

  for (let t = 0; t < n; t++) {
    const x = biomassAt(t);
    const demand = x * qO2At(t);                       // mmol L⁻¹ h⁻¹ if unlimited
    const inWindow = opts.withExcursion && t >= EXCURSION_SPEC.startTick && t < EXCURSION_SPEC.endTick;
    const afterWindow = opts.withExcursion && t >= EXCURSION_SPEC.endTick;

    // Controller: agitation ramps first, then air. Both saturate.
    const load = Math.min(1, demand / otrMax);
    const rpmT = 350 + 650 * load + noise(6);
    const airT = 0.35 + 0.65 * Math.max(0, load - 0.4) / 0.6 + noise(0.01);

    // Oxygen actually taken up is min(demand, what the vessel can transfer).
    let ourT = Math.min(demand, otrMax) + noise(0.6);
    let doT: number;

    if (inWindow) {
      // Transfer collapses below the controller's reach. DO falls to the floor
      // and respiration becomes transport-limited, so OUR clips well under demand.
      const frac = (t - EXCURSION_SPEC.startTick) / (EXCURSION_SPEC.endTick - EXCURSION_SPEC.startTick);
      doT = doSetpoint - (doSetpoint - EXCURSION_SPEC.doFloor) * Math.min(1, frac * 2.4);
      // Air supply faulted rather than the culture demanding more than the
      // vessel could ever give — consistent with the intermittent grid on
      // this site. Uptake clips to a fraction of demand, which is what makes
      // the deficit an integrable quantity rather than a zero.
      ourT = demand * 0.45 + noise(0.4);
    } else if (afterWindow && t < EXCURSION_SPEC.endTick + 25) {
      // Recovery overshoot, then settle.
      const k = (t - EXCURSION_SPEC.endTick) / 25;
      doT = EXCURSION_SPEC.doFloor + (doSetpoint - EXCURSION_SPEC.doFloor) * (1 - Math.exp(-3.2 * k)) + noise(0.5);
    } else {
      doT = doSetpoint + noise(load > 0.92 ? 1.6 : 0.7);
    }

    // After the window the culture carries a maintenance burden re-assimilating
    // the organic acid it made, so uptake runs slightly under the basis for the
    // rest of the run. This is what "did not return to trajectory" means
    // quantitatively, and it is why the deficit integral keeps growing after
    // the transient has visibly ended.
    if (afterWindow) ourT *= 0.96;

    // RQ: at or below unity when aerobic, above it when the fermentative branch opens.
    let rqT = rqAerobic + noise(0.012);
    if (inWindow) rqT = rqAerobic + (EXCURSION_SPEC.rqPeak - rqAerobic) * Math.min(1, (t - EXCURSION_SPEC.startTick) / 4);
    else if (afterWindow) {
      // Decays out of the fermentative peak, then settles ABOVE the
      // pre-excursion baseline and stays there. That permanent offset is the
      // whole basis of the "did not return to trajectory" finding, and it is
      // why off-gas CO₂ reads high without any offset being added by hand.
      const k = (t - EXCURSION_SPEC.endTick) / 60;
      const settled = rqAerobic + EXCURSION_SPEC.rqPersistentOffset;
      rqT = settled + (EXCURSION_SPEC.rqPeak - settled) * Math.exp(-2.5 * k);
    }

    const cerT = ourT * rqT;

    // Lactate accumulates only while the fermentative branch is open, and it
    // is consumed slowly afterwards rather than disappearing.
    if (inWindow) lac += 0.052;
    else if (lac > 0) lac = Math.max(0, lac - 0.00004);
    lactate.push(lac);

    // Off-gas. Inlet air is 20.95 % O₂. The persistent CO₂ shift after the
    // window is the signal that the culture did not return to trajectory.
    const vvm = airT;
    const gasFlowLPerH = vvm * workingVolumeL * 60;
    const o2Consumed = (ourT * workingVolumeL) / 1000;            // mol h⁻¹
    const co2Made = (cerT * workingVolumeL) / 1000;
    const molGasPerH = (gasFlowLPerH / 22.4) * (273.15 / (273.15 + temperatureC));
    let o2Pct = 20.95 - (o2Consumed / molGasPerH) * 100;
    const co2Pct = 0.04 + (co2Made / molGasPerH) * 100;

    // Carbon balance closure. This channel is SHAPED, not integrated from the
    // other channels — a real closure needs offline substrate and product
    // assays this simulation does not have. It converges on the run-to-run
    // figure recorded in the pool and takes a permanent step down after an
    // excursion. Calling it a mass balance would be the same dishonesty the
    // rest of the package exists to avoid, so it is labelled shaped here and
    // carries a computed Tick in the UI.
    cumCarbonIn += 1 / ticksPerHour;
    cumCarbonOut += 1 / ticksPerHour;
    const settle = 1 - Math.exp(-t / 240);
    const penalty = afterWindow ? 1.3 * (1 - Math.exp(-(t - EXCURSION_SPEC.endTick) / 600)) : 0;
    const closureT = 96.2 * settle + 88 * (1 - settle) - penalty + noise(0.18);

    doPct.push(+doT.toFixed(2));
    rpm.push(Math.round(rpmT));
    air.push(+airT.toFixed(3));
    our.push(+ourT.toFixed(2));
    cer.push(+cerT.toFixed(2));
    rq.push(+rqT.toFixed(3));
    ph.push(+(RUN_CONFIG.phSetpoint + noise(0.015) - (inWindow ? 0.04 : 0)).toFixed(3));
    base.push(+(0.4 + 0.9 * load + (inWindow ? 0.7 : 0) + noise(0.03)).toFixed(3));
    temp.push(+(RUN_CONFIG.temperatureC + noise(0.08)).toFixed(2));
    offO2.push(+o2Pct.toFixed(3));
    offCO2.push(+co2Pct.toFixed(3));
    heat.push(+((ourT * workingVolumeL / 1000) * HEAT_PER_MOL_O2_KJ / 3.6).toFixed(2)); // W
    closure.push(+closureT.toFixed(2));
  }

  const ch = (id: string, label: string, unit: string, derived: boolean, values: number[]): Channel =>
    ({ id, label, unit, derived, values });

  return [
    ch('do', 'Dissolved oxygen', '%', false, doPct),
    ch('rpm', 'Agitation', 'rpm', false, rpm),
    ch('air', 'Air flow', 'VVM', false, air),
    ch('our', 'Oxygen uptake rate', 'mmol L⁻¹ h⁻¹', true, our),
    ch('cer', 'Carbon evolution rate', 'mmol L⁻¹ h⁻¹', true, cer),
    ch('rq', 'Respiratory quotient', '', true, rq),
    ch('ph', 'pH', '', false, ph),
    ch('base', 'Base addition', 'mL h⁻¹', false, base),
    ch('temp', 'Temperature', '°C', false, temp),
    ch('offO2', 'Off-gas O₂', '% v/v', false, offO2),
    ch('offCO2', 'Off-gas CO₂', '% v/v', false, offCO2),
    ch('heat', 'Metabolic heat', 'W', true, heat),
    ch('closure', 'Carbon balance closure', '%', true, closure),
    ch('lactate', 'Lactate (offline)', 'g L⁻¹', false, lactate),
  ];
}

// ── The campaign ───────────────────────────────────────────────────────

const SEALS = ['CS-2026-0084', 'CS-2026-0086', 'CS-2026-0088', 'CS-2026-0091', 'CS-2026-0093', 'CS-2026-0096'];

function run(id: string, seed: number, startedAt: string, withExcursion: boolean, bias: number, deposited: string[]): RunRecord {
  const channels = generate({ seed, withExcursion, biasTiter: bias });
  const excursions: Excursion[] = withExcursion
    ? [{
        id: 'EXC-047-01',
        startTick: EXCURSION_SPEC.startTick,
        endTick: EXCURSION_SPEC.endTick,
        channel: 'do',
        description:
          'Dissolved oxygen fell to 8 % and held there for eleven minutes before the controller recovered it. Off-gas CO₂ shifted 0.4 % absolute and did not return to the pre-excursion trajectory.',
      }]
    : [];
  return {
    id, plantId: 'PLT-KGL-01', organismId: 'ORG-CGL-02', productId: 'L-lysine',
    startedAt, ticksPerHour: RUN_CONFIG.ticksPerHour,
    setpoints: { temperature: 30, ph: 7.0, dissolved_oxygen: 30, mu_setpoint: 0.15 },
    channels, excursions,
    comparisonBasis: id === 'RUN-047' ? ['RUN-042', 'RUN-043', 'RUN-044', 'RUN-045', 'RUN-046'] : [],
    depositedAccessionIds: deposited,
    commonSeal: { id: SEALS[Number(id.slice(-2)) - 42] ?? 'CS-2026-0099', operator: 'N. Uwase', chapterId: 'CH-KGL-01', sealedAt: startedAt },
  };
}

export const RUNS: RunRecord[] = [
  run('RUN-042', 42001, '2026-06-02T07:00:00Z', false, -0.6, ['OF-A-00149']),
  run('RUN-043', 43001, '2026-06-09T07:00:00Z', false, 0.2, []),
  run('RUN-044', 44001, '2026-06-16T07:00:00Z', false, -0.3, []),
  run('RUN-045', 45001, '2026-06-23T07:00:00Z', false, 0.5, ['OF-A-00146']),
  run('RUN-046', 46001, '2026-06-30T07:00:00Z', false, 0.1, []),
  run('RUN-047', 47001, '2026-08-17T07:00:00Z', true, -2.6, ['OF-A-00147', 'OF-A-00148', 'OF-A-00150']),
];

export const RUN_BY_ID: Record<string, RunRecord> = Object.fromEntries(RUNS.map((r) => [r.id, r]));

// ── Excursion integrals — lib/excursion.ts should own these ────────────

const trapz = (y: number[], dx: number) => y.reduce((s, v, i) => (i === 0 ? 0 : s + ((v + y[i - 1]) / 2) * dx), 0);

/**
 * What the verdict quotes. Integrated against the median of the basis runs
 * over the same Tick window, so the numbers answer "how much did this run
 * differ" rather than "what did this run do".
 */
export function excursionIntegrals(runId: string, basisIds: string[]) {
  const r = RUN_BY_ID[runId];
  const exc = r.excursions[0];
  if (!exc) return null;
  const dtH = 1 / r.ticksPerHour;
  const lo = exc.startTick;
  const hi = Math.min(exc.endTick + 120, r.channels[0].values.length); // window plus 2 h of tail

  const pick = (rec: RunRecord, id: string) => rec.channels.find((c) => c.id === id)!.values.slice(lo, hi);
  const basis = basisIds.map((id) => RUN_BY_ID[id]);
  const ourBasis = medianSeries(basis.map((b) => pick(b, 'our')));
  const cerBasis = medianSeries(basis.map((b) => pick(b, 'cer')));
  const ourRun = pick(r, 'our');
  const cerRun = pick(r, 'cer');

  const o2Deficit = trapz(ourBasis.map((v, i) => Math.max(0, v - ourRun[i])), dtH);
  const cerDeviation = trapz(cerRun.map((v, i) => v - cerBasis[i]), dtH);

  return {
    o2DeficitMmolPerL: +o2Deficit.toFixed(2),
    cerDeviationMmolPerL: +cerDeviation.toFixed(2),
    // One mole of O₂ not consumed is roughly one C-mol not fully oxidised.
    estimatedCarbonDivertedCmolPerL: +(o2Deficit * 0.92).toFixed(2),
  };
}

/** Attach integrals at load so the Run page never computes them twice. */
export function hydrateExcursions(): void {
  for (const r of RUNS) {
    for (const e of r.excursions) {
      const it = excursionIntegrals(r.id, r.comparisonBasis);
      if (it) e.integrals = it;
    }
  }
}

/** Saturation concentration at the run temperature — used by the Run page readout. */
export const C_STAR_AT_RUN_TEMP = O2_SOLUBILITY[RUN_CONFIG.temperatureC];
