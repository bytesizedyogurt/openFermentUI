// The browser's side of fermOS (OF-BLD-014 §7.4, OF-BLD-020 §3.3).
//
// A deposition's series go to the service, which fits them and keeps the fit
// as an artifact; a forecast is asked of a kept fit, or of the sample run's
// fit inline. The fitted curve drawn through the points is the closed form
// the service fitted, evaluated here on its parameters; it computes nothing
// the fit did not already hold. Shares lib/http.ts's call and its failures.
//
// A SIMULATION (OF-BLD-020 §3.3, D1) is asked of the service whole: the
// families (`GET /api/fermos/families`), what binds and what waits with the
// person's overrides laid on (`GET /api/fermos/bind`), the run
// (`POST /api/fermos/simulate`, one kept `fermos.simulation` artifact) and
// the kept ones (`GET /api/fermos/simulations`). The browser sends ids,
// words and the scope's overrides, each a typed input in its parameter's unit
// (lib/params.ts, `inputsOf`), and draws what comes back; it computes no value
// of a simulation.
//
// Every shape the service answers or takes here is generated from its models
// into src/api/types.gen.ts (ADR-007) and named below: a fit and its series,
// a forecast, a family, a binding, a simulation, a harvest and a vessel. A
// deposition and the runbook it was taken on are the store's own shapes.
import type { components } from '@/api/types.gen';
import type { Deposition, Runbook } from '@/data/types';
import { seriesOf } from '@/engine/series';
import type { TimeCourseProps, TrajectorySeries } from '@/components/figures';
import { ServiceDown, ServiceRefused, call } from './http';
import { inputsOf, type Override, type ParameterSpec } from './params';

export { ServiceDown as FermosDown, ServiceRefused as FermosRefused };

type S = components['schemas'];

/** One measure's readings in time order, as `seriesOf` makes them and a fit takes them. */
export type FermosSeries = S['FermosSeries'];
/** One fitted parameter, its 95 % interval and its unit, with why a fit reports it unidentified. */
export type FitParam = S['FitParam'];
/** Why a fitted parameter is unidentified: the gauge X0 of a run with no biomass series, the no-biomass rule on μmax, the optimizer's budget, the Jacobian's null space, the interval reaching zero. */
export type UnidentifiedReason = NonNullable<FitParam['unidentifiedBy']>[number];
/** A kinetic model fitted to a run's series: the closed-form logistic, or a kinetics family. */
export type KineticFit = S['KineticFit'];
/** `POST /api/fermos/fit`: the growth rate and the kinetic fit of a run's series, each with the artifact it is kept as; the sample run's are kept nowhere. */
export type FermosFitResponse = S['FermosFitResponse'];
/** One role's forecast band over the forecast's times. */
export type Band = S['Band'];
/** `POST /api/fermos/forecast`: a band for the next run, drawn from a fit. */
export type ForecastResult = S['ForecastResult'];
/** `GET /api/fermos/families`: a model family as the panel shows it. */
export type FamilyInfo = S['FamilyInfo'];
/** `GET /api/fermos/bind`: a family's parameters bound as a simulation would bind them, starting no integration. */
export type FermosBinding = S['FermosBinding'];
/** One kept `fermos.simulation` artifact as every reader reads it, and a chemostat's steady state within it. */
export type SimulationResult = S['SimulationResult'];
export type SteadyState = S['SteadyState'];
/** `GET /api/fermos/simulations`: one kept simulation, newest first. */
export type SimulationSummary = S['SimulationSummary'];
/** `GET /api/fermos/harvest`: a kept simulation's broth at an hour. */
export type FermosHarvest = S['FermosHarvest'];
/** `POST /api/fermos/vessel`: what a design is asked with, and the one `fermos.vessel` artifact it answers, read. */
export type VesselRequest = S['VesselRequest'];
export type VesselDesign = S['VesselDesign'];

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

/** The families a run's series can be fitted to (fermos.FIT_FAMILIES): the closed-form logistic, and the batch family. */
export const FIT_FAMILIES = ['logistic_v0', 'batch_v1'] as const;
export type FitFamily = (typeof FIT_FAMILIES)[number];
export const LOGISTIC = 'logistic_v0';
/** What each fit family is, in words, for the Fits tab's chooser. */
export const FIT_FAMILY_WORDS: Record<FitFamily, string> = {
  logistic_v0: 'Logistic growth, Luedeking–Piret production and the sugar balance, in closed form',
  batch_v1: 'The batch family: Monod growth with inhibition, integrated, fitted to product and sugar',
};
export const isFitFamily = (id: string | null | undefined): id is FitFamily => (FIT_FAMILIES as readonly string[]).includes(id ?? '');

export const fermosFit = (depositionId: string, series: FermosSeries[], sample = false, signal?: AbortSignal, family: FitFamily = LOGISTIC) =>
  post<FermosFitResponse>('/api/fermos/fit', { depositionId, series, sample, family }, signal);

// ── a simulation (OF-BLD-020 §3.3) ─────────────────────────────────────

/** A family's parameter scope: the panel's, the run's overrides' and the bind's. */
export const familyScope = (family: string) => `fermos:family:${family}`;
/** A logistic fit's forecast scope: its start values and length, in the panel. */
export const forecastScope = (fitArtifactId: string) => `fermos:forecast:${fitArtifactId}`;
export const UNTIL_RUN_OUT = 'until-sugar-runs-out';
export const FIT_LENGTH = 'fit-length';

/** What a simulation is asked with besides the overrides: ids and words alone. */
export interface SimulateAsk {
  family: string;
  /** Null: any strain the bound records name. */
  strain: string | null;
  product: string | null;
  sugar: string | null;
  fitArtifact: string | null;
  /** 'records', 'fit', or 'simulation:<artifact id>'. */
  startFrom: string;
  durationPreset: typeof UNTIL_RUN_OUT | typeof FIT_LENGTH;
}

/** The parameter panel's ask for the same binding (GET /api/params/fermos:family:<id>). */
export const paramAskOf = (ask: SimulateAsk) => ({
  strain: ask.strain,
  product: ask.product,
  sugar: ask.sugar,
  fit: ask.fitArtifact,
  startFrom: ask.startFrom,
  durationPreset: ask.durationPreset,
});

/** Every model family. */
export const fermosFamilies = (signal?: AbortSignal) => call<FamilyInfo[]>('/api/fermos/families', { signal });

/** What binds and what waits, with the person's overrides laid on (as inputs in the family's units), as Simulate would bind it. */
export function fermosBind(ask: SimulateAsk, overrides: Override[], specs: ParameterSpec[], signal?: AbortSignal): Promise<FermosBinding> {
  const q = new URLSearchParams({ family: ask.family, startFrom: ask.startFrom, durationPreset: ask.durationPreset });
  for (const k of ['strain', 'product', 'sugar'] as const) if (ask[k]) q.set(k, ask[k] as string);
  if (ask.fitArtifact) q.set('fit', ask.fitArtifact);
  if (overrides.length > 0) q.set('inputs', JSON.stringify(inputsOf(overrides, specs)));
  return call<FermosBinding>(`/api/fermos/bind?${q.toString()}`, { signal });
}

/** Simulate: the scope's overrides go with the run as inputs in the family's units, each an assumption by its person; `by` is who asks. */
export const fermosSimulate = (ask: SimulateAsk, overrides: Override[], specs: ParameterSpec[], by: string, signal?: AbortSignal) =>
  post<SimulationResult>('/api/fermos/simulate', { ...ask, inputs: inputsOf(overrides, specs), by }, signal);

/** The kept simulations, newest first (`GET /api/fermos/simulations`). Simulate and Vessel both read it. */
export const fermosSimulations = (signal?: AbortSignal) => call<SimulationSummary[]>('/api/fermos/simulations', { signal });

/**
 * OF-BLD-020 §6.2 (D10) — a kept simulation's broth at an hour, read by the
 * service from the series the artifact keeps (`GET /api/fermos/harvest`):
 * its own harvest hour, or `hour`, a person's (the value their inlet scope
 * holds; a model never sends one). Nothing is integrated again or kept, and
 * the browser computes nothing of it: it shows each state with its unit.
 */
export function fermosHarvest(simulationId: string, hour: number | null, signal?: AbortSignal) {
  const q = new URLSearchParams({ simulation: simulationId });
  if (hour != null) q.set('hour', String(hour));
  return call<FermosHarvest>(`/api/fermos/harvest?${q.toString()}`, { signal });
}

/** The word for each state a family integrates, on the time course and in its table. */
export const STATE_WORDS: Record<string, string> = {
  X: 'Cells (X)',
  S: 'Substrate (S)',
  P: 'Product (P)',
  V: 'Working volume (V)',
  N: 'Second nutrient (N)',
  Q: 'Stored product (Q)',
};

/** Whether a state's values move over the run: a volume that never changes is not drawn (V where it varies). */
export const varies = (values: number[]) => values.some((v) => v !== values[0]);

/**
 * A kept simulation as TimeCourse draws it: every state it integrated (the
 * volume where it varies), the oxygen uptake rate when the culture takes up
 * any, and Yp/s and the yield it achieved beside each ceiling the service
 * read, flagged as the service flagged it. Read from the artifact; nothing
 * is computed here.
 */
export function timeCourseOf(r: SimulationResult): Omit<TimeCourseProps, 'title'> {
  const t = r.series.t ?? [];
  const states = Object.keys(r.series)
    .filter((k) => k !== 't' && (k !== 'V' || varies(r.series[k])))
    .map((k) => ({ key: k, label: STATE_WORDS[k] ?? k, unit: r.units[k] ?? '', values: r.series[k] }));
  const yps = r.parameters.find((p) => p.key === 'yps')?.value;
  const rows = r.ceiling?.rows ?? [];
  const hasYield = typeof yps === 'number' || r.yieldAchieved != null;
  return {
    t,
    states,
    provenance: r.provenance,
    our: r.aerobic && varies(r.our.value) ? { unit: r.our.unit, values: r.our.value } : null,
    yields: hasYield
      ? {
          unit: 'g g⁻¹',
          points: [
            { label: 'Yp/s, the parameter', value: typeof yps === 'number' ? yps : null, above: rows.some((c) => c.above) },
            { label: 'yield achieved', value: r.yieldAchieved },
          ],
          ceilings: rows.map((c) => ({ label: `${c.modelId} ceiling`, value: c.ceilingGPerG, provenance: c.provenance, above: c.above })),
        }
      : null,
    basis: [r.basis],
    notes: r.notes,
  };
}

/** Where Design the vessel goes for a kept simulation (fermOS → Vessel, OF-BLD-020 §4.2). */
export const vesselPath = (simulationId: string) => `/fermos/vessel?simulation=${encodeURIComponent(simulationId)}`;
/** Where Simulate from a fit goes: the family the fit is of, started from it. */
export const simulateFromFitPath = (family: string, fitId: string) =>
  `/fermos/simulate?family=${encodeURIComponent(family)}&start=fit&fit=${encodeURIComponent(fitId)}`;

/**
 * A forecast (`POST /api/fermos/forecast`): its start values and length are
 * its scope's overrides (`fermos:forecast:<fit id>`: x0, s0, p0 and t_end),
 * sent as inputs in the units the scope's specs name, each as typed. Unset
 * ones are the run's own; a changed one names the person who typed it, with
 * the day it was typed (OF-BLD-020 §3.R): the service keeps each an
 * assumption by name, and the forecast is assumed.
 */
export const fermosForecast = (
  req: {
    fitArtifactId?: string | null;
    fit?: KineticFit | null;
    overrides?: Override[];
    specs?: ParameterSpec[];
    by?: string;
    sample?: boolean;
  },
  signal?: AbortSignal,
) =>
  post<ForecastResult>(
    '/api/fermos/forecast',
    {
      fitArtifactId: req.fitArtifactId ?? null,
      fit: req.fit ?? null,
      inputs: inputsOf(req.overrides ?? [], req.specs ?? []),
      by: req.by ?? '',
      sample: req.sample ?? false,
    },
    signal,
  );

/** A deposition's series with a role, as the service takes them. */
export function fitSeriesOf(dep: Deposition, runbook: Runbook): FermosSeries[] {
  return seriesOf(dep, runbook).filter((s) => s.role).map((s) => ({ ...s, role: s.role }));
}

/** A deposition fermOS can fit: a biomass series of four or more readings. */
export function qualifies(dep: Deposition, runbook: Runbook | undefined): boolean {
  if (!runbook) return false;
  return seriesOf(dep, runbook).some((s) => s.role === 'biomass' && s.points.length >= 4);
}

const value = (fit: KineticFit, name: string) => fit.params?.find((p) => p.name === name)?.value;

/** The fitted closed form for one role at `t` hours, or null when the fit lacks it. */
export function curveAt(fit: KineticFit, role: string, t: number): number | null {
  const x0 = value(fit, 'X0');
  const mu = value(fit, 'mu');
  const xmax = value(fit, 'Xmax');
  if (x0 == null || mu == null || xmax == null) return null;
  const denom = x0 + (xmax - x0) * Math.exp(-mu * t);
  const x = (x0 * xmax) / denom;
  const integral = xmax * t + (xmax / mu) * Math.log(denom / xmax);
  if (role === 'biomass') return x;
  const [z, a, b] = role === 'product' ? ['P0', 'alpha', 'beta'] : ['S0', 'gamma', 'delta'];
  const k0 = value(fit, z);
  const ka = value(fit, a);
  const kb = value(fit, b);
  if (k0 == null || ka == null || kb == null) return null;
  const sign = role === 'product' ? 1 : -1;
  return k0 + sign * (ka * (x - x0) + kb * integral);
}

/** The curve sampled at `n` points over `tmax` hours. */
export function curve(fit: KineticFit, role: string, tmax: number, n = 60): { t: number; value: number }[] {
  const out: { t: number; value: number }[] = [];
  for (let i = 0; i < n; i++) {
    const t = (tmax * i) / (n - 1);
    const v = curveAt(fit, role, t);
    if (v !== null && Number.isFinite(v)) out.push({ t, value: v });
  }
  return out;
}

/** The figure for one run: readings, residuals and the fitted curves. */
export function fitFigureSeries(series: FermosSeries[], fit: KineticFit | null): TrajectorySeries[] {
  const tmax = Math.max(1e-9, ...series.flatMap((s) => (s.points ?? []).map((p) => p.t)));
  return series
    .filter((s) => s.role)
    .map((s) => {
      const q = fit?.quality?.find((x) => x.measureId === s.measureId);
      return {
        role: s.role!,
        label: s.label,
        unit: s.unit,
        readings: (s.points ?? []).map((p, i) => ({ t: p.t, value: p.value, residual: q?.residuals?.[i] ?? null })),
        fitted: fit?.params?.length ? curve(fit, s.role!, tmax) : undefined,
      };
    });
}


// ── fermOS → Vessel (OF-BLD-020 §4.2, D7) ──────────────────────────────
//
// The vessel a kept simulation (or, anaerobic, a kept fit) needs, designed by
// BioSTEAM in the service's Proforma worker. The browser asks and shows: the
// scope's parameters come from `GET /api/params/fermos:vessel:<id>` through
// the panel, a person's changes are the scope's overrides (the project's rows), and
// `POST /api/fermos/vessel` designs. Nothing here computes a value.

/** The flowsheet a fit is read through for a vessel: its titre, yield and batch time, as the ethanol flowsheet reads them (vessel.FIT_FLOWSHEET). */
export const VESSEL_FIT_FLOWSHEET = 'ethanol_glucose_v0';

/** The vessel scope of a simulation or a fit: `fermos:vessel:<artifact id>`. */
export const vesselScope = (sourceId: string) => `fermos:vessel:${sourceId}`;

export type VesselType = 'stirred-tank' | 'bubble-column';

/** BioSTEAM's word for each vessel type (the `design` parameter's choices), to the request's. */
export const VESSEL_TYPE_OF_DESIGN: Record<string, VesselType> = { 'Stirred tank': 'stirred-tank', 'Bubble column': 'bubble-column' };

/** The vessel type a person chose in the panel (their override of `design`), or null for BioSTEAM's own. */
export function vesselTypeOf(overrides: Override[]): VesselType | null {
  const chosen = overrides.find((o) => o.key === 'design');
  return chosen && typeof chosen.value === 'string' ? VESSEL_TYPE_OF_DESIGN[chosen.value] ?? null : null;
}

/** The design request: the source, the vessel type the person chose, every override of the scope as typed (an input in the unit its spec names), and who asks. */
export function vesselRequest(
  source: { simulation?: string | null; fit?: string | null },
  overrides: Override[],
  specs: ParameterSpec[],
  by: string,
): VesselRequest {
  return {
    simulation: source.simulation ?? null,
    fit: source.fit ?? null,
    vesselType: vesselTypeOf(overrides),
    inputs: inputsOf(overrides, specs),
    by,
  };
}

/** Design the vessel (`POST /api/fermos/vessel`): one `fermos.vessel` artifact, or the service's refusal in its words. */
export const designVessel = (req: VesselRequest, signal?: AbortSignal) => post<VesselDesign>('/api/fermos/vessel', req, signal);

/** Whether a design request names a scale: one of plant scale and batch volume, as the service needs (said above Design). */
export function scaleOf(overrides: Override[]): 'none' | 'one' | 'both' {
  const n = overrides.filter((o) => (o.key === 'plant_scale' || o.key === 'batch_volume') && typeof o.value === 'number').length;
  return n === 0 ? 'none' : n === 1 ? 'one' : 'both';
}
