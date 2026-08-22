// The plant (fermOS · bioSTEAM).
//
// Build the flowsheet at the scenario's point, size it, and show what it is:
// the equipment, the streams, the duties, the powder it makes and what the
// model does not cover. Nothing here is authored. If the equipment table is
// empty the plant did not build, and the screen says that rather than showing a
// plausible number with nothing behind it.
//
// ── WHAT LEFT, AND WHY ────────────────────────────────────────────────────
//
// This screen used to be 1,162 lines and it used to hold the price: the NPV = 0
// solve, the capital ladder, the discounted cash flow, the cost index, the
// financial basis and the Monte Carlo. Every one of those is Proforma's by the
// architecture's own division — `EconomicsAdapter` against `ProcessAdapter`,
// `proforma_mcp` against `fermos_mcp` — and they now live at
// `/proforma/price/:scenarioId`.
//
// The rule that settled every ambiguous band: fermOS shows what a unit IS,
// Proforma shows what it COSTS. So the equipment table below carries area,
// power and duty, and Proforma's carries purchase and installed cost. The
// `Correlation` chip stays on both, because whose model sized a unit is a fact
// about the unit and not about its price.
//
// ── THE SEAM STRIP IS NOT A CONVENIENCE ───────────────────────────────────
//
// Splitting the screens without splitting the solve is the whole trick. Editing
// a vessel's residence time here re-sizes it, re-costs it and moves the price —
// and that property is the single best demonstration in this build that a
// process change IS an economic change. Deleting the price from this screen
// would have deleted the demonstration, so the price stays as a QUOTATION:
// Proforma's number, named as Proforma's, linking to where it is argued.
import { useState } from 'react';
import { AlertTriangle, ArrowUpRight, Download, Factory, Gauge, Waves } from 'lucide-react';

import { href, navigate } from '@/router';
import { fmt } from '@/engine/units';
import { usePlantSolve } from '@/lib/use-plant';
import { corpusBasis } from '@/lib/basis-corpus';
import { BasisLine } from '@/components/Basis';
import { USD } from '@/lib/money';
import { exportCSV } from '@/lib/csv';
import { Flowsheet, FlowsheetLegend } from '@/components/Flowsheet';
import { StreamTable } from '@/components/StreamTable';
import { UnitSpecEditor, DesignResultsTable } from '@/components/UnitSpecEditor';
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
const EYEBROW = partEyebrow('fermos', 'corpus');

/**
 * The equipment list, as equipment.
 *
 * No purchase cost and no installed cost: those are Proforma's, on the price
 * screen, in a table with these same rows. What is here is what the unit is —
 * where it sits in the process, what it draws, what it exchanges, and whose
 * correlation designed it.
 */
function EquipmentTable({ r }: { r: PlantResult }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-caption" data-table="equipment">
        <caption className="sr-only">
          Unit operations with their process area, electrical load and heat duty.
        </caption>
        <thead>
          <tr className="border-b border-line text-ink-soft">
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Unit</th>
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Type</th>
            <th className="text-left py-1.5 pr-3 whitespace-nowrap">Area</th>
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
                    <AlertTriangle
                      size={12}
                      className="inline ml-1.5 text-signal-warn"
                      aria-label="has a design warning"
                    />
                  )}
                </td>
              </tr>,
              isOpen ? (
                <tr key={`${u.ID}-detail`} className="border-b border-line/60 bg-surface-1/40">
                  <td colSpan={6} className="py-2 px-3">
                    <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
                      Design results
                    </div>
                    <dl className="grid grid-cols-[1fr_auto] gap-x-3 max-w-prose">
                      {Object.entries(u.design).map(([k, d]) => (
                        <div key={k} className="contents">
                          <dt className="text-caption text-ink-soft py-0.5">{k}</dt>
                          <dd className="text-caption font-num text-right py-0.5 whitespace-nowrap">
                            {fmt(d.value)} {d.units}
                          </dd>
                        </div>
                      ))}
                    </dl>
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

export default function Plant({ scenarioId }: { scenarioId: string }) {
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const { scenario, spec, result, overrides, editCount, setUnitSpec, resetUnit } =
    usePlantSolve(scenarioId);

  if (!scenario || !spec) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title="No such scenario" />
        <EmptyState
          icon={<Factory size={28} />}
          title="No such scenario"
          body="Session state resets on refresh, so a link minted in an earlier session can point at a scenario that no longer exists."
          action={<Button onClick={() => navigate('/fermos')}>Scenarios</Button>}
        />
      </>
    );
  }

  if (!result) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title={`${scenario.name} — plant`} />
        <EmptyState
          icon={<Factory size={28} />}
          title="The flowsheet did not build at this point"
          body="Usually a titer low enough that the vessel count runs away. The scenario workspace clamps to the modelled range; this screen does not, so it fails visibly instead of quietly."
          action={
            <Button onClick={() => navigate(`/fermos/s/${scenario.id}`)}>Scenario workspace</Button>
          }
        />
      </>
    );
  }

  const selectedUnitResult = selectedUnit
    ? (result.units.find((u) => u.ID === selectedUnit) ?? null)
    : null;

  // Quoted, not computed: the same basis Proforma renders in full, summarised to
  // one line so a reader can see what frame the price is in without leaving the
  // process screen.
  const basis = corpusBasis(scenario.modelId, { tea: overrides.tea, CE: overrides.CE });

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
        title={`${scenario.name} — plant`}
        subtitle="Sized equipment, the streams between it, and what the model does not cover. This is the process; the price it supports is Proforma's."
        actions={
          <>
            <Button onClick={() => navigate(`/fermos/s/${scenario.id}`)}>
              <Gauge size={14} /> Scenario workspace
            </Button>
            <Button
              onClick={() =>
                exportCSV(
                  `openferment-${scenario.id}-equipment.csv`,
                  ['Unit', 'Type', 'Area', 'Power kW', 'Duty kJ h⁻¹', 'Correlation'],
                  result.units.map((u) => [
                    u.ID,
                    u.line,
                    u.areaName,
                    u.powerKW.toFixed(2),
                    u.heatUtilities.reduce((t, h) => t + h.duty, 0).toFixed(0),
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

      {/* ── The seam ──────────────────────────────────────────────────────
          Proforma's number, on fermOS's screen, named as Proforma's. Editing
          any attribute below moves it, which is this build's clearest
          demonstration that a process change is an economic change — and the
          reason the price was quoted here rather than deleted when the
          economics moved. */}
      <a
        href={href(`/proforma/price/${scenario.id}`)}
        className="card block p-4 mb-4 motion-colors hover:border-accent/45 hover:bg-accent-wash/40"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <div>
            <div className="text-caption uppercase tracking-wide text-ink-soft">
              Priced by Proforma
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="font-num text-page-title leading-none">{USD(result.msp)}</span>
              <span className="text-body text-ink-soft">USD kg⁻¹</span>
            </div>
            <div className="text-caption text-ink-soft mt-1">solved at NPV = 0 against</div>
            {basis && <BasisLine basis={basis} className="mt-0.5" />}
          </div>
          <div className="text-caption text-ink-soft max-w-prose flex items-start gap-1.5">
            <span>
              fermOS sizes the plant; Proforma discounts it. Change an attribute below and this
              number moves — the two screens are one solve, not two copies.
              {editCount > 0 && (
                <>
                  {' '}
                  <span className="text-signal-warn">
                    {editCount} attribute{editCount === 1 ? '' : 's'} edited, so this is not the
                    scenario&rsquo;s declared plant.
                  </span>
                </>
              )}
            </span>
            <ArrowUpRight size={14} className="shrink-0 mt-[2px]" aria-hidden />
          </div>
        </div>
      </a>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-4">
        <Card className="p-4">
          <Stat
            label="Product purity"
            value={`${(result.product.purity * 100).toFixed(0)}%`}
            unit=""
            sub={
              result.product.purity < 0.8
                ? 'the price above is for this powder, not for an isolate'
                : `${spec.productLabel}`
            }
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
            label="Heating duty"
            value={fmt(result.process.heatingDuty / 1000)}
            unit="MJ h⁻¹"
            sub={`${result.units.length} unit operations`}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Cooling duty"
            value={fmt(result.process.coolingDuty / 1000)}
            unit="MJ h⁻¹"
            sub="what the plant has to reject"
          />
        </Card>
      </div>

      {/* THE FLOWSHEET IS THE SPINE, so it comes first.

          It used to sit seven hundred pixels down, beneath two large prose
          callouts — which put an explanation of the arithmetic above the thing
          the arithmetic was performed on. The diagram is what this part IS: the
          one artifact on any screen in this build that says process
          engineering. What bioSTEAM does and does not model is a caveat on it,
          and a caveat reads after its subject. */}
      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="What a flowsheet diagram is">
              The same picture bioSTEAM draws from{' '}
              <span className="font-num">system.diagram()</span>. It is read off the graph that ran
              the mass balance rather than drawn beside it, so it cannot disagree with the model:
              every arrow is a stream in the table below, and every box is a row in the equipment
              table. Click a unit to open its attributes.
            </Explain>
          }
        >
          Flowsheet
        </SectionTitle>
        <Card className="p-4">
          <Flowsheet
            graph={result.graph}
            streams={result.streams}
            onSelectUnit={(id) => setSelectedUnit(id)}
            selectedUnit={selectedUnit}
          />
          <div className="mt-3">
            <FlowsheetLegend graph={result.graph} />
          </div>
        </Card>
        {selectedUnitResult && (
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <Card className="p-4">
              <UnitSpecEditor
                unit={selectedUnitResult}
                specs={selectedUnitResult.specs}
                overrides={overrides.units?.[selectedUnitResult.ID] ?? {}}
                onChange={(key, value) => setUnitSpec(selectedUnitResult.ID, key, value)}
                onReset={() => resetUnit(selectedUnitResult.ID)}
              />
            </Card>
            <Card className="p-4">
              <DesignResultsTable unit={selectedUnitResult} />
            </Card>
          </div>
        )}
        {!selectedUnitResult && (
          <p className="text-caption text-ink-soft mt-2">
            Select a unit to see how it was sized and to change the attributes bioSTEAM would let
            you set on it — residence time, working volume, vessel material, exchanger type, split.
            Every one of them re-sizes the equipment, re-costs it and re-solves the cash flow.
          </p>
        )}
      </section>

      <div className="mb-4 space-y-3">
        <Callout kind="info" title="What is doing the arithmetic here">
          Equipment sizing, purchase-cost correlations, bare-module installation factors, CEPCI
          indexing, utility prices, MACRS depreciation and the discounted cash flow are ported from{' '}
          <span className="font-serif">bioSTEAM</span> v2.53.11 and keep its constants and its
          argument order. <span className="font-medium">ThermoSTEAM is not ported.</span> There is no
          property package, no vapour–liquid equilibrium and no recycle convergence: streams are
          lumped component mass flows. A separation whose cost turns on a relative volatility cannot
          be sized by this code, and this plant does not contain one.
        </Callout>
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
          right={<span className="text-caption text-ink-soft">Click a row for design results</span>}
        >
          Equipment
        </SectionTitle>
        <Card className="p-4">
          <EquipmentTable r={result} />
        </Card>
        <p className="text-caption text-ink-soft mt-2">
          What each of these costs is on{' '}
          <a className="text-accent hover:underline" href={href(`/proforma/price/${scenario.id}`)}>
            Proforma&rsquo;s price screen
          </a>{' '}
          — the same rows, keyed on purchase and installed cost instead of on size.
        </p>
      </section>

      <section className="mb-6">
        <SectionTitle
          right={
            <Explain label="Reading a stream table">
              Streams in columns and properties in rows, which is the orientation bioSTEAM's
              <span className="font-num"> report.stream_table</span> uses and the reason it looks the
              way it does. A feed has no source and a product no sink. Composition is by mass, and a
              component absent from a stream shows a dash rather than a zero — absent and zero are
              different things.
            </Explain>
          }
        >
          Streams
        </SectionTitle>
        <Card className="p-4">
          <StreamTable streams={result.streams} onSelectUnit={(id) => setSelectedUnit(id)} />
        </Card>
      </section>

      <section className="mb-6">
        <SectionTitle>What this flowsheet does not model</SectionTitle>
        <Card className="p-4">
          <ul className="space-y-1.5 max-w-prose">
            {spec.limitations.map((l) => (
              <li key={l} className="text-caption text-ink-soft flex gap-1.5">
                <Waves size={12} className="mt-[3px] shrink-0" />
                <span>{l}</span>
              </li>
            ))}
          </ul>
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
    </>
  );
}
