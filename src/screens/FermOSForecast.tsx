// fermOS → Forecast (OF-BLD-014 §7.4, OF-BLD-020 §3.3): pick a fit, set the
// conditions in the parameter panel, see the run.
//
// A forecast is drawn from one kept fit's covariance by the service, under the
// fitted run's own starting values and length unless a person changes them;
// a changed value is that person's assumption, and the forecast becomes
// `assumed`. The band leaves out run-to-run variation, and says so.
//
// THE CONDITIONS ARE THE PANEL'S (OF-BLD-020 §3.3, E.1‴). A logistic_v0 fit's
// start values and length are the scope `fermos:forecast:<fit id>`, served
// by the service bound to the fitted run's own, in the run's own units; a
// person's value there is an override under their reviewer name, sent as the
// forecast's start values and length. A batch_v1 fit is simulated from, not
// forecast from a covariance: its start values and run length are its
// family's scope (`fermos:family:batch_v1`, groups Start values and Run
// length), started from the fit and as long as its run, and the service
// keeps the run as a `fermos.simulation`, drawn as computed curves with the
// run's own readings as filled points. Either way this screen renders no
// number box of its own: every value comes from the service or the person.
//
// OF-BLD-020 §3.R (findings 4, 7, 11, 15): the service binds what the fit
// held (Pmax off among them), so a batch fit's simulation is the model that
// was fitted and nothing waits for a Pmax; this screen sends only the
// overrides of the keys its panel shows, so a value typed on Simulate for the
// family's other parameters never runs here unseen; Simulate from this fit is
// held while anything waits, and the keys are named; a forecast's length a
// person typed goes with that person's name (`durationBy`).
//
// Send to Proforma (OF-BLD-019 §5.1, D10): the fit in hand, the forecast
// just made from it, or the simulation, goes to a Proforma scenario, or to a
// new one made in the New scenario chooser, whose
// page attaches it to the inputs it can feed (titre, yield, productivity);
// the service computes each value from the artifact there.
import { useEffect, useMemo, useState } from 'react';
import type { ForecastResult, ParamScope, SimulationResult } from '@/data/types';
import { overridesFor, useStore } from '@/store';
import { href, navigate } from '@/router';
import { Button, Callout } from '@/components/ui';
import { NewScenarioDialog } from '@/components/NewScenarioDialog';
import { ParameterPanel } from '@/components/ParameterPanel';
import { FIT_TOOL_WORDS, sendFitPath } from '@/lib/proforma';
import { paramScope } from '@/lib/params';
import { EvidenceCard } from '@/components/EvidenceCard';
import { TimeCourse, TrajectoryBand } from '@/components/figures';
import { fmt, normalizeUnit } from '@/engine/units';
import {
  FIT_LENGTH,
  FermosDown,
  FermosRefused,
  LOGISTIC,
  STATE_WORDS,
  familyScope,
  fermosForecast,
  fermosSimulate,
  fitFigureSeries,
  fitSeriesOf,
  forecastAsk,
  forecastScope,
  paramAskOf,
  simulateFromFitPath,
  timeCourseOf,
  type SimulateAsk,
} from '@/lib/fermos';

/** The groups a batch fit's forecast shows of its family's scope. */
const FORECAST_GROUPS = ['Start values', 'Run length'];
/** The state a deposition's series of each role is read against. */
const STATE_OF_ROLE: Record<string, string> = { biomass: 'X', substrate: 'S', product: 'P' };

const problemOf = (e: unknown) =>
  e instanceof FermosDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof FermosRefused ? e.message : String(e);

/**
 * Send a kept fit, forecast or simulation to Proforma: a BioSTEAM scenario
 * on file, or a new one; the scenario page attaches it to what it can feed.
 */
export function SendToProforma({ artifactId, tool }: { artifactId: string; tool: string }) {
  const scenarios = useStore((s) => s.scenarios);
  const [open, setOpen] = useState(false);
  const [making, setMaking] = useState(false);
  const offered = scenarios.filter((sc) => sc.kind === 'biosteam');
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
              <button
                className="text-body text-accent hover:underline"
                onClick={() => navigate(sendFitPath(sc.id, artifactId))}
                data-testid="send-to-proforma-scenario"
                data-to={sendFitPath(sc.id, artifactId)}
              >
                {sc.name}
              </button>{' '}
              <span className="text-caption text-ink-soft font-num">{sc.flowsheetId ?? sc.modelId}</span>
            </li>
          ))}
          {offered.length === 0 && <li className="text-caption text-ink-soft">No Proforma scenario is in this project yet.</li>}
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
  const usable = Object.entries(fits).filter(([, f]) => f.kinetic?.params.length);
  const [chosen, setChosen] = useState<string>(usable[0]?.[0] ?? '');
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [sim, setSim] = useState<SimulationResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scopeData, setScopeData] = useState<ParamScope | null>(null);
  const [scopeProblem, setScopeProblem] = useState<string | null>(null);
  // What waits among the family's parameters this panel does not show (a batch fit's simulation).
  const [elsewhere, setElsewhere] = useState<string[]>([]);
  const fit = fits[chosen];
  const model = fit?.kinetic?.model ?? LOGISTIC;
  const fitId = fit?.kineticArtifactId ?? null;
  const batchAsk: SimulateAsk | null =
    fitId && model !== LOGISTIC
      ? { family: model, strain: null, product: null, sugar: null, fitArtifact: fitId, startFrom: 'fit', durationPreset: FIT_LENGTH }
      : null;
  const scope = !fitId ? '' : model === LOGISTIC ? forecastScope(fitId) : familyScope(model);
  const scoped = useStore(overridesFor(scope));
  // A batch fit's simulation sends only the overrides of the keys its panel shows.
  const shownKeys = new Set((scopeData?.specs ?? []).map((s) => s.key));
  const overrides = batchAsk ? scoped.filter((o) => shownKeys.has(o.key)) : scoped;
  const waitingShown = batchAsk ? (scopeData?.waiting ?? []).filter((k) => !overrides.some((o) => o.key === k)) : [];
  const held = batchAsk !== null && (elsewhere.length > 0 || waitingShown.length > 0);
  const askKey = JSON.stringify(batchAsk);

  const seriesFor = (id: string) => {
    const d = depositions.find((x) => x.id === id);
    const rb = runbooks.find((r) => r.id === d?.runbookId);
    return d && rb ? fitSeriesOf(d, rb) : [];
  };

  // The conditions' scope: the forecast's own, or the batch family's from the fit.
  useEffect(() => {
    setScopeData(null);
    setScopeProblem(null);
    setElsewhere([]);
    setResult(null);
    setSim(null);
    if (!scope) return;
    const ctrl = new AbortController();
    paramScope(scope, batchAsk ? paramAskOf(batchAsk) : {}, ctrl.signal)
      .then((d) => {
        if (!batchAsk) return setScopeData(d);
        // A batch fit's forecast shows its family's start values and run length alone.
        const keys = new Set(d.specs.filter((s) => FORECAST_GROUPS.includes(s.group)).map((s) => s.key));
        setElsewhere(d.waiting.filter((k) => !keys.has(k)));
        setScopeData({ ...d, specs: d.specs.filter((s) => keys.has(s.key)), values: d.values.filter((v) => keys.has(v.key)), waiting: d.waiting.filter((k) => keys.has(k)) });
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setScopeProblem(problemOf(e)));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, askKey]);

  const run = () => {
    if (!fit) return;
    setBusy(true);
    setProblem(null);
    if (batchAsk) {
      fermosSimulate(batchAsk, overrides)
        .then((r) => {
          setSim(r);
          setResult(null);
        })
        .catch((e: unknown) => {
          setSim(null);
          setProblem(problemOf(e));
        })
        .finally(() => setBusy(false));
      return;
    }
    const a = forecastAsk(overrides);
    fermosForecast({ fitArtifactId: fitId, fit: null, start: a.start, changedBy: a.changedBy, durationH: a.durationH, durationBy: a.durationBy, sample: false })
      .then((r) => {
        setResult(r);
        setSim(null);
      })
      .catch((e: unknown) => {
        setResult(null);
        setProblem(problemOf(e));
      })
      .finally(() => setBusy(false));
  };

  // A deposition's readings against a simulation: filled points, where the
  // series' unit is the state's own.
  const readings = useMemo(() => {
    if (!sim || !fit) return [];
    return seriesFor(fit.depositionId)
      .filter((s) => s.role && STATE_OF_ROLE[s.role] && normalizeUnit(s.unit) !== null && normalizeUnit(s.unit) === normalizeUnit(sim.units[STATE_OF_ROLE[s.role]] ?? ''))
      .map((s) => ({ key: STATE_OF_ROLE[s.role!], points: s.points.map((p) => ({ t: p.t, value: p.value })), provenance: 'measured' as const }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sim, fit, depositions, runbooks]);

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
          <select
            className="input"
            aria-label="Fit"
            value={chosen}
            onChange={(e) => {
              setChosen(e.target.value);
              setResult(null);
              setSim(null);
            }}
          >
            {usable.map(([key, f]) => (
              <option key={key} value={key}>
                {f.depositionId} · {f.kinetic?.model ?? LOGISTIC}
              </option>
            ))}
          </select>
        </label>
        <Button variant="primary" onClick={run} disabled={busy || !fit || held} data-testid="forecast-run">
          {busy ? (batchAsk ? 'Simulating…' : 'Forecasting…') : batchAsk ? 'Simulate from this fit' : 'Forecast'}
        </Button>
      </div>
      {batchAsk ? (
        <p className="text-caption text-ink-soft">
          A {model} fit is simulated from, not drawn from its covariance: the curves are its central values and what it held as
          conventions, under the start values and run length below; its parameters&rsquo; intervals are in the fit&rsquo;s table.
          The start values and run length are the family&rsquo;s, started from the fit and as long as its run; a value typed for
          its other parameters on{' '}
          <a className="text-accent hover:underline" href={href(simulateFromFitPath(model, fitId!))}>
            fermOS → Simulate
          </a>{' '}
          is not sent from here.
        </p>
      ) : (
        <p className="text-caption text-ink-soft">
          The forecast starts from the fitted run&rsquo;s own values and runs its own length unless you name others below. A changed
          starting value is an assumption in your reviewer name; the forecast it makes is marked modeled.
        </p>
      )}
      {scope && (
        <section aria-label="Conditions" className="card p-3" data-testid="forecast-panel">
          {scopeProblem && <Callout kind="warn">{scopeProblem}</Callout>}
          <ParameterPanel scope={scope} data={scopeData} request={batchAsk ? paramAskOf(batchAsk) : undefined} groups={FORECAST_GROUPS} />
        </section>
      )}
      {!fitId && <p className="text-caption text-ink-soft">This fit is not kept as an artifact, so its conditions cannot be changed here.</p>}
      {held && fitId && (
        <p className="text-caption text-signal-warn" data-testid="forecast-waiting">
          Simulate from this fit waits for {[...waitingShown, ...elsewhere].join(', ')}:{' '}
          {waitingShown.length > 0 && 'type what waits below'}
          {waitingShown.length > 0 && elsewhere.length > 0 && ', and '}
          {elsewhere.length > 0 && (
            <a className="text-accent hover:underline" href={href(simulateFromFitPath(model, fitId))}>
              give the rest a source on fermOS → Simulate
            </a>
          )}
          .
        </p>
      )}
      {problem && <Callout kind="warn">{problem}</Callout>}
      {problem && batchAsk && fitId && (
        <p className="text-caption">
          <a className="text-accent hover:underline" href={href(simulateFromFitPath(model, fitId))}>
            Open this fit in fermOS → Simulate
          </a>{' '}
          to give what waits a source.
        </p>
      )}
      {sim ? (
        <SendToProforma artifactId={sim.artifactId} tool="fermos.simulation" />
      ) : result?.artifactId ? (
        <SendToProforma artifactId={result.artifactId} tool="growth_forecast" />
      ) : (
        fitId && model === LOGISTIC && <SendToProforma artifactId={fitId} tool="kinetic_fit" />
      )}
      {sim && fit && (
        <>
          <TimeCourse
            title={`What would a run like ${fit.depositionId} do, simulated from its ${model} fit?`}
            {...timeCourseOf(sim)}
            readings={readings}
            csvName={`simulation-${sim.artifactId}`}
          />
          <p className="text-caption text-ink-soft">
            {Object.keys(sim.series)
              .filter((k) => k !== 't')
              .map((k) => STATE_WORDS[k] ?? k)
              .join(', ')}{' '}
            are computed curves, kept as{' '}
            <a className="font-num hover:text-accent" href={href(`/biorepo/artifacts/${sim.artifactId}`)}>
              {sim.artifactId}
            </a>
            ; the run&rsquo;s readings are the filled points.
          </p>
        </>
      )}
      {result && fit && (
        <>
          <TrajectoryBand
            title={`What would a run like ${fit.depositionId} do?`}
            series={fitFigureSeries(seriesFor(fit.depositionId), fit.kinetic)}
            forecast={{ times: result.times, bands: result.bands, provenance: result.evidence?.provenance }}
            readingProvenance="measured"
            notes={result.notes}
            basis={result.evidence ? [result.evidence.basis] : undefined}
            csvName={`forecast-${fit.depositionId}`}
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
