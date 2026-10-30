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

/** Blue–grey–orange diverging ramp for comparisons (t in −1…1). */
export function diverging(t: number): string {
  const x = Math.max(-1, Math.min(1, t));
  if (x < 0) {
    const f = -x;
    return `rgb(${Math.round(150 - 105 * f)}, ${Math.round(155 - 40 * f)}, ${Math.round(160 + 18 * f)})`;
  }
  const f = x;
  return `rgb(${Math.round(150 + 63 * f)}, ${Math.round(155 - 61 * f)}, ${Math.round(160 - 160 * f)})`;
}

/** Axis/grid colors bound to the theme tokens. */
export function useChartTheme() {
  const theme = useStore((s) => s.ui.theme);
  const dark = theme === 'night';
  return {
    axis: dark ? '#9AA69E' : '#5A655E',
    grid: dark ? '#2A342E' : '#D7DDD8',
    surface: dark ? '#171E1A' : '#FFFFFF',
    ink: dark ? '#E6EBE7' : '#1C221E',
    accent: dark ? '#6FAE8F' : '#2E6B4F',
    warn: dark ? '#D97A45' : '#B3541E',
    gold: dark ? '#D3A24C' : '#B07C22',
  };
}
