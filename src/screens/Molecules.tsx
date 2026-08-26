// Molecule index (OF-BLD-005 §6) — 117 products in one table, faceted along
// every axis a facility actually decides on: what it is, who makes it, which
// downstream train it needs, how it ships, what it takes to sell it, and
// whether anyone else already owns it.
//
// Clearance is a column, not a mode. It sits next to the molecule wherever the
// molecule appears, because a catalogue you have to leave to find out whether
// you are allowed to build something is a catalogue that will get someone
// sued.
//
// Every row is modeled: the provenance tick is dashed amber on all 117, and
// the value-density band is an industry estimate that `aggregateExclusion()`
// already holds out of every statistic. Nothing here is evidence.
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Boxes, Package, Thermometer, X } from 'lucide-react';
import type { Product } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { PRODUCT_CATEGORY_LABEL } from '@/data/products';
import {
  CLEARANCE_STATES_BY_ID,
  REGULATORY_PATHWAYS_BY_ID,
  SCALES_BY_ID,
  STORAGE_FORMATS_BY_ID,
  UNIT_OPERATIONS_BY_ID,
  VALUE_DENSITY_RANK,
} from '@/data/vocabulary';
import { STRAINS_BY_ID } from '@/data/strains';
import { clearanceSeverity } from '@/engine/clearance';
import { DataTable, type Column, type FacetDef } from '@/components/DataTable';
import { ClearanceChip, CounselCallout } from '@/components/Clearance';
import { ProvenanceLegend } from '@/components/Provenance';
import { Card, Explain, PageHeader, Skeleton, cx } from '@/components/ui';
import { referenceFor } from '@/data/reference';
import { delayClass } from '@/sim/latency';

// ── scoping by query string ────────────────────────────────────────────

/**
 * Three scopes can arrive on the URL, so other screens can hand off into a
 * pre-narrowed catalogue: `?host=` from an organism page, `?clearance=` from
 * the palette's "show me what is blocked", `?category=` from anywhere.
 *
 * A scope is applied to `rows`, not to the facet state, and it renders as a
 * removable chip. Filtering a table without saying so is how a demo shows
 * someone the wrong number and never finds out.
 */
type ScopeKey = 'host' | 'clearance' | 'category';

const SCOPE_LABEL: Record<ScopeKey, string> = {
  host: 'Host',
  clearance: 'Clearance',
  category: 'Category',
};

function scopeValueLabel(key: ScopeKey, value: string): string {
  if (key === 'host') return STRAINS_BY_ID[value]?.designation ?? value;
  if (key === 'clearance') return CLEARANCE_STATES_BY_ID[value]?.label ?? value;
  return PRODUCT_CATEGORY_LABEL[value as keyof typeof PRODUCT_CATEGORY_LABEL] ?? value;
}

function matchesScope(p: Product, key: ScopeKey, value: string): boolean {
  if (key === 'host') return p.defaultStrainId === value;
  if (key === 'clearance') return p.clearanceState === value;
  return p.category === value;
}

// ── screen ─────────────────────────────────────────────────────────────

/**
 * The five limitation kinds, from `dominion.claims`.
 *
 * Collapsed behind a disclosure rather than laid out flat: the catalogue's job
 * is the hundred and seventeen rows below it, and a five-row legend permanently
 * open above them would be furniture. The trigger states the one sentence that
 * matters; the table is for the reader who stops.
 */
function LimitationKinds() {
  const content = referenceFor('dominion.claims');
  const kinds = content?.tables.find((t) => t.title === 'Limitation kinds');
  if (!kinds) return null;
  const enumerable = kinds.rows.filter((r) => r[2] === 'Yes').length;

  return (
    <div className="text-caption text-ink-soft inline-flex items-center gap-1.5">
      <span>
        Clearance states describe what a claim <span className="text-ink">recites</span>, not what
        a molecule is — {enumerable} of {kinds.rows.length} limitation kinds can be designed
        around by enumeration.
      </span>
      <Explain label="The five limitation kinds">
        <div className="text-body">
          <p className="mb-2 text-ink">{content?.blurb}</p>
          <table className="w-full border-collapse text-body">
            <thead>
              <tr className="border-b border-line">
                {kinds.cols.map((c) => (
                  <th key={c} className="text-caption font-medium text-ink-soft px-1.5 py-1 text-left">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {kinds.rows.map((r) => (
                <tr key={r[0]} className="border-b border-line/60 last:border-0 align-top">
                  <td className="font-num px-1.5 py-1 text-ink whitespace-nowrap">{r[0]}</td>
                  <td className="px-1.5 py-1 text-ink-soft italic">{r[1]}</td>
                  <td
                    className={cx(
                      'px-1.5 py-1 font-num whitespace-nowrap',
                      r[2] === 'Yes' ? 'text-accent' : 'text-ink-soft',
                    )}
                  >
                    {r[2]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {content?.note && <p className="mt-2 text-ink-soft">{content.note}</p>}
        </div>
      </Explain>
    </div>
  );
}

export default function Molecules({ embedded = false }: { embedded?: boolean } = {}) {
  const products = useStore((s) => s.products);
  const runbooks = useStore((s) => s.runbooks);
  const density = useStore((s) => s.ui.density);
  const route = useRoute();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const scopes = useMemo(() => {
    const out: { key: ScopeKey; value: string }[] = [];
    for (const key of ['host', 'clearance', 'category'] as ScopeKey[]) {
      const value = route.query.get(key);
      if (value) out.push({ key, value });
    }
    return out;
  }, [route.query]);

  const rows = useMemo(
    () => products.filter((p) => scopes.every((s) => matchesScope(p, s.key, s.value))),
    [products, scopes],
  );

  const runbookCount = useMemo(() => {
    const by = new Map<string, number>();
    for (const r of runbooks) {
      if (!r.productId) continue;
      by.set(r.productId, (by.get(r.productId) ?? 0) + 1);
    }
    return by;
  }, [runbooks]);

  const blocked = useMemo(
    () => products.filter((p) => p.clearanceState === 'blocked').length,
    [products],
  );
  const unassessed = useMemo(
    () => products.filter((p) => p.clearanceState === 'unknown').length,
    [products],
  );
  const ambient = useMemo(
    () => products.filter((p) => p.storageIds.some((s) => STORAGE_FORMATS_BY_ID[s]?.tempC === 25)).length,
    [products],
  );

  const columns: Column<Product>[] = [
    {
      key: 'name',
      header: 'Molecule',
      width: '240px',
      priority: 1,
      render: (p) => (
        <div className="min-w-0">
          <a
            href={href(`/dominion/molecules/${p.id}`)}
            className="text-accent hover:underline block truncate"
            onClick={(e) => e.stopPropagation()}
            title={p.name}
          >
            {p.name}
          </a>
          {p.aliases.length > 0 && (
            <div className="text-caption text-ink-soft truncate" title={p.aliases.join(', ')}>
              {p.aliases.join(' · ')}
            </div>
          )}
        </div>
      ),
      value: (p) => p.name,
    },
    {
      key: 'category',
      header: 'Category',
      width: '176px',
      priority: 1,
      render: (p) => <span className="block truncate">{PRODUCT_CATEGORY_LABEL[p.category]}</span>,
      value: (p) => PRODUCT_CATEGORY_LABEL[p.category],
    },
    {
      key: 'clearance',
      header: 'Clearance',
      width: '196px',
      priority: 1,
      render: (p) => <ClearanceChip state={p.clearanceState} compact />,
      // Sorted by severity, not alphabetically — "blocked" belongs at one end.
      value: (p) => clearanceSeverity(p.clearanceState),
    },
    {
      key: 'host',
      header: 'Default host',
      width: '186px',
      priority: 2,
      render: (p) => {
        const s = STRAINS_BY_ID[p.defaultStrainId];
        return s ? (
          <a
            href={href(`/fermos/organisms/${s.id}`)}
            className="hover:text-accent hover:underline block truncate"
            onClick={(e) => e.stopPropagation()}
            title={`${s.binomial} ${s.designation}`}
          >
            <span className="italic">{s.binomial}</span>
          </a>
        ) : (
          <span className="text-signal-warn">{p.defaultStrainId}</span>
        );
      },
      value: (p) => STRAINS_BY_ID[p.defaultStrainId]?.binomial ?? p.defaultStrainId,
    },
    {
      key: 'process',
      header: 'Process',
      width: '78px',
      priority: 2,
      render: (p) => (
        <span className="font-num" title={`Process family ${p.processCode}`}>
          {p.processCode}
        </span>
      ),
      value: (p) => Number(p.processCode.slice(1)),
    },
    {
      key: 'steps',
      header: 'Train',
      headerUnit: 'steps',
      width: '72px',
      numeric: true,
      priority: 3,
      render: (p) => <span className="font-num">{p.unitOperationIds.length}</span>,
      value: (p) => p.unitOperationIds.length,
    },
    {
      key: 'value',
      header: 'Value density',
      width: '128px',
      priority: 2,
      render: (p) => (
        <span
          className="chip text-ink-soft text-[11px] py-0"
          title="Industry estimate — banded, not priced, and excluded from every aggregate"
        >
          {p.valueDensityBand}
        </span>
      ),
      value: (p) => VALUE_DENSITY_RANK[p.valueDensityBand] ?? -1,
    },
    {
      key: 'storage',
      header: 'Ships as',
      width: '182px',
      priority: 3,
      render: (p) => {
        const best = [...p.storageIds]
          .map((s) => STORAGE_FORMATS_BY_ID[s])
          .filter(Boolean)
          .sort((a, b) => b.tempC - a.tempC)[0];
        if (!best) return <span className="text-ink-soft">—</span>;
        const ambientFormat = best.tempC >= 25;
        return (
          <span
            className={cx('inline-flex items-center gap-1', ambientFormat ? 'text-accent' : 'text-ink-soft')}
            title={`${best.label} — ${best.logistics}. Warmest of ${p.storageIds.length} format${p.storageIds.length === 1 ? '' : 's'}.`}
          >
            <Thermometer size={12} aria-hidden />
            {best.label}
          </span>
        );
      },
      value: (p) =>
        Math.max(...p.storageIds.map((s) => STORAGE_FORMATS_BY_ID[s]?.tempC ?? -100), -100),
    },
    {
      key: 'regulatory',
      header: 'Regulatory',
      width: '150px',
      defaultHidden: true,
      render: (p) => (
        <span className="block truncate">
          {p.regulatoryIds.map((r) => REGULATORY_PATHWAYS_BY_ID[r]?.label ?? r).join(', ')}
        </span>
      ),
      value: (p) => p.regulatoryIds.map((r) => REGULATORY_PATHWAYS_BY_ID[r]?.label ?? r).join(', '),
    },
    {
      key: 'scale',
      header: 'Scale',
      width: '132px',
      defaultHidden: true,
      render: (p) => <span>{SCALES_BY_ID[p.scaleId]?.label ?? p.scaleId}</span>,
      value: (p) => SCALES_BY_ID[p.scaleId]?.label ?? p.scaleId,
    },
    {
      key: 'runbooks',
      header: 'Runbooks',
      width: '86px',
      numeric: true,
      priority: 3,
      render: (p) => {
        const n = runbookCount.get(p.id) ?? 0;
        return n === 0 ? (
          <span className="text-ink-soft font-num">—</span>
        ) : (
          <span className="font-num text-accent">{n}</span>
        );
      },
      value: (p) => runbookCount.get(p.id) ?? 0,
    },
  ];

  const facets: FacetDef<Product>[] = [
    {
      key: 'category',
      label: 'Category',
      valuesOf: (p) => [p.category],
      labelOf: (v) => PRODUCT_CATEGORY_LABEL[v as keyof typeof PRODUCT_CATEGORY_LABEL] ?? v,
    },
    {
      key: 'clearance',
      label: 'Clearance',
      valuesOf: (p) => [p.clearanceState],
      labelOf: (v) => CLEARANCE_STATES_BY_ID[v]?.label ?? v,
    },
    {
      key: 'host',
      label: 'Default host',
      valuesOf: (p) => [p.defaultStrainId],
      labelOf: (v) => STRAINS_BY_ID[v]?.binomial ?? v,
    },
    {
      key: 'process',
      label: 'Process family',
      valuesOf: (p) => [p.processCode],
    },
    {
      key: 'storage',
      label: 'Storage format',
      valuesOf: (p) => p.storageIds,
      labelOf: (v) => STORAGE_FORMATS_BY_ID[v]?.label ?? v,
    },
    {
      key: 'regulatory',
      label: 'Regulatory route',
      valuesOf: (p) => p.regulatoryIds,
      labelOf: (v) => REGULATORY_PATHWAYS_BY_ID[v]?.label ?? v,
    },
    {
      key: 'value',
      label: 'Value density',
      valuesOf: (p) => [p.valueDensityBand],
    },
    {
      key: 'unitop',
      label: 'Unit operation',
      valuesOf: (p) => p.unitOperationIds,
      labelOf: (v) => UNIT_OPERATIONS_BY_ID[v]?.label ?? v,
    },
  ];

  const subtitle =
    'Every molecule this platform can describe, with the host it would be made in, the downstream train it needs, how it ships, and who already owns it. Modeled throughout — this is a map of the option space, not a set of measurements.';

  if (!ready) {
    return (
      <>
        {!embedded && <PageHeader eyebrow="Module 5 · Molecules" title="Molecules" subtitle={subtitle} />}
        <Card>
          <Skeleton rows={12} />
        </Card>
      </>
    );
  }

  return (
    <>
      {/* Suppressed when Dominion mounts this as its default view. */}
      <PageHeader
        eyebrow={embedded ? undefined : 'Module 5 · Molecules'}
        title={embedded ? null : 'Molecules'}
        subtitle={embedded ? undefined : subtitle}
        actions={
          <a href={href('/runbooks')} className="btn">
            Runbooks <ArrowRight size={14} />
          </a>
        }
      />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-3 text-caption text-ink-soft">
        <span className="inline-flex items-center gap-1.5">
          <Boxes size={13} aria-hidden />
          <span className="font-num text-ink">{products.length}</span> molecules
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Package size={13} aria-hidden />
          <span className="font-num text-ink">
            {new Set(products.map((p) => p.processCode)).size}
          </span>{' '}
          process families
        </span>
        <span>
          <span className="font-num text-signal-error">{blocked}</span> blocked by live claims
        </span>
        <span>
          <span className="font-num text-ink">{unassessed}</span> not yet assessed
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Thermometer size={13} aria-hidden />
          <span className="font-num text-accent">{ambient}</span> ship ambient
          <Explain label="Why ambient shipping is the interesting column">
            A landlocked facility pays for the cold chain twice: once in equipment and once in
            every shipment that has to move on dry ice. A molecule that survives lyophilisation
            and travels as ordinary air freight has different economics from an identical
            molecule that does not, and the difference is larger than most titre gains. The
            count is of products with at least one 25&nbsp;°C format among their options.
          </Explain>
        </span>
      </div>

      {scopes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-caption text-ink-soft">Scoped to</span>
          {scopes.map((s) => (
            <button
              key={s.key}
              className="chip chip-active"
              onClick={() => {
                const next = scopes.filter((x) => x.key !== s.key);
                const qs = next.map((x) => `${x.key}=${encodeURIComponent(x.value)}`).join('&');
                navigate(qs ? `/dominion/molecules?${qs}` : '/dominion/molecules');
              }}
              title={`Remove the ${SCOPE_LABEL[s.key].toLowerCase()} scope`}
            >
              {SCOPE_LABEL[s.key]}: {scopeValueLabel(s.key, s.value)}
              <X size={11} />
            </button>
          ))}
          <span className="text-caption text-ink-soft font-num">
            {rows.length} of {products.length}
          </span>
        </div>
      )}

      <div className="mb-3">
        <CounselCallout scope="a catalogue of 117 molecules" />
      </div>

      <div className="mb-3">
        <ProvenanceLegend />
      </div>

      {/* OF-BLD-010 §5 — the clearance vocabulary, beside the catalogue it
          describes. Every molecule below carries a clearance state, and those
          states are judgements about what a claim RECITES: a claim naming a
          sequence can be designed around by enumeration, a claim naming a
          function cannot. That distinction decides whether the column means
          anything, and a reader should not have to go to Dominion's Claim
          Workbench — which is not built — to find it.

          Rows come from reference.ts so there is one source; nothing here is a
          patent status, and none of it is about any particular molecule. */}
      <LimitationKinds />

      <DataTable<Product>
        rows={rows}
        columns={columns}
        rowKey={(p) => p.id}
        tickOf={(p) => p.provenance}
        dense={density === 'dense'}
        onOpen={(p) => navigate(`/dominion/molecules/${p.id}`)}
        facets={facets}
        searchOf={(p) =>
          `${p.name} ${p.aliases.join(' ')} ${PRODUCT_CATEGORY_LABEL[p.category]} ${p.tags.join(' ')} ${p.processCode} ${p.note ?? ''}`
        }
        exportName="openferment-molecules"
        exportNote="Every row is modeled and every value-density band is an industry estimate. The CSV carries the provenance disclosure header; nothing in it is evidence."
        emptyTitle="No molecules match"
        emptyBody="Nothing in the catalogue matches the current filters. Clearing the narrowing facet brings the rest back."
      />

      <p className="text-caption text-ink-soft mt-3 max-w-3xl">
        Facets with shallow depth are labelled black boxes, not failures. A unit operation appears
        in this list because a product declares it, which says the step is in the train — not that
        the platform can simulate it. Open a molecule to see which parts of its process are modeled
        and which are just named.
      </p>
    </>
  );
}
