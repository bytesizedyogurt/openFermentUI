// Unit-aware quantity field (OF-DES-001 §7.5). Parses free text, validates
// dimension against the bound ParameterDef, shows the SI twin, and warns —
// but never blocks — on out-of-range values, because a reviewer may be
// recording a genuinely anomalous published number.
import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import type { FieldId } from '@/data/types';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { parseQuantity, toSI, sameFamily, convert, fmt } from '@/engine/units';
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

  let canonicalValue: number | null = null;
  if (parsed && dimensionOK) {
    try {
      canonicalValue = def.canonicalUnit === '' ? parsed.value : convert(parsed.value, parsed.unit, def.canonicalUnit);
    } catch {
      canonicalValue = null;
    }
  }
  const outOfRange =
    canonicalValue !== null && (canonicalValue < def.range[0] || canonicalValue > def.range[1]);

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
          !parsed || !dimensionOK
            ? 'border-signal-error'
            : outOfRange
              ? 'border-signal-warn'
              : undefined,
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
          <div className="text-signal-error">
            Wrong dimension for {def.name} — expects units compatible with{' '}
            <span className="font-num">{def.canonicalUnit || 'a dimensionless value'}</span>.
          </div>
        )}
        {showTwin && (
          <div className="text-ink-soft font-num">
            = {fmt(si!.value)} {si!.unit}
          </div>
        )}
        {outOfRange && (
          <div className="text-signal-warn flex items-start gap-1">
            <AlertTriangle size={12} className="mt-[2px] shrink-0" />
            <span>
              <span className="font-num">
                {fmt(canonicalValue!)} {def.canonicalUnit}
              </span>{' '}
              is outside the typical range for {def.name} (
              <span className="font-num">
                {def.range[0]}–{def.range[1]} {def.canonicalUnit}
              </span>
              ). Saving anyway records it as anomalous.
            </span>
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
  value: number;
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
