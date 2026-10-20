// What one BioSTEAM run holds, drawn (OF-BLD-014 §8.4; OF-BLD-019 §3.2, D1).
//
// A run is one `proforma.run` artifact: the price's samples and their
// Spearman sensitivity, the base case, and the base case's tables as the
// Proforma worker read them from BioSTEAM's own objects (the TEA breakdown,
// every stream, every unit, the UnitGroup's utility duties, the diagram when
// Graphviz is on the host). Every section below reads one field of that run
// (`RunView`, src/lib/proforma.ts) and computes nothing of its own: no price,
// cost, flow or duty on the page is typed or derived in the browser. Each
// table exports as CSV, and each chart is drawn by the figure grammar
// (CostWaterfall, Tornado, Distribution), never by recharts.
//
// The scenario page (ProformaScenario.tsx) composes these sections under its
// inputs and its Run; a reference biorefinery's page (ProformaReference.tsx,
// OF-BLD-019 §3.3) reads the same sections over its own `proforma.reference`
// artifact through `runViewOfReference`, one case and no samples.
import { useMemo, useState, type ReactNode } from 'react';
import { Download } from 'lucide-react';
import type { FlowsheetInfo, ScenarioInput } from '@/data/types';
import { href } from '@/router';
import { evaluateGrid, COST_LINES, COST_LINE_LABEL } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { Card } from '@/components/ui';
import { Tick } from '@/components/Provenance';
import { CostWaterfall, Distribution, Tornado } from '@/components/figures';
import {
  INFEASIBLE_WORDS,
  NO_DIAGRAM,
  asResultGrid,
  baseCaseRefusal,
  diagramSrc,
  viewPrice,
  type RunView,
} from '@/lib/proforma';

/** Where a sampled input came from, beside its tornado bar. */
export const SOURCE_WORDS: Record<string, string> = {
  record: 'records',
  assumption: 'assumption',
  model: 'reference model',
  artifact: 'artifact',
  convention: 'convention',
};

/** A number as a table cell: thousands grouped from a thousand up, else a few significant places. */
export function cell(v: number | null | undefined, digits = 3): string {
  if (v == null || !Number.isFinite(v)) return '—';
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString('en-US');
  return fmt(v, digits);
}

/** A section's frame: its heading, one line on what it reads, and its CSV. */
function Section({
  title,
  reads,
  csv,
  testid,
  children,
}: {
  title: string;
  reads: string;
  csv?: { name: string; headers: string[]; rows: (string | number)[][] };
  testid: string;
  children: ReactNode;
}) {
  return (
    <Card className="p-4" data-testid={testid}>
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">{title}</h2>
        {csv && (
          <button className="chip" data-testid={`csv-${testid}`} onClick={() => exportCSV(`${csv.name}.csv`, csv.headers, csv.rows)}>
            <Download size={12} aria-hidden /> CSV
          </button>
        )}
      </div>
      <p className="text-caption text-ink-soft mb-2">{reads}</p>
      {children}
    </Card>
  );
}

function Table({ headers, rows, rowTestid }: { headers: string[]; rows: (string | number)[][]; rowTestid: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-caption">
        <thead>
          <tr className="border-b border-line text-ink-soft">
            {headers.map((h, i) => (
              <th key={h} className={i === 0 ? 'text-left py-1 pr-2 font-medium' : 'text-right py-1 px-1.5 font-medium'}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-line/50 align-top" data-testid={rowTestid}>
              {r.map((c, j) => (
                <td key={j} className={j === 0 ? 'py-1 pr-2 font-num' : 'py-1 px-1.5 text-right font-num'}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A unit's name for a column header, from the run's own `tableUnits`. */
const u = (view: RunView, key: string, fallback = '') => view.tables.tableUnits[key] ?? fallback;

// ── Result ──────────────────────────────────────────────────────────────

export function RunResult({ view, priceBasis, scenarioId }: { view: RunView; priceBasis: string; scenarioId: string }) {
  const price = viewPrice(view, priceBasis);
  return (
    <Card className="p-4" data-testid="run-result">
      <h2 className="font-serif text-section-title font-semibold mb-2">Result</h2>
      {price ? (
        <Tick p={view.provenance}>
          <div className="text-caption uppercase tracking-wide text-ink-soft">Minimum selling price</div>
          <div className="font-num text-display leading-none" data-testid="scenario-price">
            {fmt(price.value, 4)}
          </div>
          <div className="text-caption text-ink-soft mt-1">
            {price.basis}; {price.reads}
            {price.low != null && price.high != null && (
              <>
                , <span className="font-num">{fmt(price.low, 4)}</span> to <span className="font-num">{fmt(price.high, 4)}</span> between the 5th and
                95th percentiles
              </>
            )}
            . Provenance {view.provenance}
            {view.provenance === 'demo' ? ': it rests on at least one named person’s assumption.' : '.'}
          </div>
        </Tick>
      ) : (
        <p className="text-body">No sample of this run could be held by the flowsheet, so it has no price.</p>
      )}
      <p className="text-body mt-3" data-testid="base-case">
        {view.basePrice != null ? (
          <>
            Base case, every input at its value: <span className="font-num">{fmt(view.basePrice, 4)}</span> {priceBasis}.
          </>
        ) : view.baseInfeasible ? (
          <span className="text-signal-warn">The base case could not run: {baseCaseRefusal(view.baseInfeasible)}. The tables below are empty for it.</span>
        ) : (
          <span className="text-ink-soft">This run kept no base-case price.</span>
        )}
      </p>
      <p className="text-caption text-ink-soft mt-2">
        Run{' '}
        <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${view.artifactId}`)}>
          {view.artifactId}
        </a>
        {view.createdAt && (
          <>
            , computed <span className="font-num">{view.createdAt.replace('T', ' ').slice(0, 16)}</span>
          </>
        )}
        {view.durationMs != null && (
          <>
            {' '}
            in <span className="font-num">{fmt(view.durationMs / 1000, 1)}</span> s
          </>
        )}
        {view.scenarioId && view.scenarioId !== scenarioId && <> · its basis names scenario {view.scenarioId}</>}
        {view.tables.tablesSource && <> · tables from {view.tables.tablesSource}</>}.
      </p>
    </Card>
  );
}

// ── Cost breakdown ──────────────────────────────────────────────────────

export function CostBreakdown({
  view,
  priceBasis,
  csvName,
  totalLabel = 'Base-case price',
}: {
  view: RunView;
  priceBasis: string;
  csvName: string;
  /** What the closing bar is: the base case's price, or a reference run's TEA product price. */
  totalLabel?: string;
}) {
  const tea = view.tables.tea;
  return (
    <div data-testid="cost-breakdown">
      <CostWaterfall
        title="What is the price made of?"
        lines={tea?.lines ?? []}
        total={view.basePrice != null ? { label: totalLabel, value: view.basePrice } : null}
        unit={tea?.basis ? `USD per ${tea.basis}` : priceBasis}
        annualUnit={u(view, 'annual', 'USD/yr')}
        provenance={view.provenance}
        basis={[view.basis]}
        notes={
          tea
            ? [
                `Read from BioSTEAM's ${tea.teaClass} object for the base case: sales ${cell(tea.sales)}, installed equipment ${cell(tea.installedEquipmentCost)}, fixed capital ${cell(tea.FCI)}, total capital ${cell(tea.TCI)} USD, over ${cell(tea.operatingHours)} operating hours a year.`,
              ]
            : undefined
        }
        csvName={`${csvName}-cost-breakdown`}
      />
    </div>
  );
}

// ── Sensitivity, the distribution, the sliders ──────────────────────────

export function Sensitivity({ view, labels, csvName }: { view: RunView; labels: Record<string, string>; csvName: string }) {
  return (
    <div data-testid="sensitivity">
      <Tornado
        title="Which input moves the price most?"
        drawn="The rank correlation of each sampled input with the price over the feasible samples, strongest first, each labelled with where the input came from."
        series={['Spearman ρ']}
        unit="rank correlation"
        provenance={view.provenance}
        rows={view.sensitivity.map((s) => ({ label: labels[s.key] ?? s.key, values: [s.rho], tag: SOURCE_WORDS[s.sourceKind] ?? s.sourceKind }))}
        csvName={`${csvName}-tornado`}
      />
    </div>
  );
}

export function PriceDistribution({ view, priceBasis, csvName }: { view: RunView; priceBasis: string; csvName: string }) {
  return (
    <Distribution
      title="What would this plant's product cost, across the inputs' ranges?"
      quantity="Minimum selling price"
      unit={priceBasis}
      bins={view.histogram}
      quantiles={view.quantiles}
      provenance={view.provenance}
      samples={view.samples}
      infeasible={Object.entries(view.infeasible).map(([reason, count]) => ({ reason: INFEASIBLE_WORDS[reason] ?? reason, count }))}
      basis={[view.basis]}
      notes={['The inputs are sampled independently; a real vessel links them, so the infeasible share is part of the result.']}
      csvName={`${csvName}-distribution`}
    />
  );
}

/** Three inputs moved over the run's grid, with the interpolation the authored scenarios use. */
export function Sliders({ view, labels, priceBasis, scenarioId }: { view: RunView; labels: Record<string, string>; priceBasis: string; scenarioId: string }) {
  const g = view.grid;
  const grid = useMemo(() => (g ? asResultGrid(scenarioId, g) : null), [g, scenarioId]);
  const [point, setPoint] = useState<Record<string, number>>(() =>
    Object.fromEntries((g?.dims ?? []).map((d) => [d.key, d.values[Math.floor(d.values.length / 2)]])),
  );
  if (!g || !grid) return null;
  const r = evaluateGrid(grid, point);
  return (
    <Card className="p-4" data-testid="proforma-sliders">
      <h2 className="font-serif text-section-title font-semibold mb-1">Move three inputs over the run's grid</h2>
      <p className="text-caption text-ink-soft mb-3">
        Interpolated between the {g.msp.length} grid cases the service simulated; the other inputs stay at their base value.
        {g.infeasible > 0 && ` ${g.infeasible} cases could not run, and a point near one shows no price.`}
      </p>
      <div className="space-y-3">
        {g.dims
          .filter((d) => d.values.length > 1)
          .map((d) => (
            <label key={d.key} className="block">
              <span className="flex justify-between text-body">
                <span>{labels[d.key] ?? d.key}</span>
                <span className="font-num">{fmt(point[d.key], 4)}</span>
              </span>
              <input
                type="range"
                min={d.values[0]}
                max={d.values[d.values.length - 1]}
                step={(d.values[d.values.length - 1] - d.values[0]) / 100}
                value={point[d.key]}
                aria-label={labels[d.key] ?? d.key}
                onChange={(e) => setPoint({ ...point, [d.key]: Number(e.target.value) })}
              />
            </label>
          ))}
      </div>
      <div className="mt-3 font-num text-section-title" data-testid="slider-price">
        {Number.isFinite(r.msp) ? `${fmt(r.msp, 3)} ${priceBasis}` : 'No price here: a neighbouring case could not run.'}
      </div>
      {Number.isFinite(r.msp) && (
        <table className="w-full text-caption mt-2">
          <tbody>
            {COST_LINES.map((l) => (
              <tr key={l} className="border-t border-line/50">
                <td className="py-0.5">{COST_LINE_LABEL[l]}</td>
                <td className="py-0.5 text-right font-num">{fmt(r.costLines[l], 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ── Streams, equipment, utilities ───────────────────────────────────────

export function streamsTable(view: RunView) {
  const headers = [
    'Stream',
    'From',
    'To',
    'Phase',
    `T (${u(view, 'T', 'K')})`,
    `P (${u(view, 'P', 'Pa')})`,
    `Mass flow (${u(view, 'massFlow', 'kg/hr')})`,
    `By component (${u(view, 'massFlow', 'kg/hr')})`,
    `Price (${u(view, 'price', 'USD/kg')})`,
  ];
  const rows = view.tables.streams.map((s) => [
    s.id,
    s.source ?? 'feed',
    s.sink ?? 'out',
    s.phase,
    cell(s.T, 2),
    cell(s.P),
    cell(s.massFlow),
    Object.entries(s.massFlows)
      .map(([k, v]) => `${k} ${cell(v)}`)
      .join('; '),
    cell(s.price),
  ]);
  return { headers, rows };
}

export function StreamsTable({ view, csvName }: { view: RunView; csvName: string }) {
  const t = streamsTable(view);
  return (
    <Section
      title="Streams"
      testid="streams-table"
      reads="Every stream of the base case as BioSTEAM holds it after the run: the unit it leaves (feed, for one that enters the plant) and the one it enters (out, for one that leaves it), its phase, temperature, pressure and mass flow, by component."
      csv={{ name: `${csvName}-streams`, ...t }}
    >
      {t.rows.length ? <Table {...t} rowTestid="stream-row" /> : <p className="text-body text-ink-soft">This run kept no stream table.</p>}
    </Section>
  );
}

export function equipmentTable(view: RunView) {
  const headers = [
    'Unit',
    'Class',
    'Line',
    `Installed cost (${u(view, 'cost', 'USD')})`,
    `Purchase cost (${u(view, 'cost', 'USD')})`,
    `Heating duty (${u(view, 'duty', 'kJ/hr')})`,
    `Cooling duty (${u(view, 'duty', 'kJ/hr')})`,
    `Power (${u(view, 'power', 'kW')})`,
  ];
  const rows = [...view.tables.units]
    .sort((a, b) => a.order - b.order)
    .map((x) => [x.id, x.unitClass, x.line ?? '', cell(x.installedCost), cell(x.purchaseCost), cell(x.heatingDuty), cell(x.coolingDuty), cell(x.power)]);
  return { headers, rows };
}

export function EquipmentTable({ view, csvName }: { view: RunView; csvName: string }) {
  const t = equipmentTable(view);
  return (
    <Section
      title="Equipment"
      testid="equipment-table"
      reads="Every unit operation in run order, with BioSTEAM's installed and purchase cost and its heat duties and power; a dash where the unit has none."
      csv={{ name: `${csvName}-equipment`, ...t }}
    >
      {t.rows.length ? <Table {...t} rowTestid="unit-row" /> : <p className="text-body text-ink-soft">This run kept no unit table.</p>}
    </Section>
  );
}

export function utilitiesTable(view: RunView) {
  const d = view.tables.utilities;
  const headers = ['Duty', 'Total', 'Unit'];
  const rows = d
    ? [
        ['Heating', cell(d.heating), d.heatingUnit],
        ['Cooling', cell(d.cooling), d.coolingUnit],
        ['Electricity consumed', cell(d.electricityConsumption), d.electricityConsumptionUnit],
        ['Electricity produced', cell(d.electricityProduction), d.electricityProductionUnit],
      ]
    : [];
  return { headers, rows };
}

export function UtilitiesCard({ view, csvName }: { view: RunView; csvName: string }) {
  const t = utilitiesTable(view);
  const d = view.tables.utilities;
  return (
    <Section
      title="Utilities"
      testid="utilities"
      reads={`The plant's heating, cooling and electricity, as BioSTEAM's UnitGroup totals them over ${d ? d.group : 'the units'}, each in the unit the UnitGroup states.`}
      csv={{ name: `${csvName}-utilities`, ...t }}
    >
      {t.rows.length ? <Table {...t} rowTestid="utility-row" /> : <p className="text-body text-ink-soft">This run kept no utility duties.</p>}
    </Section>
  );
}

// ── Diagram ─────────────────────────────────────────────────────────────

export function DiagramCard({ view, csvName }: { view: RunView; csvName: string }) {
  const order = view.tables.unitOrder.length ? view.tables.unitOrder : [...view.tables.units].sort((a, b) => a.order - b.order).map((x) => x.id);
  const classOf = new Map(view.tables.units.map((x) => [x.id, x.unitClass]));
  return (
    <Section
      title="Diagram"
      testid="diagram"
      reads={view.tables.diagram ? 'The flowsheet as BioSTEAM draws it with Graphviz on the host that ran it.' : 'The units in the order the run simulated them.'}
      csv={{ name: `${csvName}-unit-order`, headers: ['Order', 'Unit', 'Class'], rows: order.map((id, i) => [i + 1, id, classOf.get(id) ?? '']) }}
    >
      {view.tables.diagram ? (
        <img src={diagramSrc(view.tables.diagram)} alt={`Flowsheet diagram of ${view.flowsheet ?? 'the run'}: ${order.join(', ')}`} className="max-w-full h-auto" data-testid="diagram-svg" />
      ) : (
        <>
          <p className="text-caption text-signal-warn mb-2" data-testid="diagram-note">
            {view.tables.diagramNote ?? NO_DIAGRAM}
          </p>
          {order.length > 0 ? (
            <ol className="list-decimal pl-5 text-body" data-testid="diagram-units">
              {order.map((id) => (
                <li key={id} className="font-num">
                  {id}
                  {classOf.get(id) && <span className="text-ink-soft"> · {classOf.get(id)}</span>}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-body text-ink-soft">This run kept no unit order.</p>
          )}
        </>
      )}
    </Section>
  );
}

// ── What the reference model supplied ───────────────────────────────────

export function ReadBack({ view }: { view: RunView }) {
  const entries = Object.entries(view.readBack);
  if (!entries.length) return null;
  return (
    <Card className="p-4">
      <h2 className="font-serif text-section-title font-semibold mb-1">What the reference model supplied</h2>
      <p className="text-caption text-ink-soft mb-2">Read back from the units and the finance model after the base case ran; nobody typed these.</p>
      <table className="w-full text-caption" data-testid="proforma-readback">
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k} className="border-t border-line/50">
              <td className="py-0.5">{k}</td>
              <td className="py-0.5 text-right font-num">{fmt(v, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

/**
 * The labels a run's sections print for its inputs: the scenario's own, else
 * the shelf's; with their units for the sliders, without for the tornado.
 */
export function inputLabels(inputs: ScenarioInput[] | null, flowsheet: FlowsheetInfo | null, withUnit = false): Record<string, string> {
  const out: Record<string, string> = {};
  const say = (label: string, unit: string) => (withUnit && unit ? `${label} (${unit})` : label);
  for (const i of flowsheet?.inputs ?? []) out[i.key] = say(i.name, i.unit);
  for (const i of inputs ?? []) out[i.key] = say(i.label, i.unit);
  return out;
}

/**
 * Every section of one run, in the order a reader takes them: the result,
 * the cost breakdown, the sensitivity, the distribution, the sliders when
 * the run walked a grid, the streams, the equipment, the utilities, the
 * diagram, and what the reference model supplied.
 */
export function RunReport({
  view,
  priceBasis,
  labels,
  unitLabels,
  scenarioId,
  csvName,
}: {
  view: RunView;
  priceBasis: string;
  /** Each input's label, and the same with its unit (inputLabels). */
  labels: Record<string, string>;
  unitLabels: Record<string, string>;
  scenarioId: string;
  csvName: string;
}) {
  return (
    <div className="space-y-4" data-testid="run-report">
      <RunResult view={view} priceBasis={priceBasis} scenarioId={scenarioId} />
      <CostBreakdown view={view} priceBasis={priceBasis} csvName={csvName} />
      <Sensitivity view={view} labels={labels} csvName={csvName} />
      <PriceDistribution view={view} priceBasis={priceBasis} csvName={csvName} />
      <Sliders key={view.artifactId} view={view} labels={unitLabels} priceBasis={priceBasis} scenarioId={scenarioId} />
      <StreamsTable view={view} csvName={csvName} />
      <EquipmentTable view={view} csvName={csvName} />
      <UtilitiesCard view={view} csvName={csvName} />
      <DiagramCard view={view} csvName={csvName} />
      <ReadBack view={view} />
    </div>
  );
}
