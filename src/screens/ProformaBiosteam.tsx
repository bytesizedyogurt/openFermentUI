// A BioSTEAM scenario (OF-BLD-014 §8.4): a price the service simulated, as a
// distribution, with what moves it and where each input came from.
//
// The service binds every input (`GET /api/proforma/scenarios`): to the
// thread P records of its field, or to an assumption a named person typed
// here. An assumption is kept in the Durable tier and posted with the run;
// an input with neither holds the run, and the screen names it. A run is one
// artifact (`POST /api/proforma/run`): 500 seeded samples, a grid the
// sliders read with the interpolation the authored scenarios use, and the
// settings the reference model supplied, read back and listed.
import { useEffect, useMemo, useState } from 'react';
import { Download, Play } from 'lucide-react';
import type { InputAssumption, ProformaRunResult, ProformaScenarioInfo, Scenario, ScenarioInput } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { evaluateGrid, COST_LINES, COST_LINE_LABEL } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { exportText } from '@/lib/csv';
import { Button, Callout, Card, PageHeader } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { ProvenanceBadge } from '@/components/Provenance';
import { Distribution, Tornado } from '@/components/figures';
import {
  INFEASIBLE_WORDS,
  ProformaDown,
  asResultGrid,
  modellerQuestions,
  proformaScenarios,
  questionsText,
  runProformaScenario,
} from '@/lib/proforma';

const SOURCE_WORDS: Record<string, string> = { record: 'records', assumption: 'assumption', model: 'reference model' };

function SourceChip({ input }: { input: ScenarioInput }) {
  if (input.binding === 'records') {
    return (
      <div className="space-y-1">
        <div className="flex flex-wrap gap-1">
          {input.records.map((r) => (
            <span key={r.id} className="inline-flex items-center gap-1">
              <CitationChip recordId={r.id} paperId={r.paperId} />
              <span className="text-caption text-ink-soft">
                {r.organism ?? 'organism not stated'} · {r.carbonSource} · <span className="font-num">{fmt(r.value, 3)}</span>
              </span>
            </span>
          ))}
        </div>
      </div>
    );
  }
  if (input.binding === 'assumption' && input.source) {
    return (
      <span className="chip" data-testid="assumption-chip">
        assumed by {input.source.by} · {input.source.note}
      </span>
    );
  }
  return <span className="chip text-signal-warn">waiting for a source</span>;
}

function AssumptionForm({ input, onSave }: { input: ScenarioInput; onSave: (a: { value: number; low: number; high: number; note: string }) => void }) {
  const [value, setValue] = useState('');
  const [low, setLow] = useState('');
  const [high, setHigh] = useState('');
  const [note, setNote] = useState('');
  const v = Number(value);
  const lo = Number(low);
  const hi = Number(high);
  const ok = value !== '' && low !== '' && high !== '' && [v, lo, hi].every(Number.isFinite) && lo <= v && v <= hi;
  return (
    <div className="flex flex-wrap items-end gap-2 mt-1" data-testid={`assume-${input.key}`}>
      {(
        [
          ['Value', value, setValue],
          ['Low', low, setLow],
          ['High', high, setHigh],
        ] as const
      ).map(([label, val, set]) => (
        <label key={label} className="text-caption text-ink-soft">
          <span className="block">{label}</span>
          <input className="input w-[88px] font-num" inputMode="decimal" aria-label={`${input.label} ${label.toLowerCase()}`} value={val} onChange={(e) => set(e.target.value)} />
        </label>
      ))}
      <label className="text-caption text-ink-soft flex-1 min-w-[140px]">
        <span className="block">What it rests on</span>
        <input className="input w-full" aria-label={`${input.label} basis`} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <Button disabled={!ok} onClick={() => onSave({ value: v, low: lo, high: hi, note })}>
        Keep assumption
      </Button>
    </div>
  );
}

function InputsTable({ scenario, onAssume, onClear }: { scenario: ProformaScenarioInfo; onAssume: (key: string, a: { value: number; low: number; high: number; note: string }) => void; onClear: (key: string) => void }) {
  const reviewer = useStore((s) => s.reviewer);
  return (
    <table className="w-full text-body" data-testid="proforma-inputs">
      <thead>
        <tr className="text-caption text-ink-soft text-left">
          <th className="py-1 pr-2 font-medium">Input</th>
          <th className="py-1 pr-2 font-medium">Value</th>
          <th className="py-1 pr-2 font-medium">Range</th>
          <th className="py-1 font-medium">Source</th>
        </tr>
      </thead>
      <tbody>
        {scenario.inputs.map((i) => (
          <tr key={i.key} className="border-t border-line/60 align-top" data-testid={`input-${i.key}`}>
            <td className="py-1.5 pr-2">
              <div className="font-medium">{i.label}</div>
              <div className="text-caption text-ink-soft font-num">{i.unit || 'share'}</div>
            </td>
            <td className="py-1.5 pr-2 font-num">{i.value == null ? '—' : fmt(i.value, 4)}</td>
            <td className="py-1.5 pr-2 font-num text-caption">
              {i.low == null ? '—' : `${fmt(i.low, 4)} to ${fmt(i.high ?? i.low, 4)}`}
              {i.sampling && <div className="text-ink-soft">{i.sampling}</div>}
            </td>
            <td className="py-1.5">
              <SourceChip input={i} />
              {i.flags.map((f) => (
                <div key={f} className="text-caption text-signal-warn">
                  {f}
                </div>
              ))}
              {(i.leftOutNoCarbon > 0 || i.leftOutOtherCarbon > 0) && (
                <div className="text-caption text-ink-soft">
                  Left out: {i.leftOutNoCarbon} naming no carbon source, {i.leftOutOtherCarbon} on a feed other than a sugar or a hydrolysate.
                </div>
              )}
              {i.binding === 'assumption' && (
                <button className="text-caption text-ink-soft hover:text-accent underline" onClick={() => onClear(i.key)}>
                  Withdraw this assumption
                </button>
              )}
              {i.binding === 'waiting' &&
                (reviewer.trim() ? (
                  <AssumptionForm input={i} onSave={(a) => onAssume(i.key, a)} />
                ) : (
                  <div className="text-caption text-ink-soft">
                    An assumption carries a person's name: set yours in{' '}
                    <a className="text-accent hover:underline" href={href('/settings/corpus')}>
                      Settings
                    </a>{' '}
                    to type one.
                  </div>
                ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Sliders({ run, scenarioId }: { run: ProformaRunResult; scenarioId: string }) {
  const grid = useMemo(() => asResultGrid(scenarioId, run.grid), [run, scenarioId]);
  const [point, setPoint] = useState<Record<string, number>>(() =>
    Object.fromEntries(run.grid.dims.map((d) => [d.key, d.values[Math.floor(d.values.length / 2)]])),
  );
  const r = evaluateGrid(grid, point);
  const labels = Object.fromEntries(run.inputs.map((i) => [i.key, `${i.label} (${i.unit})`]));
  return (
    <Card className="p-4" data-testid="proforma-sliders">
      <h2 className="font-serif text-section-title font-semibold mb-1">Move three inputs over the run's grid</h2>
      <p className="text-caption text-ink-soft mb-3">
        Interpolated between the {run.grid.msp.length} grid cases the service simulated; the other inputs stay at their base value.
        {run.grid.infeasible > 0 && ` ${run.grid.infeasible} cases could not run, and a point near one shows no price.`}
      </p>
      <div className="space-y-3">
        {run.grid.dims
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
        {Number.isFinite(r.msp) ? `${fmt(r.msp, 3)} ${run.priceBasis}` : 'No price here: a neighbouring case could not run.'}
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

export default function ProformaBiosteam({ scenario: seed }: { scenario: Scenario }) {
  const assumptions = useStore((s) => s.proformaAssumptions[seed.id]) ?? [];
  const setAssumption = useStore((s) => s.setProformaAssumption);
  const clearAssumption = useStore((s) => s.clearProformaAssumption);
  const reviewer = useStore((s) => s.reviewer);
  const recordScenarioRun = useStore((s) => s.recordScenarioRun);
  const [host, setHost] = useState<string | null>(null);
  const [info, setInfo] = useState<ProformaScenarioInfo | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [run, setRun] = useState<ProformaRunResult | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    proformaScenarios(host, ctrl.signal)
      .then((all) => setInfo(all.find((s) => s.id === seed.id) ?? null))
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}` : String(e)));
    return () => ctrl.abort();
  }, [host, seed.id]);

  // What the service bound, with this browser's assumptions laid over the
  // inputs that wait for one; the service applies the same rule on the run.
  const scenario = useMemo<ProformaScenarioInfo | null>(() => {
    if (!info) return null;
    const by = new Map(assumptions.map((a) => [a.key, a]));
    const inputs = info.inputs.map((i): ScenarioInput => {
      const a = by.get(i.key);
      if (i.binding !== 'waiting' || !a) return i;
      return {
        ...i,
        binding: 'assumption',
        value: a.value,
        low: a.low,
        high: a.high,
        sampling: a.low === a.high ? 'fixed' : 'uniform',
        source: { kind: 'assumption', id: null, by: a.by, note: `typed on ${a.at}${a.note ? `: ${a.note}` : ''}` },
      };
    });
    return { ...info, inputs, waiting: inputs.filter((i) => i.binding === 'waiting').map((i) => i.key) };
  }, [info, assumptions]);

  const go = () => {
    if (!scenario) return;
    setRunning(true);
    setProblem(null);
    const used = assumptions.filter((a) => scenario.inputs.find((i) => i.key === a.key)?.binding === 'assumption');
    runProformaScenario(seed.id, used, host)
      .then((r) => {
        setRun(r);
        // Proforma's index reads the price of the newest run from this artifact (OF-BLD-019 D6).
        recordScenarioRun(seed.id, r.artifactId);
      })
      .catch((e: unknown) => setProblem(e instanceof Error ? e.message : String(e)))
      .finally(() => setRunning(false));
  };

  const questions = scenario ? modellerQuestions(scenario.inputs, run) : [];
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div data-testid="proforma-biosteam">
      <PageHeader eyebrow={`${seed.modelId} · BioSTEAM scenario`} title={seed.name} subtitle="BioSTEAM flowsheet, draft v0 — fermentation, harvest and drying only" />

      {problem && <Callout kind="warn">{problem}</Callout>}

      {scenario && (
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex flex-wrap items-end justify-between gap-3 mb-2">
              <h2 className="font-serif text-section-title font-semibold">Inputs, and where each came from</h2>
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Host</span>
                <select className="input" aria-label="Host" value={host ?? ''} onChange={(e) => setHost(e.target.value || null)}>
                  <option value="">Every organism in thread P</option>
                  {scenario.hosts.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="text-caption text-ink-soft mb-3">
              Thread P records of a sugar or hydrolysate feed, through the same gate statistics pass. Three or more give their median and
              range, sampled triangular; two a pair, sampled uniform; one is held fixed. Every other input is a named person's assumption.
            </p>
            <InputsTable
              scenario={scenario}
              onAssume={(key, a) => setAssumption(seed.id, { key, ...a, by: reviewer.trim(), at: today, note: a.note || null } satisfies InputAssumption)}
              onClear={(key) => clearAssumption(seed.id, key)}
            />
            <div className="mt-3 text-caption text-ink-soft">
              <div>The price is {scenario.priceBasis}.</div>
              <div>What this flowsheet leaves out: {scenario.leavesOut.join('; ')}.</div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button variant="primary" onClick={go} disabled={running || scenario.waiting.length > 0}>
                <Play size={14} /> {running ? 'Simulating 500 samples…' : 'Run the scenario'}
              </Button>
              {scenario.waiting.length > 0 && (
                <span className="text-caption text-signal-warn" data-testid="proforma-waiting">
                  Waiting for a source: {scenario.waiting.map((k) => scenario.inputs.find((i) => i.key === k)?.label ?? k).join(', ')}.
                </span>
              )}
            </div>
          </Card>

          {run && (
            <>
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ProvenanceBadge p={run.provenance} />
                  <a className="font-num text-caption hover:text-accent" href={href(`/biorepo/artifacts/${run.artifactId}`)}>
                    {run.artifactId}
                  </a>
                </div>
                <Distribution
                  title="What would this plant's PHA cost, across the inputs' ranges?"
                  quantity="Minimum selling price"
                  unit="USD kg-1 PHA in dried cell mass"
                  bins={run.histogram}
                  quantiles={run.quantiles}
                  provenance={run.provenance}
                  samples={run.samples}
                  infeasible={Object.entries(run.infeasible).map(([reason, count]) => ({ reason: INFEASIBLE_WORDS[reason] ?? reason, count }))}
                  basis={[run.evidence.basis]}
                  notes={['Titre, yield, content and productivity are sampled independently; a real vessel links them, so the infeasible share is part of the result.']}
                  csvName={`${seed.id}-distribution`}
                />
              </Card>
              <Tornado
                title="Which input moves the price most?"
                drawn="The rank correlation of each sampled input with the price over the feasible samples, strongest first, each labelled with where the input came from."
                series={['Spearman ρ']}
                unit="rank correlation"
                provenance={run.provenance}
                rows={run.sensitivity.map((s) => ({
                  label: run.inputs.find((i) => i.key === s.key)?.label ?? s.key,
                  values: [s.rho],
                  tag: SOURCE_WORDS[s.sourceKind] ?? s.sourceKind,
                }))}
                csvName={`${seed.id}-tornado`}
              />
              <Sliders run={run} scenarioId={seed.id} />
              <Card className="p-4">
                <h2 className="font-serif text-section-title font-semibold mb-1">What the reference model supplied</h2>
                <p className="text-caption text-ink-soft mb-2">Read back from the units and the finance model after the base case ran; nobody typed these.</p>
                <table className="w-full text-caption" data-testid="proforma-readback">
                  <tbody>
                    {Object.entries(run.readBack).map(([k, v]) => (
                      <tr key={k} className="border-t border-line/50">
                        <td className="py-0.5">{k}</td>
                        <td className="py-0.5 text-right font-num">{fmt(v, 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}

          <Card className="p-4" data-testid="modeller-questions">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Questions for a process modeller</h2>
              <Button onClick={() => exportText(`${seed.id}-questions.txt`, questionsText(scenario, run))}>
                <Download size={14} /> Export as text
              </Button>
            </div>
            <p className="text-caption text-ink-soft mb-2">
              The inputs that rest on an assumption, the strongest mover first once a run has ranked them, and what the flowsheet leaves out.
            </p>
            <ol className="list-decimal pl-5 space-y-1 text-body">
              {questions.map((q) => (
                <li key={q.key}>
                  <span className="font-medium">{q.label}</span>
                  {q.rho != null && <span className="font-num text-caption text-ink-soft"> (ρ {fmt(q.rho, 2)})</span>}: {q.question}
                </li>
              ))}
            </ol>
            <ul className="list-disc pl-5 mt-2 text-caption text-ink-soft">
              {scenario.leavesOut.map((l) => (
                <li key={l}>left out: {l}</li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </div>
  );
}
