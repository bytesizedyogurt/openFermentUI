// The browser's side of fermOS (OF-BLD-014 §7.4).
//
// A deposition's series go to the service, which fits them and keeps the fit
// as an artifact; a forecast is asked of a kept fit, or of the sample run's
// fit inline. The fitted curve drawn through the points is the closed form
// the service fitted, evaluated here on its parameters; it computes nothing
// the fit did not already hold. Shares lib/rag.ts's call and its failures.
import type { Deposition, FermosFitResponse, FermosSeries, ForecastResult, KineticFit, Override, Runbook, SimulationSummary, StartValues, VesselDesign, VesselRequest } from '@/data/types';
import { seriesOf } from '@/engine/series';
import type { TrajectorySeries } from '@/components/figures';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as FermosDown, RagRefused as FermosRefused };

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

export const fermosFit = (depositionId: string, series: FermosSeries[], sample = false, signal?: AbortSignal) =>
  post<FermosFitResponse>('/api/fermos/fit', { depositionId, series, sample }, signal);

export const fermosForecast = (
  req: { fitArtifactId?: string | null; fit?: KineticFit | null; start?: Partial<StartValues>; changedBy?: string | null; durationH?: number | null; sample?: boolean },
  signal?: AbortSignal,
) =>
  post<ForecastResult>(
    '/api/fermos/forecast',
    {
      fitArtifactId: req.fitArtifactId ?? null,
      fit: req.fit ?? null,
      start: { X0: req.start?.X0 ?? null, P0: req.start?.P0 ?? null, S0: req.start?.S0 ?? null },
      changedBy: req.changedBy ?? null,
      durationH: req.durationH ?? null,
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

const value = (fit: KineticFit, name: string) => fit.params.find((p) => p.name === name)?.value;

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
  const tmax = Math.max(1e-9, ...series.flatMap((s) => s.points.map((p) => p.t)));
  return series
    .filter((s) => s.role)
    .map((s) => {
      const q = fit?.quality.find((x) => x.measureId === s.measureId);
      return {
        role: s.role!,
        label: s.label,
        unit: s.unit,
        readings: s.points.map((p, i) => ({ t: p.t, value: p.value, residual: q?.residuals[i] ?? null })),
        fitted: fit && fit.params.length ? curve(fit, s.role!, tmax) : undefined,
      };
    });
}


// ── fermOS → Vessel (OF-BLD-020 §4.2, D7) ──────────────────────────────
//
// The vessel a kept simulation (or, anaerobic, a kept fit) needs, designed by
// BioSTEAM in the service's Proforma worker. The browser asks and shows: the
// scope's parameters come from `GET /api/params/fermos:vessel:<id>` through
// the panel, a person's changes are the scope's overrides (Durable), and
// `POST /api/fermos/vessel` designs. Nothing here computes a value.

/** The kept simulations, newest first (`GET /api/fermos/simulations`); an archived program's left out unless the switch shows it. */
export const fermosSimulations = (includeArchived: boolean, signal?: AbortSignal) =>
  call<SimulationSummary[]>(`/api/fermos/simulations${includeArchived ? '?includeArchived=true' : ''}`, { signal });

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

/** The design request: the source, the vessel type the person chose, and every override of the scope as typed. */
export function vesselRequest(source: { simulation?: string | null; fit?: string | null }, overrides: Override[], includeArchived: boolean): VesselRequest {
  return {
    simulation: source.simulation ?? null,
    fit: source.fit ?? null,
    vesselType: vesselTypeOf(overrides),
    overrides,
    includeArchived,
  };
}

/** Design the vessel (`POST /api/fermos/vessel`): one `fermos.vessel` artifact, or the service's refusal in its words. */
export const designVessel = (req: VesselRequest, signal?: AbortSignal) => post<VesselDesign>('/api/fermos/vessel', req, signal);

/** Whether a design request names a scale: one of plant scale and batch volume, as the service needs (said above Design). */
export function scaleOf(overrides: Override[]): 'none' | 'one' | 'both' {
  const n = overrides.filter((o) => (o.key === 'plant_scale' || o.key === 'batch_volume') && typeof o.value === 'number').length;
  return n === 0 ? 'none' : n === 1 ? 'one' : 'both';
}
