// A computed value a claim rests on (OF-BLD-014 §5.4, E.8).
//
// The value is the artifact's, carried in the plan's `evidence`; the model
// cited it by id and wrote none of it. Its provenance is computed from its
// basis on the service, and the basis opens to every input and where each
// came from, with a link to the stored artifact that replays it.
import { ExternalLink } from 'lucide-react';
import type { BasisInput, Evidence, ExtractionRecord } from '@/data/types';
import { useStore } from '@/store';
import { CeilingGap } from './figures';
import { productOfBasis, productWords, yieldsOnSugar } from '@/lib/geneos';
import { fmt } from '@/engine/units';
import { href } from '@/router';
import { ProvenanceBadge, Tick } from './Provenance';

function sourceWords(input: BasisInput): string {
  const s = input.source;
  const what = s.id ?? s.note ?? '';
  return [s.kind, what, s.by ? `(${s.by})` : ''].filter(Boolean).join(' ');
}

/**
 * A ceiling drawn beside every reported yield of its product (OF-BLD-014
 * §6.4): a PHB ceiling beside PHA yields, an ethanol ceiling beside ethanol
 * yields. The product is the one the ceiling's basis names.
 */
function InlineCeiling({ evidence }: { evidence: Evidence }) {
  const records = useStore((s) => s.records);
  // Held against the ceiling: the yields of its product measured on the sugar it was computed for.
  const sugar = String(evidence.basis.inputs.find((i) => i.name === 'substrate')?.value ?? '');
  const product = productOfBasis(evidence.basis.inputs);
  const yields = yieldsOnSugar(records as ExtractionRecord[], sugar, product).on;
  const model = evidence.basis.inputs.find((i) => i.name === 'model')?.source.id ?? 'model';
  return (
    <div className="mt-2" data-testid="inline-ceiling">
      <CeilingGap
        title="The reported yields beside this ceiling"
        records={yields}
        unit={evidence.unit}
        quantity={productWords(product).quantity}
        ceilings={[{ value: Number(evidence.value), model: `${model} ceiling`, basis: evidence.basis, provenance: evidence.provenance }]}
        csvName={`ceiling-${evidence.id}`}
      />
    </div>
  );
}

export function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const b = evidence.basis;
  return (
    <Tick p={evidence.provenance} className="py-1 pl-2.5" title={`${evidence.id} · ${b.tool}`}>
      <div data-testid="evidence-card">
        <div className="text-caption text-ink-soft">{evidence.label}</div>
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="font-num text-reading text-ink">
            {fmt(evidence.value)} {evidence.unit}
          </span>
          {evidence.interval && (
            <span className="font-num text-caption text-ink-soft">
              {fmt(evidence.interval.low)}–{fmt(evidence.interval.high)} {evidence.unit}
            </span>
          )}
          <ProvenanceBadge p={evidence.provenance} compact />
        </div>
        <details className="mt-0.5">
          <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent">
            Basis: {b.tool} {b.toolVersion}
          </summary>
          <ul className="mt-1 space-y-0.5 text-caption">
            {b.inputs.map((i) => (
              <li key={`${i.name}-${sourceWords(i)}`} className="flex flex-wrap gap-x-2">
                <span className="text-ink">{i.name}</span>
                <span className="font-num text-ink">
                  {typeof i.value === 'number' ? fmt(i.value) : i.value} {i.unit}
                </span>
                <span className="text-ink-soft">{sourceWords(i)}</span>
              </li>
            ))}
          </ul>
          <a
            className="mt-1 inline-flex items-center gap-1 text-caption text-ink-soft hover:text-accent"
            href={href(`/biorepo/artifacts/${b.artifactId}`)}
          >
            Artifact {b.artifactId} <ExternalLink size={10} aria-hidden />
          </a>
        </details>
        {evidence.figure === 'ceiling' && typeof evidence.value === 'number' && <InlineCeiling evidence={evidence} />}
      </div>
    </Tick>
  );
}
