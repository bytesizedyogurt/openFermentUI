// Settings → Figure grammar (OF-BLD-014 §6.1): the written definition of the
// grammar, and the encoding legend.
//
// OF-BLD-016 §3.2: the page draws over real results or not at all. When the
// service keeps a computed ceiling or frontier (BioRepo → Artifacts), the
// latest of each is drawn here beside the records it is held against; with
// none kept, or no service, the legend stands alone.
import { useEffect, useMemo, useState } from 'react';
import type { Artifact, ExtractionRecord } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { listArtifacts } from '@/lib/artifacts';
import { productOfBasis, productWords, yieldsOnSugar, type FrontierPointOut } from '@/lib/geneos';
import { CeilingGap, EncodingLegend, Frontier } from '@/components/figures';

const UNIT = 'g g⁻¹';

const inputOf = (a: Artifact, name: string): string | null => {
  const v = a.inputs.find((i) => i.name === name)?.value;
  return v == null ? null : String(v);
};

/** The newest artifact a tool kept, or null. */
const latest = (all: Artifact[], tool: string): Artifact | null =>
  all.filter((a) => a.tool === tool).sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))[0] ?? null;

export function FiguresSection() {
  // The newest ceiling and frontier the service keeps, drawn beside the
  // records they are held against.
  const records = useStore((s) => s.records);
  const [artifacts, setArtifacts] = useState<Artifact[] | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    listArtifacts(ctrl.signal).then(
      (all) => setArtifacts(Array.isArray(all) ? all : []),
      () => !ctrl.signal.aborted && setArtifacts([]),
    );
    return () => ctrl.abort();
  }, []);

  const ceiling = artifacts ? latest(artifacts, 'geneos.ceiling') : null;
  const frontier = artifacts ? latest(artifacts, 'geneos.frontier') : null;
  const frontierPoints = frontier && Array.isArray(frontier.output.points) ? (frontier.output.points as FrontierPointOut[]) : null;

  const ceilingFigure = useMemo(() => {
    if (!ceiling || typeof ceiling.output.gPerG !== 'number') return null;
    const product = String(ceiling.output.product ?? productOfBasis(ceiling.inputs));
    const substrate = String(ceiling.output.substrate ?? inputOf(ceiling, 'substrate') ?? '');
    const model = String(ceiling.output.modelId ?? inputOf(ceiling, 'model') ?? 'model');
    const words = productWords(product);
    return {
      product,
      substrate,
      words,
      on: yieldsOnSugar(records as ExtractionRecord[], substrate, product).on,
      ceilings: [{ value: ceiling.output.gPerG as number, model: `${model} ceiling`, provenance: ceiling.provenance }],
    };
  }, [ceiling, records]);

  const drawn = (ceilingFigure ? 1 : 0) + (frontierPoints ? 1 : 0);

  return (
    <div className="space-y-4" data-testid="figure-gallery">
      <section>
        <h2 className="font-medium text-reading mb-1.5">The marks</h2>
        <p className="text-body text-ink-soft mb-2">
          The kind of thing decides the mark: a measurement or a record is a point, a computed limit a rule line, a computed
          curve a line. Provenance decides shape, fill and dash, so a figure reads the same in greyscale. A filled point
          always stands for an observed value.
        </p>
        <EncodingLegend />
      </section>
      {artifacts === null ? (
        <p className="text-caption text-ink-soft">Asking the service for the results it keeps…</p>
      ) : drawn === 0 ? (
        <p className="text-body text-ink-soft" data-testid="figures-legend-only">
          No computed ceiling or frontier is kept on this service yet, so the grammar is shown by its legend alone. Compute one
          in{' '}
          <a className="text-accent hover:underline" href={href('/geneos/model')}>
            geneOS → Model
          </a>{' '}
          and it is drawn here as every figure draws it.
        </p>
      ) : (
        <p className="text-body text-ink-soft" data-testid="figures-from-artifacts">
          Drawn over the newest results this service keeps, listed in{' '}
          <a className="text-accent hover:underline" href={href('/biorepo/artifacts')}>
            BioRepo → Artifacts
          </a>
          .
        </p>
      )}
      {ceilingFigure && (
        <CeilingGap
          title={`How far is each reported ${ceilingFigure.words.reported} from the most a network allows on ${ceilingFigure.substrate}?`}
          records={ceilingFigure.on}
          unit={UNIT}
          quantity={ceilingFigure.words.quantity}
          ceilings={ceilingFigure.ceilings}
          csvName={`ceiling-gap-${ceilingFigure.product}-${ceilingFigure.substrate}`}
        />
      )}
      {frontier && frontierPoints && (
        <Frontier
          title={`How much ${productWords(productOfBasis(frontier.inputs)).short} can a growing cell make?`}
          points={frontierPoints.map((p) => ({ growth: p.growth, product: p.gPerG }))}
          growthUnit="h⁻¹"
          productUnit={UNIT}
          productLabel={productWords(productOfBasis(frontier.inputs)).quantity}
          model={inputOf(frontier, 'model') ?? 'model'}
          csvName="frontier-latest"
        />
      )}
    </div>
  );
}
