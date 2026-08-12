// The flowsheet, drawn the way the plant is actually piped.
//
// bioSTEAM renders `system.diagram()` through graphviz, and the picture it
// produces is the most recognisable artifact the library has: boxes for units,
// chevrons for the streams entering and leaving, and orthogonal pipe runs
// between them. This draws the same object from the same graph the mass balance
// ran on — `BioSystem.diagram()` reads off `sources`, so a diagram that
// disagreed with the model would be a bug rather than a difference of opinion.
//
// The layout is done here rather than by a library because the flowsheets are
// seven to nine nodes and feed-forward by construction: a longest-path layering
// with a barycentre row assignment places them exactly as an engineer would, and
// a graph layout engine would cost more than the problem is worth.
import { useId, useMemo } from 'react';
import { Table2, Workflow } from 'lucide-react';
import type {
  FlowsheetEdge,
  FlowsheetGraph,
  FlowsheetNode,
  StreamRow,
} from '@/engine/biosteam/system';
import { AREA_NAMES } from '@/engine/biosteam/types';
import { fmt } from '@/engine/units';
import { useSeriesColor } from '@/lib/viz';
import { useStore } from '@/store';
import { EmptyState, cx } from '@/components/ui';

// ── Geometry ───────────────────────────────────────────────────────────

interface Metrics {
  nodeW: number;
  nodeH: number;
  termW: number;
  termH: number;
  gapX: number;
  gapY: number;
  pad: number;
}

/**
 * Two size sets, picked off the density setting.
 *
 * Read from the store rather than from the stamped `data-density` attribute
 * because these numbers go into an SVG coordinate system, and measuring the
 * document during render to find out how big to draw would be both a layout
 * read and a rule this app does not break.
 */
const COMFORTABLE: Metrics = { nodeW: 158, nodeH: 58, termW: 118, termH: 38, gapX: 82, gapY: 30, pad: 26 };
const DENSE: Metrics = { nodeW: 146, nodeH: 50, termW: 108, termH: 34, gapX: 70, gapY: 24, pad: 20 };

/**
 * How far the drawing may be scaled down before it scrolls instead.
 *
 * A nine-unit train is close to 2400px wide, and a viewBox will happily squeeze
 * that into a 900px card — at which point the stream labels render at four
 * pixels and the drawing becomes a texture. Below this scale the container
 * scrolls sideways, which is what a wide PFD has always done on paper.
 */
const MIN_SCALE = 0.85;

interface Placed {
  node: FlowsheetNode;
  col: number;
  row: number;
  x: number;
  y: number;
  w: number;
  h: number;
  /** Vertical centre, where pipes attach. */
  midY: number;
}

interface Layout {
  placed: Placed[];
  byId: Map<string, Placed>;
  width: number;
  height: number;
}

/** Ranking used to break row ties: the process trunk keeps the top row. */
const KIND_RANK: Record<FlowsheetNode['kind'], number> = { feed: 0, unit: 0, product: 1, waste: 2 };

/**
 * Column by longest path from the feeds, row by predecessor barycentre.
 *
 * Longest path rather than shortest is what makes a bypass line up with the
 * step it bypasses: a stream that skips a unit still has to be drawn arriving
 * beside the stream that went through it, and shortest-path layering would draw
 * it arriving a column early.
 */
function layout(graph: FlowsheetGraph, m: Metrics): Layout {
  const nodes = graph.nodes;
  const index = new Map(nodes.map((n, i) => [n.id, i]));
  const edges = graph.edges.filter((e) => index.has(e.from) && index.has(e.to));

  const succ = new Map<string, string[]>();
  const pred = new Map<string, string[]>();
  for (const n of nodes) {
    succ.set(n.id, []);
    pred.set(n.id, []);
  }
  for (const e of edges) {
    succ.get(e.from)?.push(e.to);
    pred.get(e.to)?.push(e.from);
  }

  const depth = new Map<string, number>();
  const indegree = new Map<string, number>();
  for (const n of nodes) {
    depth.set(n.id, 0);
    indegree.set(n.id, (pred.get(n.id) ?? []).length);
  }

  const queue = nodes.filter((n) => (indegree.get(n.id) ?? 0) === 0).map((n) => n.id);
  const settled = new Set<string>(queue);
  for (let i = 0; i < queue.length; i++) {
    const id = queue[i];
    const d = depth.get(id) ?? 0;
    for (const s of succ.get(id) ?? []) {
      depth.set(s, Math.max(depth.get(s) ?? 0, d + 1));
      const left = (indegree.get(s) ?? 0) - 1;
      indegree.set(s, left);
      if (left <= 0 && !settled.has(s)) {
        settled.add(s);
        queue.push(s);
      }
    }
  }

  // Nothing here tears a recycle and the flowsheets have none, so a node the
  // topological sweep never reached means the graph is malformed. It gets a
  // column of its own on the right, because a diagram that drops a unit is far
  // worse than one that draws it somewhere odd.
  let deepest = 0;
  for (const id of settled) deepest = Math.max(deepest, depth.get(id) ?? 0);
  for (const n of nodes) {
    if (settled.has(n.id)) continue;
    deepest += 1;
    depth.set(n.id, deepest);
  }

  // Feeds sit one column left of whatever they feed rather than all at column
  // zero, so a stream entering halfway down the train enters beside the unit
  // that takes it instead of trailing a pipe across the whole picture.
  for (const n of nodes) {
    if (n.kind !== 'feed') continue;
    const downstream = succ.get(n.id) ?? [];
    if (downstream.length === 0) continue;
    const first = Math.min(...downstream.map((s) => depth.get(s) ?? 1));
    depth.set(n.id, Math.max(0, first - 1));
  }

  // Products leave at the right edge, level with each other, which is the
  // convention every PFD follows and the reason the eye can find them.
  let last = 0;
  for (const n of nodes) last = Math.max(last, depth.get(n.id) ?? 0);
  for (const n of nodes) {
    if (n.kind === 'product' && (pred.get(n.id) ?? []).length > 0) depth.set(n.id, last);
  }

  const used = [...new Set(nodes.map((n) => depth.get(n.id) ?? 0))].sort((a, b) => a - b);
  const column = new Map(used.map((d, i) => [d, i]));

  const row = new Map<string, number>();
  for (let c = 0; c < used.length; c++) {
    const group = nodes.filter((n) => column.get(depth.get(n.id) ?? 0) === c);
    const want = new Map<string, number>();
    for (const n of group) {
      const rows = (pred.get(n.id) ?? [])
        .map((p) => row.get(p))
        .filter((r): r is number => r !== undefined);
      want.set(n.id, rows.length > 0 ? rows.reduce((t, r) => t + r, 0) / rows.length : 0);
    }
    const wanted = (id: string): number => want.get(id) ?? 0;
    group.sort(
      (a, b) =>
        wanted(a.id) - wanted(b.id) ||
        KIND_RANK[a.kind] - KIND_RANK[b.kind] ||
        (index.get(a.id) ?? 0) - (index.get(b.id) ?? 0),
    );
    let next = 0;
    for (const n of group) {
      const r = Math.max(next, Math.round(wanted(n.id)));
      row.set(n.id, r);
      next = r + 1;
    }
  }

  const colStride = m.nodeW + m.gapX;
  const rowStride = m.nodeH + m.gapY;
  const placed: Placed[] = nodes.map((n) => {
    const c = column.get(depth.get(n.id) ?? 0) ?? 0;
    const r = row.get(n.id) ?? 0;
    const slotX = m.pad + c * colStride;
    const slotY = m.pad + r * rowStride;
    const terminal = n.kind !== 'unit';
    const w = terminal ? m.termW : m.nodeW;
    const h = terminal ? m.termH : m.nodeH;
    // Feed terminals hug the right of their slot and everything else the left,
    // so the pipe between a terminal and its unit stays short.
    const x = terminal && n.kind === 'feed' ? slotX + m.nodeW - m.termW : slotX;
    const y = slotY + (m.nodeH - h) / 2;
    return { node: n, col: c, row: r, x, y, w, h, midY: y + h / 2 };
  });

  const cols = Math.max(1, used.length);
  const rows = placed.reduce((t, p) => Math.max(t, p.row + 1), 1);
  return {
    placed,
    byId: new Map(placed.map((p) => [p.node.id, p])),
    width: m.pad * 2 + cols * m.nodeW + (cols - 1) * m.gapX,
    height: m.pad * 2 + rows * m.nodeH + (rows - 1) * m.gapY,
  };
}

interface Route {
  d: string;
  labelX: number;
  labelY: number;
}

/**
 * An orthogonal pipe run from one node's right edge to the next node's left.
 *
 * Right angles are not decoration. A diagonal between two boxes reads as a
 * graph edge — an abstract relation — and a right angle reads as a pipe, which
 * is what it is. The corners get an 8px radius for the same reason a drafted
 * elbow is not square.
 */
function route(from: Placed, to: Placed, m: Metrics): Route {
  const x1 = from.x + from.w;
  const y1 = from.midY;
  const x2 = to.x;
  const y2 = to.midY;

  if (Math.abs(y1 - y2) < 0.5) {
    return { d: `M ${x1} ${y1} H ${x2}`, labelX: (x1 + x2) / 2, labelY: y1 };
  }

  // For the adjacent columns these flowsheets are made of, this is the middle
  // of the gap. For a rarer long edge it is the gap immediately before the
  // target, which keeps the vertical leg out of a column of boxes.
  const turn = x2 - x1 > m.gapX * 1.5 ? x2 - m.gapX / 2 : (x1 + x2) / 2;
  const dir = y2 > y1 ? 1 : -1;
  const r = Math.max(0, Math.min(8, Math.abs(y2 - y1) / 2, Math.abs(turn - x1), Math.abs(x2 - turn)));
  const d =
    `M ${x1} ${y1} H ${turn - r}` +
    ` Q ${turn} ${y1} ${turn} ${y1 + dir * r}` +
    ` V ${y2 - dir * r}` +
    ` Q ${turn} ${y2} ${turn + r} ${y2}` +
    ` H ${x2}`;

  // A branch is labelled on the run at its own row rather than at the row it
  // left. Every line leaving a unit starts at the same height, so labelling the
  // first run stacks the vent on top of the broth; after the elbow each branch
  // has the row to itself.
  return { d, labelX: (turn + x2) / 2, labelY: y2 };
}

// ── Text fitting ───────────────────────────────────────────────────────

function clip(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, Math.max(1, max - 1))}…`;
}

/**
 * Unit IDs are a tag and a name — "R301 fermenter" — and the tag is the half a
 * reader looks for, so it gets its own line in mono and the name sits under it.
 */
function splitID(label: string): { tag: string; name: string } {
  const i = label.indexOf(' ');
  return i === -1 ? { tag: label, name: '' } : { tag: label.slice(0, i), name: label.slice(i + 1) };
}

/**
 * Outlet streams are named after the unit that made them, which is redundant on
 * a diagram where the pipe already leaves that unit. Dropping the prefix turns
 * "C401 disc stack-cake" into "cake", which is the part that says anything.
 */
function shortStream(streamID: string, sourceLabel: string): string {
  return streamID.startsWith(`${sourceLabel}-`) ? streamID.slice(sourceLabel.length + 1) : streamID;
}

/**
 * Process areas in the order the capital chart uses.
 *
 * `BioSystem.byArea()` sorts ascending and the Plant screen colours those bars
 * by their index, so indexing the same sorted list here is what makes the bar
 * for Fermentation and the accent on R301 the same colour.
 */
function areaOrder(graph: FlowsheetGraph): number[] {
  return [...new Set(graph.nodes.filter((n) => n.kind === 'unit').map((n) => n.area))].sort(
    (a, b) => a - b,
  );
}

/** One sentence naming the train, for anyone who cannot see the drawing. */
function summarise(graph: FlowsheetGraph): string {
  const units = graph.nodes.filter((n) => n.kind === 'unit');
  const feeds = graph.nodes.filter((n) => n.kind === 'feed').map((n) => n.label);
  const products = graph.nodes.filter((n) => n.kind === 'product').map((n) => n.label);
  const wastes = graph.nodes.filter((n) => n.kind === 'waste').length;
  const list = (xs: string[]): string =>
    xs.length === 0 ? 'no declared stream' : xs.length === 1 ? xs[0] : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`;
  const tail = wastes === 0 ? '' : `, with ${wastes} unrecovered stream${wastes === 1 ? '' : 's'} leaving the train`;
  return `Process flow diagram: ${units.length} unit operations from ${list(feeds)} to ${list(products)}${tail}.`;
}

// ── The diagram ────────────────────────────────────────────────────────

export function Flowsheet({
  graph,
  streams,
  onSelectUnit,
  selectedUnit,
}: {
  graph: FlowsheetGraph;
  streams: StreamRow[];
  onSelectUnit?: (id: string | null) => void;
  selectedUnit?: string | null;
}): JSX.Element {
  const density = useStore((s) => s.ui.density);
  const seriesColor = useSeriesColor();
  // A DOM id per instance, so two flowsheets on one page cannot claim each
  // other's arrowhead markers.
  const uid = useId().replace(/:/g, '');

  const m = density === 'dense' ? DENSE : COMFORTABLE;
  const { placed, byId, width, height } = useMemo(() => layout(graph, m), [graph, m]);

  const areaIndex = useMemo(() => {
    const order = areaOrder(graph);
    return new Map(order.map((a, i) => [a, i]));
  }, [graph]);

  const flowOf = useMemo(() => {
    const table = new Map<string, number>();
    for (const s of streams) if (!table.has(s.ID)) table.set(s.ID, s.massFlow);
    return table;
  }, [streams]);

  const drawn = useMemo(
    () => graph.edges.filter((e) => byId.has(e.from) && byId.has(e.to)),
    [graph.edges, byId],
  );

  const maxFlow = useMemo(
    () => drawn.reduce((t, e) => Math.max(t, flowOf.get(e.label) ?? 0), 0),
    [drawn, flowOf],
  );

  // What made each terminal stream, so its label can drop the unit prefix the
  // pipe already shows.
  const terminalSource = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of drawn) {
      const from = byId.get(e.from);
      if (from) map.set(e.to, from.node.label);
    }
    return map;
  }, [drawn, byId]);

  if (placed.length === 0) {
    return (
      <EmptyState
        icon={<Workflow size={20} />}
        title="No flowsheet"
        body="The system declared no units, which means it did not build. There is nothing to draw and nothing will be invented to fill the space."
      />
    );
  }

  /**
   * Line weight carries mass flow on a log scale, over 1.1 to 2.4px and no
   * wider. A PFD is read for topology first, and a weight range broad enough to
   * be measured off the page would turn the trunk into a bar chart, swamp the
   * arrowheads and imply a precision the drawing does not have. This is a hint
   * that the broth line is the big one, not a quantity.
   */
  const strokeFor = (streamID: string): number => {
    const kg = flowOf.get(streamID) ?? 0;
    if (!(kg > 0) || maxFlow <= 0) return 1.1;
    return 1.1 + 1.3 * (Math.log10(1 + kg) / Math.log10(1 + maxFlow));
  };

  const toneOf = (edge: FlowsheetEdge): { stroke: string; marker: string } =>
    edge.kind === 'product'
      ? { stroke: 'stroke-ink', marker: `${uid}-arrow-strong` }
      : edge.kind === 'waste'
        ? { stroke: 'stroke-ink-soft/45', marker: `${uid}-arrow-muted` }
        : { stroke: 'stroke-ink-soft/80', marker: `${uid}-arrow` };

  const select = (node: FlowsheetNode): void => {
    if (!onSelectUnit) return;
    onSelectUnit(selectedUnit === node.id ? null : node.id);
  };

  const nameChars = Math.floor((m.nodeW - 26) / 5.7);
  const termChars = Math.floor((m.termW - 20) / 6.4);

  return (
    <div>
      <div className="overflow-x-auto">
        {/* The drawing announces itself as one image with one sentence, which
            is the honest description of it — a screen reader walking eighty
            polylines learns nothing. The units below stay focusable so a
            keyboard can drive the selection, and the disclosure underneath
            carries the connectivity in a form that can actually be read. */}
        <svg
          role="img"
          aria-label={summarise(graph)}
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          height={height}
          preserveAspectRatio="xMidYMid meet"
          className="h-auto select-none"
          style={{ maxWidth: '100%', minWidth: Math.round(width * MIN_SCALE) }}
        >
          <defs>
            {/* userSpaceOnUse keeps the arrowhead one size while the line weight
                encodes flow — markers scale with stroke width by default, and a
                fat pipe would arrive under a fat arrow. */}
            {[
              { id: `${uid}-arrow`, fill: 'fill-ink-soft/80' },
              { id: `${uid}-arrow-strong`, fill: 'fill-ink' },
              { id: `${uid}-arrow-muted`, fill: 'fill-ink-soft/45' },
            ].map((mk) => (
              <marker
                key={mk.id}
                id={mk.id}
                markerWidth="8"
                markerHeight="8"
                refX="7.4"
                refY="4"
                orient="auto"
                markerUnits="userSpaceOnUse"
              >
                <path d="M 0.5 1 L 7.4 4 L 0.5 7 Z" className={mk.fill} />
              </marker>
            ))}
          </defs>

          <g>
            {drawn.map((e, i) => {
              const from = byId.get(e.from);
              const to = byId.get(e.to);
              if (!from || !to) return null;
              const path = route(from, to, m);
              const tone = toneOf(e);
              const named = shortStream(e.label, from.node.label);
              // A terminal is labelled with its own stream, so repeating that
              // name on the pipe an inch away is ink for nothing — at either end.
              const namedAtTerminal =
                (to.node.kind !== 'unit' &&
                  shortStream(to.node.label, terminalSource.get(to.node.id) ?? '') === named) ||
                (from.node.kind === 'feed' && from.node.label === named);
              const label = namedAtTerminal ? '' : clip(named, 13);
              const kg = flowOf.get(e.label);
              return (
                <g key={`${e.from}→${e.to}-${e.label}-${i}`}>
                  <path
                    d={path.d}
                    fill="none"
                    className={tone.stroke}
                    strokeWidth={strokeFor(e.label)}
                    strokeLinecap="butt"
                    markerEnd={`url(#${tone.marker})`}
                  />
                  {label && (
                    <text
                      x={path.labelX}
                      y={path.labelY - 6}
                      textAnchor="middle"
                      fontSize={10}
                      className="font-num fill-ink-soft"
                    >
                      {label}
                      <title>
                        {e.label}
                        {kg === undefined ? '' : ` — ${fmt(kg)} kg/hr`}
                      </title>
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          <g>
            {placed.map((p) => {
              const n = p.node;

              if (n.kind !== 'unit') {
                // Terminals are trapezoids and chevrons rather than boxes,
                // because a stream entering or leaving the battery limits is not
                // a piece of equipment and should not look like one. Emphasis is
                // carried by border weight, not hue — hue is spoken for by the
                // process areas.
                const feed = n.kind === 'feed';
                const product = n.kind === 'product';
                const slant = 9;
                const shape = feed
                  ? `${p.x},${p.y} ${p.x + p.w - 12},${p.y} ${p.x + p.w},${p.midY} ${p.x + p.w - 12},${p.y + p.h} ${p.x},${p.y + p.h}`
                  : `${p.x + slant},${p.y} ${p.x + p.w},${p.y} ${p.x + p.w - slant},${p.y + p.h} ${p.x},${p.y + p.h}`;
                return (
                  <g key={n.id}>
                    <polygon
                      points={shape}
                      className={product ? 'fill-surface-1 stroke-ink' : 'fill-surface-0 stroke-line'}
                      strokeWidth={product ? 1.5 : 1}
                      strokeLinejoin="round"
                    />
                    <text
                      x={p.x + p.w / 2 - (feed ? 4 : 0)}
                      y={p.midY + 4}
                      textAnchor="middle"
                      fontSize={11}
                      className={cx('font-num', n.kind === 'waste' ? 'fill-ink-soft' : 'fill-ink')}
                    >
                      {clip(shortStream(n.label, terminalSource.get(n.id) ?? ''), termChars)}
                      <title>
                        {n.label} — {n.kind === 'feed' ? 'feed' : n.kind === 'product' ? 'product' : 'unrecovered stream'}
                      </title>
                    </text>
                  </g>
                );
              }

              const { tag, name } = splitID(n.label);
              const selected = selectedUnit === n.id;
              const authored = n.costSource === 'authored';
              const warned = (n.warnings ?? 0) > 0;
              const tint = seriesColor(areaIndex.get(n.area) ?? 0);
              const label = [
                `${n.label}, ${n.line ?? 'unit operation'}`,
                AREA_NAMES[n.area] ? `${AREA_NAMES[n.area]} area` : null,
                authored ? 'authored cost correlation' : null,
                warned ? `${n.warnings} design warning${n.warnings === 1 ? '' : 's'}` : null,
                selected ? 'selected' : null,
              ]
                .filter(Boolean)
                .join(', ');

              return (
                <g
                  key={n.id}
                  role={onSelectUnit ? 'button' : undefined}
                  tabIndex={onSelectUnit ? 0 : undefined}
                  aria-label={onSelectUnit ? label : undefined}
                  aria-pressed={onSelectUnit ? selected : undefined}
                  onClick={() => select(n)}
                  onKeyDown={(e) => {
                    if (e.key !== 'Enter' && e.key !== ' ') return;
                    e.preventDefault();
                    select(n);
                  }}
                  className={cx('group focus:outline-none', onSelectUnit && 'cursor-pointer')}
                >
                  {/* Selection and focus both ring the box, one always visible
                      and one only while focused, so a keyboard walk through the
                      train never leaves the reader guessing where they are. */}
                  <rect
                    x={p.x - 4}
                    y={p.y - 4}
                    width={p.w + 8}
                    height={p.h + 8}
                    rx={11}
                    fill="none"
                    className={cx(
                      'stroke-accent',
                      selected ? 'opacity-100' : 'opacity-0 group-focus-visible:opacity-100',
                    )}
                    strokeWidth={1.5}
                  />
                  <rect
                    x={p.x}
                    y={p.y}
                    width={p.w}
                    height={p.h}
                    rx={7}
                    className={cx(
                      selected ? 'fill-accent-wash' : 'fill-surface-1',
                      selected ? 'stroke-accent' : 'stroke-line',
                      onSelectUnit && 'group-hover:stroke-accent/70',
                    )}
                    strokeWidth={1}
                    // The dash is the same claim the "authored" chip makes in
                    // the equipment table: this cost came from a correlation
                    // written here, not from bioSTEAM.
                    strokeDasharray={authored ? '4 2.5' : undefined}
                  />
                  {/* The area rail, at the same 3px the evidence tick uses
                      throughout the app. */}
                  <rect
                    x={p.x + 7}
                    y={p.y + 7}
                    width={3}
                    height={p.h - 14}
                    rx={1.5}
                    fill={tint}
                  />
                  <text
                    x={p.x + 17}
                    y={p.y + (name ? p.h * 0.34 : p.h * 0.44)}
                    fontSize={12}
                    className="font-num fill-ink"
                    fontWeight={500}
                  >
                    {clip(tag, nameChars)}
                  </text>
                  {name && (
                    <text x={p.x + 17} y={p.y + p.h * 0.59} fontSize={11} className="fill-ink">
                      {clip(name, nameChars)}
                    </text>
                  )}
                  <text
                    x={p.x + 17}
                    y={p.y + (name ? p.h * 0.83 : p.h * 0.76)}
                    fontSize={10}
                    className="fill-ink-soft"
                  >
                    {clip(n.line ?? '', nameChars)}
                  </text>
                  {warned && (
                    <path
                      d={`M ${p.x + p.w - 15} ${p.y + 15} L ${p.x + p.w - 8.5} ${p.y + 15} L ${p.x + p.w - 11.75} ${p.y + 8} Z`}
                      className="fill-signal-warn/20 stroke-signal-warn"
                      strokeWidth={1}
                      strokeLinejoin="round"
                    />
                  )}
                  <title>
                    {n.label} — {n.line ?? 'unit operation'}
                  </title>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      <details className="mt-2">
        <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
          <Table2 size={12} /> View as table
        </summary>
        <div className="overflow-x-auto mt-1.5">
          <table className="w-full text-caption">
            <caption className="sr-only">{summarise(graph)}</caption>
            <thead>
              <tr className="border-b border-line text-ink-soft">
                <th className="text-left py-1 pr-3 whitespace-nowrap">From</th>
                <th className="text-left py-1 pr-3 whitespace-nowrap">To</th>
                <th className="text-left py-1 pr-3 whitespace-nowrap">Stream</th>
                <th className="text-right py-1 whitespace-nowrap">kg hr⁻¹</th>
              </tr>
            </thead>
            <tbody>
              {drawn.map((e, i) => {
                const kg = flowOf.get(e.label);
                return (
                  <tr key={`${e.from}-${e.to}-${e.label}-${i}`} className="border-b border-line/50">
                    <td className="py-1 pr-3 whitespace-nowrap font-num">
                      {byId.get(e.from)?.node.label ?? e.from}
                    </td>
                    <td className="py-1 pr-3 whitespace-nowrap font-num">
                      {byId.get(e.to)?.node.label ?? e.to}
                    </td>
                    <td className="py-1 pr-3 whitespace-nowrap font-num">{e.label}</td>
                    <td className="py-1 text-right whitespace-nowrap font-num">
                      {kg === undefined ? '—' : fmt(kg)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

// ── Legend ─────────────────────────────────────────────────────────────

export function FlowsheetLegend({ graph }: { graph: FlowsheetGraph }): JSX.Element {
  const seriesColor = useSeriesColor();
  const areas = useMemo(() => areaOrder(graph), [graph]);
  const authored = graph.nodes.some((n) => n.kind === 'unit' && n.costSource === 'authored');
  const warned = graph.nodes.some((n) => n.kind === 'unit' && (n.warnings ?? 0) > 0);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-caption text-ink-soft">
      {areas.map((a, i) => (
        <span key={a} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block w-[3px] h-3 rounded-[1px] shrink-0"
            style={{ background: seriesColor(i) }}
            aria-hidden
          />
          {AREA_NAMES[a] ?? `Area ${a}`}
        </span>
      ))}
      {authored && (
        <span className="inline-flex items-center gap-1.5">
          <svg width="20" height="13" aria-hidden className="shrink-0">
            <rect
              x="0.5"
              y="0.5"
              width="19"
              height="12"
              rx="3"
              fill="none"
              className="stroke-line"
              strokeDasharray="4 2.5"
            />
          </svg>
          authored cost correlation
        </span>
      )}
      {warned && (
        <span className="inline-flex items-center gap-1.5">
          <svg width="13" height="13" aria-hidden className="shrink-0">
            <path
              d="M 1.5 10.5 L 11.5 10.5 L 6.5 2.5 Z"
              className="fill-signal-warn/20 stroke-signal-warn"
              strokeWidth="1"
              strokeLinejoin="round"
            />
          </svg>
          sized or costed outside the validated range
        </span>
      )}
      <span className="inline-flex items-center gap-1.5">
        <svg width="20" height="13" aria-hidden className="shrink-0">
          <polygon
            points="4.5,0.5 19.5,0.5 15.5,12.5 0.5,12.5"
            className="fill-surface-1 stroke-ink"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
        product leaving the battery limits
      </span>
    </div>
  );
}
