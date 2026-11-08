// A kept computation's run on the project's Runs (alpha 2.2 D3): every kept
// simulation, forecast and vessel design is one run of the engine `kinetics`,
// as a train run is one of `train`'s, its id the artifact's, read at
// /proforma/runs/<id> beside every other engine's run.
import { href } from '@/router';

export function EngineRunLink({ artifactId, engine }: { artifactId: string; engine: string }) {
  return (
    <a
      className="text-ink hover:text-accent underline underline-offset-2"
      href={href(`/proforma/runs/${encodeURIComponent(artifactId)}`)}
      data-testid="engine-run-link"
      data-engine={engine}
    >
      its run of the engine {engine}, listed with the project&rsquo;s runs
    </a>
  );
}
