// Unit-aware quantity field (OF-DES-001 §7.5). Parses free text, validates
// dimension against the bound ParameterDef and shows the SI twin. A field
// carries no range (alpha 2.0, ADR-010), so a value is held to its unit and
// to the quote it stands in, which review checks.
import { useEffect, useState } from 'react';
import type { FieldId } from '@/data/types';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { parseQuantity, toSI, sameFamily, fmt, explainRefusal } from '@/engine/units';
import { ComponentTag } from './ComponentTag';
import { cx } from './ui';

export interface QuantityValue {
  value: number;
  unit: string;
}

export function QuantityField({
  field,
  value,
  onChange,
  autoFocus,
  id,
  onSubmit,
}: {
  field: FieldId;
  value: QuantityValue;
  onChange: (v: QuantityValue | null) => void;
  autoFocus?: boolean;
  id?: string;
  onSubmit?: () => void;
}) {
  const def = ONTOLOGY_BY_ID[field];
  const [text, setText] = useState(`${fmt(value.value)}${value.unit ? ' ' + value.unit : ''}`);

  useEffect(() => {
    setText(`${fmt(value.value)}${value.unit ? ' ' + value.unit : ''}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value.value, value.unit]);

  const parsed = parseQuantity(text);
  const dimensionOK =
    parsed !== null && (def.canonicalUnit === '' ? parsed.unit === '' : sameFamily(parsed.unit, def.canonicalUnit));

  const si = parsed && dimensionOK ? toSI(parsed.value, parsed.unit) : null;
  const showTwin = si && parsed && si.unit !== parsed.unit;

  const commit = (t: string) => {
    setText(t);
    const p = parseQuantity(t);
    if (!p) return onChange(null);
    if (def.canonicalUnit !== '' && !sameFamily(p.unit, def.canonicalUnit)) return onChange(null);
    onChange(p);
  };

  return (
    <div className="space-y-1">
      <input
        id={id}
        autoFocus={autoFocus}
        className={cx(
          'input font-num',
          !parsed || !dimensionOK ? 'border-signal-error' : undefined,
        )}
        value={text}
        onChange={(e) => commit(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && onSubmit) {
            e.preventDefault();
            onSubmit();
          }
        }}
        aria-label={`${def.name} value with unit`}
        aria-invalid={!parsed || !dimensionOK}
        aria-describedby={`${id ?? field}-hint`}
      />
      <div id={`${id ?? field}-hint`} className="text-caption space-y-0.5">
        {!parsed && text.trim() !== '' && (
          <div className="text-signal-error">
            Can’t read that. Try a number and a unit, e.g. “0.12 {def.canonicalUnit || 'pH'}”.
          </div>
        )}
        {parsed && !dimensionOK && (
          // A refusal that names its reason turns a dead end into a
          // measurement plan, which is the whole point of explainRefusal():
          // %TSP to g/L is not a dimension error to be scolded for, it is two
          // quantities nobody recorded. Where the engine has no specific
          // reason, the generic dimension message still stands.
          <div className="text-signal-error space-y-0.5">
            <div>
              Wrong dimension for {def.name} — expects units compatible with{' '}
              <span className="font-num">{def.canonicalUnit || 'a dimensionless value'}</span>.
            </div>
            {explainRefusal(parsed.unit, def.canonicalUnit) && (
              <div className="text-ink-soft">
                {explainRefusal(parsed.unit, def.canonicalUnit)}
              </div>
            )}
            <ComponentTag unnamed="the unit engine" action="conversion refused" />
          </div>
        )}
        {showTwin && (
          <div className="text-ink-soft font-num">
            = {fmt(si!.value)} {si!.unit}
          </div>
        )}
      </div>
    </div>
  );
}

/** Read-only display of a quantity with optional SI twin. */
export function Quantity({
  value,
  unit,
  si,
  mode = 'published',
  className,
}: {
  /** Categorical records carry a string; fmt() passes it through. */
  value: number | string;
  unit: string;
  si?: { value: number; unit: string };
  mode?: 'published' | 'si';
  className?: string;
}) {
  const shown = mode === 'si' && si ? si : { value, unit };
  return (
    <span className={cx('font-num', className)}>
      {fmt(shown.value)}
      {shown.unit && <span className="text-ink-soft"> {shown.unit}</span>}
    </span>
  );
}
