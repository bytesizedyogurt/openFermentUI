// geneOS → Model (OF-BLD-014 §6.4): the ceiling beside what was reported.
//
// Pick a sugar and a model. The service computes, for every model on the
// shelf that can take the sugar up, the most PHB the network can make from
// it (flux balance analysis, kept as an artifact), and the view draws each as
// a dotted rule beside every reported PHA-yield record in the store: curated,
// verified, and the extractor's undecided candidates as hollow marks. A point
// above a rule is ringed and listed for a reviewer to check its basis. Below
// sit the chosen model's production envelope and its sugar-mix line. With the
// service down this says so; nothing stands in for a result (E.2).
import { useEffect, useMemo, useState } from 'react';
import { Calculator } from 'lucide-react';
import type { ExtractionRecord, GeneosModelInfo, GeneosResult } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { Callout, EmptyState } from '@/components/ui';
import { EvidenceCard } from '@/components/EvidenceCard';
import { CeilingGap, Frontier, MixLine, stripPoints, type Ceiling } from '@/components/figures';
import { GeneosDown, GeneosRefused, SUBSTRATES, geneosCeiling, geneosFrontier, geneosMix, geneosModels, type FrontierPointOut, type MixPointOut } from '@/lib/geneos';

const FIELD = 'pha_yield_substrate';
const UNIT = 'g g⁻¹';
const QUANTITY = 'PHB yield on substrate';

/** The one line the geneOS callout says, repeated where a ceiling is drawn. */
export const NOT_A_VESSEL = 'Nothing on this screen predicts what a vessel will produce: a ceiling has no time axis and no vessel.';

interface Loaded {
  ceilings: GeneosResult[];
  frontier: GeneosResult | null;
  mix: GeneosResult | null;
}

export default function GeneOSModel() {
  const route = useRoute();
  const records = useStore((s) => s.records);
  const [shelf, setShelf] = useState<GeneosModelInfo[] | null>(null);
  const [down, setDown] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [busy, setBusy] = useState(false);

  const substrate = route.query.get('substrate') ?? 'glucose';
  const modelId = route.query.get('model') ?? '';
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

  const usable = useMemo(() => (shelf ?? []).filter((m) => !m.unavailable), [shelf]);
  const chosen = usable.find((m) => m.id === modelId) ?? usable[0] ?? null;

  useEffect(() => {
    if (!shelf || !chosen) return;
    const ctrl = new AbortController();
    setBusy(true);
    setRefused(null);
    const other = substrate === 'xylose' ? 'glucose' : 'xylose';
    Promise.all([
      Promise.all(usable.map((m) => geneosCeiling(m.id, substrate, 'phb', ctrl.signal))),
      geneosFrontier(chosen.id, substrate, 'phb', ctrl.signal),
      geneosMix(chosen.id, substrate === 'xylose' ? 'glucose' : substrate, substrate === 'xylose' ? 'xylose' : other, 'phb', ctrl.signal),
    ])
      .then(([ceilings, frontier, mix]) => setLoaded({ ceilings, frontier, mix }))
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        if (e instanceof GeneosRefused) setRefused(e.message);
        else if (e instanceof GeneosDown) setDown(`${e.message} ${e.remedy}`);
        else setRefused(String(e));
      })
      .finally(() => !ctrl.signal.aborted && setBusy(false));
    return () => ctrl.abort();
  }, [shelf, chosen?.id, substrate, usable]);

  const yields = useMemo(() => records.filter((r) => r.field === FIELD) as ExtractionRecord[], [records]);
  const ceilings: Ceiling[] = (loaded?.ceilings ?? [])
    .filter((c) => c.evidence)
    .map((c) => ({
      value: Number(c.evidence!.value),
      model: `${c.modelId} ceiling`,
      basis: c.evidence!.basis,
    }));
  const findings = [
    ...(loaded?.ceilings ?? []).filter((c) => c.finding).map((c) => `${c.modelId}: ${c.finding}`),
    ...(shelf ?? []).filter((m) => m.unavailable).map((m) => `${m.id}: ${m.unavailable}`),
  ];
  const flagged = stripPoints({ title: '', records: yields, unit: UNIT, quantity: QUANTITY, groupBy: 'organism', rules: ceilings.map((c) => ({ value: c.value, label: c.model })), flagAbove: true }).points.filter((p) => p.above);

  if (down) {
    return <EmptyState icon={<Calculator size={28} />} title="The Model view needs the service" body={<>{down} The service runs flux balance analysis in its geneOS worker.</>} />;
  }

  return (
    <div className="space-y-4" data-testid="geneos-model">
      <Callout kind="info" title="Stoichiometry, not a forecast">
        {NOT_A_VESSEL}
      </Callout>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">Product</span>
          <select className="input" value="phb" disabled aria-label="Product">
            <option value="phb">PHB (poly-3-hydroxybutyrate)</option>
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
          title={`How far is each reported PHA yield from the most a network allows on ${substrate}?`}
          records={yields}
          unit={UNIT}
          quantity={QUANTITY}
          ceilings={ceilings}
          csvName={`ceiling-gap-${substrate}`}
        />
      )}

      {flagged.length > 0 && (
        <section aria-label="Yields above a ceiling" className="space-y-1.5" data-testid="above-ceiling">
          <h3 className="font-medium text-reading">Reported above a ceiling: check the basis</h3>
          {flagged.map((p) => (
            <div key={p.record.id} className="rounded-card border border-signal-warn/45 bg-signal-warn/[0.06] p-2 text-body">
              <span className="font-num">{p.record.id}</span> ({p.group}) is {p.above}. A reported yield above a network's
              ceiling may rest on a different basis (another sugar counted, the dry weight measured otherwise).{' '}
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
          title={`How much PHB can a growing cell make on ${substrate}, by ${chosen.id}?`}
          points={(loaded.frontier.output.points as FrontierPointOut[]).map((p) => ({ growth: p.growth, product: p.gPerG }))}
          growthUnit="h⁻¹"
          productUnit={UNIT}
          productLabel={QUANTITY}
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
          quantity={QUANTITY}
          model={chosen.name}
          csvName={`sugar-mix-${chosen.id}`}
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

      {shelf && (
        <section aria-label="The shelf">
          <h3 className="font-medium text-reading mb-1">The shelf</h3>
          <ul className="space-y-1 text-body">
            {shelf.map((m) => (
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
 * On a strain page: when a model of this host is on geneOS's shelf, its
 * ceiling on the sugar it takes up, and a link to the Model view. With the
 * service down, or no model of this host, it draws nothing.
 */
export function HostCeilingCard({ strainId }: { strainId: string }) {
  const [model, setModel] = useState<GeneosModelInfo | null>(null);
  const [result, setResult] = useState<GeneosResult | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    geneosModels(ctrl.signal)
      .then((shelf) => {
        const m = shelf.find((x) => x.host === strainId) ?? null;
        setModel(m);
        if (m && !m.unavailable) return geneosCeiling(m.id, m.feed, 'phb', ctrl.signal).then(setResult);
      })
      .catch(() => undefined);
    return () => ctrl.abort();
  }, [strainId]);
  if (!model) return null;
  const to = href(`/geneos/model?model=${model.id}&substrate=${model.feed}`);
  return (
    <section className="mb-6" aria-label="Yield ceiling" data-testid="host-ceiling">
      <div className="rounded-card border border-line bg-surface-0 p-3">
        <div className="font-medium text-reading">A published reaction network of this host is on geneOS's shelf</div>
        <p className="text-body text-ink-soft mt-0.5">
          {model.name}, {model.scope}. {model.route}.
        </p>
        {model.unavailable && <p className="text-body text-ink mt-1">{model.unavailable}.</p>}
        {result?.finding && <p className="text-body text-ink mt-1">{result.finding}.</p>}
        {result?.evidence && (
          <div className="mt-2">
            <EvidenceCard evidence={result.evidence} />
          </div>
        )}
        <a className="mt-2 inline-block text-accent hover:underline text-body" href={to}>
          Compare it with every reported yield in geneOS → Model
        </a>
      </div>
    </section>
  );
}
