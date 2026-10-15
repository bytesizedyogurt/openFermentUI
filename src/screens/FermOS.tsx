// fermOS — the reactor (OF-BLD-011 §3, OF-BLD-014 Phase 7).
//
//     fermOS answers: what DOES a real vessel achieve over time?
//
// WHAT IT HOLDS NOW. Fits and forecasts computed from depositions, and nothing
// else. A deposition whose readings carry sample times becomes time series
// (§7.1); the service fits a growth rate and a kinetic model to them — logistic
// growth, Luedeking–Piret production, the substrate balance — and keeps each
// fit as an artifact with the deposition as its source (§7.2); a forecast is a
// band drawn from one fit's covariance (§7.3). Fits is the default view;
// Forecast is the second. Transport, operating mode, scale and control remain
// unbuilt, and the shelf below says so.
//
// AND IT IS NOT SEEDED FROM LITERATURE (§3, D6). Kinetic parameters are fitted
// to real runs in a specific vessel; mu_max copied out of a paper about a
// different strain in a different reactor is a number with no owner. No
// parameter from a paper enters fermOS: the screen sends only a deposition's
// own series, or the invented sample run, which is labelled, computed inline
// and kept nowhere. The service cannot see the browser's depositions, so it
// takes the readings as sent, and each fit's basis says so (§7.R). The only route from here to a
// kinetic model runs through Deposition.
//
// This screen may be extended. Keep this header's reasoning with it.
import { useEffect, useMemo, useState } from 'react';
import { FlaskConical } from 'lucide-react';
import type { FermosFitResponse, FermosSeries, FitParam } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { Button, Callout, EmptyState, PageHeader } from '@/components/ui';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import { OwnerTabs } from '@/components/OwnerTabs';
import { TrajectoryBand } from '@/components/figures';
import { FERMOS_TABS } from '@/data/tabs';
import { SAMPLE_DEPOSITION_ID, SAMPLE_NOTE, SAMPLE_SERIES } from '@/data/fermosSample';
import { stubsFor } from '@/data/subsystems';
import { fmt } from '@/engine/units';
import { FermosDown, FermosRefused, fermosFit, fitFigureSeries, fitSeriesOf, qualifies } from '@/lib/fermos';
import FermOSForecast from './FermOSForecast';

function ParamTable({ params }: { params: FitParam[] }) {
  return (
    <table className="w-full text-body" data-testid="fit-params">
      <thead>
        <tr className="text-caption text-ink-soft text-left">
          <th className="py-1 pr-2 font-medium">Parameter</th>
          <th className="py-1 pr-2 font-medium">Value</th>
          <th className="py-1 pr-2 font-medium">95 % interval</th>
          <th className="py-1 pr-2 font-medium">Unit</th>
          <th className="py-1 font-medium">What the run says</th>
        </tr>
      </thead>
      <tbody>
        {params.map((p) => (
          <tr key={p.name} className="border-t border-line/60">
            <td className="py-1 pr-2 font-num">{p.name}</td>
            <td className="py-1 pr-2 font-num">{fmt(p.value, 4)}</td>
            <td className="py-1 pr-2 font-num">
              {fmt(p.low, 4)} to {fmt(p.high, 4)}
            </td>
            <td className="py-1 pr-2 font-num text-caption">{p.unit}</td>
            <td className="py-1 text-caption">
              {p.identified === true && 'identified'}
              {p.identified === false && <span className="text-signal-warn">not identified: the interval reaches zero</span>}
              {p.indistinguishableFromZero === true && <span className="text-ink-soft">indistinguishable from zero on this run</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Fits() {
  const depositions = useStore((s) => s.depositions);
  const runbooks = useStore((s) => s.runbooks);
  const sampleLoaded = useStore((s) => s.fermosSampleLoaded);
  const setSample = useStore((s) => s.setFermosSample);
  const keepFit = useStore((s) => s.keepFermosFit);
  const route = useRoute();
  const qualifying = useMemo(
    () => depositions.filter((d) => qualifies(d, runbooks.find((r) => r.id === d.runbookId))),
    [depositions, runbooks],
  );
  const options = [...qualifying.map((d) => d.id), ...(sampleLoaded ? [SAMPLE_DEPOSITION_ID] : [])];
  const chosen = route.query.get('run') ?? options[0] ?? null;
  const [result, setResult] = useState<FermosFitResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const seriesFor = (id: string): FermosSeries[] => {
    if (id === SAMPLE_DEPOSITION_ID) return SAMPLE_SERIES;
    const d = depositions.find((x) => x.id === id);
    const rb = runbooks.find((r) => r.id === d?.runbookId);
    return d && rb ? fitSeriesOf(d, rb) : [];
  };

  useEffect(() => {
    if (!chosen) return;
    const ctrl = new AbortController();
    setBusy(true);
    setProblem(null);
    setResult(null);
    fermosFit(chosen, seriesFor(chosen), chosen === SAMPLE_DEPOSITION_ID, ctrl.signal)
      .then((r) => {
        setResult(r);
        keepFit(r);
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setProblem(e instanceof FermosDown ? `${e.message} ${e.remedy}` : e instanceof FermosRefused ? e.message : String(e));
      })
      .finally(() => !ctrl.signal.aborted && setBusy(false));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chosen, depositions]);

  const isSample = chosen === SAMPLE_DEPOSITION_ID;
  return (
    <div className="space-y-4" data-testid="fermos-fits">
      <div className="flex flex-wrap items-end gap-3">
        {options.length > 0 && (
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Run</span>
            <select
              className="input"
              aria-label="Run"
              value={chosen ?? ''}
              onChange={(e) => {
                navigate(`/fermos?run=${encodeURIComponent(e.target.value)}`, { replace: true });
              }}
            >
              {options.map((id) => (
                <option key={id} value={id}>
                  {id === SAMPLE_DEPOSITION_ID ? 'Sample run (invented)' : id}
                </option>
              ))}
            </select>
          </label>
        )}
        <Button onClick={() => setSample(!sampleLoaded)}>{sampleLoaded ? 'Unload the sample run' : 'Load a sample run'}</Button>
        {busy && <span className="text-caption text-ink-soft">Fitting…</span>}
      </div>

      {options.length === 0 && (
        <EmptyState
          icon={<FlaskConical size={28} />}
          title="No run to fit yet"
          body={
            <>
              fermOS fits what a run measured. Record a biomass reading at four or more times in a{' '}
              <a href={href('/runbooks/depositions')} className="text-accent hover:underline">
                deposition
              </a>
              , give each its hours into the run on the deposition's Time series panel, and mark the series as biomass; a
              product and a substrate series add the production and substrate terms. Or load the sample run to see what
              fermOS does with one.
            </>
          }
        />
      )}

      {isSample && <Callout kind="warn" title="Sample run">{SAMPLE_NOTE} Its fit is computed inline and kept nowhere.</Callout>}
      {problem && <Callout kind="warn">{problem}</Callout>}

      {result && chosen && (
        <>
          <TrajectoryBand
            title={`What did ${isSample ? 'the sample run' : chosen} do, and what curve fits it?`}
            series={fitFigureSeries(seriesFor(chosen), result.kinetic)}
            readingProvenance={isSample ? 'demo' : 'measured'}
            notes={result.notes}
            csvName={`fit-${chosen}`}
          />
          <section aria-label="Growth rate" className="text-body" data-testid="growth-fit">
            {result.growth?.mu ? (
              <p>
                Growth rate <span className="font-num">{fmt(result.growth.mu.value, 4)} h⁻¹</span> (95 % interval{' '}
                <span className="font-num">
                  {fmt(result.growth.mu.low, 4)} to {fmt(result.growth.mu.high, 4)}
                </span>
                ), doubling every <span className="font-num">{fmt(result.growth.doublingTimeH ?? 0, 3)} h</span>, read over{' '}
                <span className="font-num">
                  {fmt(result.growth.window[0])} to {fmt(result.growth.window[1])} h
                </span>{' '}
                (R² <span className="font-num">{fmt(result.growth.r2 ?? 0, 4)}</span>).
              </p>
            ) : (
              <p className="text-ink-soft">No growth rate: {result.growth?.reason}.</p>
            )}
          </section>
          {result.kinetic?.params.length ? (
            <ParamTable params={result.kinetic.params} />
          ) : (
            <p className="text-body text-ink-soft">No kinetic fit: {result.kinetic?.reason}.</p>
          )}
          <p className="text-caption text-ink-soft">
            {Math.round(result.confirmedShare * 100)} % of the readings were confirmed by a person.{' '}
            {result.kineticArtifactId && (
              <>
                Kept as{' '}
                <a className="font-num hover:text-accent" href={href(`/biorepo/artifacts/${result.kineticArtifactId}`)}>
                  {result.kineticArtifactId}
                </a>
                , computed from the deposition.
              </>
            )}
          </p>
        </>
      )}
    </div>
  );
}

export default function FermOS() {
  const route = useRoute();
  const onForecast = route.path.startsWith('/fermos/forecast');
  const stubs = stubsFor('fermOS');

  return (
    <>
      <PageHeader
        eyebrow="Reactor, kinetics, scale"
        title="fermOS"
        subtitle="The vessel. What a real reactor achieves over time: fitted to the runs deposited here and forecast from those fits. Transport, operating mode, scale-up and control are not built."
      />
      <OwnerTabs tabs={FERMOS_TABS} />

      {onForecast ? <FermOSForecast /> : <Fits />}

      <div className="mt-6 space-y-4">
        <Callout kind="warn" title="Kinetic parameters come from runs, not from papers">
          <p className="text-ink">
            mu_max, Xmax and the production and uptake coefficients are <em>fitted</em> to a real fermentation in a
            specific vessel. Lifting them from a paper about a different strain in a different reactor produces a number
            with no owner and no error bar, which is the failure mode this whole platform is built against. So fermOS is
            not seeded: every fit here comes from a{' '}
            <a href={href('/runbooks/depositions')} className="text-accent hover:underline">
              deposition
            </a>
            , or from the invented sample run, which says so.
          </p>
        </Callout>

        <Callout kind="info" title="Titre is fermOS's output — and the seam on either side">
          <p className="text-ink">
            Upstream,{' '}
            <a href={href('/geneos')} className="text-accent hover:underline">
              geneOS
            </a>{' '}
            is stoichiometry: a genome-scale model gives a yield ceiling with no time axis. fermOS
            is dynamics: the curve in a specific vessel. The gap between the ceiling and the titre
            actually achieved is exactly what reconciliation measures.
          </p>
          <p className="text-ink mt-2">
            Downstream, the seam to{' '}
            <a href={href('/pureos')} className="text-accent hover:underline">
              pureOS
            </a>{' '}
            is the harvest step, and it carries a decision made back in geneOS:{' '}
            <strong>secreted or intracellular</strong>. A secreted product starts at centrifuge
            and filter; an intracellular one starts at lysis and inherits every problem after it.
            The handoff has to carry product location, not just a titre.
          </p>
        </Callout>
      </div>

      <SubsystemShelf owner="fermOS" />

      <div className="mt-5">
        <ComponentTag component="fermOS" action={`kinetics live; ${stubs.length} subsystems named and not built`} />
      </div>
    </>
  );
}
