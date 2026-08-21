// Capex against scale, log-log (OF-DEMO-002 §4.9).
//
// The six-tenths line with the concept points on it, breakeven annotated, and
// the ACCURACY CLASS STATED ON THE CHART rather than in a caption. That last
// one is the whole reason this is a bespoke component: an AACE Class 5 estimate
// carries −30/+50 %, and a crisp line drawn without that band is a promise the
// number cannot keep. The band is drawn first and the line sits inside it.
import { useMemo } from 'react';

import type { FacilityConcept } from '@/data/demo/types';
import { CAPEX_SCALE_EXPONENT } from '@/data/demo/core';
import { capexAtScale } from '@/lib/demo';
import { cx } from '@/components/ui';

const W = 560;
const H = 260;
const PAD = { l: 54, r: 16, t: 14, b: 34 };

/** −30/+50 %, parsed off the concept's own stated class rather than assumed. */
function accuracyBand(cls: string): { low: number; high: number } | null {
  const m = cls.match(/([−-]?\d+)\s*\/\s*\+?(\d+)\s*%/);
  if (!m) return null;
  return { low: 1 + Number(m[1].replace('−', '-')) / 100, high: 1 + Number(m[2]) / 100 };
}

export function CapexCurve({
  concepts,
  className,
}: {
  concepts: FacilityConcept[];
  className?: string;
}) {
  const model = useMemo(() => {
    if (!concepts.length) return null;
    // The reference is the smallest concept: a six-tenths line drawn through
    // the largest would flatter the small end, which is where the accuracy is
    // worst.
    const sorted = [...concepts].sort((a, b) => a.scaleTonnesPerYear - b.scaleTonnesPerYear);
    const ref = sorted[0];
    const sLo = ref.scaleTonnesPerYear * 0.4;
    const sHi = sorted[sorted.length - 1].scaleTonnesPerYear * 2.2;
    const line: [number, number][] = [];
    const steps = 48;
    for (let i = 0; i <= steps; i += 1) {
      const s = sLo * Math.pow(sHi / sLo, i / steps);
      line.push([s, capexAtScale(ref.capexUSD, ref.scaleTonnesPerYear, s)]);
    }
    const allCapex = [...concepts.map((c) => c.capexUSD), ...line.map((p) => p[1])];
    const band = accuracyBand(ref.capexAccuracyClass);
    return {
      ref,
      line,
      band,
      sLo,
      sHi,
      cLo: Math.min(...allCapex) * (band ? band.low : 1) * 0.85,
      cHi: Math.max(...allCapex) * (band ? band.high : 1) * 1.15,
    };
  }, [concepts]);

  if (!model) return <div className="text-caption text-ink-soft">No concepts to plot.</div>;

  const lx = (s: number) =>
    PAD.l + (Math.log10(s / model.sLo) / Math.log10(model.sHi / model.sLo)) * (W - PAD.l - PAD.r);
  const ly = (c: number) =>
    H - PAD.b - (Math.log10(c / model.cLo) / Math.log10(model.cHi / model.cLo)) * (H - PAD.t - PAD.b);

  const path = model.line.map(([s, c], i) => `${i ? 'L' : 'M'}${lx(s).toFixed(1)},${ly(c).toFixed(1)}`).join(' ');
  const bandPath = model.band
    ? [
        ...model.line.map(([s, c], i) => `${i ? 'L' : 'M'}${lx(s).toFixed(1)},${ly(c * model.band!.high).toFixed(1)}`),
        ...[...model.line].reverse().map(([s, c]) => `L${lx(s).toFixed(1)},${ly(c * model.band!.low).toFixed(1)}`),
        'Z',
      ].join(' ')
    : null;

  const decades = (lo: number, hi: number) => {
    const out: number[] = [];
    for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e += 1) {
      for (const m of [1, 2, 5]) {
        const v = m * 10 ** e;
        if (v >= lo && v <= hi) out.push(v);
      }
    }
    return out;
  };

  const fmtUSD = (v: number) => (v >= 1e6 ? `${+(v / 1e6).toFixed(1)} M` : `${Math.round(v / 1e3)} k`);

  return (
    <div className={cx('min-w-0', className)}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Capex against scale, log-log">
        {/* Accuracy band FIRST. The line is only meaningful inside it. */}
        {bandPath && <path d={bandPath} fill="rgb(var(--ink-soft))" opacity="0.10" />}

        {decades(model.sLo, model.sHi).map((s) => (
          <g key={`x${s}`}>
            <line x1={lx(s)} y1={PAD.t} x2={lx(s)} y2={H - PAD.b} stroke="rgb(var(--line))" strokeWidth="1" />
            <text x={lx(s)} y={H - PAD.b + 12} textAnchor="middle" className="fill-[rgb(var(--ink-soft))]" style={{ fontSize: 9 }}>
              {s >= 1000 ? `${s / 1000}k` : s}
            </text>
          </g>
        ))}
        {decades(model.cLo, model.cHi).map((c) => (
          <g key={`y${c}`}>
            <line x1={PAD.l} y1={ly(c)} x2={W - PAD.r} y2={ly(c)} stroke="rgb(var(--line))" strokeWidth="1" />
            <text x={PAD.l - 5} y={ly(c) + 3} textAnchor="end" className="fill-[rgb(var(--ink-soft))]" style={{ fontSize: 9 }}>
              {fmtUSD(c)}
            </text>
          </g>
        ))}

        <path d={path} fill="none" stroke="rgb(var(--ink))" strokeWidth="1.25" />

        {concepts.map((c) => (
          <g key={c.id}>
            <circle cx={lx(c.scaleTonnesPerYear)} cy={ly(c.capexUSD)} r="4" fill="rgb(var(--accent))" />
            <text
              x={lx(c.scaleTonnesPerYear) + 7}
              y={ly(c.capexUSD) - 5}
              className="fill-[rgb(var(--ink))]"
              style={{ fontSize: 9 }}
            >
              {c.id}
            </text>
            {/* Breakeven, annotated on the chart. */}
            {c.breakevenTonnesPerYear > model.sLo && c.breakevenTonnesPerYear < model.sHi && (
              <line
                x1={lx(c.breakevenTonnesPerYear)}
                y1={PAD.t}
                x2={lx(c.breakevenTonnesPerYear)}
                y2={H - PAD.b}
                stroke="rgb(var(--signal-warn))"
                strokeWidth="1"
                strokeDasharray="3 3"
              >
                <title>{`${c.id} breakeven at ${c.breakevenTonnesPerYear.toLocaleString()} t/yr`}</title>
              </line>
            )}
          </g>
        ))}

        {/* The accuracy class, ON the chart. */}
        <text x={PAD.l + 4} y={PAD.t + 10} className="fill-[rgb(var(--ink-soft))]" style={{ fontSize: 9 }}>
          {model.ref.capexAccuracyClass} · six-tenths rule, exponent {CAPEX_SCALE_EXPONENT}
        </text>
        <text x={W - PAD.r} y={H - 4} textAnchor="end" className="fill-[rgb(var(--ink-soft))]" style={{ fontSize: 9 }}>
          scale, t a⁻¹
        </text>
      </svg>

      <div className="text-caption text-ink-soft mt-1">
        The shaded band is the stated accuracy class, drawn rather than footnoted: at{' '}
        {model.ref.capexAccuracyClass.replace(/^.*\(/, '').replace(/\)$/, '')} the line is a centre
        of mass, not a quotation. Dashed verticals are breakeven.
      </div>
    </div>
  );
}
