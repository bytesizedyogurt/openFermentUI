// Latency model (OF-DES-001 §13.5). One global simSpeed multiplier lets the
// demo driver rehearse at 4× or instant.
import { useStore } from '@/store';

export type OpClass = 'instant' | 'quick' | 'job';

const RANGES: Record<OpClass, [number, number]> = {
  instant: [0, 40],
  quick: [200, 450],
  job: [1500, 4000],
};

/** Cosmetic jitter only — never affects computed values (§11.5). */
export function jitter(cls: OpClass): number {
  const [lo, hi] = RANGES[cls];
  return lo + Math.random() * (hi - lo);
}

export function scaled(ms: number): number {
  const speed = useStore.getState().ui.simSpeed;
  if (speed === Infinity) return 0;
  return ms / speed;
}

export function delay(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, scaled(ms)));
}

export function delayClass(cls: OpClass): Promise<void> {
  return delay(jitter(cls));
}

/** Streaming cadence: ~40 tokens/s, scaled by simSpeed. */
export function streamInterval(): number {
  return Math.max(4, scaled(1000 / 40));
}
