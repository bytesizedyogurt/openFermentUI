// The SFF graph (execution prompt §8.5; docs/api/sff.md "The graph"): a
// flowsheet's units as nodes and its streams as edges, read from the file by
// the service. Each unit stands in the column the service gave it (`rank`,
// one right of the furthest unit feeding it); a stream that closes a recycle
// runs back, dashed. Feeds enter from the left edge and products leave by the
// right, each named as the file's metadata names it. Nothing is laid out from
// a number this page computes beyond the drawing itself.
import type { SFFGraph } from '@/data/types';

const BOX_W = 132;
const BOX_H = 34;
const COL = 196;
const ROW = 52;
const PAD = 72;
// Room beside the outer columns for a feed's or a product's name, so the
// boundary's names stand inside the drawing.
const EDGE = 128;
// How many characters of a name fit: at the boundary, and in the gap
// between two columns, where a longer name would run under the next box.
const EDGE_CHARS = 20;
const GAP_CHARS = 10;
// One line of a name's text.
const LINE = 11;

function short(text: string, n = 18): string {
  return text.length > n ? `${text.slice(0, n - 1)}…` : text;
}

export function SffGraph({ graph, title = 'The flowsheet' }: { graph: SFFGraph; title?: string }) {
  const columns = new Map<number, string[]>();
  for (const n of [...graph.nodes].sort((a, b) => a.rank - b.rank || a.id.localeCompare(b.id))) {
    columns.set(n.rank, [...(columns.get(n.rank) ?? []), n.id]);
  }
  const at = new Map<string, { x: number; y: number }>();
  for (const [rank, ids] of columns) ids.forEach((id, i) => at.set(id, { x: EDGE + rank * COL, y: PAD / 2 + i * ROW }));
  const rankOf = new Map(graph.nodes.map((n) => [n.id, n.rank]));
  const lastRank = Math.max(0, ...graph.nodes.map((n) => n.rank));
  const width = EDGE * 2 + lastRank * COL + BOX_W;
  const height = PAD + Math.max(1, ...[...columns.values()].map((c) => c.length)) * ROW;
  const typeOf = new Map(graph.nodes.map((n) => [n.id, n.type]));
  // A unit with more than one feed or product stacks their names, one line each.
  const nth = (ends: { id: string; unit: string }[]) => {
    const seen = new Map<string, number>();
    return new Map(ends.map((e) => {
      const i = seen.get(e.unit) ?? 0;
      seen.set(e.unit, i + 1);
      return [e.id, i];
    }));
  };
  const feedLine = nth(graph.feeds);
  const productLine = nth(graph.products);
  return (
    <figure className="m-0" data-testid="sff-graph" data-units={graph.nodes.length} data-streams={graph.edges.length}>
      <figcaption className="text-caption text-ink-soft mb-1.5">
        {title}: {graph.nodes.length} units, {graph.edges.length} streams between them, {graph.feeds.length} feeds and{' '}
        {graph.products.length} products at the boundary
        {graph.dangling.length > 0 ? `; ${graph.dangling.length} streams name a unit the file does not list` : ''}. A
        dashed stream closes a recycle.
      </figcaption>
      <div className="overflow-auto border border-line rounded-md bg-surface-1" style={{ maxHeight: 520 }}>
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${title}: ${graph.nodes.length} units and ${graph.edges.length} streams`}
          className="block"
        >
          <defs>
            <marker id="sff-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" className="fill-ink-soft" />
            </marker>
          </defs>
          {graph.edges.map((e) => {
            const a = at.get(e.source);
            const b = at.get(e.sink);
            if (!a || !b) return null;
            const back = (rankOf.get(e.sink) ?? 0) <= (rankOf.get(e.source) ?? 0);
            const x1 = a.x + BOX_W;
            const y1 = a.y + BOX_H / 2;
            const x2 = b.x;
            const y2 = b.y + BOX_H / 2;
            const d = back
              ? `M${x1},${y1} C${x1 + 60},${y1 - 70} ${x2 - 60},${y2 - 70} ${x2},${y2}`
              : `M${x1},${y1} C${x1 + 40},${y1} ${x2 - 40},${y2} ${x2},${y2}`;
            return (
              <path key={e.id} d={d} fill="none" className="stroke-ink-soft" strokeWidth={1}
                strokeDasharray={back ? '4 3' : undefined} markerEnd="url(#sff-arrow)">
                <title>{e.id}</title>
              </path>
            );
          })}
          {graph.feeds.map((f) => {
            const u = at.get(f.unit);
            if (!u) return null;
            return (
              <g key={`feed-${f.id}`}>
                <line x1={u.x - 44} y1={u.y + BOX_H / 2} x2={u.x} y2={u.y + BOX_H / 2} className="stroke-accent"
                  strokeWidth={1.5} markerEnd="url(#sff-arrow)" />
                <text x={u.x - 4} y={u.y + BOX_H / 2 - 5 - (feedLine.get(f.id) ?? 0) * LINE} textAnchor="end" className="fill-accent" fontSize={10}>
                  {short(f.name ?? f.id, rankOf.get(f.unit) === 0 ? EDGE_CHARS : GAP_CHARS)}
                  <title>{f.name ?? f.id}</title>
                </text>
              </g>
            );
          })}
          {graph.products.map((p) => {
            const u = at.get(p.unit);
            if (!u) return null;
            return (
              <g key={`product-${p.id}`}>
                <line x1={u.x + BOX_W} y1={u.y + BOX_H / 2 + 6} x2={u.x + BOX_W + 40} y2={u.y + BOX_H / 2 + 6}
                  className="stroke-signal-info" strokeWidth={1.5} markerEnd="url(#sff-arrow)" />
                <text x={u.x + BOX_W + 4} y={u.y + BOX_H / 2 + 18 + (productLine.get(p.id) ?? 0) * LINE} className="fill-signal-info" fontSize={10}>
                  {short(p.name ?? p.id, rankOf.get(p.unit) === lastRank ? EDGE_CHARS : GAP_CHARS)}
                  <title>{p.name ?? p.id}</title>
                </text>
              </g>
            );
          })}
          {graph.nodes.map((n) => {
            const p = at.get(n.id)!;
            return (
              <g key={n.id} data-testid="sff-unit">
                <rect x={p.x} y={p.y} width={BOX_W} height={BOX_H} rx={5} className="fill-surface-0 stroke-ink" strokeWidth={1} />
                <text x={p.x + 8} y={p.y + 14} fontSize={11} className="fill-ink font-num">
                  {short(n.id, 16)}
                </text>
                <text x={p.x + 8} y={p.y + 27} fontSize={9} className="fill-ink-soft">
                  {short(typeOf.get(n.id) ?? '', 20)}
                </text>
                <title>{`${n.id} · ${n.type}${n.method ? ` · ${n.method}` : ''}`}</title>
              </g>
            );
          })}
        </svg>
      </div>
    </figure>
  );
}
