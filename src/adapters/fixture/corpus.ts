/**
 * BioRepo, answered from the bundled corpus.
 *
 * Reads go through `@/data/source` — the adapter that already exists, with its
 * two backends and its assembly rules — and not around it. Nothing here
 * re-sorts, re-derives or re-filters what that module already settled.
 */
import { PAPERS, RECORDS, search, withSI } from '@/data/source';
import { PATENTS } from '@/data/patents';
import { GOLD_SET_PLAN, GOLD_SET_DIFFICULTY_CASES } from '@/data/runOutputs';
import { inScope } from '@/engine/scope';
import type { ExtractionRecord, Paper, Patent, ScopeHit } from '@/data/types';
import type {
  AdapterResponse,
  CorpusAdapter,
  GoldSetPlan,
  RecordQuery,
  ScopeRequest,
  WhitespaceRegion,
  WhitespaceRequest,
} from '@/adapters/types';
import type { CorpusSearchOptions, CorpusSearchResult } from '@/data/source';
import { respond } from './meta';

/**
 * Stated on every `writeRecord` response. A caller that renders the record it
 * got back without this is showing a saved row that was not saved.
 */
const NO_DURABLE_STORE =
  'Accepted and normalised, but not persisted — the fixture backend has nowhere to put a record. ' +
  'The session store in src/store.ts is the only writer in this build, and it is also the only ' +
  'thing that can enforce the deposit invariant, because it alone sees records minted this session.';

/**
 * Stated on every `getScope` response.
 *
 * The distinction it carries is the one `DesignRecord.scope` makes about the
 * word `clear`: no hits is not the same sentence as unencumbered.
 */
const SCOPE_NOT_EVALUABLE =
  'No claim in the corpus carries parsed bounds, so nothing was tested. An empty result here ' +
  'means the question could not be asked — not that the configuration is unencumbered.';

/** Stated on every `getWhitespace` response. See the method. */
const WHITESPACE_NOT_COMPUTED =
  'Whitespace is not computed in this build. It is the complement of the claimed regions, and no ' +
  'claim in the corpus has parsed bounds, so the complement of nothing is the entire parameter ' +
  'space — an answer that would read as analysis and be the most damaging thing this method could ' +
  'return. The empty array is a stub, not a finding.';

function matchesQuery(r: ExtractionRecord, q: RecordQuery): boolean {
  if (q.paperId && r.paperId !== q.paperId) return false;
  if (q.field && r.field !== q.field) return false;
  if (q.organism && r.organism !== q.organism) return false;
  return true;
}

export const fixtureCorpusAdapter: CorpusAdapter = {
  async searchPapers(
    query: string,
    options?: CorpusSearchOptions,
  ): Promise<AdapterResponse<CorpusSearchResult>> {
    // `search()` already states what produced its hits, in `method`, for
    // exactly the reason this seam has `notice`. Passed through whole rather
    // than unpacked, so the hits and the statement cannot be separated.
    return respond(await search(query, options ?? {}));
  },

  async getPaper(paperId: string): Promise<AdapterResponse<Paper | null>> {
    return respond(PAPERS.find((p) => p.id === paperId) ?? null);
  },

  async getRecords(query: RecordQuery = {}): Promise<AdapterResponse<ExtractionRecord[]>> {
    if (query.ids) {
      const wanted = new Set(query.ids);
      // Filtered over RECORDS rather than mapped over `ids`, so the order is
      // the corpus's and a duplicate or unknown id cannot put a hole in the
      // result.
      return respond(RECORDS.filter((r) => wanted.has(r.id) && matchesQuery(r, query)));
    }
    return respond(RECORDS.filter((r) => matchesQuery(r, query)));
  },

  /**
   * The six catalogued patents, in authored order.
   *
   * Copied out rather than handed over, like `listStrains` and `listScenarios`
   * do with theirs: the array a caller receives is its own, and a screen that
   * sorts or splices what it got back cannot reach into the module's copy.
   * Order is the module's and is not re-sorted here — see the KNOWN GAP in
   * `src/data/source.ts` on array order being the datum for collections with
   * no ordering key.
   */
  async listPatents(): Promise<AdapterResponse<Patent[]>> {
    return respond(PATENTS.slice());
  },

  /**
   * The planned gold set, straight out of OF-COR-001 §18.
   *
   * NOTHING IS COMPUTED, so no `modelVersion` — `ResponseMeta` says an absent
   * one means no model ran, and a plan read off a curation document is a read.
   * In particular this does NOT report progress against the plan: "0 of 62
   * annotated" is the screen's arithmetic over a corpus with no `gold`
   * records in it, and the day there are some it becomes a count over
   * `getRecords`, not a number this method starts asserting.
   */
  async getGoldSetPlan(): Promise<AdapterResponse<GoldSetPlan>> {
    return respond({
      entries: GOLD_SET_PLAN.slice(),
      difficultyCases: GOLD_SET_DIFFICULTY_CASES.slice(),
    });
  },

  async writeRecord(record: ExtractionRecord): Promise<AdapterResponse<ExtractionRecord>> {
    // Normalised with the SAME function the read path uses, so the value that
    // comes back is the value the corpus would have held. That is real work
    // and worth doing here; storing it is not this backend's to do.
    return respond(withSI(record), { notice: NO_DURABLE_STORE });
  },

  /**
   * NEW METHOD. Empty under the fixture — but empty because the arithmetic ran
   * and found nothing, not because it was skipped.
   *
   * `inScope` is real and already built: it takes a configuration and a claim
   * and answers. What it has nothing to answer against is the corpus, where
   * every one of the six patents carries `bounds: []` and `parseUncertain:
   * true`, because no claim text has been retrieved. `inScope` returns false
   * for a claim with no bounds by design — "an unparsed claim is not a claim
   * that covers nothing" — so this returns `[]` today and will return hits the
   * day claims are parsed, with no change here.
   */
  async getScope(request: ScopeRequest): Promise<AdapterResponse<ScopeHit[]>> {
    const hits: ScopeHit[] = [];
    for (const patent of PATENTS) {
      for (const claim of patent.claims) {
        if (inScope(request.config, claim)) {
          hits.push({ patentId: patent.id, claim: claim.number });
        }
      }
    }
    return respond(hits, { notice: SCOPE_NOT_EVALUABLE });
  },

  /**
   * NEW METHOD. Always empty under the fixture, and unlike `getScope` nothing
   * even runs.
   *
   * There is no whitespace function in this repo to call, and writing one for
   * this backend would produce a single answer: with zero parsed claims, every
   * region is unclaimed and the whole parameter space is whitespace. That is
   * not a conservative default — it is the most commercially dangerous
   * sentence the system could emit, and it would arrive with the authority of
   * a computation. Parchment already refuses to draw the scope map for the
   * same reason, in the same words: a region inferred from subject matter is a
   * guess wearing the clothes of an analysis.
   *
   * So the array is empty and `notice` says the array is a stub. A real
   * BioRepo computes this from parsed claim bounds and returns regions with
   * the patents they abut named.
   */
  async getWhitespace(
    _request?: WhitespaceRequest,
  ): Promise<AdapterResponse<WhitespaceRegion[]>> {
    return respond([], { notice: WHITESPACE_NOT_COMPUTED });
  },
};
