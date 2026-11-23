// A reference plant's page (alpha 2.2 D8; OF-BLD-019 §3.3): /proforma/reference/:plant.
//
// One page for each plant of the library shelf a reference run reads: the
// corn stover plant (the NREL 2011 design, the benchmark) and the dry-grind
// corn plant, each run whole by BioSTEAM on its package's own values through
// the library's door, and any other plant of the shelf by its id (called a
// plant of the library shelf, and held to a package test only when its
// entry names one). It reads, and never types:
//
//   GET  /api/library                     the plant's entry: its title, its module,
//                                         its package test, its default
//                                         configuration, the changes it needs to
//                                         build here
//   GET  /api/runs?engine=biosteam        the project's runs: the plant's newest
//                                         run on its package's own values, in the
//                                         configuration a run of it takes when it
//                                         names none
//   GET  /api/runs/{id}                   that run's report: its artifact, its SFF
//                                         record, its parameters
//   GET  /api/biorepo/artifacts?tool=     the runs a person kept from the shelf's
//                                         retired reference entry for this plant
//                                         (alpha 2.2 D8), each listed with its
//                                         checks and a link to BioRepo's page
//   GET  /api/library/{plant}/regression  the package test's values, before a run
//   POST /api/library/{plant}/run         Run or Rerun, in the person's name (a
//                                         basis already run answers from its row)
//
// The header names the plant's package and version, the provenance as the
// run's artifact computes it, and the package test the run is held to. The
// price is the one the run's TEA solves at the package's rate of return.
// Below it, "Held to its package's own test" sets each value of the
// package's test beside what this run measured, the relative difference and
// whether it is within the package's tolerance, every number from the
// artifact's `checks` (or, before a run, the service's `regression`), none
// typed here (the table is lib/proforma's `regressionTable`, the run's page
// shows the same). Then the sections the run's page shows, over the library
// run read as one case (`runViewOfRun`): the result, the cost breakdown, the
// streams, the equipment, the utilities and what the package set, read back;
// the plant's drawing is its SFF file's graph, on the run's page. A change
// this installation makes so the package builds at all (the plant's
// `compat`) is said in words.
import { useEffect, useState } from 'react';
import { BookOpen, Play } from 'lucide-react';
import type { PackageRegression, RegressionCheck } from '@/lib/proforma';
import type { Artifact, EngineRun, RunReport as EngineRunReport } from '@/lib/studies';
import { href } from '@/router';
import { useStore } from '@/store';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { runnable, type LibraryPlant, type LibraryShelf } from '@/lib/library';
import { PageHeader, Card, Button, Callout, LinkButton, cx } from '@/components/ui';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import {
  ProformaDown,
  REFERENCE_PLANTS,
  SIMULATOR_SAYS,
  type SimulatorStatus,
  keptReferenceRuns,
  keptRunsOf,
  libraryPrice,
  libraryRegression,
  packageChecks,
  proformaStatus,
  referenceRunOf,
  regressionRows,
  regressionTable,
  retiredEntryOf,
  runViewOfRun,
  stamp,
} from '@/lib/proforma';
import { StudiesRefused, libraryShelf, listRuns, runPlant, runReport } from '@/lib/studies';
import { RunReport } from '@/screens/ProformaBiosteam';

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

// ── Held to its package's own test ──────────────────────────────────────

function RegressionCard({
  regression,
  checks,
  ran,
  packageTest,
  plant,
}: {
  regression: PackageRegression | null;
  checks: RegressionCheck[];
  ran: boolean;
  packageTest: string | null;
  plant: string;
}) {
  const rows = regressionRows(regression, checks, ran);
  const t = regressionTable(rows);
  const within = rows.filter((r) => r.within === true).length;
  return (
    <Card className="p-4" data-testid="regression-table">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Held to its package&rsquo;s own test</h2>
        {rows.length > 0 && (
          <button className="chip" data-testid="csv-regression" onClick={() => exportCSV(`${plant}-package-test.csv`, t.headers, t.rows)}>
            CSV
          </button>
        )}
      </div>
      <p className="text-caption text-ink-soft mb-2">
        {regression ? (
          <>
            Each value <span className="font-num">{regression.file}::{regression.test}</span> asserts in{' '}
            <span className="font-num">{regression.package}</span>, read by the service from the test file installed with the package, beside what
            this run measured for the same expression. The service holds each as numpy&rsquo;s allclose holds the package&rsquo;s own test: the
            relative difference within the test&rsquo;s tolerance.
          </>
        ) : (
          <>
            The service read no package test for this plant
            {packageTest ? (
              <>
                {' '}
                (<span className="font-num">{packageTest}</span> was not found in the installed package)
              </>
            ) : null}
            .
          </>
        )}
      </p>
      {ran && rows.length > 0 && (
        <p className="text-body mb-2 font-num" data-testid="regression-summary">
          {within} of {rows.length} within the package&rsquo;s tolerance on this run.
        </p>
      )}
      {!ran && rows.length > 0 && <p className="text-body mb-2">Not run in this project yet: run it, and this run&rsquo;s values stand beside the package&rsquo;s.</p>}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-caption">
            <thead>
              <tr className="border-b border-line text-ink-soft">
                {t.headers.map((h, i) => (
                  <th key={h} className={i < 3 ? 'text-left py-1 pr-2 font-medium' : 'text-right py-1 px-1.5 font-medium'}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.expression} className="border-b border-line/50 align-top" data-testid="regression-row" data-within={r.within == null ? 'not-run' : String(r.within)}>
                  <td className="py-1 pr-2">{t.rows[i][0]}</td>
                  <td className="py-1 pr-2 font-num text-ink-soft">{t.rows[i][1]}</td>
                  <td className="py-1 pr-2 font-num">{t.rows[i][2]}</td>
                  <td className="py-1 px-1.5 text-right font-num">{t.rows[i][3]}</td>
                  <td className="py-1 px-1.5 text-right font-num" data-testid="regression-measured">
                    {t.rows[i][4]}
                  </td>
                  <td className="py-1 px-1.5 text-right font-num">{t.rows[i][5]}</td>
                  <td className="py-1 px-1.5 text-right font-num">{t.rows[i][6]}</td>
                  <td className={cx('py-1 px-1.5 text-right', r.within === false && 'text-signal-warn', r.within === true && 'text-signal-info')}>{t.rows[i][7]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ── Runs kept from the retired reference entry (alpha 2.2 D8) ───────────

function KeptRunsCard({ kept }: { kept: Artifact[] }) {
  const entries = [...new Set(kept.map((a) => retiredEntryOf(a)).filter((e): e is string => !!e))];
  return (
    <Card className="p-4" data-testid="kept-reference-runs">
      <h2 className="font-serif text-section-title font-semibold mb-1">Runs kept from the retired reference entry</h2>
      <p className="text-caption text-ink-soft mb-2">
        Proforma&rsquo;s shelf held a hand-written entry for this plant (<span className="font-num">{entries.join(', ')}</span>) until alpha 2.2. The
        runs a person kept from it stay theirs: each replays as kept and is held to this plant&rsquo;s package test, and BioRepo&rsquo;s page for it
        shows the whole run.
      </p>
      <ul className="space-y-3">
        {kept.map((a) => {
          const checks = packageChecks(a);
          const rows = regressionRows(null, checks, true);
          const t = regressionTable(rows);
          const within = rows.filter((r) => r.within === true).length;
          return (
            <li key={a.id} className="border-t border-line pt-2" data-testid="kept-reference-run" data-artifact={a.id}>
              <p className="text-caption flex flex-wrap items-center gap-1.5">
                <ProvenanceBadge p={a.provenance} compact />
                {a.tool === 'proforma_benchmark' ? 'The benchmark' : `A reference run of ${retiredEntryOf(a)}`}, kept{' '}
                <span className="font-num">{stamp(a.createdAt)}</span> ·{' '}
                <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/biorepo/artifacts/${encodeURIComponent(a.id)}`)}>
                  {a.id}
                </a>
              </p>
              {rows.length > 0 ? (
                <>
                  <p className="text-caption font-num mt-1" data-testid="kept-reference-within">
                    {within} of {rows.length} within the package&rsquo;s tolerance on this run.
                  </p>
                  <div className="overflow-x-auto mt-1">
                    <table className="w-full text-caption">
                      <thead>
                        <tr className="border-b border-line text-ink-soft">
                          {t.headers.map((h, i) => (
                            <th key={h} className={i < 3 ? 'text-left py-1 pr-2 font-medium' : 'text-right py-1 px-1.5 font-medium'}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {t.rows.map((cells, i) => (
                          <tr key={rows[i].expression} className="border-b border-line/50 align-top">
                            {cells.map((c, j) => (
                              <td key={j} className={j < 3 ? 'py-1 pr-2' : 'py-1 px-1.5 text-right font-num'}>
                                {c}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="text-caption text-ink-soft mt-1">This run keeps no checks against the package&rsquo;s test.</p>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// ── the page ────────────────────────────────────────────────────────────

export default function ProformaReference({ plantId }: { plantId: string }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [shelf, setShelf] = useState<LibraryShelf | null>(null);
  // Whether the shelf answered, either way: the plant's default configuration waits on it.
  const [shelfAsked, setShelfAsked] = useState(false);
  const [report, setReport] = useState<EngineRunReport | null>(null);
  // The project's runs: undefined until they answer, null when they could not be read.
  const [runs, setRuns] = useState<EngineRun[] | null | undefined>(undefined);
  // The runs kept from the retired entry for this plant: undefined until they answer, null when unread.
  const [kept, setKept] = useState<Artifact[] | null | undefined>(undefined);
  const [regression, setRegression] = useState<PackageRegression | null>(null);
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setShelf(null);
    setShelfAsked(false);
    setReport(null);
    setRuns(undefined);
    setKept(undefined);
    setRegression(null);
    setProblem(null);
    const said = (e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e));
    // The package test's values are asked for once the shelf names the plant.
    libraryShelf(ctrl.signal)
      .then((sh) => {
        if (ctrl.signal.aborted) return;
        setShelf(sh);
        if (sh.plants?.some((p) => p.id === plantId))
          libraryRegression(plantId, ctrl.signal).then(setRegression, () => !ctrl.signal.aborted && setRegression(null));
      }, said)
      .finally(() => !ctrl.signal.aborted && setShelfAsked(true));
    proformaStatus(ctrl.signal).then(setStatus, () => !ctrl.signal.aborted && setStatus(null));
    listRuns(ctrl.signal, 'biosteam').then(
      (rs) => !ctrl.signal.aborted && setRuns(rs),
      (e: unknown) => {
        if (ctrl.signal.aborted) return;
        setRuns(null);
        said(e);
      },
    );
    keptReferenceRuns(ctrl.signal).then(
      (all) => !ctrl.signal.aborted && setKept(keptRunsOf(plantId, all)),
      () => !ctrl.signal.aborted && setKept(null),
    );
    return () => ctrl.abort();
  }, [plantId]);

  const plant: LibraryPlant | null = shelf?.plants?.find((p) => p.id === plantId) ?? null;
  // The configuration a run of the plant takes when it names none: its default, as the library door runs it.
  const configuration = plant ? (runnable(plant).configurations[0] ?? null) : null;
  const chosen = runs && shelfAsked ? referenceRunOf(plantId, runs, configuration) : null;
  useEffect(() => {
    if (!chosen) return;
    const ctrl = new AbortController();
    runReport(chosen.id, ctrl.signal).then(
      (r) => !ctrl.signal.aborted && setReport(r),
      (e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)),
    );
    return () => ctrl.abort();
  }, [chosen?.id]);
  // The project's runs answered (with the plant's reference run or none), and the shelf named its configuration.
  const asked = runs !== undefined && runs !== null && shelfAsked && (!chosen || report !== null);

  useEffect(() => {
    if (!busy) return;
    const t0 = Date.now();
    setElapsed(0);
    const tick = window.setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => window.clearInterval(tick);
  }, [busy]);

  const run = () => {
    setBusy(true);
    setProblem(null);
    runPlant(plantId, null, reviewer)
      .then((r) => {
        setReport(r);
      })
      .catch((e: unknown) => setProblem(e instanceof StudiesRefused ? `${plantId} refused: ${e.message}` : problemOf(e)))
      .finally(() => {
        setBusy(false);
        proformaStatus().then(setStatus, () => setStatus(null));
      });
  };

  // A plant the shelf does not hold: the page claims nothing about it and offers no run.
  const missing = shelf !== null && plant === null;
  // A reference plant is one of the two the reference runs read; any other is a plant of the library shelf.
  const reference = REFERENCE_PLANTS.includes(plantId);
  const keptHere = kept ?? [];
  const art = report?.run.status === 'done' ? (report.artifact ?? null) : null;
  const view = art ? runViewOfRun(art) : null;
  const checks = packageChecks(art);
  const price = art ? libraryPrice(art) : null;
  const o = (art?.output ?? {}) as Record<string, unknown>;
  const irr = num((o.price as Record<string, unknown> | undefined)?.IRR) ?? num(view?.tables.tea?.IRR);
  const packageTest = plant?.tests?.find((t) => t === `test_${plantId}`) ?? plant?.tests?.[0] ?? null;
  const title = plant?.title ?? plantId;
  const shownRegression = regression ?? ((o.regression as PackageRegression | undefined) || null);

  return (
    <div data-testid="proforma-reference" data-plant={plantId}>
      <PageHeader
        eyebrow={<><span className="normal-case font-num">{plantId}</span>{missing ? null : reference ? ' · reference plant' : ' · plant of the library shelf'}</>}
        title={title}
        subtitle={
          missing
            ? undefined
            : `A published plant from the BioSTEAM project’s own biorefineries package, on the library shelf, run whole on its package’s own values${packageTest ? ' and held to its package’s own test' : ''}.`
        }
        actions={
          <LinkButton to="/proforma">
            <BookOpen size={14} /> Proforma
          </LinkButton>
        }
      />

      {(problem || missing) && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="reference-problem">{missing ? `The library shelf holds no plant ${plantId}.` : problem}</span>
            {missing && (
              <span className="block mt-1">
                <a className="text-accent hover:underline" href={href('/proforma')}>
                  Proforma
                </a>
                &rsquo;s Reference runs row lists the reference plants, and{' '}
                <a className="text-accent hover:underline" href={href('/proforma/studies')}>
                  Studies
                </a>{' '}
                runs any plant the shelf holds.
              </span>
            )}
          </Callout>
        </div>
      )}
      {missing ? null : (
        <>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-4 text-caption text-ink-soft" data-testid="reference-meta">
            <span>
              Source: <span className="text-ink font-num">{shelf ? `${shelf.package}, ${plant?.module ?? plantId}` : 'the library shelf has not answered'}</span>
            </span>
            {shelf && (
              <span>
                · on <span className="font-num text-ink">{shelf.simulator}</span>, <span className="font-num text-ink">{shelf.thermosteam}</span>
              </span>
            )}
            {packageTest && shelf && (
              <span data-testid="reference-package-test">
                · Held to <span className="font-num text-ink">{shelf.testFile}::{packageTest}</span>
              </span>
            )}
            {configuration && (
              <span data-testid="reference-configuration">
                · in its default configuration, <span className="font-num text-ink">{configuration}</span>
              </span>
            )}
            {art ? (
              <span className="inline-flex items-center gap-1" data-testid="reference-provenance">
                · Provenance, as the artifact computes it: <ProvenanceBadge p={art.provenance} />
              </span>
            ) : (
              asked && <span className="chip">not run yet</span>
            )}
          </div>

          <div className="space-y-4">
            <Card className="p-4" data-testid="reference-run-card">
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="primary" onClick={run} disabled={busy || !shelf || !reviewer} data-testid="reference-run">
                  <Play size={14} /> {busy ? 'Running…' : art ? 'Rerun' : 'Run'}
                </Button>
                <span className="text-caption text-ink-soft" data-testid="reference-status">
                  {status ? SIMULATOR_SAYS[status.status] : 'The simulator is the service’s.'}
                  {status?.error && <> {status.error}</>}
                  {busy && (
                    <>
                      {' '}
                      Running for <span className="font-num">{elapsed}</span> s; a first run starts the simulator and builds the plant, and takes a minute or two.
                    </>
                  )}
                </span>
              </div>
              {!reviewer && <p className="text-caption text-ink-soft mt-2">A run is asked for in a person&rsquo;s name: set yours in Settings first.</p>}
              {runs === null && !art && (
                <p className="text-body mt-3 text-signal-warn" data-testid="reference-runs-unread">
                  The project&rsquo;s runs could not be read, so this page cannot say whether the plant has run here.
                </p>
              )}
              {asked && !art && !busy && (
                <p className="text-body mt-3" data-testid="reference-not-run">
                  {keptHere.length > 0
                    ? 'The library plant has not run in this project yet; the runs kept from its retired entry are listed below. '
                    : 'Not run in this project yet. '}
                  A run is BioSTEAM building the package&rsquo;s plant on its own values and solving it once; the service keeps it as one run with
                  its artifact and its SFF file, and the same run asked again answers from it.
                </p>
              )}
              {report && art && (
                <div className="mt-3" data-testid="reference-result">
                  {price ? (
                    <Tick p={art.provenance}>
                      <div className="text-caption uppercase tracking-wide text-ink-soft">Price</div>
                      <div className="font-num text-display leading-none" data-testid="reference-price">
                        {fmt(price.value, 4)}
                      </div>
                      <div className="text-caption text-ink-soft mt-1">
                        {price.basis}; {price.reads}.
                        {irr != null && (
                          <>
                            {' '}
                            Internal rate of return the TEA holds: <span className="font-num">{fmt(irr, 4)}</span>.
                          </>
                        )}
                      </div>
                    </Tick>
                  ) : (
                    <p className="text-body text-ink-soft">The run holds no price: the plant carries no TEA here, or its TEA solved none.</p>
                  )}
                  <p className="text-caption text-ink-soft mt-2">
                    Run{' '}
                    <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/proforma/runs/${report.run.id}`)} data-testid="reference-run-page">
                      {report.run.id}
                    </a>
                    , kept by {report.run.by}, computed <span className="font-num">{stamp(art.createdAt)}</span>
                    {art.durationMs > 0 && (
                      <>
                        {' '}
                        in <span className="font-num">{fmt(art.durationMs / 1000, 1)}</span> s
                      </>
                    )}
                    , with <span className="font-num">{art.toolVersion}</span>
                    {view?.tables.tablesSource && <> · tables from {view.tables.tablesSource}</>}
                    {report.flowsheet && (
                      <>
                        {' '}
                        · its SFF file{' '}
                        <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/flowsheets/${report.flowsheet.id}`)}>
                          {report.flowsheet.id}
                        </a>
                      </>
                    )}
                    . The run&rsquo;s page draws the plant from its SFF file and lists its parameters.
                  </p>
                </div>
              )}
            </Card>

            {(plant?.compat ?? []).map((c) => (
              <Card key={c.change} className="p-4" data-testid="compatibility">
                <h2 className="font-serif text-section-title font-semibold mb-1">What this installation changes so the package builds</h2>
                <p className="text-body">
                  <span className="font-num">{c.change}</span>
                </p>
                <p className="text-caption text-ink-soft mt-1">{c.why}</p>
                <p className="text-caption text-ink-soft mt-1">Every run&rsquo;s basis states it as a convention.</p>
              </Card>
            ))}

            <RegressionCard regression={shownRegression} checks={checks} ran={!!art} packageTest={packageTest} plant={plantId} />

            {keptHere.length > 0 && <KeptRunsCard kept={keptHere} />}
            {kept === null && (
              <p className="text-caption text-ink-soft" data-testid="kept-reference-unread">
                The runs kept from the retired reference entries could not be read; BioRepo lists every artifact the project keeps.
              </p>
            )}

            {view && (
              <>
                <p className="text-caption text-ink-soft" data-testid="reference-one-case">
                  A reference run is one case on the package&rsquo;s own values: it samples nothing, so it has no price distribution, no sensitivity and
                  no sliders.
                </p>
                <RunReport
                  view={view}
                  priceBasis={price ? price.basis : 'USD per kg of the product the package names'}
                  labels={{}}
                  unitLabels={{}}
                  scenarioId=""
                  csvName={plantId}
                  oneCase
                  sffRecord={report?.flowsheet?.id ?? null}
                />
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
