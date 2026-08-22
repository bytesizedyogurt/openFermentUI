// Scenario index (OF-DES-001 §8.13).
import { LineChart, Pin, PinOff, Plus, GitCompare } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import { evaluateGrid } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { PageHeader, Card, Button, LinkButton, cx, EmptyState } from '@/components/ui';
import { Tick } from '@/components/Provenance';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('fermos', 'corpus');
export default function Simulate() {
  const scenarios = useStore((s) => s.scenarios);
  const grids = useStore((s) => s.grids);
  const duplicateScenario = useStore((s) => s.duplicateScenario);
  const togglePin = useStore((s) => s.togglePin);

  const pinnedCount = scenarios.filter((s) => s.pinned).length;

  return (
    <div>
      <PageHeader eyebrow={EYEBROW}
        title="Scenarios"
        subtitle="Turn verified parameters into economics. Each scenario is a sweep over a techno-economic model; every assumption carries its provenance."
        actions={
          <>
            <LinkButton to="/simulate/compare">
              <GitCompare size={14} /> Compare
              {pinnedCount > 0 && (
                <span className="font-num text-caption ml-1">({pinnedCount} pinned)</span>
              )}
            </LinkButton>
            <Button
              variant="primary"
              onClick={() => {
                const id = duplicateScenario(scenarios[0]?.id ?? '');
                navigate(`/simulate/${id}`);
              }}
              disabled={scenarios.length === 0}
            >
              <Plus size={14} /> New scenario
            </Button>
          </>
        }
      />

      {scenarios.length === 0 ? (
        <EmptyState
          title="No scenarios yet"
          body="A scenario pairs a cost model with a point in its sweep space."
          icon={<LineChart size={28} />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {scenarios.map((sc) => {
            const grid = grids[sc.modelId];
            const result = grid ? evaluateGrid(grid, sc.point) : null;
            // `a.basis.recordId`, not `a.recordId`.
            //
            // The top-level field is the pre-discriminator binding and is
            // populated on ZERO assumptions in the corpus, so this card reported
            // "0 of 12 assumptions linked to corpus records" while the corpus
            // holds six of them. The product's central claim is that a cost
            // assumption binds to a Ledger record; its own index denied it.
            // `ScenarioWorkspace` reads `basis.kind` and has always printed the
            // right number on the very next screen.
            const linked = sc.assumptions.filter((a) => a.basis.kind === 'record').length;
            return (
              <Card key={sc.id} className="p-4 flex flex-col">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="chip font-num">{sc.modelId}</span>
                  <button
                    className={cx('btn btn-sm', sc.pinned && 'text-accent border-accent/40')}
                    onClick={() => togglePin(sc.id)}
                    aria-pressed={sc.pinned}
                    title={sc.pinned ? 'Unpin from compare' : 'Pin to compare'}
                  >
                    {sc.pinned ? <Pin size={13} /> : <PinOff size={13} />}
                  </button>
                </div>

                <a
                  href={`#/fermos/s/${sc.id}`}
                  className="font-serif text-section-title font-semibold hover:text-accent leading-snug"
                >
                  {sc.name}
                </a>
                <p className="text-body text-ink-soft mt-1 mb-3 flex-1">{sc.description}</p>

                {/* WHAT fermOS OWNS, FIRST.
                    This card led with the minimum selling price — Proforma's
                    number, at Proforma's weight — which is what made the two
                    parts' indexes the same screen. A scenario IS a space: a set
                    of axes and a point on them. */}
                <dl className="text-caption mb-3 border-y border-line divide-y divide-line">
                  {sc.dims.map((d) => (
                    <div key={d.key} className="flex items-baseline justify-between gap-3 py-1">
                      <dt className="text-ink-soft truncate">{d.label}</dt>
                      <dd className="font-num text-ink whitespace-nowrap">
                        {fmt(sc.point[d.key])}
                        <span className="text-ink-soft ml-1">{d.unit}</span>
                      </dd>
                    </div>
                  ))}
                </dl>

                <div className="text-caption text-ink-soft mb-3">
                  <span className="font-num text-ink">{linked}</span> of{' '}
                  <span className="font-num text-ink">{sc.assumptions.length}</span> assumptions
                  bind to a Ledger record.
                </div>

                {/* Proforma's number, named as Proforma's — the same quotation
                    form the plant and workspace screens use. */}
                <a
                  href={`#/proforma/price/${sc.id}`}
                  className="text-caption text-ink-soft hover:text-accent motion-colors mb-3 block"
                >
                  Priced by Proforma at{' '}
                  <span className="font-num text-ink">{result ? fmt(result.msp, 1) : '—'}</span> USD
                  kg⁻¹ →
                </a>

                <LinkButton to={`/simulate/${sc.id}`} variant="primary" className="justify-center">
                  Open scenario
                </LinkButton>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
