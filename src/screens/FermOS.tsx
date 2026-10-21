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
// Forecast is the last. OF-BLD-020 §4.2 adds Vessel (FermOSVessel.tsx): the
// vessel BioSTEAM sizes for a kept simulation, with the oxygen balance, so
// transport and scale are live; operating mode and control remain unbuilt,
// and the shelf below says so.
//
// AND IT IS NOT SEEDED FROM LITERATURE (§3, D6). Kinetic parameters are fitted
// to real runs in a specific vessel; mu_max copied out of a paper about a
// different strain in a different reactor is a number with no owner. No
// parameter from a paper enters fermOS: the screen sends only a deposition's
// own series. With no deposition to fit, the screen names the readings to
// deposit and where (OF-BLD-016 §3.2: the invented sample run left the
// screen; demo.py still writes it for the service double). The service cannot see the browser's depositions, so it
// takes the readings as sent, and each fit's basis says so (§7.R). The only route from here to a
// kinetic model runs through Deposition.
//
// PROPERTIES OF A BROTH (OF-BLD-019 §4.2, D9). Below the fits, a person picks
// an ethanol titre record of the active program, and thermosteam (BioSTEAM's
// property engine, in the Proforma worker) gives the density, heat capacity
// and boiling point of water and ethanol at that titre (the preset
// `beer-at-titre-of`). A titre is a measured value, not a kinetic parameter:
// it enters no fit and no forecast, and the card names the record it read, the
// library's version and the artifact the answer is kept as. With no titre
// record on file the card says what would fill it.
//
// This screen may be extended. Keep this header's reasoning with it.
import { useEffect, useMemo, useState } from 'react';
import { FlaskConical } from 'lucide-react';
import type { FermosFitResponse, FermosSeries, FitParam } from '@/data/types';
import { useProgramFilter, useStore } from '@/store';
import { ArchivedBanner } from '@/components/ArchivedBanner';
import { href, navigate, useRoute } from '@/router';
import { Callout, EmptyState, PageHeader, SectionTitle } from '@/components/ui';
import { PropertiesPanel } from '@/components/PropertiesPanel';
import { BEER, TITRE_FIELD } from '@/lib/thermo';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import { OwnerTabs } from '@/components/OwnerTabs';
import { TrajectoryBand } from '@/components/figures';
import { FERMOS_TABS } from '@/data/tabs';
import { stubsFor } from '@/data/subsystems';
import { fmt } from '@/engine/units';
import { FermosDown, FermosRefused, fermosFit, fitFigureSeries, fitSeriesOf, qualifies } from '@/lib/fermos';
import FermOSForecast from './FermOSForecast';
import FermOSVessel from './FermOSVessel';

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
  const keepFit = useStore((s) => s.keepFermosFit);
  const route = useRoute();
  // The runs Runbooks → Depositions shows (OF-BLD-016 §2): a deposition of an
  // archived program's runbook or protocol waits for the program switch.
  const shows = useProgramFilter();
  const qualifying = useMemo(
    () =>
      depositions.filter(
        (d) => shows('deposition', d.id) && qualifies(d, runbooks.find((r) => r.id === d.runbookId)),
      ),
    [depositions, runbooks, shows],
  );
  const options = qualifying.map((d) => d.id);
  const chosen = route.query.get('run') ?? options[0] ?? null;
  const [result, setResult] = useState<FermosFitResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const seriesFor = (id: string): FermosSeries[] => {
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
    fermosFit(chosen, seriesFor(chosen), false, ctrl.signal)
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
                  {id}
                </option>
              ))}
            </select>
          </label>
        )}
        {busy && <span className="text-caption text-ink-soft">Fitting…</span>}
      </div>
      {chosen && !options.includes(chosen) && <ArchivedBanner kind="deposition" id={chosen} />}

      {options.length === 0 && (
        <div data-testid="fermos-empty">
          <EmptyState
            icon={<FlaskConical size={28} />}
            title="No run deposited yet"
            body={
              <>
                fermOS fits what a run measured, and nothing else. Deposit a run in{' '}
                <a href={href('/runbooks/depositions')} className="text-accent hover:underline">
                  Runbooks → Depositions
                </a>{' '}
                with these readings: the time of each sample, in hours into the run; a biomass reading at four or more of
                those times; and, for the production and uptake terms, a product reading and a substrate reading at the
                same times. On the deposition&rsquo;s Time series panel, give each reading its hours and mark each series as
                biomass, product or substrate. The run then appears here to fit.
              </>
            }
          />
        </div>
      )}

      {problem && <Callout kind="warn">{problem}</Callout>}

      {result && chosen && (
        <>
          <TrajectoryBand
            title={`What did ${chosen} do, and what curve fits it?`}
            series={fitFigureSeries(seriesFor(chosen), result.kinetic)}
            readingProvenance="measured"
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

function BrothProperties() {
  const records = useStore((s) => s.records);
  const shows = useProgramFilter();
  const titres = useMemo(
    () =>
      records.filter(
        (r) => r.field === TITRE_FIELD && typeof r.value === 'number' && r.status !== 'rejected' && shows('record', r.id),
      ),
    [records, shows],
  );
  const [picked, setPicked] = useState('');
  const chosen = titres.find((r) => r.id === picked) ?? null;
  return (
    <section className="mt-6" aria-labelledby="broth-properties-title" data-testid="broth-properties">
      <SectionTitle
        right={
          titres.length > 0 && (
            <label className="text-caption text-ink-soft flex items-center gap-1.5">
              Titre record
              <select className="input" aria-label="Titre record" value={picked} onChange={(e) => setPicked(e.target.value)}>
                <option value="">pick one</option>
                {titres.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id} · {fmt(r.value as number)} {r.unit} · {r.paperId}
                  </option>
                ))}
              </select>
            </label>
          )
        }
      >
        <span id="broth-properties-title">Properties of a broth</span>
      </SectionTitle>
      <p className="text-caption text-ink-soft mb-2">
        Density, heat capacity, viscosity, and bubble and dew points of water and ethanol at a titre a paper measured, as
        thermosteam (BioSTEAM&rsquo;s property engine) computes them. The page names the record; the service reads its value,
        and nothing is typed. The beer&rsquo;s cells, residual sugar and dissolved carbon dioxide are not in the mixture.
      </p>
      {titres.length === 0 ? (
        <p className="text-body text-ink-soft" data-testid="broth-properties-empty">
          No ethanol titre record of an active program is on file yet. A titre extracted from a thread Q paper in{' '}
          <a href={href('/intake')} className="text-accent hover:underline">
            Intake
          </a>
          , anchored to its sentence, fills this: pick it here and thermosteam computes the density, heat capacity and
          boiling point of water and ethanol at that titre.
        </p>
      ) : chosen ? (
        <PropertiesPanel
          key={chosen.id}
          title={
            <>
              Water and ethanol at the titre of <span className="font-num">{chosen.id}</span>
            </>
          }
          question={{ preset: BEER, recordId: chosen.id }}
        />
      ) : (
        <p className="text-body text-ink-soft">Pick a titre record above to ask what thermosteam says of that beer.</p>
      )}
    </section>
  );
}

export default function FermOS() {
  const route = useRoute();
  const onForecast = route.path.startsWith('/fermos/forecast');
  // OF-BLD-020 §4.2 — 'vessel' is a second segment of its own: the vessel
  // BioSTEAM designs for a kept simulation.
  const onVessel = route.path.startsWith('/fermos/vessel');
  const stubs = stubsFor('fermOS');

  return (
    <>
      <PageHeader
        eyebrow="Reactor, kinetics, scale"
        title="fermOS"
        subtitle="The vessel. What a real reactor achieves over time: fitted to the runs deposited here and forecast from those fits, and the vessel BioSTEAM sizes for a kept simulation, with its oxygen balance. Operating mode and control are not built."
      />
      <OwnerTabs tabs={FERMOS_TABS} />

      {onVessel ? <FermOSVessel /> : onForecast ? <FermOSForecast /> : <Fits />}

      <BrothProperties />

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
            .
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
        <ComponentTag component="fermOS" action={`kinetics, transport and scale live; ${stubs.length} subsystems named and not built`} />
      </div>
    </>
  );
}
