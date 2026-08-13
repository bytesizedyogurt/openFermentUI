/**
 * geneOS, answered from the bundled corpus.
 */
import { PAPERS, RECORDS, STRAINS } from '@/data/source';
import type { ExtractionRecord, Paper, Strain } from '@/data/types';
import type {
  AdapterResponse,
  CellAdapter,
  FluxPrediction,
  FluxRequest,
} from '@/adapters/types';
import { respond } from './meta';

/**
 * Word for word the reason every design in this build carries an absent T1.
 * One string, so the adapter and the design engine cannot come to say
 * different things about the same missing model.
 */
const NO_FLUX_MODEL =
  'No genome-scale metabolic model in this build. Flux balance is COBRApy’s, in Python, and ' +
  'server-side; a prediction is absent here rather than estimated, which is what T1 reports on ' +
  'every design for the same reason.';

/**
 * A record counts for a strain when it is tagged with it, or — absent a tag —
 * when its paper's organism list names it. An explicit tag for a different
 * strain always wins, so a two-organism paper never double-counts a record
 * that already knows which organism it belongs to.
 *
 * WRITTEN TWICE, ON PURPOSE AND TEMPORARILY. `recordsFor` in
 * `src/screens/Organisms.tsx` is the same rule; that file is another agent's
 * to migrate and may not be edited here. The rule is server-side work — it is
 * an attribution decision about the corpus, not a display choice — so this is
 * where it ends up, and the screen's copy goes when the screen migrates. The
 * comment is here so that the duplication is visible rather than discovered.
 */
function attributedTo(
  records: readonly ExtractionRecord[],
  paperById: Map<string, Paper>,
  strainId: string,
): ExtractionRecord[] {
  return records.filter((r) => {
    if (r.organism) return r.organism === strainId;
    return paperById.get(r.paperId)?.organisms.includes(strainId) ?? false;
  });
}

export const fixtureCellAdapter: CellAdapter = {
  async listStrains(): Promise<AdapterResponse<Strain[]>> {
    return respond(STRAINS.slice());
  },

  async getStrain(strainId: string): Promise<AdapterResponse<Strain | null>> {
    return respond(STRAINS.find((s) => s.id === strainId) ?? null);
  },

  async getStrainRecords(strainId: string): Promise<AdapterResponse<ExtractionRecord[]>> {
    // Built per call rather than at module scope: under the `api` backend the
    // collections are empty until `initCorpus()` resolves, and a map captured
    // at import would be a map of nothing for the rest of the session.
    const paperById = new Map(PAPERS.map((p) => [p.id, p]));
    return respond(attributedTo(RECORDS, paperById, strainId));
  },

  /**
   * Always `null`, and permanently so under this backend.
   *
   * `notice` carries the reason rather than the absence being silent, because
   * `null` alone reads as "no answer for this strain" when the truth is "no
   * model, for any strain". A caller must be able to tell those apart.
   */
  async predictFlux(_request: FluxRequest): Promise<AdapterResponse<FluxPrediction | null>> {
    return respond(null, { notice: NO_FLUX_MODEL });
  },
};
