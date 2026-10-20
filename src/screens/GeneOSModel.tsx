// geneOS → Model (OF-BLD-014 §6.4): the ceiling beside what was reported.
//
// Pick a product, a sugar and a model. The service computes, for every model
// on the shelf that names a route to the product, the most of it the network
// can make from the sugar (flux balance analysis, kept as an artifact), and
// the view draws each as a dotted rule beside every reported yield of that
// product in the store: curated, verified, and the extractor's undecided
// candidates as hollow marks. A point above a rule is ringed and listed for a
// reviewer to check its basis. Below sit the chosen model's production
// envelope and its sugar-mix line. A model the service cannot compute is
// named in words and the others still draw; with the service down this says
// so; nothing stands in for a result (E.2).
//
// PROGRAMS (OF-BLD-016 §2.2). The product chooser, the models (the chooser,
// the ceilings drawn and the shelf list) and the reported yields pass the
// program selector: a model shows when its host and one of its products do,
// and with archived programs hidden the view opens on the first product that
// shows, not on PHB. A URL naming a product, or a model whose product it is
// (a strain page's card links so), opens that product under ArchivedBanner
// with its own program's models and records (`useProgramScope`). When nothing
// on the shelf shows, the view says what is hidden and where the switch is.
// With the switch on, all as before.
import { useEffect, useMemo, useState } from 'react';
import { Calculator } from 'lucide-react';
import type { ExtractionRecord, GeneosModelInfo, GeneosResult } from '@/data/types';
import { PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { useProgramFilter, useStore, type ProgramEntityKind, useProgramScope } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { Callout, EmptyState, LinkButton } from '@/components/ui';
import { ArchivedBanner } from '@/components/ArchivedBanner';
import { HiddenByArchive, archivedProgramsOf } from '@/components/HiddenByArchive';
import { EvidenceCard } from '@/components/EvidenceCard';
import { CeilingGap, Frontier, MixLine, stripPoints, type Ceiling } from '@/components/figures';
import {
  GeneosDown,
  SUBSTRATES,
  productWords,
  yieldFieldKnown,
  yieldsOnSugar,
  geneosCeiling,
  geneosFrontier,
  geneosMix,
  geneosModels,
  type FrontierPointOut,
  type MixPointOut,
} from '@/lib/geneos';

const UNIT = 'g g⁻¹';

/** The one line the geneOS callout says, repeated where a ceiling is drawn. */
export const NOT_A_VESSEL = 'Nothing on this screen predicts what a vessel will produce: a ceiling has no time axis and no vessel.';

interface Loaded {
  ceilings: GeneosResult[];
  /** The models whose ceiling the service refused or could not compute, in words. */
  failed: string[];
  frontier: GeneosResult | null;
  mix: GeneosResult | null;
}

/** A refusal's words (GeneosRefused carries the service's), or the error's. */
const said = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** Every product the shelf names a route to, in the shelf's order. */
const productsOf = (shelf: GeneosModelInfo[]) => [...new Set(shelf.flatMap((m) => m.products))];

export default function GeneOSModel() {
  const route = useRoute();
  const allRecords = useStore((s) => s.records);
  const runbooks = useStore((s) => s.runbooks);
  const depositions = useStore((s) => s.depositions);
  const shows = useProgramFilter();
  const [shelf, setShelf] = useState<GeneosModelInfo[] | null>(null);
  const [down, setDown] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [busy, setBusy] = useState(false);

  const substrate = route.query.get('substrate') ?? 'glucose';
  const modelId = route.query.get('model') ?? '';
  // A link to one model opens on that model's own product, shown or archived.
  const named = route.query.get('product') ?? shelf?.find((m) => m.id === modelId)?.product ?? null;
  // With no product named, the view opens on PHB while it shows, else on the
  // first product on the shelf that does (OF-BLD-016 §2.2), else on none.
  const firstShown = productsOf(shelf ?? []).find((p) => shows('product', p)) ?? '';
  const product = named ?? (shows('product', 'phb') ? 'phb' : firstShown);
  const inView = useProgramScope(named ? { kind: 'product', id: named } : null);
  const records = useMemo(() => allRecords.filter((r) => inView('record', r.id)), [allRecords, inView]);
  const words = productWords(product);
  const set = (patch: Record<string, string>) => {
    const q = new URLSearchParams(route.query);
    for (const [k, v] of Object.entries(patch)) q.set(k, v);
    navigate(`/geneos/model?${q.toString()}`, { replace: true });
  };

  useEffect(() => {
    const ctrl = new AbortController();
    geneosModels(ctrl.signal).then(setShelf, (e: unknown) => {
      if (!ctrl.signal.aborted) setDown(e instanceof GeneosDown ? `${e.message} ${e.remedy}` : String(e));
    });
    return () => ctrl.abort();
  }, []);

  // A model shows when its host does (a model with none is general) and one of its products does.
  const shownShelf = useMemo(
    () =>
      (shelf ?? []).filter(
        (m) => (!m.host || inView('strain', m.host)) && m.products.some((p) => inView('product', p)),
      ),
    [shelf, inView],
  );
  const products = useMemo(() => productsOf(shelf ?? []).filter((p) => inView('product', p)), [shelf, inView]);
  // Which models' hosts show, as a key that changes only when one does, so a
  // candidate arriving in the store does not ask for every ceiling again.
  const hostsShown = (shelf ?? []).map((m) => (!m.host || inView('strain', m.host) ? '1' : '0')).join('');
  const forProduct = useMemo(
    () => (shelf ?? []).filter((m, i) => m.products.includes(product) && hostsShown[i] === '1'),
    [shelf, product, hostsShown],
  );
  const usable = useMemo(() => forProduct.filter((m) => !m.unavailable), [forProduct]);
  const chosen = usable.find((m) => m.id === modelId) ?? usable[0] ?? null;

  useEffect(() => {
    if (!shelf) return;
    // The last sugar's or product's answers never stand under these titles
    // (§6.R), even when no model of this product can be loaded here.
    setRefused(null);
    setLoaded(null);
    if (!chosen) {
      setBusy(false);
      return;
    }
    const ctrl = new AbortController();
    setBusy(true);
    const other = substrate === 'xylose' ? 'glucose' : 'xylose';
    // Settled one by one: a model the service cannot compute is named, and
    // the others still draw.
    Promise.all([
      Promise.allSettled(usable.map((m) => geneosCeiling(m.id, substrate, product, ctrl.signal))),
      Promise.allSettled([
        geneosFrontier(chosen.id, substrate, product, ctrl.signal),
        geneosMix(chosen.id, substrate === 'xylose' ? 'glucose' : substrate, substrate === 'xylose' ? 'xylose' : other, product, ctrl.signal),
      ]),
    ])
      .then(([ceilings, [frontier, mix]]) => {
        if (ctrl.signal.aborted) return;
        const gone = [...ceilings, frontier, mix].find((r) => r.status === 'rejected' && r.reason instanceof GeneosDown);
        if (gone && gone.status === 'rejected') {
          setDown(`${gone.reason.message} ${(gone.reason as GeneosDown).remedy}`);
          return;
        }
        setLoaded({
          ceilings: ceilings.flatMap((r) => (r.status === 'fulfilled' ? [r.value] : [])),
          failed: ceilings.flatMap((r, i) => (r.status === 'rejected' ? [`${usable[i].id}: ${said(r.reason)}`] : [])),
          frontier: frontier.status === 'fulfilled' ? frontier.value : null,
          mix: mix.status === 'fulfilled' ? mix.value : null,
        });
        const why = [frontier, mix].flatMap((r) => (r.status === 'rejected' ? [said(r.reason)] : []));
        if (why.length > 0) setRefused(why.join(' '));
      })
      .finally(() => !ctrl.signal.aborted && setBusy(false));
    return () => ctrl.abort();
  }, [shelf, chosen?.id, substrate, product, usable]);

  // Only the yields of this product measured on this sugar are held against its ceilings.
  const { on: yields, elsewhere } = useMemo(
    () => yieldsOnSugar(records as ExtractionRecord[], substrate, product),
    [records, substrate, product],
  );
  const known = yieldFieldKnown(product);
  const ceilings: Ceiling[] = (loaded?.ceilings ?? [])
    .filter((c) => c.evidence)
    .map((c) => ({
      value: Number(c.evidence!.value),
      model: `${c.modelId} ceiling`,
      basis: c.evidence!.basis,
      provenance: c.evidence!.provenance,
    }));
  const findings = [
    ...(loaded?.ceilings ?? []).filter((c) => c.finding).map((c) => `${c.modelId}: ${c.finding}`),
    ...(loaded?.failed ?? []),
    ...forProduct.filter((m) => m.unavailable).map((m) => `${m.id}: ${m.unavailable}`),
  ];
  const flagged = stripPoints({ title: '', records: yields, unit: UNIT, quantity: words.quantity, groupBy: 'organism', rules: ceilings.map((c) => ({ value: c.value, label: c.model })), flagAbove: true }).points.filter((p) => p.above);

  if (down) {
    return <EmptyState icon={<Calculator size={28} />} title="The Model view needs the service" body={<>{down} The service runs flux balance analysis in its geneOS worker.</>} />;
  }

  if (shelf && product === '') {
    // Nothing on the shelf shows: every product it computes is archived.
    const hidden = productsOf(shelf);
    return (
      <div className="space-y-4" data-testid="geneos-model">
        <Callout kind="info" title="Stoichiometry, not a forecast">
          {NOT_A_VESSEL}
        </Callout>
        <EmptyState
          icon={<Calculator size={28} />}
          title={shelf.length === 0 ? 'No model on the shelf' : 'No model on the shelf computes for an active program'}
          body={
            shelf.length === 0 ? (
              'The service lists no reaction network on geneOS\'s shelf.'
            ) : (
              <HiddenByArchive
                subject={`The ${shelf.length === 1 ? 'one model' : `${shelf.length} models`} on the shelf, for ${hidden.map((p) => productWords(p).short).join(' and ')},`}
                plural={shelf.length !== 1}
                programs={archivedProgramsOf(
                  hidden.map((p) => ['product', p] as [ProgramEntityKind, string]),
                  { records: allRecords, runbooks, depositions },
                )}
              />
            )
          }
          action={shelf.length > 0 ? <LinkButton to={PROGRAMS_SETTINGS_PATH}>Open Settings → Programs</LinkButton> : undefined}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="geneos-model">
      <ArchivedBanner kind="product" id={product} />

      <Callout kind="info" title="Stoichiometry, not a forecast">
        {NOT_A_VESSEL}
      </Callout>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Product</span>
          <select className="input" aria-label="Product" value={product} onChange={(e) => set({ product: e.target.value })}>
            {(products.includes(product) || product === '' ? products : [product, ...products]).map((p) => (
              <option key={p} value={p}>
                {productWords(p).option}
              </option>
            ))}
          </select>
        </label>
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Sugar fed</span>
          <select className="input" aria-label="Sugar fed" value={substrate} onChange={(e) => set({ substrate: e.target.value })}>
            {SUBSTRATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Model, for the envelope and the mix</span>
          <select className="input" aria-label="Model" value={chosen?.id ?? ''} onChange={(e) => set({ model: e.target.value })}>
            {usable.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        {busy && <span className="text-caption text-ink-soft">Computing in the geneOS worker…</span>}
      </div>

      {refused && <Callout kind="warn">{refused}</Callout>}

      {shelf && (
        <CeilingGap
          title={`How far is each reported ${words.reported} from the most a network allows on ${substrate}?`}
          records={yields}
          unit={UNIT}
          quantity={words.quantity}
          ceilings={ceilings}
          csvName={product === 'phb' ? `ceiling-gap-${substrate}` : `ceiling-gap-${product}-${substrate}`}
        />
      )}

      {shelf && (
        <p className="text-caption text-ink-soft" data-testid="yields-elsewhere">
          {known
            ? `The ceilings are for ${words.short}; the records are ${words.reported}s the papers reported on ${substrate}, as written.`
            : `The ceilings are for ${words.short}; the ontology holds no ${words.reported} field yet, so no reported yield is drawn beside them.`}
          {elsewhere > 0 &&
            ` ${elsewhere} ${words.reported} record${elsewhere === 1 ? '' : 's'} on another feed, or with no feed stated, ${elsewhere === 1 ? 'is' : 'are'} not drawn here.`}
        </p>
      )}

      {flagged.length > 0 && (
        <section aria-label="Yields above a ceiling" className="space-y-1.5" data-testid="above-ceiling">
          <h3 className="font-medium text-reading">Reported above a ceiling: check the basis</h3>
          {flagged.map((p) => (
            <div key={p.record.id} className="rounded-card border border-signal-warn/45 bg-signal-warn/[0.06] p-2 text-body">
              <span className="font-num">{p.record.id}</span> ({p.group}) is {p.above}. A reported yield above a network's
              ceiling may rest on a different basis (another sugar counted, the {product === 'phb' ? 'dry weight' : 'product'} measured
              otherwise).{' '}
              <a className="text-accent hover:underline" href={href(`/guild?record=${p.record.id}`)}>
                Ask a reviewer to check its basis
              </a>
              .
            </div>
          ))}
        </section>
      )}

      {chosen && loaded?.frontier?.output && Array.isArray(loaded.frontier.output.points) && (
        <Frontier
          title={`How much ${words.short} can a growing cell make on ${substrate}, by ${chosen.id}?`}
          points={(loaded.frontier.output.points as FrontierPointOut[]).map((p) => ({ growth: p.growth, product: p.gPerG }))}
          growthUnit="h⁻¹"
          productUnit={UNIT}
          productLabel={words.quantity}
          model={chosen.name}
          basis={loaded.frontier.evidence?.basis}
          csvName={`frontier-${chosen.id}-${substrate}`}
        />
      )}

      {chosen && loaded?.mix?.output && Array.isArray(loaded.mix.output.points) && (
        <MixLine
          title={`How does the sugar mix of a hydrolysate bound the yield, by ${chosen.id}?`}
          points={(loaded.mix.output.points as MixPointOut[]).map((p) => ({ share: p.shareA, value: p.gPerG }))}
          a={loaded.mix.substrates[0]}
          b={loaded.mix.substrates[1]}
          unit={UNIT}
          quantity={words.quantity}
          model={chosen.name}
          csvName={`sugar-mix-${chosen.id}`}
          basis={loaded.mix.evidence?.basis}
        />
      )}

      {(findings.length > 0 || chosen) && (
        <section aria-label="What the models lack" data-testid="model-lacks">
          <h3 className="font-medium text-reading mb-1">What the models lack</h3>
          <ul className="space-y-0.5 text-body text-ink">
            {findings.map((f) => (
              <li key={f}>{f}</li>
            ))}
            {loaded?.frontier?.finding && <li>{`${chosen?.id}: ${loaded.frontier.finding}`}</li>}
            {loaded?.mix?.finding && <li>{`${chosen?.id}, for the mix: ${loaded.mix.finding}`}</li>}
            {chosen &&
              chosen.notes.map((n) => (
                <li key={n} className="text-ink-soft">
                  {chosen.id}: {n}
                </li>
              ))}
          </ul>
        </section>
      )}

      {shelf && !chosen && forProduct.length > 0 && (
        <Callout kind="warn">
          No model on the shelf with a route to {words.short} can be loaded here; each says why under What the models lack.
        </Callout>
      )}

      {shelf && (
        <section aria-label="The shelf">
          <h3 className="font-medium text-reading mb-1">The shelf</h3>
          <ul className="space-y-1 text-body">
            {shownShelf.map((m) => (
              <li key={m.id}>
                <span className="font-num">{m.id}</span> — {m.name}, {m.scope}. {m.route}. Source: {m.source}; {m.licence}.
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/**
 * On a strain page: for each model of this host on geneOS's shelf, its
 * ceiling for the model's own product on the sugar it takes up, and a link to
 * the Model view. A model the service cannot compute says so beside the
 * others. With the service down, or no model of this host, it draws nothing.
 */
export function HostCeilingCard({ strainId }: { strainId: string }) {
  const [allModels, setModels] = useState<GeneosModelInfo[]>([]);
  const [results, setResults] = useState<Record<string, GeneosResult | string>>({});
  // OF-BLD-016 §2.2 — a model of this host shows when its product does, or
  // when the product belongs to the host's own archived program (the page
  // opened under ArchivedBanner).
  const inView = useProgramScope({ kind: 'strain', id: strainId });
  const models = allModels.filter((m) => inView('product', m.product));
  useEffect(() => {
    const ctrl = new AbortController();
    setModels([]);
    setResults({});
    geneosModels(ctrl.signal)
      .then((shelf) => {
        const mine = shelf.filter((x) => x.host === strainId);
        setModels(mine);
        for (const m of mine.filter((x) => !x.unavailable)) {
          geneosCeiling(m.id, m.feed, m.product, ctrl.signal).then(
            (r) => setResults((was) => ({ ...was, [m.id]: r })),
            (e: unknown) => !ctrl.signal.aborted && setResults((was) => ({ ...was, [m.id]: said(e) })),
          );
        }
      })
      .catch(() => undefined);
    return () => ctrl.abort();
  }, [strainId]);
  if (models.length === 0) return null;
  return (
    <section className="mb-6" aria-label="Yield ceiling" data-testid="host-ceiling">
      <div className="rounded-card border border-line bg-surface-0 p-3 space-y-3">
        <div className="font-medium text-reading">
          {models.length === 1
            ? "A published reaction network of this host is on geneOS's shelf"
            : `${models.length} published reaction networks of this host are on geneOS's shelf`}
        </div>
        {models.map((model) => {
          const result = results[model.id];
          return (
            <div key={model.id} data-testid="host-ceiling-model">
              <p className="text-body text-ink-soft">
                {model.name}, {model.scope}. {model.route}.
              </p>
              {model.unavailable && <p className="text-body text-ink mt-1">{model.unavailable}.</p>}
              {typeof result === 'string' && <p className="text-body text-ink mt-1">{result}.</p>}
              {typeof result === 'object' && result.finding && <p className="text-body text-ink mt-1">{result.finding}.</p>}
              {typeof result === 'object' && result.evidence && (
                <div className="mt-2">
                  <EvidenceCard evidence={result.evidence} />
                </div>
              )}
              <a
                className="mt-2 inline-block text-accent hover:underline text-body"
                href={href(`/geneos/model?model=${model.id}&substrate=${model.feed}&product=${model.product}`)}
              >
                Compare it with every reported yield in geneOS → Model
              </a>
            </div>
          );
        })}
      </div>
    </section>
  );
}
