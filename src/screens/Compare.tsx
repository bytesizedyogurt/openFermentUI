// Scenario comparison (OF-DES-001 §8.13; OF-BLD-019 §3.3, D1, D6).
//
// Pinned BioSTEAM scenarios (kind 'biosteam', held or made here) side by
// side from each one's NEWEST RUN ARTIFACT (its `lastRunId`, read at GET
// /api/biorepo/artifacts/{id}): the price with its basis and provenance, the
// TEA's cost lines closing on the run's own base-case price, and the inputs as
// the run's basis names them (records with their count and range, a named
// person's assumption with its range, an artifact, a model or a convention).
// Nothing is recomputed: no delta, no total, no price is made here. A scenario
// with no run says so; scenarios on different flowsheets are compared under a
// line saying their bases differ.
//
// Pins are Durable (D6): a created scenario carries its own.
import { useEffect, useState } from 'react';
import { Download, GitCompare, Pin } from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import type { Artifact, FlowsheetInfo, Scenario } from '@/data/types';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { PageHeader, Card, Button, EmptyState, Callout, cx } from '@/components/ui';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';
import { cell } from '@/screens/ProformaBiosteam';
import {
  ProformaDown,
  newestRunId,
  proformaArtifact,
  proformaNewestRun,
  proformaShelf,
  runInputs,
  runViewOfArtifact,
  stamp,
  viewPrice,
  type RunInput,
  type RunView,
} from '@/lib/proforma';

export default function Compare() {
  const scenarios = useStore((s) => s.scenarios);
  const pinned = scenarios.filter((s) => s.pinned && s.kind === 'biosteam');

  if (pinned.length === 0) {
    return (
      <div>
        <PageHeader title="Compare scenarios" subtitle="Pin scenarios to line them up side by side." />
        <OwnerTabs tabs={BIOREPO_TABS} />
        <EmptyState
          title="Nothing pinned yet"
          body="Open a scenario and use Pin to add it here: BioSTEAM scenarios are set side by side from their newest runs, two or more at once."
          icon={<GitCompare size={28} />}
          action={<Button onClick={() => navigate('/proforma')}>Browse scenarios</Button>}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Compare scenarios"
        subtitle={`${pinned.length} pinned scenario${pinned.length === 1 ? '' : 's'}. BioSTEAM scenarios are read from their newest runs, side by side; nothing is recomputed here.`}
      />
      <OwnerTabs tabs={BIOREPO_TABS} />
      <BiosteamCompare scenarios={pinned} />
    </div>
  );
}

// ── BioSTEAM scenarios, from their newest runs ──────────────────────────

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));
const when = (iso: string | null) => (iso ? stamp(iso) : '');

interface Column {
  scenario: Scenario;
  flowsheetId: string;
  flowsheet: FlowsheetInfo | null;
  runId: string | null;
  view: RunView | null;
  problem: string | null;
  /** Whether the service has answered for this scenario's newest run. */
  asked: boolean;
}

/** An input's source in words, with its range, as the run's basis states it. */
export function inputWords(i: RunInput): string {
  const u = i.unit ? ` ${i.unit}` : '';
  const range = (lo: number | null, hi: number | null) => (lo == null || hi == null ? '' : lo === hi ? `${fmt(lo, 4)}${u}` : `${fmt(lo, 4)}–${fmt(hi, 4)}${u}`);
  switch (i.kind) {
    case 'record':
      return `${i.count} record${i.count === 1 ? '' : 's'}, ${range(i.low, i.high)}${i.note ? `; ${i.note}` : ''}`;
    case 'assumption':
      return `assumption by ${i.by ?? 'nobody named'}: ${i.value == null ? '' : fmt(i.value, 4)}${u}${i.low != null && i.high != null ? `, range ${range(i.low, i.high)}` : ''}`;
    case 'artifact':
      // A fermOS fit's value with its range, and what the basis says of it
      // (§7.R): the run took this input from a kept artifact.
      return `artifact ${i.by ?? ''}${i.value != null ? `: ${typeof i.value === 'number' ? fmt(i.value, 4) + u : i.value}` : ''}${i.low != null && i.high != null ? `, range ${range(i.low, i.high)}` : ''}${i.note ? `; ${i.note}` : ''}`.trim();
    case 'absent':
      return i.note ?? 'not in this run\u2019s basis';
    default:
      return `${i.kind}${i.value != null ? `: ${typeof i.value === 'number' ? fmt(i.value, 4) + u : i.value}` : ''}`;
  }
}

function BiosteamCompare({ scenarios }: { scenarios: Scenario[] }) {
  const [shelf, setShelf] = useState<FlowsheetInfo[]>([]);
  const [arts, setArts] = useState<Record<string, Artifact | string>>({});
  // Each scenario's newest run on the service (§3.R, findings 8 and 21): a
  // run made in another browser, by the API or by Postdoc is compared too;
  // the run this browser kept stands in only where the service holds none.
  const [served, setServed] = useState<Record<string, Artifact | null>>({});
  const scenarioIds = scenarios.map((s) => s.id).join('|');
  useEffect(() => {
    const ctrl = new AbortController();
    for (const id of scenarioIds.split('|').filter(Boolean)) {
      proformaNewestRun(id, ctrl.signal)
        .then((art) => setServed((m) => ({ ...m, [id]: art })))
        .catch(() => !ctrl.signal.aborted && setServed((m) => ({ ...m, [id]: null })));
    }
    return () => ctrl.abort();
  }, [scenarioIds]);
  const runIdOf = (s: Scenario) => newestRunId(served[s.id], s.lastRunId);
  const runIds = scenarios.map((s) => (served[s.id] ? '' : (s.lastRunId ?? ''))).join('|');

  useEffect(() => {
    const ctrl = new AbortController();
    proformaShelf(ctrl.signal)
      .then(setShelf)
      .catch(() => {
        /* the columns name the flowsheet by its id */
      });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    const ids = [...new Set(runIds.split('|').filter(Boolean))];
    for (const id of ids) {
      proformaArtifact(id, ctrl.signal)
        .then((art) => setArts((a) => ({ ...a, [id]: art })))
        .catch((e: unknown) => !ctrl.signal.aborted && setArts((a) => ({ ...a, [id]: problemOf(e) })));
    }
    return () => ctrl.abort();
  }, [runIds]);

  const columns: Column[] = scenarios.map((scenario) => {
    const flowsheetId = scenario.flowsheetId ?? scenario.modelId;
    const runId = runIdOf(scenario);
    const got = served[scenario.id] ?? (runId ? arts[runId] : undefined);
    const art = got && typeof got !== 'string' ? got : null;
    const view = art ? runViewOfArtifact(art) : null;
    const problem = typeof got === 'string' ? got : art && !view ? `${runId} is not a scenario run: it was kept by ${art.tool}.` : null;
    return { scenario, flowsheetId, flowsheet: shelf.find((f) => f.id === flowsheetId) ?? null, runId, view, problem, asked: scenario.id in served };
  });

  const flowsheets = [...new Set(columns.map((c) => c.flowsheetId))];
  const basisOf = (c: Column) => c.flowsheet?.priceBasis ?? 'on the basis its flowsheet states';
  // Each column's inputs carry its own flowsheet's names (§3.R, finding 16):
  // two flowsheets share keys (titre, yield, productivity), so with more
  // than one flowsheet a row is the key, and each cell names its input.
  const several = flowsheets.length > 1;
  const inputsOf = (c: Column) => (c.view ? runInputs(c.view, c.flowsheet) : []);
  const rowLabel = (k: string) => {
    if (several) return k;
    for (const c of columns) {
      const named = c.flowsheet?.inputs.find((i) => i.key === k)?.name ?? inputsOf(c).find((i) => i.key === k)?.label;
      if (named) return named;
    }
    return k;
  };
  const cellWords = (i: RunInput) => (several ? `${i.label}: ${inputWords(i)}` : inputWords(i));
  const inputKeys = [...new Set(columns.flatMap((c) => [...(c.flowsheet?.inputs.map((i) => i.key) ?? []), ...inputsOf(c).map((i) => i.key)]))];
  const lineKeys: { key: string; label: string }[] = [];
  for (const c of columns)
    for (const l of c.view?.tables.tea?.lines ?? []) if (!lineKeys.some((x) => x.key === l.key)) lineKeys.push({ key: l.key, label: l.label });

  const priceCell = (c: Column) => (c.view ? viewPrice(c.view, basisOf(c)) : null);
  const lineOf = (c: Column, key: string) => c.view?.tables.tea?.lines.find((l) => l.key === key) ?? null;
  const inputOf = (c: Column, key: string) => inputsOf(c).find((i) => i.key === key) ?? null;

  const exportAll = () => {
    const headers = ['Row', ...columns.map((c) => c.scenario.name)];
    const rows: (string | number)[][] = [
      ['Flowsheet', ...columns.map((c) => c.flowsheetId)],
      ['Newest run', ...columns.map((c) => c.runId ?? 'not run yet')],
      ['Provenance', ...columns.map((c) => c.view?.provenance ?? '')],
      ['Minimum selling price', ...columns.map((c) => priceCell(c)?.value ?? '')],
      ['Price basis', ...columns.map((c) => (c.view ? basisOf(c) : ''))],
      ['Price, 5th percentile', ...columns.map((c) => priceCell(c)?.low ?? '')],
      ['Price, 95th percentile', ...columns.map((c) => priceCell(c)?.high ?? '')],
      ...lineKeys.map((l) => [`${l.label} (per unit of the price's basis)`, ...columns.map((c) => lineOf(c, l.key)?.perUnit ?? '')]),
      ['Base-case price', ...columns.map((c) => c.view?.basePrice ?? '')],
      ...inputKeys.map((k) => [`Input: ${rowLabel(k)}`, ...columns.map((c) => (c.view ? cellWords(inputOf(c, k) ?? { key: k, label: k, kind: 'absent', unit: '', count: 0, low: null, high: null, value: null, by: null, note: null }) : ''))]),
    ];
    exportCSV('biosteam-comparison.csv', headers, rows);
  };

  const th = 'text-left py-1.5 px-2 font-medium align-bottom min-w-[180px]';
  const td = 'py-1.5 px-2 align-top';
  return (
    <section className="mb-8" data-testid="compare-biosteam">
      <div className="flex flex-wrap items-end justify-between gap-2 mb-2">
        <h2 className="font-serif text-section-title font-semibold">BioSTEAM scenarios, from their newest runs</h2>
        <Button onClick={exportAll} data-testid="compare-csv">
          <Download size={14} /> Export comparison CSV
        </Button>
      </div>
      {columns.length === 1 && (
        <p className="text-body text-ink-soft mb-3" data-testid="compare-one">
          One BioSTEAM scenario is pinned. Pin another on its page, or on Proforma&rsquo;s index, and they stand side by side here.
        </p>
      )}
      {flowsheets.length > 1 && (
        <div className="mb-3" data-testid="compare-bases-differ">
          <Callout kind="warn" title="Their bases differ">
            These scenarios run different flowsheets:{' '}
            {flowsheets
              .map((id) => {
                const f = shelf.find((x) => x.id === id);
                return `${f?.title ?? id} prices ${f?.priceBasis ?? 'on its own basis'}`;
              })
              .join('; ')}
            . A price, a cost line or an input of one is not the same quantity as the same row of another; read the columns side by side, not
            as a difference.
          </Callout>
        </div>
      )}
      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-body">
          <thead>
            <tr className="border-b border-line text-caption text-ink-soft">
              <th className={cx(th, 'min-w-[160px]')} />
              {columns.map((c) => (
                <th key={c.scenario.id} className={th} data-testid="compare-column" data-scenario={c.scenario.id}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="chip font-num">{c.flowsheetId}</span>
                    <Pin size={12} className="text-accent" />
                  </div>
                  <a href={href(`/proforma/scenario/${c.scenario.id}`)} className="font-serif text-body font-semibold text-ink hover:text-accent">
                    {c.scenario.name}
                  </a>
                  <div className="font-normal">{c.flowsheet?.title ?? `Flowsheet ${c.flowsheetId}`}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line/60">
              <td className={cx(td, 'text-caption text-ink-soft')}>Newest run</td>
              {columns.map((c) => (
                <td key={c.scenario.id} className={cx(td, 'text-caption')}>
                  {!c.runId && !c.asked ? (
                    <span className="text-ink-soft">Asking the service for its newest run…</span>
                  ) : !c.runId ? (
                    <span data-testid="compare-not-run">
                      Not run yet.{' '}
                      <a className="text-accent hover:underline" href={href(`/proforma/scenario/${c.scenario.id}`)}>
                        Open it to run it
                      </a>
                      .
                    </span>
                  ) : c.problem ? (
                    <span className="text-signal-warn">
                      Its newest run, {c.runId}, could not be read: {c.problem}
                    </span>
                  ) : c.view ? (
                    <span className="inline-flex flex-wrap items-center gap-1.5">
                      <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${c.view.artifactId}`)}>
                        {c.view.artifactId}
                      </a>
                      <span className="font-num">{when(c.view.createdAt)}</span>
                      <ProvenanceBadge p={c.view.provenance} compact />
                      {c.view.scenarioId && c.view.scenarioId !== c.scenario.id && <span>its basis names scenario {c.view.scenarioId}</span>}
                    </span>
                  ) : (
                    <span className="text-ink-soft">Reading {c.runId}…</span>
                  )}
                </td>
              ))}
            </tr>
            <tr className="border-b border-line/60" data-testid="compare-price-row">
              <td className={cx(td, 'text-caption text-ink-soft')}>Minimum selling price</td>
              {columns.map((c) => {
                const p = priceCell(c);
                return (
                  <td key={c.scenario.id} className={td}>
                    {p && c.view ? (
                      <Tick p={c.view.provenance}>
                        <div className="font-num text-section-title leading-none" data-testid="compare-price">
                          {fmt(p.value, 4)}
                        </div>
                        <div className="text-caption text-ink-soft mt-0.5">
                          {p.basis}; {p.reads}
                          {p.low != null && p.high != null && (
                            <>
                              , <span className="font-num">{fmt(p.low, 4)}</span> to <span className="font-num">{fmt(p.high, 4)}</span> between the 5th
                              and 95th percentiles
                            </>
                          )}
                          . Provenance {c.view.provenance}.
                        </div>
                      </Tick>
                    ) : (
                      <span className="text-ink-soft">{c.view ? 'No sample of this run could be held, so it has no price.' : '—'}</span>
                    )}
                  </td>
                );
              })}
            </tr>
            <tr className="border-b border-line bg-surface-1/60">
              <td className={cx(td, 'text-caption uppercase tracking-wide text-ink-soft')} colSpan={columns.length + 1}>
                Cost breakdown, from each run&rsquo;s TEA, per unit of its price&rsquo;s basis
              </td>
            </tr>
            {lineKeys.map((l) => (
              <tr key={l.key} className="border-b border-line/60" data-testid="compare-line-row" data-line={l.key}>
                <td className={cx(td, 'text-caption')}>{l.label}</td>
                {columns.map((c) => {
                  const line = lineOf(c, l.key);
                  return (
                    <td key={c.scenario.id} className={cx(td, 'font-num')}>
                      {line ? (
                        <>
                          {line.perUnit == null ? '—' : fmt(line.perUnit, 4)}
                          <span className="block text-caption text-ink-soft">
                            {cell(line.usdPerYear)} {c.view?.tables.tableUnits.annual ?? 'USD/yr'}
                          </span>
                        </>
                      ) : (
                        <span className="text-ink-soft">{c.view ? 'not a line of this run' : '—'}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr className="border-b border-line" data-testid="compare-base-row">
              <td className={cx(td, 'text-caption font-medium')}>Base-case price</td>
              {columns.map((c) => (
                <td key={c.scenario.id} className={cx(td, 'font-num font-medium')}>
                  {c.view?.basePrice != null ? fmt(c.view.basePrice, 4) : '—'}
                  {c.view?.tables.tea?.basis && <span className="block text-caption text-ink-soft font-normal">USD per {c.view.tables.tea.basis}</span>}
                </td>
              ))}
            </tr>
            <tr className="border-b border-line bg-surface-1/60">
              <td className={cx(td, 'text-caption uppercase tracking-wide text-ink-soft')} colSpan={columns.length + 1}>
                Inputs, as each run&rsquo;s basis names them
              </td>
            </tr>
            {inputKeys.map((k) => (
              <tr key={k} className="border-b border-line/60" data-testid="compare-input-row" data-input={k}>
                <td className={cx(td, 'text-caption', several && 'font-num')}>{rowLabel(k)}</td>
                {columns.map((c) => {
                  const i = inputOf(c, k);
                  return (
                    <td key={c.scenario.id} className={cx(td, 'text-caption')} data-kind={i?.kind ?? 'none'}>
                      {!c.view ? '—' : i ? cellWords(i) : <span className="text-ink-soft">not an input of this flowsheet</span>}
                      {c.view && i?.kind === 'artifact' && i.by && (
                        <>
                          {' '}
                          <a
                            className="text-accent underline underline-offset-2"
                            href={href(`/biorepo/artifacts/${encodeURIComponent(i.by)}`)}
                            data-testid="compare-input-artifact"
                          >
                            open the artifact
                          </a>
                        </>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-caption text-ink-soft mt-2">
        Every number above is read from a run artifact: the price is the median of the samples that ran (else the base case), each cost line
        is the TEA&rsquo;s, and the base-case price is the run&rsquo;s own, never a sum made here. A record-bound input&rsquo;s range is the
        lowest and highest record value the run&rsquo;s basis lists.
      </p>
    </section>
  );
}
