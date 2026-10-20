// fermOS → Forecast (OF-BLD-014 §7.4): pick a fit, set the conditions, see
// the band.
//
// A forecast is drawn from one kept fit's covariance by the service, under the
// fitted run's own starting values and length unless a person changes them;
// a changed value is that person's assumption, and the forecast becomes
// `demo`. The band leaves out run-to-run variation, and says so.
import { useState } from 'react';
import type { ForecastResult } from '@/data/types';
import { useStore, reviewerName } from '@/store';
import { Button, Callout } from '@/components/ui';
import { EvidenceCard } from '@/components/EvidenceCard';
import { TrajectoryBand } from '@/components/figures';
import { fmt } from '@/engine/units';
import { FermosDown, FermosRefused, fermosForecast, fitFigureSeries, fitSeriesOf } from '@/lib/fermos';

export default function FermOSForecast() {
  const fits = useStore((s) => s.fermosFits);
  const depositions = useStore((s) => s.depositions);
  const runbooks = useStore((s) => s.runbooks);
  const usable = Object.values(fits).filter((f) => f.kinetic?.params.length);
  const [chosen, setChosen] = useState<string>(usable[0]?.depositionId ?? '');
  const [start, setStart] = useState<{ X0: string; P0: string; S0: string }>({ X0: '', P0: '', S0: '' });
  const [duration, setDuration] = useState('');
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fit = fits[chosen];

  const seriesFor = (id: string) => {
    const d = depositions.find((x) => x.id === id);
    const rb = runbooks.find((r) => r.id === d?.runbookId);
    return d && rb ? fitSeriesOf(d, rb) : [];
  };

  const run = () => {
    if (!fit) return;
    const num = (v: string) => (v.trim() === '' ? null : Number(v));
    const changed = Object.values(start).some((v) => v.trim() !== '');
    setBusy(true);
    setProblem(null);
    fermosForecast({
      fitArtifactId: fit.kineticArtifactId,
      fit: null,
      start: { X0: num(start.X0), P0: num(start.P0), S0: num(start.S0) },
      changedBy: changed ? reviewerName() : null,
      durationH: num(duration),
      sample: false,
    })
      .then(setResult)
      .catch((e: unknown) => {
        setResult(null);
        setProblem(e instanceof FermosDown ? `${e.message} ${e.remedy}` : e instanceof FermosRefused ? e.message : String(e));
      })
      .finally(() => setBusy(false));
  };

  if (usable.length === 0) {
    return (
      <Callout kind="info" title="No fit to forecast from yet">
        A forecast is drawn from a fit of a deposited run. Deposit a run with timed biomass, product and substrate readings in
        Runbooks → Depositions, open Fits, choose it, and come back.
      </Callout>
    );
  }

  return (
    <div className="space-y-4" data-testid="fermos-forecast">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Fit</span>
          <select className="input" aria-label="Fit" value={chosen} onChange={(e) => { setChosen(e.target.value); setResult(null); }}>
            {usable.map((f) => (
              <option key={f.depositionId} value={f.depositionId}>
                {f.depositionId}
              </option>
            ))}
          </select>
        </label>
        {(['X0', 'P0', 'S0'] as const).map((k) => (
          <label key={k} className="text-caption text-ink-soft">
            <span className="block mb-0.5">{k}, blank for the run's own</span>
            <input className="input w-24 font-num" type="number" step="any" aria-label={`Starting ${k}`} value={start[k]} onChange={(e) => setStart({ ...start, [k]: e.target.value })} />
          </label>
        ))}
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Hours, blank for the run's own</span>
          <input className="input w-24 font-num" type="number" step="any" aria-label="Duration in hours" value={duration} onChange={(e) => setDuration(e.target.value)} />
        </label>
        <Button variant="primary" onClick={run} disabled={busy || !fit}>
          {busy ? 'Forecasting…' : 'Forecast'}
        </Button>
      </div>
      {Object.values(start).some((v) => v.trim()) && (
        <p className="text-caption text-ink-soft">
          A changed starting value is an assumption in the name of {reviewerName() ?? 'the reviewer set in Settings'}; the forecast it
          makes is marked modeled.
        </p>
      )}
      {problem && <Callout kind="warn">{problem}</Callout>}
      {result && fit && (
        <>
          <TrajectoryBand
            title={`What would a run like ${chosen} do?`}
            series={fitFigureSeries(seriesFor(chosen), fit.kinetic)}
            forecast={{ times: result.times, bands: result.bands, provenance: result.evidence?.provenance }}
            readingProvenance="measured"
            notes={result.notes}
            basis={result.evidence ? [result.evidence.basis] : undefined}
            csvName={`forecast-${chosen}`}
          />
          <ul className="text-body space-y-0.5" data-testid="forecast-finals">
            {result.finals.map((f) => (
              <li key={f.role}>
                Final {f.role}: <span className="font-num">{fmt(f.median, 4)}</span> {f.unit}, 90 % of readings between{' '}
                <span className="font-num">
                  {fmt(f.low, 4)} and {fmt(f.high, 4)}
                </span>
              </li>
            ))}
            {result.yieldInterval && (
              <li>
                Yield: <span className="font-num">{fmt(result.yieldInterval.median, 4)}</span> {result.yieldInterval.unit} (
                <span className="font-num">
                  {fmt(result.yieldInterval.low, 4)} to {fmt(result.yieldInterval.high, 4)}
                </span>
                )
              </li>
            )}
            {result.substrateRunsOutH !== null && (
              <li className="text-signal-warn">The sugar runs out at about {fmt(result.substrateRunsOutH, 3)} h, and the forecast ends there.</li>
            )}
          </ul>
          {result.evidence && <EvidenceCard evidence={result.evidence} />}
        </>
      )}
    </div>
  );
}
