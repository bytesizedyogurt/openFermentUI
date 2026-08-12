// The assumptions behind every number on the plant screen, made editable.
//
// A techno-economic result is a function of two things: the flowsheet, and the
// basis it is discounted and indexed against. The flowsheet gets a whole screen.
// The basis usually gets a footnote, which is how two plants end up compared at
// two different discount rates and nobody notices. This panel puts the basis in
// the same place as the equipment list and lets the reader push on it.
//
// Nothing here is authored by this app. Every field maps onto something
// `bst.settings` or a bioSTEAM TEA constructor already takes, and the utility
// table below is upstream's price list reproduced rather than summarised — a
// price is an assumption a reviewer is entitled to challenge, and they can only
// challenge the number the engine actually charges.
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { RotateCcw, Table2 } from 'lucide-react';
import { CEPCI_BY_YEAR, CEPCI_LATEST_YEAR } from '@/engine/biosteam/cepci';
import { DEPRECIATION_SCHEDULES } from '@/engine/biosteam/tea';
import {
  COOLING_AGENTS,
  ELECTRICITY_PRICE,
  HEATING_AGENTS,
  MINIMUM_APPROACH_DT,
  type UtilityAgent,
} from '@/engine/biosteam/utilities';
import { Button, Callout, Explain, cx } from '@/components/ui';

/**
 * The global and financial settings the whole plant is costed against.
 *
 * Fractions are stored as fractions — 0.1 is ten per cent — and displayed as
 * per cent. The two are never mixed in this file: every control that shows a
 * percentage scales on the way in and on the way out, and the label says which
 * unit the reader is looking at.
 */
export interface PlantSettings {
  /** CEPCI year the cost index is taken from. Null means `CE` was typed directly. */
  cepciYear: number | null;
  /** Chemical Engineering Plant Cost Index every correlation is scaled to. */
  CE: number;
  /** Operating days per year; sets the plant's annual operating hours. */
  operatingDays: number;
  /** Discount rate the minimum selling price is solved against, fraction. */
  IRR: number;
  /** Combined federal and state income tax, fraction. */
  incomeTax: number;
  /** Depreciation schedule name, e.g. 'MACRS7'. */
  depreciation: string;
  /** Working capital as a fraction of fixed capital investment. */
  WC_over_FCI: number;
  /** Nominal yearly interest on the loan, fraction. */
  financeInterest: number;
  /** Years over which the loan is repaid. */
  financeYears: number;
  /** Fraction of capital cost that is financed. */
  financeFraction: number;
  /** Start-up time before the plant reaches design output, months. */
  startupMonths: number;
  /** Total labour cost, USD per year. */
  laborCost: number;
  /** Yearly maintenance as a fraction of fixed capital investment. */
  maintenance: number;
  /** Fixed capital as a multiple of purchase cost. Null uses bare-module factors. */
  langFactor: number | null;
}

/**
 * Lang's own 1948 figure for a fluid-processing plant.
 *
 * Used only as the opening value when a reader switches away from bare-module
 * factors and has nothing else to start from. It is not bioSTEAM's default,
 * because bioSTEAM has no Lang default — `lang_factor` is None upstream until
 * somebody sets it.
 */
const LANG_FLUID_PROCESSING = 4.74;

/** Most recent first: a reader indexing a plant today wants the top of the list. */
const CEPCI_YEARS: number[] = Object.keys(CEPCI_BY_YEAR)
  .map(Number)
  .sort((a, b) => b - a);

const SCHEDULE_NAMES: string[] = Object.keys(DEPRECIATION_SCHEDULES);

/**
 * Per cent, for a stored fraction.
 *
 * The multiply is rounded before it is shown because binary floating point
 * turns 0.085 × 100 into 8.499999999999998, and a field that reads back
 * something other than what was typed into it is a field the reader stops
 * trusting.
 */
function asPercent(fraction: number): number {
  return Number((fraction * 100).toPrecision(12));
}

/**
 * Whether two numbers differ by more than the round trip through per cent can
 * account for. Typing a default value back in should read as untouched.
 */
function differs(a: number, b: number): boolean {
  return Math.abs(a - b) > Math.max(1e-12, Math.abs(b) * 1e-12);
}

/** The settings the reader has moved off the shared basis. */
function changedFields(value: PlantSettings, defaults: PlantSettings): Set<keyof PlantSettings> {
  const out = new Set<keyof PlantSettings>();
  for (const key of Object.keys(defaults) as (keyof PlantSettings)[]) {
    const a = value[key];
    const b = defaults[key];
    if (typeof a === 'string' || typeof b === 'string' || a === null || b === null) {
      if (a !== b) out.add(key);
    } else if (differs(a, b)) {
      out.add(key);
    }
  }
  return out;
}

/** The year by which a schedule has written off half the depreciable capital. */
function halfWrittenOffBy(schedule: number[]): number | null {
  let acc = 0;
  for (let i = 0; i < schedule.length; i++) {
    acc += schedule[i];
    if (acc >= 0.5) return i + 1;
  }
  return null;
}

// ── Field primitives ───────────────────────────────────────────────────

function Field({
  label,
  htmlFor,
  changed,
  note,
  explain,
  children,
}: {
  label: string;
  htmlFor: string;
  changed: boolean;
  note: ReactNode;
  explain?: ReactNode;
  children: ReactNode;
}): JSX.Element {
  return (
    <div className="py-2.5">
      <div className="flex items-baseline justify-between gap-x-3 gap-y-1 flex-wrap">
        <div className="flex items-baseline gap-1.5 min-w-0">
          <label htmlFor={htmlFor} className="text-body">
            {label}
          </label>
          {explain && <Explain label={`About ${label}`}>{explain}</Explain>}
        </div>
        {changed && <span className="chip chip-active">changed</span>}
      </div>
      <div className="mt-1.5">{children}</div>
      <p id={`${htmlFor}-note`} className="text-caption text-ink-soft mt-1.5">
        {note}
      </p>
    </div>
  );
}

/**
 * A number field that lets the reader finish typing.
 *
 * The draft is held as text, because "1." and "-" are states a number cannot
 * represent and clobbering them mid-keystroke makes the control fight the
 * typist. The incoming value is only written back over the draft when it came
 * from somewhere else — a reset, or the CEPCI year changing the index — which
 * is what the emitted-value ref distinguishes.
 */
function NumberField({
  id,
  value,
  unit,
  min,
  max,
  step,
  onCommit,
  describedBy,
}: {
  id: string;
  value: number;
  unit: string;
  min?: number;
  max?: number;
  step?: number;
  onCommit: (n: number) => void;
  /** Note to read out with the field. Defaults to the note its own Field renders. */
  describedBy?: string;
}): JSX.Element {
  const [draft, setDraft] = useState<string>(() => String(value));
  const emitted = useRef<number>(value);

  useEffect(() => {
    if (differs(value, emitted.current)) {
      emitted.current = value;
      setDraft(String(value));
    }
  }, [value]);

  return (
    <div className="flex items-center gap-2">
      <input
        id={id}
        type="number"
        inputMode="decimal"
        className="input font-num text-right w-[9rem]"
        min={min}
        max={max}
        step={step}
        value={draft}
        aria-describedby={describedBy ?? `${id}-note`}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          const n = Number(text);
          if (text.trim() === '' || !Number.isFinite(n)) return;
          emitted.current = n;
          onCommit(n);
        }}
      />
      <span className="text-caption text-ink-soft">{unit}</span>
    </div>
  );
}

// ── Depreciation schedule ──────────────────────────────────────────────

/**
 * The selected schedule, drawn so its shape is visible before its numbers are.
 *
 * MACRS7 takes 14.3% in the first year and 24.5% in the second, then falls away
 * — the whole point of an accelerated schedule is that the tax shield arrives
 * early, and a column of percentages hides that while a row of bars does not.
 */
function ScheduleBars({ name, schedule }: { name: string; schedule: number[] }): JSX.Element {
  const max = Math.max(...schedule);
  const total = schedule.reduce((t, f) => t + f, 0);
  const half = halfWrittenOffBy(schedule);
  return (
    <div className="mt-2">
      <div className="flex items-end gap-[3px] h-14" aria-hidden>
        {schedule.map((f, i) => (
          <div
            key={i}
            className="flex-1 min-w-[5px] min-h-[2px] rounded-t bg-accent/70"
            style={{ height: `${(f / max) * 100}%` }}
          />
        ))}
      </div>
      <p className="text-caption text-ink-soft mt-1.5">
        {schedule.length} years, opening at{' '}
        <span className="font-num">{(schedule[0] * 100).toFixed(2)}%</span>
        {half !== null && (
          <>
            {' '}
            and half written off by year <span className="font-num">{half}</span>
          </>
        )}
        . The half-year convention is why an n-year schedule runs over n+1 years.
      </p>
      <details className="mt-1">
        <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
          <Table2 size={12} /> View as table
        </summary>
        <div className="overflow-x-auto mt-1.5">
          <table className="w-full text-caption">
            <caption className="sr-only">
              The {name} depreciation schedule: the fraction of depreciable capital written off in
              each year, and the running total.
            </caption>
            <thead>
              <tr className="border-b border-line text-ink-soft">
                <th className="text-left py-1 whitespace-nowrap">Year</th>
                <th className="text-right py-1 whitespace-nowrap">Written off</th>
                <th className="text-right py-1 whitespace-nowrap">Cumulative</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((f, i) => {
                const cumulative = schedule.slice(0, i + 1).reduce((t, x) => t + x, 0);
                return (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-1 font-num whitespace-nowrap">{i + 1}</td>
                    <td className="py-1 text-right font-num whitespace-nowrap">
                      {(f * 100).toFixed(2)}%
                    </td>
                    <td className="py-1 text-right font-num whitespace-nowrap">
                      {(cumulative * 100).toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-line font-medium">
                <td className="py-1 whitespace-nowrap">Total</td>
                <td className="py-1 text-right font-num whitespace-nowrap">
                  {(total * 100).toFixed(2)}%
                </td>
                <td className="py-1" />
              </tr>
            </tfoot>
          </table>
        </div>
      </details>
    </div>
  );
}

// ── The panel ──────────────────────────────────────────────────────────

export function SettingsPanel({
  value,
  onChange,
  onReset,
  defaults,
}: {
  value: PlantSettings;
  onChange: (patch: Partial<PlantSettings>) => void;
  onReset: () => void;
  defaults: PlantSettings;
}): JSX.Element {
  const base = useId();
  const id = (key: string): string => `${base}-${key}`;
  const changed = changedFields(value, defaults);

  // The last Lang factor the reader typed, so that switching to bare-module
  // factors and back does not throw their number away.
  const [lastLang, setLastLang] = useState<number>(
    value.langFactor ?? defaults.langFactor ?? LANG_FLUID_PROCESSING,
  );

  // Only MACRS schedules are tabulated; 'SL10' and friends are generated on
  // demand by the TEA, so an unrecognised name is a valid basis with no bars to
  // draw rather than a mistake to correct.
  const schedule: number[] | undefined = DEPRECIATION_SCHEDULES[value.depreciation];
  const knownSchedule = value.depreciation in DEPRECIATION_SCHEDULES;

  const indexRatio = value.CE / CEPCI_BY_YEAR[2007];

  return (
    <div>
      <div className="flex items-start justify-between gap-x-6 gap-y-2 flex-wrap pb-3 border-b border-line">
        <p className="text-caption text-ink-soft max-w-2xl">
          Everything the plant is indexed and discounted against. These are bioSTEAM&rsquo;s own
          settings — the module-global cost index, and the arguments a TEA is constructed with.
        </p>
        <div className="flex items-center gap-2 shrink-0">
          {changed.size > 0 && (
            <span className="chip chip-active font-num">{changed.size} changed</span>
          )}
          <Button
            size="sm"
            onClick={onReset}
            disabled={changed.size === 0}
            title="Put every setting back to the basis the three plants are compared on"
          >
            <RotateCcw size={12} /> Reset to the shared basis
          </Button>
        </div>
      </div>

      <div className="mt-3">
        <Callout kind="info" title="One basis, three plants">
          All three plants are costed against this same financial basis on purpose. Three plants
          compared on three discount rates is not a comparison — it is three separate claims printed
          next to each other, and whichever plant got the kindest IRR wins. Move a setting here and
          it moves for all of them.
        </Callout>
      </div>

      {/* h3 rather than SectionTitle: the panel sits inside a card that already
          owns the h2, and skipping a level breaks the document outline. */}
      <h3 className="font-serif text-section-title font-semibold mt-5 mb-1">Plant settings</h3>

      <div className="divide-y divide-line/60">
        <Field
          label="Cost index basis"
          htmlFor={id('cepci')}
          changed={changed.has('cepciYear') || changed.has('CE')}
          explain={
            <>
              The Chemical Engineering Plant Cost Index is dimensionless and only ratios of two
              entries mean anything. A correlation fitted against 2007 quotations is charged here at{' '}
              <span className="font-num">CE ÷ {CEPCI_BY_YEAR[2007]}</span>. The table runs from 1980
              to <span className="font-num">{CEPCI_LATEST_YEAR}</span>.
            </>
          }
          note={
            <>
              Every purchase-cost correlation in the engine was fitted in the dollars of some past
              year, so each is charged at CE divided by the index it was published at — without that
              ratio a 2007 correlation quietly returns 2007 money. At{' '}
              <span className="font-num">CE {value.CE}</span> a 2007-dollar correlation is charged
              at <span className="font-num">×{indexRatio.toFixed(2)}</span>.
            </>
          }
        >
          <div className="flex items-center gap-2 flex-wrap">
            <div className="w-[17rem] max-w-full">
              <select
                id={id('cepci')}
                className="input"
                value={value.cepciYear === null ? 'custom' : String(value.cepciYear)}
                aria-describedby={`${id('cepci')}-note`}
                onChange={(e) => {
                  const raw = e.target.value;
                  if (raw === 'custom') {
                    onChange({ cepciYear: null });
                    return;
                  }
                  const year = Number(raw);
                  onChange({ cepciYear: year, CE: CEPCI_BY_YEAR[year] });
                }}
              >
                <option value="custom">Custom index</option>
                {CEPCI_YEARS.map((year) => (
                  <option key={year} value={year}>
                    {year} — CE {CEPCI_BY_YEAR[year]}
                  </option>
                ))}
              </select>
            </div>
            <span className="chip font-num">CE {value.CE}</span>
          </div>
          {value.cepciYear === null && (
            <div className="mt-2">
              <label htmlFor={id('ce')} className="text-caption text-ink-soft block mb-1">
                Cost index value
              </label>
              <NumberField
                id={id('ce')}
                value={value.CE}
                unit="dimensionless"
                min={1}
                step={0.5}
                describedBy={`${id('cepci')}-note`}
                onCommit={(n) => onChange({ CE: n })}
              />
            </div>
          )}
        </Field>

        <Field
          label="Operating days"
          htmlFor={id('days')}
          changed={changed.has('operatingDays')}
          note={
            <>
              <span className="font-num">{(value.operatingDays * 24).toLocaleString('en-US')}</span>{' '}
              operating hours a year. Utilities and feedstock are charged by the hour, so this sets
              the annual bill for both. Shared basis{' '}
              <span className="font-num">{defaults.operatingDays}</span> days.
            </>
          }
        >
          <NumberField
            id={id('days')}
            value={value.operatingDays}
            unit="days per year"
            min={1}
            max={365}
            step={1}
            onCommit={(n) => onChange({ operatingDays: n })}
          />
        </Field>

        <Field
          label="Capital factor basis"
          htmlFor={id('lang')}
          changed={changed.has('langFactor')}
          note={
            <>
              A Lang factor multiplies total purchase cost once to reach fixed capital. Bare-module
              factors multiply each piece of equipment by its own F<sub>BM</sub>, so a train of
              stainless vessels and a train of carbon-steel tanks stop costing the same multiple of
              their purchase price.
            </>
          }
        >
          <div role="group" aria-label="Capital factor basis" className="flex flex-wrap gap-1.5">
            <Button
              size="sm"
              aria-pressed={value.langFactor === null}
              className={cx(value.langFactor === null && 'bg-accent-wash border-accent/40')}
              onClick={() => onChange({ langFactor: null })}
            >
              Bare-module factors (bioSTEAM default)
            </Button>
            <Button
              size="sm"
              aria-pressed={value.langFactor !== null}
              className={cx(value.langFactor !== null && 'bg-accent-wash border-accent/40')}
              onClick={() => onChange({ langFactor: lastLang })}
            >
              Lang factor
            </Button>
          </div>
          {value.langFactor !== null && (
            <div className="mt-2">
              <label htmlFor={id('langval')} className="text-caption text-ink-soft block mb-1">
                Lang factor
              </label>
              <NumberField
                id={id('langval')}
                value={value.langFactor}
                unit="× purchase cost"
                min={1}
                step={0.01}
                describedBy={`${id('lang')}-note`}
                onCommit={(n) => {
                  setLastLang(n);
                  onChange({ langFactor: n });
                }}
              />
            </div>
          )}
        </Field>
      </div>

      <h3 className="font-serif text-section-title font-semibold mt-5 mb-1">Financial basis</h3>

      <div className="grid gap-x-6 sm:grid-cols-2">
        <Field
          label="Internal rate of return"
          htmlFor={id('irr')}
          changed={changed.has('IRR')}
          explain={
            <>
              The minimum selling price is whatever price drives net present value to zero at this
              return, so the IRR is not an output of the model — it is the bar the price has to
              clear, and moving it moves every price on the screen.
            </>
          }
          note={
            <>
              Real, per year. Shared basis{' '}
              <span className="font-num">{asPercent(defaults.IRR)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('irr')}
            value={asPercent(value.IRR)}
            unit="% per year"
            min={0}
            max={100}
            step={0.5}
            onCommit={(n) => onChange({ IRR: n / 100 })}
          />
        </Field>

        <Field
          label="Income tax"
          htmlFor={id('tax')}
          changed={changed.has('incomeTax')}
          note={
            <>
              Combined federal and state, charged on taxable income after depreciation. Shared basis{' '}
              <span className="font-num">{asPercent(defaults.incomeTax)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('tax')}
            value={asPercent(value.incomeTax)}
            unit="% of income"
            min={0}
            max={100}
            step={0.5}
            onCommit={(n) => onChange({ incomeTax: n / 100 })}
          />
        </Field>

        <div className="sm:col-span-2">
          <Field
            label="Depreciation schedule"
            htmlFor={id('dep')}
            changed={changed.has('depreciation')}
            note={
              <>
                Depreciation is not a cash cost; it is what shields income from tax, so an
                accelerated schedule is worth real money early in the project. Shared basis{' '}
                <span className="font-num">{defaults.depreciation}</span>.
              </>
            }
          >
            <div className="w-[17rem] max-w-full">
              <select
                id={id('dep')}
                className="input"
                value={value.depreciation}
                aria-describedby={`${id('dep')}-note`}
                onChange={(e) => onChange({ depreciation: e.target.value })}
              >
                {!knownSchedule && <option value={value.depreciation}>{value.depreciation}</option>}
                {SCHEDULE_NAMES.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            {schedule ? (
              <ScheduleBars name={value.depreciation} schedule={schedule} />
            ) : (
              <p className="text-caption text-ink-soft mt-2">
                <span className="font-num">{value.depreciation}</span> is generated by the TEA
                rather than tabulated, so there is nothing to draw until it runs.
              </p>
            )}
          </Field>
        </div>

        <Field
          label="Working capital"
          htmlFor={id('wc')}
          changed={changed.has('WC_over_FCI')}
          note={
            <>
              Put in at start-up and recovered at the end of the project, so it costs the time value
              of money and nothing else. Shared basis{' '}
              <span className="font-num">{asPercent(defaults.WC_over_FCI)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('wc')}
            value={asPercent(value.WC_over_FCI)}
            unit="% of FCI"
            min={0}
            max={100}
            step={1}
            onCommit={(n) => onChange({ WC_over_FCI: n / 100 })}
          />
        </Field>

        <Field
          label="Loan interest"
          htmlFor={id('fin')}
          changed={changed.has('financeInterest')}
          note={
            <>
              Nominal, per year, on the financed fraction only. Shared basis{' '}
              <span className="font-num">{asPercent(defaults.financeInterest)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('fin')}
            value={asPercent(value.financeInterest)}
            unit="% per year"
            min={0}
            max={100}
            step={0.5}
            onCommit={(n) => onChange({ financeInterest: n / 100 })}
          />
        </Field>

        <Field
          label="Loan term"
          htmlFor={id('finyears')}
          changed={changed.has('financeYears')}
          note={
            <>
              Years the loan is repaid over. Shared basis{' '}
              <span className="font-num">{defaults.financeYears}</span>.
            </>
          }
        >
          <NumberField
            id={id('finyears')}
            value={value.financeYears}
            unit="years"
            min={0}
            step={1}
            onCommit={(n) => onChange({ financeYears: n })}
          />
        </Field>

        <Field
          label="Financed fraction"
          htmlFor={id('finfrac')}
          changed={changed.has('financeFraction')}
          note={
            <>
              Share of capital raised as debt rather than equity; zero is an unfinanced project.
              Shared basis <span className="font-num">{asPercent(defaults.financeFraction)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('finfrac')}
            value={asPercent(value.financeFraction)}
            unit="% of capital"
            min={0}
            max={100}
            step={1}
            onCommit={(n) => onChange({ financeFraction: n / 100 })}
          />
        </Field>

        <Field
          label="Start-up time"
          htmlFor={id('startup')}
          changed={changed.has('startupMonths')}
          note={
            <>
              How long the plant runs before it reaches design output. The fractions of cost
              incurred and sales achieved in that window are fixed by the model. Shared basis{' '}
              <span className="font-num">{defaults.startupMonths}</span> months.
            </>
          }
        >
          <NumberField
            id={id('startup')}
            value={value.startupMonths}
            unit="months"
            min={0}
            step={1}
            onCommit={(n) => onChange({ startupMonths: n })}
          />
        </Field>

        <Field
          label="Labour cost"
          htmlFor={id('labor')}
          changed={changed.has('laborCost')}
          note={
            <>
              Total wages and salaries before fringe benefits, which are charged separately as a
              fraction of this. Shared basis{' '}
              <span className="font-num">${defaults.laborCost.toLocaleString('en-US')}</span>.
            </>
          }
        >
          <NumberField
            id={id('labor')}
            value={value.laborCost}
            unit="USD per year"
            min={0}
            step={10000}
            onCommit={(n) => onChange({ laborCost: n })}
          />
        </Field>

        <Field
          label="Maintenance"
          htmlFor={id('maint')}
          changed={changed.has('maintenance')}
          note={
            <>
              Charged yearly against fixed capital investment, alongside property tax, insurance and
              administration. Shared basis{' '}
              <span className="font-num">{asPercent(defaults.maintenance)}%</span>.
            </>
          }
        >
          <NumberField
            id={id('maint')}
            value={asPercent(value.maintenance)}
            unit="% of FCI per year"
            min={0}
            max={100}
            step={0.5}
            onCommit={(n) => onChange({ maintenance: n / 100 })}
          />
        </Field>
      </div>
    </div>
  );
}

// ── Utility agents ─────────────────────────────────────────────────────

/**
 * A price at full precision.
 *
 * `fmt` rounds to three decimals, which turns cooling water's 0.00048785
 * USD/kmol into nothing at all. These figures are quoted as upstream's, so they
 * are printed as upstream holds them.
 */
function exact(v: number): string {
  if (!Number.isFinite(v)) return '—';
  if (v === 0) return '0';
  const s = String(v);
  return s.includes('e') ? v.toFixed(12).replace(/0+$/, '') : s;
}

/** Six significant figures, grouped. Enough to recognise, short enough to scan. */
function sixFigures(v: number): string {
  return Number(v.toPrecision(6)).toLocaleString('en-US');
}

function AgentRow({ agent }: { agent: UtilityAgent }): JSX.Element {
  return (
    <tr className="border-b border-line/60">
      <td className="py-1.5 pr-3 font-num whitespace-nowrap">{agent.ID}</td>
      <td className="py-1.5 pr-3 whitespace-nowrap">
        <span className="chip">{agent.kind}</span>
      </td>
      <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">{agent.T}</td>
      <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
        {agent.T_limit === undefined ? <span className="text-ink-soft">—</span> : agent.T_limit}
      </td>
      <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
        {agent.heatTransferPrice === 0 ? (
          <span className="text-ink-soft">0</span>
        ) : (
          exact(agent.heatTransferPrice)
        )}
      </td>
      <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
        {agent.regenerationPrice === 0 ? (
          <span className="text-ink-soft">0</span>
        ) : (
          exact(agent.regenerationPrice)
        )}
      </td>
      <td className="py-1.5 pr-3 text-right font-num whitespace-nowrap">
        {sixFigures(agent.energyPerKmol)}
      </td>
      <td className="py-1.5 text-right font-num whitespace-nowrap">
        {agent.heatTransferEfficiency.toFixed(2)}
      </td>
    </tr>
  );
}

/**
 * bioSTEAM's utility price list, reproduced.
 *
 * Read-only on purpose. This is not a control panel — it is the receipt for
 * every heating and cooling duty the plant screen reports, and the point of
 * showing it is that a reader can check the engine against upstream rather than
 * take the totals on trust.
 */
export function UtilityAgentTable(): JSX.Element {
  return (
    <div>
      <p className="text-caption text-ink-soft max-w-2xl mb-2">
        The agents the costing engine picks between, at bioSTEAM&rsquo;s own prices, temperatures
        and pressures. They are not rounded, not converted and not updated: a utility price is an
        assumption a reviewer is entitled to challenge, and it can only be challenged if it is the
        number upstream actually ships.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-caption" data-table="utility-agents">
          <caption className="sr-only">
            Utility agents: agent identifier, whether it heats or cools, supply temperature and
            return temperature limit in kelvin, price per kilojoule transferred and per kilomole
            circulated in US dollars, energy carried per kilomole in kilojoules, and heat-transfer
            efficiency as a fraction.
          </caption>
          <thead>
            <tr className="border-b border-line text-ink-soft">
              <th className="text-left py-1.5 pr-3 whitespace-nowrap">Agent</th>
              <th className="text-left py-1.5 pr-3 whitespace-nowrap">Kind</th>
              <th className="text-right py-1.5 pr-3 whitespace-nowrap">Supply T [K]</th>
              <th className="text-right py-1.5 pr-3 whitespace-nowrap">T limit [K]</th>
              <th className="text-right py-1.5 pr-3 whitespace-nowrap">Heat transfer [USD/kJ]</th>
              <th className="text-right py-1.5 pr-3 whitespace-nowrap">Regeneration [USD/kmol]</th>
              <th className="text-right py-1.5 pr-3 whitespace-nowrap">Energy [kJ/kmol]</th>
              <th className="text-right py-1.5 whitespace-nowrap">Efficiency</th>
            </tr>
          </thead>
          <tbody>
            {HEATING_AGENTS.map((agent) => (
              <AgentRow key={agent.ID} agent={agent} />
            ))}
            {COOLING_AGENTS.map((agent) => (
              <AgentRow key={agent.ID} agent={agent} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 pt-3 border-t border-line flex items-baseline justify-between gap-4 flex-wrap">
        <span className="text-body">Electricity</span>
        <span className="font-num text-body">
          {exact(ELECTRICITY_PRICE)} <span className="text-ink-soft">USD/kWh</span>
        </span>
      </div>
      <p className="text-caption text-ink-soft mt-1">
        Charged on net draw, so a turbogenerator or an expander returns a credit rather than being
        clamped at zero.
      </p>

      <p className="text-caption text-ink-soft mt-3 max-w-2xl">
        Energy per kilomole is shown to six significant figures; the engine uses the full value. For
        a cooling agent that figure is the full rise from supply to the return limit, and it is only
        achieved when the process is hot enough to deliver it — the agent comes back at whichever is
        lower, the limit or the process inlet less the{' '}
        <span className="font-num">{MINIMUM_APPROACH_DT} K</span> minimum approach. Cool a stream
        that enters near ambient and each mole carries half the heat, so twice the flow is needed
        and a per-kilomole agent costs twice as much. That is why the cost function takes a process
        temperature and not only a duty. Natural gas runs the same way in reverse: the hotter the
        process, the less of the flame is recovered, and the figure below is its most favourable
        case.
      </p>
    </div>
  );
}
