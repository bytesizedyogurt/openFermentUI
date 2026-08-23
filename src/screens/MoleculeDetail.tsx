// Molecule detail (OF-BLD-005 §6) — one page per product, holding the whole
// answer to "could we make this, and would we be allowed to".
//
// Five bands: what it is, whether it is clear, how it would be made, how it
// would ship and sell, and what work is already attached to it. Clearance is
// the second band rather than a footnote, because a molecule you cannot ship
// is not a candidate however good its process looks.
//
// Everything on this page is modeled. The gold tick belongs to evidence, and
// there is no evidence here — the page wears the dashed amber demo tick and
// the value figures wear the industry-estimate tick, both from the existing
// provenance system.
import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  Boxes,
  FlaskConical,
  GitBranch,
  Package,
  Scale as ScaleIcon,
  Sparkles,
  Tag,
  Thermometer,
} from 'lucide-react';
import { useStore, PROVENANCE_LABEL } from '@/store';
import { href, navigate } from '@/router';
import { PRODUCT_CATEGORY_LABEL } from '@/data/products';
import {
  PATHWAYS_BY_ID,
  REGULATORY_BURDEN_RANK,
  REGULATORY_PATHWAYS_BY_ID,
  SCALES_BY_ID,
  STORAGE_FORMATS_BY_ID,
} from '@/data/vocabulary';
import { STRAINS_BY_ID } from '@/data/strains';
import { RUNBOOK_STATUS_LABEL } from '@/data/runbooks';
import { territorialityNote } from '@/engine/clearance';
import {
  ClearanceChip,
  ClearanceStrip,
  CounselCallout,
  JurisdictionMatrix,
} from '@/components/Clearance';
import { ProcessTrain } from '@/components/ProcessTrain';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

function StorageRow({ id, warmest }: { id: string; warmest: boolean }) {
  const f = STORAGE_FORMATS_BY_ID[id];
  if (!f) return null;
  const ambient = f.tempC >= 25;
  return (
    <li className="py-2 border-b border-line/70 last:border-0">
      <div className="flex items-baseline justify-between gap-3">
        <span className={cx('font-medium', ambient && 'text-accent')}>{f.label}</span>
        <span className="font-num text-caption text-ink-soft shrink-0">{f.tempC} °C</span>
      </div>
      <div className="text-caption text-ink-soft mt-0.5">
        {f.logistics} · shelf life {f.shelfLife} · {f.cost} cost
      </div>
      {f.note && <div className="text-caption text-ink-soft mt-0.5">{f.note}</div>}
      {warmest && ambient && (
        <div className="text-caption text-accent mt-0.5">
          The cold chain is optional for this molecule. That is a logistics decision, not a
          scientific one, and it is usually worth more than a titre improvement.
        </div>
      )}
    </li>
  );
}

export default function MoleculeDetail({ productId }: { productId: string }) {
  const products = useStore((s) => s.products);
  const runbooks = useStore((s) => s.runbooks);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    setReady(false);
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, [productId]);

  const product = products.find((p) => p.id === productId);

  const linkedRunbooks = useMemo(
    () => runbooks.filter((r) => r.productId === productId),
    [runbooks, productId],
  );

  const siblings = useMemo(
    () =>
      product
        ? products.filter((p) => p.id !== product.id && p.processCode === product.processCode)
        : [],
    [products, product],
  );

  if (!product) {
    return (
      <>
        <PageHeader
          eyebrow="Molecules"
          title="Molecule not found"
          subtitle="Session state resets on refresh, so a deep link from an earlier session can point at nothing."
        />
        <Card>
          <EmptyState
            icon={<Boxes size={22} aria-hidden />}
            title={`No molecule with the id “${productId}”`}
            body="The molecule index lists every product this catalogue covers. Open it to pick one."
            action={<LinkButton to="/molecules">Back to molecules</LinkButton>}
          />
        </Card>
      </>
    );
  }

  if (!ready) {
    return (
      <>
        <PageHeader eyebrow="Molecules" title={product.name} />
        <Card className="p-4 mb-4">
          <Skeleton rows={3} />
        </Card>
        <Card>
          <Skeleton rows={8} />
        </Card>
      </>
    );
  }

  const strain = STRAINS_BY_ID[product.defaultStrainId];
  const scale = SCALES_BY_ID[product.scaleId];
  const formats = product.storageIds.map((s) => STORAGE_FORMATS_BY_ID[s]).filter(Boolean);
  const warmestId = [...formats].sort((a, b) => b.tempC - a.tempC)[0]?.id;
  const territoriality = territorialityNote(product);
  const heaviestRoute = [...product.regulatoryIds]
    .map((r) => REGULATORY_PATHWAYS_BY_ID[r])
    .filter(Boolean)
    .sort((a, b) => (REGULATORY_BURDEN_RANK[b.burden] ?? 0) - (REGULATORY_BURDEN_RANK[a.burden] ?? 0))[0];

  return (
    <>
      <PageHeader
        eyebrow={`Molecules · ${PRODUCT_CATEGORY_LABEL[product.category]}`}
        title={product.name}
        subtitle={
          product.aliases.length > 0 ? `Also known as ${product.aliases.join(', ')}.` : undefined
        }
        actions={
          <>
            <LinkButton to={`/molecules?category=${product.category}`}>
              <Tag size={14} /> Same category
            </LinkButton>
            <LinkButton to="/molecules">
              <ArrowRight size={14} className="rotate-180" /> All molecules
            </LinkButton>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <ClearanceChip state={product.clearanceState} />
        <ProvenanceBadge p={product.provenance} />
        <span className="chip text-ink-soft font-num" title="Process family — the downstream archetype">
          {product.processCode}
        </span>
        <span className="chip text-ink-soft font-num">{product.id}</span>
        {product.tags.map((t) => (
          <span key={t} className="chip text-ink-soft">
            {t}
          </span>
        ))}
      </div>

      {product.note && (
        <Card className="p-4 mb-5">
          <Tick p="demo" title="Modeled framing — not a measurement and not a legal reading">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
              Why this molecule is interesting
            </div>
            <p className="font-serif text-reading">{product.note}</p>
          </Tick>
        </Card>
      )}

      {/* ── BAND 1 — clearance ─────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-clearance">
        <SectionTitle
          right={
            <Explain label="How clearance is decided here">
              openFerment classifies what a claim <em>recites</em> — a sequence, a process, an
              application — because that is what decides whether designing around it is possible.
              A claim reciting a specific sequence can be enumerated around; one reciting a
              functional class usually cannot, however much molecular diversity you throw at it.
              The stored state is the worst case across jurisdictions, and the matrix below
              spreads it back out. None of it is a search of national registers.
            </Explain>
          }
        >
          <span id="band-clearance">Clearance</span>
        </SectionTitle>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4">
          <Card className="p-4">
            <ClearanceStrip state={product.clearanceState} />
            {territoriality && (
              <p className="text-body text-ink-soft mt-3 pt-3 border-t border-line">
                {territoriality}
              </p>
            )}
            {product.clearanceState === 'blocked' && (
              <div className="mt-3 pt-3 border-t border-line">
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                  There is a way through
                </div>
                <p className="text-body text-ink-soft mb-2">
                  Blocking claims stop the industrial route, not the question. If the claims recite
                  sequence or structure, a research runbook can enumerate the genus around the
                  fence and rank what falls outside it. If they recite a functional class, it will
                  tell you that instead — and save you the compute.
                </p>
                <Button
                  variant="primary"
                  onClick={() => navigate(`/runbooks?handoff=${product.id}`)}
                >
                  <Sparkles size={14} /> Enumerate around this fence
                </Button>
              </div>
            )}
            {product.clearanceState === 'unknown' && (
              <div className="mt-3 pt-3 border-t border-line">
                <p className="text-body text-ink-soft mb-2">
                  Nothing has been assessed for this molecule. Everything below describes a process
                  that may or may not be yours to run.
                </p>
                <Button onClick={() => navigate(`/runbooks?handoff=${product.id}`)}>
                  <ScaleIcon size={14} /> Run a clearance sweep
                </Button>
              </div>
            )}
          </Card>

          <Card className="p-4">
            <JurisdictionMatrix product={product} />
          </Card>
        </div>

        <div className="mt-3">
          <CounselCallout scope={product.name} />
        </div>
      </section>

      {/* ── BAND 2 — how it would be made ──────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-process">
        <SectionTitle>
          <span id="band-process">Process train</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Fermenter to finished vial, in the order the product declares. Every step is a named
          operation with a defined role; none of them is simulated. Click a step to see what the
          platform does and does not know about it.
        </p>
        <Card className="p-4">
          <ProcessTrain
            unitOperationIds={product.unitOperationIds}
            strainId={product.defaultStrainId}
            storageIds={product.storageIds}
            scaleId={product.scaleId}
            processCode={product.processCode}
          />
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <FlaskConical size={13} aria-hidden /> Host
            </div>
            {strain ? (
              <>
                <a
                  href={href(`/organisms/${strain.id}`)}
                  className="font-serif text-section-title font-semibold italic hover:text-accent hover:underline"
                >
                  {strain.binomial}
                </a>
                <div className="font-num text-body mt-0.5">{strain.designation}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {strain.badges.map((b) => (
                    <span key={b} className="chip text-ink-soft">
                      {b}
                    </span>
                  ))}
                </div>
                <p className="text-body text-ink-soft mt-2">{strain.description}</p>
                <div className="mt-2">
                  <a
                    href={href(`/molecules?host=${strain.id}`)}
                    className="text-caption text-accent hover:underline"
                  >
                    Every molecule defaulting to this host
                  </a>
                </div>
              </>
            ) : (
              <div className="text-body text-signal-warn">
                Host id “{product.defaultStrainId}” does not resolve to a seeded strain.
              </div>
            )}
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <ScaleIcon size={13} aria-hidden /> Scale
            </div>
            {scale ? (
              <>
                <div className="font-num text-display leading-tight">{scale.volumeL}</div>
                <div className="text-caption text-ink-soft">litres · {scale.label}</div>
                <p className="text-body text-ink-soft mt-2">{scale.role}</p>
              </>
            ) : (
              <div className="text-body text-ink-soft">No scale band assigned.</div>
            )}
            <Tick p="industry-estimate" className="mt-3 pt-3 border-t border-line">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Value density
              </div>
              <div className="text-section-title font-medium mt-0.5">{product.valueDensityBand}</div>
              <div className="text-caption text-ink-soft mt-0.5">
                {PROVENANCE_LABEL[product.economicsProvenance]} — banded rather than priced, and
                held out of every aggregate in the platform.
              </div>
            </Tick>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <Sparkles size={13} aria-hidden /> Pathway
            </div>
            {product.pathwayIds.length === 0 ? (
              <p className="text-body text-ink-soft">
                No metabolic pathway is declared. For a recombinant protein there is nothing to
                declare — expression is the pathway, and the interesting flux question is folding
                capacity rather than carbon routing.
              </p>
            ) : (
              <ul className="space-y-2.5">
                {product.pathwayIds.map((id) => {
                  const pw = PATHWAYS_BY_ID[id];
                  if (!pw) return null;
                  return (
                    <li key={id}>
                      <div className="font-medium">{pw.label}</div>
                      <div className="font-num text-caption text-ink-soft mt-0.5">{pw.fluxNode}</div>
                      {pw.note && <div className="text-caption text-ink-soft mt-0.5">{pw.note}</div>}
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </div>
      </section>

      {/* ── BAND 3 — how it ships and sells ────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-ship">
        <SectionTitle>
          <span id="band-ship">Storage and route to market</span>
        </SectionTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-1">
              <Thermometer size={13} aria-hidden /> Storage formats
              <span className="font-num">({formats.length})</span>
            </div>
            {formats.length === 0 ? (
              <EmptyState
                title="No storage format declared"
                body="Nothing here says how this molecule would be held or shipped, so the cold-chain question is open."
              />
            ) : (
              <ul>
                {product.storageIds.map((id) => (
                  <StorageRow key={id} id={id} warmest={id === warmestId} />
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-1">
              <Package size={13} aria-hidden /> Regulatory routes
              <span className="font-num">({product.regulatoryIds.length})</span>
            </div>
            {product.regulatoryIds.length === 0 ? (
              <EmptyState
                title="No regulatory route declared"
                body="Nothing here says what approval this product would need, which usually means the question has not been asked rather than that the answer is none."
              />
            ) : (
              <>
                <ul>
                  {product.regulatoryIds.map((id) => {
                    const r = REGULATORY_PATHWAYS_BY_ID[id];
                    if (!r) return null;
                    return (
                      <li key={id} className="py-2 border-b border-line/70 last:border-0">
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="font-medium">{r.label}</span>
                          <span className="chip text-ink-soft text-[11px] py-0 shrink-0">
                            {r.burden} burden
                          </span>
                        </div>
                        {r.note && <div className="text-caption text-ink-soft mt-0.5">{r.note}</div>}
                      </li>
                    );
                  })}
                </ul>
                {heaviestRoute && (
                  <p className="text-caption text-ink-soft mt-2">
                    The binding constraint is {heaviestRoute.label.toLowerCase()} at{' '}
                    {heaviestRoute.burden} burden. Regulatory burden is a quality-systems problem
                    and a calendar, not a fermentation problem — it rarely changes what you build,
                    and it usually changes when you can sell it.
                  </p>
                )}
              </>
            )}
          </Card>
        </div>
      </section>

      {/* ── BAND 4 — attached work ─────────────────────────────────────── */}
      <section className="mb-4" aria-labelledby="band-work">
        <SectionTitle>
          <span id="band-work">Runbooks and neighbours</span>
        </SectionTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <GitBranch size={13} aria-hidden /> Linked runbooks
              <span className="font-num">({linkedRunbooks.length})</span>
            </div>
            {linkedRunbooks.length === 0 ? (
              <EmptyState
                title="No runbook for this molecule"
                body="Nothing has been synthesised against it yet. A runbook turns this page into a process you could build and defend, or into a prediction and the experiments that would test it."
                action={<LinkButton to="/runbooks">Open the runbook board</LinkButton>}
              />
            ) : (
              <ul className="space-y-2">
                {linkedRunbooks.map((r) => (
                  <li key={r.id}>
                    <a
                      href={href(`/runbooks/${r.id}`)}
                      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-medium leading-snug">{r.title}</span>
                        <span className="chip text-ink-soft text-[11px] py-0 shrink-0">
                          {r.kind}
                        </span>
                      </div>
                      <div className="text-caption text-ink-soft mt-1">
                        {RUNBOOK_STATUS_LABEL[r.status]} ·{' '}
                        <span className="font-num">{r.progressPct}%</span> ·{' '}
                        <span className="font-num">{r.stages.length}</span> stages
                      </div>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <Boxes size={13} aria-hidden /> Same process family
              <span className="font-num">({siblings.length})</span>
            </div>
            {siblings.length === 0 ? (
              <EmptyState
                title="Nothing else uses this train"
                body="This molecule is alone in its process family, which means its equipment earns its keep on one product or not at all."
              />
            ) : (
              <>
                <p className="text-caption text-ink-soft mb-2">
                  These share {product.processCode} — broadly the same equipment, so they amortise
                  the same capital. This is the question a facility answers before it buys
                  anything.
                </p>
                <div className="flex flex-wrap gap-1.5 max-h-[220px] overflow-y-auto">
                  {siblings.map((s) => (
                    <a
                      key={s.id}
                      href={href(`/molecules/${s.id}`)}
                      className="chip hover:border-accent/45 hover:bg-accent-wash"
                      title={`${s.name} — ${PRODUCT_CATEGORY_LABEL[s.category]}`}
                    >
                      {s.name}
                    </a>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>
      </section>

      <Callout kind="info" title="What this page is claiming">
        Nothing on this page was measured. The train, the host, the storage options and the value
        band describe a plausible way to make {product.name}, assembled from vocabulary rather than
        from experiments — {PROVENANCE_LABEL[product.provenance].toLowerCase()}. The corpus behind
        this platform covers one throughline in depth, and this molecule is not it.{' '}
        <a className="text-accent hover:underline" href={href('/organisms')}>
          The organism pages
        </a>{' '}
        say exactly how much evidence stands behind each host.
      </Callout>
    </>
  );
}
