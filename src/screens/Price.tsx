// The price behind the plant (Proforma · bioSTEAM).
//
// ── WHY THIS SCREEN EXISTS ────────────────────────────────────────────────
//
// openFerment separates fermOS from Proforma at four layers — the Pydantic
// schema, the adapter seam (`ProcessAdapter` against `EconomicsAdapter`), two
// shipped MCP servers with their own manifests, and the two charters. Until
// this file existed the UI was the only layer where that separation did not
// exist: `/fermos/s/:id/plant` rendered the NPV = 0 solve, the capital ladder,
// the cash flow, the cost index and the Monte Carlo under fermOS's name, and
// Proforma — whose charter is "techno-economics against an explicit regional
// and temporal basis" — had no corpus surface at all.
//
// This is the first `partEyebrow('proforma', 'corpus')` in the build.
//
// ── THE RULE THAT SETTLED EVERY AMBIGUOUS BAND ────────────────────────────
//
// fermOS shows what a unit IS; Proforma shows what it COSTS. So the equipment
// table appears on both screens and they are not the same table: fermOS's is
// keyed on size, duty and how the unit was designed, and this one is keyed on
// purchase cost, installed cost and whose correlation charged it.
//
// `src/engine/plant.ts` is titled "Where a plant becomes a price" and
// `PlantResult` splits along that sentence — `units`/`streams`/`graph`/
// `product` on one side, `msp`/`capital`/`cashflow`/`operating` on the other.
// This screen renders the second half.
//
// ── ONE SOLVE, TWO SCREENS ────────────────────────────────────────────────
//
// Both screens read `usePlantSolve`, so an equipment edit made on fermOS is the
// same edit Proforma quotes. Two copies of the overrides would let the two
// screens disagree about one plant, and the disagreement would read as a
// modelling result rather than as a bug.
import { useState } from 'react';
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
import { Boxes, Download, Factory, Wallet } from 'lucide-react';

import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { fmt } from '@/engine/units';
import { usePlantSolve } from '@/lib/use-plant';
import { corpusBasis } from '@/lib/basis-corpus';
import { BasisLine, BasisPanel } from '@/components/Basis';
import { usePlantUncertainty, type PlantUncertainty } from '@/lib/use-uncertainty';
import { money, USD } from '@/lib/money';
import { exportCSV } from '@/lib/csv';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import { ChartTable } from '@/components/ChartTable';
import { SettingsPanel, UtilityAgentTable } from '@/components/BiosteamSettings';
import { partEyebrow } from '@/data/parts';
import type { PlantResult } from '@/engine/plant';
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

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('proforma', 'corpus');

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
        <div
          key={row.label}
          className="py-2 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 items-baseline"
        >
          <div className="min-w-0">
            <div className="text-body">{row.label}</div>
            <div className="text-caption text-ink-soft">{row.note}</div>
          </div>
          <div className="font-num text-body whitespace-nowrap">{money(row.value)}</div>
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

/**
 * The equipment list, costed.
 *
 * fermOS's table on `/fermos/s/:id/plant` carries the same rows keyed on size
 * and duty; this one carries what each unit costs and whose correlation said
 * so. The unit id links back, because a reader who wants to know why a
 * centrifuge costs what it does needs the design results, and those are
 * fermOS's.
 */
function CostedEquipment({ r, scenarioId }: { r: PlantResult; scenarioId: string }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-caption" data-table="equipment-cost">
        <caption className="sr-only">
          Purchase and installed cost per unit operation, with the source of each cost correlation.
        </caption>
        <thead>
          <tr className="border-b border-line text-ink-soft">
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Unit</th>
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Area</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Purchase</th>
            <th className="text-right py-1.5 pr-3 whitespace-nowrap">Installed</th>
            <th className="text-left py-1.5 whitespace-nowrap">Correlation</th>
          </tr>
        </thead>
        <tbody>
          {r.units.map((u) => {
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
                <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">{u.areaName}</td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
                  {money(u.purchaseCost)}
                </td>
                <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
                  {money(u.installedCost)}
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
                </td>
              </tr>,
              isOpen ? (
                <tr key={`${u.ID}-detail`} className="border-b border-line/60 bg-surface-1/40">
                  <td colSpan={5} className="py-2 px-3">
                    <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
                      Purchase cost items
                    </div>
                    <dl className="grid grid-cols-[1fr_auto] gap-x-3 max-w-prose">
                      {Object.entries(u.purchaseCosts).map(([k, v]) => (
                        <div key={k} className="contents">
                          <dt className="text-caption text-ink-soft py-0.5">
                            {k}
                            {(u.parallel[k] ?? 1) > 1 && (
                              <span className="font-num"> ×{u.parallel[k]}</span>
                            )}
                            <span className="text-ink-soft/70">
                              {' '}
                              · F<sub>BM</sub> {u.F_BM[k]}
                            </span>
                          </dt>
                          <dd className="text-caption font-num text-right py-0.5 whitespace-nowrap">
                            {money(v * (u.parallel[k] ?? 1))}
                          </dd>
                        </div>
                      ))}
                    </dl>
                    {u.costBasis && (
                      <p className="text-caption text-ink-soft mt-2 max-w-prose">{u.costBasis}</p>
                    )}
                    <p className="text-caption mt-2">
                      <a
                        className="text-accent hover:underline"
                        href={href(`/fermos/s/${scenarioId}/plant`)}
                      >
                        How this unit was sized →
                      </a>{' '}
                      <span className="text-ink-soft">
                        fermOS holds the design results; this screen holds the money.
                      </span>
                    </p>
                  </td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-line font-medium">
            <td className="py-1.5 pr-3" colSpan={2}>
              {r.units.length} units
            </td>
            <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
              {money(r.capital.purchaseCost)}
            </td>
            <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
              {money(r.capital.installedEquipmentCost)}
            </td>
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
                    row.rho < 0 ? { right: '50%', width: `${w}%` } : { left: '50%', width: `${w}%` }
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
    </div>
  );
}

export default function Price({ scenarioId }: { scenarioId: string }) {
  const toast = useStore((s) => s.toast);
  const theme = useChartTheme();
  const seriesColor = useSeriesColor();

  const {
    scenario,
    spec,
    result,
    baseline,
    editCount,
    settings,
    settingsDefaults,
    applySettings,
    overrides,
    restore,
    restoreBasis,
  } = usePlantSolve(scenarioId);

  const { uncertainty, running, run: runUncertainty } = usePlantUncertainty(scenarioId);

  if (!scenario || !spec) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title="No such scenario" />
        <EmptyState
          icon={<Factory size={28} />}
          title="No such scenario"
          body="Session state resets on refresh, so a link minted in an earlier session can point at a scenario that no longer exists."
          action={<Button onClick={() => navigate('/proforma')}>Proforma</Button>}
        />
      </>
    );
  }

  if (!result) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title={`${scenario.name} — price`} />
        <EmptyState
          icon={<Factory size={28} />}
          title="There is no price, because the flowsheet did not build"
          body="A price is solved from a plant. With no plant there is nothing to discount, and a number here would be arithmetic over an absence."
          action={
            <Button onClick={() => navigate(`/fermos/s/${scenario.id}/plant`)}>
              Open the plant in fermOS
            </Button>
          }
        />
      </>
    );
  }

  // The basis the reader is actually looking at, not the one the corpus
  // declares — the settings panel below IS the basis, so a stamp that ignored
  // an edit would describe a plant nobody is on.
  const basis = corpusBasis(scenario.modelId, { tea: overrides.tea, CE: overrides.CE });

  const split = result.costSourceSplit;
  const authoredShare =
    split.biosteam + split.authored > 0 ? split.authored / (split.biosteam + split.authored) : 0;

  const areaData = result.areas.map((a) => ({
    name: a.name,
    installed: a.installedCost / 1e6,
    power: a.powerKW,
  }));

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
        title={`${scenario.name} — price`}
        subtitle="The price that drives net present value to zero, and the capital, cash flow and basis it is solved against. fermOS sizes the plant; this screen costs it."
        actions={
          <>
            <Button onClick={() => navigate(`/fermos/s/${scenario.id}/plant`)}>
              <Factory size={14} /> The plant in fermOS
            </Button>
            <Button
              onClick={() =>
                exportCSV(
                  `openferment-${scenario.id}-cost.csv`,
                  ['Unit', 'Area', 'Purchase USD', 'Installed USD', 'Correlation'],
                  result.units.map((u) => [
                    u.ID,
                    u.areaName,
                    u.purchaseCost.toFixed(0),
                    u.installedCost.toFixed(0),
                    u.costSource,
                  ]),
                )
              }
            >
              <Download size={14} /> Export costs
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
          {basis && <BasisLine basis={basis} className="mt-2 pt-2 border-t border-line" />}
        </Card>
        <Card className="p-4">
          <Stat
            label="Total capital investment"
            value={money(result.capital.TCI).replace(/^\$/, '')}
            unit="USD"
            sub={`${result.units.length} unit operations`}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Annual operating cost"
            value={money(result.operating.AOC).replace(/^\$/, '')}
            unit="USD yr⁻¹"
            sub={`${money(result.operating.materialCost)} feedstock`}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Annual production"
            value={USD(result.annualProduction / 1000)}
            unit="t yr⁻¹"
            sub={`${(result.product.purity * 100).toFixed(0)}% pure — the price is for this powder`}
          />
        </Card>
      </div>

      <div className="mb-4 space-y-3">
        {editCount > 0 && (
          <Callout
            kind="warn"
            title={`${editCount} attribute${editCount === 1 ? '' : 's'} edited — this price is not the scenario's`}
          >
            The scenario grid, the workspace waterfall and the comparison screen are all still
            running the flowsheet as the corpus declares it. This price and the plant in fermOS both
            reflect your edits — they are one solve.{' '}
            {baseline && Number.isFinite(baseline.msp) && (
              <>
                The declared plant prices at{' '}
                <span className="font-num">{money(baseline.msp)}</span> per kg against{' '}
                <span className="font-num">{money(result.msp)}</span> here.{' '}
              </>
            )}
            <button
              className="text-accent hover:underline"
              onClick={() => {
                restore();
                toast({ text: 'Plant restored to the scenario’s declared flowsheet', kind: 'info' });
              }}
            >
              Restore the declared plant
            </button>
            .
          </Callout>
        )}
        {authoredShare > 0.01 && (
          <Callout
            kind={authoredShare > 0.4 ? 'warn' : 'info'}
            title={`${(authoredShare * 100).toFixed(0)}% of installed capital uses a correlation written here, not bioSTEAM's`}
          >
            bioSTEAM ships no photobioreactor, no pulsed-electric-field disruptor and no membrane
            skid, because nobody has published a costing correlation into it for them. Those units
            are costed by correlations written for this app and marked{' '}
            <span className="chip chip-warn">authored</span> in the equipment table. The split is{' '}
            <span className="font-num">{money(split.biosteam)}</span> bioSTEAM against{' '}
            <span className="font-num">{money(split.authored)}</span> authored.
          </Callout>
        )}
      </div>

      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="How capital is built up">
              Purchase cost is the equipment at the plant gate. Bare-module factors carry it to
              installed cost — piping, foundations, instrumentation, erection — which is
              bioSTEAM&rsquo;s default rather than a single Lang factor. The indirect steps that
              follow are the NREL structure every published fermentation TEA uses.
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
                <BarChart
                  data={areaData}
                  layout="vertical"
                  margin={{ left: 8, right: 16, bottom: 18 }}
                >
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
                  <Tooltip
                    {...tooltipStyle(theme)}
                    formatter={(v: number) => `${v.toFixed(2)} M USD`}
                  />
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
        <SectionTitle
          right={<span className="text-caption text-ink-soft">Click a row for its cost items</span>}
        >
          What the equipment costs
        </SectionTitle>
        <Card className="p-4">
          <CostedEquipment r={result} scenarioId={scenario.id} />
        </Card>
      </section>

      <section className="mb-6">
        <SectionTitle>Operating cost</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Annual cost
            </div>
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
                    {money(v as number)}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              What the plant draws
            </div>
            <dl className="grid grid-cols-[1fr_auto] gap-x-3 text-body">
              <dt className="py-0.5 text-ink-soft">Electricity</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                {fmt(result.process.powerConsumption)} kW
              </dd>
              <dt className="py-0.5 text-ink-soft">Power cost</dt>
              <dd className="py-0.5 text-right font-num whitespace-nowrap">
                {money(result.operating.powerCost)} yr⁻¹
              </dd>
            </dl>
            <p className="text-caption text-ink-soft mt-2">
              The duties these are drawn against — heating, cooling, the mass balance they come out
              of — are fermOS&rsquo;s, on{' '}
              <a className="text-accent hover:underline" href={href(`/fermos/s/${scenario.id}/plant`)}>
                the plant screen
              </a>
              .
            </p>
          </Card>
        </div>
      </section>

      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="Why these are shared">
              All three plants are priced on the same discount rate, the same tax rate and the same
              cost index, because three plants compared on three financial bases is not a
              comparison. Change them here and this price moves — and so does the quotation fermOS
              shows beside the plant, because the two screens are one solve. The scenario grid and
              the comparison screen keep the declared basis.
            </Explain>
          }
        >
          The basis
        </SectionTitle>
        <div className="space-y-3">
          {basis && <BasisPanel basis={basis} />}
          <Card className="p-4">
            {settings && settingsDefaults && (
              <SettingsPanel
                value={settings}
                defaults={settingsDefaults}
                onChange={applySettings}
                onReset={restoreBasis}
              />
            )}
          </Card>
          <Card className="p-4">
            <UtilityAgentTable />
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
              <Boxes size={14} />{' '}
              {running ? 'Sampling…' : uncertainty ? 'Re-run' : 'Run 200 samples'}
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
              action={
                <Button variant="primary" onClick={runUncertainty}>
                  Run the samples
                </Button>
              }
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
                  <div className="text-body text-ink-soft">median, USD kg⁻¹</div>
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
                      <span className="font-num">{money(v)}</span>
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
                    <span className="font-num">{uncertainty.requested}</span> samples failed to
                    build a plant. They are counted rather than dropped, because a corner of the
                    design space that cannot be sized is a finding about the design.
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
