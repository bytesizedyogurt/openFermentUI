// One parameter in the panel (OF-BLD-020 §2.2, D2–D4). ParameterPanel.tsx
// renders one of these per `ParameterSpec`; no screen writes a form for a
// parameter of its own (E.1‴): a numeric control in a module's screens
// stands in these two files alone.
//
// The row COMPUTES NOTHING. The value, its interval, its source, the bounds
// and their reason, the warning outside them and the words that explain a
// value all came from the service (`ParamScope`, `ParamResolveResult`);
// the override's value, interval and note came from the person who typed
// them. A slider is a way of choosing a number inside the spec's bounds and
// nothing more: a typed value outside them is kept, never clamped (D4), and
// the service's warning says so on the row.
//
// A row the caller lets offer readings (`offersReadings`: a Proforma
// scenario's panel, alpha 2.2 E.17) also lists, on asking, the project's
// readings deposited at the bench that this parameter may take (GET
// /api/depositions/readings?unit=, the service's lookup deciding), and a
// person may set the parameter to one: the panel keeps it as the scope's
// override in the reading's own value and unit (`onRead`), and the service
// sets it in the parameter's unit each time it is sent. A typed value or the
// slider then replaces the reading with the person's own.
//
// The bench may use it (pureOS's Builder, fermOS at the fermenter), so the
// constraints Deposition.tsx's header lists hold here too: every control is
// labelled, every touch target is at least 44 px (the citation chips a
// record-bound row opens included, through TOUCH_CHIP), nothing appears only
// on hover (Why, the records and the readings are disclosures a key or a tap
// opens), and the keyboard reaches every control, here and in the records
// Proforma renders into a row.
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { readingLeftTheList, type Override, type ParameterSpec, type ParameterValue } from '@/lib/params';
import { StudiesDown, depositionReadings, type DepositionReading } from '@/lib/studies';
import { href } from '@/router';
import { fmt } from '@/engine/units';
import { plainNote } from '@/lib/proforma';
import { CitationChip } from './Chip';
import { ReadingChoice, depositionPath, minute, readingOf } from './ReadingOrigin';
import { Button, cx } from './ui';

/**
 * A reading's words as the panel says them, the time it was taken to the minute and what follows it: a basis note
 * (`measured on <time>…`) or the service's detail of a value set to a reading (params.py, `reading <ref>, deposited by
 * <person> and taken at <time>…`).
 */
function measuredWords(note: string): string {
  const m = /^measured on (\S+?)(?:: (.*))?$/s.exec(note);
  if (m) return `measured ${minute(m[1])}${m[2] ? `: ${m[2]}` : ''}`;
  const r = /^(reading \S+, deposited by .+?) and taken at (\S+?)(?:: (.*))?$/s.exec(note);
  return r ? `${r[1]}, taken ${minute(r[2])}${r[3] ? `: ${r[3]}` : ''}` : note;
}

/** What a person typed for a row: the panel keeps it as an Override under the reviewer name, at now. */
export interface ParameterChange {
  value: number | string;
  low: number | null;
  high: number | null;
  note: string | null;
}

/** A deposition's reading a person chose for a row, as the service listed it: the panel keeps its own value and unit. */
export type ChosenReading = Pick<DepositionReading, 'ref' | 'value' | 'unit' | 'by' | 'at'>;

interface ParameterRowProps {
  spec: ParameterSpec;
  /** The value as the service served or resolved it, or as the person's override gives it while the service has not answered. */
  value: ParameterValue | null;
  /** This browser's override of the parameter, when a person made one. */
  override: Override | null;
  /** The reviewer name edits are kept under; empty disables every edit control. */
  reviewer: string;
  /** Show the value and its source alone. */
  readOnly?: boolean;
  /** The service's warning when the value lies outside its bounds (kept, never clamped). */
  warning: string | null;
  /** What a record-bound value's link opens; by default the records as citation chips. */
  records?: ReactNode;
  onSet: (change: ParameterChange) => void;
  onReset: () => void;
  /** Offer the project's readings deposited at the bench this parameter may take, beside a typed value (a Proforma scenario's panel). */
  offersReadings?: boolean;
  /** The scope the row belongs to: it names the row's group of reading choices. */
  scope?: string;
  /** A reading the person chose, with why it stands for the parameter in their words: the panel keeps it as the override. */
  onRead?: (reading: ChosenReading, note: string | null) => void;
}

/** Where the settings that hold the reviewer name live. */
const REVIEWER_SETTINGS = '/settings/corpus';

/**
 * A citation chip inside the panel as a bench-sized touch target
 * (OF-BLD-020 §2.R, finding 11): CitationChip's own trigger is a 12 px line,
 * so the panel, and the records a caller renders into it, give it this.
 */
export const TOUCH_CHIP = 'min-h-[44px] inline-flex items-center';

/** A value in the row's own words: a number formatted, words as they are, nothing as a dash. */
export const shown = (v: number | string | null | undefined, digits = 4): string => (v == null ? '—' : typeof v === 'number' ? fmt(v, digits) : v);

/** A unit as the row prints it: a share has none of its own. */
const unitWords = (spec: ParameterSpec): string => spec.unit || (spec.dimension === 'fraction' ? 'share' : '');

/** One entry of a source rule, in words. */
export function ruleWords(entry: string, spec: ParameterSpec): string {
  if (entry.startsWith('record:')) return `records of ${entry.slice('record:'.length)} through the aggregate gate`;
  switch (entry) {
    case 'fit':
      return 'a fermOS fit a person chose';
    case 'artifact':
      return 'a kept artifact';
    case 'simulation':
      return 'a kept simulation';
    case 'assumption':
      return 'a named person’s assumption, a model’s estimate, or a reading deposited at the bench';
    case 'convention':
      return spec.convention != null ? `a stated convention: ${shown(spec.convention)}` : 'a stated convention';
    case 'library-default':
      return 'the library’s own default, read from its code';
    default:
      return entry;
  }
}

/** Which entry of the rule answered: the value's origin, the record field its words name, a person's change over all. */
export function answered(entry: string, spec: ParameterSpec, value: ParameterValue | null): boolean {
  if (!value || value.origin === 'waiting') return false;
  if (value.overriddenBy) return entry === 'assumption';
  if (value.origin !== 'record') return entry === value.origin;
  // The records' field is the one the service's words name, else the rule's first.
  const fields = spec.sourceRule.filter((e) => e.startsWith('record:'));
  return entry === (fields.find((e) => (value.detail ?? '').includes(e.slice('record:'.length))) ?? fields[0]);
}

/** The bounds in words, as the spec states them. */
function boundsWords(spec: ParameterSpec): string {
  const u = unitWords(spec);
  const unit = u && u !== 'share' ? ` ${u}` : '';
  if (spec.min != null && spec.max != null) return `${shown(spec.min, 6)} to ${shown(spec.max, 6)}${unit}`;
  if (spec.min != null) return `at least ${shown(spec.min, 6)}${unit}`;
  if (spec.max != null) return `at most ${shown(spec.max, 6)}${unit}`;
  return 'none';
}

/** The interval a value carries, when it has one wider than itself. */
const intervalOf = (v: ParameterValue | null): [number, number] | null =>
  v && v.low != null && v.high != null && v.low !== v.high ? [v.low, v.high] : null;

/** The source chip: where the value came from, with its link. */
export function SourceChip({ value, records }: { value: ParameterValue | null; records?: ReactNode }) {
  if (!value) return <span className="chip text-ink-soft" data-testid="param-chip" data-origin="unknown">asking the service</span>;
  const id = value.source?.id ?? null;
  const linkClass = 'chip font-num hover:text-accent underline-offset-2 inline-flex items-center min-h-[44px]';
  switch (value.origin) {
    case 'fit':
      return id ? (
        <a className={linkClass} href={href(`/biorepo/artifacts/${id}`)} data-testid="param-chip" data-origin="fit">
          fitted · artifact {id}
          {value.identified === false ? ' · not identified' : ''}
        </a>
      ) : (
        <span className="chip" data-testid="param-chip" data-origin="fit">
          fitted
        </span>
      );
    case 'artifact':
    case 'simulation':
      return id ? (
        <a className={linkClass} href={href(`/biorepo/artifacts/${id}`)} data-testid="param-chip" data-origin={value.origin}>
          {value.origin} {id}
        </a>
      ) : (
        <span className="chip" data-testid="param-chip" data-origin={value.origin}>
          {value.origin}
        </span>
      );
    case 'record': {
      const n = value.recordIds.length;
      const span = intervalOf(value);
      return (
        <details className="inline-block align-top open:basis-full" data-testid="param-records">
          <summary className="list-none cursor-pointer inline-flex items-center min-h-[44px]">
            <span className="chip hover:text-accent" data-testid="param-chip" data-origin="record">
              record ×{n}
              {span ? (
                <span className="font-num">
                  &nbsp;{shown(span[0])}–{shown(span[1])}
                </span>
              ) : value.value != null ? (
                <span className="font-num">&nbsp;{shown(value.value)}</span>
              ) : null}
            </span>
          </summary>
          <div className="flex flex-col gap-1 mt-1">
            {records ??
              value.recordIds.map((rid) => <CitationChip key={rid} recordId={rid} className={TOUCH_CHIP} />)}
          </div>
        </details>
      );
    }
    case 'assumption':
      return (
        <span className="chip" data-testid="param-chip" data-origin="assumption">
          assumption by {value.overriddenBy ?? value.source?.by ?? 'nobody named'}
        </span>
      );
    case 'model-estimate':
      return (
        <span className="chip" data-testid="param-chip" data-origin="model-estimate">
          estimate by {value.overriddenBy ?? value.source?.by ?? 'no model named'}
        </span>
      );
    case 'measurement': {
      // A deposition's reading (alpha 2.2 C.5): its source names it, `<deposition id>/<entry id>`, and links to the
      // deposition's record.
      const who = value.overriddenBy ?? value.source?.by ?? 'nobody named';
      const reading = readingOf(id);
      return reading ? (
        <a className={linkClass} href={href(depositionPath(reading.deposition, reading.entry))} data-testid="param-chip" data-origin="measurement" data-ref={id ?? ''}>
          measured · deposited by {who} · reading {id}
        </a>
      ) : (
        <span className="chip" data-testid="param-chip" data-origin="measurement">
          measured · deposited by {who}
        </span>
      );
    }
    case 'convention':
      return (
        <span className="chip" data-testid="param-chip" data-origin="convention">
          convention
        </span>
      );
    case 'library-default':
      return (
        <span className="chip" data-testid="param-chip" data-origin="library-default">
          library default
        </span>
      );
    case 'not-read':
      // The other values leave it unread (a fed-batch's μset under a constant feed): it waits for nothing (OF-BLD-020 §3.R).
      return (
        <span className="chip text-ink-soft" data-testid="param-chip" data-origin="not-read">
          not read here
        </span>
      );
    default:
      return (
        <span className="chip text-signal-warn" data-testid="param-chip" data-origin="waiting">
          waiting
        </span>
      );
  }
}

/** Why: the gloss, the source chain in its order with the one that answered, the bounds and their reason, the library's default. */
function Why({ spec, value }: { spec: ParameterSpec; value: ParameterValue | null }) {
  return (
    <details className="mt-1" data-testid="param-why">
      <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">Why</summary>
      <dl className="text-caption space-y-1.5 mt-1 max-w-3xl">
        <div>
          <dt className="font-medium">What it means</dt>
          <dd className="text-ink-soft">
            {spec.gloss || spec.label}
            {spec.symbol && <span className="font-num"> ({spec.symbol})</span>}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Where its value comes from, the first that has one</dt>
          <dd>
            <ol className="list-decimal pl-5 text-ink-soft">
              {spec.sourceRule.map((e) => {
                const hit = answered(e, spec, value);
                return (
                  <li key={e} data-testid="param-why-source" data-answered={hit ? 'true' : 'false'} className={cx(hit && 'text-ink font-medium')}>
                    {ruleWords(e, spec)}
                    {hit && ' — this one answered'}
                  </li>
                );
              })}
            </ol>
            {value?.overriddenBy && value.origin === 'measurement' && (
              <p className="text-ink-soft mt-0.5">
                A value set for the run wins over every source: this one is a reading {value.overriddenBy} deposited at the bench, and a run&rsquo;s
                basis names the reading.
              </p>
            )}
            {value?.overriddenBy && value.origin === 'model-estimate' && (
              <p className="text-ink-soft mt-0.5">
                A value set for the run wins over every source: this one is an estimate by {value.overriddenBy}, a model&rsquo;s, and a
                run&rsquo;s basis names it as one.
              </p>
            )}
            {value?.overriddenBy && value.origin !== 'measurement' && value.origin !== 'model-estimate' && (
              <p className="text-ink-soft mt-0.5">
                A person&rsquo;s change wins over every source: this value is {value.overriddenBy}&rsquo;s assumption, and a run&rsquo;s basis
                names it.
              </p>
            )}
            {value?.origin === 'waiting' && <p className="text-signal-warn mt-0.5">None has a value yet.</p>}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Bounds</dt>
          <dd className="text-ink-soft">
            <span className="font-num">{boundsWords(spec)}</span>: {plainNote(spec.boundsReason)}. A value outside them is kept as typed, and the
            panel says so.
          </dd>
        </div>
        {value?.libraryDefault != null && (
          <div>
            <dt className="font-medium">The library&rsquo;s own default</dt>
            <dd className="font-num text-ink-soft">
              {shown(value.libraryDefault)} {unitWords(spec)}
            </dd>
          </div>
        )}
        {spec.note && (
          <div>
            <dt className="font-medium">Note</dt>
            <dd className="text-ink-soft" title={spec.note}>{plainNote(spec.note)}</dd>
          </div>
        )}
        {value?.detail && (
          <div>
            <dt className="font-medium">What the service says of this value</dt>
            <dd className="text-ink-soft" title={value.detail}>{plainNote(value.detail)}</dd>
          </div>
        )}
      </dl>
    </details>
  );
}

/** A number box that keeps what a person is typing until it is a number, then keeps it. */
function NumberBox({
  label,
  value,
  disabled,
  onNumber,
  onEmpty,
  testId,
}: {
  label: string;
  value: number | null;
  disabled: boolean;
  onNumber: (n: number) => void;
  onEmpty?: () => void;
  testId: string;
}) {
  const [draft, setDraft] = useState(value == null ? '' : String(value));
  const [editing, setEditing] = useState(false);
  useEffect(() => {
    if (!editing) setDraft(value == null ? '' : String(value));
  }, [value, editing]);
  return (
    <input
      type="number"
      step="any"
      inputMode="decimal"
      className="input w-[120px] min-h-[44px] font-num"
      aria-label={label}
      data-testid={testId}
      value={draft}
      disabled={disabled}
      onFocus={() => setEditing(true)}
      onBlur={() => setEditing(false)}
      onChange={(e) => {
        const text = e.target.value;
        setDraft(text);
        if (text.trim() === '') {
          onEmpty?.();
          return;
        }
        const n = Number(text);
        if (Number.isFinite(n)) onNumber(n);
      }}
    />
  );
}

/** Steps of a slider on a log scale: the position is a share of the decades between the bounds. */
const LOG_STEPS = 1000;

/** The slider, inside the spec's bounds (the caller draws one only for a spec with both) and on its scale; a way of choosing a number and nothing more. */
function Slider({
  spec,
  min,
  max,
  value,
  disabled,
  onNumber,
}: {
  spec: ParameterSpec;
  min: number;
  max: number;
  value: number | null;
  disabled: boolean;
  onNumber: (n: number) => void;
}) {
  const log = spec.scale === 'log' && min > 0 && max > min;
  const label = `${spec.label} slider`;
  if (log) {
    const span = Math.log(max / min);
    const pos = value == null || value <= 0 ? 0 : Math.round((Math.log(value / min) / span) * LOG_STEPS);
    return (
      <input
        type="range"
        className="touch-range w-full min-h-[44px]"
        aria-label={label}
        aria-valuetext={value == null ? 'no value yet' : `${shown(value)} ${unitWords(spec)}`}
        data-testid="param-slider"
        data-scale="log"
        min={0}
        max={LOG_STEPS}
        step={1}
        value={Math.max(0, Math.min(LOG_STEPS, pos))}
        disabled={disabled}
        onChange={(e) => onNumber(Number((min * Math.exp((Number(e.target.value) / LOG_STEPS) * span)).toPrecision(4)))}
      />
    );
  }
  return (
    <input
      type="range"
      className="touch-range w-full min-h-[44px]"
      aria-label={label}
      aria-valuetext={value == null ? 'no value yet' : `${shown(value)} ${unitWords(spec)}`}
      data-testid="param-slider"
      data-scale="linear"
      min={min}
      max={max}
      step={spec.step ?? (max - min) / 200}
      value={value == null ? min : Math.max(min, Math.min(max, value))}
      disabled={disabled}
      onChange={(e) => onNumber(Number(Number(e.target.value).toPrecision(6)))}
    />
  );
}

/** The readings of the row's unit as the service listed them: null while it is asked, with its words when it could not answer. */
type Listed = { readings: DepositionReading[] | null; problem: string | null };

const listedProblem = (e: unknown) =>
  e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e);

/**
 * A reading deposited at the bench, as a row offers one (alpha 2.2 E.17): on first opening, the project's readings
 * this parameter may take in its unit or one that converts into it, as the service's lookup lists them, each said as
 * what it measured and what it would set; the one the row is set to is checked. Choosing one keeps it, with why it
 * stands for the parameter in the person's words, through `onRead`.
 */
function Readings({
  spec,
  override,
  scope,
  disabled,
  onRead,
}: {
  spec: ParameterSpec;
  override: Override | null;
  scope: string;
  disabled: boolean;
  onRead: (reading: ChosenReading, note: string | null) => void;
}) {
  const reading = override?.origin === 'measurement' ? override : null;
  const [open, setOpen] = useState(reading !== null);
  const [listed, setListed] = useState<Listed | null>(null);
  // Why a reading stands for the parameter, typed before one is chosen; a chosen one keeps its own on the override.
  const [draft, setDraft] = useState('');
  const asked = useRef(false);
  useEffect(() => {
    if (!open || asked.current) return;
    asked.current = true;
    setListed({ readings: null, problem: null });
    depositionReadings(spec.unit).then(
      (readings) => setListed({ readings, problem: null }),
      (e: unknown) => setListed({ readings: [], problem: listedProblem(e) }),
    );
  }, [open, spec.unit]);
  const note = reading ? (reading.note ?? '') : draft;
  const unit = spec.unit || 'no unit';
  // Said gone only when the service answered with a listing that lacks it; a listing it could not give says nothing of it.
  const gone = readingLeftTheList(reading, listed);
  const chosen = (r: ChosenReading): ChosenReading => ({ ref: r.ref, value: r.value, unit: r.unit, by: r.by, at: r.at });
  return (
    <details
      className="mt-1"
      data-testid="param-readings"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">
        A reading deposited at the bench
      </summary>
      <div className="mt-1 space-y-1 text-caption" data-unit={spec.unit}>
        {!listed || listed.readings === null ? (
          <p className="text-ink-soft">Asking the service for the project&rsquo;s readings in {unit}…</p>
        ) : listed.problem ? (
          <p className="text-signal-warn" data-testid="param-readings-problem">
            {listed.problem}
          </p>
        ) : listed.readings.length === 0 ? (
          <p className="text-ink-soft" data-testid="param-no-reading">
            No confirmed reading of this project is in {unit} or in a unit that converts into it. A reading is deposited at the bench on a
            locked runbook, from its page, and read back there.
          </p>
        ) : (
          listed.readings.map((r) => (
            <ReadingChoice
              key={r.ref}
              reading={r}
              label={spec.label}
              unit={spec.unit}
              name={`param-reading-${scope}-${spec.key}`}
              chosen={reading?.ref === r.ref}
              disabled={disabled}
              onChoose={() => onRead(chosen(r), note || null)}
              testid="param-reading"
            />
          ))
        )}
        {reading?.chosenBy && (
          <p className="text-ink-soft" data-testid="param-reading-chosen">
            {reading.chosenBy} chose reading <span className="font-num">{reading.ref}</span> for {spec.label}, deposited by {reading.by}.
          </p>
        )}
        {reading && gone && (
          <p className="text-signal-warn" data-testid="param-reading-gone" data-ref={reading.ref ?? ''}>
            This value is set to reading <span className="font-num">{reading.ref}</span>, which has left the readings the service lists in{' '}
            {unit}; the service&rsquo;s words above say why. Choose another reading here, type your own value, or reset it to its source.
          </p>
        )}
        <p className="text-ink-soft">
          The service sets a reading in this parameter&rsquo;s unit each time it is sent, and holds its unit to this parameter&rsquo;s. Which
          measure stands for {spec.label} is your choice, kept in your name with the scenario.
        </p>
        <input
          className="input w-full min-h-[44px]"
          aria-label={`Why the reading stands for ${spec.label}`}
          placeholder="Why this reading stands for it (optional)"
          data-testid="param-reading-note"
          value={note}
          disabled={disabled}
          onChange={(e) => {
            const text = e.target.value;
            if (reading?.ref && typeof reading.value === 'number')
              onRead({ ref: reading.ref, value: reading.value, unit: reading.unit ?? spec.unit, by: reading.by, at: reading.at }, text || null);
            else setDraft(text);
          }}
        />
      </div>
    </details>
  );
}

export function ParameterRow({
  spec,
  value,
  override,
  reviewer,
  readOnly,
  warning,
  records,
  onSet,
  onReset,
  offersReadings = false,
  scope = '',
  onRead,
}: ParameterRowProps) {
  const labelId = useId();
  const named = reviewer.trim() !== '';
  // A person may change a parameter whose rule takes a person's value; a
  // convention stated in words, or a library's default alone, is shown.
  const editable = !readOnly && spec.sourceRule.includes('assumption');
  const words = spec.choices != null;
  // A reading set on the row is its one value: Your value stays empty, and a person's change builds on no part of it.
  const read = override?.origin === 'measurement';
  const own = read ? null : override;
  const typed = own && typeof own.value === 'number' ? own.value : null;
  const current = typeof value?.value === 'number' ? value.value : null;
  const interval = intervalOf(value);
  const keep = (change: Partial<ParameterChange>) =>
    onSet({
      value: change.value ?? own?.value ?? '',
      low: change.low !== undefined ? change.low : own?.low ?? null,
      high: change.high !== undefined ? change.high : own?.high ?? null,
      note: change.note !== undefined ? change.note : own?.note ?? null,
    });
  return (
    <div
      role="group"
      aria-labelledby={labelId}
      className={cx('border-t border-line/60 py-2', warning && 'bg-signal-warn/[0.05]')}
      data-testid="param-row"
      data-key={spec.key}
      data-origin={value?.origin ?? 'unknown'}
      data-overridden={override ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span id={labelId} className="font-medium text-body">
          {spec.label}
        </span>
        {spec.symbol && <span className="font-num text-ink-soft">{spec.symbol}</span>}
        <span className="font-num text-body" data-testid="param-value">
          {shown(value?.value)}
          {unitWords(spec) && value?.value != null && typeof value.value === 'number' && <span className="text-ink-soft"> {unitWords(spec)}</span>}
        </span>
        {interval && (
          <span className="font-num text-caption text-ink-soft" data-testid="param-interval">
            ({shown(interval[0])}–{shown(interval[1])})
          </span>
        )}
        <SourceChip value={value} records={records} />
        {override && (
          <Button onClick={onReset} className="min-h-[44px]" data-testid="param-reset">
            Reset to source
          </Button>
        )}
      </div>
      {value?.detail && value.origin !== 'assumption' && value.origin !== 'model-estimate' && (
        <p className="text-caption text-ink-soft mt-0.5" data-testid="param-detail">
          {value.origin === 'measurement' ? measuredWords(value.detail) : plainNote(value.detail)}
        </p>
      )}
      {warning && (
        <p className="text-caption text-signal-warn mt-0.5" role="status" data-testid="param-warning">
          {warning}
        </p>
      )}
      {editable && !named && (
        <p className="text-caption text-ink-soft mt-0.5" data-testid="param-need-reviewer">
          <a className="text-accent hover:underline inline-flex items-center min-h-[44px]" href={href(REVIEWER_SETTINGS)}>
            Set a reviewer name in Settings
          </a>{' '}
          to change it: a change is a named assumption.
        </p>
      )}
      {editable && (
        <div className="mt-1 flex flex-wrap items-end gap-3" data-testid="param-edit">
          {words ? (
            <label className="text-caption text-ink-soft">
              <span className="block">Your choice</span>
              <select
                className="input min-h-[44px]"
                aria-label={`${spec.label} choice`}
                data-testid="param-choice"
                disabled={!named}
                value={typeof override?.value === 'string' ? override.value : typeof value?.value === 'string' ? value.value : ''}
                onChange={(e) => keep({ value: e.target.value, low: null, high: null })}
              >
                <option value="" disabled>
                  —
                </option>
                {(spec.choices ?? []).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="text-caption text-ink-soft">
                <span className="block">Your value{unitWords(spec) ? ` (${unitWords(spec)})` : ''}</span>
                <NumberBox label={`${spec.label} value`} testId="param-value-input" value={typed} disabled={!named} onNumber={(n) => keep({ value: n })} />
              </label>
              {spec.min != null && spec.max != null && spec.max > spec.min && (
                <label className="text-caption text-ink-soft flex-1 min-w-[160px]">
                  <span className="block">
                    Within <span className="font-num">{boundsWords(spec)}</span>
                  </span>
                  <Slider spec={spec} min={spec.min} max={spec.max} value={typed ?? current} disabled={!named} onNumber={(n) => keep({ value: n })} />
                </label>
              )}
            </>
          )}
        </div>
      )}
      {editable && !words && offersReadings && onRead && (
        <Readings spec={spec} override={override} scope={scope} disabled={!named} onRead={onRead} />
      )}
      {editable && !words && !read && (
        <details className="mt-1" data-testid="param-more">
          <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">
            Its low, its high, and what it rests on
          </summary>
          {!override && <p className="text-caption text-ink-soft">Type a value first; its low, its high and what it rests on are kept with it.</p>}
          <div className="flex flex-wrap items-end gap-3 mt-1">
            <label className="text-caption text-ink-soft">
              <span className="block">Low</span>
              <NumberBox
                label={`${spec.label} low`}
                testId="param-low-input"
                value={override?.low ?? null}
                disabled={!named || !override}
                onNumber={(n) => keep({ low: n })}
                onEmpty={() => override && keep({ low: null })}
              />
            </label>
            <label className="text-caption text-ink-soft">
              <span className="block">High</span>
              <NumberBox
                label={`${spec.label} high`}
                testId="param-high-input"
                value={override?.high ?? null}
                disabled={!named || !override}
                onNumber={(n) => keep({ high: n })}
                onEmpty={() => override && keep({ high: null })}
              />
            </label>
            <label className="text-caption text-ink-soft flex-1 min-w-[200px]">
              <span className="block">What it rests on</span>
              <input
                className="input w-full min-h-[44px]"
                aria-label={`${spec.label} basis`}
                data-testid="param-note-input"
                value={override?.note ?? ''}
                disabled={!named || !override}
                onChange={(e) => keep({ note: e.target.value || null })}
              />
            </label>
          </div>
        </details>
      )}
      <Why spec={spec} value={value} />
    </div>
  );
}
