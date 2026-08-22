// The panel that makes a bioSTEAM unit's attributes editable.
//
// Everything downstream of this panel is live. Moving a residence time or
// swapping a vessel material re-runs the mass balance, re-sizes the train,
// re-costs it at the current CE index and re-solves the minimum selling price,
// which is the whole argument of the plant screen: a techno-economic model you
// cannot push on is a slideshow.
//
// The contract with the parent is that `specs` carries the flowsheet's own
// values — what the model says before anybody touched it — and `overrides`
// carries the reader's edits on top. Keeping the two apart is what lets this
// panel say which numbers are yours, and a control that cannot tell you it has
// been touched is a control you stop trusting.
//
// Re-simulation timing is not this component's business. Every commit is
// reported immediately; the parent decides whether to debounce before it pays
// for a solve.
import { useEffect, useId, useState, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw, Table2, Undo2 } from 'lucide-react';
import type { UnitResult } from '@/engine/biosteam/types';
import type { UnitSpec } from '@/engine/biosteam/unit';
import { fmt } from '@/engine/units';
import { money } from '@/lib/money';
import { Button, EmptyState, Explain, cx } from '@/components/ui';

/**
 * The marker a spec uses when the attribute is ours rather than upstream's.
 *
 * bioSTEAM has no photobioreactor and no membrane skid, so the units that model
 * them expose attributes the library has never heard of. Letting those sit in
 * the same monospace as `tau` would quietly borrow authority the number has not
 * earned, and this repo draws that line everywhere else it appears.
 */
const AUTHORED = '—';


/** The value a control should show: the reader's edit if there is one. */
function currentValue(spec: UnitSpec, overrides: Record<string, number | string>): number | string {
  const edit = overrides[spec.key];
  return edit === undefined ? spec.value : edit;
}

/**
 * Whether a spec is showing something other than the model's own value.
 *
 * Compared by value rather than by the presence of a key, so reverting a
 * control by writing the default back reads as untouched — which is what the
 * reader means by reverting it.
 */
function isModified(spec: UnitSpec, overrides: Record<string, number | string>): boolean {
  return currentValue(spec, overrides) !== spec.value;
}

/** The attribute name, or the mark that this app added the attribute. */
function AttributeName({ spec, id }: { spec: UnitSpec; id: string }): JSX.Element {
  if (spec.biosteamName === AUTHORED) {
    return (
      <span
        id={id}
        className="chip chip-warn"
        title="openFerment added this attribute. bioSTEAM has no equivalent, so nothing upstream stands behind it."
      >
        authored attribute
      </span>
    );
  }
  return (
    <span id={id} className="font-num text-caption text-ink-soft" title="bioSTEAM attribute name">
      {spec.biosteamName}
    </span>
  );
}

function ControlHeader({
  spec,
  labelFor,
  attrId,
  modified,
  onRevert,
}: {
  spec: UnitSpec;
  labelFor: string;
  attrId: string;
  modified: boolean;
  onRevert: () => void;
}): JSX.Element {
  return (
    <div className="flex items-baseline justify-between gap-x-3 gap-y-1 flex-wrap">
      <div className="flex items-baseline gap-2 flex-wrap min-w-0">
        <label htmlFor={labelFor} className="text-body">
          {spec.label}
        </label>
        <AttributeName spec={spec} id={attrId} />
      </div>
      {modified && (
        <div className="flex items-center gap-1.5">
          <span className="chip chip-active">modified</span>
          <Button
            size="sm"
            onClick={onRevert}
            aria-label={`Revert ${spec.label} to the model default of ${fmt(spec.value)} ${spec.units}`.trim()}
          >
            <Undo2 size={12} /> Revert
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * A number, offered twice: a slider for the feel of it and a field for the
 * exact figure.
 *
 * The field is not clamped to the correlation's range. A reader who types a
 * volume past the upper bound is asking a real question — bioSTEAM answers it
 * by splitting the duty across parallel units and saying so — and blocking the
 * keystroke would hide the answer. The bound is shown instead, in the warn hue.
 */
function NumberControl({
  spec,
  value,
  modified,
  onChange,
  onRevert,
}: {
  spec: UnitSpec;
  value: number;
  modified: boolean;
  onChange: (key: string, value: number | string) => void;
  onRevert: () => void;
}): JSX.Element {
  const base = useId();
  const fieldId = `${base}-value`;
  const rangeId = `${base}-range`;
  const attrId = `${base}-attr`;
  const noteId = `${base}-note`;

  // The field holds text while it is being typed, because "1." and "-" are
  // states a number cannot represent and clobbering them mid-keystroke makes
  // the input fight the reader.
  const [draft, setDraft] = useState(() => String(value));
  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const min = spec.min ?? 0;
  const max = spec.max ?? Math.max(min + 1, value * 2);
  const step = spec.step ?? (max - min) / 100;
  const outOfRange = value < min || value > max;
  const described = `${attrId} ${noteId}`;

  const commitText = (text: string): void => {
    setDraft(text);
    const n = Number(text);
    if (text.trim() === '' || !Number.isFinite(n)) return;
    onChange(spec.key, n);
  };

  return (
    <div className="py-3">
      <ControlHeader
        spec={spec}
        labelFor={fieldId}
        attrId={attrId}
        modified={modified}
        onRevert={onRevert}
      />
      <div className="mt-2 grid gap-x-3 gap-y-2 items-center sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0">
          <label htmlFor={rangeId} className="sr-only">
            {spec.label} slider
          </label>
          <input
            id={rangeId}
            type="range"
            min={min}
            max={max}
            step={step}
            value={Math.min(max, Math.max(min, value))}
            aria-describedby={described}
            onChange={(e) => {
              setDraft(e.target.value);
              onChange(spec.key, Number(e.target.value));
            }}
          />
        </div>
        <div className="flex items-center gap-2 justify-end">
          <input
            id={fieldId}
            type="number"
            inputMode="decimal"
            className={cx('input font-num text-right w-[8.5rem]', outOfRange && 'border-signal-warn')}
            min={spec.min}
            max={spec.max}
            step={step}
            value={draft}
            aria-describedby={described}
            onChange={(e) => commitText(e.target.value)}
          />
          {spec.units && (
            <span className="text-caption text-ink-soft whitespace-nowrap w-[5rem]">{spec.units}</span>
          )}
        </div>
      </div>
      <p id={noteId} className="text-caption text-ink-soft mt-1.5">
        {spec.note}
        {modified && (
          <span className="ml-1">
            Model default <span className="font-num">{fmt(spec.value)}</span>.
          </span>
        )}
      </p>
      {outOfRange && (
        <p className="text-caption text-signal-warn mt-1 flex items-start gap-1.5">
          <AlertTriangle size={12} className="mt-[2px] shrink-0" />
          <span>
            Outside the range this attribute is offered over (
            <span className="font-num">
              {fmt(min)}–{fmt(max)}
            </span>
            ). The plant will still size and cost at it, and any correlation pushed past its own
            bounds says so in the unit&rsquo;s warnings.
          </span>
        </p>
      )}
    </div>
  );
}

function SelectControl({
  spec,
  value,
  modified,
  onChange,
  onRevert,
}: {
  spec: UnitSpec;
  value: string;
  modified: boolean;
  onChange: (key: string, value: number | string) => void;
  onRevert: () => void;
}): JSX.Element {
  const base = useId();
  const fieldId = `${base}-value`;
  const attrId = `${base}-attr`;
  const noteId = `${base}-note`;
  const options = spec.options ?? [];

  return (
    <div className="py-3">
      <ControlHeader
        spec={spec}
        labelFor={fieldId}
        attrId={attrId}
        modified={modified}
        onRevert={onRevert}
      />
      <div className="mt-2 max-w-sm">
        <select
          id={fieldId}
          className="input"
          value={value}
          aria-describedby={`${attrId} ${noteId}`}
          onChange={(e) => onChange(spec.key, e.target.value)}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <p id={noteId} className="text-caption text-ink-soft mt-1.5">
        {spec.note}
        {modified && (
          <span className="ml-1">
            Model default <span className="font-num">{String(spec.value)}</span>.
          </span>
        )}
      </p>
    </div>
  );
}

function HeaderChip({ children, warn }: { children: ReactNode; warn?: boolean }): JSX.Element {
  return <span className={cx('chip', warn ? 'chip-warn' : 'text-ink-soft')}>{children}</span>;
}

export function UnitSpecEditor({
  unit,
  specs,
  overrides,
  onChange,
  onReset,
}: {
  unit: UnitResult;
  specs: UnitSpec[];
  overrides: Record<string, number | string>;
  onChange: (key: string, value: number | string) => void;
  onReset: () => void;
}): JSX.Element {
  const modifiedKeys = specs.filter((s) => isModified(s, overrides)).map((s) => s.key);
  const modifiedCount = modifiedKeys.length;
  const hasAuthored = specs.some((s) => s.biosteamName === AUTHORED);

  return (
    <div>
      <div className="flex items-start justify-between gap-x-6 gap-y-2 flex-wrap pb-3 border-b border-line">
        <div className="min-w-0">
          <h3 className="font-serif text-section-title font-semibold leading-tight">
            <span className="font-num">{unit.ID}</span>{' '}
            <span className="font-sans font-normal text-body text-ink-soft">{unit.line}</span>
          </h3>
          <div className="flex items-center gap-2 flex-wrap mt-1.5">
            <span className="text-caption text-ink-soft">
              Area <span className="font-num">{unit.area}</span> · {unit.areaName}
            </span>
            <HeaderChip warn={unit.costSource === 'authored'}>
              {unit.costSource === 'biosteam' ? 'bioSTEAM correlation' : 'authored correlation'}
            </HeaderChip>
          </div>
        </div>
        <div className="text-right">
          <div className="text-caption uppercase tracking-wide text-ink-soft">Installed cost</div>
          <div className="font-num text-display leading-tight">{money(unit.installedCost)}</div>
          <div className="text-caption text-ink-soft mt-0.5">
            purchase <span className="font-num">{money(unit.purchaseCost)}</span>
          </div>
        </div>
      </div>

      {modifiedCount > 0 ? (
        <div className="mt-3 flex items-center justify-between gap-3 flex-wrap rounded-card border border-accent/40 bg-accent-wash px-3 py-2">
          <span className="text-caption">
            <span className="font-num">{modifiedCount}</span>{' '}
            {modifiedCount === 1 ? 'attribute differs' : 'attributes differ'} from what the flowsheet
            declares.
          </span>
          <Button size="sm" onClick={onReset}>
            <RotateCcw size={12} /> Reset unit to defaults
          </Button>
        </div>
      ) : (
        <p className="mt-3 text-caption text-ink-soft">
          Every attribute is at the flowsheet&rsquo;s own value. Changing one re-sizes this unit,
          re-costs the train and re-solves the selling price.
          {hasAuthored && (
            <>
              {' '}
              <Explain label="What is an authored attribute?">
                Attributes marked <span className="chip chip-warn">authored attribute</span> are ones
                openFerment added. bioSTEAM models no photobioreactor, no pulsed-electric-field
                disruptor and no membrane skid, so the units standing in for them expose settings the
                library has never had. They move the answer exactly as hard as the upstream ones do,
                with none of the same standing behind them.
              </Explain>
            </>
          )}
        </p>
      )}

      {specs.length === 0 ? (
        <EmptyState
          title="Nothing to set on this unit"
          body="This unit publishes no editable attributes: its size follows entirely from the streams reaching it."
        />
      ) : (
        <div className="mt-1 divide-y divide-line">
          {specs.map((spec) => {
            const value = currentValue(spec, overrides);
            const modified = isModified(spec, overrides);
            const revert = (): void => onChange(spec.key, spec.value);
            return spec.kind === 'select' ? (
              <SelectControl
                key={spec.key}
                spec={spec}
                value={String(value)}
                modified={modified}
                onChange={onChange}
                onRevert={revert}
              />
            ) : (
              <NumberControl
                key={spec.key}
                spec={spec}
                value={typeof value === 'number' ? value : Number(value)}
                modified={modified}
                onChange={onChange}
                onRevert={revert}
              />
            );
          })}
        </div>
      )}

      {specs.length > 0 && (
        <details className="mt-3">
          <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
            <Table2 size={12} /> View as table
          </summary>
          <div className="overflow-x-auto mt-1.5">
            <table className="w-full text-caption">
              <caption className="sr-only">
                Every editable attribute on {unit.ID}, with the value in force and the value the
                flowsheet declares.
              </caption>
              <thead>
                <tr className="border-b border-line text-ink-soft">
                  <th className="text-left py-1 pr-3 whitespace-nowrap">Setting</th>
                  <th className="text-left py-1 pr-3 whitespace-nowrap">Attribute</th>
                  <th className="text-right py-1 pr-3 whitespace-nowrap">Value</th>
                  <th className="text-right py-1 pr-3 whitespace-nowrap">Default</th>
                  <th className="text-left py-1 whitespace-nowrap">Units</th>
                </tr>
              </thead>
              <tbody>
                {specs.map((spec) => {
                  const modified = isModified(spec, overrides);
                  return (
                    <tr key={spec.key} className="border-b border-line/50">
                      <td className="py-1 pr-3">{spec.label}</td>
                      <td className="py-1 pr-3 font-num whitespace-nowrap">
                        {spec.biosteamName === AUTHORED ? 'authored' : spec.biosteamName}
                      </td>
                      <td
                        className={cx(
                          'py-1 pr-3 text-right font-num whitespace-nowrap',
                          modified && 'text-accent',
                        )}
                      >
                        {fmt(currentValue(spec, overrides))}
                      </td>
                      <td className="py-1 pr-3 text-right font-num whitespace-nowrap text-ink-soft">
                        {fmt(spec.value)}
                      </td>
                      <td className="py-1 whitespace-nowrap text-ink-soft">{spec.units || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {unit.warnings.length > 0 && (
        <ul className="mt-3 space-y-1" aria-label={`Design warnings for ${unit.ID}`}>
          {unit.warnings.map((w) => (
            <li key={w} className="text-caption text-signal-warn flex gap-1.5">
              <AlertTriangle size={12} className="mt-[3px] shrink-0" />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * bioSTEAM's `unit.results()`: what the sizing decided, and what it costs.
 *
 * The two halves are shown side by side because they answer different
 * questions and fail in different ways. A number wrong because the vessel came
 * out the wrong size is a different bug from one wrong because the correlation
 * was applied outside its bounds, and a table that merged them would hide which
 * one the reader has.
 */
export function DesignResultsTable({ unit }: { unit: UnitResult }): JSX.Element {
  const design = Object.entries(unit.design);
  const costs = Object.entries(unit.purchaseCosts);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <section className="min-w-0">
        <h4 className="text-caption uppercase tracking-wide text-ink-soft mb-1">Design results</h4>
        {design.length === 0 ? (
          <p className="text-caption text-ink-soft">This unit reports no design results.</p>
        ) : (
          <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3">
            {design.map(([k, d]) => (
              <div key={k} className="contents">
                <dt className="text-caption text-ink-soft py-1 border-b border-line/50">{k}</dt>
                <dd className="text-caption font-num text-right py-1 whitespace-nowrap border-b border-line/50">
                  {fmt(d.value)} <span className="text-ink-soft">{d.units}</span>
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section className="min-w-0">
        <h4 className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Purchase cost items
        </h4>
        {costs.length === 0 ? (
          <p className="text-caption text-ink-soft">This unit carries no purchase cost.</p>
        ) : (
          <>
            <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3">
              {costs.map(([k, v]) => {
                const N = unit.parallel[k] ?? 1;
                return (
                  <div key={k} className="contents">
                    <dt className="text-caption text-ink-soft py-1 border-b border-line/50">
                      {k}
                      {N > 1 && <span className="font-num"> ×{N}</span>}
                      <span className="text-ink-soft/70">
                        {' '}
                        · F<sub>BM</sub> <span className="font-num">{unit.F_BM[k] ?? 1}</span>
                      </span>
                    </dt>
                    <dd className="text-caption font-num text-right py-1 whitespace-nowrap border-b border-line/50">
                      {money(v * N)}
                    </dd>
                  </div>
                );
              })}
              <div className="contents">
                <dt className="text-caption py-1 font-medium">Installed</dt>
                <dd className="text-caption font-num text-right py-1 whitespace-nowrap font-medium">
                  {money(unit.installedCost)}
                </dd>
              </div>
            </dl>
            {unit.costBasis && <p className="text-caption text-ink-soft mt-2">{unit.costBasis}</p>}
          </>
        )}
      </section>
    </div>
  );
}
