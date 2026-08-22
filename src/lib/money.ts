// Money, in the magnitude a reader can hold.
//
// Lifted out of `screens/Plant.tsx` when the plant and the price became two
// screens. It was already duplicated verbatim in `components/UnitSpecEditor.tsx`,
// and a third copy was exactly what splitting the screen would have produced —
// so the split is the occasion, not the cause.
import { fmt } from '@/engine/units';

/**
 * `fmt` switches to scientific notation above a million, which is right for a
 * titer and wrong for a capital cost: a ladder reading $1.83×10⁶ then $5.16×10⁶
 * then $484,682.7 makes the reader do the comparison the chart was supposed to
 * do for them. Millions get an M, thousands get separators, and nothing gets a
 * decimal it has not earned.
 */
export function money(v: number): string {
  if (!Number.isFinite(v)) return '—';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}$${Math.round(abs).toLocaleString('en-US')}`;
  return `${sign}$${abs.toFixed(2)}`;
}

/** A quantity that may not have resolved. An em dash is not a zero. */
export const USD = (v: number): string => (Number.isFinite(v) ? fmt(v) : '—');
