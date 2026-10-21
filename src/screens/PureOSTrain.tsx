// pureOS → Train (OF-BLD-019 §4.1, D1): the units of the run Proforma priced.
//
// /pureos/train/:scenarioId opens the newest run of that scenario (or one run
// by its artifact id) and reads its stream and unit tables, unit by unit, in
// run order: each unit's inlets and outlets, the product's mass in and out,
// the share of it that leaves on the way to the product stream, and the
// cumulative share still on the path. The SERVICE reads all of it from the one
// artifact (`core/openferment_core/pureos/__init__.py`); this page shows those fields
// and computes none. Clicking a unit cuts the stream table to its streams.
//
// A unit whose BioSTEAM class is a step in the unit-operation vocabulary
// (`biosteamClasses` in src/data/vocabulary.ts) links to that step on pureOS's
// front page. A deep link to an archived program's train opens under the
// banner naming it, as every page opened by id does.
//
// PROPERTIES (§4.2, D9): the broth and the product stream, and any other
// stream a person picks, as thermosteam answers for them at the stream's own
// temperature, pressure and phase. The page names the run and the stream; the
// service reads the stream from the run and asks thermosteam in the Proforma
// worker, and the answer is one `thermo_props` artifact (PropertiesPanel).
//
// A TRAIN BUILT IN PUREOS (OF-BLD-020 §5.3) opens here too, by its train id
// (its newest run) or a run's artifact id: the same reading of the one
// `pureos.train_run` artifact, with a link back to the Builder when this
// browser saved the train. A Proforma or reference run offers **Build a train
// from this run**, which opens the Builder with the run's units read into a
// train by the service.
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Download, Filter } from 'lucide-react';
import type { StreamRow, Train, TrainUnit } from '@/data/types';
import { trainSubjects } from '@/lib/thermo';
import { PropertiesPanel } from '@/components/PropertiesPanel';
import { operationForClass } from '@/data/vocabulary';
import { PureosDown, PureosRefused, RUN_WORDS, builderFromRunPath, builderPath, productIn, pureosTrain, share, streamsOf } from '@/lib/pureos';
import { useStore } from '@/store';
import { OwnerTabs } from '@/components/OwnerTabs';
import { PUREOS_TABS } from '@/data/tabs';
import { exportCSV } from '@/lib/csv';
import { fmt } from '@/engine/units';
import { href, useRoute } from '@/router';
import { Callout, Card, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ComponentTag } from '@/components/ComponentTag';
import { ArchivedBanner } from '@/components/ArchivedBanner';
import { RecoveryByUnit } from '@/components/figures';

const mass = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '—' : fmt(v, 3));

export default function PureOSTrain({ scenarioId }: { scenarioId: string }) {
  const route = useRoute();
  const [train, setTrain] = useState<Train | null>(null);
  const [problem, setProblem] = useState<{ kind: 'down' | 'refused'; text: string } | null>(null);
  const [picked, setPicked] = useState<string | null>(route.query.get('unit'));

  useEffect(() => {
    const ctrl = new AbortController();
    setTrain(null);
    setProblem(null);
    pureosTrain(scenarioId, ctrl.signal)
      .then(setTrain)
      .catch((e) => {
        if (ctrl.signal.aborted) return;
        if (e instanceof PureosDown) setProblem({ kind: 'down', text: `${e.message} ${e.remedy}` });
        else if (e instanceof PureosRefused) setProblem({ kind: 'refused', text: e.message });
        else setProblem({ kind: 'down', text: String(e) });
      });
    return () => ctrl.abort();
  }, [scenarioId]);

  const unit = useMemo(() => train?.units.find((u) => u.id === picked) ?? null, [train, picked]);
  const choose = (id: string) => setPicked((now) => (now === id ? null : id));

  return (
    <div data-testid="pureos-train">
      <a href={href('/pureos')} className="inline-flex items-center gap-1 text-caption text-ink-soft hover:text-accent mb-2">
        <ArrowLeft size={13} aria-hidden /> pureOS
      </a>
      <ArchivedBanner kind="scenario" id={scenarioId} />
      {train?.scenarioId && train.scenarioId !== scenarioId && <ArchivedBanner kind="scenario" id={train.scenarioId} />}
      <PageHeader
        eyebrow="pureOS · Train"
        title={train ? (train.scenarioName ?? train.trainName ?? train.flowsheet ?? train.artifactId) : scenarioId}
        subtitle="The units of a run, in the order it ran them (a run Proforma priced, or a train built in pureOS): what enters and leaves each, how much of the product it passes on toward the product stream, and how much is still on the path after it."
      />
      <OwnerTabs tabs={PUREOS_TABS} />

      {problem?.kind === 'down' && (
        <Callout kind="warn" title="pureOS reads the train from the service">
          <p className="text-ink">{problem.text}</p>
        </Callout>
      )}
      {problem?.kind === 'refused' && (
        <Callout kind="info" title="No train on file for this">
          <p className="text-ink" data-testid="train-none">
            {problem.text}
          </p>
          <p className="mt-1">
            A train is read from a Proforma run. Open the scenario in{' '}
            <a className="text-accent hover:underline" href={href(`/proforma/scenario/${encodeURIComponent(scenarioId)}`)}>
              Proforma
            </a>
            , give every input a source, and run it; its train shows here.
          </p>
        </Callout>
      )}
      {!train && !problem && <p className="text-body text-ink-soft">Reading the run…</p>}

      {train && <TrainView train={train} unit={unit} choose={choose} />}

      <div className="mt-5">
        <ComponentTag component="pureOS" action={train ? `train of ${train.units.length} units, read from a run` : 'train'} />
      </div>
    </div>
  );
}

/** Back to the Builder for a train this browser saved; for any other run, a fresh train read from its units. */
function BuilderLink({ train }: { train: Train }) {
  const saved = useStore((s) => (train.trainId ? (s.trainsMade[train.trainId] ?? null) : null));
  if (train.tool === 'pureos.train_run') {
    if (!train.trainId || !saved)
      return (
        <span className="text-caption text-ink-soft" data-testid="train-builder-elsewhere">
          Built in pureOS, but not saved in this browser.
        </span>
      );
    return (
      <a className="chip" href={href(builderPath(train.trainId))} data-testid="train-open-builder">
        Open in the Builder
      </a>
    );
  }
  return (
    <a className="chip" href={href(builderFromRunPath(train.artifactId))} data-testid="train-build-from-run">
      Build a train from this run
    </a>
  );
}

function TrainView({ train, unit, choose }: { train: Train; unit: TrainUnit | null; choose: (id: string) => void }) {
  const onPath = train.units.filter((u) => u.onPath).length;
  const massUnit = train.tableUnits.massFlow ?? 'kg/hr';
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-4">
        <Stat label="Product" value={train.product ?? '—'} sub={train.productStream ? `in ${train.productStream}` : 'the run names none'} />
        <Stat
          label="Overall recovery"
          value={share(train.overallRecovery)}
          sub={train.overallRecovery == null ? 'not read for this run' : 'of what the path delivers or loses'}
        />
        <Stat label="Units" value={String(train.units.length)} sub={`${onPath} on the product's path`} />
        <Stat label="Product out" value={mass(train.productOut)} unit={massUnit} sub={`${mass(train.productLost)} ${massUnit} lost on the way`} />
      </div>

      <Card className="p-3 mb-4">
        <div className="flex flex-wrap items-center gap-2 text-caption">
          <ProvenanceBadge p={train.provenance} />
          <span className="text-ink-soft">
            Run{' '}
            <a className="font-num text-ink hover:text-accent" href={href(`/biorepo/artifacts/${train.artifactId}`)}>
              {train.artifactId}
            </a>{' '}
            · {train.flowsheet ?? 'flowsheet not named'} · {train.createdAt}
            {train.runs > 1 ? ` · the newest of ${train.runs} runs on file` : ''}
          </span>
          {train.scenarioId && (
            <a className="chip" href={href(`/proforma/scenario/${encodeURIComponent(train.scenarioId)}`)}>
              Open the scenario in Proforma
            </a>
          )}
          <BuilderLink train={train} />
        </div>
        <p className="text-caption text-ink-soft mt-2">{RUN_WORDS}</p>
        <p className="text-caption text-ink-soft mt-1" data-testid="train-product-basis">
          The product traced: {train.productBasis}.
        </p>
        {train.tablesSource && <p className="text-caption text-ink-soft mt-1">Tables made by: {train.tablesSource}</p>}
      </Card>

      {train.note && (
        <div className="mb-4">
          <Callout kind="info" title="What this run cannot say">
            <p className="text-ink" data-testid="train-note">
              {train.note}
            </p>
          </Callout>
        </div>
      )}

      <RecoveryByUnit
        title={`How much of the ${train.product ?? 'product'} does each unit pass on?`}
        product={train.product}
        units={train.units}
        provenance={train.provenance}
        massUnit={massUnit}
        why={train.note}
        selected={unit?.id ?? null}
        onSelect={choose}
        csvName={`recovery-${train.scenarioId ?? train.artifactId}`}
        notes={[
          "A unit's recovery counts the outlets that lead on to the product stream, directly, through later units or round a recycle. Outlets over inlets would read one for every unit that reacts nothing, so it is not used.",
          "A unit whose passes stay apart, such as a process heat exchanger, is counted only on the pass that carries the product on; product that enters a unit on the path and leaves by no outlet is lost there.",
          'Click a unit to cut the stream table below to its streams.',
        ]}
      />

      <section className="mt-5" aria-labelledby="train-units">
        <SectionTitle right={<span className="font-num text-caption text-ink-soft">{train.units.length} units</span>}>
          <span id="train-units">Units, in run order</span>
        </SectionTitle>
        <Card className="overflow-x-auto">
          <table className="w-full text-caption" data-testid="train-units">
            <thead>
              <tr className="text-left text-ink-soft border-b border-line">
                <th className="px-2 py-1.5 font-medium">Unit</th>
                <th className="px-2 py-1.5 font-medium">Class</th>
                <th className="px-2 py-1.5 font-medium">In</th>
                <th className="px-2 py-1.5 font-medium">Out</th>
                <th className="px-2 py-1.5 font-medium text-right">{train.product ?? 'Product'} in</th>
                <th className="px-2 py-1.5 font-medium text-right">{train.product ?? 'Product'} out</th>
                <th className="px-2 py-1.5 font-medium text-right">Recovery</th>
                <th className="px-2 py-1.5 font-medium text-right">On the path after</th>
              </tr>
            </thead>
            <tbody>
              {train.units.map((u) => (
                <UnitRowView key={u.id} u={u} picked={unit?.id === u.id} choose={choose} />
              ))}
            </tbody>
          </table>
        </Card>
        <p className="text-caption text-ink-soft mt-1">Masses are {massUnit} of the product, in the run's base case.</p>
      </section>

      <StreamTable train={train} unit={unit} clear={() => unit && choose(unit.id)} />

      <TrainProperties train={train} />
    </>
  );
}

function TrainProperties({ train }: { train: Train }) {
  const subjects = useMemo(() => trainSubjects(train), [train]);
  const [other, setOther] = useState('');
  const shown = [
    ...subjects,
    ...(other && !subjects.some((s) => s.streamId === other) ? [{ role: 'Stream', streamId: other }] : []),
  ];
  return (
    <section className="mt-5" aria-labelledby="train-properties-title" data-testid="thermo-card">
      <SectionTitle
        right={
          <label className="text-caption text-ink-soft flex items-center gap-1.5 whitespace-nowrap">
            Another stream
            <select className="input" aria-label="Another stream" value={other} onChange={(e) => setOther(e.target.value)}>
              <option value="">none</option>
              {train.streams.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id}
                </option>
              ))}
            </select>
          </label>
        }
      >
        <span id="train-properties-title">Properties</span>
      </SectionTitle>
      <p className="text-caption text-ink-soft mb-2">
        Density, heat capacity, viscosity, and bubble and dew points, as thermosteam (BioSTEAM&rsquo;s property engine)
        computes them for a stream of this run at the stream&rsquo;s own temperature, pressure and phase. The page names the
        run and the stream; the service reads the stream from the run, and nothing is typed. A chemical thermosteam&rsquo;s
        library lacks is refused in words.
      </p>
      {shown.length === 0 && (
        <p className="text-body text-ink-soft">This run names no broth or product stream; pick a stream above to ask about it.</p>
      )}
      <div className="grid md:grid-cols-2 gap-3">
        {shown.map((s) => (
          <PropertiesPanel
            key={`${train.artifactId}:${s.streamId}`}
            title={
              <>
                {s.role}: <span className="font-num">{s.streamId}</span>
              </>
            }
            question={{ artifactId: train.artifactId, streamId: s.streamId }}
          />
        ))}
      </div>
    </section>
  );
}

function UnitRowView({ u, picked, choose }: { u: TrainUnit; picked: boolean; choose: (id: string) => void }) {
  const op = operationForClass(u.unitClass);
  return (
    <>
      <tr
        className={cx('border-b border-line/60 cursor-pointer hover:bg-ink-soft/[0.04]', picked && 'bg-accent/[0.06]', !u.onPath && 'text-ink-soft')}
        data-testid="train-unit"
        data-unit={u.id}
        aria-selected={picked}
        onClick={() => choose(u.id)}
      >
        <td className="px-2 py-1.5">
          <button className="font-num text-ink hover:text-accent" onClick={(e) => (e.stopPropagation(), choose(u.id))} aria-pressed={picked}>
            {u.id}
          </button>
          {u.line && <div className="text-ink-soft">{u.line}</div>}
        </td>
        <td className="px-2 py-1.5">
          <span className="font-num">{u.unitClass}</span>
          {op && (
            <div>
              <a
                className="text-accent hover:underline"
                href={href(`/pureos?op=${encodeURIComponent(op.id)}`)}
                data-testid="train-unit-operation"
                onClick={(e) => e.stopPropagation()}
              >
                {op.label}
              </a>
            </div>
          )}
        </td>
        <td className="px-2 py-1.5 font-num">{u.ins.join(', ') || '—'}</td>
        <td className="px-2 py-1.5 font-num">{u.outs.join(', ') || '—'}</td>
        <td className="px-2 py-1.5 font-num text-right">{mass(u.productIn)}</td>
        <td className="px-2 py-1.5 font-num text-right">{mass(u.productOut)}</td>
        <td className="px-2 py-1.5 font-num text-right">{share(u.recovery)}</td>
        <td className="px-2 py-1.5 font-num text-right">{share(u.cumulative)}</td>
      </tr>
      {(u.note || u.lostTo.length > 0) && (
        <tr className="border-b border-line/60" data-testid="train-unit-note">
          <td colSpan={8} className="px-2 pb-1.5 text-ink-soft">
            {u.note}
            {u.note && u.lostTo.length > 0 ? ' · ' : ''}
            {u.lostTo.length > 0 && (
              <>
                lost to <span className="font-num">{u.lostTo.join(', ')}</span>: {mass(u.productLost)}
              </>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export function StreamTable({ train, unit, clear }: { train: Train; unit: TrainUnit | null; clear: () => void }) {
  const rows = streamsOf(train, unit);
  const u = train.tableUnits;
  const headers = [
    'Stream',
    'From',
    'To',
    'Phase',
    `T (${u.T ?? 'K'})`,
    `P (${u.P ?? 'Pa'})`,
    `Mass flow (${u.massFlow ?? 'kg/hr'})`,
    `${train.product ?? 'Product'} (${u.massFlow ?? 'kg/hr'})`,
  ];
  const cells = (s: StreamRow) => [
    s.id,
    s.source ?? 'feed',
    s.sink ?? 'leaves the plant',
    s.phase,
    fmt(s.T, 2),
    fmt(s.P, 0),
    mass(s.massFlow),
    mass(productIn(train, s)),
  ];
  const side = (s: StreamRow) => (unit ? (unit.ins.includes(s.id) ? 'in' : 'out') : null);
  return (
    <section className="mt-5" aria-labelledby="train-streams-title">
      <SectionTitle
        right={
          <span className="flex items-center gap-2">
            {unit && (
              <button className="chip" onClick={clear} data-testid="train-streams-all">
                <Filter size={12} aria-hidden /> Show every stream
              </button>
            )}
            <button
              className="chip"
              onClick={() => exportCSV(`streams-${train.scenarioId ?? train.artifactId}${unit ? `-${unit.id}` : ''}.csv`, headers, rows.map(cells))}
            >
              <Download size={12} aria-hidden /> CSV
            </button>
          </span>
        }
      >
        <span id="train-streams-title">{unit ? `Streams of ${unit.id}` : 'Every stream'}</span>
      </SectionTitle>
      <Card className="overflow-x-auto">
        <table className="w-full text-caption" data-testid="train-streams" data-unit={unit?.id ?? ''}>
          <thead>
            <tr className="text-left text-ink-soft border-b border-line">
              {unit && <th className="px-2 py-1.5 font-medium">Side</th>}
              {headers.map((h, i) => (
                <th key={h} className={cx('px-2 py-1.5 font-medium', i >= 4 && 'text-right')}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b border-line/60" data-testid="train-stream" data-stream={s.id}>
                {unit && <td className="px-2 py-1.5">{side(s)}</td>}
                {cells(s).map((c, i) => (
                  <td key={i} className={cx('px-2 py-1.5', i === 0 || i >= 4 ? 'font-num' : '', i >= 4 && 'text-right')}>
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="p-3 text-body text-ink-soft">This run kept no stream table.</p>}
      </Card>
    </section>
  );
}
