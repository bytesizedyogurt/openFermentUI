// fermOS → Simulate (OF-BLD-020 §3.3; D1, D2, D5, D6, D14, E.1‴).
//
// WHAT IT DOES. A person chooses a model family (kinetics.py's, each shown
// with its equations in plain Unicode and one line saying what it is; the
// light socket is listed and cannot be chosen, in its own words), the strain
// whose records bind (or every strain on file), the product and the
// sugar, and where the parameters start from: the records, a fit fermOS
// keeps, or a kept simulation. The service binds every parameter the family
// declares (fermos.bind_parameters): a fit a person chose, the records
// through the aggregate gate, a kept simulation, a named person's value, a
// stated convention. The parameter panel shows each with its source; what
// still waits is said above Simulate, which stays disabled until nothing
// does and says what. Simulate posts the family scope's overrides; the
// service integrates on scipy and keeps one `fermos.simulation` artifact.
//
// D1, AMENDED. A fit takes only a deposition's measurements. A simulation
// may take records, fits, artifacts, a person's assumptions and stated
// conventions, each labelled; its provenance is basis_provenance over all of
// them, so one with any typed value is `demo`. A simulation never pretends
// to be a measurement: its curves are computed lines (TimeCourse), and the
// card above the figure says what it was built from.
//
// THE RESULT. The time course (every state; the volume where it varies; the
// oxygen uptake rate on the second axis), the end state (final titre, yield
// achieved, productivity, the hour the sugar runs out; for a chemostat its
// steady state too: X, S, P and D·P, or washout, whether washout is a second
// stable state, and which one the run reached, each the service's number,
// OF-BLD-020 §3.R findings 1 and 17), the ceiling card (Yp/s
// beside each geneOS ceiling the service read for the strain's host models:
// flagged when above, never clamped, D11), the parameters with their sources
// and intervals, and the basis. From there: Fit this family to a deposition
// (Fits, with the family chosen), Design the vessel (fermOS → Vessel), Use as
// a train's inlet (OF-BLD-020 §6.2: pureOS → Builder opens a new train whose
// inlet is this simulation's broth at harvest, which the service reads from
// the kept series), and Send to Proforma (the OF-BLD-019 §5.1 bridge, which
// reads a simulation's end state as it reads a fit's forecast).
//
// THE SCREEN COMPUTES NOTHING. Every number here is the service's answer or
// the person's override; the CSVs export the artifact's own numbers. No
// numeric control is rendered here: every parameter is the panel's (E.1‴).
import { useEffect, useMemo, useState } from 'react';
import type { FamilyInfo, FermosBinding, FermosFitInfo, ParameterSpec, ParameterValue, ParamScope, SimulationResult, SimulationSummary, SteadyState } from '@/data/types';
import { overridesFor, useStore } from '@/store';
import { href, useRoute } from '@/router';
import { Button, Callout, SectionTitle } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ParameterPanel } from '@/components/ParameterPanel';
import { SourceChip, shown } from '@/components/ParameterRow';
import { TimeCourse } from '@/components/figures';
import { CARBON_SOURCES } from '@/data/vocabulary';
import { PRODUCT_WORDS, productWords } from '@/lib/geneos';
import { paramScope } from '@/lib/params';
import { FIT_TOOL_WORDS, fermosFits, proformaShelf } from '@/lib/proforma';
import { exportCSV } from '@/lib/csv';
import { fmt } from '@/engine/units';
import {
  FermosDown,
  FermosRefused,
  FIT_LENGTH,
  UNTIL_RUN_OUT,
  familyScope,
  fermosBind,
  fermosFamilies,
  fermosSimulate,
  fermosSimulations,
  isFitFamily,
  paramAskOf,
  timeCourseOf,
  vesselPath,
  type SimulateAsk,
} from '@/lib/fermos';
import { builderInletPath } from '@/lib/pureos';
import { SendToProforma } from './FermOSForecast';

/** The panel's groups, in the order Appendix 2 §A lists them. */
export const SIMULATE_GROUPS = ['Growth', 'Product', 'Substrate', 'Inhibition', 'Oxygen', 'Feed', 'Dilution', 'Storage', 'Start values', 'Run length'];
/** How long the screen waits after a change before asking what waits. */
const BIND_AFTER_MS = 350;
type Start = 'records' | 'fit' | 'simulation';

const problemOf = (e: unknown) =>
  e instanceof FermosDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof FermosRefused ? e.message : e instanceof Error ? e.message : String(e);

/** Each origin in words, for the card that says what a simulation was built from. */
function originWords(v: ParameterValue): string {
  if (v.overriddenBy) return `values typed by ${v.overriddenBy}`;
  switch (v.origin) {
    case 'record':
      return 'records';
    case 'fit':
      return 'a fit';
    case 'artifact':
      return 'a kept artifact';
    case 'simulation':
      return 'a kept simulation';
    case 'convention':
      return 'stated conventions';
    case 'library-default':
      return "the library's defaults";
    default:
      return 'nothing yet';
  }
}

function FamilyChooser({ families, chosen, onChoose }: { families: FamilyInfo[]; chosen: string; onChoose: (id: string) => void }) {
  return (
    <div role="radiogroup" aria-label="Model family" className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="simulate-families">
      {families.map((f) => {
        const on = f.id === chosen;
        return (
          <div key={f.id} className={`card p-3 ${on ? 'ring-2 ring-accent' : ''}`} data-testid="simulate-family" data-family={f.id} data-socket={f.socket ? 'true' : 'false'}>
            <button
              type="button"
              role="radio"
              aria-checked={on}
              disabled={f.socket}
              onClick={() => onChoose(f.id)}
              className="text-left w-full min-h-[44px] disabled:cursor-not-allowed disabled:opacity-70"
            >
              <span className="font-medium text-body">{f.title}</span> <span className="font-num text-caption text-ink-soft">{f.id}</span>
              <span className="block text-caption text-ink-soft">{f.what}</span>
            </button>
            <details className="mt-1" open={on}>
              <summary className="text-caption text-ink-soft cursor-pointer hover:text-accent">Equations</summary>
              <pre className="text-caption whitespace-pre-wrap font-num mt-1" data-testid="simulate-equations">
                {f.equations}
              </pre>
            </details>
          </div>
        );
      })}
    </div>
  );
}

function BuiltFrom({ r }: { r: SimulationResult }) {
  const groups = new Map<string, string[]>();
  for (const v of [...r.parameters, ...r.start]) {
    const w = originWords(v);
    groups.set(w, [...(groups.get(w) ?? []), v.key]);
  }
  return (
    <div className="card p-3" data-testid="simulation-built-from" data-provenance={r.provenance}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">
          A simulation of {r.title} ({r.family}), not a measurement
        </span>
        <ProvenanceBadge p={r.provenance} />
      </div>
      <p className="text-caption text-ink-soft mt-1">
        Every value below was computed from the sources its parameters name, and its provenance follows the weakest of them
        {r.provenance === 'demo' ? ': a value a person typed makes it modeled' : ''}. Kept as{' '}
        <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${r.artifactId}`)}>
          {r.artifactId}
        </a>
        .
      </p>
      <ul className="text-caption mt-1 space-y-0.5">
        {[...groups.entries()].map(([w, keys]) => (
          <li key={w}>
            <span className="text-ink-soft">From {w}:</span> <span className="font-num">{keys.join(', ')}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** A chemostat's steady state: the service's X, S, P and D·P, or washout, in its own words. */
function SteadyStateCard({ ss, units }: { ss: SteadyState; units: Record<string, string> }) {
  const conc = units.P ?? units.X ?? '';
  const rows: [string, string, number | null, string][] = [
    ['X', 'Cells', ss.X, units.X ?? conc],
    ['S', 'Sugar', ss.S, units.S ?? conc],
    ['P', 'Product', ss.P, conc],
    ['productivity', 'Productivity, D·P', ss.productivity, `${conc} h⁻¹`],
  ];
  return (
    <div
      className="mt-2 border-t border-line/60 pt-2"
      data-testid="simulation-steady"
      data-washout={ss.washout ? 'true' : 'false'}
      data-bistable={ss.bistable ? 'true' : 'false'}
      data-reached={ss.reached ?? ''}
    >
      <h4 className={`font-medium text-body ${ss.washout ? 'text-signal-warn' : ''}`}>
        {ss.washout ? 'No steady culture: the cells wash out' : `At steady state, D = ${fmt(ss.dilutionRate, 4)} h⁻¹`}
      </h4>
      {!ss.washout && (
        <ul className="text-body space-y-0.5">
          {rows.map(([key, label, value, unit]) => (
            <li key={key} data-testid="steady-value" data-key={key} data-value={value == null ? '' : String(value)}>
              {label}: <span className="font-num">{value == null ? '—' : fmt(value, 4)}</span> {unit}
            </li>
          ))}
        </ul>
      )}
      <p className={`text-caption mt-1 ${ss.washout || (ss.bistable && ss.reached === 'washout') ? 'text-signal-warn' : 'text-ink-soft'}`}>{ss.words}</p>
    </div>
  );
}

function EndState({ r }: { r: SimulationResult }) {
  const u = r.units;
  const conc = u.P ?? u.Q ?? u.X ?? '';
  return (
    <section className="card p-3" aria-label="End state" data-testid="simulation-end">
      <h3 className="font-medium text-body mb-1">At harvest</h3>
      <ul className="text-body space-y-0.5">
        <li>
          Final titre: <span className="font-num" data-testid="simulation-titre">{r.finalTitre == null ? '—' : fmt(r.finalTitre, 4)}</span> {r.finalTitre == null ? 'the family keeps no product' : conc}
        </li>
        <li>
          Yield achieved: <span className="font-num" data-testid="simulation-yield">{r.yieldAchieved == null ? '—' : fmt(r.yieldAchieved, 4)}</span> g g⁻¹, product made over
          sugar used
        </li>
        <li data-testid="simulation-productivity">
          Productivity: <span className="font-num">{r.productivity == null ? '—' : fmt(r.productivity, 4)}</span> {conc} h⁻¹,{' '}
          {r.steadyState ? "the final titre over the run's hours, a batch's measure: a chemostat's is D·P at its steady state, below" : 'the titre over the harvest hour'}
        </li>
        <li data-testid="simulation-runs-out">
          {r.sugarRunsOutH != null ? (
            <>
              The sugar runs out at <span className="font-num">{fmt(r.sugarRunsOutH, 4)}</span> h
            </>
          ) : (
            <>The sugar does not run out within the run</>
          )}
          ; harvested at <span className="font-num">{fmt(r.harvestH, 4)}</span> h.
        </li>
      </ul>
      <p className={`text-caption mt-1 ${r.massBalance.ok ? 'text-ink-soft' : 'text-signal-warn'}`}>{r.massBalance.note}</p>
      {r.steadyState && <SteadyStateCard ss={r.steadyState} units={u} />}
      {r.flags.map((f) => (
        <p key={f} className="text-caption text-signal-warn" data-testid="simulation-flag">
          {f}
        </p>
      ))}
      {r.our.note && <p className="text-caption text-ink-soft mt-1">{r.our.note}</p>}
    </section>
  );
}

function CeilingCard({ r }: { r: SimulationResult }) {
  const c = r.ceiling;
  return (
    <section className="card p-3" aria-label="Yield beside the ceiling" data-testid="simulation-ceiling" data-flagged={c?.flagged ? 'true' : 'false'}>
      <h3 className="font-medium text-body mb-1">Yp/s beside the geneOS ceiling</h3>
      {!c ? (
        <p className="text-caption text-ink-soft">
          No ceiling is read beside this simulation: the service reads one when a strain, a product and a sugar are all named, and geneOS
          computes a ceiling for that product.
        </p>
      ) : (
        <>
          {c.flagged && (
            <Callout kind="warn" title="Above a ceiling: flagged, never clamped">
              Yp/s lies above what a reaction network of this organism allows from {c.sugar}. The value stands as it was bound or typed; a
              reviewer should check what it rests on.
            </Callout>
          )}
          {c.rows.length > 0 && (
            <ul className="space-y-1 mt-1">
              {c.rows.map((row) => (
                <li key={row.modelId} className="text-caption" data-testid="simulation-ceiling-row" data-model={row.modelId} data-above={row.above ? 'true' : 'false'}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{row.modelName}</span>
                    <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${row.artifactId}`)}>
                      ceiling {fmt(row.ceilingGPerG, 4)} g g⁻¹
                    </a>
                    <ProvenanceBadge p={row.provenance} compact />
                  </div>
                  <div>
                    Yp/s <span className="font-num">{row.ypsGPerG == null ? '—' : fmt(row.ypsGPerG, 4)}</span> g g⁻¹ · yield achieved{' '}
                    <span className="font-num">{row.yieldAchievedGPerG == null ? '—' : fmt(row.yieldAchievedGPerG, 4)}</span> g g⁻¹
                  </div>
                  <div className={row.above ? 'text-signal-warn' : 'text-ink-soft'}>{row.words}</div>
                  <div className="text-ink-soft">{row.matchWords}</div>
                </li>
              ))}
            </ul>
          )}
          {c.empty && (
            <p className="text-caption text-ink-soft" data-testid="simulation-ceiling-empty">
              {c.empty}{' '}
              <a className="text-accent hover:underline" href={href(c.computeAt)}>
                geneOS → Model
              </a>
            </p>
          )}
        </>
      )}
    </section>
  );
}

function ParamTable({ r, specs }: { r: SimulationResult; specs: ParameterSpec[] }) {
  const spec = new Map(specs.map((s) => [s.key, s]));
  const rows = [...r.parameters, ...r.start];
  const csv = () =>
    exportCSV(
      `simulation-${r.artifactId}-parameters.csv`,
      ['Parameter', 'Symbol', 'Value', 'Low', 'High', 'Unit', 'Origin', 'By', 'Source', 'Records'],
      rows.map((v) => [
        v.key,
        spec.get(v.key)?.symbol ?? '',
        v.value ?? '',
        v.low ?? '',
        v.high ?? '',
        spec.get(v.key)?.unit ?? '',
        v.origin,
        v.overriddenBy ?? '',
        v.source?.id ?? v.source?.note ?? '',
        v.recordIds.join(' '),
      ]),
    );
  return (
    <section aria-label="Parameters" data-testid="simulation-params">
      <SectionTitle right={<Button onClick={csv}>CSV</Button>}>Every parameter, with its source</SectionTitle>
      <div className="overflow-x-auto">
        <table className="w-full text-caption">
          <thead>
            <tr className="text-ink-soft text-left">
              <th className="py-1 pr-2 font-medium">Parameter</th>
              <th className="py-1 pr-2 font-medium">Value</th>
              <th className="py-1 pr-2 font-medium">Interval</th>
              <th className="py-1 pr-2 font-medium">Unit</th>
              <th className="py-1 font-medium">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => {
              const s = spec.get(v.key);
              return (
                <tr key={v.key} className="border-t border-line/60" data-testid="simulation-param" data-key={v.key} data-origin={v.origin}>
                  <td className="py-1 pr-2">
                    {s?.label ?? v.key} <span className="font-num text-ink-soft">{s?.symbol || v.key}</span>
                  </td>
                  <td className="py-1 pr-2 font-num">{shown(v.value)}</td>
                  <td className="py-1 pr-2 font-num">{v.low != null && v.high != null && v.low !== v.high ? `${shown(v.low)} to ${shown(v.high)}` : ''}</td>
                  <td className="py-1 pr-2 font-num">{s?.unit ?? ''}</td>
                  <td className="py-1">
                    <SourceChip value={v} />
                    {v.outOfBounds && <span className="block text-signal-warn">{v.outOfBounds}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function FermOSSimulate() {
  const route = useRoute();
  const strains = useStore((s) => s.strains);
  const [families, setFamilies] = useState<FamilyInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [family, setFamily] = useState<string>(route.query.get('family') ?? '');
  const [strain, setStrain] = useState<string>(route.query.get('strain') ?? '');
  // The products this build has words for (lib/geneos.ts's PRODUCT_WORDS).
  const products = useMemo(() => Object.keys(PRODUCT_WORDS), []);
  // null: nobody has chosen, so the family's own default; '': None named, chosen (OF-BLD-020 §3.R, finding 14).
  const [product, setProduct] = useState<string | null>(route.query.get('product'));
  const [sugar, setSugar] = useState<string>(route.query.get('sugar') ?? 'glucose');
  const queryStart = route.query.get('start');
  const [start, setStart] = useState<Start>(queryStart === 'fit' || queryStart === 'simulation' ? queryStart : 'records');
  const [fit, setFit] = useState<string>(route.query.get('fit') ?? '');
  const [kept, setKept] = useState<string>(route.query.get('simulation') ?? '');
  const [preset, setPreset] = useState<SimulateAsk['durationPreset']>(UNTIL_RUN_OUT);
  const [fits, setFits] = useState<FermosFitInfo[] | null>(null);
  const [sims, setSims] = useState<SimulationSummary[] | null>(null);
  const [listProblem, setListProblem] = useState<string | null>(null);
  const [scopeData, setScopeData] = useState<ParamScope | null>(null);
  const [scopeProblem, setScopeProblem] = useState<string | null>(null);
  const [binding, setBinding] = useState<FermosBinding | null>(null);
  const [bindProblem, setBindProblem] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [runProblem, setRunProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // The families.
  useEffect(() => {
    const ctrl = new AbortController();
    setProblem(null);
    fermosFamilies(ctrl.signal)
      .then(setFamilies)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);

  const runnable = (families ?? []).filter((f) => !f.socket);
  const chosen = runnable.find((f) => f.id === family) ?? runnable.find((f) => f.id === 'batch_v1') ?? runnable[0] ?? null;
  // A family with no product state in the broth (P) names no product by default, and None named stays chosen
  // once a person chose it.
  const freeProduct = !!chosen && chosen.states.includes('P');
  const productDefault = freeProduct ? (products.includes('ethanol') ? 'ethanol' : (products[0] ?? '')) : '';
  const productChosen = product === '' ? '' : product && products.includes(product) ? product : productDefault;
  const strainChosen = strains.some((s) => s.id === strain) ? strain : '';
  const ready = start === 'records' || (start === 'fit' && !!fit) || (start === 'simulation' && !!kept);
  const ask: SimulateAsk | null = chosen
    ? {
        family: chosen.id,
        strain: strainChosen || null,
        product: productChosen || null,
        sugar: sugar || null,
        fitArtifact: start === 'fit' && fit ? fit : null,
        startFrom: start === 'fit' && fit ? 'fit' : start === 'simulation' && kept ? `simulation:${kept}` : 'records',
        durationPreset: start === 'fit' && fit ? preset : UNTIL_RUN_OUT,
      }
    : null;
  const askKey = JSON.stringify(ask);
  const scope = chosen ? familyScope(chosen.id) : '';
  const overrides = useStore(overridesFor(scope));
  const overridesKey = JSON.stringify(overrides);

  // The fits and kept simulations to start from, asked when that start is chosen.
  useEffect(() => {
    if (start === 'records') return;
    const ctrl = new AbortController();
    setListProblem(null);
    const load =
      start === 'fit'
        ? proformaShelf(ctrl.signal).then((shelf) => {
            // The fits list is read for a flowsheet (what each can feed it):
            // the first one a scenario can name; the fits are the same for any.
            const flowsheet = shelf.find((f) => !f.reference);
            if (!flowsheet) throw new FermosRefused(422, 'No flowsheet a scenario can name is on the shelf, so the fits list cannot be read.');
            return fermosFits(flowsheet.id, ctrl.signal).then((all) => setFits(all.filter((x) => x.tool !== 'fermos.simulation')));
          })
        : fermosSimulations(ctrl.signal).then(setSims);
    load.catch((e: unknown) => !ctrl.signal.aborted && setListProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [start]);

  // The panel's scope, bound as the simulation would bind it.
  useEffect(() => {
    setScopeData(null);
    setScopeProblem(null);
    setResult(null);
    setRunProblem(null);
    if (!ask || !ready) return;
    const ctrl = new AbortController();
    paramScope(scope, paramAskOf(ask), ctrl.signal)
      .then(setScopeData)
      .catch((e: unknown) => !ctrl.signal.aborted && setScopeProblem(problemOf(e)));
    return () => ctrl.abort();
    // `askKey` names the ask; the scope follows its family.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [askKey, ready]);

  // What waits, with the person's overrides laid on: what Simulate would refuse for.
  useEffect(() => {
    setBinding(null);
    setBindProblem(null);
    if (!ask || !ready) return;
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      fermosBind(ask, overrides, ctrl.signal)
        .then(setBinding)
        .catch((e: unknown) => !ctrl.signal.aborted && setBindProblem(problemOf(e)));
    }, BIND_AFTER_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [askKey, overridesKey, ready]);

  const specs = chosen?.specs ?? [];
  const label = (key: string) => specs.find((s) => s.key === key)?.label ?? key;
  const waiting = binding?.waiting ?? [];
  // §8.R (findings 12, 14): what the family would refuse though nothing
  // waits holds the button, in the run's own words (fermos.run_refusal).
  const refused = binding?.refused ?? null;
  const canRun = !!ask && ready && !!binding && waiting.length === 0 && !refused && !busy;

  const simulate = () => {
    if (!ask || !canRun) return;
    setBusy(true);
    setRunProblem(null);
    fermosSimulate(ask, overrides)
      .then(setResult)
      .catch((e: unknown) => {
        setResult(null);
        setRunProblem(problemOf(e));
      })
      .finally(() => setBusy(false));
  };

  const strainLabel = (id: string) => {
    const s = strains.find((x) => x.id === id);
    return s ? `${s.binomial} ${s.designation}`.trim() : id;
  };

  return (
    <div className="space-y-4" data-testid="fermos-simulate">
      <p className="text-body text-ink-soft">
        A simulation integrates a model family from its parameters, each bound to a source the panel names: a fit a person chose, the
        records through the aggregate gate, a kept simulation, a named person&rsquo;s value, or a stated convention. It is kept as an
        artifact whose provenance follows those sources; it is never a measurement.
      </p>
      {problem && <Callout kind="warn">{problem}</Callout>}
      {families === null && !problem && <p className="text-caption text-ink-soft">Asking the service for the model families…</p>}
      {families && <FamilyChooser families={families} chosen={chosen?.id ?? ''} onChoose={setFamily} />}

      {chosen && (
        <div className="flex flex-wrap items-end gap-3" data-testid="simulate-choosers">
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Strain</span>
            <select className="input" aria-label="Strain" value={strainChosen} onChange={(e) => setStrain(e.target.value)} data-testid="simulate-strain">
              <option value="">Every strain on file</option>
              {strains.map((s) => (
                <option key={s.id} value={s.id}>
                  {strainLabel(s.id)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Product</span>
            <select className="input" aria-label="Product" value={productChosen} onChange={(e) => setProduct(e.target.value)} data-testid="simulate-product">
              {products.map((p) => (
                <option key={p} value={p}>
                  {productWords(p).option}
                </option>
              ))}
              <option value="">None named</option>
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Sugar</span>
            <select className="input" aria-label="Sugar" value={sugar} onChange={(e) => setSugar(e.target.value)} data-testid="simulate-sugar">
              {CARBON_SOURCES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Start from</span>
            <select className="input" aria-label="Start from" value={start} onChange={(e) => setStart(e.target.value as Start)} data-testid="simulate-start">
              <option value="records">Records</option>
              <option value="fit">A fit</option>
              <option value="simulation">A kept simulation</option>
            </select>
          </label>
          {start === 'fit' && fits && fits.length > 0 && (
            <>
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Fit</span>
                <select className="input" aria-label="Fit" value={fit} onChange={(e) => setFit(e.target.value)} data-testid="simulate-fit">
                  <option value="">choose one</option>
                  {fits.map((f) => (
                    <option key={f.artifactId} value={f.artifactId}>
                      {FIT_TOOL_WORDS[f.tool] ?? f.tool} {f.artifactId}
                      {f.depositionId ? ` · run ${f.depositionId}` : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Run length</span>
                <select className="input" aria-label="Run length" value={preset} onChange={(e) => setPreset(e.target.value as SimulateAsk['durationPreset'])}>
                  <option value={UNTIL_RUN_OUT}>Until the sugar runs out</option>
                  <option value={FIT_LENGTH}>As long as the fitted run</option>
                </select>
              </label>
            </>
          )}
          {start === 'simulation' && sims && sims.length > 0 && (
            <label className="text-caption text-ink-soft">
              <span className="block mb-0.5">Kept simulation</span>
              <select className="input" aria-label="Kept simulation" value={kept} onChange={(e) => setKept(e.target.value)} data-testid="simulate-kept">
                <option value="">choose one</option>
                {sims.map((s) => (
                  <option key={s.artifactId} value={s.artifactId}>
                    {s.title} · {s.strain ?? 'every strain'} · {s.artifactId}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}
      {listProblem && <Callout kind="warn">{listProblem}</Callout>}
      {start === 'fit' && fits && fits.length === 0 && (
        <p className="text-caption" data-testid="simulate-no-fit">
          No fit is on file yet. A fit is made from a deposited run on{' '}
          <a className="text-accent hover:underline" href={href('/fermos')}>
            fermOS → Fits
          </a>
          .
        </p>
      )}
      {start === 'simulation' && sims && sims.length === 0 && (
        <p className="text-caption" data-testid="simulate-no-kept">
          No simulation is kept yet: the first one made here is.
        </p>
      )}
      {chosen && !ready && <p className="text-caption text-ink-soft">Choose the {start === 'fit' ? 'fit' : 'kept simulation'} to start from.</p>}

      {chosen && ready && (
        <section aria-label="Parameters" className="card p-3" data-testid="simulate-panel">
          <SectionTitle>
            <span>The parameters of {chosen.title}, each with its source</span>
          </SectionTitle>
          {scopeProblem && <Callout kind="warn">{scopeProblem}</Callout>}
          {!scopeData && !scopeProblem && <p className="text-caption text-ink-soft">Asking the service what binds…</p>}
          <ParameterPanel scope={scope} data={scopeData} request={ask ? paramAskOf(ask) : undefined} groups={SIMULATE_GROUPS} />
          {binding && binding.notes.length > 0 && (
            <ul className="text-caption text-ink-soft space-y-0.5 mt-2" data-testid="simulate-notes">
              {binding.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {chosen && ready && (
        <div className="space-y-2" data-testid="simulate-run">
          {bindProblem && <Callout kind="warn">{bindProblem}</Callout>}
          {!binding && !bindProblem && <p className="text-caption text-ink-soft">Asking the service what waits…</p>}
          {binding && waiting.length > 0 && (
            <div className="text-caption" data-testid="simulate-waiting" data-keys={waiting.join(',')}>
              <p className="font-medium text-signal-warn">
                {waiting.length === 1 ? 'One parameter waits' : `${waiting.length} parameters wait`} before {chosen.id} can run:
              </p>
              <ul className="ml-3 list-disc">
                {waiting.map((k) => (
                  <li key={k}>
                    <span className="font-num">{k}</span> ({label(k)}): {binding.values.find((v) => v.key === k)?.detail ?? 'no source yet'}
                  </li>
                ))}
              </ul>
              <p className="text-ink-soft mt-1">Type each in the panel under your reviewer name, or choose a strain, sugar or fit whose records bind it.</p>
            </div>
          )}
          {binding && waiting.length === 0 && refused && (
            <p className="text-caption text-signal-warn" data-testid="simulate-refused">
              Every parameter of {chosen.id} has a source, but the run would be refused: {refused}
            </p>
          )}
          {binding && waiting.length === 0 && !refused && (
            <p className="text-caption text-ink-soft" data-testid="simulate-ready">
              Nothing waits: every parameter of {chosen.id} has a source.
            </p>
          )}
          <Button variant="primary" onClick={simulate} disabled={!canRun} data-testid="simulate-button">
            {busy ? 'Simulating…' : 'Simulate'}
          </Button>
          {runProblem && <Callout kind="warn">{runProblem}</Callout>}
        </div>
      )}

      {result && (
        <div className="space-y-4" data-testid="simulation-result" data-artifact={result.artifactId}>
          <BuiltFrom r={result} />
          <TimeCourse
            title={`How does a simulated ${result.title.toLowerCase()} culture of ${result.strain ? strainLabel(result.strain) : 'every strain on file'} run${result.product ? `, making ${productWords(result.product).short}` : ''}${result.sugar ? ` from ${result.sugar}` : ''}?`}
            {...timeCourseOf(result)}
            csvName={`simulation-${result.artifactId}`}
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <EndState r={result} />
            <CeilingCard r={result} />
          </div>
          <ParamTable r={result} specs={specs} />
          <div className="flex flex-wrap items-center gap-2" data-testid="simulation-actions">
            {isFitFamily(result.family) && (
              <a className="btn" href={href(`/fermos?family=${encodeURIComponent(result.family)}`)} data-testid="simulation-fit-link">
                Fit this family to a deposition
              </a>
            )}
            <a className="btn" href={href(vesselPath(result.artifactId))} data-testid="simulation-vessel-link">
              Design the vessel
            </a>
            {/* OF-BLD-020 §6.2: the broth that leaves fermOS is the stream that enters pureOS. */}
            <a className="btn" href={href(builderInletPath({ kind: 'simulation', id: result.artifactId }))} data-testid="simulation-train-inlet">
              Use as a train&rsquo;s inlet
            </a>
          </div>
          <SendToProforma artifactId={result.artifactId} tool="fermos.simulation" />
        </div>
      )}
    </div>
  );
}
