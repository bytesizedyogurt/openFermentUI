// The decomposition tree (OF-DEMO-002 §4.8).
//
// Archetype 5's deliverable. The system is handed a question it cannot answer
// as posed and restructures it, and the tree is the restructuring made
// inspectable.
//
// PATENT DENSITY IS A FOUR-STEP VISUAL SCALE, deliberately, and the reason is
// in OF-DEMO-003 §2: the asymmetry must be PRE-VERBAL. Eight jurisdictions
// enclosed against one open should be visible as a shape before anybody reads
// the label, because that asymmetry is the line the room remembers.
//
// Leaves carry a handoff. That is the composability demonstration — clicking a
// branch spawns a route comparison — and it is why `spawnsFlowId` exists on the
// node rather than being wired at the call site.
import { useState } from 'react';
import { ChevronRight, ChevronDown, ArrowUpRight } from 'lucide-react';

import type { ProblemNode } from '@/data/demo/types';
import { ORGANISM_BY_ID } from '@/data/demo/core';
import { AUX_ORGANISMS } from '@/data/demo/archetypes';
import { href } from '@/router';
import { cx } from '@/components/ui';

const DENSITY_STEPS: Record<ProblemNode['patentDensity'], number> = {
  low: 1,
  moderate: 2,
  high: 3,
  'very-high': 4,
};

const MATURITY_LABEL: Record<ProblemNode['technicalMaturity'], string> = {
  demonstrated: 'demonstrated at scale',
  pilot: 'pilot',
  lab: 'lab',
  speculative: 'speculative',
};

const REC_STYLE: Record<ProblemNode['recommendation'], { label: string; className: string }> = {
  build: { label: 'build', className: 'text-signal-open' },
  license: { label: 'license', className: 'text-signal-warn' },
  partner: { label: 'partner', className: 'text-signal-info' },
  avoid: { label: 'avoid', className: 'text-signal-closed' },
};

/** Four steps, filled left to right. Readable in greyscale; that is the point. */
export function PatentDensity({ level }: { level: ProblemNode['patentDensity'] }) {
  const n = DENSITY_STEPS[level];
  return (
    <span className="inline-flex items-center gap-[2px] align-middle" title={`Patent density: ${level}`}>
      {[1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={cx(
            'inline-block w-[6px] h-[10px] border border-signal-closed',
            i <= n ? 'bg-signal-closed opacity-85' : 'bg-transparent opacity-35',
          )}
        />
      ))}
    </span>
  );
}

function organismName(id: string): string {
  const o = ORGANISM_BY_ID[id] ?? AUX_ORGANISMS.find((x) => x.id === id);
  return o ? o.binomial : id;
}

function Node({
  node,
  nodes,
  depth,
  onSpawn,
}: {
  node: ProblemNode;
  nodes: ProblemNode[];
  depth: number;
  onSpawn?: (n: ProblemNode) => void;
}) {
  const children = nodes.filter((x) => x.parentId === node.id);
  const [open, setOpen] = useState(depth < 2);
  const rec = REC_STYLE[node.recommendation];

  return (
    <div style={{ marginLeft: depth === 0 ? 0 : 16 }}>
      <div
        className={cx(
          'flex items-start gap-2 py-1.5 border-l',
          depth === 0 ? 'border-transparent' : 'border-line pl-3',
        )}
      >
        <button
          className={cx('mt-0.5 shrink-0 text-ink-soft hover:text-ink', !children.length && 'invisible')}
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? 'collapse' : 'expand'}
        >
          {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className={cx(depth === 0 ? 'font-medium' : '')}>{node.label}</span>
            <PatentDensity level={node.patentDensity} />
            <span className={cx('text-caption', rec.className)}>{rec.label}</span>
            <span className="text-caption text-ink-soft">{MATURITY_LABEL[node.technicalMaturity]}</span>
          </div>

          {node.molecularTarget && (
            <div className="text-caption text-ink-soft">
              target: <span className="font-num">{node.molecularTarget}</span>
            </div>
          )}

          {node.candidateOrganismIds.length > 0 && (
            <div className="text-caption text-ink-soft">
              hosts:{' '}
              {node.candidateOrganismIds.map((id, i) => (
                <span key={id}>
                  {i > 0 && ', '}
                  <a href={href(`/geneos/${id}`)} className="italic hover:text-accent">
                    {organismName(id)}
                  </a>
                </span>
              ))}
            </div>
          )}

          <div className="text-caption text-ink-soft mt-0.5">{node.rationale}</div>

          <div className="flex flex-wrap items-center gap-2 mt-1">
            {node.accessionIds.slice(0, 6).map((id) => (
              <a key={id} href={href(`/repo/a/${id}`)} className="text-caption font-num text-ink-soft hover:text-accent">
                {id}
              </a>
            ))}
            {node.accessionIds.length > 6 && (
              <span className="text-caption text-ink-soft">+{node.accessionIds.length - 6}</span>
            )}
            {node.spawnsFlowId && (
              <button
                className="text-caption text-accent hover:underline inline-flex items-center gap-1"
                onClick={() => onSpawn?.(node)}
              >
                run this as a route comparison
                <ArrowUpRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {open && children.map((c) => <Node key={c.id} node={c} nodes={nodes} depth={depth + 1} onSpawn={onSpawn} />)}
    </div>
  );
}

export function ProblemTree({
  rootId,
  nodes,
  onSpawn,
  className,
}: {
  rootId: string;
  nodes: ProblemNode[];
  onSpawn?: (n: ProblemNode) => void;
  className?: string;
}) {
  const root = nodes.find((n) => n.id === rootId);
  if (!root) {
    return <div className="text-caption text-signal-error">No node {rootId} in this tree.</div>;
  }
  return (
    <div className={className}>
      <Node node={root} nodes={nodes} depth={0} onSpawn={onSpawn} />
    </div>
  );
}

export { DENSITY_STEPS };
