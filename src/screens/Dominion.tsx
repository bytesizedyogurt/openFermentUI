// Dominion — patents and clearance (OF-BLD-008 §4).
//
// NOT A PLACEHOLDER. Dominion arrives with the molecule catalogue as its
// default view and the clearance engine behind it — 117 molecules, six
// jurisdictions, and a set of authored findings. `Molecules.tsx` and
// `MoleculeDetail.tsx` are the same files they were; what changed is that they
// live under an owner now, because a catalogue of what could be made is
// inseparable from the question of who already owns it.
//
// WHAT THIS SCREEN MUST NOT DO is make the coverage look better than it is.
// The clearance distribution below counts stored headline states, which are
// claim-architecture judgements and are NOT resolved to any jurisdiction; the
// per-jurisdiction matrix is almost entirely unassessed and says so. A reader
// glancing at "21 blocked" must not come away thinking somebody searched.
//
// The four unbuilt pieces — Claim Workbench, Priority Engine, Enablement,
// Notary — used to be an UnbuiltList inside the clearance view. They are the
// four Dominion subsystems, so `SubsystemShelf` now names each of them AND
// carries the reference content for it (OF-BLD-010). Keeping both would have
// stated the same four absences twice on one screen, and the shelf says more.
import { useMemo } from 'react';
import { PRODUCTS } from '@/data/products';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';
import { CLEARANCE_FINDINGS } from '@/data/clearanceFindings';
import {
  CLEARANCE_MODEL_NOTE,
  HEADLINE_SCOPE_NOTE,
  JURISDICTIONS,
} from '@/engine/clearance';
import { href, useRoute } from '@/router';
import { Callout, Card, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { OwnerTabs, activeTab, type OwnerTab } from '@/components/OwnerTabs';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import Molecules from './Molecules';


const RISK_TONE: Record<string, string> = {
  low: 'text-accent',
  'low-moderate': 'text-accent/80',
  moderate: 'text-signal-warn',
  high: 'text-signal-error',
};

function ClearanceView() {
  // Distribution over the STORED headline state, which is a claim-architecture
  // judgement rather than a search result. Counted from the catalogue so the
  // number cannot drift from what the molecule pages show.
  const distribution = useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of PRODUCTS) {
      counts.set(product.clearanceState, (counts.get(product.clearanceState) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([id, count]) => ({ state: CLEARANCE_STATES_BY_ID[id], count }))
      .filter((row) => row.state)
      .sort((a, b) => b.count - a.count);
  }, []);

  const cells = PRODUCTS.length * JURISDICTIONS.length;
  const authored = CLEARANCE_FINDINGS.length;

  return (
    <>
      <Callout kind="warn" title="Nothing here is a freedom-to-operate opinion">
        <p className="text-ink">{HEADLINE_SCOPE_NOTE}</p>
      </Callout>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-5">
        <Stat label="Molecules" value={String(PRODUCTS.length)} sub="each carrying one headline state" />
        <Stat label="Jurisdictions" value={String(JURISDICTIONS.length)} sub="offices the matrix has rows for" />
        <Stat
          label="Cells authored"
          value={`${authored}`}
          sub={`of ${cells.toLocaleString()} — every other cell reads 'not assessed'`}
        />
        <Stat
          label="Coverage"
          value={`${((authored / cells) * 100).toFixed(2)}%`}
          sub="of the matrix has been looked at by a person"
        />
      </div>

      <section aria-labelledby="clearance-dist">
        <SectionTitle
          right={<span className="font-num text-caption text-ink-soft">{PRODUCTS.length} molecules</span>}
        >
          <span id="clearance-dist">Headline state across the catalogue</span>
        </SectionTitle>
        <Card className="px-4 py-1">
          <ul>
            {distribution.map(({ state, count }) => (
              <li key={state.id} className="py-2.5 border-b border-line/70 last:border-0">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <span className="font-num text-body text-ink">{state.label}</span>
                  <span className={cx('chip text-[11px] py-0', RISK_TONE[state.risk] ?? 'text-ink-soft')}>
                    {state.risk} risk
                  </span>
                  <a
                    href={href(`/dominion/molecules?clearance=${state.id}`)}
                    className="ml-auto font-num text-body text-ink hover:text-accent shrink-0"
                  >
                    {count}
                  </a>
                </div>
                <div className="text-body text-ink-soft mt-0.5">{state.action}</div>
                <div
                  className="mt-1.5 h-1.5 rounded-full bg-accent/25"
                  style={{ width: `${(count / PRODUCTS.length) * 100}%` }}
                  role="img"
                  aria-label={`${count} of ${PRODUCTS.length} molecules`}
                />
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <div className="mt-5">
        <Callout kind="info" title="What an empty jurisdiction cell means">
          <p className="text-ink">{CLEARANCE_MODEL_NOTE}</p>
        </Callout>
      </div>

    </>
  );
}

export default function Dominion() {
  const route = useRoute();
  const tabs: OwnerTab[] = useMemo(
    () => [
      { label: 'Molecules', to: '/dominion/molecules', badge: PRODUCTS.length },
      { label: 'Clearance', to: '/dominion/clearance', badge: CLEARANCE_FINDINGS.length },
    ],
    [],
  );
  const active = activeTab(route.path, tabs);
  const onClearance = active === '/dominion/clearance';

  return (
    <>
      <PageHeader
        eyebrow="What is fenced, what is open"
        title="Dominion"
        subtitle="What could be made, and who already owns it. Dominion holds the molecule catalogue and the clearance work — research leads about claim architecture, never legal opinions."
      />

      <OwnerTabs tabs={tabs} />

      {onClearance ? <ClearanceView /> : <Molecules embedded />}

      <SubsystemShelf owner="Dominion" />

      <div className="mt-5">
        <ComponentTag
          component="Dominion"
          action={
            onClearance
              ? `${CLEARANCE_FINDINGS.length} findings authored`
              : `${PRODUCTS.length} molecules`
          }
        />
      </div>
    </>
  );
}
