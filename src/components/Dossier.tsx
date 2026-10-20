// The chain behind a runbook's predictions (OF-BLD-014 §9.4). For a runbook
// whose predictions point at artifacts, the band lays them out in the order
// the product runs: the geneOS ceiling (stoichiometry), the fermOS forecast
// (dynamics), the Proforma price. Each is drawn from its artifact as the
// service keeps it, shows its basis, and names the prediction it stands
// behind. The two seam sentences the product already uses sit between the
// figures. With the service down the band says the artifacts need it.
import { useEffect, useState } from 'react';
import type { Artifact, Band, ComputedBasis, HistogramBin, Runbook } from '@/data/types';
import { useStore } from '@/store';
import { ArtifactsDown, getArtifact } from '@/lib/artifacts';
import { productOfBasis, productWords, yieldsOnSugar } from '@/lib/geneos';
import { INFEASIBLE_WORDS } from '@/lib/proforma';
import { CeilingGap, Distribution, TrajectoryBand } from '@/components/figures';
import { Card } from './ui';

/** The order of the chain, by the tool that kept each artifact. */
export const DOSSIER_ORDER = ['geneos.ceiling', 'growth_forecast', 'proforma.run'] as const;

/** The seams, in the words fermOS's page already uses. */
export const SEAMS = {
  afterCeiling:
    'Upstream, geneOS is stoichiometry: a genome-scale model gives a yield ceiling with no time axis. fermOS is dynamics: the curve in a specific vessel.',
  afterForecast:
    'The seam to pureOS is the harvest step, and it carries a decision made back in geneOS: secreted or intracellular.',
};

const basisOf = (a: Artifact): ComputedBasis => ({
  tool: a.tool,
  toolVersion: a.toolVersion,
  inputs: a.inputs,
  artifactId: a.id,
  at: a.createdAt,
  seed: a.seed,
});

export interface Link {
  predictionLabel: string;
  artifact: Artifact;
}

export interface Gathered {
  links: Link[];
  /** Predictions whose artifact did not come back, each with why. */
  failed: { predictionLabel: string; why: string }[];
  /** Set when the service did not answer at all. */
  down: string | null;
}

/**
 * Fetch every prediction's artifact and keep what came back, in the chain's
 * order (§9.R: one missing artifact no longer blanks the band). A prediction
 * whose artifact failed is named with the reason; the service being down is
 * said once.
 */
export async function gatherLinks(
  pointed: { label: string; artifactId?: string }[],
  fetch: (id: string) => Promise<Artifact>,
): Promise<Gathered> {
  const settled = await Promise.allSettled(pointed.map((p) => fetch(p.artifactId!)));
  const links: Link[] = [];
  const failed: Gathered['failed'] = [];
  let down: string | null = null;
  settled.forEach((r, i) => {
    if (r.status === 'fulfilled') links.push({ predictionLabel: pointed[i].label, artifact: r.value });
    else if (r.reason instanceof ArtifactsDown)
      down = `These predictions rest on artifacts the service keeps. ${r.reason.message} ${r.reason.remedy}`;
    else failed.push({ predictionLabel: pointed[i].label, why: r.reason instanceof Error ? r.reason.message : String(r.reason) });
  });
  links.sort((x, y) => DOSSIER_ORDER.indexOf(x.artifact.tool as never) - DOSSIER_ORDER.indexOf(y.artifact.tool as never));
  return { links, failed, down };
}

function Figure({ link }: { link: Link }) {
  const records = useStore((s) => s.records);
  const a = link.artifact;
  const o = a.output as Record<string, unknown>;
  if (a.tool === 'geneos.ceiling') {
    const sugar = String(a.inputs.find((i) => i.name === 'substrate')?.value ?? 'glucose');
    const model = String(a.inputs.find((i) => i.name === 'model')?.value ?? 'a reaction network');
    // Beside the reported yields of the product the ceiling is for.
    const product = productOfBasis(a.inputs);
    const reported = productWords(product).reported;
    return (
      <CeilingGap
        title={`What is the most this network allows on ${sugar}?`}
        records={yieldsOnSugar(records, sugar, product).on}
        unit="g g-1"
        quantity={`${reported.charAt(0).toUpperCase()}${reported.slice(1)} on substrate`}
        ceilings={[{ value: Number(o.gPerG), model, basis: basisOf(a), provenance: a.provenance }]}
        csvName={`dossier-ceiling-${a.id}`}
      />
    );
  }
  if (a.tool === 'growth_forecast') {
    const bands = (o.bands as Band[]) ?? [];
    return (
      <TrajectoryBand
        title="What would a run like the fitted one do?"
        series={bands.map((b) => ({ role: b.role, label: b.role, unit: b.unit, readings: [] }))}
        forecast={{ times: (o.times as number[]) ?? [], bands, provenance: a.provenance }}
        basis={[basisOf(a)]}
        csvName={`dossier-forecast-${a.id}`}
      />
    );
  }
  const infeasible = (o.infeasible as Record<string, number>) ?? {};
  return (
    <Distribution
      title="What would the plant's product cost?"
      quantity="Minimum selling price"
      unit="USD kg-1"
      bins={(o.histogram as HistogramBin[]) ?? []}
      quantiles={(o.quantiles as Record<string, number>) ?? {}}
      provenance={a.provenance}
      samples={Number(o.samples ?? 0)}
      infeasible={Object.entries(infeasible).map(([reason, count]) => ({ reason: INFEASIBLE_WORDS[reason] ?? reason, count }))}
      basis={[basisOf(a)]}
      csvName={`dossier-price-${a.id}`}
    />
  );
}

export function Dossier({ runbook }: { runbook: Runbook }) {
  const pointed = runbook.predictions.filter((p) => p.artifactId);
  const [got, setGot] = useState<Gathered | null>(null);
  const key = pointed.map((p) => p.artifactId).join(',');

  useEffect(() => {
    if (!pointed.length) return;
    const ctrl = new AbortController();
    void gatherLinks(pointed, (id) => getArtifact(id, ctrl.signal)).then((g) => {
      if (!ctrl.signal.aborted) setGot(g);
    });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (!pointed.length) return null;
  const links = got?.links ?? null;
  const down = got?.down ?? null;
  return (
    <section className="mb-6" aria-labelledby="band-dossier" data-testid="dossier">
      <h2 id="band-dossier" className="font-serif text-section-title font-semibold mb-1">
        Dossier: the chain behind these predictions
      </h2>
      <p className="text-caption text-ink-soft mb-3 max-w-3xl">
        Each figure is drawn from the artifact a prediction names, with its basis, in the order the product runs: the most the
        organism's network allows, what a vessel does over time, what the plant's product costs.
      </p>
      {down && <Card className="p-4 text-body text-ink-soft" data-testid="dossier-down">{down}</Card>}
      {got?.failed.map((f) => (
        <p key={f.predictionLabel} className="text-caption text-signal-warn" data-testid="dossier-failed">
          The artifact behind {f.predictionLabel} could not be read: {f.why}
        </p>
      ))}
      {links && (
        <div className="space-y-3">
          {links.map((l, i) => {
            const next = links[i + 1];
            const seam =
              next && l.artifact.tool === 'geneos.ceiling' && next.artifact.tool === 'growth_forecast'
                ? SEAMS.afterCeiling
                : next && l.artifact.tool === 'growth_forecast' && next.artifact.tool === 'proforma.run'
                  ? SEAMS.afterForecast
                  : null;
            return (
              <div key={`${l.predictionLabel}:${l.artifact.id}`} data-testid="dossier-link" data-tool={l.artifact.tool}>
                <div className="text-caption text-ink-soft mb-1">
                  Stands behind the prediction <span className="font-medium text-ink">{l.predictionLabel}</span>
                </div>
                <Figure link={l} />
                {seam && (
                  <p className="text-caption italic text-ink-soft mt-2" data-testid="dossier-seam">
                    {seam}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
