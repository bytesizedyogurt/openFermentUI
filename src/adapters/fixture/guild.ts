/**
 * The Guild, answered honestly — which here means answered mostly empty.
 *
 * Of the three things this adapter fronts, one exists in the repo and two do
 * not. Deposits exist as a type and a store action and are SEEDED EMPTY on
 * purpose, because a fabricated bench deposit stamped `evidenceClass:
 * 'experiment'` would launder invented data as measurement. Chapters and seals
 * have no registry, no records and no issuer. None of that is fixed by
 * returning something.
 */
import type { RunOutcome } from '@/data/types';
import type {
  AdapterResponse,
  DepositQuery,
  GuildAdapter,
  GuildChapter,
  Seal,
  SealQuery,
  SealRequest,
} from '@/adapters/types';
import { AdapterRefusal } from '@/adapters/types';
import { respond } from './meta';

const NO_CHAPTER_REGISTRY =
  'No chapter registry exists. The empty list is the absence of a registry, not a guild with no ' +
  'chapters in it, and inventing an institution to populate it would be inventing an affiliation.';

/**
 * Deposits are session-only by product decision, like everything else in this
 * build: no localStorage, no sessionStorage, nothing that outlives a reload.
 */
const DEPOSITS_ARE_SESSION_ONLY =
  'Deposits made in this session live in the store (OFState.deposits) and nowhere else — session ' +
  'only, by design, and seeded empty because a fabricated bench deposit would enter the Ledger as ' +
  'measurement. A guild server is what would make a deposit outlive the session; none is running.';

const NOTHING_SEALED =
  'Nothing has been sealed, because nothing can be. The empty list is the absence of an issuer, ' +
  'not a queue that came back clean.';

export const fixtureGuildAdapter: GuildAdapter = {
  async listChapters(): Promise<AdapterResponse<GuildChapter[]>> {
    return respond([], { notice: NO_CHAPTER_REGISTRY });
  },

  async getChapter(_chapterId: string): Promise<AdapterResponse<GuildChapter | null>> {
    return respond(null, { notice: NO_CHAPTER_REGISTRY });
  },

  /**
   * Always empty, and NOT because the store is empty — this adapter cannot see
   * the store at all, and must not: the store reads the data layer, so an
   * adapter that read the store would close a loop between the two.
   */
  async listDeposits(_query?: DepositQuery): Promise<AdapterResponse<RunOutcome[]>> {
    return respond([], { notice: DEPOSITS_ARE_SESSION_ONLY });
  },

  /**
   * Accepts and hands back, exactly as `writeRecord` does, and for the same
   * reason: what it was given is what it returns, so nothing is manufactured.
   *
   * It does NOT set `depositedAt`, and that omission is the honest part — a
   * timestamp would assert that something recorded this. `store.depositRun`
   * stamps it when the session takes the deposit, and the store is also the
   * only thing that can enforce the invariant that every produced record is
   * `evidenceClass: 'experiment'`, because only the store can see records
   * minted this session.
   */
  async submitDeposit(outcome: RunOutcome): Promise<AdapterResponse<RunOutcome>> {
    return respond(outcome, { notice: DEPOSITS_ARE_SESSION_ONLY });
  },

  async listSeals(_query?: SealQuery): Promise<AdapterResponse<Seal[]>> {
    return respond([], { notice: NOTHING_SEALED });
  },

  /**
   * REFUSES. The only method on this seam that does.
   *
   * Every other fixture method either returns what it was handed or returns
   * what it computed. This one would have to MINT an artifact — a seal is an
   * attestation that some chapter checked something, and there is no chapter
   * and no check. A fabricated one would carry authority nobody granted, and
   * it would carry it into exactly the place where authority matters most:
   * Notary's standing finding is that NO design currently clears enablement,
   * so the first seal in this build would be a stamp on a disclosure that a
   * screen elsewhere is busy explaining cannot be made.
   *
   * Refusing is louder than returning `null`, deliberately. `null` would let a
   * caller shrug; a rejection makes the missing subsystem visible at the call
   * site, which is where somebody can do something about it.
   */
  async requestSeal(_request: SealRequest): Promise<AdapterResponse<Seal>> {
    throw new AdapterRefusal(
      'GuildAdapter',
      'requestSeal',
      'a seal is an attestation and there is no chapter here to make one; issuing one from the ' +
        'fixture would stamp a disclosure nobody checked',
    );
  },
};
