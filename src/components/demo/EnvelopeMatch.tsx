// Demand against supply, one row per axis (OF-DEMO-002 §4.5).
//
// A signed bar per axis. Negative is a violation, it renders in `signal-error`,
// and the binding axis is LABELLED rather than left to be inferred from which
// bar is longest — a reader should be able to say what killed a candidate
// without measuring anything.
//
// The axes are the plant's, not the product's: OTR, cooling, installed power,
// viscosity class, sterility class, separation class, cycle time. A candidate
// does not fail "because it is hard"; it fails on one of seven things, and the
// screen's job is to name which.
import type { EnvelopeMatchResult } from '@/data/demo/types';
import { cx } from '@/components/ui';

const AXIS_LABEL: Record<string, string> = {
  otr: 'Oxygen transfer',
  cooling: 'Cooling duty',
  power: 'Installed power',
  viscosity: 'Viscosity class',
  sterility: 'Sterility class',
  separation: 'Separation class',
  cycle: 'Cycle time',
};

/** A categorical axis has no headroom to draw; it passes or it does not. */
const isNumeric = (v: number | string): v is number => typeof v === 'number';

export function EnvelopeMatch({
  match,
  className,
}: {
  match: EnvelopeMatchResult;
  className?: string;
}) {
  return (
    <div className={cx('min-w-0', className)}>
      <table className="w-full text-caption">
        <thead>
          <tr className="text-ink-soft text-left">
            <th className="font-normal pb-1">Axis</th>
            <th className="font-normal pb-1 text-right">Demand</th>
            <th className="font-normal pb-1 text-right">Supply</th>
            <th className="font-normal pb-1 pl-3">Headroom</th>
          </tr>
        </thead>
        <tbody>
          {match.axes.map((ax) => {
            const pct = ax.headroom * 100;
            // Bars are clipped to ±100 % so one catastrophic axis does not
            // flatten the others into invisibility. The number is always shown.
            const clipped = Math.max(-100, Math.min(100, pct));
            const violated = ax.headroom < 0;
            return (
              <tr key={ax.axis} className={cx('align-middle', violated && 'text-signal-error')}>
                <td className="py-0.5 pr-2 whitespace-nowrap">
                  {AXIS_LABEL[ax.axis] ?? ax.axis}
                  {ax.binding && (
                    <span className="ml-1.5 px-1 rounded-[2px] text-[10px] uppercase tracking-wide bg-signal-error/10 text-signal-error">
                      binding
                    </span>
                  )}
                </td>
                <td className="py-0.5 text-right font-num whitespace-nowrap">
                  {isNumeric(ax.demand) ? +ax.demand.toFixed(1) : ax.demand}
                </td>
                <td className="py-0.5 text-right font-num whitespace-nowrap">
                  {isNumeric(ax.supply) ? +ax.supply.toFixed(1) : ax.supply}
                </td>
                <td className="py-0.5 pl-3 w-1/2">
                  <div className="flex items-center gap-2">
                    {/* Zero sits in the middle, so surplus and deficit read as
                        directions rather than as two different lengths. */}
                    <div className="relative flex-1 h-3 bg-[rgb(var(--line))]/40">
                      <div className="absolute inset-y-0 left-1/2 w-px bg-[rgb(var(--ink-soft))]/50" />
                      <div
                        className="absolute inset-y-[2px]"
                        style={{
                          left: clipped >= 0 ? '50%' : `${50 + clipped / 2}%`,
                          width: `${Math.abs(clipped) / 2}%`,
                          background: violated
                            ? 'rgb(var(--signal-error))'
                            : 'rgb(var(--signal-open))',
                        }}
                      />
                    </div>
                    <span className="font-num w-14 text-right shrink-0">
                      {isNumeric(ax.demand) ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)} %` : violated ? 'fails' : 'ok'}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="mt-2 text-caption">
        {match.feasible ? (
          <span style={{ color: 'rgb(var(--signal-open))' }}>
            Fits the envelope on every axis.
          </span>
        ) : (
          <span className="text-signal-error">
            Does not fit. Binding axis:{' '}
            <span className="font-medium">
              {AXIS_LABEL[match.bindingAxis ?? ''] ?? match.bindingAxis}
            </span>
            . Every other axis has room, which is why this is a named failure rather than a
            verdict.
          </span>
        )}
      </div>
    </div>
  );
}
