// Authored clearance findings (OF-BLD-005 §8).
//
// This file is the ONLY source of a populated jurisdiction cell. Every office
// not named here reads `unknown`, and the matrix says "not assessed" rather
// than inferring anything. That is deliberate and it replaces an earlier
// version of this feature that spread a product's stored state across offices
// by a filing-propensity model with a deterministic jitter. That model
// produced specific, plausible, actionable-looking divergences out of nothing,
// on the one surface where a false reading has real consequences. Labelling it
// "modeled" did not rescue it: a fabricated divergence is worse than no
// divergence, because it looks like a finding.
//
// TERM EXPIRY IS THE ANSWER; LITIGATION IS COLOUR. Every patent entry carries
// `expiresOnTerm` next to its litigation history, and the UI leads with it.
// Term expiry is arithmetic — a filing date, a statutory term, a date. A
// litigation outcome is contingent, frequently unresolved, and sometimes never
// finally adjudicated at all. US 4,889,818 is the case in point: the Promega
// dispute ran for years, produced a district-court holding of unenforceability
// that the Federal Circuit then vacated, and ended in a settlement rather than
// a judgment — while the patent quietly ran out on its own term regardless. A
// clearance answer built on the litigation would have been built on nothing.
//
// PROVENANCE. These entries are 'curated', not 'verified', and the distinction
// is load-bearing. In this platform 'verified' means checked against the
// source document. These were read from secondary and quasi-primary sources —
// reporting on a court opinion, journal coverage of an EPO decision, and
// register legal-status readouts relayed by a reviewer. Nobody has pulled the
// registers themselves, and nobody can from this build environment: outbound
// access is allowlisted to package registries and GitHub, so patent offices,
// court reporters and journals are permanently unreachable from here. Treat
// that as a fixed property of the environment, not a transient failure — an
// entry only reaches 'verified' when a person pulls the primary document
// outside the build and records that they did.
//
// Nothing here is a legal opinion, and every surface that renders it carries
// the counsel warning.
import type { ClearanceStateId, Provenance } from './types';

export interface ClearancePatent {
  /** Office code as it appears on the family member. */
  office: string;
  number: string;
  title: string;
  assignee: string;
  /**
   * When the patent runs out on its own term, independent of any dispute.
   * This is the field that usually answers the clearance question. Null when
   * this build has not established it — never a guess.
   */
  expiresOnTerm: string | null;
  /** How that date was arrived at, and how firm it is. */
  termBasis?: string;
  /**
   * Register and litigation history. Contingent by nature: read it as context
   * for the term date above, not as a substitute for it.
   */
  status: string;
  /** When the most recent recorded event happened. */
  at?: string;
}

export interface ClearanceFinding {
  productId: string;
  jurisdictionId: string;
  /**
   * 'unknown' is a legitimate finding, not an absence. A cell reading
   * "examined, outcome not established" is a different claim from a cell
   * nobody has looked at, and the matrix distinguishes the two.
   */
  state: ClearanceStateId;
  provenance: Provenance;
  patents: ClearancePatent[];
  summary: string;
  sources: { label: string; url: string }[];
  /** When the sources were read. */
  readAt: string;
  /** Exactly what would move this entry to 'verified'. */
  toVerify: string;
}

export const CLEARANCE_FINDINGS: ClearanceFinding[] = [
  {
    productId: 'taq-dna-polymerase',
    jurisdictionId: 'us',
    state: 'clear-expired',
    provenance: 'curated',
    patents: [
      {
        office: 'US',
        number: 'US 4,683,202',
        title: 'Process for amplifying nucleic acid sequences',
        assignee: 'Cetus Corporation (later Roche)',
        expiresOnTerm: '2005-03-28',
        termBasis:
          'Expiry date as given by the register legal-status readout for this patent specifically.',
        status: 'Expired on term. No unresolved dispute recorded against it here.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,683,195',
        title: 'Process for amplifying, detecting, and/or-cloning nucleic acid sequences',
        assignee: 'Cetus Corporation (later Roche)',
        expiresOnTerm: '2005-03-28',
        termBasis:
          'Same PCR process family as US 4,683,202, and reported to expire on the same date. NOT individually confirmed against the register — the readout that was checked was for the ’202.',
        status: 'Expired on term. No unresolved dispute recorded against it here.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,965,188',
        title: 'Process for amplifying nucleic acid sequences using a thermostable enzyme',
        assignee: 'Cetus Corporation (later Roche)',
        expiresOnTerm: '2005-03-28',
        termBasis:
          'Same PCR process family as US 4,683,202, and reported to expire on the same date. NOT individually confirmed against the register.',
        status: 'Expired on term. No unresolved dispute recorded against it here.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,889,818',
        title: 'Purified thermostable enzyme',
        assignee: 'Cetus Corporation (later Roche)',
        expiresOnTerm: '2006-12-26',
        termBasis:
          'Issued 1989-12-26 from a pre-GATT filing, so it ran seventeen years from issue. The date is arithmetic from the issue date rather than a register readout, so treat it as approximate to within any terminal disclaimer or term adjustment nobody has checked for.',
        status:
          'Never finally adjudicated. The district court held it unenforceable for inequitable conduct (N.D. Cal., December 1999). On appeal, Hoffmann-La Roche v. Promega, 323 F.3d 1354 (Fed. Cir., 31 March 2003) sustained the inequitable-conduct findings but VACATED the unenforceability order and remanded for a determination on remedy. Roche and Promega settled in September 2005, so no court ever entered a final judgment of unenforceability.',
        at: '2005-09',
      },
    ],
    summary:
      'The decisive fact here is arithmetic, not litigation. The PCR process family ran out on term in March 2005 and the composition patent on the enzyme itself ran out around December 2006 — and would have done so whatever the Promega dispute produced. The dispute is worth knowing about and worth nothing to rely on: the unenforceability holding was vacated on appeal and the parties settled before any court entered final judgment, so a clearance position resting on it would have been resting on a result that does not exist. What none of this covers is hot-start, fusion or other engineered variants, which are separately claimed and are why the molecule’s headline state is watch-variant rather than clear.',
    sources: [
      {
        label:
          'Hoffmann-La Roche, Inc. v. Promega Corp., 323 F.3d 1354 (Fed. Cir. 2003) — appellate disposition, vacatur of the unenforceability order and remand on remedy',
        url: 'https://www.finnegan.com/en/tools/hoffmann-la-roche-v-promega/analysis.html',
      },
      {
        label: 'Register legal-status readout for US 4,683,202 — expiry 2005-03-28',
        url: 'https://patents.google.com/patent/US4683202A/en',
      },
      {
        label:
          'Cook-Deegan et al., case study on PCR licensing and intellectual property (PMC1523369)',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC1523369/',
      },
    ],
    readAt: '2026-08-23',
    toVerify:
      'Pull US 4,683,195 / 4,965,188 / 4,889,818 from the USPTO register and confirm each expiry date directly — only the ’202 date has been read off a legal-status readout, and the ’818 date is computed from its issue date rather than read. Confirm no terminal disclaimer or term adjustment shortens or extends the ’818. Read 323 F.3d 1354 in full and confirm the September 2005 settlement terminated the case without a final unenforceability judgment. Then flip provenance to verified and record who checked.',
  },
  {
    productId: 'taq-dna-polymerase',
    jurisdictionId: 'ep',
    state: 'unknown',
    provenance: 'curated',
    patents: [
      {
        office: 'EP',
        number: 'EP 0 258 017 B1',
        title: 'Purified thermostable enzyme',
        assignee: 'F. Hoffmann-La Roche (from Cetus)',
        expiresOnTerm: null,
        termBasis:
          'Not established. The filing and priority dates behind the twenty-year term have not been read off the register from this build, so the date that would settle this cell is exactly the thing that is missing.',
        status:
          'Revoked by the European Patent Office at opposition, on grounds of lack of novelty and obviousness over prior art, following opposition by Promega, Becton Dickinson, New England Biolabs and Bioline. Roche stated it would appeal. This build has NOT established the outcome of that appeal.',
        at: '2001-05-30',
      },
    ],
    summary:
      'Examined, and still unresolved — a different answer from "not assessed" and a very different answer from "clear". Two things are missing and either would settle it: the outcome of the appeal against revocation, and the term expiry date, which is arithmetic and would make the appeal moot if it has already passed. Until one of them is established this cell stays unknown. A revocation under appeal is not a lapsed patent, and treating it as one is how a facility ends up shipping into a jurisdiction it never actually cleared.',
    sources: [
      {
        label:
          'Roche dealt a setback on European Taq patent, Science 292(5523):1815 (2001) — EPO revocation of EP 0 258 017 B1',
        url: 'https://www.science.org/doi/10.1126/science.292.5523.1815a',
      },
      {
        label: 'Roche to appeal European decision to revoke Taq polymerase patent, GenomeWeb',
        url: 'https://www.genomeweb.com/archive/update-roche-appeal-european-decision-revoke-taq-polymerase-patent',
      },
    ],
    readAt: '2026-08-23',
    toVerify:
      'Pull the EP 0 258 017 file wrapper from the EPO Register: read the Board of Appeal decision, and take the filing and priority dates so the twenty-year term can be computed. The term date alone may resolve this cell without the appeal outcome mattering at all.',
  },
];

/** The authored finding for one product in one office, or null. */
export function findingFor(
  productId: string,
  jurisdictionId: string,
): ClearanceFinding | null {
  return (
    CLEARANCE_FINDINGS.find(
      (f) => f.productId === productId && f.jurisdictionId === jurisdictionId,
    ) ?? null
  );
}

/**
 * The last of a finding's patents to run out on term — the date the fence
 * actually falls, ignoring every dispute along the way.
 *
 * Returns null if ANY patent's term is unestablished, because the latest of a
 * partial set is not the latest: one unknown term could outlast everything
 * else in the family, and reporting the maximum of what happens to be known
 * would understate the fence.
 */
export function termFalls(finding: ClearanceFinding): string | null {
  if (finding.patents.length === 0) return null;
  if (finding.patents.some((p) => p.expiresOnTerm === null)) return null;
  // ISO dates sort lexicographically. Indexed rather than .at(-1) because the
  // project targets ES2020.
  const dates = finding.patents.map((p) => p.expiresOnTerm as string).sort();
  return dates[dates.length - 1];
}

/** Products with at least one authored finding — used to label the rest honestly. */
export const PRODUCTS_WITH_FINDINGS: Set<string> = new Set(
  CLEARANCE_FINDINGS.map((f) => f.productId),
);
