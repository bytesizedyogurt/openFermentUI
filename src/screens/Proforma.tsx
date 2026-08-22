// Proforma — the part index, and the corpus pool's first Proforma surface.
//
// ── WHY THIS FILE IS NEW ──────────────────────────────────────────────────
//
// Proforma had a rail entry, a charter, a Pydantic schema, an `EconomicsAdapter`
// and a shipped MCP server that reads `data/corpus/scenarios.json` — and not one
// corpus screen. Every `/proforma/*` route rendered the demo pool, and
// `partEyebrow('proforma', 'corpus')` was uncalled anywhere in the build. The
// corpus's entire techno-economics lived under fermOS's name.
//
// ── TWO POOLS, TWO SCREENS, ONE PART ──────────────────────────────────────
//
// Precedent is `parchment` and `notary`, and the rule `App.tsx` states for them:
// two pools stay in separate screens because the corpus half reads through the
// adapter seam and the demo half reads its modules directly. This file holds no
// `Candidate` and no `FacilityConcept`; `ProformaDemoCard` does, and is composed
// rather than imported from.
//
// ── WHY THE INDEX QUOTES THE GRID AND THE PRICE SCREEN SOLVES ─────────────
//
// An index of three plants that solved three flowsheets to draw three numbers
// would spend a second of main thread to say what the precomputed sweep already
// knows. `evaluateGrid` is the interpolation CLAUDE.md deliberately keeps in
// TypeScript, and the difference from the solve is stated on the card rather
// than hidden — a reader who wants the solved price clicks through to it.
import { Calculator } from 'lucide-react';

import { useStore } from '@/store';
import { evaluateGrid } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { href } from '@/router';
import { partEyebrow } from '@/data/parts';
import { ProformaDemoCard } from '@/components/demo/ProformaDemoCard';
import { Tick } from '@/components/Provenance';
import { PageHeader, Card, SectionTitle, EmptyState } from '@/components/ui';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('proforma', 'corpus');

export default function Proforma() {
  const scenarios = useStore((s) => s.scenarios);
  const grids = useStore((s) => s.grids);

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
        title="Proforma"
        subtitle="Techno-economics against an explicit regional and temporal basis. fermOS sizes a plant; this part discounts it and says what frame the answer is quoted in."
      />

      <section className="mb-6">
        <SectionTitle right={<span className="text-caption text-ink-soft">β-casein corpus</span>}>
          The plants, priced
        </SectionTitle>
        {scenarios.length === 0 ? (
          <EmptyState
            title="No scenarios to price"
            body="A price is solved from a plant. With no scenario there is no flowsheet, and nothing to discount."
            icon={<Calculator size={28} />}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {scenarios.map((sc) => {
              const grid = grids[sc.modelId];
              const result = grid ? evaluateGrid(grid, sc.point) : null;
              return (
                <Card key={sc.id} className="p-4 flex flex-col">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="chip font-num">{sc.modelId}</span>
                  </div>
                  <a
                    href={href(`/proforma/price/${sc.id}`)}
                    className="font-serif text-section-title font-semibold hover:text-accent leading-snug"
                  >
                    {sc.name}
                  </a>
                  <p className="text-body text-ink-soft mt-1 mb-3 flex-1">{sc.product}</p>

                  <Tick p="demo" className="mb-2">
                    <div className="text-caption uppercase tracking-wide text-ink-soft">
                      Minimum selling price
                    </div>
                    <div className="font-num text-display leading-none">
                      {result ? USD_KG(result.msp) : '—'}
                    </div>
                    <div className="text-caption text-ink-soft mt-0.5">
                      USD kg⁻¹ — read off the precomputed sweep. The solve at this point, with its
                      capital ladder and cash flow, is one click away.
                    </div>
                  </Tick>

                  <a
                    href={href(`/proforma/price/${sc.id}`)}
                    className="text-caption text-accent hover:underline"
                  >
                    The price and its basis →
                  </a>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <section className="mb-6">
        <SectionTitle>The other pool</SectionTitle>
        <ProformaDemoCard />
      </section>
    </>
  );
}

/** One format for a price, everywhere in this part. */
function USD_KG(v: number): string {
  return Number.isFinite(v) ? fmt(v, 1) : '—';
}
