// openFerment demo suite — the computation layer.
//
// 00-BRIEF.md §4 lists what must be computed rather than hard-coded. This is
// that list, implemented. Split it into lib/units.ts, lib/transport.ts,
// lib/envelope.ts, lib/economics.ts, lib/excursion.ts and lib/patents.ts when
// you wire it in; it is one file here so the package hands over as a unit.
//
// The point of this file is that a reviewer can change an input and watch the
// output move. Anything that only ever renders a stored number is decoration.
import type {
  Accession, Plant, Candidate, EnvelopeMatchResult, PatentFamily, ClaimStatus,
} from '@/data/demo/types';
import {
  O2_SOLUBILITY, HEAT_PER_MOL_O2_KJ, KLA_CORRELATION, UNIT_TABLE, MOLAR_MASS,
  CAPEX_SCALE_EXPONENT, CAPITAL_CHARGE, OPERATING_DAYS, DEMO_NOW,
} from '@/data/demo/core';

// ══════════════════════════════════════════════════════════════════════
// units
// ══════════════════════════════════════════════════════════════════════

export function unitDef(unit: string) {
  return UNIT_TABLE.find((u) => u.unit === unit);
}

/**
 * Recompute an Accession's normalisation from its reported original. The
 * stored `normalized` value is a reading convenience; this is the value the
 * UI should display, so that a wrong authored number surfaces as a mismatch
 * rather than as a plausible-looking lie.
 */
export function normalise(acc: Accession, pool: Record<string, Accession>): number {
  const r = acc.reported.value;
  const { fn, usingAccessionIds } = acc.derivation;

  switch (fn) {
    case 'identity':
      return r;

    case 'temperature': {
      if (acc.field === 'ph') return acc.normalized.value; // medium-specific offset, stated in the note
      const u = unitDef(acc.reported.unit);
      return acc.reported.unit === '°C' ? r : r + (u?.offset ?? 0);
    }

    case 'specific-to-volumetric': {
      const x = pool[usingAccessionIds[0]];
      if (!x) throw new Error(`${acc.id}: auxiliary ${usingAccessionIds[0]} missing`);
      // Key on the TARGET unit, not the reported one. A specific oxygen
      // uptake rate in mmol gDCW⁻¹ h⁻¹ normalises to mmol L⁻¹ h⁻¹ by q·X with
      // no molar mass involved; a specific product rate in the same reported
      // unit normalises to g L⁻¹ h⁻¹ and does need one. Reading the reported
      // unit alone cannot tell those apart.
      const targetIsMolar = acc.normalized.unit.startsWith('mmol') || acc.normalized.unit.startsWith('mol');
      if (targetIsMolar) return r * x.normalized.value;
      const molar = acc.reported.unit.startsWith('mmol');
      const m = molar ? (MOLAR_MASS[acc.context.productId ?? 'L-lysine'] ?? 1) : 1;
      return molar ? (r * m) / 1000 * x.normalized.value : r * x.normalized.value;
    }

    case 'molar-to-mass':
      // Ratio pairs are stated in the derivation note rather than inferred,
      // because the numerator and denominator are different species and
      // guessing them from the field is how a normaliser silently goes wrong.
      return acc.normalized.value;

    case 'yield-basis':
      return acc.normalized.value;

    case 'linear':
    default: {
      if (acc.reported.unit === 'µg L⁻¹') return r * 1e-3;
      if (acc.reported.unit === '% (w/w)' && acc.normalized.unit === 'g g⁻¹') return r * 0.01;
      if (acc.reported.unit === 'EUR kg⁻¹') return r * 1080;
      if (acc.reported.unit === 'fraction' && usingAccessionIds.length === 1) {
        const base = pool[usingAccessionIds[0]];
        if (!base) throw new Error(`${acc.id}: base ${usingAccessionIds[0]} missing`);
        return r * base.normalized.value;
      }
      const u = unitDef(acc.reported.unit);
      return u ? r * u.toCanonical : r;
    }
  }
}

/** The display string. Never render the normalised value alone (§2.4). */
export function accessionDisplay(acc: Accession, pool: Record<string, Accession>): string {
  const v = normalise(acc, pool);
  const orig = `${acc.reported.value} ${acc.reported.unit}`.trim();
  const aux = acc.derivation.usingAccessionIds
    .map((id) => pool[id])
    .filter(Boolean)
    .map((x) => `@ ${x.normalized.value} ${x.normalized.unit}`)
    .join(' ');
  if (acc.reported.unit === acc.normalized.unit) return `${v} ${acc.normalized.unit}`.trim();
  return `${round(v, 4)} ${acc.normalized.unit} (orig. ${orig}${aux ? ' ' + aux : ''})`;
}

const round = (v: number, d = 3) => +v.toFixed(d);

// ══════════════════════════════════════════════════════════════════════
// transport
// ══════════════════════════════════════════════════════════════════════

/** Vessel diameter from working volume and aspect ratio. V = π (H/D) D³ / 4. */
export function vesselDiameterM(volumeM3: number, hOverD: number): number {
  return Math.cbrt((4 * volumeM3) / (Math.PI * hOverD));
}

export function crossSectionM2(volumeM3: number, hOverD: number): number {
  const d = vesselDiameterM(volumeM3, hOverD);
  return (Math.PI * d * d) / 4;
}

/** Superficial gas velocity, m s⁻¹, from VVM. */
export function superficialGasVelocity(vvm: number, volumeM3: number, hOverD: number): number {
  const qM3PerS = (vvm * volumeM3) / 60;
  return qM3PerS / crossSectionM2(volumeM3, hOverD);
}

/**
 * van 't Riet. Returns h⁻¹. `coalescing` is clean water; use it with an
 * explicit broth factor rather than reaching for the non-coalescing constants,
 * because a kLa quoted without a broth factor is the most common way a plant
 * gets specified wrong.
 */
export function klaVantRiet(
  powerPerVolumeWm3: number,
  vsMPerS: number,
  mode: 'coalescing' | 'nonCoalescing' = 'coalescing',
): number {
  const { C, a, b } = KLA_CORRELATION[mode];
  return C * Math.pow(powerPerVolumeWm3, a) * Math.pow(vsMPerS, b) * 3600;
}

/** Oxygen saturation, mmol L⁻¹, at temperature and absolute pressure. */
export function cStar(tempC: number, pressureBara = 1.0): number {
  const keys = Object.keys(O2_SOLUBILITY).map(Number).sort((p, q) => p - q);
  const lo = keys.filter((k) => k <= tempC).pop() ?? keys[0];
  const hi = keys.find((k) => k >= tempC) ?? keys[keys.length - 1];
  const base =
    lo === hi
      ? O2_SOLUBILITY[lo]
      : O2_SOLUBILITY[lo] + ((tempC - lo) / (hi - lo)) * (O2_SOLUBILITY[hi] - O2_SOLUBILITY[lo]);
  return base * pressureBara;
}

/** OTR ceiling, mmol L⁻¹ h⁻¹, at a given DO setpoint expressed as % of saturation. */
export function otrCeiling(klaPerH: number, tempC: number, doSetpointPct: number, pressureBara = 1.0): number {
  const cs = cStar(tempC, pressureBara);
  return klaPerH * (cs - cs * (doSetpointPct / 100));
}

/** Metabolic heat, kW, from oxygen uptake. */
export function metabolicHeatKW(ourMmolPerLPerH: number, volumeL: number): number {
  return (ourMmolPerLPerH * volumeL * HEAT_PER_MOL_O2_KJ) / 1000 / 3600;
}

/** The OUR above which the installed chiller cannot keep up. */
export function coolingCeiling(chillerKW: number, agitationKW: number, totalVolumeL: number): number {
  const availableKW = chillerKW - agitationKW;
  return (availableKW * 3600 * 1000) / HEAT_PER_MOL_O2_KJ / totalVolumeL;
}

/** Everything the Archetype 3 envelope panel needs, from the plant alone. */
export function plantCeilings(plant: Plant, opts?: { brothFactor?: number; pressureBara?: number; doSetpointPct?: number; tempC?: number }) {
  const brothFactor = opts?.brothFactor ?? 0.46;
  const pressureBara = opts?.pressureBara ?? 1.0;
  const doPct = opts?.doSetpointPct ?? 20;
  const tempC = opts?.tempC ?? 30;
  const { workingVolumeM3, hOverD, installedPowerPerVolume, maxAerationVvm, count } = plant.vessels;

  const vs = superficialGasVelocity(maxAerationVvm, workingVolumeM3, hOverD);
  const klaClean = klaVantRiet(installedPowerPerVolume, vs);
  const klaEff = klaClean * brothFactor;
  const agitationKW = (installedPowerPerVolume * workingVolumeM3 * count) / 1000;

  return {
    vesselDiameterM: round(vesselDiameterM(workingVolumeM3, hOverD), 3),
    superficialGasVelocity: round(vs, 4),
    klaClean: round(klaClean, 1),
    klaEffective: round(klaEff, 1),
    cStar: round(cStar(tempC, pressureBara), 4),
    otrCeiling: round(otrCeiling(klaEff, tempC, doPct, pressureBara), 1),
    agitationKW: round(agitationKW, 1),
    coolingCeiling: round(coolingCeiling(plant.utilities.chilledWaterKW, agitationKW, workingVolumeM3 * count * 1000), 1),
    /** Driving force to ambient cooling water. The tropical constraint, stated. */
    towerDrivingForceK: round(tempC - plant.utilities.coolingTowerSupplyC, 1),
  };
}

// ══════════════════════════════════════════════════════════════════════
// envelope matching
// ══════════════════════════════════════════════════════════════════════

/** Power per volume a rheology class REQUIRES to keep a vessel mixed. */
const VISCOSITY_POWER_REQUIRED: Record<string, number> = {
  'newtonian-low': 800,
  'newtonian-high': 1400,
  'non-newtonian': 3500,
};

/**
 * Separation headroom. A centrifuge and a filter are on site. Crystallisation
 * and extraction are additions a project can make; a distillation column is a
 * different plant, so it is a hard exclusion rather than a cost line.
 */
const SEPARATION_HEADROOM: Record<string, number> = {
  centrifuge: 1,
  filtration: 1,
  crystallisation: 0.1,
  extraction: 0.1,
  distillation: -1,
};

/**
 * Demand vector against supply envelope, one row per axis. A candidate
 * survives when every axis has non-negative headroom. Failed candidates keep
 * their rows — a screen that shows only survivors is a screen a reviewer
 * distrusts.
 */
export function matchEnvelope(plant: Plant, cand: Candidate, opts?: { pressureBara?: number }): EnvelopeMatchResult {
  const c = plantCeilings(plant, { pressureBara: opts?.pressureBara ?? 1.0, tempC: cand.demand.temperatureC });
  const totalVolumeL = plant.vessels.workingVolumeM3 * plant.vessels.count * 1000;
  const heatDemandKW = metabolicHeatKW(cand.demand.otrRequired, totalVolumeL) + c.agitationKW;

  const rows: EnvelopeMatchResult['axes'] = [
    {
      axis: 'Oxygen transfer',
      demand: cand.demand.otrRequired,
      supply: c.otrCeiling,
      headroom: (c.otrCeiling - cand.demand.otrRequired) / Math.max(1e-9, c.otrCeiling),
      binding: false,
    },
    {
      axis: 'Cooling duty',
      demand: round(heatDemandKW, 1),
      supply: plant.utilities.chilledWaterKW,
      headroom: (plant.utilities.chilledWaterKW - heatDemandKW) / plant.utilities.chilledWaterKW,
      binding: false,
    },
    {
      axis: 'Installed power',
      demand: cand.demand.powerPerVolume,
      supply: plant.vessels.installedPowerPerVolume,
      headroom: (plant.vessels.installedPowerPerVolume - cand.demand.powerPerVolume) / plant.vessels.installedPowerPerVolume,
      binding: false,
    },
    {
      axis: 'Rheology',
      demand: `${cand.demand.viscosityClass} — needs ${VISCOSITY_POWER_REQUIRED[cand.demand.viscosityClass]} W m⁻³`,
      supply: `${plant.vessels.impeller} at ${plant.vessels.installedPowerPerVolume} W m⁻³`,
      headroom:
        (plant.vessels.installedPowerPerVolume - VISCOSITY_POWER_REQUIRED[cand.demand.viscosityClass]) /
        VISCOSITY_POWER_REQUIRED[cand.demand.viscosityClass],
      binding: false,
    },
    {
      axis: 'Separation',
      demand: cand.demand.separationClass,
      supply: plant.downstream.map((d) => d.unit).join(', '),
      headroom: SEPARATION_HEADROOM[cand.demand.separationClass] ?? -1,
      binding: false,
    },
    {
      axis: 'Thermal driving force',
      demand: `${cand.demand.temperatureC} °C broth`,
      supply: `${plant.utilities.coolingTowerSupplyC} °C tower water`,
      // Informational. The chiller sets the real limit and it is already
      // counted on the cooling axis; a low driving force raises chiller duty
      // rather than excluding a candidate outright, so this never binds.
      headroom: Math.max(0.01, (cand.demand.temperatureC - plant.utilities.coolingTowerSupplyC) / 25),
      binding: false,
    },
  ];

  const worst = rows.reduce((a, b) => (a.headroom <= b.headroom ? a : b));
  worst.binding = true;
  const feasible = worst.headroom >= 0;
  // Only name a binding axis when the candidate actually fails. On a survivor
  // the tightest axis is still just the tightest axis, and labelling it
  // "binding" reads as an accusation the match does not support.
  return {
    axes: rows.map((r) => ({ ...r, headroom: round(r.headroom, 4) })),
    feasible,
    ...(feasible ? {} : { bindingAxis: worst.axis }),
  };
}

/** Verdict from the match plus the FTO position. Never authored in the seed. */
export function verdictFor(m: EnvelopeMatchResult, cand: Candidate, jurisdiction: string): Candidate['verdict'] {
  const blockedHere = cand.patentPosition.some((p) => p.jurisdiction === jurisdiction && (p.status === 'enclosed' || p.status === 'expiring'));
  if (blockedHere) return 'excluded';
  if (!m.feasible) return cand.rescue ? 'marginal' : 'excluded';
  const tightest = Math.min(...m.axes.map((a) => a.headroom));
  if (tightest < 0.08) return 'marginal';
  return 'viable';
}

// ══════════════════════════════════════════════════════════════════════
// economics
// ══════════════════════════════════════════════════════════════════════

/**
 * Six-tenths rule against the anchor in OF-A-00416. Note that the bottom-up
 * equipment estimates in BAGASSE_CONCEPTS will not sit on this line and are
 * not supposed to — the curve is a single-product reference and FC-001 is a
 * two-product plant. Plot the concepts against the line and let the gap show.
 */
export function capexAtScale(refCapexUSD: number, refScale: number, scale: number, exponent = CAPEX_SCALE_EXPONENT): number {
  return refCapexUSD * Math.pow(scale / refScale, exponent);
}

export function annualisedCostUSD(capexUSD: number, opexPerTonne: number, tonnesPerYear: number): number {
  return capexUSD * CAPITAL_CHARGE + opexPerTonne * tonnesPerYear;
}

export function minimumSellingPrice(capexUSD: number, opexPerTonne: number, tonnesPerYear: number): number {
  return annualisedCostUSD(capexUSD, opexPerTonne, tonnesPerYear) / tonnesPerYear;
}

/** Where MSP crosses the achievable price. Bisection; the curve is monotone. */
export function breakevenTonnesPerYear(capexUSD: number, refScale: number, opexPerTonne: number, priceUSDPerTonne: number): number {
  let lo = 100;
  let hi = refScale * 6;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    const msp = minimumSellingPrice(capexAtScale(capexUSD, refScale, mid), opexPerTonne, mid);
    if (msp > priceUSDPerTonne) lo = mid;
    else hi = mid;
  }
  return Math.round((lo + hi) / 2);
}

/** Annual capacity a plant can actually turn out, from cycle time and turns. */
export function annualCapacityTonnes(titerGPerL: number, volumeL: number, vessels: number, cycleTimeH: number, downstreamYield: number): number {
  const turnsPerYear = (OPERATING_DAYS * 24) / cycleTimeH;
  return (titerGPerL * volumeL * vessels * turnsPerYear * downstreamYield) / 1e6;
}

export function importDisplacementUSD(capacityTonnes: number, importVolumeTonnes: number, cifUSDPerTonne: number, landedCostUSDPerTonne: number): number {
  return Math.min(capacityTonnes, importVolumeTonnes) * (cifUSDPerTonne - landedCostUSDPerTonne);
}

// ══════════════════════════════════════════════════════════════════════
// excursion
// ══════════════════════════════════════════════════════════════════════

export function trapezoid(y: number[], dx: number): number {
  let s = 0;
  for (let i = 1; i < y.length; i++) s += ((y[i] + y[i - 1]) / 2) * dx;
  return s;
}

export function medianSeries(rows: number[][]): number[] {
  return rows[0].map((_, i) => {
    const col = rows.map((r) => r[i]).sort((a, b) => a - b);
    return col[Math.floor(col.length / 2)];
  });
}

/**
 * Does the trajectory recover? The verdict turns on this more than on the
 * depth or the duration, so it is a named function rather than an inline test.
 * Compares the post-window mean against the pre-window mean, both taken
 * outside the transient itself.
 */
export function trajectoryRecovered(series: number[], startTick: number, endTick: number, tolerance = 0.05): boolean {
  const pre = series.slice(Math.max(0, startTick - 60), startTick);
  const post = series.slice(endTick + 60, endTick + 180);
  if (!pre.length || !post.length) return true;
  const mean = (x: number[]) => x.reduce((a, b) => a + b, 0) / x.length;
  const p = mean(pre);
  return Math.abs(mean(post) - p) / Math.max(1e-9, Math.abs(p)) <= tolerance;
}

// ══════════════════════════════════════════════════════════════════════
// patents
// ══════════════════════════════════════════════════════════════════════

export function monthsToExpiry(iso: string, demoNow = DEMO_NOW): number {
  return Math.round((new Date(iso).getTime() - new Date(demoNow).getTime()) / (1000 * 60 * 60 * 24 * 30.44));
}

export function statusIn(family: PatentFamily, jurisdiction: string, horizonMonths = 24): ClaimStatus {
  const j = family.jurisdictions.find((x) => x.code === jurisdiction);
  if (!j) return 'never-nationalised';
  if (j.status === 'never-nationalised' || j.status === 'expired' || j.status === 'pending' || j.status === 'no-claim-found') return j.status;
  if (!j.expiry) return j.status;
  const m = monthsToExpiry(j.expiry);
  if (m <= 0) return 'expired';
  if (m <= horizonMonths) return 'expiring';
  return 'enclosed';
}

/** Open surface for a route, recomputed per jurisdiction rather than stored. */
export function openSurfaceIn(
  stepClaims: { patentFamilyId: string; jurisdictions: string[] }[][],
  families: Record<string, PatentFamily>,
  jurisdiction: string,
) {
  let enclosed = 0;
  let expiring = 0;
  for (const claims of stepClaims) {
    const s = claims.map((c) => (c.jurisdictions.includes(jurisdiction) ? statusIn(families[c.patentFamilyId], jurisdiction) : 'never-nationalised'));
    if (s.includes('enclosed')) enclosed++;
    else if (s.includes('expiring')) expiring++;
  }
  return { totalSteps: stepClaims.length, enclosedSteps: enclosed, expiringSteps: expiring };
}

// ══════════════════════════════════════════════════════════════════════
// the contradiction rail's statistics
// ══════════════════════════════════════════════════════════════════════
//
// Pure, and here rather than in the component, because `check:demo-seed` must
// assert over them and it runs under node where a component's `href` import
// touches `window`. A rule a gate cannot reach is a rule nobody is holding.

import type { Accession as _Accession, FieldId as _FieldId } from '@/data/demo/types';
import { ACCESSIONS as _ACCESSIONS, ACCESSION_BY_ID as _BY_ID } from '@/data/demo/accessions';

/** Accessions on a field, pool order preserved. */
export function accessionsOnField(field: _FieldId, pool: _Accession[] = _ACCESSIONS): _Accession[] {
  return pool.filter((a) => a.field === field);
}

/** The ones that may enter a statistic: not held, and primary. */
export function countable(accs: _Accession[]): _Accession[] {
  return accs.filter((a) => !a.hold && a.isPrimary);
}

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function quartiles(xs: number[]): { q1: number; q3: number } | null {
  if (xs.length < 4) return null;
  const s = [...xs].sort((a, b) => a - b);
  const at = (p: number) => {
    const i = (s.length - 1) * p;
    const lo = Math.floor(i);
    const hi = Math.ceil(i);
    return s[lo] + (s[hi] - s[lo]) * (i - lo);
  };
  return { q1: at(0.25), q3: at(0.75) };
}

/**
 * Is there a real disagreement on this field?
 *
 * Two Accessions conflict when one NAMES the other in `conflictsWith`. That is
 * a curation decision recorded in the seed, deliberately, rather than something
 * inferred from spread: two values far apart under different organisms are not
 * in conflict, and two values close together can be (contradiction 2 in
 * OF-DEMO-003 §5 is an identical measured outcome whose IMPLICATIONS differ).
 * Spread cannot tell those apart and a curator can.
 */
export function isContradiction(accs: _Accession[]): boolean {
  return accs.some((a) => (a.conflictsWith ?? []).some((id) => accs.some((b) => b.id === id)));
}

/** The conflicting pairs, deduplicated, both directions collapsed to one. */
/**
 * Pairs that LOOK like they disagree and do not, once the units are closed.
 *
 * Rendered differently from a conflict on purpose: an unresolved pair is a
 * warning and a reconciled pair is the system working. Filing the second under
 * the first would make the interface cry wolf about its own success.
 */
export function reconciledPairs(accs: _Accession[]): [_Accession, _Accession][] {
  const out: [_Accession, _Accession][] = [];
  const seen = new Set<string>();
  for (const a of accs) {
    for (const id of a.reconciledWith ?? []) {
      const b = _BY_ID[id];
      if (!b || !accs.includes(b)) continue;
      const key = [a.id, b.id].sort().join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      out.push([a, b]);
    }
  }
  return out;
}

export function conflictPairs(accs: _Accession[]): [Accession, Accession][] {
  const out: [Accession, Accession][] = [];
  const seen = new Set<string>();
  for (const a of accs) {
    for (const id of a.conflictsWith ?? []) {
      const b = _BY_ID[id];
      if (!b || !accs.includes(b)) continue;
      const key = [a.id, b.id].sort().join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      out.push([a, b]);
    }
  }
  return out;
}



/**
 * Every curator-linked pair in the pool, unresolved and reconciled alike.
 *
 * One implementation, because the BioRepo index states the count and the
 * contradiction queue lists the rows, and a count that disagrees with the list
 * it links to is worse than no count. A pair is here because a curator LINKED
 * it, never because two numbers are far apart — spread cannot tell a
 * disagreement from two different experiments.
 */
export function contradictionRows(): {
  field: _FieldId;
  kind: 'unresolved' | 'reconciled';
  pair: [Accession, Accession];
}[] {
  const out: { field: _FieldId; kind: 'unresolved' | 'reconciled'; pair: [Accession, Accession] }[] = [];
  const fields = [...new Set(_ACCESSIONS.map((a) => a.field))] as _FieldId[];
  for (const f of fields) {
    const accs = accessionsOnField(f);
    for (const pair of conflictPairs(accs)) out.push({ field: f, kind: 'unresolved', pair });
    for (const pair of reconciledPairs(accs)) out.push({ field: f, kind: 'reconciled', pair });
  }
  return out;
}

// ══════════════════════════════════════════════════════════════════════
// routes
// ══════════════════════════════════════════════════════════════════════
//
// The one place that answers "where does this id render". It lives here rather
// than in `screens/demo/Repo.tsx`, where it used to, because everything that
// needs it is upstream of that screen: the corpus's agent workspace resolves
// `chip:` follow-ups, the Notary queue links back to the deliverable that
// produced each candidate, and `DemoChip` renders an id it has just resolved.
// Importing a screen module to get a route is a cycle, and `DemoChip` paid for
// it by hard-coding `/bench` for every `DLV-*` chip rather than importing.

import { DELIVERABLES as _DELIVERABLES } from '@/data/demo/archetypes';

/**
 * Where a `chip:<id>` follow-up goes.
 *
 * The archetype flows end with `chip:DLV-AR5-001|Open the decomposition tree`
 * and nothing in the UI knew what `chip:` meant — the button rendered with the
 * raw string as its label and clicking it fed that string back to the matcher
 * as a question. One resolver, covering every id kind a follow-up can name, so
 * a new chip kind is one line here rather than a new prefix nobody handles.
 */
export function chipRoute(id: string): string {
  if (id.startsWith('DLV-')) return deliverableRoute(id);
  if (id.startsWith('RB-')) return `/runbook/design/${id}`;
  if (id.startsWith('RUN-')) return `/fermos/runs/${id}`;
  if (id.startsWith('OF-A-')) return `/repo/a/${id}`;
  if (id.startsWith('PF-')) return `/parchment/families#${id}`;
  // The Bench, which shows the state of both pools. `/bench` used to be a
  // second home of its own; it canonicalises here now.
  return '/';
}

/** Where a deliverable renders. One table, so no screen invents a route. */
export function deliverableRoute(deliverableId: string): string {
  const d = _DELIVERABLES.find((x) => x.id === deliverableId);
  if (!d) return '/repo';
  switch (d.payload.kind) {
    case 'factor-map':
      return `/fermos/gap/${d.id}`;
    case 'route-comparison':
      return `/geneos/routes/${d.payload.productId}`;
    case 'capacity-screen':
      return `/proforma/screen/${d.payload.plantId}`;
    case 'facility-concept':
      return `/proforma/concept/${d.id}`;
    case 'problem-tree':
      return `/postdoc/tree/${d.id}`;
    case 'excursion-verdict':
      return `/fermos/runs/${d.payload.runId}`;
    default:
      return '/repo';
  }
}
