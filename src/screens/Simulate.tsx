// Scenario index (OF-DES-001 §8.13).
import { LineChart, Pin, PinOff, Plus, GitCompare } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import { evaluateGrid } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { PageHeader, Card, Button, LinkButton, cx, EmptyState } from '@/components/ui';
import { Tick } from '@/components/Provenance';

export default function Simulate() {
  const scenarios = useStore((s) => s.scenarios);
  const grids = useStore((s) => s.grids);
  const duplicateScenario = useStore((s) => s.duplicateScenario);
  const togglePin = useStore((s) => s.togglePin);

  const pinnedCount = scenarios.filter((s) => s.pinned).length;

  return (
    <div>
      <PageHeader
        title="Simulate"
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
            const linked = sc.assumptions.filter((a) => a.recordId).length;
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

                <Tick p="demo" className="mb-3">
                  <div className="text-caption uppercase tracking-wide text-ink-soft">
                    Minimum selling price
                  </div>
                  <div className="font-num text-display leading-none">
                    {result ? `$${fmt(result.msp, 1)}` : '—'}
                    <span className="text-body text-ink-soft ml-1">/kg</span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">
                    Demo model v0 — illustrative economics, not validated
                  </div>
                </Tick>

                <div className="text-caption text-ink-soft space-y-0.5 mb-3">
                  <div>
                    Sweep:{' '}
                    <span className="text-ink">{sc.dims.map((d) => d.label).join(' × ')}</span>
                  </div>
                  <div className="font-num">
                    {linked} of {sc.assumptions.length} assumptions linked to corpus records
                  </div>
                </div>

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
