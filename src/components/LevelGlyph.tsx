// Level glyph (OF-BLD-013 §1.4). Shape carries the level and colour backs it
// up, so the Matrix reads in print, in Night Shift and for a reader who does
// not see the colours: an empty square, a quarter filled, half filled, full,
// full with a ring. Lapsed lays a hatch over the square; suspended draws a
// heavy outline around it.
import { useId } from 'react';
import type { CompetenceStatus, Level } from '@/engine/competence';
import { LEVEL_NAME } from '@/engine/competence';

export function levelLabel(st: Pick<CompetenceStatus, 'level' | 'lapsed' | 'suspended'>): string {
  return LEVEL_NAME[st.level] + (st.suspended ? ', suspended' : '') + (st.lapsed ? ', lapsed' : '');
}

export function LevelGlyph({
  status,
  level,
  size = 16,
}: {
  status?: Pick<CompetenceStatus, 'level' | 'lapsed' | 'suspended'>;
  level?: Level;
  size?: number;
}) {
  const lvl: Level = status ? status.level : (level ?? 0);
  const lapsed = status?.lapsed ?? false;
  const suspended = status?.suspended ?? false;
  const pad = 4;
  const box = size + pad * 2;
  const label = levelLabel({ level: lvl, lapsed, suspended });
  // useId's colons are not safe inside url(#…), so they are dropped.
  const hatch = `of-hatch-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  return (
    <svg width={box} height={box} viewBox={`0 0 ${box} ${box}`} role="img" aria-label={label} className="shrink-0">
      <title>{label}</title>
      {lapsed && (
        <defs>
          <pattern id={hatch} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="2" height="4" fill="rgb(var(--signal-warn))" />
          </pattern>
        </defs>
      )}
      {lvl === 4 && (
        <rect x={1} y={1} width={box - 2} height={box - 2} rx={4} fill="none" stroke="rgb(var(--gold))" strokeWidth={1.5} />
      )}
      <rect
        x={pad}
        y={pad}
        width={size}
        height={size}
        rx={2}
        fill={lvl >= 3 ? 'rgb(var(--accent))' : 'rgb(var(--surface-1))'}
        stroke={suspended ? 'rgb(var(--signal-error))' : lvl >= 3 ? 'rgb(var(--accent))' : 'rgb(var(--ink-soft) / 0.55)'}
        strokeWidth={suspended ? 2.5 : 1.25}
      />
      {lvl === 1 && (
        <rect x={pad + 1} y={pad + size * 0.72} width={size - 2} height={size * 0.28 - 1} fill="rgb(var(--signal-info))" />
      )}
      {lvl === 2 && <rect x={pad + 1} y={pad + size / 2} width={size - 2} height={size / 2 - 1} fill="rgb(var(--signal-info))" />}
      {lapsed && <rect x={pad} y={pad} width={size} height={size} rx={2} fill={`url(#${hatch})`} opacity={0.9} />}
    </svg>
  );
}

/** The seven states in a row, for under the Matrix. */
export function LevelLegend() {
  const items: [string, Pick<CompetenceStatus, 'level' | 'lapsed' | 'suspended'>][] = [
    ['Not started', { level: 0, lapsed: false, suspended: false }],
    ['Learning', { level: 1, lapsed: false, suspended: false }],
    ['Supervised', { level: 2, lapsed: false, suspended: false }],
    ['Qualified', { level: 3, lapsed: false, suspended: false }],
    ['Assessor', { level: 4, lapsed: false, suspended: false }],
    ['Lapsed', { level: 3, lapsed: true, suspended: false }],
    ['Suspended', { level: 3, lapsed: false, suspended: true }],
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft">
      {items.map(([name, st]) => (
        <span key={name} className="inline-flex items-center gap-1">
          <LevelGlyph status={st} size={12} /> {name}
        </span>
      ))}
    </div>
  );
}
