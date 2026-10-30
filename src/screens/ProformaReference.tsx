// A reference biorefinery's page (OF-BLD-019 §3.3, D3): /proforma/reference/:id.
//
// One page for every reference flowsheet on the shelf: the corn stover
// benchmark (the NREL 2011 design) and the dry-grind corn ethanol plant, each
// run whole by BioSTEAM on its package's own defaults. It reads, and never
// types:
//
//   GET /api/proforma/reference/{id}   the shelf's entry, the newest stored
//                                      `proforma.reference` run (or none), the
//                                      package test's values as the service
//                                      read them from the installed test
//                                      file, the simulator's status;
//   POST /api/proforma/reference/{id}  Run or Rerun (a basis already run
//                                      returns its stored artifact).
//
// The header names the source package and version, the provenance as the
// artifact computes it, and the package test the run is held to. The price is the output the shelf names (`priceOutput`). Below it,
// "Held to its package's own test" sets each regression value of the package
// beside what this run measured, the relative difference and whether it is
// within the package's tolerance, every number from the artifact's `checks`
// (or, before a run, the service's `regression`), none typed here. Then the
// same sections a scenario page shows, over the reference artifact read as a
// run (`runViewOfReference`): the cost breakdown closing on the TEA's own
// product price, what the TEA holds (its installed equipment cost is the
// TEA's, never a sum over the units: a TEA with a Lang factor prices
// installation on the purchase costs as a whole), streams, equipment,
// utilities, the diagram, and what the package set, read back. A reference
// run is one case, so it has no distribution, sensitivity or sliders. A
// change this installation makes so the package runs at all (the corn
// plant's `compatibility` convention) is said in words.
import { useEffect, useState } from 'react';
import { BookOpen, Play } from 'lucide-react';
import type { Artifact, FlowsheetInfo, PackageRegression, RegressionCheck } from '@/data/types';
import { href } from '@/router';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { PageHeader, Card, Button, Callout, LinkButton, cx } from '@/components/ui';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import {
  LEGACY_BENCHMARK_TOOL,
  ProformaDown,
  REFERENCE_TOOL,
  SIMULATOR_SAYS,
  basisInput,
  proformaReference,
  referenceChecks,
  referencePrice,
  runProformaReference,
  runViewOfReference,
  stamp,
  type ReferenceResponse,
} from '@/lib/proforma';
import { CostBreakdown, DiagramCard, EquipmentTable, ReadBack, StreamsTable, UtilitiesCard, cell } from '@/screens/ProformaBiosteam';

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** A value as a regression table prints it: thousands grouped, else five significant figures. */
const sig = (v: number | null | undefined, n = 5): string => {
  if (v == null || !Number.isFinite(v)) return '—';
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString('en-US');
  return String(Number(v.toPrecision(n)));
};
/** A share as a percentage, for the relative difference and the tolerance. */
const pct = (v: number | null | undefined): string => (v == null || !Number.isFinite(v) ? '—' : `${sig(v * 100, 2)} %`);

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

// ── Held to its package's own test ──────────────────────────────────────

interface RegressionRow {
  expression: string;
  label: string;
  unit: string;
  package: number;
  rtol: number;
  measured: number | null;
  relDiff: number | null;
  within: boolean | null;
}

/** The rows: the run's checks when it ran, else the package's values with nothing beside them. */
export function regressionRows(regression: PackageRegression | null, checks: RegressionCheck[], ran: boolean): RegressionRow[] {
  if (ran && checks.length) return checks.map((c) => ({ ...c }));
  return (regression?.values ?? []).map((v) => ({ ...v, measured: null, relDiff: null, within: null }));
}

export function regressionTable(rows: RegressionRow[]) {
  const headers = ['Quantity', 'Expression', 'Unit', "Package's value", 'This run', 'Relative difference', 'Tolerance', 'Within'];
  const body = rows.map((r) => [
    r.label,
    r.expression,
    r.unit || '—',
    sig(r.package),
    sig(r.measured),
    r.relDiff == null ? (r.measured != null && r.package === 0 ? 'package value is zero' : '—') : pct(r.relDiff),
    pct(r.rtol),
    r.within == null ? 'not run' : r.within ? 'within' : 'outside',
  ]);
  return { headers, rows: body };
}

function RegressionCard({
  regression,
  checks,
  art,
  packageTest,
  id,
}: {
  regression: PackageRegression | null;
  checks: RegressionCheck[];
  art: Artifact | null;
  packageTest: string | null;
  id: string;
}) {
  // Only a reference run is checked against the package's test; the
  // benchmark kept before reference runs held their checks measured a price
  // alone, so nothing stands beside the package's values for it (§3.R).
  const checked = art?.tool === REFERENCE_TOOL;
  art = checked ? art : null;
  const rows = regressionRows(regression, checks, !!art);
  const t = regressionTable(rows);
  const within = rows.filter((r) => r.within === true).length;
  return (
    <Card className="p-4" data-testid="regression-table">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Held to its package&rsquo;s own test</h2>
        {rows.length > 0 && (
          <button className="chip" data-testid="csv-regression" onClick={() => exportCSV(`${id}-package-test.csv`, t.headers, t.rows)}>
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
            The service read no regression test for this flowsheet
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
      {art && rows.length > 0 && (
        <p className="text-body mb-2 font-num" data-testid="regression-summary">
          {within} of {rows.length} within the package&rsquo;s tolerance on this run.
        </p>
      )}
      {!art && rows.length > 0 && <p className="text-body mb-2">Not run on this service yet: run it, and this run&rsquo;s values stand beside the package&rsquo;s.</p>}
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

// ── What the TEA holds ──────────────────────────────────────────────────

function TeaCard({ art, readBack }: { art: Artifact; readBack: Record<string, unknown> }) {
  const view = runViewOfReference(art);
  const tea = view?.tables.tea ?? null;
  if (!view || !tea) return null;
  const units = view.tables.tableUnits;
  const annual = units.annual ?? 'USD/yr';
  const cost = units.cost ?? 'USD';
  const lang = num(readBack.langFactor);
  const rows: [string, string, string, string?][] = [
    ['Product price', sig(tea.productPrice), tea.basis ? `USD per ${tea.basis}` : (units.price ?? 'USD/kg')],
    ['Internal rate of return', sig(tea.IRR), 'share'],
    ['Sales', cell(tea.sales), annual],
    ['Material cost', cell(tea.materialCost), annual],
    ['of which feedstock', cell(tea.feedstockCost), annual],
    ['Utility cost', cell(tea.utilityCost), annual],
    ['Purchase cost of equipment', cell(tea.purchaseCost), cost],
    ['Installed equipment cost', cell(tea.installedEquipmentCost), cost, 'tea-installed'],
    ['Fixed capital investment', cell(tea.FCI), cost],
    ['Total capital investment', cell(tea.TCI), cost],
    ['Fixed operating cost', cell(tea.FOC), annual],
    ['Labour', cell(tea.laborCost), annual],
    ['Capital recovery', cell(tea.capitalRecovery), annual],
    ['Co-product credits', cell(tea.coproductCredits), annual],
    ['Operating hours', cell(tea.operatingHours), 'h/yr'],
  ];
  return (
    <Card className="p-4" data-testid="tea-summary">
      <h2 className="font-serif text-section-title font-semibold mb-1">What the TEA holds</h2>
      <p className="text-caption text-ink-soft mb-2">
        Read from the package&rsquo;s {tea.teaClass} object after the run, through its own attributes; nothing here is summed in the browser.
      </p>
      <table className="w-full text-caption">
        <tbody>
          {rows.map(([label, value, unit, testid]) => (
            <tr key={label} className="border-t border-line/50" data-testid={testid}>
              <td className="py-0.5 pr-2">{label}</td>
              <td className="py-0.5 px-1.5 text-right font-num">{value}</td>
              <td className="py-0.5 pl-1.5 font-num text-ink-soft">{unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-caption text-ink-soft mt-2" data-testid="tea-installed-note">
        The installed equipment cost is the TEA&rsquo;s own figure, the one the price rests on. The equipment table below lists each unit&rsquo;s installed
        cost as BioSTEAM&rsquo;s unit holds it; their sum need not equal the TEA&rsquo;s, because a TEA with a Lang factor prices installation on the
        purchase costs as a whole.
        {lang != null && (
          <>
            {' '}
            The Lang factor read back from this package: <span className="font-num">{sig(lang)}</span>.
          </>
        )}
      </p>
    </Card>
  );
}

// ── the page ────────────────────────────────────────────────────────────

export default function ProformaReference({ flowsheetId }: { flowsheetId: string }) {
  const [state, setState] = useState<ReferenceResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState(null);
    setProblem(null);
    proformaReference(flowsheetId, ctrl.signal)
      .then(setState)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [flowsheetId]);

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
    runProformaReference(flowsheetId)
      .then((r) => setState((s) => ({ ...(s ?? {}), ...r })))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };

  const info: FlowsheetInfo | null = state?.flowsheet ?? null;
  const art = state?.artifact ?? null;
  const view = art ? runViewOfReference(art) : null;
  const regression = state?.regression ?? (art?.output?.regression as PackageRegression | undefined) ?? null;
  const checks = referenceChecks(art);
  const price = art ? referencePrice(info, art) : null;
  const compat = basisInput(art, 'compatibility');
  const simulator = basisInput(art, 'simulator');
  const thermo = basisInput(art, 'thermodynamics');
  const pkg = basisInput(art, 'flowsheet');
  const o = (art?.output ?? {}) as Record<string, unknown>;
  const refs = Array.isArray(o.references) ? (o.references as unknown[]).filter((r): r is string => typeof r === 'string') : [];
  const irr = num(o.IRR) ?? num(view?.tables.tea?.IRR);
  const title = info?.title ?? flowsheetId;
  // The benchmark kept before reference runs held their tables (OF-BLD-014
  // §8.2): shown, price only, with the note that says so; Run makes the full
  // reference run.
  const legacy = art?.tool === LEGACY_BENCHMARK_TOOL;
  // A 404 in words: the service holds no such reference (§3.R, finding 14).
  // The page then claims nothing about it and offers no run.
  const missing = !!problem && !state;

  return (
    <div data-testid="proforma-reference" data-flowsheet={flowsheetId}>
      <PageHeader
        eyebrow={missing ? flowsheetId : `${flowsheetId} · reference biorefinery`}
        title={title}
        subtitle={
          missing ? undefined : (info?.description ?? 'A published biorefinery from the BioSTEAM project’s own biorefineries package, run whole on its package’s defaults.')
        }
        actions={
          <LinkButton to="/proforma">
            <BookOpen size={14} /> Proforma
          </LinkButton>
        }
      />

      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="reference-problem">{problem}</span>
            {missing && (
              <span className="block mt-1">
                <a className="text-accent hover:underline" href={href('/proforma')}>
                  Proforma
                </a>
                &rsquo;s Reference runs row lists the reference biorefineries this service holds.
              </span>
            )}
          </Callout>
        </div>
      )}
      {missing ? null : (
      <>
      {state?.note && <p className="text-caption text-ink-soft mb-3" data-testid="reference-note">{state.note}</p>}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-4 text-caption text-ink-soft" data-testid="reference-meta">
        <span>
          Source: <span className="text-ink font-num">{info?.source ?? 'the shelf has not answered'}</span>
          {pkg?.source.id && <> (<span className="font-num">{pkg.source.id}</span>)</>}
        </span>
        {simulator && (
          <span>
            · on <span className="font-num text-ink">{String(simulator.value)}</span>
            {thermo && (
              <>
                , <span className="font-num text-ink">{String(thermo.value)}</span>
              </>
            )}
          </span>
        )}
        {info?.packageTest && (
          <span data-testid="reference-package-test">
            · Held to <span className="font-num text-ink">{info.packageTest}</span>
          </span>
        )}
        {art ? (
          <span className="inline-flex items-center gap-1" data-testid="reference-provenance">
            · Provenance, as the artifact computes it: <ProvenanceBadge p={art.provenance} />
          </span>
        ) : (
          <span className="chip">not run yet</span>
        )}
      </div>

      <div className="space-y-4">
        <Card className="p-4" data-testid="reference-run-card">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" onClick={run} disabled={busy || !state} data-testid="reference-run">
              <Play size={14} /> {busy ? 'Running…' : art && !legacy ? 'Rerun' : 'Run'}
            </Button>
            <span className="text-caption text-ink-soft" data-testid="reference-status">
              {state ? SIMULATOR_SAYS[state.simulator.status] : problem ? 'The simulator is the service’s.' : 'Asking the service…'}
              {state?.simulator.error && <> {state.simulator.error}</>}
              {busy && (
                <>
                  {' '}
                  Running for <span className="font-num">{elapsed}</span> s; a first run starts the simulator and loads the plant, and takes a minute or two.
                </>
              )}
            </span>
          </div>
          {state && !art && !busy && (
            <p className="text-body mt-3" data-testid="reference-not-run">
              Not run on this service yet. A run is BioSTEAM building the package&rsquo;s plant on its own defaults and solving it once; the service
              keeps it as one artifact.
            </p>
          )}
          {art && (
            <div className="mt-3" data-testid="reference-result">
              {price ? (
                <Tick p={art.provenance}>
                  <div className="text-caption uppercase tracking-wide text-ink-soft">{info?.priceOutput ? `Price (${info.priceOutput})` : 'Price'}</div>
                  <div className="font-num text-display leading-none" data-testid="reference-price">
                    {fmt(price.value, 4)}
                  </div>
                  <div className="text-caption text-ink-soft mt-1">
                    {price.basis}; {price.reads}.
                    {irr != null && (
                      <>
                        {' '}
                        Internal rate of return at this price: <span className="font-num">{sig(irr)}</span>.
                      </>
                    )}
                  </div>
                </Tick>
              ) : (
                <p className="text-body text-ink-soft">The run holds no price the shelf names for this flowsheet.</p>
              )}
              <p className="text-caption text-ink-soft mt-2">
                Run{' '}
                <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${art.id}`)}>
                  {art.id}
                </a>
                , computed <span className="font-num">{stamp(art.createdAt)}</span>
                {art.durationMs > 0 && (
                  <>
                    {' '}
                    in <span className="font-num">{fmt(art.durationMs / 1000, 1)}</span> s
                  </>
                )}
                , by <span className="font-num">{art.toolVersion}</span>
                {view?.tables.tablesSource && <> · tables from {view.tables.tablesSource}</>}.
              </p>
            </div>
          )}
        </Card>

        {compat && (
          <Card className="p-4" data-testid="compatibility">
            <h2 className="font-serif text-section-title font-semibold mb-1">What this installation changes so the package runs</h2>
            <p className="text-body">
              <span className="font-num">{String(compat.value)}</span>
            </p>
            {compat.source.note && <p className="text-caption text-ink-soft mt-1">{compat.source.note}</p>}
            <p className="text-caption text-ink-soft mt-1">The run&rsquo;s basis states it as a {compat.source.kind}.</p>
          </Card>
        )}

        <RegressionCard regression={regression} checks={checks} art={art} packageTest={info?.packageTest ?? null} id={flowsheetId} />

        {view && (
          <>
            <CostBreakdown view={view} priceBasis={info?.priceBasis ?? 'on the basis the package states'} csvName={flowsheetId} totalLabel="The TEA’s product price" />
            {art && <TeaCard art={art} readBack={(o.readBack ?? {}) as Record<string, unknown>} />}
            <p className="text-caption text-ink-soft" data-testid="reference-one-case">
              A reference run is one case on the package&rsquo;s own defaults: it samples nothing, so it has no price distribution, no sensitivity and
              no sliders.
            </p>
            <StreamsTable view={view} csvName={flowsheetId} />
            <EquipmentTable view={view} csvName={flowsheetId} />
            <UtilitiesCard view={view} csvName={flowsheetId} />
            <DiagramCard view={view} csvName={flowsheetId} />
            <ReadBack view={view} flowsheet={info} />
          </>
        )}

        {refs.length > 0 && (
          <Card className="p-4" data-testid="reference-citations">
            <h2 className="font-serif text-section-title font-semibold mb-1">What the package cites for the design</h2>
            <ul className="list-disc pl-5 text-body">
              {refs.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>
      </>
      )}
    </div>
  );
}
