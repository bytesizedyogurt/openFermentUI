// Data-visualization palettes (OF-DES-001 §6.2). Chart colors are deliberately
// independent of the UI accent so "green" in a chart never implies "verified".
import { useStore } from '@/store';

/** Okabe–Ito colorblind-safe categorical palette, fixed assignment order. */
export const CATEGORICAL_LIGHT = [
  '#0072B2', // blue
  '#D55E00', // vermillion
  '#009E73', // bluish green
  '#CC79A7', // reddish purple
  '#E69F00', // orange
  '#56B4E9', // sky blue
  '#8C6D31', // brown (extension)
  '#525252', // grey (extension)
];

/** Same hues lifted for legibility on the Night Shift ground. */
export const CATEGORICAL_DARK = [
  '#5AA9DC',
  '#F08A4B',
  '#4FC3A1',
  '#E39BC2',
  '#F0BE5A',
  '#8FD3F4',
  '#C4A26A',
  '#A3AAA6',
];

export function useCategorical(): string[] {
  const theme = useStore((s) => s.ui.theme);
  return theme === 'night' ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
}
