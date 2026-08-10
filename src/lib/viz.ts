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

export function useSeriesColor(): (i: number) => string {
  const palette = useCategorical();
  return (i: number) => palette[i % palette.length];
}

/** Viridis stops for sequential surfaces (sweep grids, heatmaps). */
const VIRIDIS = [
  [68, 1, 84],
  [72, 40, 120],
  [62, 74, 137],
  [49, 104, 142],
  [38, 130, 142],
  [31, 158, 137],
  [53, 183, 121],
  [110, 206, 88],
  [181, 222, 43],
  [253, 231, 37],
];

export function viridis(t: number): string {
  const x = Math.max(0, Math.min(1, t)) * (VIRIDIS.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = VIRIDIS[i];
  const b = VIRIDIS[Math.min(VIRIDIS.length - 1, i + 1)];
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
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

/** Shared recharts tooltip styling. */
export function tooltipStyle(t: ReturnType<typeof useChartTheme>) {
  return {
    contentStyle: {
      background: t.surface,
      border: `1px solid ${t.grid}`,
      borderRadius: 8,
      fontSize: 12,
      fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
      color: t.ink,
      boxShadow: '0 8px 24px -6px rgba(0,0,0,0.18)',
    },
    labelStyle: { color: t.axis, fontSize: 11, marginBottom: 2 },
    itemStyle: { color: t.ink, fontSize: 12 },
  };
}
