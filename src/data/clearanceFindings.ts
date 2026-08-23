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
// PROVENANCE. These entries are 'curated', not 'verified', and the distinction
// is load-bearing here. In this platform 'verified' means checked against the
// source document. These were read from secondary reporting — a court opinion
// summarised by two law sources, and journal news coverage of an EPO decision.
// The patent registers, the Federal Circuit opinion and the EPO file wrapper
// were all unreachable from the build environment, so nobody has pulled the
// primary documents. Each entry therefore carries its sources, the date they
// were read, and the specific thing a person must do to promote it to
// 'verified'. Marking these 'verified' on the strength of news coverage would
// be the same class of error as the model this file replaces.
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
  /** What the cited source says happened to it. Never a term of art we picked. */
  status: string;
  /** When that happened, where the source gives a date. */
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
        number: 'US 4,683,195',
        title: 'Process for amplifying, detecting, and/or-cloning nucleic acid sequences',
        assignee: 'Cetus Corporation (later Roche)',
        status:
          'Expired. Reporting on the PCR process family states that from this date no US licence was needed to practise basic PCR amplification.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,683,202',
        title: 'Process for amplifying nucleic acid sequences',
        assignee: 'Cetus Corporation (later Roche)',
        status: 'Expired, in the same PCR process family as US 4,683,195.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,965,188',
        title: 'Process for amplifying nucleic acid sequences using a thermostable enzyme',
        assignee: 'Cetus Corporation (later Roche)',
        status: 'Expired, in the same PCR process family as US 4,683,195.',
        at: '2005-03-28',
      },
      {
        office: 'US',
        number: 'US 4,889,818',
        title: 'Purified thermostable enzyme',
        assignee: 'Cetus Corporation (later Roche)',
        status:
          'Issued 1989. Held unenforceable for inequitable conduct by the district court in 1999. On appeal, Hoffmann-La Roche v. Promega, 323 F.3d 1354 (Fed. Cir. 2003) upheld two of the three categories of misstatement, overturned the third, and remanded. This build has not established the outcome after remand.',
        at: '2003',
      },
    ],
    summary:
      'The foundational US position on native Taq is not a live fence. The PCR process family expired in 2005, and the composition patent on the enzyme itself was held unenforceable for inequitable conduct before that. What this does NOT say is anything about hot-start, fusion or other engineered variants, which are separately claimed and are why the molecule’s headline state is watch-variant rather than clear.',
    sources: [
      {
        label:
          'Hoffmann-La Roche, Inc. v. Promega Corp., 323 F.3d 1354 (Fed. Cir. 2003) — as summarised by Finnegan',
        url: 'https://www.finnegan.com/en/tools/hoffmann-la-roche-v-promega/analysis.html',
      },
      {
        label:
          'Cook-Deegan et al., case study on PCR licensing and IP (PMC1523369) — for the 2005 process-patent expiry',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC1523369/',
      },
    ],
    readAt: '2026-08-23',
    toVerify:
      'Pull US 4,683,195 / 4,683,202 / 4,965,188 / 4,889,818 from USPTO Patent Center and confirm the maintenance and term data directly; read 323 F.3d 1354 in full and establish what happened on remand. Then flip provenance to verified and record who checked.',
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
        status:
          'Revoked by the European Patent Office at opposition, on grounds of lack of novelty and obviousness over prior art, following opposition by Promega, Becton Dickinson, New England Biolabs and Bioline. Roche stated it would appeal. This build has NOT established the outcome of that appeal, so the European position is recorded as unresolved rather than clear.',
        at: '2001-05-30',
      },
    ],
    summary:
      'Examined, and still unresolved — which is a different answer from "not assessed" and a very different answer from "clear". A revocation under appeal is not a lapsed patent, and treating it as one is how a facility ends up shipping into a jurisdiction it never actually cleared.',
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
      'Pull the EP 0 258 017 file wrapper from EPO Register and read the Board of Appeal decision. Until someone does, this cell stays unknown — the appeal outcome is the whole question.',
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

/** Products with at least one authored finding — used to label the rest honestly. */
export const PRODUCTS_WITH_FINDINGS: Set<string> = new Set(
  CLEARANCE_FINDINGS.map((f) => f.productId),
);
