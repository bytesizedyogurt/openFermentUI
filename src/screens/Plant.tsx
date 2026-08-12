// The plant behind the price (fermOS · bioSTEAM).
//
// Everything on this screen is downstream of one function call: build the
// flowsheet at the scenario's point, size it, cost it, and solve for the price
// that drives net present value to zero. Nothing here is authored. If the
// equipment table is empty the plant did not build, and the screen says that
// rather than showing a plausible number with nothing behind it.
//
// The screen is long on purpose. A techno-economic result that shows only its
// headline is asking to be believed; one that shows its equipment list, its
// capital ladder and its cash flow is asking to be checked, and checking is the
// entire point.
import { useMemo, useState } from 'react';
import {
  BarChart,
  Bar as RBar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import {
  AlertTriangle,
  Boxes,
  Download,
  Factory,
  Gauge,
  Table2,
  Wallet,
  Waves,
} from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { fmt } from '@/engine/units';
import { evaluatePlantCached } from '@/engine/plant';
import type { PlantResult } from '@/engine/plant';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import { runPlantUncertainty, type PlantUncertainty } from '@/engine/uncertainty';
import { exportCSV } from '@/lib/csv';
import { scaled } from '@/sim/latency';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import {
  PageHeader,
  Card,
  SectionTitle,
  Button,
  Callout,
  EmptyState,
  Explain,
  Stat,
  cx,
} from '@/components/ui';

const USD = (v: number): string => (Number.isFinite(v) ? fmt(v) : '—');

/** A "view as table" disclosure — the accessibility floor for every chart. */
function ChartTable({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  return (
    <details className="mt-2">
      <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
        <Table2 size={12} /> View as table
      </summary>
      <div className="overflow-x-auto mt-1.5">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {headers.map((h, i) => (
                <th key={h} className={cx('py-1 whitespace-nowrap', i === 0 ? 'text-left' : 'text-right')}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-line/50">
                {r.map((c, j) => (
                  <td
                    key={j}
                    className={cx('py-1 whitespace-nowrap', j === 0 ? 'text-left' : 'text-right font-num')}
                  >
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** The DPI → TCI ladder, as a list of steps that each name what was added. */
function CapitalLadder({ r }: { r: PlantResult }) {
  const c = r.capital;
  const rows: { label: string; value: number; note: string }[] = [
    {
      label: 'Purchase cost',
      value: c.purchaseCost,
      note: 'Equipment at the plant gate, indexed to the current CE.',
    },
    {
      label: 'Installed equipment cost',
      value: c.installedEquipmentCost,
      note: 'Bare-module factors: piping, foundations, instrumentation, erection.',
    },
    {
      label: 'Direct permanent investment (DPI)',
      value: c.DPI,
      note: 'Installed cost plus warehouse, site development and additional piping.',
    },
    {
      label: 'Total depreciable capital (TDC)',
      value: c.TDC,
      note: 'DPI plus field expenses, construction, contingency and other indirects.',
    },
    { label: 'Fixed capital investment (FCI)', value: c.FCI, note: 'What gets depreciated.' },
    {
      label: 'Working capital',
      value: c.workingCapital,
      note: 'Recovered in the final year of the venture, and it shows in the cash flow.',
    },
    { label: 'Total capital investment (TCI)', value: c.TCI, note: 'What has to be raised.' },
  ];
  const max = Math.max(...rows.map((x) => x.value));
  return (
    <div className="divide-y divide-line">
      {rows.map((row) => (
        <div key={row.label} className="py-2 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 items-baseline">
          <div className="min-w-0">
            <div className="text-body">{row.label}</div>
            <div className="text-caption text-ink-soft">{row.note}</div>
          </div>
          <div className="font-num text-body whitespace-nowrap">${USD(row.value)}</div>
          <div className="col-span-2 h-1 rounded-full bg-ink-soft/15 overflow-hidden">
            <div
              className="h-full rounded-full bg-accent/70"
              style={{ width: `${max > 0 ? (row.value / max) * 100 : 0}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function EquipmentTable({ r }: { r: PlantResult }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-caption" data-table="equipment">
        <thead>
          <tr className="border-b border-line text-ink-soft">
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Unit</th>
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Type</th>
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Area</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Purchase</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Installed</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Power</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Duty</th>
            <th className="text-left py-1.5 whitespace-nowrap">Correlation</th>
          </tr>
        </thead>
        <tbody>
          {r.units.map((u) => {
            const duty = u.heatUtilities.reduce((t, h) => t + h.duty, 0);
            const isOpen = open === u.ID;
            return [
              <tr
                key={u.ID}
                className={cx(
                  'border-b border-line/60 cursor-pointer hover:bg-ink-soft/[0.04]',
                  isOpen && 'bg-accent-wash',
                )}
                onClick={() => setOpen(isOpen ? null : u.ID)}
              >
                <td className="py-1.5 pr-3 font-num whitespace-nowrap">{u.ID}</td>
                <td className="py-1.5 pr-3 whitespace-nowrap">{u.line}</td>
                <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">{u.areaName}</td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">${USD(u.purchaseCost)}</td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">${USD(u.installedCost)}</td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
                  {u.powerKW ? `${fmt(u.powerKW)} kW` : '—'}
                </td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
                  {duty ? `${fmt(duty / 1000)} MJ h⁻¹` : '—'}
                </td>
                <td className="py-1.5 whitespace-nowrap">
                  <span
                    className={cx(
                      'chip',
                      u.costSource === 'biosteam' ? 'text-ink-soft' : 'chip-warn',
                    )}
                  >
                    {u.costSource === 'biosteam' ? 'bioSTEAM' : 'authored'}
                  </span>
                  {u.warnings.length > 0 && (
                    <AlertTriangle size={12} className="inline ml-1.5 text-signal-warn" aria-label="has a design warning" />
                  )}
                </td>
              </tr>,
              isOpen ? (
                <tr key={`${u.ID}-detail`} className="border-b border-line/60 bg-surface-1/40">
                  <td colSpan={8} className="py-2 px-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
                          Design results
                        </div>
                        <dl className="grid grid-cols-[1fr_auto] gap-x-3">
                          {Object.entries(u.design).map(([k, d]) => (
                            <div key={k} className="contents">
                              <dt className="text-caption text-ink-soft py-0.5">{k}</dt>
                              <dd className="text-caption font-num text-right py-0.5 whitespace-nowrap">
                                {fmt(d.value)} {d.units}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                      <div>
                        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
                          Purchase cost items
                        </div>
                        <dl className="grid grid-cols-[1fr_auto] gap-x-3">
                          {Object.entries(u.purchaseCosts).map(([k, v]) => (
                            <div key={k} className="contents">
                              <dt className="text-caption text-ink-soft py-0.5">
                                {k}
                                {(u.parallel[k] ?? 1) > 1 && (
                                  <span className="font-num"> ×{u.parallel[k]}</span>
                                )}
                                <span className="text-ink-soft/70"> · F<sub>BM</sub> {u.F_BM[k]}</span>
                              </dt>
                              <dd className="text-caption font-num text-right py-0.5 whitespace-nowrap">
                                ${USD(v * (u.parallel[k] ?? 1))}
                              </dd>
                            </div>
                          ))}
                        </dl>
                        {u.costBasis && (
                          <p className="text-caption text-ink-soft mt-2">{u.costBasis}</p>
                        )}
                      </div>
                    </div>
                    {u.warnings.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {u.warnings.map((w) => (
                          <li key={w} className="text-caption text-signal-warn flex gap-1.5">
                            <AlertTriangle size={12} className="mt-[3px] shrink-0" />
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-line font-medium">
            <td className="py-1.5 pr-3" colSpan={3}>
              {r.units.length} units
            </td>
            <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
              ${USD(r.capital.purchaseCost)}
            </td>
            <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
              ${USD(r.capital.installedEquipmentCost)}
            </td>
            <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
              {fmt(r.process.powerConsumption)} kW
            </td>
            <td className="py-1.5 pr-3" />
            <td className="py-1.5" />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function CashflowTable({ r }: { r: PlantResult }) {
  const cols: { key: keyof PlantResult['cashflow'][number] & string; label: string }[] = [
    { key: 'depreciableCapital', label: 'Depreciable capital' },
    { key: 'fixedCapitalInvestment', label: 'Fixed capital' },
    { key: 'workingCapital', label: 'Working capital' },
    { key: 'depreciation', label: 'Depreciation' },
    { key: 'loan', label: 'Loan' },
    { key: 'loanPayment', label: 'Loan payment' },
    { key: 'annualOperatingCost', label: 'Operating cost' },
    { key: 'sales', label: 'Sales' },
    { key: 'tax', label: 'Tax' },
    { key: 'netEarnings', label: 'Net earnings' },
    { key: 'cashFlow', label: 'Cash flow' },
    { key: 'discountFactor', label: 'Discount factor' },
    { key: 'NPV', label: 'NPV' },
    { key: 'cumulativeNPV', label: 'Cumulative NPV' },
  ];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-caption" data-table="cashflow">
        <caption className="sr-only">
          Discounted cash flow by year, in millions of US dollars except the discount factor.
        </caption>
        <thead>
          <tr className="border-b border-line text-ink-soft">
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Year</th>
            {cols.map((c) => (
              <th key={c.key} className="text-right py-1.5 pr-3 whitespace-nowrap">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {r.cashflow.map((row) => (
            <tr key={row.year} className="border-b border-line/50">
              <td className="py-1 pr-3 font-num whitespace-nowrap">{row.year}</td>
              {cols.map((c) => {
                const v = row[c.key];
                const scaledV = c.key === 'discountFactor' ? v : v / 1e6;
                return (
                  <td
                    key={c.key}
                    className={cx(
                      'py-1 pr-3 text-right font-num whitespace-nowrap',
                      scaledV < 0 && 'text-signal-error',
                    )}
                  >
                    {c.key === 'discountFactor' ? scaledV.toFixed(3) : fmt(scaledV)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Tornado({ u }: { u: PlantUncertainty }) {
  const theme = useChartTheme();
  const rows = u.spearman;
  if (rows.length === 0) return null;
  const max = Math.max(...rows.map((x) => Math.abs(x.rho)), 0.1);
  return (
    <div>
      <div className="space-y-1.5">
        {rows.map((row) => {
          const w = (Math.abs(row.rho) / max) * 50;
          return (
            <div key={row.key} className="grid grid-cols-[11rem_1fr_3.5rem] items-center gap-2">
              <div className="text-caption truncate" title={row.name}>
                {row.field ? (
                  <a className="text-accent hover:underline" href={href(`/ledger/p/${row.field}`)}>
                    {row.name}
                  </a>
                ) : (
                  row.name
                )}
              </div>
              <div className="relative h-4">
                <div className="absolute inset-y-0 left-1/2 w-px bg-line" />
                <div
                  className={cx(
                    'absolute inset-y-[3px] rounded-[2px]',
                    row.rho < 0 ? 'bg-signal-info' : 'bg-signal-warn',
                  )}
                  style={
                    row.rho < 0
                      ? { right: '50%', width: `${w}%` }
                      : { left: '50%', width: `${w}%` }
                  }
                />
              </div>
              <div className="text-caption font-num text-right">{row.rho.toFixed(2)}</div>
            </div>
          );
        })}
      </div>
      <p className="text-caption text-ink-soft mt-2">
        Spearman rank correlation against MSP over {u.n} Latin hypercube samples, seed{' '}
        <span className="font-num">{u.seed}</span>. A negative coefficient means raising the
        parameter lowers the price.
      </p>
      <ChartTable
        headers={['Parameter', 'Spearman ρ']}
        rows={rows.map((r) => [r.name, r.rho.toFixed(3)])}
      />
      <span className="sr-only">{theme.grid ? '' : ''}</span>
    </div>
  );
}

export default function Plant({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const toast = useStore((s) => s.toast);
  const theme = useChartTheme();
  const seriesColor = useSeriesColor();

  const [uncertainty, setUncertainty] = useState<PlantUncertainty | null>(null);
  const [running, setRunning] = useState(false);

  const spec = scenario ? FLOWSHEET_BY_MODEL[scenario.modelId] : undefined;

  const result = useMemo(() => {
    if (!scenario) return null;
    try {
      return evaluatePlantCached(scenario.modelId, scenario.point);
    } catch {
      return null;
    }
  }, [scenario]);

  if (!scenario || !spec) {
    return (
      <>
        <PageHeader eyebrow="fermOS" title="Plant" />
        <Card>
          <EmptyState
            icon={<Factory size={22} />}
            title="No such scenario"
            body="Session state resets on refresh, so a link minted in an earlier session can point at a scenario that no longer exists."
            action={<Button onClick={() => navigate('/fermos')}>Back to scenarios</Button>}
          />
        </Card>
      </>
    );
  }

  if (!result) {
    return (
      <>
        <PageHeader
          eyebrow="fermOS · bioSTEAM"
          title={`${scenario.name} — plant`}
          subtitle="The flowsheet, the capital, and the cash flow behind the headline price."
        />
        <Card>
          <EmptyState
            icon={<AlertTriangle size={22} />}
            title="The flowsheet did not build at this point"
            body="A parameter combination the sizing routines cannot resolve — usually a titer low enough that the vessel count runs away. The scenario workspace clamps to the modelled range; this screen does not, so it fails visibly instead of quietly."
            action={
              <Button onClick={() => navigate(`/fermos/s/${scenario.id}`)}>
                Back to the workspace
              </Button>
            }
          />
        </Card>
      </>
    );
  }

  const split = result.costSourceSplit;
  const authoredShare = split.biosteam + split.authored > 0
    ? split.authored / (split.biosteam + split.authored)
    : 0;

  const areaData = result.areas.map((a) => ({
    name: a.name,
    installed: a.installedCost / 1e6,
    power: a.powerKW,
  }));

  const runUncertainty = () => {
    setRunning(true);
    window.setTimeout(() => {
      try {
        setUncertainty(runPlantUncertainty(spec, scenario.point, { n: 200 }));
      } catch {
        toast({ text: 'The uncertainty run could not build a plant at any sample.', kind: 'error' });
      }
      setRunning(false);
    }, scaled(900));
  };

  return (
    <>
      <PageHeader
        eyebrow="fermOS · bioSTEAM"
        title={`${scenario.name} — plant`}
        subtitle="Sized equipment, a capital ladder and a discounted cash flow. The price below is the one that drives net present value to zero, not a sum of assumed cost lines."
        actions={
          <>
            <Button onClick={() => navigate(`/fermos/s/${scenario.id}`)}>
              <Gauge size={14} /> Scenario workspace
            </Button>
            <Button
              onClick={() =>
                exportCSV(
                  `openferment-${scenario.id}-equipment.csv`,
                  ['Unit', 'Type', 'Area', 'Purchase USD', 'Installed USD', 'Power kW', 'Correlation'],
                  result.units.map((u) => [
                    u.ID,
                    u.line,
                    u.areaName,
                    u.purchaseCost.toFixed(0),
                    u.installedCost.toFixed(0),
                    u.powerKW.toFixed(2),
                    u.costSource,
                  ]),
                )
              }
            >
              <Download size={14} /> Export equipment
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-4">
        <Card className="p-4">
          <Stat
            label="Minimum selling price"
            value={USD(result.msp)}
            unit="USD kg⁻¹"
            sub={
              <>
                solved at NPV = 0, residual{' '}
                <span className="font-num">{result.npvResidual.toExponential(1)}</span> USD
              </>
            }
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Total capital investment"
            value={USD(result.capital.TCI / 1e6)}
            unit="M USD"
            sub={`${result.units.length} unit operations`}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Annual production"
            value={USD(result.annualProduction / 1000)}
            unit="t yr⁻¹"
            sub={`${fmt(result.process.powerConsumption)} kW connected`}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Annual operating cost"
            value={USD(result.operating.AOC / 1e6)}
            unit="M USD yr⁻¹"
            sub={`${USD(result.operating.materialCost / 1e6)}M feedstock`}
          />
        </Card>
      </div>

      <div className="mb-4 space-y-3">
        <Callout kind="info" title="What is doing the arithmetic here">
          Equipment sizing, purchase-cost correlations, bare-module installation factors, CEPCI
          indexing, utility prices, MACRS depreciation and the discounted cash flow are ported from{' '}
          <span className="font-serif">bioSTEAM</span> v2.53.11 and keep its constants and its
          argument order.{' '}
          <span className="font-medium">ThermoSTEAM is not ported.</span> There is no property
          package, no vapour–liquid equilibrium and no recycle convergence: streams are lumped
          component mass flows. A separation whose cost turns on a relative volatility cannot be
          sized by this code, and this plant does not contain one.
        </Callout>
        {authoredShare > 0.01 && (
          <Callout
            kind={authoredShare > 0.4 ? 'warn' : 'info'}
            title={`${(authoredShare * 100).toFixed(0)}% of installed capital uses a correlation written here, not bioSTEAM's`}
          >
            bioSTEAM ships no photobioreactor, no pulsed-electric-field disruptor and no membrane
            skid, because nobody has published a costing correlation into it for them. Those units
            are costed by correlations written for this app and marked{' '}
            <span className="chip chip-warn">authored</span> in the equipment table. The split is{' '}
            <span className="font-num">${USD(split.biosteam / 1e6)}M</span> bioSTEAM against{' '}
            <span className="font-num">${USD(split.authored / 1e6)}M</span> authored.
          </Callout>
        )}
        {result.warnings.length > 0 && (
          <Callout kind="warn" title={`${result.warnings.length} design warnings`}>
            <ul className="space-y-0.5 mt-1">
              {result.warnings.map((w) => (
                <li key={`${w.ID}-${w.message}`}>
                  <span className="font-num">{w.ID}</span> — {w.message}
                </li>
              ))}
            </ul>
          </Callout>
        )}
      </div>

      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="How capital is built up">
              Purchase cost is the equipment at the plant gate. Bare-module factors carry it to
              installed cost — piping, foundations, instrumentation, erection — which is bioSTEAM&rsquo;s
              default rather than a single Lang factor. The indirect steps that follow are the NREL
              structure every published fermentation TEA uses.
            </Explain>
          }
        >
          Capital
        </SectionTitle>
        <div className="grid gap-3 lg:grid-cols-2">
          <Card className="p-4">
            <CapitalLadder r={result} />
          </Card>
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Installed cost by process area
            </div>
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={areaData} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid stroke={theme.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    stroke={theme.axis}
                    tick={{ fontSize: 11 }}
                    label={{ value: 'M USD', position: 'insideBottom', offset: -2, fontSize: 11 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke={theme.axis}
                    tick={{ fontSize: 11 }}
                    width={110}
                  />
                  <Tooltip {...tooltipStyle(theme)} formatter={(v: number) => `${v.toFixed(2)} M USD`} />
                  <RBar dataKey="installed" radius={[0, 2, 2, 0]}>
                    {areaData.map((_, i) => (
                      <Cell key={i} fill={seriesColor(i)} />
                    ))}
                  </RBar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ChartTable
              headers={['Area', 'Installed (M USD)', 'Power (kW)']}
              rows={areaData.map((a) => [a.name, a.installed.toFixed(2), a.power.toFixed(1)])}
            />
          </Card>
        </div>
      </section>

      <section className="mb-6">
        <SectionTitle right={<span className="text-caption text-ink-soft">Click a row for design results</span>}>
          Equipment
        </SectionTitle>
        <Card className="p-4">
          <EquipmentTable r={result} />
        </Card>
      </section>

      <section className="mb-6">
        <SectionTitle>Operating cost and process demand</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">Annual cost</div>
            <dl className="grid grid-cols-[1fr_auto] gap-x-3 text-body">
              {[
                ['Feedstock and media', result.operating.materialCost],
                ['Utilities', result.operating.utilityCost],
                ['Variable operating cost', result.operating.VOC],
                ['Fixed operating cost', result.operating.FOC],
                ['Annual operating cost', result.operating.AOC],
              ].map(([label, v], i) => (
                <div key={label as string} className={cx('contents', i === 4 && 'font-medium')}>
                  <dt className="py-0.5 text-ink-soft">{label}</dt>
                  <dd className="py-0.5 text-right font-num whitespace-nowrap">
                    ${USD((v as number) / 1e6)}M
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Process demand
            </div>
            <dl className="grid grid-cols-[1fr_auto] gap-x-3 text-body">
              <dt className="py-0.5 text-ink-soft">Heating duty</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                {fmt(result.process.heatingDuty / 1000)} MJ h⁻¹
              </dd>
              <dt className="py-0.5 text-ink-soft">Cooling duty</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                {fmt(result.process.coolingDuty / 1000)} MJ h⁻¹
              </dd>
              <dt className="py-0.5 text-ink-soft">Electricity</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                {fmt(result.process.powerConsumption)} kW
              </dd>
              <dt className="py-0.5 text-ink-soft">Power cost</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                ${USD(result.operating.powerCost / 1e6)}M yr⁻¹
              </dd>
            </dl>
          </Card>
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              What this flowsheet does not model
            </div>
            <ul className="space-y-1.5">
              {spec.limitations.map((l) => (
                <li key={l} className="text-caption text-ink-soft flex gap-1.5">
                  <Waves size={12} className="mt-[3px] shrink-0" />
                  <span>{l}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </section>

      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="Reading a cash flow">
              Everything is in millions of dollars except the discount factor. The first rows are
              construction, when capital goes out and nothing comes in. Working capital appears the
              year before start-up and comes back in the last year, which is why the final cash flow
              jumps. Cumulative NPV reaches zero at exactly the selling price above — that is what
              solving for the price means.
            </Explain>
          }
        >
          Discounted cash flow
        </SectionTitle>
        <Card className="p-4">
          <CashflowTable r={result} />
        </Card>
      </section>

      <section className="mb-6">
        <SectionTitle
          right={
            <Button onClick={runUncertainty} disabled={running}>
              <Boxes size={14} /> {running ? 'Sampling…' : uncertainty ? 'Re-run' : 'Run 200 samples'}
            </Button>
          }
        >
          Uncertainty
        </SectionTitle>
        <Card className="p-4">
          {!uncertainty && !running && (
            <EmptyState
              icon={<Boxes size={22} />}
              title="No Monte Carlo has been run in this session"
              body="Two hundred Latin hypercube samples, each one a full flowsheet build and a fresh discounted cash flow. It takes a moment, and it is real work rather than a loading animation — which is why it is a button and not something that happens on arrival."
              action={<Button variant="primary" onClick={runUncertainty}>Run the samples</Button>}
            />
          )}
          {running && (
            <div className="py-10 text-center text-ink-soft text-body">
              Building {200} plants and solving {200} cash flows…
            </div>
          )}
          {uncertainty && !running && (
            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
                  Minimum selling price
                </div>
                <div className="flex items-baseline gap-3 flex-wrap">
                  <div className="font-num text-display leading-tight">
                    {USD(uncertainty.percentiles.p50)}
                  </div>
                  <div className="text-body text-ink-soft">
                    median, USD kg⁻¹
                  </div>
                </div>
                <div className="mt-3 space-y-1 text-caption">
                  {(
                    [
                      ['5th percentile', uncertainty.percentiles.p5],
                      ['25th percentile', uncertainty.percentiles.p25],
                      ['75th percentile', uncertainty.percentiles.p75],
                      ['95th percentile', uncertainty.percentiles.p95],
                    ] as const
                  ).map(([label, v]) => (
                    <div key={label} className="flex justify-between gap-4">
                      <span className="text-ink-soft">{label}</span>
                      <span className="font-num">${USD(v)}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3" style={{ height: 140 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={uncertainty.histogram} margin={{ left: 0, right: 8 }}>
                      <CartesianGrid stroke={theme.grid} vertical={false} />
                      <XAxis
                        dataKey="x"
                        stroke={theme.axis}
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v: number) => fmt(v)}
                      />
                      <YAxis stroke={theme.axis} tick={{ fontSize: 10 }} width={28} />
                      <Tooltip {...tooltipStyle(theme)} />
                      <ReferenceLine x={result.msp} stroke={theme.axis} strokeDasharray="3 3" />
                      <RBar dataKey="n" fill={seriesColor(0)} radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {uncertainty.failed > 0 && (
                  <p className="text-caption text-signal-warn mt-2">
                    <span className="font-num">{uncertainty.failed}</span> of{' '}
                    <span className="font-num">{uncertainty.requested}</span> samples failed to build
                    a plant. They are counted rather than dropped, because a corner of the design
                    space that cannot be sized is a finding about the design.
                  </p>
                )}
              </div>
              <div>
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
                  What moves the price
                </div>
                <Tornado u={uncertainty} />
              </div>
            </div>
          )}
        </Card>
      </section>

      <section className="mb-6">
        <SectionTitle>Parameters and where they come from</SectionTitle>
        <Card className="p-4">
          <div className="divide-y divide-line">
            {spec.parameters.map((p) => (
              <div key={p.key} className="py-2.5 grid gap-x-4 gap-y-1 sm:grid-cols-[14rem_1fr]">
                <div>
                  <div className="text-body">{p.label}</div>
                  <div className="font-num text-caption text-ink-soft">
                    {fmt(scenario.point[p.key] ?? p.baseline)} {p.unit}{' '}
                    <span className="text-ink-soft/70">
                      ({fmt(p.bounds[0])}–{fmt(p.bounds[1])})
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-caption text-ink-soft">{p.note}</p>
                  <p className="text-caption mt-1">
                    {p.basis.kind === 'record' ? (
                      <>
                        <span className="chip">record</span>{' '}
                        <a
                          className="text-accent hover:underline font-num"
                          href={href(`/ledger/records?record=${p.basis.recordId}`)}
                        >
                          {p.basis.recordId}
                        </a>
                      </>
                    ) : p.basis.kind === 'model' ? (
                      <>
                        <span className="chip">modelling choice</span>{' '}
                        <span className="text-ink-soft">{p.basis.justification}</span>
                      </>
                    ) : (
                      <>
                        <span className="chip chip-error">unsourced</span>{' '}
                        <span className="text-signal-error">
                          No record and no declared justification. This is a defect.
                        </span>
                      </>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <div className="text-caption text-ink-soft flex items-start gap-1.5 mb-8">
        <Wallet size={12} className="mt-[3px] shrink-0" />
        <span>
          bioSTEAM: Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S.{' '}
          <span className="font-serif italic">
            BioSTEAM: A Fast and Flexible Platform for the Design, Simulation, and Techno-Economic
            Analysis of Biorefineries under Uncertainty
          </span>
          . ACS Sustainable Chem. Eng. 2020, 8 (8), 3302–3310. Distributed under the University of
          Illinois/NCSA Open Source License.
        </span>
      </div>
    </>
  );
}
