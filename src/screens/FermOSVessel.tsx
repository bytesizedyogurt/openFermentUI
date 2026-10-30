// fermOS → Vessel (OF-BLD-020 §4.2, D7, D14; Appendix 2 §C).
//
//     What vessel does this batch need, and does it get the oxygen it takes?
//
// A person picks a kept simulation (fermOS → Simulate keeps one) or, for an
// anaerobic vessel, a kept kinetic fit. The service designs the vessel with
// BioSTEAM's own classes in its Proforma worker: an AeratedBioreactor, a
// stirred tank or a bubble column, for a simulation that takes up oxygen
// (Yx/o set), else the NREL batch fermenter. Every design parameter is the
// parameter panel's, over the scope `fermos:vessel:<artifact id>`, in groups
// Scale, Vessel, Schedule, Aeration, Agitation, Heat: each with its source
// (BioSTEAM's own default read from its code, the simulation's harvest hour
// and oxygen uptake, a stated convention, or a named person's assumption),
// and the vessel type is the panel's choice parameter (`design`). A plant
// scale or one vessel's batch volume is a person's alone, and the page says
// above **Design** which one is needed.
//
// THE SCREEN COMPUTES NOTHING. Every number on it came from the service's
// answer or a person's override: the design table is BioSTEAM's objects read
// by the worker, each row with where BioSTEAM put it; the oxygen balance is
// the simulated uptake against what the vessel transfers, with the hours it
// falls short as the service found them; the heat line sets BioSTEAM's duty
// beside the convention's estimate from the oxygen consumed, labelled; the
// cost line names BioSTEAM's plant cost index. No numeric control is written
// here (E.1‴): the panel is the only way to type a number.
//
// **Price this in Proforma** (OF-BLD-020 §6.1) opens New scenario on
// `custom_train_v1`, a vessel and a train priced, with this design chosen as
// its fermenter; the dialog lists the train runs pureOS keeps and, when it
// keeps none, says how one is made (pureOS → New train). Nothing is made
// until a person chooses a train run and makes the scenario.
//
// OF-BLD-020 §4.R (the Phase 4 review). The chooser opens on a choice that
// is no source when none is chosen, so a kept fit can be chosen when no
// simulation is kept; the line above Design names only the scales the panel
// offers (an anaerobic vessel takes a plant scale alone); a design in flight
// is dropped, and a shown one cleared, when the source or the vessel type
// changes; and the heat line says how BioSTEAM found its duty (the heats of
// formation, or a person's heat per oxygen times the oxygen the vessel
// consumed) and what the cross-check rests on, in the service's words.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Gauge } from 'lucide-react';
import type { FermosFitInfo, ParamScope, SimulationSummary, VesselDesign } from '@/data/types';
import { overridesFor, useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { Button, Callout, EmptyState, SectionTitle } from '@/components/ui';
import { NewScenarioDialog } from '@/components/NewScenarioDialog';
import { ParameterPanel } from '@/components/ParameterPanel';
import { ProvenanceBadge } from '@/components/Provenance';
import { OxygenBalance } from '@/components/figures';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { paramScope } from '@/lib/params';
import { COMPOSITE_FLOWSHEET, fermosFits, proformaStatus, stamp } from '@/lib/proforma';
import {
  FermosDown,
  FermosRefused,
  VESSEL_FIT_FLOWSHEET,
  designVessel,
  fermosSimulations,
  scaleOf,
  vesselRequest,
  vesselScope,
  vesselTypeOf,
} from '@/lib/fermos';

/** The panel's groups, in Appendix 2 §C's order. */
export const VESSEL_GROUPS = ['Scale', 'Vessel', 'Schedule', 'Aeration', 'Agitation', 'Heat'];

/** What Price this in Proforma does, said beside it (OF-BLD-020 §6.1). */
export const PRICE_WORDS =
  'Proforma prices this design as the fermenter of custom_train_v1, followed by a train pureOS ran on its beer, with the TEA the shelf flowsheets use. Choose the train run in New scenario; pureOS → New train builds and runs one when none is kept.';

const problemOf = (e: unknown) =>
  e instanceof FermosDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof FermosRefused ? e.message : String(e);

/** One value in the row's own words: a number formatted, a word as it is. */
const shown = (v: number | string | boolean | null | undefined) =>
  v == null ? '—' : typeof v === 'number' ? fmt(v, 4) : typeof v === 'boolean' ? (v ? 'yes' : 'no') : v;

function Chooser({
  simulations,
  fits,
  chosen,
}: {
  simulations: SimulationSummary[];
  fits: FermosFitInfo[];
  chosen: { kind: 'simulation' | 'fit'; id: string } | null;
}) {
  const value = chosen ? `${chosen.kind}:${chosen.id}` : '';
  const known = simulations.some((s) => `simulation:${s.artifactId}` === value) || fits.some((f) => `fit:${f.artifactId}` === value);
  return (
    <label className="text-caption text-ink-soft">
      <span className="block mb-0.5">Design the vessel for</span>
      <select
        className="input min-h-[44px]"
        aria-label="Design the vessel for"
        data-testid="vessel-source"
        value={value}
        onChange={(e) => {
          const [kind, id] = e.target.value.split(':');
          navigate(`/fermos/vessel?${kind}=${encodeURIComponent(id)}`, { replace: true });
        }}
      >
        {/* Nothing chosen: a first choice that is no source, so choosing the first listed one is a change (§4.R). */}
        {!chosen && (
          <option value="" disabled data-testid="vessel-source-none">
            Choose a kept simulation or fit
          </option>
        )}
        {!known && chosen && <option value={value}>{`${chosen.kind} ${chosen.id}`}</option>}
        {simulations.length > 0 && (
          <optgroup label="Kept simulations">
            {simulations.map((s) => (
              <option key={s.artifactId} value={`simulation:${s.artifactId}`}>
                {`${s.title} · ${s.artifactId}${s.product ? ` · ${s.product}` : ''}${s.sugar ? ` on ${s.sugar}` : ''}`}
              </option>
            ))}
          </optgroup>
        )}
        {fits.length > 0 && (
          <optgroup label="Kept fits (an anaerobic vessel)">
            {fits.map((f) => (
              <option key={f.artifactId} value={`fit:${f.artifactId}`}>
                {`${f.tool === 'growth_forecast' ? 'forecast' : 'kinetic fit'} · ${f.artifactId}`}
              </option>
            ))}
          </optgroup>
        )}
      </select>
    </label>
  );
}

function DesignTable({ design }: { design: VesselDesign }) {
  const headers = ['What', 'Value', 'Unit', 'Where BioSTEAM put it'];
  const rows = design.design.map((r) => [r.label, shown(r.value), r.unit, r.readFrom]);
  return (
    <section aria-label="The design" className="space-y-1">
      <SectionTitle
        right={
          <Button onClick={() => exportCSV(`vessel-${design.artifactId}.csv`, headers, design.design.map((r) => [r.label, r.value, r.unit, r.readFrom]))}>
            CSV
          </Button>
        }
      >
        The design, as BioSTEAM sized it
      </SectionTitle>
      <div className="overflow-x-auto">
        <table className="w-full text-body" data-testid="vessel-design-table">
          <thead>
            <tr className="text-caption text-ink-soft text-left">
              {headers.map((h) => (
                <th key={h} className="py-1 pr-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r[0]}-${i}`} className="border-t border-line/60" data-testid="vessel-design-row" data-label={String(r[0])}>
                <td className="py-1 pr-2">{r[0]}</td>
                <td className="py-1 pr-2 font-num">{r[1]}</td>
                <td className="py-1 pr-2 font-num text-caption">{r[2]}</td>
                <td className="py-1 text-caption text-ink-soft">{r[3]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Result({ design }: { design: VesselDesign }) {
  const [pricing, setPricing] = useState(false);
  const ox = design.oxygen;
  const kind = design.vesselType ? ` · ${design.vesselType.replace('-', ' ')}` : '';
  return (
    <div className="space-y-4 mt-4" data-testid="vessel-result" data-artifact={design.artifactId} data-unit-class={design.unitClass}>
      <p className="text-body flex flex-wrap items-center gap-2">
        <span className="font-medium">
          BioSTEAM&rsquo;s {design.unitClass}
          {kind}
        </span>
        <ProvenanceBadge p={design.provenance} compact />
        <span className="text-caption text-ink-soft">
          kept as{' '}
          <a className="font-num hover:text-accent" href={href(`/biorepo/artifacts/${design.artifactId}`)}>
            {design.artifactId}
          </a>{' '}
          on {stamp(design.createdAt)}, designed for {design.sourceTool} <span className="font-num">{design.source}</span>
        </span>
      </p>

      <DesignTable design={design} />

      {ox ? (
        <OxygenBalance
          title="Does the vessel transfer the oxygen the batch takes up?"
          t={ox.t}
          our={ox.our}
          otr={ox.otr}
          unit={ox.unit}
          short={ox.short}
          method={ox.method}
          aerated={ox.aerated}
          provenance={design.provenance}
          basis={design.evidence.basis}
          csvName={`oxygen-${design.artifactId}`}
          notes={[
            ox.kLa != null
              ? `kLa achieved ${fmt(ox.kLa, 4)} ${ox.kLaUnit} by ${ox.method ?? 'BioSTEAM’s correlation'}; the peak uptake would need ${ox.kLaNeededAtPeak != null ? fmt(ox.kLaNeededAtPeak, 4) : '—'} ${ox.kLaUnit}. The air was sized for the simulation’s ${ox.oxygenBasis ?? 'uptake'}.`
              : 'BioSTEAM designed no aeration for this uptake, so every hour the simulation takes up oxygen is short.',
          ]}
        />
      ) : (
        <Callout kind="info" title="Anaerobic: no compressor, no oxygen balance">
          <p className="text-ink" data-testid="vessel-anaerobic">
            {design.oxygenNote}
          </p>
        </Callout>
      )}

      <section aria-label="Heat" className="text-body" data-testid="vessel-heat" data-method={design.heat.method ?? ''}>
        <SectionTitle>Heat</SectionTitle>
        <p>
          BioSTEAM&rsquo;s duty: <span className="font-num">{fmt(design.heat.bst, 4)} {design.heat.unit}</span>
          {design.heat.dutyNote ? `, ${design.heat.dutyNote}.` : '.'}
          {design.heat.convention != null ? (
            <>
              {' '}
              Beside it, a convention&rsquo;s estimate from the oxygen{' '}
              {design.heat.oxygenKmolPerH != null ? 'the simulation took up' : 'consumed'}:{' '}
              <span className="font-num">
                {fmt(design.heat.convention, 4)} {design.heat.unit}
              </span>{' '}
              (a convention, a cross-check and nothing more).
            </>
          ) : null}
        </p>
        <p className="text-caption text-ink-soft mt-0.5">{design.heat.conventionNote}</p>
      </section>

      <section aria-label="Cost" className="text-body" data-testid="vessel-cost">
        <SectionTitle>Cost</SectionTitle>
        <p>
          Purchase <span className="font-num">{fmt(design.cost.purchase, 4)} USD</span>, installed{' '}
          <span className="font-num">{fmt(design.cost.installed, 4)} USD</span>, at BioSTEAM&rsquo;s plant cost index{' '}
          <span className="font-num">{fmt(design.cost.costIndex, 4)}</span>
          {design.cost.costIndexYear != null ? <> (its default, of {design.cost.costIndexYear})</> : null}; utilities{' '}
          <span className="font-num">{fmt(design.cost.utility, 4)} USD/hr</span>.
        </p>
        <p className="text-caption text-ink-soft mt-0.5">{design.cost.note}</p>
      </section>

      {design.flags.length > 0 && (
        <ul className="text-caption text-signal-warn space-y-0.5" data-testid="vessel-flags">
          {design.flags.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}

      <details data-testid="vessel-basis">
        <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">
          The basis: every input of the design, with its source
        </summary>
        <ul className="mt-1 space-y-0.5 text-caption">
          {design.evidence.basis.inputs.map((i, n) => (
            <li key={`${i.name}-${n}`} className="text-ink-soft">
              {i.name}: <span className="font-num text-ink">{String(i.value)}</span> {i.unit} — {i.source.kind}
              {i.source.by ? ` by ${i.source.by}` : ''}
              {i.source.id ? ` ${i.source.id}` : ''}
              {i.source.note ? ` (${i.source.note})` : ''}
            </li>
          ))}
        </ul>
      </details>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => setPricing(true)} className="min-h-[44px]" data-testid="vessel-price">
          Price this in Proforma
        </Button>
        <p className="text-caption text-ink-soft max-w-3xl" data-testid="vessel-price-words">
          {PRICE_WORDS}
        </p>
      </div>
      <NewScenarioDialog
        key={design.artifactId}
        open={pricing}
        onClose={() => setPricing(false)}
        initialFlowsheet={COMPOSITE_FLOWSHEET}
        initialVessel={design.artifactId}
      />
    </div>
  );
}

export default function FermOSVessel() {
  const route = useRoute();
  const [simulations, setSimulations] = useState<SimulationSummary[] | null>(null);
  const [fits, setFits] = useState<FermosFitInfo[]>([]);
  const [listProblem, setListProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setListProblem(null);
    fermosSimulations(ctrl.signal)
      .then(setSimulations)
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setSimulations([]);
        setListProblem(problemOf(e));
      });
    // The fits list also carries kept simulations (OF-BLD-020 §3.3: a
    // simulation feeds Proforma as a fit does); a simulation is chosen above
    // as itself, so the fits offered here are the kinetic fits and forecasts.
    fermosFits(VESSEL_FIT_FLOWSHEET, ctrl.signal)
      .then((all) => setFits(all.filter((f) => f.tool !== 'fermos.simulation')))
      .catch(() => !ctrl.signal.aborted && setFits([]));
    return () => ctrl.abort();
  }, []);

  const askedSim = route.query.get('simulation');
  const askedFit = route.query.get('fit');
  const chosen = useMemo<{ kind: 'simulation' | 'fit'; id: string } | null>(() => {
    if (askedSim) return { kind: 'simulation', id: askedSim };
    if (askedFit) return { kind: 'fit', id: askedFit };
    const first = simulations?.[0];
    return first ? { kind: 'simulation', id: first.artifactId } : null;
  }, [askedSim, askedFit, simulations]);

  const scope = chosen ? vesselScope(chosen.id) : '';
  const overrides = useStore(overridesFor(scope));
  const vesselType = vesselTypeOf(overrides);
  const ask = useMemo(() => ({ vesselType }), [vesselType]);
  const [panel, setPanel] = useState<ParamScope | null>(null);
  const [panelProblem, setPanelProblem] = useState<string | null>(null);
  // A design, or a refusal, belongs to the source and the vessel type it was asked for (§4.R).
  const asked = `${scope}|${vesselType ?? ''}`;
  const [design, setDesign] = useState<{ asked: string; design: VesselDesign } | null>(null);
  const [refused, setRefused] = useState<{ asked: string; words: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef<AbortController | null>(null);

  // §8.R (finding 15): the first read of a vessel's parameters on a service
  // just started starts BioSTEAM's simulator (lib/params.ts), about half a
  // minute; while it is in hand the page says so, as Proforma's status line
  // does, and holds Design and the Scale line until the panel answers.
  const [simulator, setSimulator] = useState<string | null>(null);
  useEffect(() => {
    setPanel(null);
    setPanelProblem(null);
    setSimulator(null);
    if (!scope) return;
    const ctrl = new AbortController();
    paramScope(scope, ask, ctrl.signal)
      .then(setPanel)
      .catch((e: unknown) => !ctrl.signal.aborted && setPanelProblem(problemOf(e)));
    proformaStatus(ctrl.signal)
      .then((st) => !ctrl.signal.aborted && setSimulator(st.status))
      .catch(() => undefined);
    return () => ctrl.abort();
  }, [scope, ask]);

  // A design belongs to the source and the vessel type it was made for: a
  // change of either drops the one in flight and clears the one shown (§4.R).
  useEffect(() => {
    inFlight.current?.abort();
    inFlight.current = null;
    setBusy(false);
    setDesign(null);
    setRefused(null);
  }, [asked]);
  useEffect(() => () => inFlight.current?.abort(), []);

  const scale = scaleOf(overrides);
  // The scales the panel offers: an anaerobic vessel takes a plant scale alone (§4.R).
  const offersBatch = panel ? panel.specs.some((sp) => sp.key === 'batch_volume') : null;
  const run = () => {
    if (!chosen) return;
    inFlight.current?.abort();
    const ctrl = new AbortController();
    inFlight.current = ctrl;
    const mine = asked;
    setBusy(true);
    setRefused(null);
    designVessel(vesselRequest(chosen.kind === 'simulation' ? { simulation: chosen.id } : { fit: chosen.id }, overrides), ctrl.signal)
      .then((d) => {
        if (ctrl.signal.aborted) return;
        setDesign({ asked: mine, design: d });
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setDesign(null);
        setRefused({ asked: mine, words: problemOf(e) });
      })
      .finally(() => {
        if (inFlight.current !== ctrl) return;
        inFlight.current = null;
        setBusy(false);
      });
  };
  const shownDesign = design && design.asked === asked ? design.design : null;
  const shownRefusal = refused && refused.asked === asked ? refused.words : null;

  return (
    <div className="space-y-4" data-testid="fermos-vessel">
      <p className="text-body text-ink-soft max-w-3xl">
        The vessel a kept simulation needs, designed by BioSTEAM: its AeratedBioreactor, a stirred tank or a bubble column, for a culture
        that takes up oxygen, else the NREL batch fermenter. Every design parameter is below with its source; a value you type is your
        named assumption, and the design&rsquo;s basis names it.
      </p>

      {simulations === null ? (
        <p className="text-caption text-ink-soft">Asking the service for its kept simulations…</p>
      ) : (
        <div className="flex flex-wrap items-end gap-3">
          {(simulations.length > 0 || fits.length > 0 || chosen) && <Chooser simulations={simulations} fits={fits} chosen={chosen} />}
        </div>
      )}
      {listProblem && <Callout kind="warn">{listProblem}</Callout>}

      {simulations !== null && !chosen && !listProblem && fits.length > 0 && (
        <p className="text-body text-ink-soft" data-testid="vessel-choose">
          No simulation is kept yet. Choose a kept fit above to design the anaerobic vessel it needs, or simulate a batch in{' '}
          <a href={href('/fermos/simulate')} className="text-accent hover:underline">
            fermOS → Simulate
          </a>
          .
        </p>
      )}
      {simulations !== null && !chosen && !listProblem && fits.length === 0 && (
        <div data-testid="vessel-empty">
          <EmptyState
            icon={<Gauge size={28} />}
            title="No simulation kept yet"
            body={
              <>
                A vessel is designed for a batch fermOS kept. Simulate one in{' '}
                <a href={href('/fermos/simulate')} className="text-accent hover:underline">
                  fermOS → Simulate
                </a>
                , or fit a deposited run in{' '}
                <a href={href('/fermos')} className="text-accent hover:underline">
                  fermOS → Fits
                </a>{' '}
                for an anaerobic vessel; it appears here to design.
              </>
            }
          />
        </div>
      )}

      {chosen && (
        <>
          {panelProblem && <Callout kind="warn">{panelProblem}</Callout>}
          {!panel && !panelProblem && (
            <p className="text-caption text-ink-soft" data-testid="vessel-panel-asking" data-simulator={simulator ?? ''}>
              {simulator === 'cold' || simulator === 'starting'
                ? 'BioSTEAM’s simulator is starting: the first read of a vessel’s parameters starts it, which takes about half a minute on a service just started. The parameters appear here when it answers.'
                : 'Asking BioSTEAM for this vessel’s parameters…'}
            </p>
          )}
          {panel && (
            <section aria-labelledby="vessel-panel-title">
              <SectionTitle>
                <span id="vessel-panel-title">{panel.title}</span>
              </SectionTitle>
              <ParameterPanel scope={scope} data={panel} request={ask} groups={VESSEL_GROUPS} />
            </section>
          )}
          {panel && (
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-body" data-testid="vessel-scale" data-scale={scale}>
              {scale === 'none'
                ? offersBatch === null
                  ? 'A scale is needed, and none is set: type one under Scale, as your named assumption.'
                  : offersBatch
                    ? 'One of plant scale and batch volume is needed, and neither is set: type one under Scale, as your named assumption.'
                    : 'A plant scale is needed, and none is set: type one under Scale, as your named assumption.'
                : scale === 'both'
                  ? 'Give plant scale or batch volume, not both: one sets how much broth the vessels take.'
                  : 'The scale is set, as your named assumption.'}
            </p>
            <Button onClick={run} disabled={busy} className="min-h-[44px]" data-testid="vessel-design">
              {busy ? 'Designing…' : 'Design'}
            </Button>
          </div>
          )}
          {shownRefusal && (
            <Callout kind="warn">
              <p data-testid="vessel-refused">{shownRefusal}</p>
            </Callout>
          )}
          {shownDesign && <Result design={shownDesign} />}
        </>
      )}
    </div>
  );
}
