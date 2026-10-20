// fermOS → Forecast (OF-BLD-014 §7.4): pick a fit, set the conditions, see
// the band.
//
// A forecast is drawn from one kept fit's covariance by the service, under the
// fitted run's own starting values and length unless a person changes them;
// a changed value is that person's assumption, and the forecast becomes
// `demo`. The band leaves out run-to-run variation, and says so.
//
// Send to Proforma (OF-BLD-019 §5.1, D10): the fit in hand, or the forecast
// just made from it, goes to a Proforma scenario of the active program, or
// to a new one made in the New scenario chooser, whose page attaches it to
// the inputs it can feed (titre, yield, productivity); the service computes
// each value from the artifact there.
import { useState } from 'react';
import type { ForecastResult } from '@/data/types';
import { useStore, reviewerName, useProgramFilter } from '@/store';
import { navigate } from '@/router';
import { Button, Callout } from '@/components/ui';
import { NewScenarioDialog } from '@/components/NewScenarioDialog';
import { FIT_TOOL_WORDS, sendFitPath } from '@/lib/proforma';
import { EvidenceCard } from '@/components/EvidenceCard';
import { TrajectoryBand } from '@/components/figures';
import { fmt } from '@/engine/units';
import { FermosDown, FermosRefused, fermosForecast, fitFigureSeries, fitSeriesOf } from '@/lib/fermos';

/**
 * Send a kept fit or forecast to Proforma: a scenario the program switch
 * shows, or a new one; the scenario page attaches it to what it can feed.
 */
function SendToProforma({ artifactId, tool }: { artifactId: string; tool: string }) {
  const scenarios = useStore((s) => s.scenarios);
  const shows = useProgramFilter();
  const [open, setOpen] = useState(false);
  const [making, setMaking] = useState(false);
  const offered = scenarios.filter((sc) => sc.kind === 'biosteam' && shows('scenario', sc.id));
  return (
    <div className="card p-3" data-testid="send-to-proforma">
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => setOpen(!open)} aria-expanded={open}>
          Send to Proforma
        </Button>
        <span className="text-caption text-ink-soft">
          The {FIT_TOOL_WORDS[tool] ?? tool} <span className="font-num">{artifactId}</span> can give a scenario&rsquo;s titre, yield and
          batch time; the scenario&rsquo;s page says which it can feed and why not.
        </span>
      </div>
      {open && (
        <ul className="mt-2 space-y-1" data-testid="send-to-proforma-list">
          {offered.map((sc) => (
            <li key={sc.id}>
              <button className="text-body text-accent hover:underline" onClick={() => navigate(sendFitPath(sc.id, artifactId))}>
                {sc.name}
              </button>{' '}
              <span className="text-caption text-ink-soft font-num">{sc.flowsheetId ?? sc.modelId}</span>
            </li>
          ))}
          {offered.length === 0 && <li className="text-caption text-ink-soft">No Proforma scenario of the active program is in this browser yet.</li>}
          <li>
            <Button onClick={() => setMaking(true)}>New scenario…</Button>
          </li>
        </ul>
      )}
      <NewScenarioDialog open={making} onClose={() => setMaking(false)} attachFit={artifactId} />
    </div>
  );
}

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
      {result?.artifactId ? (
        <SendToProforma artifactId={result.artifactId} tool="growth_forecast" />
      ) : (
        fit?.kineticArtifactId && <SendToProforma artifactId={fit.kineticArtifactId} tool="kinetic_fit" />
      )}
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
