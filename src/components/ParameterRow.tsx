// One parameter in the panel (OF-BLD-020 §2.2, D2–D4). ParameterPanel.tsx
// renders one of these per `ParameterSpec`; no screen writes a form for a
// parameter of its own (E.1‴: `check:seed` fails on a numeric control in a
// module's screens outside these two files).
//
// The row COMPUTES NOTHING. The value, its interval, its source, the bounds
// and their reason, the warning outside them and the words that explain a
// value all came from the service (`ParamScope`, `ParamResolveResult`);
// the override's value, interval and note came from the person who typed
// them. A slider is a way of choosing a number inside the spec's bounds and
// nothing more: a typed value outside them is kept, never clamped (D4), and
// the service's warning says so on the row.
//
// The bench may use it (pureOS's Builder, fermOS at the fermenter), so the
// constraints Deposition.tsx's header lists hold here too: every control is
// labelled, every touch target is at least 44 px (the citation chips a
// record-bound row opens included, through TOUCH_CHIP), nothing appears only
// on hover (Why and the records are disclosures a key or a tap opens), and
// the keyboard reaches every control. check:store walks these files, and the
// records Proforma renders into a row, for it.
import { useEffect, useId, useState, type ReactNode } from 'react';
import type { Override, ParameterSpec, ParameterValue } from '@/data/types';
import { href } from '@/router';
import { fmt } from '@/engine/units';
import { CitationChip } from './Chip';
import { Button, cx } from './ui';

/** What a person typed for a row: the panel keeps it as an Override under the reviewer name, at now. */
export interface ParameterChange {
  value: number | string;
  low: number | null;
  high: number | null;
  note: string | null;
}

export interface ParameterRowProps {
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
}

/** Where the settings that hold the reviewer name live. */
export const REVIEWER_SETTINGS = '/settings/corpus';

/**
 * A citation chip inside the panel as a bench-sized touch target
 * (OF-BLD-020 §2.R, finding 11): CitationChip's own trigger is a 12 px line,
 * so the panel, and the records a caller renders into it, give it this.
 */
export const TOUCH_CHIP = 'min-h-[44px] inline-flex items-center';

/** A value in the row's own words: a number formatted, words as they are, nothing as a dash. */
export const shown = (v: number | string | null | undefined, digits = 4): string => (v == null ? '—' : typeof v === 'number' ? fmt(v, digits) : v);

/** A unit as the row prints it: a share has none of its own. */
export const unitWords = (spec: ParameterSpec): string => spec.unit || (spec.dimension === 'fraction' ? 'share' : '');

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
      return 'a named person’s assumption';
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
export function boundsWords(spec: ParameterSpec): string {
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
              value.recordIds.map((rid) => <CitationChip key={rid} recordId={rid} label={rid} className={TOUCH_CHIP} />)}
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
            {value?.overriddenBy && (
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
            <span className="font-num">{boundsWords(spec)}</span>: {spec.boundsReason}. A value outside them is kept as typed, and the
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
            <dd className="text-ink-soft">{spec.note}</dd>
          </div>
        )}
        {value?.detail && (
          <div>
            <dt className="font-medium">What the service says of this value</dt>
            <dd className="text-ink-soft">{value.detail}</dd>
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

/** The slider, inside the spec's bounds and on its scale; a way of choosing a number and nothing more. */
function Slider({ spec, value, disabled, onNumber }: { spec: ParameterSpec; value: number | null; disabled: boolean; onNumber: (n: number) => void }) {
  const min = spec.min as number;
  const max = spec.max as number;
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

export function ParameterRow({ spec, value, override, reviewer, readOnly, warning, records, onSet, onReset }: ParameterRowProps) {
  const labelId = useId();
  const named = reviewer.trim() !== '';
  // A person may change a parameter whose rule takes a person's value; a
  // convention stated in words, or a library's default alone, is shown.
  const editable = !readOnly && spec.sourceRule.includes('assumption');
  const words = spec.choices != null;
  const typed = override && typeof override.value === 'number' ? override.value : null;
  const current = typeof value?.value === 'number' ? value.value : null;
  const interval = intervalOf(value);
  const keep = (change: Partial<ParameterChange>) =>
    onSet({
      value: change.value ?? override?.value ?? '',
      low: change.low !== undefined ? change.low : override?.low ?? null,
      high: change.high !== undefined ? change.high : override?.high ?? null,
      note: change.note !== undefined ? change.note : override?.note ?? null,
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
      {value?.detail && value.origin !== 'assumption' && (
        <p className="text-caption text-ink-soft mt-0.5" data-testid="param-detail">
          {value.detail}
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
                  <Slider spec={spec} value={typed ?? current} disabled={!named} onNumber={(n) => keep({ value: n })} />
                </label>
              )}
            </>
          )}
        </div>
      )}
      {editable && !words && (
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
