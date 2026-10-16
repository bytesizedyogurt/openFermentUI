// The browser's side of fermOS (OF-BLD-014 §7.4).
//
// A deposition's series go to the service, which fits them and keeps the fit
// as an artifact; a forecast is asked of a kept fit, or of the sample run's
// fit inline. The fitted curve drawn through the points is the closed form
// the service fitted, evaluated here on its parameters; it computes nothing
// the fit did not already hold. Shares lib/rag.ts's call and its failures.
import type { Deposition, FermosFitResponse, FermosSeries, ForecastResult, KineticFit, Runbook, StartValues } from '@/data/types';
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

